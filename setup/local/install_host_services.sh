#!/bin/bash

# VirtualPyTest - Install and Configure backend_host Services
# This script sets up capture monitoring, alert system, and FFmpeg services

set -e

echo "🔧 Installing VirtualPyTest backend_host Services..."

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend_host" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Install backend_host dependencies first
echo "📦 Installing backend_host dependencies..."
./setup/local/install_host.sh

# Activate virtual environment for service file generation
source venv/bin/activate

# Ensure backend_host .env configuration exists
echo "⚙️ Setting up backend_host environment configuration..."

# Ensure .env file exists for backend_host (already done by install_host.sh, but verify)
if [ ! -f "backend_host/src/.env" ]; then
    echo "📋 Creating backend_host .env from template..."
    cp backend_host/src/env.example backend_host/src/.env
    echo "✅ Configuration copied to backend_host/src/.env"
    echo "⚠️  Please edit this file to match your hardware setup"
else
    echo "✅ backend_host .env already exists"
fi

# Create systemd service files
echo "🖥️ Creating systemd service files..."

# Capture Monitor Service (matches backend_host/config/services/monitor.service)
cat > /tmp/monitor.service << EOF
[Unit]
Description=VirtualPyTest Capture Monitor Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)/backend_host/scripts
Environment=HOST_NAME=$USER
Environment=PYTHONPATH=$(pwd)/shared/lib:$(pwd)/backend_host/src
Environment=PATH=$(pwd)/venv/bin:/usr/bin:/usr/local/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/backend_host/scripts/capture_monitor.py
TimeoutStopSec=10
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

# FFmpeg Capture Service (uses project scripts - .env driven)
cat > /tmp/stream.service << EOF
[Unit]
Description=VirtualPyTest FFmpeg Capture Service
After=network.target
Wants=network.target

[Service]
Type=forking
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_ROOT/backend_host/scripts
ExecStart=/bin/bash $PROJECT_ROOT/backend_host/scripts/run_ffmpeg_and_rename_local.sh
Restart=always
RestartSec=15
TimeoutStopSec=20

# Logging to files for easier debugging
StandardOutput=append:/tmp/ffmpeg_service.log
StandardError=append:/tmp/ffmpeg_service.log

[Install]
WantedBy=multi-user.target
EOF

# VNC Server Service (matches backend_host/config/services/vncserver.service)
# Use tigervncserver (the correct TigerVNC binary name)
VNC_BINARY="/usr/bin/tigervncserver"

cat > /tmp/vncserver.service << EOF
[Unit]
Description=Tigervnc full-control service for display 1
After=network.target

[Service]
Type=forking
User=$USER
ExecStartPre=/bin/bash -c 'if [ -f /tmp/.X1-lock ]; then rm -f /tmp/.X1-lock; fi'
ExecStartPre=/bin/bash -c 'if [ -S /tmp/.X11-unix/X1 ]; then rm -f /tmp/.X11-unix/X1; fi'
ExecStart=$VNC_BINARY :1 -rfbauth /home/$USER/.vnc/passwd -rfbport 5901 -localhost no -geometry 1280x720
ExecStop=$VNC_BINARY -kill :1
PIDFile=/home/$USER/.vnc/%H:1.pid
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# noVNC Service (matches backend_host/config/services/novnc.service)
cat > /tmp/novnc.service << EOF
[Unit]
Description=noVNC websockify service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/usr/share/novnc
ExecStart=/usr/bin/websockify --web /usr/share/novnc 6080 localhost:5901
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# No separate rename/cleanup services needed - they're handled internally by the stream service

# Install systemd services
echo "📋 Installing systemd services..."
# Core services (matching backend_host/config/services/ names)
sudo cp backend_host/systemd/monitor.service /etc/systemd/system/
sudo cp backend_host/systemd/stream.service /etc/systemd/system/
sudo cp backend_host/systemd/vncserver.service /etc/systemd/system/
sudo cp backend_host/systemd/novnc.service /etc/systemd/system/
# Additional host services from backend_host/systemd/
sudo cp backend_host/systemd/archive-manifest.service /etc/systemd/system/
sudo cp backend_host/systemd/transcript-stream.service /etc/systemd/system/
sudo systemctl daemon-reload

# Create required directories
echo "📁 Creating stream directories..."
sudo mkdir -p /var/www/html/stream/capture1/captures
sudo mkdir -p /var/www/html/stream/capture2/captures
sudo mkdir -p /var/www/html/stream/capture3/captures
sudo mkdir -p /var/www/html/stream/capture4/captures
sudo chown -R $USER:$USER /var/www/html/stream
echo "✅ Stream directories created"

# Make project scripts executable (no copying needed - .env driven)
echo "📋 Making project scripts executable..."
chmod +x backend_host/scripts/run_ffmpeg_and_rename_local.sh
chmod +x backend_host/scripts/clean_captures.sh
chmod +x backend_host/scripts/capture_monitor.py
chmod +x backend_host/scripts/archive_manifest_generator.py
chmod +x backend_host/scripts/transcript_accumulator.py
echo "✅ Scripts made executable in project directory"
echo "ℹ️  Scripts now read configuration from backend_host/src/.env (single source of truth)"

# Install and configure nginx for local development
echo ""
echo "🌐 Installing and configuring nginx for local development..."

# Install nginx if not present
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing nginx..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y nginx
    elif command -v yum &> /dev/null; then
        sudo yum install -y nginx
    else
        echo "⚠️ Could not install nginx automatically. Please install manually."
    fi
else
    echo "✅ nginx already installed"
fi

# Detect host IP for nginx configuration
echo "📋 Detecting host IP address for nginx configuration..."
HOST_IP=""
if command -v ip >/dev/null 2>&1; then
    # Use ip command (preferred on modern systems)
    HOST_IP=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' 2>/dev/null || echo "")
elif command -v ifconfig >/dev/null 2>&1; then
    # Fallback to ifconfig
    HOST_IP=$(ifconfig 2>/dev/null | grep -E "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | sed 's/addr://')
fi

if [ -z "$HOST_IP" ]; then
    echo "⚠️ Could not detect host IP, using localhost only"
    HOST_IP="localhost"
else
    echo "✅ Detected host IP: $HOST_IP"
fi

# Install local nginx configuration with dynamic IP replacement
echo "📋 Installing local nginx configuration with host IP: $HOST_IP..."
# Create temporary config with replaced HOST_IP
sed "s/HOST_IP/$HOST_IP/g" backend_server/config/nginx/local.conf > /tmp/virtualpytest-local.conf
sudo cp /tmp/virtualpytest-local.conf /etc/nginx/sites-available/virtualpytest-local
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/virtualpytest*
sudo ln -sf /etc/nginx/sites-available/virtualpytest-local /etc/nginx/sites-enabled/virtualpytest-local
rm -f /tmp/virtualpytest-local.conf

# Test nginx configuration
if sudo nginx -t; then
    echo "✅ nginx configuration is valid"
    # Restart nginx to apply new configuration
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    echo "✅ nginx configured for local development"
else
    echo "⚠️ nginx configuration has errors - check 'sudo nginx -t' for details"
fi

# Enable and start all services
echo ""
echo "🚀 Enabling and starting all host services..."
echo ""
echo "📋 Service Management:"
echo "   Start all:    sudo systemctl start stream monitor vncserver novnc archive-manifest transcript-stream"
echo "   Stop all:     sudo systemctl stop stream monitor vncserver novnc archive-manifest transcript-stream"  
echo "   Restart all:  sudo systemctl restart stream monitor archive-manifest transcript-stream"
echo "   Status:       sudo systemctl status stream"
echo "   FFmpeg logs:  tail -f /tmp/ffmpeg_service.log"
echo "   Monitor logs: tail -f /tmp/capture_monitor.log"
echo "   Archive logs: tail -f /tmp/archive_manifest_generator.log"
echo "   Transcript logs: tail -f /tmp/transcript_accumulator.log"
echo ""

# Enable services for auto-start
sudo systemctl enable monitor.service
sudo systemctl enable stream.service  
sudo systemctl enable vncserver.service
sudo systemctl enable novnc.service
sudo systemctl enable archive-manifest.service
sudo systemctl enable transcript-stream.service

# Start services (with error handling to continue on failures)
echo "🔵 Starting VNC server..."
if sudo systemctl start vncserver.service; then
    echo "✅ VNC server started successfully"
else
    echo "⚠️ VNC server failed to start - check 'sudo systemctl status vncserver' for details"
fi

echo "🟢 Starting noVNC web interface..."
if sudo systemctl start novnc.service; then
    echo "✅ noVNC web interface started successfully"
else
    echo "⚠️ noVNC web interface failed to start - check 'sudo systemctl status novnc' for details"
fi

echo "🟡 Starting stream service..."
if sudo systemctl start stream.service; then
    echo "✅ Stream service started successfully"
else
    echo "⚠️ Stream service failed to start - check 'sudo systemctl status stream' for details"
fi

echo "🟠 Starting monitor service..."
if sudo systemctl start monitor.service; then
    echo "✅ Monitor service started successfully"
else
    echo "⚠️ Monitor service failed to start - check 'sudo systemctl status monitor' for details"
fi

echo "🟣 Starting archive manifest service..."
if sudo systemctl start archive-manifest.service; then
    echo "✅ Archive manifest service started successfully"
else
    echo "⚠️ Archive manifest service failed to start - check 'sudo systemctl status archive-manifest' for details"
fi

echo "🔴 Starting transcript stream service..."
if sudo systemctl start transcript-stream.service; then
    echo "✅ Transcript stream service started successfully"
else
    echo "⚠️ Transcript stream service failed to start - check 'sudo systemctl status transcript-stream' for details"
fi

echo "✅ Host services installation completed (check individual service status above)"
echo "🌐 nginx configured with host IP: $HOST_IP"

# Note: Service management scripts would be copied from examples if they existed
echo "ℹ️  Service management scripts can be created manually if needed"

# VNC Server Setup
echo ""
echo "🖥️ Setting up VNC server with default configuration..."

# Make sure we continue even if VNC setup fails
set +e  # Disable exit on error for VNC setup

# Clean up any existing VNC sessions for display :1 (HDMI-safe)
echo "🧹 Cleaning up existing VNC sessions (preserving HDMI display :0)..."
pkill -f "Xvnc.*:1" 2>/dev/null || true
tigervncserver -kill :1 2>/dev/null || true
# ONLY remove VNC display :1 files - NEVER touch display :0 (HDMI)
rm -f /tmp/.X1-lock 2>/dev/null || true
rm -f /tmp/.X11-unix/X1 2>/dev/null || true
# CRITICAL: Do NOT remove /tmp/.X0-lock or /tmp/.X11-unix/X0

# Create VNC directory
mkdir -p ~/.vnc

# Set default VNC password (admin1234)
echo "admin1234" | tigervncpasswd -f > ~/.vnc/passwd 2>/dev/null
chmod 600 ~/.vnc/passwd
echo "✅ TigerVNC password set to: admin1234"

# Create XFCE4 desktop session files (fixes black screen issue)
echo "🖥️ Creating XFCE4 session desktop files..."
sudo mkdir -p /usr/share/xsessions
sudo tee /usr/share/xsessions/xfce4.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=Xfce Session
Comment=Use this session to run Xfce as your desktop environment
Exec=startxfce4
Icon=
Type=Application
DesktopNames=XFCE
EOF

# Also create it in wayland-sessions for compatibility
sudo mkdir -p /usr/share/wayland-sessions
sudo cp /usr/share/xsessions/xfce4.desktop /usr/share/wayland-sessions/
echo "✅ XFCE4 session desktop files created"

# Create xstartup file for VNC session (using proven working configuration)
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/sh

# Load X resources if available
xrdb "$HOME/.Xresources" 2>/dev/null || true

# Set background color (prevents black screen)
xsetroot -solid grey

# Fix locale and D-Bus issues
export XKL_XMODMAP_DISABLE=1
export LANG=en_GB.UTF-8
export LC_ALL=en_GB.UTF-8

# Start XFCE4 directly with proper session
exec /usr/bin/startxfce4
EOF
chmod +x ~/.vnc/xstartup

# Create VNC config file
cat > ~/.vnc/config << 'EOF'
session=xfce4
geometry=1280x720
localhost=no
alwaysshared
EOF

echo "✅ VNC server configured with default password: admin1234"

# Test VNC setup
echo "🧪 Testing VNC configuration..."
echo "✅ VNC password file created"
echo "✅ VNC startup script created"
echo "✅ VNC config file created"
echo "✅ XFCE4 session files created"

# Proactive VNC cleanup (enhanced with user's manual fix steps - HDMI-safe)
echo "🧹 Enhanced proactive VNC cleanup before testing (preserving HDMI display :0)..."
sudo systemctl stop vncserver 2>/dev/null || true  # Step 1: Stop the service
# Step 2: Clean up ONLY VNC stale files - preserve HDMI display :0
sudo rm -f /tmp/.X1-lock /tmp/.X11-unix/X1  # Only VNC display :1
# CRITICAL: Never remove /tmp/.X0-lock or /tmp/.X11-unix/X0 (HDMI display)
pkill -f "Xvnc.*:1" 2>/dev/null || true  # Step 3: Kill only VNC processes
sleep 2  # Brief pause for cleanup

# Step 4: Test VNC web interface (simple curl test)
echo "🔧 Testing VNC web interface..."
if [ "$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:6080/vnc_lite.html")" = "200" ]; then
    echo "✅ VNC web interface test successful"
else
    echo "⚠️ VNC web interface test failed"
fi

# Step 5: Restart the service (as per user)
echo "🔄 Restarting VNC service..."
sudo systemctl start vncserver || echo "⚠️ Service start failed - check 'sudo systemctl status vncserver'"

echo "✅ Enhanced VNC cleanup and test completed"

# Re-enable exit on error
set -e

# Configure firewall ports for VNC services
echo "🔥 Configuring firewall for VNC services..."

# Source port checking functions
source "$PROJECT_ROOT/setup/local/check_and_open_port.sh"

echo "🔧 Configuring firewall for VNC ports:"
echo "   - VNC Server: 5901"
echo "   - noVNC Web Interface: 6080"

# Configure UFW for VNC ports
check_and_open_port "5901" "VNC server" "tcp"
check_and_open_port "6080" "noVNC web interface" "tcp"

echo ""
echo "🔄 Finishing installation..."
echo ""
echo "✅ backend_host services installation completed!"
echo ""
echo "📋 Configuration files:"
echo "   backend_host/src/.env                      # MASTER config (edit here only)"
echo ""
echo "📝 Required .env variables for FFmpeg capture:"
echo "   HOST_VIDEO_SOURCE, HOST_VIDEO_AUDIO, HOST_VIDEO_CAPTURE_PATH, HOST_VIDEO_FPS"
echo "   DEVICE*_VIDEO, DEVICE*_VIDEO_AUDIO, DEVICE*_VIDEO_CAPTURE_PATH, DEVICE*_VIDEO_FPS"
echo ""
echo "📚 Documentation: backend_host/scripts/CAPTURE_CONFIG.md"
echo ""
echo "📋 Next steps (in order):"
echo "1. Configure your devices in .env file:"
echo "   nano backend_host/src/.env"
echo ""
echo "   Example configuration:"
echo "   HOST_VIDEO_SOURCE=:1              # VNC display"
echo "   HOST_VIDEO_AUDIO=null"
echo "   HOST_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture1"
echo "   HOST_VIDEO_FPS=2"
echo ""
echo "   DEVICE1_VIDEO=/dev/video0         # Hardware device"
echo "   DEVICE1_VIDEO_AUDIO=plughw:2,0"
echo "   DEVICE1_VIDEO_CAPTURE_PATH=/var/www/html/stream/capture2"
echo "   DEVICE1_VIDEO_FPS=10"
echo ""
echo "   # Disable with 'x' prefix or comment with '#'"
echo "   xDEVICE2_VIDEO=/dev/video2"
echo ""
echo "2. Manage services using systemctl:"
echo "   sudo systemctl enable <service_name>       # Enable auto-start"
echo "   sudo systemctl start <service_name>        # Start service"
echo "   sudo systemctl status <service_name>       # Check status"
echo ""
echo "📋 Log Files:"
echo "   /tmp/ffmpeg_service.log                    # FFmpeg capture logs"
echo "   /tmp/capture_monitor.log                   # Monitoring logs"
echo "   /tmp/ffmpeg_output_*.log                   # Individual FFmpeg process logs"
echo "   /tmp/clean.log                             # Cleanup script logs"
echo ""
echo "   View logs: tail -f /tmp/ffmpeg_service.log"
echo ""
echo "🔧 Available services (matching backend_host/config/services/):"
echo "   - monitor.service                   # Capture analysis & alerts"
echo "   - stream.service                    # Video/audio capture + rename + cleanup"
echo "   - vncserver.service                 # VNC server (display :1, port 5901)"
echo "   - novnc.service                     # noVNC web interface (port 6080)"
echo "   - archive-manifest.service          # HLS archive manifest generation (24h)"
echo "   - transcript-stream.service         # Audio transcription (24h circular buffer)"
echo ""
echo "🖥️ VNC Access Information:"
echo "   - VNC Server: $HOST_IP:5901 (display :1)"
echo "   - Default Password: admin1234"
echo "   - Web Interface: http://$HOST_IP:6080"
echo "   - nginx Proxy: http://$HOST_IP/vnc/"
echo "   - Resolution: 1280x720"
echo ""
echo "🚀 Quick VNC Test:"
echo "   tigervncserver :1                   # Start TigerVNC server manually"
echo "   xrandr -display :1 -s 1280x720     # Set display resolution"
echo "   tigervncserver -kill :1             # Stop TigerVNC server"
echo ""
echo "🔧 VNC Troubleshooting:"
echo "   sudo systemctl status vncserver     # Check service status"
echo "   sudo journalctl -u vncserver -f    # View service logs"
echo "   sudo systemctl restart vncserver   # Restart VNC service"
echo "   ps aux | grep vnc                  # Check running VNC processes"
echo ""
echo "⚠️  Common VNC Issues:"
echo "   - Display lock files: Service automatically cleans /tmp/.X1-lock and /tmp/.X11-unix/X1"
echo "   - Permission issues: Ensure ~/.vnc/passwd has 600 permissions"
echo "   - Service restart: sudo systemctl restart vncserver"
echo ""
echo "💡 Note: rename and cleanup are handled internally by stream.service"
