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
cat > /tmp/monitor.service << 'EOF'
[Unit]
Description=VirtualPyTest Capture Monitor Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)
Environment=PYTHONPATH=$(pwd)/shared/lib:$(pwd)/backend_core/src
Environment=PATH=$(pwd)/venv/bin:/usr/bin:/usr/local/bin
ExecStart=$(pwd)/venv/bin/python backend_host/scripts/capture_monitor.py
Restart=always
RestartSec=10
StandardOutput=append:/tmp/capture_monitor_service.log
StandardError=append:/tmp/capture_monitor_service.log

[Install]
WantedBy=multi-user.target
EOF

# FFmpeg Capture Service (matches backend_host/config/services/stream.service)
cat > /tmp/stream.service << EOF
[Unit]
Description=VirtualPyTest FFmpeg Capture Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)/backend_host/scripts
ExecStart=/bin/bash run_ffmpeg_and_rename_local.sh
Restart=always
RestartSec=15
StandardOutput=append:/tmp/ffmpeg_service.log
StandardError=append:/tmp/ffmpeg_service.log

[Install]
WantedBy=multi-user.target
EOF

# VNC Server Service (matches backend_host/config/services/vncserver.service)
cat > /tmp/vncserver.service << EOF
[Unit]
Description=Tigervnc full-control service for display 1
After=network.target

[Service]
Type=forking
User=$USER
ExecStart=/usr/bin/vncserver :1 -rfbauth /home/$USER/.vnc/passwd -rfbport 5901 -localhost no
ExecStop=/usr/bin/vncserver -kill :1
Restart=on-failure

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
sudo cp /tmp/monitor.service /etc/systemd/system/
sudo cp /tmp/stream.service /etc/systemd/system/
sudo cp /tmp/vncserver.service /etc/systemd/system/
sudo cp /tmp/novnc.service /etc/systemd/system/
sudo systemctl daemon-reload

# Note: Service management scripts would be copied from examples if they existed
echo "ℹ️  Service management scripts can be created manually if needed"

# VNC Server Setup
echo ""
echo "🖥️ Setting up VNC server with default configuration..."

# Create VNC directory
mkdir -p ~/.vnc

# Set default VNC password (admin1234)
echo "admin1234" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# Create xstartup file for VNC session
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
xrdb $HOME/.Xresources 2>/dev/null || true
fluxbox &
EOF
chmod +x ~/.vnc/xstartup

# Create VNC config file
cat > ~/.vnc/config << 'EOF'
session=fluxbox
geometry=1280x720
localhost=no
alwaysshared
EOF

echo "✅ VNC server configured with default password: admin1234"

# Test VNC setup
echo "🧪 Testing VNC configuration..."
if [ -f ~/.vnc/passwd ]; then
    echo "✅ VNC password file created"
else
    echo "❌ VNC password file missing"
fi

if [ -f ~/.vnc/xstartup ]; then
    echo "✅ VNC startup script created"
else
    echo "❌ VNC startup script missing"
fi

if [ -f ~/.vnc/config ]; then
    echo "✅ VNC config file created"
else
    echo "❌ VNC config file missing"
fi



echo ""
echo "✅ backend_host services installation completed!"
echo ""
echo "📋 Configuration files created:"
echo "   backend_host/src/.env                      # Device and hardware configuration"
echo ""
echo "📋 Next steps (in order):"
echo "1. Configure your devices FIRST:"
echo "   nano backend_host/src/.env"
echo ""
echo "2. Manage services using systemctl:"
echo "   sudo systemctl enable <service_name>       # Enable auto-start"
echo "   sudo systemctl start <service_name>        # Start service"
echo "   sudo systemctl status <service_name>       # Check status"
echo "   sudo journalctl -u <service_name> -f       # View logs"
echo ""
echo "🔧 Available services (matching backend_host/config/services/):"
echo "   - monitor.service                   # Capture analysis & alerts"
echo "   - stream.service                    # Video/audio capture + rename + cleanup"
echo "   - vncserver.service                 # VNC server (display :1, port 5901)"
echo "   - novnc.service                     # noVNC web interface (port 6080)"
echo ""
echo "🖥️ VNC Access Information:"
echo "   - VNC Server: localhost:5901 (display :1)"
echo "   - Default Password: admin1234"
echo "   - Web Interface: http://localhost:6080"
echo "   - Resolution: 1280x720"
echo ""
echo "🚀 Quick VNC Test:"
echo "   vncserver :1                        # Start VNC server manually"
echo "   xrandr -display :1 -s 1280x720     # Set display resolution"
echo "   vncserver -kill :1                  # Stop VNC server"
echo ""
echo "💡 Note: rename and cleanup are handled internally by stream.service" 