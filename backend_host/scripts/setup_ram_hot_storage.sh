#!/bin/bash
# Setup RAM-based hot storage for all capture devices
# NO LEGACY CODE - Pure RAM implementation

set -e

MOUNT_SIZE="100M"
BASE_PATH="/var/www/html/stream"
DEVICES=("capture1" "capture2" "capture3" "capture4")

echo "================================"
echo "RAM Hot Storage Setup"
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
    # Mount tmpfs
    echo "Mounting tmpfs ($MOUNT_SIZE) at $HOT_PATH"
    sudo mount -t tmpfs -o size=$MOUNT_SIZE,noexec,nodev,nosuid,uid=$(id -u),gid=$(id -g) tmpfs "$HOT_PATH"
    echo "✓ Mounted"
  fi
  
  # Create subdirectories (as current user, not sudo)
  mkdir -p "$HOT_PATH/captures"
  mkdir -p "$HOT_PATH/thumbnails"
  mkdir -p "$HOT_PATH/segments"
  
  # Create archive directories on SD card
  for hour in {0..23}; do
    sudo mkdir -p "$BASE_PATH/$DEVICE/captures/$hour"
    sudo mkdir -p "$BASE_PATH/$DEVICE/thumbnails/$hour"
    sudo mkdir -p "$BASE_PATH/$DEVICE/metadata/$hour"
    sudo mkdir -p "$BASE_PATH/$DEVICE/segments/$hour"
  done
  
  # Set ownership
  sudo chown -R $(id -u):$(id -g) "$BASE_PATH/$DEVICE"
  
  echo "✓ $DEVICE hot storage ready (RAM + SD archive)"
  echo ""
done

# Show mounted RAM disks
echo "================================"
echo "Mounted RAM disks:"
df -h | grep -E "hot|Filesystem" || echo "No hot mounts found"
echo "================================"

# Check if we should add to /etc/fstab
echo ""
echo "💡 To make RAM mounts persistent across reboots:"
echo ""
echo "Add these lines to /etc/fstab:"
echo "---"
for DEVICE in "${DEVICES[@]}"; do
  echo "tmpfs $BASE_PATH/$DEVICE/hot tmpfs size=$MOUNT_SIZE,noexec,nodev,nosuid,uid=$(id -u),gid=$(id -g) 0 0"
done
echo "---"
echo ""
echo "Run: sudo nano /etc/fstab"
echo "Then: sudo mount -a  # to test"
echo ""
echo "⚠️  Note: This is optional. RAM mounts will be recreated on each reboot"
echo "by the install_host_services.sh script if not in fstab."
echo ""
echo "✅ RAM hot storage setup complete!"

