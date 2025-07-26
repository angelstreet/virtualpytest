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

# Verify installation
echo "✅ Verifying installation..."
docker --version
docker compose version

echo ""
echo "🎉 Docker installation completed!"
echo "⚠️  Please log out and log back in (or restart) for group changes to take effect."
echo "🚀 Then you can run: ./setup/launch_all.sh" 