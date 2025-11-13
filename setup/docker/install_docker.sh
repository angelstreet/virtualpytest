#!/bin/bash

# VirtualPyTest - Docker Installation Script for Linux/Raspberry Pi
# This script installs Docker and Docker Compose

set -e

# Set non-interactive mode for apt (works on both Ubuntu and Debian)
export DEBIAN_FRONTEND=noninteractive

echo "🐳 Installing Docker for VirtualPyTest..."

# Detect if running as root
if [ "$EUID" -eq 0 ]; then
    echo "ℹ️  Running as root user"
    SUDO=""
    DOCKER_USER="root"
else
    echo "ℹ️  Running as non-root user (will use sudo)"
    SUDO="sudo"
    DOCKER_USER="$USER"
fi

# Install Docker
echo "📦 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
$SUDO sh get-docker.sh
rm get-docker.sh

# Add user to docker group (skip if root)
if [ "$EUID" -ne 0 ]; then
    echo "👤 Adding user to docker group..."
    $SUDO usermod -aG docker $USER
fi

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
$SUDO apt update
$SUDO apt install -y docker-compose-plugin

# Also install standalone docker-compose for compatibility
$SUDO curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
$SUDO chmod +x /usr/local/bin/docker-compose

# Verify installation
echo "✅ Verifying installation..."
docker --version
docker compose version
docker-compose --version

echo ""
echo "🎉 Docker installation completed!"

# Install Cloudflared for HTTPS tunnel
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  Installing Cloudflared..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$SUDO mkdir -p /usr/local/bin
$SUDO curl -L --output /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
$SUDO chmod +x /usr/local/bin/cloudflared

echo "✅ Cloudflared installed"

# Setup cloudflared systemd service
if [ -f "setup/docker/hetzner_custom/cloudflared.service" ]; then
    echo "⚙️  Setting up Cloudflared service..."
    $SUDO cp setup/docker/hetzner_custom/cloudflared.service /etc/systemd/system/
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable cloudflared
    echo "✅ Cloudflared service configured (needs tunnel setup before starting)"
fi

# Apply group changes for non-root users
if [ "$EUID" -ne 0 ]; then
    echo "🔧 Applying group changes immediately..."
    $SUDO systemctl restart docker
    newgrp docker << EOF
echo "✅ Group changes applied successfully!"
echo "🚀 Testing Docker access..."
docker --version
EOF
else
    echo "✅ Restarting Docker service..."
    systemctl restart docker
fi

echo ""
echo "🎉 Setup complete! You can now run:"
echo ""
echo "📦 Deployment Options:"
echo "   Standalone:     ./setup/docker/standalone_server_host/launch.sh"
echo "   Hetzner Custom: ./setup/docker/hetzner_custom/launch.sh"
echo ""
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Note: You may need to log out and back in for docker group changes to take effect"
    echo "    Or run: newgrp docker"
fi 