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
echo "5️⃣ Installing frontend (smart update)..."
./setup/local/install_frontend.sh --smart-update

echo ""
echo "6️⃣ Installing Grafana for monitoring (smart update)..."
./setup/local/install_grafana.sh --smart-update

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
echo ""
echo "🚀 Launch VirtualPyTest:"
echo "   ./setup/local/launch_all.sh        - Start all services"
echo "   ./setup/local/launch_server.sh     - Start backend_server only"
echo "   ./setup/local/launch_host.sh       - Start backend_host only"  
echo "   ./setup/local/launch_frontend.sh   - Start frontend only"
echo ""
echo "🔧 Individual fresh installs:"
echo "   ./setup/local/install_db.sh --force-clean       - Fresh database only"
echo "   ./setup/local/install_host_services.sh          - Fresh host services setup" 