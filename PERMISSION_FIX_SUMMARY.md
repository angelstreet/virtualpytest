✅ PERMISSION FIXES COMPLETED
==============================

Updated Files:
1. setup_ram_hot_storage.sh - Creates all directories with 777 permissions
2. setup_permissions.sh - Emergency fix script for existing systems

What setup_ram_hot_storage.sh now does:
=========================================

HOT STORAGE (RAM):
- Creates: /hot/captures, /hot/thumbnails, /hot/segments, /hot/metadata, /hot/audio
- Sets ALL to 777 permissions
- Owner: www-data:www-data

COLD STORAGE (SD):
- Creates: /captures, /segments, /metadata, /audio (root directories)
- Creates: /segments/0 through /segments/23 (24 hour folders)
- Creates: /segments/temp (for MP4 merging)
- Sets ALL to 777 permissions
- Owner: www-data:www-data

Why 777?
========
Multiple services with DIFFERENT users need to write/delete files:
- FFmpeg capture process (writes captures/segments)
- hot_cold_archiver service (deletes/moves files)
- capture_monitor service (writes metadata)
- nginx/www-data (serves files)

Without 777: Permission Denied errors!

Usage on Raspberry Pi:
======================

OPTION 1 - Fresh setup (creates everything):
  bash ~/virtualpytest/backend_host/scripts/setup_ram_hot_storage.sh

OPTION 2 - Fix existing system (permissions only):
  bash ~/virtualpytest/backend_host/scripts/setup_permissions.sh

Then restart services:
  sudo systemctl restart hot_cold_archiver.service
  sudo systemctl restart capture_monitor.service

Verify no more permission errors:
  journalctl -u hot_cold_archiver.service -f | grep "Permission denied"
  # Should see nothing!
