#!/bin/bash

# VirtualPyTest - Launch Backend Host Only
# This script starts only the backend host (device controller) - connects to external backend server

set -e

echo "🚀 Launching VirtualPyTest - Backend Host Only"

# Get to project root directory (from setup/docker to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "setup/docker" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
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

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found in project root"
    echo "📝 You'll need to configure environment variables for backend server connection"
    echo "💡 See setup/docker/docker.md for configuration details"
    echo ""
fi

# Check for required environment variables
echo "🔍 Checking configuration..."
if [ -z "$SERVER_URL" ] && [ -f ".env" ]; then
    if ! grep -q "SERVER_URL" .env; then
        echo "⚠️  Warning: SERVER_URL not found in .env file"
        echo "📝 Backend host requires connection to backend server"
        echo "💡 Example: SERVER_URL=http://your-backend-server:5109"
        echo "💡 See setup/docker/docker.md for configuration details"
        echo ""
    fi
fi

# Check for hardware access
echo "🔍 Checking hardware access..."
if [ ! -d "/dev" ]; then
    echo "⚠️  Warning: /dev directory not accessible"
    echo "🔧 Hardware devices may not be available in container"
fi

# Start the backend host
echo "🐳 Starting VirtualPyTest Backend Host..."
docker-compose -f setup/docker/docker-compose.backend-host.yml up -d

# Wait a moment for service to start
echo "⏳ Waiting for service to initialize..."
sleep 5

# Check if service is running
echo "🔍 Checking service status..."
docker-compose -f setup/docker/docker-compose.backend-host.yml ps

echo ""
echo "🎉 VirtualPyTest Backend Host is starting up!"
echo ""
echo "📋 Access Points:"
echo "   🔧 Backend Host Controller: http://localhost:6109"
echo ""
echo "📋 What's Running:"
echo "   ✅ Backend Host (Device controller)"
echo "   ✅ Shared library (included in container)"
echo "   ✅ Hardware access (privileged container)"
echo ""
echo "📋 External Dependencies Required:"
echo "   🖥️  Backend Server - Configure SERVER_URL in .env file"
echo "   🗄️  Database Access - Via backend server or direct Supabase"
echo ""
echo "🔧 Hardware Configuration:"
echo "   📺 Video Devices: /dev/video* (HDMI capture cards)"
echo "   🔊 Audio Devices: /dev/snd/* (Audio capture)"
echo "   📡 Remote Control: IR blasters, network control"
echo ""
echo "🔧 Useful Commands:"
echo "   📊 View logs:    docker-compose -f setup/docker/docker-compose.backend-host.yml logs -f"
echo "   🛑 Stop host:    docker-compose -f setup/docker/docker-compose.backend-host.yml down"
echo "   🔄 Restart:     docker-compose -f setup/docker/docker-compose.backend-host.yml restart"
echo ""
echo "⚙️  Configuration:"
echo "   📝 Edit .env file to configure:"
echo "      • SERVER_URL - Backend server connection"
echo "      • HOST_NAME - Unique identifier for this host"
echo "      • DEVICE*_* - Hardware device configurations"
echo "   📖 See setup/docker/docker.md for detailed configuration guide"
echo ""
echo "💡 Perfect for Raspberry Pi deployments at hardware locations!"
