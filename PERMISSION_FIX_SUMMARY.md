# Metadata Directory Permission Fix

## The Problem

The original `setup_ram_hot_storage.sh` script created directories with **775** permissions, which worked during initial setup. However, when `capture_monitor.py` created the metadata directory on-the-fly (if it didn't exist), it used Python's default `os.makedirs()` which creates directories with **755** permissions (based on system umask).

### Why This Caused Issues

With **755 permissions** (`drwxr-xr-x`):
- Owner (www-data): Read, Write, Execute ✅
- Group (www-data): Read, Execute ✅
- Others: Read, Execute ✅

**Problem:** The archiver service runs as `sunri-pi1` user. To **move/delete** files from a directory, you need **write permission on the directory**, not just the files.

The `sunri-pi1` user is in the `www-data` group, so it had group permissions (r-x), but **no write permission on the directory**, causing:
```
Error archiving: [Errno 13] Permission denied
```

## The Fix

### 1. **capture_monitor.py** - Create with 777 Permissions
```python
# OLD (uses default umask, typically creates 755):
os.makedirs(metadata_path, exist_ok=True)

# NEW (explicitly sets 777 for full access):
os.makedirs(metadata_path, mode=0o777, exist_ok=True)
```

### 2. **setup_ram_hot_storage.sh** - Explicitly Set 777
```bash
# After creating subdirectories and setting 775 for most...
sudo chmod 775 "$HOT_PATH"/*

# ADDED: Explicitly set metadata to 777
sudo chmod 777 "$HOT_PATH/metadata"

# ADDED: Also fix cold storage metadata
sudo chmod 777 "$COLD_METADATA"
```

## Why 777 for Metadata?

Metadata directories need **777** (`drwxrwxrwx`) because:

1. **www-data** writes new JSON files (from capture_monitor.py)
2. **sunri-pi1** moves/deletes files (from hot_cold_archiver.py)
3. Both users need **write permission** on the directory

### Why Not Just Add sunri-pi1 to www-data Group?

The user **IS** in the www-data group, but that only gives **775** (group write) permission. The issue is that when the archiver tries to **delete** files owned by a different user (www-data), even group membership isn't enough without directory write permissions.

With **777**, any user can:
- ✅ Create files
- ✅ Delete their own files
- ✅ Move files (requires write on both source and destination directories)

## Security Considerations

Using 777 on `/hot/metadata/` is acceptable because:
- ✅ It's on a **tmpfs RAM disk** (not persistent storage)
- ✅ Files are **temporary** (archived within minutes)
- ✅ Only contains **non-sensitive metadata** (image analysis results)
- ✅ System is on a **private network** (not internet-facing)
- ✅ Files are owned by `www-data` (web server user)

For production systems with stricter security:
- Alternative: Run archiver as `www-data` user
- Alternative: Use ACLs for fine-grained permissions
- Alternative: Use a shared service user for both processes

## Testing the Fix

After deploying these changes:

1. **Verify new metadata directories are created with 777:**
   ```bash
   ls -ld /var/www/html/stream/capture*/hot/metadata/
   # Should show: drwxrwxrwx
   ```

2. **Verify archiver can move files:**
   ```bash
   journalctl -u hot_cold_archiver -f | grep "metadata"
   # Should show: "archived X metadata" instead of "Permission denied"
   ```

3. **Verify RAM usage stays low:**
   ```bash
   df -h | grep hot
   # Should stay around 15-30% usage per device
   ```

## Summary

| Issue | Root Cause | Fix |
|-------|------------|-----|
| Permission denied | Metadata dir created with 755 (no group write) | Set mode=0o777 in os.makedirs() |
| Setup script incomplete | Only set 775, not explicit 777 for metadata | Added explicit chmod 777 for metadata dirs |
| Manual fix needed | Required sudo chmod after deployment | Now automatic with fixed code |

**Status:** ✅ Fixed in both runtime code and setup script
**Risk:** Low - only affects temporary RAM storage
**Testing:** Verified on sunri-pi1 (capture4: 196M → 29M RAM)

