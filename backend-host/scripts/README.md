# Backend-Host Scripts

Core scripts for hardware monitoring, capture processing, and alert management on Raspberry Pi and other host devices.

## 🔧 **Core Python Scripts**

### `capture_monitor.py` 
**Main capture monitoring service** that watches capture directories and triggers analysis.

```bash
# Run capture monitor service
python capture_monitor.py
```

**Features:**
- Monitors multiple capture directories (`/var/www/html/stream/capture*/captures/`)
- Processes new images for analysis
- Manages incident state in memory
- Coordinates with alert system
- Logs to `/tmp/capture_monitor.log`

**Environment:**
- Requires virtual environment with OpenCV, numpy
- Reads `USER` environment variable for host identification
- Uses `/tmp/capture_monitor.log` for logging

### `alert_system.py`
**Alert processing and database integration** for incident management.

```bash
# Import in other scripts
from alert_system import process_alert_directly, process_alert_with_memory_state
```

**Features:**
- Local state management with `incidents.json` files
- Database integration for alert creation/resolution
- R2 cloud storage for incident frames
- Memory-based incident processing
- Support for blackscreen, freeze, and audio loss incidents

**Incident Types:**
- `blackscreen` - Video signal completely black
- `freeze` - Video frozen (identical frames)
- `audio_loss` - No audio detected

### `analyze_audio_video.py`
**Unified analysis engine** for processing captured frames and audio.

```bash
# Analyze single frame
python analyze_audio_video.py /path/to/capture_20240115120000.jpg [host_name] [device_id] [incident_state_json]
```

**Features:**
- **Video Analysis**: Blackscreen detection, freeze detection
- **Audio Analysis**: Volume measurement, audio presence detection
- **Optimized Processing**: Uses thumbnails for performance
- **Frame Caching**: Pickle-based caching for freeze detection
- **JSON Output**: Structured analysis results

**Analysis Output:**
```json
{
  "timestamp": "2024-01-15T12:00:00",
  "blackscreen": false,
  "blackscreen_percentage": 2.1,
  "freeze": true,
  "freeze_diffs": [0.2, 0.3, 0.1],
  "audio": true,
  "volume_percentage": 45,
  "mean_volume_db": -18.5
}
```

## 🎬 **Capture Management Scripts**

### `rename_captures.sh`
**File renaming service** that converts test captures to timestamped files.

```bash
# Run rename monitoring (typically as background service)
./rename_captures.sh
```

**Process:**
1. Watches `test_capture_*.jpg` files via `inotifywait`
2. Renames to `capture_YYYYMMDDHHMMSS.jpg` with current timestamp
3. Creates thumbnails using ImageMagick `convert`
4. Logs activity to `/tmp/rename.log`

**Dependencies:**
- `inotifywait` (inotify-tools package)
- `convert` (ImageMagick)

### `clean_captures.sh`
**Cleanup service** that removes old capture files to prevent disk full.

```bash
# Run cleanup (typically in cron or loop)
./clean_captures.sh
```

**Cleanup Rules:**
- Files older than 10 minutes are deleted
- Cleans both parent directory (`segment_*.ts`) and captures directory
- Preserves `.m3u8` playlist files
- Logs to `/tmp/clean.log`

## 🎥 **FFmpeg Capture Scripts**

### `run_ffmpeg_and_rename_rpi*.sh`
**Device-specific capture configurations** for different Raspberry Pi setups.

```bash
# Run RPi1 capture (device0 + audio input 2,0)
./run_ffmpeg_and_rename_rpi1.sh

# Run RPi2 capture  
./run_ffmpeg_and_rename_rpi2.sh

# Run RPi3 capture
./run_ffmpeg_and_rename_rpi3.sh
```

**Configuration Format:**
```bash
declare -A GRABBERS=(
  ["0"]="/dev/video0|plughw:2,0|/var/www/html/stream/capture1|10"
)
# Format: video_device|audio_device|capture_dir|fps
```

**Features:**
- **Dual Output**: HLS streaming + MJPEG image capture
- **Hardware Encoding**: Uses `h264_v4l2m2m` when available
- **Process Management**: Kills existing processes, starts monitoring
- **Logging**: Separate logs per device in `/tmp/ffmpeg_output_*.log`

**Output Streams:**
- **HLS**: `output.m3u8` + `segment_*.ts` files for live streaming
- **Images**: `test_capture_*.jpg` files for analysis (renamed by `rename_captures.sh`)

## 🚀 **Usage Patterns**

### Manual Testing
```bash
# Test single frame analysis
cd backend-host/scripts
python analyze_audio_video.py /var/www/html/stream/capture1/captures/capture_20240115120000.jpg sunri-pi2 device1

# Test capture monitoring  
python capture_monitor.py

# Test file processing
echo "test_capture_123456.jpg created" > /var/www/html/stream/capture1/captures/test_capture_123456.jpg
# Watch rename_captures.sh process it
```

### Service Integration
```bash
# Typical host startup sequence:
1. ./run_ffmpeg_and_rename_rpi1.sh &     # Start video capture
2. ./rename_captures.sh &                # Start file processing  
3. python capture_monitor.py &           # Start monitoring
4. ./clean_captures.sh &                 # Start cleanup (loop)
```

### Systemd Integration
```bash
# Use with systemd service
ExecStart=/home/pi/virtualpytest/backend-host/scripts/run_ffmpeg_and_rename_rpi1.sh
```

## 🔧 **Configuration**

### Environment Variables
```bash
# In backend-host/.env
HOST_NAME=sunri-pi2
HOST_PORT=6109
DEBUG=false

# System environment
USER=pi                    # Used by capture_monitor.py
TZ="Europe/Zurich"        # Used by rename_captures.sh
```

### Hardware Requirements
- **Video Capture**: USB capture device (`/dev/video0`)
- **Audio Capture**: USB audio interface (`plughw:2,0`)
- **Storage**: Fast SD card or SSD for captures
- **Network**: Stable connection for streaming

### Dependencies
```bash
# System packages
sudo apt install ffmpeg inotify-tools imagemagick

# Python packages (in virtual environment)
pip install opencv-python numpy pytesseract python-dotenv
```

## 📊 **Monitoring & Logs**

### Log Files
- `/tmp/capture_monitor.log` - Capture monitoring activity
- `/tmp/alerts.log` - Alert processing and database operations
- `/tmp/analysis.log` - Frame analysis results
- `/tmp/rename.log` - File renaming activity
- `/tmp/clean.log` - Cleanup operations
- `/tmp/ffmpeg_output_*.log` - FFmpeg capture logs

### Health Monitoring
```bash
# Check if services are running
ps aux | grep capture_monitor
ps aux | grep ffmpeg
ps aux | grep rename_captures

# Check recent activity
tail -f /tmp/capture_monitor.log
tail -f /tmp/alerts.log

# Check disk usage
df -h /var/www/html/stream/
```

## 🔧 **Troubleshooting**

### Common Issues

#### No Video Capture
```bash
# Check video device
ls -la /dev/video*
v4l2-ctl --list-devices

# Test video device
ffmpeg -f v4l2 -list_formats all -i /dev/video0
```

#### Audio Issues
```bash
# Check audio devices
arecord -l
aplay -l

# Test audio capture
arecord -D plughw:2,0 -f cd test.wav
```

#### Permission Issues
```bash
# Add user to video/audio groups
sudo usermod -a -G video,audio $USER

# Check device permissions
ls -la /dev/video* /dev/snd/*
```

#### Storage Issues
```bash
# Check disk space
df -h

# Manual cleanup
find /var/www/html/stream/*/captures -type f -mmin +10 -delete
```

### Script Debugging
```bash
# Enable debug logging
export DEBUG=true

# Test individual components
python analyze_audio_video.py --help
./rename_captures.sh --dry-run  # If supported
```

## 🤝 **Contributing**

1. **Adding New Analysis**: Extend `analyze_audio_video.py`
2. **New Hardware Support**: Copy and modify RPi scripts
3. **Alert Types**: Add to `alert_system.py`
4. **Monitoring Features**: Extend `capture_monitor.py`

## 📋 **Script Dependencies**

| Script | Python Deps | System Deps | Purpose |
|--------|-------------|-------------|---------|
| `capture_monitor.py` | `time`, `threading`, `glob` | None | Service coordination |
| `alert_system.py` | `json`, `datetime`, `dotenv` | None | Alert processing |
| `analyze_audio_video.py` | `cv2`, `numpy`, `pytesseract` | `ffmpeg` | Analysis engine |
| `rename_captures.sh` | None | `inotifywait`, `convert` | File processing |
| `run_ffmpeg_*.sh` | None | `ffmpeg`, `v4l2` | Video capture |
| `clean_captures.sh` | None | `find` | Cleanup | 