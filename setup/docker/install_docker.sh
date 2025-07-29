#!/bin/bash

# VirtualPyTest - Docker Installation Script for Linux/Raspberry Pi
# This script installs Docker and Docker Compose

set -e

echo "🐳 Installing Docker for VirtualPyTest..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root (without sudo)"
    exit 1
fi

# Install Docker
echo "📦 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Add user to docker group
echo "👤 Adding user to docker group..."
sudo usermod -aG docker $USER

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
sudo apt update
sudo apt install -y docker-compose-plugin

# Also install standalone docker-compose for compatibility
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
echo "✅ Verifying installation..."
docker --version
docker compose version
docker-compose --version

echo ""
echo "🎉 Docker installation completed!"
echo "🔧 Applying group changes immediately..."

# Apply group changes without logout/login
sudo systemctl restart docker
newgrp docker << EOF
echo "✅ Group changes applied successfully!"
echo "🚀 Testing Docker access..."
docker --version
EOF

echo ""
echo "🎉 Setup complete! You can now run:"
echo "   ./setup/docker/launch_all.sh - Start all services with Docker"
echo ""  
echo "💡 Service Configuration:"
echo "   - Backend Host auto-detects services from .env configuration"
echo "   - Minimal: Only VNC services (no DEVICE* variables needed)"
echo "   - Full: Add DEVICE*_VIDEO variables for video capture + monitoring"
echo "   - Config file: backend_host/src/.env"
echo ""
echo "💡 For local development without Docker, use:"
echo "   ./setup/local/install_local.sh - Install for local development"
echo "   ./setup/local/launch_all.sh - Run all services locally" 