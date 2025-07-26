#!/bin/bash

# VirtualPyTest - Fix Docker Compose Installation
# This script fixes Docker Compose on systems where Docker is already installed

set -e

echo "🔧 Fixing Docker Compose installation..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please run: ./setup/install_docker.sh"
    exit 1
fi

echo "✅ Docker is installed"

# Check if docker compose (modern) works
if docker compose version &> /dev/null; then
    echo "✅ Modern Docker Compose (docker compose) is working"
else
    echo "⚠️  Modern Docker Compose not working, installing plugin..."
    sudo apt update
    sudo apt install -y docker-compose-plugin
fi

# Check if docker-compose (legacy) works
if command -v docker-compose &> /dev/null; then
    echo "✅ Legacy Docker Compose (docker-compose) is available"
else
    echo "⚠️  Legacy Docker Compose not found, installing standalone version..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

echo ""
echo "🎉 Docker Compose setup completed!"
echo "✅ Testing both versions:"

# Test both versions
docker --version
if docker compose version &> /dev/null; then
    docker compose version
else
    echo "❌ docker compose not working"
fi

if docker-compose --version &> /dev/null; then
    docker-compose --version
else
    echo "❌ docker-compose not working"
fi

echo ""
echo "🚀 You can now run: ./setup/launch_all.sh" 