# VirtualPyTest Backend Host

Hardware interface service providing direct device control and system management.

## 🚀 **Quick Deploy to Render**

**TL;DR**: Use Docker deployment with these settings:
- **Environment**: Docker (NOT Python)
- **Root Directory**: Empty
- **Dockerfile Path**: `backend_host/Dockerfile`
- **Port**: 6109

## 🎯 **Purpose**

backend_host runs on hardware devices (like Raspberry Pi) and provides REST API endpoints for direct hardware control. It bridges the gap between cloud-based test orchestration and physical device manipulation.

## 🔧 **Installation**

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python src/app.py
```

**Note**: Both `shared` and `backend_host` are included via PYTHONPATH in Docker deployments. For local development, ensure the project structure is maintained.

## 🌐 **API Endpoints**

### Device Control
- `POST /host/takeControl` - Take control of device
- `POST /host/releaseControl` - Release device control
- `GET /host/status` - Get device status

### Recording & Capture
- `POST /host/rec/listRestartImages` - List recent images
- `GET /host/rec/stream` - Live video stream
- `POST /host/rec/capture` - Capture screenshot

### Automation Controllers
- `POST /host/web/executeCommand` - Web automation
- `POST /host/remote/executeAction` - Mobile device action
- `POST /host/desktop/click` - Desktop click action
- `POST /host/desktop/type` - Desktop typing

### Desktop Access
- **NoVNC Web Interface**: `http://host:6080` - Browser-based desktop access
- **VNC Direct**: `host:5900` - Direct VNC client access
- **Virtual Display**: `:99` - Xvfb virtual display server

### Audio/Video
- `POST /host/av/startCapture` - Start A/V capture
- `POST /host/av/stopCapture` - Stop A/V capture
- `GET /host/av/status` - Get A/V status

### Power Management
- `POST /host/power/on` - Turn device on
- `POST /host/power/off` - Turn device off
- `GET /host/power/status` - Get power status

### Verification
- `POST /host/verification/image` - Image verification
- `POST /host/verification/text` - Text verification
- `POST /host/verification/audio` - Audio verification

## 🏗️ **Architecture**

```
backend_host Service
├── Flask Application (Gunicorn)
├── Route Handlers (/host/*)
├── backend_host Controllers
├── Hardware Abstraction Layer
└── Physical Devices
```

## 🔧 **Configuration**

### Environment Variables

Copy the host-specific template:

```bash
# Copy host-specific template (from src directory)
cp src/env.example src/.env

# Edit with your values
nano src/.env
```

### Service Configuration

Backend Host automatically detects required services based on your `.env` configuration:

#### **Minimal Configuration (VNC Only)**
```bash
# .env - Only basic host settings
HOST_NAME=my-host
HOST_PORT=6109
```
**Result**: Only VNC services start (NoVNC web interface + VNC server)

#### **Full Configuration (VNC + Video + Monitor)**
```bash
# .env - With video devices
HOST_NAME=my-host
HOST_PORT=6109

# Device 1 configuration
DEVICE1_VIDEO=/dev/video0
DEVICE1_AUDIO=plughw:2,0
DEVICE1_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture1
DEVICE1_FPS=10

# Device 2 configuration  
DEVICE2_VIDEO=/dev/video2
DEVICE2_AUDIO=plughw:3,0
DEVICE2_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture2
DEVICE2_FPS=10
```
**Result**: VNC + FFmpeg capture (2 grabbers) + Monitor services start

### Required Environment Variables

```bash
# Host Identification
HOST_NAME=my-host-1
HOST_PORT=6109
HOST_URL=http://localhost:6109

# Database Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Optional: Cloud Storage & AI
CLOUDFLARE_R2_ENDPOINT=your_r2_endpoint
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
OPENROUTER_API_KEY=your_openrouter_key
```

### Hardware Setup

#### Raspberry Pi Setup
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3-pip git nginx

# Clone repository
git clone <repository-url>
cd virtualpytest

# Install Python dependencies
cd backend_host
pip3 install -r requirements.txt

# Setup systemd service
sudo cp ../deployment/systemd/backend_host.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend_host
sudo systemctl start backend_host
```

#### Device Connections
- **Android**: Enable USB debugging, connect via ADB
- **iOS**: Install dependencies for iOS automation
- **Desktop**: Configure display server access
- **A/V**: Setup video capture devices

## 🚀 **Deployment**

### Render Deployment (Cloud Host)

**IMPORTANT**: This project requires Docker deployment due to system dependencies (hardware drivers, graphics libraries, multi-directory structure).

#### Step-by-Step Render Docker Deployment:

1. **Create New Web Service** on Render dashboard
2. **Connect Repository**: Link your GitHub repo to Render
3. **Configure Service Settings**:
   - **Environment**: Select **"Docker"** (NOT Python)
   - **Region**: Choose your preferred region
   - **Branch**: `dev` (or your deployment branch)
   - **Root Directory**: Leave **EMPTY** (uses project root)
   - **Dockerfile Path**: `backend_host/Dockerfile`

4. **Environment Variables**: Set these in Render dashboard:
```bash
# Required Render environment variables
HOST_PORT=6109
HOST_NAME=render-host-1
SERVER_URL=https://your-backend-server.onrender.com
DEBUG=false
RENDER=true
DISPLAY=:99

# Optional: Add your API keys
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
OPENROUTER_API_KEY=your_openrouter_key
```

5. **Deploy**: Click "Create Web Service" - Render will build and deploy automatically

#### Why Docker is Required:
- ✅ **System Dependencies**: Hardware drivers, graphics libraries (libGL, Xvfb)
- ✅ **Multi-Directory Structure**: Needs `shared/`, `backend_host/`, `backend_host/`
- ✅ **Hardware Access**: Virtual display server and automation tools
- ✅ **Consistent Environment**: Same setup across dev/staging/prod

#### Troubleshooting Render Deployment:
- **Build fails**: Ensure "Docker" environment is selected, not "Python"
- **Wrong paths**: Root Directory should be empty, Dockerfile Path should be `backend_host/Dockerfile`
- **Port issues**: Ensure HOST_PORT=6109 is set in environment variables

**Note**: Render deployment creates a "cloud host" for testing. For physical hardware control, deploy on actual hardware (Raspberry Pi, etc.).

#### Desktop Access on Render:
Once deployed, you can access the virtual desktop:
- **NoVNC Web Interface**: `https://your-host-service.onrender.com:6080`
- **API Endpoints**: `https://your-host-service.onrender.com:6109/host/*`

### Docker Deployment (Local/Hardware)

#### **Quick Docker Launch**
```bash
# Use the setup script for easy deployment
./setup/docker/launch_all.sh
```

#### **Manual Docker Build & Run**
```bash
# Build image
docker build -f backend_host/Dockerfile -t virtualpytest/backend_host .

# Run with minimal config (VNC only)
# Configure via backend_host/src/.env file
docker run -d \
  -p 6109:6109 -p 6080:6080 \
  virtualpytest/backend_host

# Run with video devices (requires privileged mode for hardware access)
# Configure DEVICE* variables in backend_host/src/.env file
docker run -d --privileged \
  -p 6109:6109 -p 6080:6080 \
  -v /dev:/dev \
  virtualpytest/backend_host
```

#### **Docker Compose (Recommended)**
```bash
# Use docker-compose for full stack
cd docker
docker compose up backend_host
```

### Systemd Service
```bash
# Install service
sudo systemctl enable backend_host
sudo systemctl start backend_host

# Check status
sudo systemctl status backend_host
sudo journalctl -u backend_host -f
```

### Manual Start
```bash
# Development mode
DEBUG=true python src/app.py

# Production mode
python src/app.py
```

## 🌐 **Communication**

### Registration with backend_server
backend_host automatically registers itself with backend_server:

```python
# Automatic registration on startup
{
    "host_name": "sunri-pi2",
    "host_url": "http://sunri-pi2:6109",
    "capabilities": ["mobile", "desktop", "av", "power"],
    "status": "available"
}
```

### Health Monitoring
- Periodic ping to backend_server
- Health check endpoint: `/host/health`
- Status reporting and error handling

## 🔧 **Hardware Support**

### Supported Platforms
- **Raspberry Pi**: Primary target platform
- **Linux**: Ubuntu, Debian, CentOS
- **macOS**: Development and testing
- **Windows**: Limited support

### Device Types
- **Mobile**: Android (ADB), iOS (Appium)
- **Desktop**: Local display automation
- **A/V**: USB cameras, HDMI capture, audio devices
- **Power**: Smart plugs, UPS devices
- **Network**: IoT devices, smart switches

## 🧪 **Testing**

### Health Check
```bash
curl http://localhost:6109/host/health
```

### Device Control Test
```bash
# Take control
curl -X POST http://localhost:6109/host/takeControl \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device1"}'

# Execute action
curl -X POST http://localhost:6109/host/remote/executeAction \
  -H "Content-Type: application/json" \
  -d '{"action": "tap", "x": 100, "y": 200}'
```

### Integration Tests
```bash
# Run hardware tests
python -m pytest tests/hardware/

# Run API tests
python -m pytest tests/api/
```

## 📊 **Monitoring**

### Logs
```bash
# View service logs
sudo journalctl -u backend_host -f

# View application logs
tail -f /var/log/backend_host.log
```

### Metrics
- Device status and availability
- Action execution times
- Error rates and types
- Resource usage (CPU, memory, disk)

## 🔧 **Troubleshooting**

### Common Issues

#### Port Already in Use
```bash
# Find process using port
sudo netstat -tlnp | grep :6109

# Kill process
sudo kill -9 <PID>
```

#### Device Connection Issues
```bash
# Check ADB devices
adb devices

# Restart ADB server
adb kill-server && adb start-server

# Check USB permissions
ls -la /dev/ttyUSB*
```

#### Hardware Access
```bash
# Check video devices
ls -la /dev/video*

# Check audio devices
aplay -l

# Check camera permissions
sudo usermod -a -G video $USER
```

### Service Recovery
```bash
# Restart service
sudo systemctl restart backend_host

# Reset to clean state
sudo systemctl stop backend_host
rm -rf /tmp/backend_host-*
sudo systemctl start backend_host
```

## 🔐 **Security**

- **Network**: Restrict access to trusted networks
- **Authentication**: Token-based API access
- **Hardware**: Secure device connections
- **Updates**: Regular security updates

## 📋 **Requirements**

### Hardware
- ARM64 or x86_64 processor
- 2GB+ RAM recommended
- USB ports for device connections
- Network connectivity

### Software
- Python 3.8+
- Linux kernel with device support
- Required system packages (see Dockerfile)

## 🤝 **Contributing**

1. Add new hardware controllers to backend_host
2. Create corresponding route handlers
3. Update API documentation
4. Add integration tests
5. Test on actual hardware 