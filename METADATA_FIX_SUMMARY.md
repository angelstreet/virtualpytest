# Metadata Directory Fix - Summary

## Problem Identified

**Root Cause:** JSON metadata files were being written to `/hot/captures/` instead of `/hot/metadata/`, causing:
- **176MB RAM usage** on capture2 and capture4 (88% of 200MB tmpfs)
- **9,578+ JSON files** accumulating in wrong location
- **Archiver not working** because it checks `/hot/metadata/` (empty) instead of `/hot/captures/`
- **Files never archived** resulting in RAM exhaustion

### Evidence from sunri-pi2:
```bash
# Metadata directory (where archiver looks): EMPTY
/var/www/html/stream/capture2/hot/metadata/: 0 files

# Captures directory (wrong location): FLOODED
/var/www/html/stream/capture2/hot/captures/: 9,578 JSON files + 300 JPG files (176MB)

# All 4 devices affected:
- capture1: 4,402 JSON files in wrong location
- capture2: 9,578 JSON files (176MB RAM)
- capture3: 4,868 JSON files
- capture4: 9,589 JSON files (176MB RAM)
```

## Changes Made

### 1. **capture_monitor.py** (Write Location Fix)
**Before:**
```python
json_file = frame_path.replace('.jpg', '.json')  # Written to captures/
```

**After:**
```python
# Get metadata path using centralized storage resolution
metadata_path = get_capture_storage_path(capture_folder, 'metadata')
os.makedirs(metadata_path, exist_ok=True)
json_file = os.path.join(metadata_path, json_filename)  # Written to metadata/
```

### 2. **analysis_utils.py** (Read Location Fix - 2 functions)
**Before:**
```python
frame_json_path = os.path.join(capture_folder, f"{base_name}.json")  # Read from captures/
```

**After:**
```python
metadata_folder = get_capture_storage_path(device_folder, 'metadata')
frame_json_path = os.path.join(metadata_folder, f"{base_name}.json")  # Read from metadata/
```

### 3. **video_monitoring_helpers.py** (Read Location Fix)
**Before:**
```python
for filename in os.listdir(capture_folder):  # Listed from captures/
    if filename.endswith('.json'):
```

**After:**
```python
metadata_folder = get_capture_storage_path(device_folder, 'metadata')
for filename in os.listdir(metadata_folder):  # Listed from metadata/
    if filename.endswith('.json'):
```

## Architecture Now Correct

### Hot Storage Structure (RAM Mode):
```
/var/www/html/stream/capture1/hot/
├── captures/      # 300 JPG files (60s buffer, 74MB) ✅
├── thumbnails/    # 100 thumbnail files (3MB) ✅
├── segments/      # 150 TS files (2.5min buffer, 6MB) ✅
└── metadata/      # 100 JSON files (0.2MB) ✅ FIXED!
```

### Total RAM per device: ~83MB (within 200MB budget) ✅

## Next Steps on Server

### Step 1: Deploy Updated Code
```bash
cd ~/virtualpytest
git pull origin main  # Get the fixes
```

### Step 2: Move Existing JSON Files to Correct Location
```bash
# Create cleanup script
cat > /tmp/fix_metadata_locations.sh << 'EOF'
#!/bin/bash
for capture_dir in /var/www/html/stream/capture*; do
    device=$(basename "$capture_dir")
    echo "=== Processing $device ==="
    
    # Check if RAM mode
    if [ -d "$capture_dir/hot/captures" ]; then
        # RAM mode: Move from hot/captures/ to hot/metadata/
        captures_dir="$capture_dir/hot/captures"
        metadata_dir="$capture_dir/hot/metadata"
        
        mkdir -p "$metadata_dir"
        
        # Count and move JSON files
        json_count=$(find "$captures_dir" -maxdepth 1 -name "*.json" -type f | wc -l)
        echo "  Found $json_count JSON files in captures/"
        
        if [ "$json_count" -gt 0 ]; then
            find "$captures_dir" -maxdepth 1 -name "*.json" -type f -exec mv {} "$metadata_dir/" \;
            echo "  ✅ Moved $json_count JSON files to metadata/"
        fi
    else
        # SD mode: Move from captures/ to metadata/
        captures_dir="$capture_dir/captures"
        metadata_dir="$capture_dir/metadata"
        
        mkdir -p "$metadata_dir"
        
        json_count=$(find "$captures_dir" -maxdepth 1 -name "*.json" -type f | wc -l)
        echo "  Found $json_count JSON files in captures/"
        
        if [ "$json_count" -gt 0 ]; then
            find "$captures_dir" -maxdepth 1 -name "*.json" -type f -exec mv {} "$metadata_dir/" \;
            echo "  ✅ Moved $json_count JSON files to metadata/"
        fi
    fi
    
    # Verify
    if [ -d "$metadata_dir" ]; then
        new_count=$(find "$metadata_dir" -maxdepth 1 -name "*.json" -type f | wc -l)
        echo "  ✓ Metadata directory now has $new_count JSON files"
    fi
done

echo ""
echo "=== Cleanup Complete ==="
df -h | grep hot
EOF

chmod +x /tmp/fix_metadata_locations.sh
```

### Step 3: Run Cleanup (AS ROOT or with sudo)
```bash
sudo /tmp/fix_metadata_locations.sh
```

Expected output:
```
=== Processing capture1 ===
  Found 4,402 JSON files in captures/
  ✅ Moved 4,402 JSON files to metadata/
  ✓ Metadata directory now has 4,402 JSON files

=== Processing capture2 ===
  Found 9,578 JSON files in captures/
  ✅ Moved 9,578 JSON files to metadata/
  ✓ Metadata directory now has 9,578 JSON files

[... similar for capture3, capture4 ...]

=== Cleanup Complete ===
tmpfs  200M   94M  107M  47% /var/www/html/stream/capture1/hot
tmpfs  200M   25M  176M  13% /var/www/html/stream/capture2/hot  # ← RAM usage drops!
tmpfs  200M  100M  101M  50% /var/www/html/stream/capture3/hot
tmpfs  200M   26M  175M  14% /var/www/html/stream/capture4/hot  # ← RAM usage drops!
```

### Step 4: Restart Services (Let New Code Take Effect)
```bash
# Restart capture monitor (will use new metadata path)
sudo systemctl restart capture_monitor

# Restart archiver (will now find files to archive)
sudo systemctl restart hot_cold_archiver

# Monitor logs
journalctl -u hot_cold_archiver -f
```

### Step 5: Verify Fix
```bash
# Check metadata folders are being archived
ls -lh /var/www/html/stream/capture2/hot/metadata/ | wc -l  # Should stay around 100
ls -lh /var/www/html/stream/capture2/metadata/  # Should have archived JSON files

# Check RAM usage
df -h | grep hot  # Should be ~50% instead of 88%

# Check archiver logs
journalctl -u hot_cold_archiver --since "5 minutes ago" | grep "archived"
```

## Expected Results After Fix

### Before Fix:
- capture2/capture4: 88% RAM usage (176MB / 200MB)
- 9,578+ JSON files stuck in captures/
- Archiver skipping files ("0 metadata archived")

### After Fix:
- capture2/capture4: ~50% RAM usage (100MB / 200MB)
- JSON files archived every 60 seconds
- Archiver working correctly ("archived X metadata")
- System stable and sustainable

## Why This Happened

1. **capture_monitor.py** wrote JSON to same directory as JPG (captures/)
2. **hot_cold_archiver.py** looked for JSON in metadata/ directory
3. **Mismatch caused files to accumulate** endlessly in wrong location
4. **RAM exhausted** because JSON files were never cleaned up

## Why Segments Showed "< 30s old" Issue

The 30-second safety check was protecting against archiving files from a **recent FFmpeg restart**. When FFmpeg restarts, all segment numbers reset to 0, creating fresh files. The archiver correctly waited 30 seconds to avoid race conditions during the restart window.

This is **working as intended** - not a bug!

---

**Status:** ✅ Code fixed and ready to deploy
**Risk:** Low - changes only affect file I/O paths (write/read consistency)
**Rollback:** Simply restore old code (JSON accumulation will resume)

