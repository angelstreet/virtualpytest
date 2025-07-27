# backend_host Examples

This directory contains example configuration files and scripts that you can copy and customize for your host setup.

## 📁 Directory Structure

```
backend_host/examples/
├── config/
│   └── host_config.example.json     # Example host configuration
├── scripts/
│   ├── manage_services.example.sh   # Example service manager
│   └── setup_host_environment.example.sh # Example environment setup
└── README.md                        # This file
```

## 🚀 Quick Setup

### 1. Copy Example Files

```bash
# Copy configuration template
cp backend_host/examples/config/host_config.example.json backend_host/config/host_config.json

# Copy management scripts
cp backend_host/examples/scripts/manage_services.example.sh backend_host/manage_services.sh
cp backend_host/examples/scripts/setup_host_environment.example.sh backend_host/setup_host_environment.sh

# Make scripts executable
chmod +x backend_host/manage_services.sh
chmod +x backend_host/setup_host_environment.sh
```

### 2. Customize Configuration

Edit `backend_host/config/host_config.json` to match your hardware:

```bash
nano backend_host/config/host_config.json
```

**Key settings to customize:**
- `host_name`: Your Raspberry Pi hostname
- `host_id`: Unique identifier (e.g., "rpi1", "rpi2")
- `video_device`: Your USB capture device (e.g., "/dev/video0")
- `audio_device`: Your audio input (e.g., "plughw:2,0")
- `capture_dir`: Where to store captures

### 3. Run Setup

```bash
# Setup system environment
./backend_host/setup_host_environment.sh

# Enable and start services
./backend_host/manage_services.sh enable
./backend_host/manage_services.sh start

# Check status
./backend_host/manage_services.sh status
```

## ⚙️ Configuration Reference

### Host Configuration (`host_config.json`)

```json
{
  "host_name": "raspberrypi",           // Hostname for identification
  "host_id": "rpi1",                    // Unique host ID
  "capture_devices": [                  // Array of capture devices
    {
      "device_id": "device1",           // Logical device ID
      "video_device": "/dev/video0",    // Video capture device
      "audio_device": "plughw:2,0",     // Audio capture device
      "capture_dir": "/var/www/html/stream/capture1",
      "fps": 10,                        // Capture frame rate
      "enabled": true                   // Enable this device
    }
  ],
  "monitoring": {
    "analysis_interval": 3,             // Analysis frequency (seconds)
    "cleanup_interval": 300,            // Cleanup frequency (seconds)
    "blackscreen_threshold": 10,        // Pixel intensity threshold
    "freeze_threshold": 0.5,            // Frame difference threshold
    "audio_threshold_percentage": 5     // Audio detection threshold
  }
}
```

### Device Detection

Find your hardware devices:

```bash
# List video devices
ls -la /dev/video*
v4l2-ctl --list-devices

# List audio devices  
arecord -l
aplay -l

# Test video capture
ffmpeg -f v4l2 -list_formats all -i /dev/video0

# Test audio capture
arecord -D plughw:2,0 -f cd test.wav
```

## 🛠️ Service Management

The `manage_services.sh` script provides easy control over all backend_host services:

```bash
# Service control
./backend_host/manage_services.sh start     # Start all services
./backend_host/manage_services.sh stop      # Stop all services  
./backend_host/manage_services.sh restart   # Restart all services
./backend_host/manage_services.sh status    # Show service status

# Auto-start configuration
./backend_host/manage_services.sh enable    # Enable auto-start on boot
./backend_host/manage_services.sh disable   # Disable auto-start

# Monitoring
./backend_host/manage_services.sh logs      # Show recent logs
./backend_host/manage_services.sh logs virtualpytest-capture-monitor  # Specific service logs
```

### Services Overview

| Service | Purpose | Script |
|---------|---------|---------|
| `virtualpytest-ffmpeg-capture` | Video/audio capture | `run_ffmpeg_and_rename_rpi1.sh` |
| `virtualpytest-rename-captures` | File processing | `rename_captures.sh` |
| `virtualpytest-capture-monitor` | Analysis & alerts | `capture_monitor.py` |
| `virtualpytest-cleanup.timer` | Cleanup (timer) | `clean_captures.sh` |

## 📊 Monitoring & Logs

### Log Files

- `/tmp/capture_monitor_service.log` - Capture monitoring
- `/tmp/ffmpeg_service.log` - Video capture
- `/tmp/rename_service.log` - File processing
- `/tmp/cleanup_service.log` - Cleanup operations

### Health Checks

```bash
# Check if services are running
systemctl status virtualpytest-*

# Check recent activity
tail -f /tmp/capture_monitor_service.log

# Check disk usage
df -h /var/www/html/stream/

# Check recent captures
ls -la /var/www/html/stream/capture1/captures/ | tail -10
```

## 🔧 Troubleshooting

### Common Issues

**No video capture:**
```bash
# Check video device permissions
ls -la /dev/video*

# Add user to video group
sudo usermod -a -G video $USER

# Reboot for group changes
sudo reboot
```

**Audio issues:**
```bash
# Check audio devices
arecord -l

# Test audio capture
arecord -D plughw:2,0 -f cd -d 5 test.wav
```

**Service won't start:**
```bash
# Check service logs
journalctl -u virtualpytest-capture-monitor -n 50

# Check dependencies
./backend_host/setup_host_environment.sh
```

**Disk space issues:**
```bash
# Manual cleanup
find /var/www/html/stream/*/captures -name "*.jpg" -mmin +10 -delete

# Check cleanup service
systemctl status virtualpytest-cleanup.timer
```

## 🔄 Updates

When you update VirtualPyTest, you may need to:

1. **Compare configurations**: Check if new options were added to the example config
2. **Update scripts**: Copy updated management scripts if needed
3. **Restart services**: `./backend_host/manage_services.sh restart`

```bash
# Compare your config with new example
diff backend_host/config/host_config.json backend_host/examples/config/host_config.example.json
``` 