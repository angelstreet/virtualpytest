#!/bin/bash

# VirtualPyTest - Launch Hetzner Custom Deployment
# 1 Backend Server + 2 Backend Hosts

set -e

echo "🚀 Launching VirtualPyTest - Hetzner Custom (1 Server + 2 Hosts)"

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo ""
    echo "Please create .env file:"
    echo "  cp setup/docker/hetzner_custom/env.example .env"
    echo "  nano .env  # Edit with your configuration"
    exit 1
fi

# Launch services
echo "🐳 Starting services..."
docker-compose --env-file .env -f setup/docker/hetzner_custom/docker-compose.yml up -d

# Show status
echo ""
docker-compose --env-file .env -f setup/docker/hetzner_custom/docker-compose.yml ps

echo ""
echo "🎉 Services started!"
echo ""
echo "📋 Access Points:"
echo "   Backend Server:  http://localhost:5109"
echo "   Grafana:         http://localhost:3000"
echo "   Backend Host 1:  http://localhost:6109"
echo "   Backend Host 2:  http://localhost:6110"
echo ""
echo "📊 View logs:  docker-compose --env-file .env -f setup/docker/hetzner_custom/docker-compose.yml logs -f"
echo "🛑 Stop:       docker-compose --env-file .env -f setup/docker/hetzner_custom/docker-compose.yml down"
