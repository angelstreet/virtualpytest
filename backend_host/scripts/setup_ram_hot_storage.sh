#!/bin/bash
# Setup RAM-based hot storage - DYNAMIC FROM .ENV
# Auto-configures /etc/fstab for automatic remount on reboot
# Reads device configuration from backend_host/src/.env

set -e

MOUNT_SIZE="200M"
BASE_PATH="/var/www/html/stream"
FSTAB_BACKUP="/etc/fstab.backup.$(date +%Y%m%d_%H%M%S)"

# Get script directory and find .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/backend_host/src/.env"

echo "================================"
echo "RAM Hot Storage Setup (Dynamic)"
echo "================================"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found at $ENV_FILE"
    echo "   Please run install_host.sh first to create .env file"
    exit 1
fi

echo "Reading device configuration from: $ENV_FILE"
echo ""

# Parse devices from .env file (look for HOST_VIDEO_CAPTURE_PATH and DEVICE{N}_VIDEO_CAPTURE_PATH)
DEVICES=()

# Check for HOST device first
HOST_CAPTURE_PATH=$(grep "^HOST_VIDEO_CAPTURE_PATH=" "$ENV_FILE" 2>/dev/null | cut -d '=' -f 2- | tr -d '"' | tr -d "'")
if [ -n "$HOST_CAPTURE_PATH" ]; then
    CAPTURE_FOLDER=$(basename "$HOST_CAPTURE_PATH")
    DEVICES+=("$CAPTURE_FOLDER")
    echo "✓ Found host: HOST -> $CAPTURE_FOLDER"
fi

# Check for regular devices (dynamically detect up to 100)
for i in {1..14}; do
    DEVICE_NAME=$(grep "^DEVICE${i}_NAME=" "$ENV_FILE" 2>/dev/null | cut -d '=' -f 2- | tr -d '"' | tr -d "'")
    VIDEO_CAPTURE_PATH=$(grep "^DEVICE${i}_VIDEO_CAPTURE_PATH=" "$ENV_FILE" 2>/dev/null | cut -d '=' -f 2- | tr -d '"' | tr -d "'")
    
    if [ -n "$VIDEO_CAPTURE_PATH" ]; then
        CAPTURE_FOLDER=$(basename "$VIDEO_CAPTURE_PATH")
        DEVICES+=("$CAPTURE_FOLDER")
        echo "✓ Found device$i: $DEVICE_NAME -> $CAPTURE_FOLDER"
    elif [ $i -gt 20 ] && [ ${#DEVICES[@]} -gt 0 ]; then
        # Stop scanning after 20 consecutive empty slots beyond configured devices
        break
    fi
done

if [ ${#DEVICES[@]} -eq 0 ]; then
    echo "⚠️  No devices found in .env file"
    echo "   Please configure DEVICE1_VIDEO_CAPTURE_PATH, etc. in $ENV_FILE"
    exit 1
fi

echo ""
echo "Configuring RAM storage for ${#DEVICES[@]} device(s): ${DEVICES[*]}"
echo ""

# Check if we have sudo access
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  This script requires sudo access"
    exit 1
fi

# Get www-data user info for web server access
WWW_DATA_UID=$(id -u www-data 2>/dev/null || echo "33")  # Default UID 33 if www-data doesn't exist yet
WWW_DATA_GID=$(id -g www-data 2>/dev/null || echo "33")  # Default GID 33

# Get current user info (for fallback/verification)
CURRENT_USER=$(whoami)
CURRENT_UID=$(id -u)
CURRENT_GID=$(id -g)

echo "Mount ownership: www-data (uid=$WWW_DATA_UID, gid=$WWW_DATA_GID)"
echo "Current user: $CURRENT_USER (uid=$CURRENT_UID)"
echo ""

# Add current user to www-data group for access (if not already in it)
if ! groups "$CURRENT_USER" | grep -q "\bwww-data\b"; then
    echo "Adding $CURRENT_USER to www-data group for access..."
    sudo usermod -a -G www-data "$CURRENT_USER"
    echo "✓ User $CURRENT_USER added to www-data group"
    echo "⚠️  You may need to log out and back in for group changes to take effect"
    echo ""
else
    echo "✓ User $CURRENT_USER already in www-data group"
    echo ""
fi

for DEVICE in "${DEVICES[@]}"; do
  HOT_PATH="$BASE_PATH/$DEVICE/hot"
  
  # Create mount point
  echo "Creating mount point: $HOT_PATH"
  sudo mkdir -p "$HOT_PATH"
  
  # Check if already mounted
  if mount | grep -q "$HOT_PATH"; then
    echo "✓ $HOT_PATH already mounted"
  else
    # Mount tmpfs with www-data ownership (for nginx access) + group writable
    echo "Mounting tmpfs ($MOUNT_SIZE) at $HOT_PATH"
    sudo mount -t tmpfs -o size=$MOUNT_SIZE,noexec,nodev,nosuid,uid=$WWW_DATA_UID,gid=$WWW_DATA_GID,mode=775 tmpfs "$HOT_PATH"
    echo "✓ Mounted (owner: www-data, mode: 775)"
  fi
  
  # Create subdirectories in RAM (instant, no SD card I/O)
  sudo mkdir -p "$HOT_PATH/captures"
  sudo mkdir -p "$HOT_PATH/thumbnails"
  sudo mkdir -p "$HOT_PATH/segments"
  sudo mkdir -p "$HOT_PATH/metadata"
  sudo mkdir -p "$HOT_PATH/audio"
  
  # Fix ownership and permissions (www-data:www-data, group writable)
  sudo chown -R www-data:www-data "$HOT_PATH"
  sudo chmod 777 "$HOT_PATH"
  sudo chmod 777 "$HOT_PATH/captures"
  sudo chmod 777 "$HOT_PATH/thumbnails"
  sudo chmod 777 "$HOT_PATH/segments"
  sudo chmod 777 "$HOT_PATH/audio"
  
  # CRITICAL: metadata directory needs 777 for archiver to move files (different user)
  sudo chmod 777 "$HOT_PATH/metadata"
  
  echo "✓ $DEVICE hot storage ready (www-data:www-data, group writable)"
  
  # Create ALL cold storage directories with 777 permissions
  for subdir in captures segments metadata audio; do
    COLD_DIR="$BASE_PATH/$DEVICE/$subdir"
    if [ ! -d "$COLD_DIR" ]; then
      sudo mkdir -p "$COLD_DIR"
      sudo chown www-data:www-data "$COLD_DIR"
    fi
    sudo chmod 777 "$COLD_DIR"
  done
  
  # Create hour folders and temp directory
  for hour in {0..23}; do
    HOUR_DIR="$BASE_PATH/$DEVICE/segments/$hour"
    if [ ! -d "$HOUR_DIR" ]; then
      sudo mkdir -p "$HOUR_DIR"
      sudo chown www-data:www-data "$HOUR_DIR"
    fi
    sudo chmod 777 "$HOUR_DIR"
  done
  
  TEMP_DIR="$BASE_PATH/$DEVICE/segments/temp"
  if [ ! -d "$TEMP_DIR" ]; then
    sudo mkdir -p "$TEMP_DIR"
    sudo chown www-data:www-data "$TEMP_DIR"
  fi
  sudo chmod 777 "$TEMP_DIR"
  
  echo "✓ Cold storage ready (all dirs 777)"
  echo ""
done

# Configure /etc/fstab for auto-mount on reboot
echo "================================"
echo "Configuring /etc/fstab for auto-mount on reboot..."
echo "================================"

# Backup fstab
sudo cp /etc/fstab "$FSTAB_BACKUP"
echo "✓ Backed up /etc/fstab to $FSTAB_BACKUP"

ENTRIES_ADDED=0

for DEVICE in "${DEVICES[@]}"; do
  HOT_PATH="$BASE_PATH/$DEVICE/hot"
  FSTAB_LINE="tmpfs $HOT_PATH tmpfs size=$MOUNT_SIZE,noexec,nodev,nosuid,uid=$WWW_DATA_UID,gid=$WWW_DATA_GID,mode=775 0 0"
  
  # Check if entry already exists
  if grep -q "$HOT_PATH" /etc/fstab; then
    echo "✓ $HOT_PATH already in /etc/fstab"
  else
    echo "Adding $HOT_PATH to /etc/fstab..."
    echo "$FSTAB_LINE" | sudo tee -a /etc/fstab > /dev/null
    echo "✓ Added (www-data:www-data, mode: 775)"
    ENTRIES_ADDED=$((ENTRIES_ADDED + 1))
  fi
done

if [ $ENTRIES_ADDED -gt 0 ]; then
  echo ""
  echo "Testing /etc/fstab configuration..."
  if sudo mount -a; then
    echo "✅ /etc/fstab test successful - mounts will auto-mount on reboot"
  else
    echo "❌ /etc/fstab test failed - restoring backup"
    sudo cp "$FSTAB_BACKUP" /etc/fstab
    exit 1
  fi
fi

# Clean up: Unmount and remove from fstab any devices NOT in .env
echo ""
echo "================================"
echo "Cleaning up unused devices..."
echo "================================"

# Find all mounted hot storage paths and check if they're still configured
MOUNTED_HOT_PATHS=$(mount | grep "$BASE_PATH.*hot" | awk '{print $3}')
CLEANUP_COUNT=0

for HOT_PATH in $MOUNTED_HOT_PATHS; do
  CAPTURE_FOLDER=$(basename "$(dirname "$HOT_PATH")")
  
  # Check if this device is in our active list
  if [[ ! " ${DEVICES[*]} " =~ " ${CAPTURE_FOLDER} " ]]; then
    echo "Unmounting unused device: $CAPTURE_FOLDER"
    sudo umount "$HOT_PATH" 2>/dev/null && CLEANUP_COUNT=$((CLEANUP_COUNT + 1)) || echo "  ⚠️  Could not unmount $HOT_PATH"
  fi
done

# Also check fstab for entries not in active list
FSTAB_HOT_PATHS=$(grep "$BASE_PATH.*hot" /etc/fstab 2>/dev/null | awk '{print $2}')
for HOT_PATH in $FSTAB_HOT_PATHS; do
  CAPTURE_FOLDER=$(basename "$(dirname "$HOT_PATH")")
  
  if [[ ! " ${DEVICES[*]} " =~ " ${CAPTURE_FOLDER} " ]]; then
    echo "Removing $CAPTURE_FOLDER from /etc/fstab..."
    sudo cp /etc/fstab "$FSTAB_BACKUP.cleanup"
    sudo grep -v "$HOT_PATH" /etc/fstab | sudo tee /etc/fstab.tmp > /dev/null
    sudo mv /etc/fstab.tmp /etc/fstab
    echo "  ✓ Removed from /etc/fstab"
    CLEANUP_COUNT=$((CLEANUP_COUNT + 1))
  fi
done

if [ $CLEANUP_COUNT -eq 0 ]; then
  echo "✓ No unused devices found"
fi

# Show mounted RAM disks
echo ""
echo "================================"
echo "Mounted RAM disks:"
df -h | grep -E "hot|Filesystem"
echo "================================"

echo ""
echo "✅ RAM hot storage setup complete!"
echo "   • Devices configured: ${#DEVICES[@]} (${DEVICES[*]})"
echo "   • Each device mounted in RAM ($MOUNT_SIZE)"
echo "   • Owner: www-data:www-data"
echo "   • All directories: 777 (full cross-service access)"
echo "   • Auto-mount configured in /etc/fstab"
echo "   • Will automatically remount on reboot"
echo ""
echo "💡 To add/remove devices:"
echo "   1. Edit $ENV_FILE"
echo "   2. Add/remove HOST_VIDEO_CAPTURE_PATH or DEVICE{N}_VIDEO_CAPTURE_PATH"
echo "   3. Re-run this script to apply changes"
echo ""
echo "⚠️  NOTE: If you just added $CURRENT_USER to www-data group,"
echo "   you may need to log out and back in for changes to take effect"
echo ""
