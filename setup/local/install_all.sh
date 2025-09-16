#!/bin/bash

# VirtualPyTest - Fresh Installation
# This script performs a complete fresh installation of VirtualPyTest
# Usage: ./install_all.sh (no parameters - always fresh install)

set -e

echo "🔥 VirtualPyTest Fresh Installation"
echo "🗑️  This will clean and reinstall core components for a fresh system..."
echo ""

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "shared" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Make all install scripts executable
chmod +x setup/local/install_*.sh
chmod +x setup/local/setup_permissions.sh

echo "🚀 Installing all components..."

# Install system requirements first (automatically)
echo "0️⃣ Installing system requirements..."
if [ -f "./setup/local/install_requirements.sh" ]; then
    ./setup/local/install_requirements.sh
else
    echo "⚠️ Warning: install_requirements.sh not found, skipping system requirements"
fi

echo ""
echo "🔐 Setting up system permissions..."
# Set up permissions for www-data and directories (requires sudo)
if command -v sudo >/dev/null 2>&1; then
    echo "Setting up permissions (requires sudo access)..."
    if sudo -n true 2>/dev/null; then
        # Can run sudo without password
        sudo ./setup/local/setup_permissions.sh --user "$(whoami)"
    else
        # Need to prompt for sudo password
        echo "⚠️ Permission setup requires sudo access for:"
        echo "   - Creating /var/www directories"
        echo "   - Setting up www-data user permissions"
        echo "   - Configuring system group memberships"
        echo ""
        read -p "Run permission setup now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo ./setup/local/setup_permissions.sh --user "$(whoami)"
        else
            echo "⚠️ Skipping permission setup. You may need to run it manually later:"
            echo "   sudo ./setup/local/setup_permissions.sh --user $(whoami)"
        fi
    fi
else
    echo "⚠️ sudo not available. Skipping permission setup."
    echo "   You may need to manually create directories and set permissions."
fi

echo ""
echo "📄 Setting up environment files..."
# Automatically copy .env.example files to .env
if [ -f "env.local.example" ] && [ ! -f ".env" ]; then
    cp env.local.example .env
    echo "✅ Created main .env from env.local.example"
else
    echo "ℹ️ Main .env already exists or template not found"
fi

if [ -f "backend_host/src/env.example" ] && [ ! -f "backend_host/src/.env" ]; then
    cp backend_host/src/env.example backend_host/src/.env
    echo "✅ Created backend_host/.env from env.example"
else
    echo "ℹ️ Backend host .env already exists or template not found"
fi

if [ -f "frontend/env.example" ] && [ ! -f "frontend/.env" ]; then
    cp frontend/env.example frontend/.env
    echo "✅ Created frontend/.env from env.example"
else
    echo "ℹ️ Frontend .env already exists or template not found"
fi

echo ""
echo "1️⃣ Installing database (fresh)..."
./setup/local/install_db.sh --force-clean

echo ""
echo "2️⃣ Installing shared library (smart update)..."
./setup/local/install_shared.sh --smart-update

echo ""
echo "3️⃣ Installing backend_server (smart update)..."
./setup/local/install_server.sh --smart-update

echo ""
echo "4️⃣ Installing backend_host (fresh services)..."
./setup/local/install_host.sh --force-clean

echo ""
echo "4️⃣b Installing and starting host services (VNC, stream, monitor)..."
# Continue even if host services fail (e.g., VNC installation issues)
if ./setup/local/install_host_services.sh; then
    echo "✅ Host services installation completed successfully"
else
    echo "⚠️ Host services installation completed with some issues (VNC may need manual setup)"
fi

echo ""
echo "5️⃣ Installing frontend (smart update)..."
# Continue even if frontend installation fails
if ./setup/local/install_frontend.sh --smart-update; then
    echo "✅ Frontend installation completed successfully"
else
    echo "⚠️ Frontend installation completed with issues"
fi

echo ""
echo "6️⃣ Installing Grafana for monitoring (smart update)..."
# Continue even if Grafana installation fails
if ./setup/local/install_grafana.sh --smart-update; then
    echo "✅ Grafana installation completed successfully"
else
    echo "⚠️ Grafana installation completed with issues"
fi

echo ""
echo "🎉 Fresh VirtualPyTest installation completed successfully!"
echo "🐍 Virtual environment: $(pwd)/venv"
echo "🔌 To activate manually: source venv/bin/activate"
echo ""
echo "📝 IMPORTANT: Edit your .env files before launching:"
echo "   📁 .env - Main configuration (database, API keys)"
echo "   📁 backend_host/src/.env - Hardware/device settings"
echo "   📁 frontend/.env - Web interface settings"
echo ""
echo "🗄️ Fresh Database Configuration:"
echo "   🚀 Application DB: postgresql://virtualpytest_user:virtualpytest_pass@localhost:5432/virtualpytest"
echo "   📊 Grafana DB: postgresql://grafana_user:grafana_pass@localhost:5432/grafana_metrics"
echo ""
echo "🖥️ Fresh VNC Configuration:"
echo "   - VNC Server: localhost:5901 (display :1)"
echo "   - Default Password: admin1234"
echo "   - Web Interface: http://localhost:6080"
echo "   - Remote Access: Use device IP addresses shown in Network Information section"
echo ""
echo "🔧 VNC Troubleshooting (if VNC failed to start):"
echo "   sudo systemctl status vncserver     # Check service status"
echo "   sudo journalctl -u vncserver -f    # View service logs"
echo "   sudo systemctl restart vncserver   # Restart VNC service"
echo "   tigervncserver :1                  # Start manually for testing"
echo "   tigervncserver -kill :1            # Stop manual session"
echo ""
echo "🔧 VNC Requirements:"
echo "   sudo apt-get install xfce4 xfce4-goodies  # Install XFCE4 desktop"
echo "   which startxfce4                   # Verify XFCE4 is available"
echo ""
echo "📱 Android Device Control:"
echo "   adb version                        # Verify ADB is available"
echo "   adb devices                        # List connected Android devices"
echo "   # Note: ADB is automatically installed by install_requirements.sh"
echo ""
echo "🔥 Firewall Configuration:"
echo "   sudo ufw status                    # Check UFW firewall status"
echo "   sudo ufw allow <port>              # Open specific port if needed"
echo "   # Note: UFW is automatically installed and ports are opened during launch"
echo ""
echo "🌐 Network Protocol Detection:"
echo "   # System automatically detects local installations and uses HTTP instead of HTTPS"
echo "   # Local IPs (192.168.x.x, 10.x.x.x, etc.) are auto-converted from HTTPS to HTTP"
echo "   # This prevents SSL connection errors in local development environments"
echo ""
echo "🔧 Advanced VNC Troubleshooting (if needed):"
echo "   # Manual display settings (usually not needed):"
echo "   export DISPLAY=:1"
echo "   export XAUTHORITY=~/.Xauthority"
echo "   xhost +local:"
echo "   xrandr -display :1 -s 1280x720"

echo ""
echo "🚀 Launch VirtualPyTest:"
echo "   ./scripts/launch_virtualpytest.sh           - Start complete system"
echo "   ./scripts/launch_virtualpytest.sh --discard - Start with AI Discard service"
echo ""
echo "🔧 Individual Services:"
echo "   ./setup/local/launch_server.sh     - Backend server only"
echo "   ./setup/local/launch_host.sh       - Backend host only"  
echo "   ./setup/local/launch_frontend.sh   - Frontend only"
echo ""
echo "🔧 Individual fresh installs:"
echo "   ./setup/local/install_db.sh --force-clean       - Fresh database only"
echo "   ./setup/local/install_host_services.sh          - Fresh host services setup"

echo ""
echo "=================================================================="
echo "🎉 VirtualPyTest Installation Complete!"
echo "=================================================================="
echo ""
echo "🌐 Access URLs:"
echo "   📱 Frontend:        http://localhost:3000"
echo "   🖥️  Backend Server:  http://localhost:5109" 
echo "   🤖 Backend Host:     http://localhost:6109"
echo "   📊 Grafana:          http://localhost:3001"
echo "   🖥️  VNC Web:         http://localhost:6080"
echo ""
echo "🔧 Service Status:"

# Quick service status check at the end
services=("postgresql:PostgreSQL" "grafana-server:Grafana" "vncserver:VNC" "novnc:noVNC" "stream:Stream" "monitor:Monitor")
for service_info in "${services[@]}"; do
    IFS=':' read -r service_name display_name <<< "$service_info"
    if systemctl is-active --quiet "$service_name" 2>/dev/null; then
        echo "   ✅ $display_name: Running"
    elif systemctl is-enabled --quiet "$service_name" 2>/dev/null; then
        echo "   🟡 $display_name: Enabled (not running)"
    else
        echo "   ❌ $display_name: Not enabled"
    fi
done

echo ""
echo "🌐 Network Information:"
# Get device IP addresses
if command -v ip >/dev/null 2>&1; then
    # Use ip command (preferred on modern systems)
    DEVICE_IPS=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' 2>/dev/null || echo "")
    if [ -n "$DEVICE_IPS" ]; then
        echo "   📍 Primary IP: $DEVICE_IPS"
    fi
    
    # Show all network interfaces with IPs
    echo "   🔗 All Network Interfaces:"
    ip -4 addr show 2>/dev/null | grep -E "^\d+:|inet " | while read -r line; do
        if [[ $line =~ ^[0-9]+: ]]; then
            INTERFACE=$(echo "$line" | cut -d: -f2 | tr -d ' ')
            echo -n "      $INTERFACE: "
        elif [[ $line =~ inet ]]; then
            IP=$(echo "$line" | awk '{print $2}' | cut -d/ -f1)
            echo "$IP"
        fi
    done 2>/dev/null || echo "      Unable to detect network interfaces"
elif command -v ifconfig >/dev/null 2>&1; then
    # Fallback to ifconfig
    echo "   🔗 Network Interfaces (ifconfig):"
    ifconfig 2>/dev/null | grep -E "^[a-zA-Z0-9]+:" -A 1 | grep -E "inet |^[a-zA-Z0-9]+:" | while read -r line; do
        if [[ $line =~ ^[a-zA-Z0-9]+: ]]; then
            INTERFACE=$(echo "$line" | cut -d: -f1)
            echo -n "      $INTERFACE: "
        elif [[ $line =~ inet ]]; then
            IP=$(echo "$line" | awk '{print $2}' | sed 's/addr://')
            echo "$IP"
        fi
    done 2>/dev/null || echo "      Unable to detect network interfaces"
else
    echo "   ⚠️ Network detection tools not available (ip/ifconfig)"
fi

echo ""
echo "🚀 Ready to Launch:"
echo "   ./scripts/launch_virtualpytest.sh"
echo ""
echo "==================================================================" 