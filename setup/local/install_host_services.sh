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

# Create service configuration
echo "⚙️ Creating service configuration from examples..."

# Create backend_host config directory
mkdir -p backend_host/config

# Copy configuration from examples
if [ ! -f "backend_host/config/host_config.json" ]; then
    echo "📋 Copying default host configuration..."
    cp backend_host/examples/config/host_config.example.json backend_host/config/host_config.json
    echo "✅ Configuration copied to backend_host/config/host_config.json"
    echo "⚠️  Please edit this file to match your hardware setup"
else
    echo "⚠️  Configuration file already exists, skipping copy"
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

# Copy management scripts from examples
echo "🛠️ Copying service management scripts..."
if [ ! -f "backend_host/manage_services.sh" ]; then
    cp backend_host/examples/scripts/manage_services.example.sh backend_host/manage_services.sh
    chmod +x backend_host/manage_services.sh
    echo "✅ Service manager copied to backend_host/manage_services.sh"
else
    echo "⚠️  Service manager already exists, skipping copy"
fi

if [ ! -f "backend_host/setup_host_environment.sh" ]; then
    cp backend_host/examples/scripts/setup_host_environment.example.sh backend_host/setup_host_environment.sh
    chmod +x backend_host/setup_host_environment.sh
    echo "✅ Environment setup copied to backend_host/setup_host_environment.sh"
else
    echo "⚠️  Environment setup already exists, skipping copy"
fi

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
echo "   backend_host/config/host_config.json       # Device configuration"
echo "   backend_host/manage_services.sh            # Service management"
echo "   backend_host/setup_host_environment.sh     # Environment setup"
echo ""
echo "📋 Next steps (in order):"
echo "1. Configure your devices FIRST:"
echo "   nano backend_host/config/host_config.json"
echo ""
echo "2. Setup host environment:"
echo "   ./backend_host/setup_host_environment.sh"
echo ""
echo "3. Manage services:"
echo "   ./backend_host/manage_services.sh enable    # Enable auto-start"
echo "   ./backend_host/manage_services.sh start     # Start all services"
echo "   ./backend_host/manage_services.sh status    # Check status"
echo "   ./backend_host/manage_services.sh logs      # View logs"
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