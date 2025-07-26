#!/bin/bash

# VirtualPyTest - Install and Configure Backend-Host Services
# This script sets up capture monitoring, alert system, and FFmpeg services

set -e

echo "🔧 Installing VirtualPyTest Backend-Host Services..."

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-host" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Install backend-host dependencies first
echo "📦 Installing backend-host dependencies..."
./setup/local/install_host.sh

# Create service configuration
echo "⚙️ Creating service configuration from examples..."

# Create backend-host config directory
mkdir -p backend-host/config

# Copy configuration from examples
if [ ! -f "backend-host/config/host_config.json" ]; then
    echo "📋 Copying default host configuration..."
    cp backend-host/examples/config/host_config.example.json backend-host/config/host_config.json
    echo "✅ Configuration copied to backend-host/config/host_config.json"
    echo "⚠️  Please edit this file to match your hardware setup"
else
    echo "⚠️  Configuration file already exists, skipping copy"
fi

# Create systemd service files
echo "🖥️ Creating systemd service files..."

# Capture Monitor Service
cat > /tmp/virtualpytest-capture-monitor.service << 'EOF'
[Unit]
Description=VirtualPyTest Capture Monitor Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/virtualpytest
Environment=PYTHONPATH=/home/pi/virtualpytest/shared/lib:/home/pi/virtualpytest/backend-core/src
ExecStart=/home/pi/myvenv/bin/python backend-host/scripts/capture_monitor.py
Restart=always
RestartSec=10
StandardOutput=append:/tmp/capture_monitor_service.log
StandardError=append:/tmp/capture_monitor_service.log

[Install]
WantedBy=multi-user.target
EOF

# FFmpeg Capture Service
cat > /tmp/virtualpytest-ffmpeg-capture.service << 'EOF'
[Unit]
Description=VirtualPyTest FFmpeg Capture Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/virtualpytest/backend-host/scripts
ExecStart=/bin/bash run_ffmpeg_and_rename_rpi1.sh
Restart=always
RestartSec=15
StandardOutput=append:/tmp/ffmpeg_service.log
StandardError=append:/tmp/ffmpeg_service.log

[Install]
WantedBy=multi-user.target
EOF

# Rename Captures Service
cat > /tmp/virtualpytest-rename-captures.service << 'EOF'
[Unit]
Description=VirtualPyTest Rename Captures Service
After=virtualpytest-ffmpeg-capture.service
Wants=virtualpytest-ffmpeg-capture.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/virtualpytest/backend-host/scripts
ExecStart=/bin/bash rename_captures.sh
Restart=always
RestartSec=10
StandardOutput=append:/tmp/rename_service.log
StandardError=append:/tmp/rename_service.log

[Install]
WantedBy=multi-user.target
EOF

# Cleanup Service (timer-based)
cat > /tmp/virtualpytest-cleanup.service << 'EOF'
[Unit]
Description=VirtualPyTest Cleanup Service
After=network.target

[Service]
Type=oneshot
User=pi
Group=pi
WorkingDirectory=/home/pi/virtualpytest/backend-host/scripts
ExecStart=/bin/bash clean_captures.sh
StandardOutput=append:/tmp/cleanup_service.log
StandardError=append:/tmp/cleanup_service.log
EOF

cat > /tmp/virtualpytest-cleanup.timer << 'EOF'
[Unit]
Description=VirtualPyTest Cleanup Timer
Requires=virtualpytest-cleanup.service

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Install systemd services
echo "📋 Installing systemd services..."
sudo cp /tmp/virtualpytest-*.service /etc/systemd/system/
sudo cp /tmp/virtualpytest-*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Copy management scripts from examples
echo "🛠️ Copying service management scripts..."
if [ ! -f "backend-host/manage_services.sh" ]; then
    cp backend-host/examples/scripts/manage_services.example.sh backend-host/manage_services.sh
    chmod +x backend-host/manage_services.sh
    echo "✅ Service manager copied to backend-host/manage_services.sh"
else
    echo "⚠️  Service manager already exists, skipping copy"
fi

if [ ! -f "backend-host/setup_host_environment.sh" ]; then
    cp backend-host/examples/scripts/setup_host_environment.example.sh backend-host/setup_host_environment.sh
    chmod +x backend-host/setup_host_environment.sh
    echo "✅ Environment setup copied to backend-host/setup_host_environment.sh"
else
    echo "⚠️  Environment setup already exists, skipping copy"
fi



echo ""
echo "✅ Backend-Host services installation completed!"
echo ""
echo "📋 Configuration files created:"
echo "   backend-host/config/host_config.json       # Device configuration"
echo "   backend-host/manage_services.sh            # Service management"
echo "   backend-host/setup_host_environment.sh     # Environment setup"
echo ""
echo "📋 Next steps (in order):"
echo "1. Configure your devices FIRST:"
echo "   nano backend-host/config/host_config.json"
echo ""
echo "2. Setup host environment:"
echo "   ./backend-host/setup_host_environment.sh"
echo ""
echo "3. Manage services:"
echo "   ./backend-host/manage_services.sh enable    # Enable auto-start"
echo "   ./backend-host/manage_services.sh start     # Start all services"
echo "   ./backend-host/manage_services.sh status    # Check status"
echo "   ./backend-host/manage_services.sh logs      # View logs"
echo ""
echo "🔧 Individual services:"
echo "   - virtualpytest-ffmpeg-capture     # Video/audio capture"
echo "   - virtualpytest-rename-captures    # File processing"
echo "   - virtualpytest-capture-monitor    # Analysis & alerts"
echo "   - virtualpytest-cleanup.timer      # Cleanup (every 5 min)" 