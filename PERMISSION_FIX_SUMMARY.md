# ✅ PERMISSION FIXES - COMPLETE

## All Permissions Now Set to 777

### Files Updated:
1. **run_ffmpeg_and_rename_local.sh** - Creates `/tmp/active_captures.conf` with 777
2. **setup_ram_hot_storage.sh** - Creates all directories + fixes active_captures.conf to 777
3. **setup_permissions.sh** - Emergency fix for existing systems (all 777)

---

## What Gets 777 Permissions:

### Hot Storage (RAM):
- `/var/www/html/stream/capture*/hot/`
- `/var/www/html/stream/capture*/hot/captures/`
- `/var/www/html/stream/capture*/hot/thumbnails/`
- `/var/www/html/stream/capture*/hot/segments/`
- `/var/www/html/stream/capture*/hot/metadata/`
- `/var/www/html/stream/capture*/hot/audio/`

### Cold Storage (SD):
- `/var/www/html/stream/capture*/captures/`
- `/var/www/html/stream/capture*/segments/`
- `/var/www/html/stream/capture*/segments/0/` through `/segments/23/` (hour folders)
- `/var/www/html/stream/capture*/segments/temp/` (MP4 merging)
- `/var/www/html/stream/capture*/metadata/`
- `/var/www/html/stream/capture*/audio/`

### Config File:
- `/tmp/active_captures.conf` - **777** (critical for cross-service communication)

---

## Why 777?

Multiple services with **different users** need read/write/execute access:

| Service | User | Needs Access To |
|---------|------|-----------------|
| **FFmpeg capture** | (varies) | Write captures/segments/metadata |
| **hot_cold_archiver** | (varies) | Delete/move files between hot/cold |
| **capture_monitor** | (varies) | Write metadata JSON files |
| **nginx** | www-data | Serve files to web |
| **All services** | (all) | Read/write `/tmp/active_captures.conf` |

Without 777: **Permission Denied errors!**

---

## Usage on Raspberry Pi:

### Option 1: Full Setup (creates everything)
```bash
cd ~/virtualpytest/backend_host/scripts
bash setup_ram_hot_storage.sh
```

### Option 2: Fix Existing System (permissions only)
```bash
cd ~/virtualpytest/backend_host/scripts
bash setup_permissions.sh
```

### Restart Services:
```bash
sudo systemctl restart ffmpeg_capture.service
sudo systemctl restart hot_cold_archiver.service
sudo systemctl restart capture_monitor.service
```

### Verify No Errors:
```bash
# Check FFmpeg created config correctly
ls -la /tmp/active_captures.conf
# Should show: -rwxrwxrwx (777)

# Check capture directories exist
ls -ld /var/www/html/stream/capture*
# Should show: drwxrwxrwx (777) for all

# Check no permission errors
journalctl -u hot_cold_archiver.service -f | grep "Permission denied"
# Should see nothing!

journalctl -u capture_monitor.service -n 20
# Should see "Found N capture directories"
```

---

## Summary of Changes:

✅ **All storage directories:** 777  
✅ **All hour folders (0-23):** 777  
✅ **Temp directory:** 777  
✅ **/tmp/active_captures.conf:** 777  

**Result:** All services can now read/write/delete files regardless of which user created them!
