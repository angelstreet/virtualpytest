#!/bin/bash

# VirtualPyTest - Launch All Services (Docker)
# This script starts all services using Docker Compose

set -e

echo "🚀 Launching VirtualPyTest - All Services (Docker)"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "docker" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please run: ./setup/docker/install_docker.sh"
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please run: ./setup/docker/install_docker.sh"
    exit 1
fi

# Navigate to docker directory
cd docker

# Make deploy script executable
chmod +x scripts/deploy.sh

# Deploy development environment
echo "🐳 Starting Docker services..."
./scripts/deploy.sh development

echo ""
echo "🎉 All services are starting up!"
echo "📱 Frontend: http://localhost:3000"
echo "🖥️  backend_server: http://localhost:5109"  
echo "🔧 backend_host: http://localhost:6109"
echo "🖥️  NoVNC (Virtual Desktop): http://localhost:6080"
echo ""
echo "📊 To view logs: docker compose -f docker-compose.yml logs -f"
echo "🛑 To stop: docker compose -f docker-compose.yml down"
echo ""
echo "💡 Backend Host Configuration:"
echo "   - Minimal config: Only VNC services (no .env DEVICE* variables)"
echo "   - Full config: Add DEVICE*_VIDEO variables to enable video capture + monitoring"
echo "   - Config file: backend_host/src/.env" 