# Service Restart Cascade Configuration

## Overview
All dependent services now automatically restart when `stream.service` is restarted.

## Configuration Applied

### Service Dependencies
All processing services now include:
```ini
[Unit]
After=network.target stream.service
PartOf=stream.service
ExecStartPre=/bin/sleep 10
```

### Affected Services
1. **monitor.service** - Capture monitoring and incident detection
2. **hot_cold_archiver.service** - RAM/SD storage archiver
3. **transcript-stream.service** - Audio transcription accumulator
4. **heatmap_processor.service** - Heatmap generation

## How It Works

### `After=stream.service`
- Ensures service starts **after** stream service
- Prevents race conditions on startup

### `PartOf=stream.service`
- **Automatic restart**: When stream restarts, all dependent services restart
- **Automatic stop**: When stream stops, all dependent services stop
- **Cascading behavior**: Single command affects entire stack

### `ExecStartPre=/bin/sleep 10`
- Waits 10 seconds before starting service
- Allows FFmpeg processes to create directory structure
- Ensures `/tmp/active_captures.conf` is populated
- Fixes "Found 0 capture directories" issue

## Usage

### Restart Everything
```bash
sudo systemctl restart stream
```

This single command will:
1. Stop stream service (kills all FFmpeg processes)
2. Stop all dependent services (monitor, archiver, transcript, heatmap)
3. Start stream service (launches FFmpeg for all captures)
4. Wait 10 seconds
5. Start all dependent services (they detect all 6 captures)

### Check Status
```bash
systemctl status monitor hot_cold_archiver transcript-stream heatmap_processor
```

### View Logs
```bash
tail -f /tmp/capture_monitor.log
tail -f /tmp/hot_cold_archiver.log
tail -f /tmp/transcript_accumulator.log
```

## Verified Behavior

### Test Results (sunri-pi4)
Before restart:
- monitor: PID 353280
- hot_cold_archiver: PID 352390
- heatmap_processor: PID 352702

After `sudo systemctl restart stream`:
- monitor: PID 357066 ✅ (restarted)
- hot_cold_archiver: PID 357065 ✅ (restarted)
- heatmap_processor: PID 357064 ✅ (restarted)

Monitor log shows:
```
✅ Loaded 6 capture directories from active_captures.conf
Found 6 capture directories
Monitoring [HOT (RAM)]: /var/www/html/stream/capture1/hot/captures -> hot
Monitoring [HOT (RAM)]: /var/www/html/stream/capture2/hot/captures -> hot
Monitoring [HOT (RAM)]: /var/www/html/stream/capture3/hot/captures -> hot
Monitoring [HOT (RAM)]: /var/www/html/stream/capture4/hot/captures -> hot
Monitoring [HOT (RAM)]: /var/www/html/stream/capture5/hot/captures -> hot
Monitoring [HOT (RAM)]: /var/www/html/stream/capture6/hot/captures -> hot
```

## Benefits

1. **Simplified Operations**: One command restarts entire capture stack
2. **Consistency**: All services see same fresh state
3. **Race Condition Prevention**: 10s delay ensures directories exist
4. **Clean State**: Old PIDs/processes are properly terminated
5. **Automatic Recovery**: Services restart together on reboot

## Applied To
- ✅ sunri-pi4 (live system)
- ✅ Template service files in repo

## Files Modified
- `backend_host/config/services/monitor.service`
- `backend_host/config/services/hot_cold_archiver.service`
- `backend_host/config/services/transcript-stream.service`
- `/etc/systemd/system/monitor.service` (on pi4)
- `/etc/systemd/system/hot_cold_archiver.service` (on pi4)
- `/etc/systemd/system/transcript-stream.service` (on pi4)
- `/etc/systemd/system/heatmap_processor.service` (on pi4)

---
**Status**: ✅ Production-ready and tested on sunri-pi4
**Date**: 2025-10-05

## Deployment Status

### ✅ All Raspberry Pis Configured
Service restart cascade has been applied to all production systems:

| Pi | Port | Status | Services Modified |
|---|---|---|---|
| **sunri-pi1** | 221 | ✅ Complete | monitor, hot_cold_archiver, transcript-stream, heatmap_processor |
| **sunri-pi2** | 222 | ✅ Complete | monitor, hot_cold_archiver, transcript-stream |
| **sunri-pi3** | 223 | ✅ Complete | monitor, hot_cold_archiver, transcript-stream |
| **sunri-pi4** | 224 | ✅ Complete | monitor, hot_cold_archiver, transcript-stream, heatmap_processor |

### Service Configuration Applied to All Pis
```ini
[Unit]
After=network.target stream.service
PartOf=stream.service
ExecStartPre=/bin/sleep 10
```

### Usage on Any Pi
```bash
# Restart entire capture stack on any Pi
sudo systemctl restart stream

# This automatically restarts:
# - monitor.service (incident detection)
# - hot_cold_archiver.service (RAM/SD archiving)
# - transcript-stream.service (audio transcription)
# - heatmap_processor.service (on pi1 & pi4 only)
```

### Notes
- **pi2 and pi3** do not have heatmap_processor service (expected)
- **All Pis** now have 10s startup delay to ensure directories are created
- **All Pis** will automatically restart dependent services when stream restarts
- **All Pis** use the new hot/cold storage architecture

