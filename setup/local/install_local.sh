#!/bin/bash

# VirtualPyTest - Install All Local Dependencies
# This script installs all dependencies for local development

set -e

echo "🔧 Setting up VirtualPyTest for local development..."

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "shared" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Make all install scripts executable
chmod +x setup/local/install_*.sh

echo "🚀 Installing all components..."

# Install individual components
echo "1️⃣ Installing shared library..."
./setup/local/install_shared.sh

echo ""
echo "2️⃣ Installing backend-server..."
./setup/local/install_server.sh

echo ""
echo "3️⃣ Installing backend-host..."
./setup/local/install_host.sh

echo ""
echo "4️⃣ Installing frontend..."
./setup/local/install_frontend.sh

echo ""
echo "🎉 All components installed successfully!"
echo ""
echo "🚀 You can now run services locally:"
echo "   ./setup/local/launch_all_local.sh - Start all services locally (recommended)"
echo "   ./setup/local/launch_server.sh    - Start backend-server only"
echo "   ./setup/local/launch_host.sh      - Start backend-host only"  
echo "   ./setup/local/launch_frontend.sh  - Start frontend only"
echo ""
echo "🔧 Individual component installation:"
echo "   ./setup/local/install_shared.sh      - Install shared library only"
echo "   ./setup/local/install_server.sh      - Install backend-server only"
echo "   ./setup/local/install_host.sh        - Install backend-host only"
echo "   ./setup/local/install_frontend.sh    - Install frontend only"
echo ""
echo "🏠 Host services setup (for Raspberry Pi):"
echo "   ./setup/local/install_host_services.sh - Full host services setup"
echo ""
echo "🐳 Or use Docker deployment:"
echo "   ./setup/docker/launch_all.sh      - Start all services with Docker" 