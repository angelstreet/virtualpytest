#!/bin/bash
# Setup RAM-based hot storage - CLEAN IMPLEMENTATION
# Only creates and mounts RAM, no migration

set -e

MOUNT_SIZE="100M"
BASE_PATH="/var/www/html/stream"
DEVICES=("capture1" "capture2" "capture3" "capture4")

echo "================================"
echo "RAM Hot Storage Setup (Fresh)"
echo "================================"

# Check if we have sudo access
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  This script requires sudo access to mount tmpfs"
    echo "Please run with sudo or enter password when prompted"
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
    # Mount tmpfs with ownership set at mount time
    echo "Mounting tmpfs ($MOUNT_SIZE) at $HOT_PATH"
    sudo mount -t tmpfs -o size=$MOUNT_SIZE,noexec,nodev,nosuid,uid=$(id -u),gid=$(id -g) tmpfs "$HOT_PATH"
    echo "✓ Mounted"
  fi
  
  # Create subdirectories in RAM (instant, no SD card I/O)
  mkdir -p "$HOT_PATH/captures"
  mkdir -p "$HOT_PATH/thumbnails"
  mkdir -p "$HOT_PATH/segments"
  
  echo "✓ $DEVICE hot storage ready"
  echo ""
done

# Show mounted RAM disks
echo "================================"
echo "Mounted RAM disks:"
df -h | grep -E "hot|Filesystem" || echo "No hot mounts found"
echo "================================"

echo ""
echo "✅ RAM hot storage setup complete!"
echo ""
echo "💡 Optional: To make persistent across reboots, add to /etc/fstab:"
for DEVICE in "${DEVICES[@]}"; do
  echo "tmpfs $BASE_PATH/$DEVICE/hot tmpfs size=$MOUNT_SIZE,noexec,nodev,nosuid,uid=$(id -u),gid=$(id -g) 0 0"
done
echo ""
