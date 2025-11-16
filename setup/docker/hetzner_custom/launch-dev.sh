#!/bin/bash
# VirtualPyTest - Launch Services (DEVELOPMENT MODE)
# Starts containers with source code mounted for rapid iteration
# Edit code locally → Changes reflect immediately → Just restart container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 VirtualPyTest - Launch Services (DEV MODE)"
echo "========================================="

# Check if setup was run
if [ ! -f "setup/docker/hetzner_custom/docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo ""
    echo "Run setup first:"
    echo "  cd setup/docker/hetzner_custom"
    echo "  ./setup.sh"
    exit 1
fi

# Check if dev compose exists
if [ ! -f "setup/docker/hetzner_custom/docker-compose.dev.yml" ]; then
    echo "❌ Error: docker-compose.dev.yml not found"
    echo ""
    echo "Run setup first:"
    echo "  cd setup/docker/hetzner_custom"
    echo "  ./setup.sh"
    exit 1
fi

# Check if main .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in project root"
    echo ""
    echo "Create .env file with your configuration:"
    echo "  cp setup/docker/hetzner_custom/env.example .env"
    echo "  nano .env"
    exit 1
fi

echo ""
echo "📦 DEV MODE: Source code will be mounted from host"
echo "   → Edit files locally"
echo "   → Changes reflect immediately" 
echo "   → Just restart containers to pick up changes"
echo ""

# Build images first (one-time, or when Dockerfile changes)
echo "🐳 Building images (if needed)..."
docker-compose --env-file .env \
    -f setup/docker/hetzner_custom/docker-compose.yml \
    -f setup/docker/hetzner_custom/docker-compose.dev.yml \
    build backend_host_base

echo ""
echo "🚀 Starting Docker containers with dev overrides..."
docker-compose --env-file .env \
    -f setup/docker/hetzner_custom/docker-compose.yml \
    -f setup/docker/hetzner_custom/docker-compose.dev.yml \
    up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Show status
echo ""
docker-compose --env-file .env \
    -f setup/docker/hetzner_custom/docker-compose.yml \
    -f setup/docker/hetzner_custom/docker-compose.dev.yml \
    ps

echo ""
echo "========================================="
echo "✅ Services Started (DEV MODE)!"
echo ""
echo "📦 Source Code Mounted:"
echo "   • shared/ → All containers"
echo "   • backend_server/src/ → backend_server"
echo "   • backend_host/src/ → All backend_host containers"
echo ""
echo "💡 Quick Restart After Code Changes:"
echo "   docker-compose -f setup/docker/hetzner_custom/docker-compose.yml restart backend_host_1"
echo "   docker-compose -f setup/docker/hetzner_custom/docker-compose.yml restart backend_server"
echo ""
echo "📋 Local Access:"
echo "   Backend Server:  http://localhost:5109"
echo "   Grafana:         http://localhost:3000"

# Show host ports dynamically
if [ -f "setup/docker/hetzner_custom/config.env" ]; then
    source setup/docker/hetzner_custom/config.env
    for i in $(seq 1 $HOST_MAX); do
        PORT=$((HOST_START_PORT + i - 1))
        echo "   Backend Host ${i}:   http://localhost:${PORT}"
    done
fi

echo ""
echo "🌐 Public Access (if nginx configured):"
if [ -f "setup/docker/hetzner_custom/config.env" ]; then
    source setup/docker/hetzner_custom/config.env
    echo "   API: https://${DOMAIN}"
    for i in $(seq 1 $HOST_MAX); do
        echo "   VNC Host ${i}: https://${DOMAIN}/host${i}/vnc/vnc_lite.html"
    done
fi

echo ""
echo "📊 View logs:"
echo "   docker-compose -f setup/docker/hetzner_custom/docker-compose.yml logs -f [service]"
echo ""
echo "🛑 Stop:"
echo "   docker-compose -f setup/docker/hetzner_custom/docker-compose.yml down"
echo ""

