#!/bin/bash

# VirtualPyTest - Launch Standalone (Complete Local System)
# This script starts the complete VirtualPyTest system locally

set -e

echo "🚀 Launching VirtualPyTest - Standalone (Complete Local System)"

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

# Start the standalone system
echo "🐳 Starting complete VirtualPyTest system..."
docker-compose -f setup/docker/docker-compose.standalone.yml up -d

# Wait a moment for services to start
echo "⏳ Waiting for services to initialize..."
sleep 5

# Check if services are running
echo "🔍 Checking service status..."
docker-compose -f setup/docker/docker-compose.standalone.yml ps

echo ""
echo "🎉 VirtualPyTest Standalone system is starting up!"
echo ""
echo "📋 Access Points:"
echo "   🌐 Web Interface:      http://localhost:3000"
echo "   🖥️  Backend Server:     http://localhost:5109"
echo "   🔧 Backend Host:       http://localhost:6109"
echo "   📊 Grafana Monitoring: http://localhost:3001"
echo "   🗄️  PostgreSQL DB:      localhost:5432"
echo "   📈 Grafana Metrics DB: localhost:5433"
echo ""
echo "📋 What's Running:"
echo "   ✅ Complete local database with VirtualPyTest schema"
echo "   ✅ Backend Server (API + Grafana monitoring)"
echo "   ✅ Backend Host (Device controller)"
echo "   ✅ Frontend (React web interface)"
echo "   ✅ PostgreSQL (Application data)"
echo "   ✅ Grafana Metrics DB (Monitoring data)"
echo ""
echo "🔧 Useful Commands:"
echo "   📊 View logs:    docker-compose -f setup/docker/docker-compose.standalone.yml logs -f"
echo "   🛑 Stop system: docker-compose -f setup/docker/docker-compose.standalone.yml down"
echo "   🔄 Restart:     docker-compose -f setup/docker/docker-compose.standalone.yml restart"
echo ""
echo "💡 This is a complete self-contained system - no external dependencies needed!"
echo "🚀 Open http://localhost:3000 to start using VirtualPyTest!"
