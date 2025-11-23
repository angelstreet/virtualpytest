#!/bin/bash
# VirtualPyTest - One-Click Quickstart
# Installs Docker + Launches Standalone Environment

set -e

echo "🚀 VirtualPyTest Quickstart"
echo "==========================="

# 1. Check/Install Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing..."
    chmod +x setup/docker/install_docker.sh
    ./setup/docker/install_docker.sh
    
    echo ""
    echo "⚠️  Docker installed! You may need to log out and back in for group changes."
    echo "   Trying to continue..."
else
    echo "✅ Docker is already installed"
fi

# 2. Launch Standalone Environment
echo ""
echo "🚀 Launching Standalone Environment..."
echo "   (1 Server + 1 Host + Frontend + Database)"
echo ""

# Ensure launch script is executable
chmod +x setup/docker/standalone_server_host/launch.sh

# Launch
./setup/docker/standalone_server_host/launch.sh

