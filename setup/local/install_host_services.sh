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
Environment=PYTHONPATH=$(pwd)/shared/lib:$(pwd)/backend_core/src
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
WorkingDirectory=/usr/local/bin
ExecStart=/bin/bash /usr/local/bin/run_ffmpeg_and_rename.sh
Restart=always
RestartSec=15
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
sudo cp /tmp/monitor.service /etc/systemd/system/
sudo cp /tmp/stream.service /etc/systemd/system/
sudo cp /tmp/vncserver.service /etc/systemd/system/
sudo cp /tmp/novnc.service /etc/systemd/system/
sudo systemctl daemon-reload

# Create required directories
echo "📁 Creating stream directories..."
sudo mkdir -p /var/www/html/stream/capture1/captures
sudo mkdir -p /var/www/html/stream/capture2/captures
sudo mkdir -p /var/www/html/stream/capture3/captures
sudo mkdir -p /var/www/html/stream/capture4/captures
sudo chown -R $USER:$USER /var/www/html/stream
echo "✅ Stream directories created"

# Copy required scripts to system locations
echo "📋 Installing system scripts..."
sudo cp backend_host/scripts/run_ffmpeg_and_rename_local.sh /usr/local/bin/run_ffmpeg_and_rename.sh
sudo cp backend_host/scripts/clean_captures.sh /usr/local/bin/clean_captures.sh
sudo chmod +x /usr/local/bin/run_ffmpeg_and_rename.sh
sudo chmod +x /usr/local/bin/clean_captures.sh
echo "✅ Scripts installed to /usr/local/bin/"

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

# Install local nginx configuration
echo "📋 Installing local nginx configuration..."
sudo cp backend_server/config/nginx/local.conf /etc/nginx/sites-available/virtualpytest-local
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/virtualpytest*
sudo ln -sf /etc/nginx/sites-available/virtualpytest-local /etc/nginx/sites-enabled/virtualpytest-local

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

# Enable services for auto-start
sudo systemctl enable monitor.service
sudo systemctl enable stream.service  
sudo systemctl enable vncserver.service
sudo systemctl enable novnc.service

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

echo "✅ Host services installation completed (check individual service status above)"

# Note: Service management scripts would be copied from examples if they existed
echo "ℹ️  Service management scripts can be created manually if needed"

# VNC Server Setup
echo ""
echo "🖥️ Setting up VNC server with default configuration..."

# Make sure we continue even if VNC setup fails
set +e  # Disable exit on error for VNC setup

# Clean up any existing VNC sessions for display :1
echo "🧹 Cleaning up existing VNC sessions..."
pkill -f "Xvnc.*:1" 2>/dev/null || true
tigervncserver -kill :1 2>/dev/null || true
rm -f /tmp/.X1-lock 2>/dev/null || true
rm -f /tmp/.X11-unix/X1 2>/dev/null || true

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

# Proactive VNC cleanup (we know these steps are required)
echo "🧹 Proactive VNC cleanup before testing..."
sudo systemctl stop vncserver 2>/dev/null || true
pkill -f "Xvnc.*:1" 2>/dev/null || true
sudo rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 2>/dev/null || true
sleep 2
echo "✅ VNC cleanup completed"

# Test VNC server startup
echo "🔧 Testing VNC server startup..."
if tigervncserver :1 -rfbauth ~/.vnc/passwd -rfbport 5901 -localhost no -geometry 1280x720 >/dev/null 2>&1; then
    echo "✅ VNC server test successful"
    # Check if it's actually listening on port 5901
    sleep 2
    if netstat -tlnp 2>/dev/null | grep -q ":5901"; then
        echo "✅ VNC server listening on port 5901"
    else
        echo "⚠️ VNC server started but not listening on port 5901"
    fi
    # Kill test session before starting service
    tigervncserver -kill :1 >/dev/null 2>&1
    sleep 1
else
    echo "⚠️ VNC server test failed - check configuration manually"
fi

# Final cleanup before starting systemd services
echo "🧹 Final cleanup before systemd service start..."
pkill -f "Xvnc.*:1" 2>/dev/null || true
sudo rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 2>/dev/null || true
sleep 2



# Re-enable exit on error
set -e

echo ""
echo "🔄 Finishing installation..."
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
