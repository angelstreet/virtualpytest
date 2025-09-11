# Deployment Scripts

Service launcher scripts for VirtualPyTest microservices deployment.

## 🚀 **Service Launchers**

### `launch_virtualpytest.sh`
**Main orchestration script** that starts all VirtualPyTest services in the correct order.

```bash
# Launch complete VirtualPyTest system
./launch_virtualpytest.sh
```

**Features:**
- Starts backend_server and backend_host services
- Handles dependencies between services
- Manages service health checking
- Configures environment variables

### `launch_virtualhost.sh`
**backend_host service launcher** for Raspberry Pi hardware interface.

```bash
# Launch only backend_host service
./launch_virtualhost.sh
```

**Services Started:**
- backend_host Flask application (port 6109)
- Hardware monitoring scripts
- Device controllers
- Alert system

**Target Environment:**
- Raspberry Pi with hardware devices
- Local network accessible
- Direct hardware control required

### `launch_virtualserver.sh`
**backend_server launcher** for cloud/local API server.

```bash
# Launch backend_server service
./launch_virtualserver.sh
```

**Services Started:**
- backend_server Flask application (port 5109)
- API endpoints for client access
- WebSocket connections
- Business logic services

**Target Environment:**
- Cloud platforms (Render, AWS, etc.)
- Local development servers
- No hardware access needed

## 🍎 **Mac Development Scripts**

### `mac/mac_run_ffmpeg_and_rename.sh`
**macOS-compatible capture script** for development and testing.

```bash
# Run on macOS for development
./mac/mac_run_ffmpeg_and_rename.sh
```

**Differences from RPi version:**
- Uses macOS-compatible audio/video devices
- Adjusted paths for macOS filesystem
- Development-friendly configuration

### `mac/mac_clean_captures.sh`
**macOS cleanup script** for development captures.

```bash
# Clean up development captures on macOS
./mac/mac_clean_captures.sh
```

### `mac/mac_rename_captures.sh` (DEPRECATED)
**REMOVED** - File renaming system has been removed. FFmpeg now uses sequential naming directly.

## 🔧 **Usage Patterns**

### Production Deployment
```bash
# Raspberry Pi (hardware host)
./launch_virtualhost.sh

# Cloud server (Render/AWS)
./launch_virtualserver.sh

# Complete local setup
./launch_virtualpytest.sh
```

### Development Setup
```bash
# macOS development
cd mac/
./mac_run_ffmpeg_and_rename.sh &
./mac_clean_captures.sh &

# Local server development
./launch_virtualserver.sh
```

### Docker Alternative
Instead of using these scripts, you can use Docker:

```bash
# Docker deployment (recommended)
cd ../docker/
./scripts/deploy.sh development
```

## 🌐 **Environment Configuration**

### Common Variables
```bash
# Service URLs
SERVER_URL=http://localhost:5109
HOST_URL=http://localhost:6109

# Debug mode
DEBUG=false

# Host identification
HOST_NAME=sunri-pi2
```

### Platform-Specific
```bash
# Raspberry Pi
HOST_PORT=6109
CAPTURE_FOLDER=/var/www/html/stream/captures

# macOS Development
HOST_PORT=6109
CAPTURE_FOLDER=~/dev/virtualpytest/captures
```

## 📋 **Migration from Legacy Scripts**

These scripts have been migrated from the old `/scripts` directory:

| **Old Location** | **New Location** | **Purpose** |
|------------------|------------------|-------------|
| `scripts/launch_virtualpytest.sh` | `deployment/scripts/launch_virtualpytest.sh` | Main launcher |
| `scripts/launch_virtualhost.sh` | `deployment/scripts/launch_virtualhost.sh` | Host launcher |
| `scripts/launch_virtualserver.sh` | `deployment/scripts/launch_virtualserver.sh` | Server launcher |
| `scripts/mac_*.sh` | `deployment/scripts/mac/` | macOS development |

## 🔄 **Service Dependencies**

### Launch Order
1. **backend_server** (API layer) - port 5109
2. **backend_host** (hardware interface) - port 6109
3. **Frontend** (if local) - port 3000

### Inter-Service Communication
```
Frontend (3000) → backend_server (5109) → backend_host (6109) → Hardware
```

## 🧪 **Testing Deployment**

### Health Checks
```bash
# Check backend_server
curl http://localhost:5109/api/health

# Check backend_host  
curl http://localhost:6109/host/health

# Check service processes
ps aux | grep python | grep virtualpytest
```

### Service Logs
```bash
# View launcher logs
tail -f /tmp/virtualpytest_*.log

# View service logs
tail -f /tmp/backend_server.log
tail -f /tmp/backend_host.log
```

## 🔧 **Troubleshooting**

### Port Conflicts
```bash
# Check port usage
sudo netstat -tlnp | grep :5109
sudo netstat -tlnp | grep :6109

# Kill conflicting processes
sudo kill -9 $(lsof -ti:5109)
sudo kill -9 $(lsof -ti:6109)
```

### Permission Issues
```bash
# Make scripts executable
chmod +x deployment/scripts/*.sh
chmod +x deployment/scripts/mac/*.sh

# Check script paths
which python3
which ffmpeg
```

### Service Dependencies
```bash
# Install required packages
sudo apt install python3-pip python3-venv  # Linux
brew install python3 ffmpeg  # macOS

# Virtual environment setup (use project venv)
cd /path/to/virtualpytest
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🎯 **Recommended Usage**

### **Production**: Use Docker
```bash
cd docker/
./scripts/deploy.sh production
```

### **Development**: Use specific launchers
```bash
# API development
./launch_virtualserver.sh

# Hardware development
./launch_virtualhost.sh

# macOS development
cd mac/ && ./mac_run_ffmpeg_and_rename.sh
```

### **Legacy Compatibility**: Use main launcher
```bash
# If you need the old behavior
./launch_virtualpytest.sh
```

## 🤝 **Contributing**

1. **New Platform Support**: Add platform-specific directory (e.g., `windows/`)
2. **Service Extensions**: Modify launcher scripts for new services
3. **Environment Configs**: Add environment-specific configurations
4. **Health Monitoring**: Extend health check capabilities

## 📝 **Notes**

- These scripts provide **legacy compatibility** for existing deployments
- **Docker deployment is recommended** for new installations
- Scripts maintain **backward compatibility** with existing RPi setups
- **macOS scripts are for development only**, not production use 