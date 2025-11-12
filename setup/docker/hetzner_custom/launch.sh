#!/bin/bash

# VirtualPyTest - Launch Hetzner Custom Deployment
# 1 Backend Server + 2 Backend Hosts

set -e

echo "🚀 Launching VirtualPyTest - Hetzner Custom (1 Server + 2 Hosts)"

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

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
    echo "❌ Error: .env file not found in project root"
    echo "📝 Please create .env file with required configuration"
    echo "💡 Copy template: cp setup/docker/hetzner_custom/env.server.example .env"
    exit 1
fi

# Check for required environment variables
echo "🔍 Checking configuration..."
MISSING_VARS=()

if ! grep -q "SUPABASE_DB_URI" .env; then
    MISSING_VARS+=("SUPABASE_DB_URI")
fi

if ! grep -q "GRAFANA_ADMIN_PASSWORD" .env; then
    MISSING_VARS+=("GRAFANA_ADMIN_PASSWORD")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "⚠️  Warning: Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo "💡 Copy template: cp setup/docker/hetzner_custom/env.server.example .env"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start services
echo "🐳 Starting VirtualPyTest Hetzner Custom (1 Server + 2 Hosts)..."
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml up -d

# Wait for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check service status
echo "🔍 Checking service status..."
docker-compose -f setup/docker/hetzner_custom/docker-compose.yml ps

echo ""
echo "🎉 VirtualPyTest Hetzner Custom is starting up!"
echo ""
echo "📋 Services Running:"
echo "   ✅ Backend Server (API + Grafana)"
echo "   ✅ Backend Host 1 (Device Controller)"
echo "   ✅ Backend Host 2 (Device Controller)"
echo ""
echo "📋 Access Points:"
echo "   🖥️  Backend Server API:      http://localhost:5109"
echo "   📊 Grafana Monitoring:       http://localhost:3000"
echo "   🔗 Grafana (Integrated):     http://localhost:5109/grafana"
echo "   🎮 Backend Host 1:           http://localhost:6109"
echo "   🎮 Backend Host 2:           http://localhost:6110"
echo ""
echo "📋 External Dependencies:"
echo "   🗄️  Supabase Database - Configured in .env"
echo "   🌐 Frontend - Deploy separately"
echo ""
echo "🔧 Useful Commands:"
echo "   📊 View logs:    docker-compose -f setup/docker/hetzner_custom/docker-compose.yml logs -f"
echo "   🛑 Stop all:     docker-compose -f setup/docker/hetzner_custom/docker-compose.yml down"
echo "   🔄 Restart:      docker-compose -f setup/docker/hetzner_custom/docker-compose.yml restart"
echo ""
echo "📖 Documentation: setup/docker/hetzner_custom/README.md"

