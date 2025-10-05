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

# Parse devices from .env file (look for DEVICE1_VIDEO_CAPTURE_PATH, etc.)
DEVICES=()
for i in {1..8}; do
    DEVICE_NAME=$(grep "^DEVICE${i}_NAME=" "$ENV_FILE" 2>/dev/null | cut -d '=' -f 2- | tr -d '"' | tr -d "'")
    VIDEO_CAPTURE_PATH=$(grep "^DEVICE${i}_VIDEO_CAPTURE_PATH=" "$ENV_FILE" 2>/dev/null | cut -d '=' -f 2- | tr -d '"' | tr -d "'")
    
    if [ -n "$VIDEO_CAPTURE_PATH" ]; then
        # Extract capture folder name from path (e.g., /var/www/html/stream/capture1 -> capture1)
        CAPTURE_FOLDER=$(basename "$VIDEO_CAPTURE_PATH")
        DEVICES+=("$CAPTURE_FOLDER")
        echo "✓ Found device$i: $DEVICE_NAME -> $CAPTURE_FOLDER"
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
  sudo chmod 775 "$HOT_PATH"
  sudo chmod 775 "$HOT_PATH"/*
  
  # CRITICAL: metadata directory needs 777 for archiver to move files (different user)
  sudo chmod 777 "$HOT_PATH/metadata"
  
  echo "✓ $DEVICE hot storage ready (www-data:www-data, group writable)"
  
  # Also ensure cold storage directories exist with correct permissions
  COLD_METADATA="$BASE_PATH/$DEVICE/metadata"
  COLD_AUDIO="$BASE_PATH/$DEVICE/audio"
  
  if [ ! -d "$COLD_METADATA" ]; then
    sudo mkdir -p "$COLD_METADATA"
    sudo chown www-data:www-data "$COLD_METADATA"
  fi
  sudo chmod 777 "$COLD_METADATA"
  
  if [ ! -d "$COLD_AUDIO" ]; then
    sudo mkdir -p "$COLD_AUDIO"
    sudo chown www-data:www-data "$COLD_AUDIO"
  fi
  sudo chmod 775 "$COLD_AUDIO"
  
  echo "✓ Cold storage metadata & audio directories ready"
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

for i in {1..8}; do
  CAPTURE_FOLDER="capture$i"
  HOT_PATH="$BASE_PATH/$CAPTURE_FOLDER/hot"
  
  # Check if this device is in our active list
  if [[ ! " ${DEVICES[*]} " =~ " ${CAPTURE_FOLDER} " ]]; then
    # Device not in .env, check if it's mounted or in fstab
    if mount | grep -q "$HOT_PATH"; then
      echo "Unmounting unused device: $CAPTURE_FOLDER"
      sudo umount "$HOT_PATH" 2>/dev/null || echo "  ⚠️  Could not unmount $HOT_PATH"
    fi
    
    # Remove from fstab if present
    if grep -q "$HOT_PATH" /etc/fstab 2>/dev/null; then
      echo "Removing $CAPTURE_FOLDER from /etc/fstab..."
      sudo cp /etc/fstab "$FSTAB_BACKUP.cleanup"
      sudo grep -v "$HOT_PATH" /etc/fstab | sudo tee /etc/fstab.tmp > /dev/null
      sudo mv /etc/fstab.tmp /etc/fstab
      echo "  ✓ Removed from /etc/fstab"
    fi
  fi
done

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
echo "   • Owner: www-data:www-data (mode: 775)"
echo "   • Group members can read/write (nginx + capture services)"
echo "   • Auto-mount configured in /etc/fstab"
echo "   • Will automatically remount on reboot"
echo ""
echo "💡 To add/remove devices:"
echo "   1. Edit $ENV_FILE"
echo "   2. Add/remove DEVICE{N}_VIDEO_CAPTURE_PATH entries"
echo "   3. Re-run this script to apply changes"
echo ""
echo "⚠️  NOTE: If you just added $CURRENT_USER to www-data group,"
echo "   you may need to log out and back in for changes to take effect"
echo ""
