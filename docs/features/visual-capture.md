# 📹 Visual Capture & Monitoring

**See everything. Miss nothing.**

Automatic video capture, live streaming, and screenshot generation for comprehensive visual testing and monitoring.

---

## The Problem

Testing without visual evidence is blind testing:
- ❌ "The test passed but the screen was black"
- ❌ "I can't reproduce what the tester saw"
- ❌ "The UI was broken but the test didn't catch it"
- ❌ "No evidence of what actually happened"

---

## The VirtualPyTest Solution

✅ **Live streaming** - Watch devices in real-time from anywhere  
✅ **Automatic screenshots** - Capture every test step  
✅ **Video replay** - Review test execution frame-by-frame  
✅ **Visual evidence** - Prove what happened with timestamped captures  

---

## Features

### 📺 Live Streaming

**Watch your devices in real-time through the web interface.**

#### HDMI Capture
- Capture video from any HDMI source
- Supported capture cards: USB HDMI, PCIe cards
- Real-time streaming to web browser
- Multiple devices simultaneously

#### VNC Streaming
- Desktop sharing for Android devices
- Remote view of virtual displays
- Built-in VNC server integration
- NoVNC web client (no plugins needed)

#### Network Cameras
- IP camera integration
- Physical device monitoring
- Multi-camera views
- Motion detection

**Use cases:**
- Monitor streaming quality 24/7
- Debug test failures visually
- Remote device observation
- Quality assurance validation

---

### 📸 Automatic Screenshots

**Every action captured automatically.**

#### Test Execution Screenshots
```python
# Automatic screenshots at each step
controller.navigate_to("settings")  # Screenshot: before_navigate.png
controller.press_key("DOWN")        # Screenshot: after_press_down.png
controller.verify_text("Audio")     # Screenshot: verification_result.png
```

#### Screenshot Timeline
- Before and after each action
- Timestamped file names
- Organized by test execution ID
- Easy navigation and review

#### Storage Options
- Local filesystem storage
- Cloudflare R2 cloud storage
- Configurable retention policies
- Automatic cleanup of old captures

---

### 🎬 Video Recording

**Record entire test sessions.**

#### Continuous Recording
- Always-on recording for monitoring
- Circular buffer (keeps last N hours)
- Triggered recording on events
- Export clips of interest

#### Test Session Recording
- Full video of test execution
- Synchronized with test logs
- Frame-accurate playback
- Shareable video reports

**Formats supported:**
- MP4 (web-friendly)
- MKV (high quality)
- HLS segments (live streaming)

---

## Setup Examples

### HDMI Capture Card Setup

```yaml
# Device configuration
device:
  name: "living_room_tv"
  video_capture:
    method: "hdmi"
    device: "/dev/video0"
    resolution: "1920x1080"
    fps: 30
    stream_path: "/stream/capture1"
```

### VNC Desktop Sharing

```yaml
# Android device with VNC
device:
  name: "android_tablet"
  video_capture:
    method: "vnc"
    vnc_port: 5900
    display: ":1"
    stream_url: "http://localhost:6080"
```

---

## Web Interface Integration

### Live View Dashboard

Access via **Rec** menu in web interface:

- Grid view of all devices
- Click to enlarge any stream
- Fullscreen mode
- Recording controls

### Screenshot Gallery

Browse captured screenshots:

- Filter by test execution
- Timeline view
- Compare screenshots
- Download or share

---

## Visual Testing Workflow

### 1. Run Test with Visual Capture

```python
# Visual capture happens automatically
result = run_test(
    test_case="netflix_playback",
    device="android_tv_1",
    capture_video=True  # Records entire session
)
```

### 2. Review Results

- View test report with embedded screenshots
- Play back video recording
- Compare expected vs. actual images
- Identify exactly when/where failure occurred

### 3. Debug Issues

- Screenshot timeline shows progression
- Video replay at normal or slow speed
- Jump to specific test steps
- Visual diff between attempts

---

## Advanced Features

### Frame Comparison

Automatically detect visual changes:

```python
# Compare frames for stability
detector.detect_freeze(
    video_stream="/dev/video0",
    threshold=0.95,  # 95% similarity = frozen
    duration=5       # Frozen for 5 seconds
)
```

### Black Screen Detection

Catch playback failures immediately:

```python
# Detect black screens
detector.detect_black_screen(
    video_stream="/dev/video0",
    threshold=10,    # Max brightness level
    min_duration=2   # Black for 2+ seconds = alert
)
```

### Subtitle Detection

Verify subtitles appear and are readable:

```python
# OCR on subtitle region
detector.detect_subtitle_text(
    region=(0, 800, 1920, 1080),  # Bottom of screen
    expected_text="Hello world"
)
```

---

## Storage Management

### Automatic Cleanup

```yaml
retention:
  screenshots:
    passed_tests: 7    # Keep for 7 days
    failed_tests: 30   # Keep for 30 days
    
  videos:
    continuous: 24     # Keep last 24 hours
    test_sessions: 14  # Keep for 14 days
```

### Cloud Storage

```yaml
storage:
  type: "cloudflare_r2"
  bucket: "virtualpytest-captures"
  public_url: "https://cdn.virtualpytest.com"
  
  # Automatic upload of screenshots
  auto_upload: true
  upload_failed_only: false
```

---

## Performance Optimization

### HLS Streaming

Low-latency live streaming:

```yaml
streaming:
  method: "hls"
  segment_duration: 2    # 2-second segments
  playlist_size: 5       # Keep 5 segments
  low_latency: true
```

### Hardware Encoding

Use GPU for efficient encoding:

```yaml
encoding:
  codec: "h264_nvenc"    # NVIDIA GPU encoding
  preset: "fast"
  bitrate: "2M"
  quality: "high"
```

---

## Integration with Tests

### Screenshot Verification

```python
# Capture and verify in one step
controller.verify_screen(
    reference_image="expected_home_screen.png",
    threshold=0.95,
    capture_on_fail=True  # Save screenshot if doesn't match
)
```

### Visual Test Reports

Test reports automatically include:
- Screenshot thumbnails
- Links to full-size images
- Video playback embed
- Visual diff comparisons

---

## Monitoring & Alerts

### Visual Quality Alerts

```yaml
alerts:
  - type: "black_screen"
    duration: 5
    action: "notify_slack"
    
  - type: "freeze_detected"
    duration: 10
    action: "restart_device"
    
  - type: "subtitle_missing"
    expected: "yes"
    action: "create_incident"
```

---

## Hardware Requirements

### For HDMI Capture

- HDMI capture card (USB or PCIe)
- Recommended: Elgato, AVerMedia, or generic USB 3.0 HDMI capture
- USB 3.0 port (for USB capture cards)
- Sufficient disk space or cloud storage

### For VNC Capture

- VNC server on Android device
- Network connectivity
- Minimal bandwidth (<1 Mbps per stream)

---

## Benefits

### 🔍 Complete Visibility
Never wonder what happened during a test. Full visual record of every action.

### 🐛 Faster Debugging
Screenshot timeline and video replay cut debugging time by 90%.

### 📊 Better Reporting
Visual evidence makes test reports meaningful to non-technical stakeholders.

### ⚡ Continuous Monitoring
24/7 streaming detects issues in real-time, not after the fact.

---

## Next Steps

- 📖 [AI Validation](./ai-validation.md) - Analyze captures automatically
- 📖 [Analytics](./analytics.md) - Monitor quality metrics
- 📚 [User Guide - Monitoring](../user-guide/monitoring.md) - Set up monitoring
- 🔧 [Technical Docs - Video Architecture](../technical/architecture/video_architecture.md)

---

**Ready to see everything your devices do?**  
➡️ [Get Started](../get-started/quickstart.md)


