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
# Detect vncserver binary location
VNC_BINARY=""
for path in "/usr/bin/vncserver" "/usr/local/bin/vncserver" "/bin/vncserver"; do
    if [ -x "$path" ]; then
        VNC_BINARY="$path"
        break
    fi
done

if [ -z "$VNC_BINARY" ]; then
    echo "⚠️ vncserver binary not found - VNC service will be disabled"
    echo "   Install TigerVNC with: sudo apt-get install tigervnc-standalone-server"
    VNC_BINARY="/usr/bin/vncserver"  # Use default path for service file
fi

echo "📍 Using VNC binary: $VNC_BINARY"

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

# Enable and start all services
echo ""
echo "🚀 Enabling and starting all host services..."

# Enable services for auto-start
sudo systemctl enable monitor.service
sudo systemctl enable stream.service  
sudo systemctl enable vncserver.service
sudo systemctl enable novnc.service

# Start services with error handling
echo "🔵 Starting VNC server..."
if [ -x "$VNC_BINARY" ]; then
    if sudo systemctl start vncserver.service; then
        echo "✅ VNC server started successfully"
    else
        echo "❌ VNC server failed to start - continuing with other services"
        echo "   Check logs with: sudo journalctl -u vncserver.service"
    fi
else
    echo "⚠️ VNC server skipped - binary not found"
fi

echo "🟢 Starting noVNC web interface..."
if sudo systemctl start novnc.service; then
    echo "✅ noVNC web interface started successfully"
else
    echo "❌ noVNC failed to start - continuing with other services"
    echo "   Check logs with: sudo journalctl -u novnc.service"
fi

echo "🟡 Starting stream service..."
if sudo systemctl start stream.service; then
    echo "✅ Stream service started successfully"
else
    echo "❌ Stream service failed to start - continuing with other services"
    echo "   Check logs with: sudo journalctl -u stream.service"
fi

echo "🟠 Starting monitor service..."
if sudo systemctl start monitor.service; then
    echo "✅ Monitor service started successfully"
else
    echo "❌ Monitor service failed to start - continuing with other services"
    echo "   Check logs with: sudo journalctl -u monitor.service"
fi

echo "✅ Host services installation completed (some services may have failed)"

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
vncserver -kill :1 2>/dev/null || true
rm -f /tmp/.X1-lock 2>/dev/null || true
rm -f /tmp/.X11-unix/X1 2>/dev/null || true

# Create VNC directory
mkdir -p ~/.vnc

# Set default VNC password (admin1234)
if command -v vncpasswd &> /dev/null; then
    echo "admin1234" | vncpasswd -f > ~/.vnc/passwd 2>/dev/null || {
        echo "⚠️ vncpasswd failed, creating manual password file"
        # Create a simple password file manually (this is a fallback)
        echo "admin1234" > ~/.vnc/passwd
    }
    chmod 600 ~/.vnc/passwd
    echo "✅ VNC password set to: admin1234"
else
    echo "⚠️ vncpasswd not found - VNC password setup skipped"
    echo "   Install TigerVNC with: sudo apt-get install tigervnc-standalone-server"
    echo "   Or run: ./setup/local/cleanup_vnc.sh"
fi

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
echo "   vncserver :1                        # Start VNC server manually"
echo "   xrandr -display :1 -s 1280x720     # Set display resolution"
echo "   vncserver -kill :1                  # Stop VNC server"
echo ""
echo "🔧 VNC Troubleshooting:"
echo "   sudo systemctl status vncserver     # Check service status"
echo "   sudo journalctl -u vncserver -f    # View service logs"
echo "   sudo systemctl restart vncserver   # Restart VNC service"
echo "   ps aux | grep vnc                  # Check running VNC processes"
echo ""
echo "⚠️  Common VNC Issues:"
echo "   - Binary not found: Install TigerVNC with 'sudo apt-get install tigervnc-standalone-server'"
echo "   - Conflicting packages: Run './setup/local/cleanup_vnc.sh' to fix"
echo "   - Display lock files: Service automatically cleans /tmp/.X1-lock and /tmp/.X11-unix/X1"
echo "   - Permission issues: Ensure ~/.vnc/passwd has 600 permissions"
echo ""
echo "🔧 Quick VNC Fix:"
echo "   ./setup/local/cleanup_vnc.sh              # Clean install TigerVNC only"
echo "   sudo systemctl restart vncserver          # Restart VNC service"
echo ""
echo "💡 Note: rename and cleanup are handled internally by stream.service"

# Final VNC status check
echo ""
echo "🔍 Final VNC Status Check:"
if command -v vncserver >/dev/null 2>&1; then
    echo "✅ vncserver binary found: $(which vncserver)"
    if systemctl is-active --quiet vncserver.service 2>/dev/null; then
        echo "✅ VNC service is running"
    else
        echo "⚠️ VNC service is not running - may need manual start"
    fi
else
    echo "❌ vncserver binary not found"
    echo "   Run: sudo apt-get install tigervnc-standalone-server"
    echo "   Or:  ./setup/local/cleanup_vnc.sh"
fi 