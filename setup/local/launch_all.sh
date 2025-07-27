#!/bin/bash

# VirtualPyTest - Launch All Services in Background
# This script starts all services in the background and shows combined logs

set -e

echo "🚀 Launching VirtualPyTest - All Services in Background"

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    exit 1
fi

# Check if all components are installed
MISSING_COMPONENTS=""

if [ ! -d "venv" ]; then
    MISSING_COMPONENTS="$MISSING_COMPONENTS venv"
fi

if [ ! -d "frontend/node_modules" ]; then
    MISSING_COMPONENTS="$MISSING_COMPONENTS frontend-deps"
fi

if [ -n "$MISSING_COMPONENTS" ]; then
    echo "❌ Missing components:$MISSING_COMPONENTS"
    echo "Please install all components first:"
    echo "   ./setup/local/install_local.sh"
    exit 1
fi

echo "🔄 Starting all services..."

# Launch backend-server
echo "1️⃣ Starting backend-server..."
./setup/local/launch_server.sh

# Small delay between services
sleep 2

# Launch backend-host
echo ""
echo "2️⃣ Starting backend-host..."
./setup/local/launch_host.sh

# Small delay between services
sleep 2

# Launch frontend
echo ""
echo "3️⃣ Starting frontend..."
./setup/local/launch_frontend.sh

# Wait for all services to fully start
sleep 3

# Check final status
echo ""
echo "📊 Final Service Status:"
ALL_RUNNING=true

# Check backend-server
if pgrep -f "python.*backend-server.*app.py" > /dev/null; then
    echo "✅ Backend-Server: running"
else
    echo "❌ Backend-Server: failed"
    ALL_RUNNING=false
fi

# Check backend-host
if pgrep -f "python.*backend-host.*app.py" > /dev/null; then
    echo "✅ Backend-Host: running"
else
    echo "❌ Backend-Host: failed"
    ALL_RUNNING=false
fi

# Check frontend
if pgrep -f "npm.*run.*dev" > /dev/null || pgrep -f "node.*vite" > /dev/null; then
    echo "✅ Frontend: running"
else
    echo "❌ Frontend: failed"
    ALL_RUNNING=false
fi

if [ "$ALL_RUNNING" = true ]; then
    echo ""
    echo "🎉 All services running successfully!"
    echo "📱 Frontend: http://localhost:3000"
    echo "🖥️  Backend-Server: http://localhost:5109" 
    echo "🔧 Backend-Host: http://localhost:6109"
    echo ""
    echo "📊 Log files:"
    echo "   Backend-Server: /tmp/backend_server.log"
    echo "   Backend-Host: /tmp/backend_host.log"
    echo "   Frontend: /tmp/frontend.log"
    echo ""
    echo "🛑 To stop all services: ./setup/local/stop_all_local.sh"
    echo "📊 To view live logs: tail -f /tmp/backend_server.log /tmp/backend_host.log /tmp/frontend.log"
else
    echo ""
    echo "💥 Some services failed to start!"
    echo "🔍 Check individual service logs:"
    echo "   Backend-Server: cat /tmp/backend_server.log"
    echo "   Backend-Host: cat /tmp/backend_host.log"
    echo "   Frontend: cat /tmp/frontend.log"
    exit 1
fi 