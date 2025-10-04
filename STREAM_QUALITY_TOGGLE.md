# Stream Quality Toggle - Implementation Complete ✅

## Overview
Per-device stream quality toggle (SD/HD) with zero code duplication.

## Usage

### Command Line
```bash
# Start all devices (systemd service)
./run_ffmpeg_and_rename_local.sh

# Restart specific device with quality
./run_ffmpeg_and_rename_local.sh device1 hd
./run_ffmpeg_and_rename_local.sh host sd
```

### API
```bash
# Restart device with HD quality
curl -X POST http://host/host/system/restartHostStreamService \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device1", "quality": "hd"}'
```

### Frontend (Ready for Integration)
```typescript
// Call from modal
await fetch(buildServerUrl('/server/system/restartHostStreamService'), {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    host_name: host.host_name,
    device_id: device_id,
    quality: 'hd' // or 'sd'
  })
});
```

## Quality Specifications

| Type | Quality | Resolution | Bitrate | RAM per Device |
|------|---------|------------|---------|----------------|
| HDMI | SD | 640x360 | 350k | ~500KB |
| HDMI | HD | 1280x720 | 1500k | ~1.87MB |
| VNC | SD | 480x360 | 250k | ~350KB |
| VNC | HD | 1280x720 | 1000k | ~1.25MB |

**RAM Impact:**
- Typical: 1 HD + 4 SD = ~4MB (4% of 100MB) ✅
- Worst: 5 HD = ~10MB (10% of 100MB) ✅

## Architecture

### Single Script Design
- `run_ffmpeg_and_rename_local.sh` handles both modes
- No code duplication
- Quality logic in one place

### Process Targeting
- Uses `/tmp/active_captures.conf` with CSV format
- Single file stores: capture_dir, PID, quality
- Only kills specific device's ffmpeg process

**Format:**
```csv
/var/www/html/stream/capture1,12345,sd
/var/www/html/stream/capture4,12346,hd
/var/www/html/stream/capture2,12347,sd
/var/www/html/stream/capture3,12348,sd
```

### Quality Detection
```bash
get_device_info() {
  # Parses CSV line for capture_dir
  # Returns field: 'pid' or 'quality'
}

get_device_quality() {
  # 1. Use parameter if in single device mode
  # 2. Read quality from active_captures.conf
  # 3. Default to 'sd'
}
```

## Files Modified

### Backend Scripts
- `backend_host/scripts/run_ffmpeg_and_rename_local.sh`
  - Added argument parsing for device_id and quality
  - Added get_device_quality() function
  - Modified GRABBERS filtering for single device mode
  - Modified kill logic to target specific device
  - Modified start_grabber() to use quality variables
  - Added PID and quality persistence

### Backend Controllers
- `backend_host/src/controllers/audiovideo/hdmi_stream.py`
  - Updated restart_stream() to accept quality parameter
  - Calls script with device_id and quality
  - Uses relative path (no hardcoded home directory)

- `backend_host/src/controllers/audiovideo/vnc_stream.py`
  - Updated restart_stream() to accept quality parameter
  - Calls script with device_id and quality
  - Uses relative path (no hardcoded home directory)

### Backend Routes
- `backend_host/src/routes/host_system_routes.py`
  - Updated restartHostStreamService to accept quality
  - Passes quality to av_controller.restart_stream()

- `backend_server/src/routes/server_system_routes.py`
  - No changes needed (auto-passes request body)

### Shared Utilities (CSV Format)
- `shared/src/lib/utils/storage_path_utils.py`
  - **NEW**: `parse_active_captures_conf()` - centralized CSV parser
  - Returns structured data: `[{'directory': '...', 'pid': '...', 'quality': '...'}]`
  - Updated `get_capture_base_directories()` to use centralized parser
  - Removed auto-discover fallback (clean, no legacy)

- `backend_host/src/services/disk_usage_service.py`
  - Updated `get_config_status()` to use centralized `parse_active_captures_conf()`
  - No duplicate parsing logic

- `backend_host/scripts/hot_cold_archiver.py`
  - No changes (uses `get_capture_base_directories()`)

- `backend_host/src/services/navigation/navigation_executor.py`
  - ✅ UPDATED: Now uses `get_capture_base_directories()` + `get_capture_storage_path()` (hot/cold aware)

## Testing

### Test SD/HD Toggle
```bash
# 1. Start all devices (default SD)
sudo systemctl restart stream

# 2. Switch device1 to HD
./run_ffmpeg_and_rename_local.sh device1 hd

# 3. Verify bitrate increased
tail -f /tmp/ffmpeg_output_device1.log

# 4. Switch back to SD
./run_ffmpeg_and_rename_local.sh device1 sd

# 5. Check other devices still running
ps aux | grep ffmpeg
```

### Verify Quality Files
```bash
# Check active captures with CSV format
cat /tmp/active_captures.conf
# Output example:
# /var/www/html/stream/capture1,12345,sd
# /var/www/html/stream/capture4,12346,hd

# Parse and display nicely
while IFS=',' read -r dir pid quality; do
  echo "=== $dir ==="
  echo "  PID: $pid"
  echo "  Quality: $quality"
  echo "  Running: $(ps -p $pid > /dev/null && echo "YES" || echo "NO")"
done < /tmp/active_captures.conf
```

## Design Principles Applied ✅

1. **No Legacy Code** - Clean implementation only
2. **No Verbose** - Minimal output
3. **No Backward Compatibility** - Single approach
4. **Simple & Clean** - One script, clear logic
5. **Per-Device Targeting** - Zero disruption to other devices
6. **Reuse Existing Structure** - Uses capture directories, no new config files

## Next Steps

Frontend integration:
1. Add quality state in RecHostStreamModal
2. Add SD/HD toggle button
3. Call API on toggle
4. Reset to SD on modal close

