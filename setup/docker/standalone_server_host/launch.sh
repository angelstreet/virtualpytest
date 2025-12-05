#!/bin/bash

# VirtualPyTest - Launch Standalone Complete System
# Everything included: Database + Backend Services + Frontend + Monitoring

set -e

echo "🚀 Launching VirtualPyTest - Standalone Complete System"

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

# Start services
echo "🐳 Starting VirtualPyTest Standalone (Complete Local System)..."
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml up -d

# Wait for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check service status
echo "🔍 Checking service status..."
docker-compose -f setup/docker/standalone_server_host/docker-compose.yml ps

echo ""
echo "🎉 VirtualPyTest Standalone is starting up!"
echo ""
echo "📋 Services Running:"
echo "   ✅ PostgreSQL Database (Main Application Data)"
echo "   ✅ Grafana Metrics Database (Monitoring Data)"
echo "   ✅ Backend Server (API + Grafana)"
echo "   ✅ Backend Host (Device Controller)"
echo "   ✅ Frontend (React Web Interface)"
echo ""
echo "📋 Access Points:"
echo "   🌐 Web Interface:            http://localhost:3000"
echo "   🖥️  Backend Server API:      http://localhost:5109"
echo "   📊 Grafana Monitoring:       http://localhost:3001"
echo "   🔗 Grafana (Integrated):     http://localhost:5109/grafana"
echo "   🔍 Langfuse (if installed):  http://localhost:3001 or /langfuse/"
echo "   🎮 Backend Host:             http://localhost:6109"
echo "   🗄️  PostgreSQL Database:     localhost:5432"
echo "   📊 Grafana Metrics DB:       localhost:5433"
echo ""
echo "📋 Default Credentials:"
echo "   🗄️  PostgreSQL:"
echo "      Database: virtualpytest"
echo "      User: virtualpytest_user"
echo "      Password: virtualpytest_pass"
echo ""
echo "   📊 Grafana:"
echo "      User: admin"
echo "      Password: admin123"
echo ""
echo "📋 What's Included:"
echo "   ✅ Complete local development environment"
echo "   ✅ No external dependencies required"
echo "   ✅ All data stored in Docker volumes"
echo "   ✅ Auto-initialized database schema"
echo ""
echo "🔧 Useful Commands:"
echo "   📊 View logs:    docker-compose -f setup/docker/standalone_server_host/docker-compose.yml logs -f"
echo "   🛑 Stop all:     docker-compose -f setup/docker/standalone_server_host/docker-compose.yml down"
echo "   🔄 Restart:      docker-compose -f setup/docker/standalone_server_host/docker-compose.yml restart"
echo "   🗑️  Clean all:    docker-compose -f setup/docker/standalone_server_host/docker-compose.yml down -v"
echo ""
echo "📖 Documentation: setup/docker/standalone_server_host/README.md"

