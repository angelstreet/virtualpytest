#!/bin/bash
# Setup RAM-based hot storage - CLEAN IMPLEMENTATION
# Auto-configures /etc/fstab for automatic remount on reboot

set -e

MOUNT_SIZE="100M"
BASE_PATH="/var/www/html/stream"
DEVICES=("capture1" "capture2" "capture3" "capture4")
FSTAB_BACKUP="/etc/fstab.backup.$(date +%Y%m%d_%H%M%S)"

echo "================================"
echo "RAM Hot Storage Setup (Auto-mount)"
echo "================================"

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
  # These inherit www-data:www-data ownership from parent mount
  mkdir -p "$HOT_PATH/captures"
  mkdir -p "$HOT_PATH/thumbnails"
  mkdir -p "$HOT_PATH/segments"
  mkdir -p "$HOT_PATH/metadata"
  
  # Set group write permissions on subdirectories
  chmod 775 "$HOT_PATH"/*
  
  echo "✓ $DEVICE hot storage ready (www-data:www-data, group writable)"
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

# Show mounted RAM disks
echo ""
echo "================================"
echo "Mounted RAM disks:"
df -h | grep -E "hot|Filesystem"
echo "================================"

echo ""
echo "✅ RAM hot storage setup complete!"
echo "   • All devices mounted in RAM ($MOUNT_SIZE each)"
echo "   • Owner: www-data:www-data (mode: 775)"
echo "   • Group members can read/write (nginx + capture services)"
echo "   • Auto-mount configured in /etc/fstab"
echo "   • Will automatically remount on reboot"
echo ""
echo "⚠️  NOTE: If you just added $CURRENT_USER to www-data group,"
echo "   you may need to log out and back in for changes to take effect"
echo ""
