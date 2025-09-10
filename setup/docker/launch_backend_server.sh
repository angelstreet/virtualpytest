#!/bin/bash

# VirtualPyTest - Launch Backend Server Only
# This script starts only the backend server (API + Grafana) - requires external Supabase

set -e

echo "🚀 Launching VirtualPyTest - Backend Server Only"

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
    echo "📝 You'll need to configure environment variables for Supabase connection"
    echo "💡 See setup/docker/docker.md for configuration details"
    echo ""
fi

# Check for required environment variables
echo "🔍 Checking configuration..."
if [ -z "$SUPABASE_DB_URI" ] && [ -f ".env" ]; then
    if ! grep -q "SUPABASE_DB_URI" .env; then
        echo "⚠️  Warning: SUPABASE_DB_URI not found in .env file"
        echo "📝 Backend server requires Supabase database connection"
        echo "💡 See setup/docker/docker.md for configuration details"
        echo ""
    fi
fi

# Start the backend server
echo "🐳 Starting VirtualPyTest Backend Server..."
docker-compose -f setup/docker/docker-compose.backend-server.yml up -d

# Wait a moment for service to start
echo "⏳ Waiting for service to initialize..."
sleep 5

# Check if service is running
echo "🔍 Checking service status..."
docker-compose -f setup/docker/docker-compose.backend-server.yml ps

echo ""
echo "🎉 VirtualPyTest Backend Server is starting up!"
echo ""
echo "📋 Access Points:"
echo "   🖥️  Backend Server API:  http://localhost:5109"
echo "   📊 Grafana Monitoring:  http://localhost:3001"
echo "   🔗 Grafana (Integrated): http://localhost:5109/grafana"
echo ""
echo "📋 What's Running:"
echo "   ✅ Backend Server (API + Grafana monitoring)"
echo "   ✅ Shared library (included in container)"
echo ""
echo "📋 External Dependencies Required:"
echo "   🗄️  Supabase Database - Configure in .env file"
echo "   🌐 Frontend - Deploy separately (Vercel, Netlify, etc.)"
echo "   🔧 Backend Host - Deploy separately for device control"
echo ""
echo "🔧 Useful Commands:"
echo "   📊 View logs:    docker-compose -f setup/docker/docker-compose.backend-server.yml logs -f"
echo "   🛑 Stop server:  docker-compose -f setup/docker/docker-compose.backend-server.yml down"
echo "   🔄 Restart:     docker-compose -f setup/docker/docker-compose.backend-server.yml restart"
echo ""
echo "⚙️  Configuration:"
echo "   📝 Edit .env file to configure Supabase connection"
echo "   📖 See setup/docker/docker.md for detailed configuration guide"
echo "   🔗 Connect your frontend to: http://localhost:5109"
