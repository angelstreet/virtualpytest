# UPDATE setup_ram_hot_storage.sh to use 777 permissions

## Changes to make in `backend_host/scripts/setup_ram_hot_storage.sh`:

### 1. Replace lines 122-130:

**FIND:**
```bash
  # Fix ownership and permissions (www-data:www-data, group writable)
  sudo chown -R www-data:www-data "$HOT_PATH"
  sudo chmod 775 "$HOT_PATH"
  sudo chmod 775 "$HOT_PATH"/*
  
  # CRITICAL: metadata directory needs 777 for archiver to move files (different user)
  sudo chmod 777 "$HOT_PATH/metadata"
  
  echo "✓ $DEVICE hot storage ready (www-data:www-data, group writable)"
```

**REPLACE WITH:**
```bash
  # Fix ownership (www-data:www-data)
  sudo chown -R www-data:www-data "$HOT_PATH"
  
  # CRITICAL: ALL subdirectories need 777 for cross-service access
  # Multiple services with different users need to write/delete files:
  # - FFmpeg capture process
  # - hot_cold_archiver service
  # - capture_monitor service
  sudo chmod 777 "$HOT_PATH"
  sudo chmod 777 "$HOT_PATH/captures"
  sudo chmod 777 "$HOT_PATH/thumbnails"
  sudo chmod 777 "$HOT_PATH/segments"
  sudo chmod 777 "$HOT_PATH/metadata"
  sudo chmod 777 "$HOT_PATH/audio"
  
  echo "✓ $DEVICE hot storage ready (www-data:www-data, all dirs 777)"
```

---

### 2. Replace lines 132-149:

**FIND:**
```bash
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
```

**REPLACE WITH:**
```bash
  # Also ensure cold storage directories exist with correct permissions (777 for cross-service access)
  COLD_CAPTURES="$BASE_PATH/$DEVICE/captures"
  COLD_SEGMENTS="$BASE_PATH/$DEVICE/segments"
  COLD_METADATA="$BASE_PATH/$DEVICE/metadata"
  COLD_AUDIO="$BASE_PATH/$DEVICE/audio"
  
  # Create all cold storage directories if they don't exist
  for COLD_DIR in "$COLD_CAPTURES" "$COLD_SEGMENTS" "$COLD_METADATA" "$COLD_AUDIO"; do
    if [ ! -d "$COLD_DIR" ]; then
      sudo mkdir -p "$COLD_DIR"
      sudo chown www-data:www-data "$COLD_DIR"
    fi
    sudo chmod 777 "$COLD_DIR"
  done
  
  # Also ensure hour folders in segments have 777 permissions
  for hour in {0..23}; do
    HOUR_DIR="$COLD_SEGMENTS/$hour"
    if [ ! -d "$HOUR_DIR" ]; then
      sudo mkdir -p "$HOUR_DIR"
      sudo chown www-data:www-data "$HOUR_DIR"
    fi
    sudo chmod 777 "$HOUR_DIR"
  done
  
  # Ensure temp directory exists for MP4 merging
  TEMP_DIR="$COLD_SEGMENTS/temp"
  if [ ! -d "$TEMP_DIR" ]; then
    sudo mkdir -p "$TEMP_DIR"
    sudo chown www-data:www-data "$TEMP_DIR"
  fi
  sudo chmod 777 "$TEMP_DIR"
  
  echo "✓ Cold storage directories ready (all 777)"
  echo ""
```

---

### 3. Replace lines 237-243:

**FIND:**
```bash
echo "✅ RAM hot storage setup complete!"
echo "   • Devices configured: ${#DEVICES[@]} (${DEVICES[*]})"
echo "   • Each device mounted in RAM ($MOUNT_SIZE)"
echo "   • Owner: www-data:www-data (mode: 775)"
echo "   • Group members can read/write (nginx + capture services)"
echo "   • Auto-mount configured in /etc/fstab"
echo "   • Will automatically remount on reboot"
```

**REPLACE WITH:**
```bash
echo "✅ RAM hot storage setup complete!"
echo "   • Devices configured: ${#DEVICES[@]} (${DEVICES[*]})"
echo "   • Each device mounted in RAM ($MOUNT_SIZE)"
echo "   • Owner: www-data:www-data"
echo "   • All subdirectories: 777 (full cross-service access)"
echo "   • Auto-mount configured in /etc/fstab"
echo "   • Will automatically remount on reboot"
```

---

## IMMEDIATE FIX (No waiting for setup script update):

Just run the updated **fix_metadata_permissions.sh** script - it fixes ALL directories to 777:

```bash
# On Raspberry Pi:
bash backend_host/scripts/fix_metadata_permissions.sh

# Then restart archiver:
sudo systemctl restart hot_cold_archiver.service

# Verify no more permission errors:
journalctl -u hot_cold_archiver.service -f | grep -i "permission denied"
# Should see nothing!
```

This fixes the issue immediately. The setup_ram_hot_storage.sh changes are just for next time you set up a new device.

