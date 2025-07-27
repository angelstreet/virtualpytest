#!/bin/bash

# VirtualPyTest - Launch Frontend Only
# This script starts only the frontend in the background

set -e

echo "⚛️ Launching VirtualPyTest - Frontend Only"

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "frontend" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend dependencies not installed. Please run: ./setup/local/install_frontend.sh"
    exit 1
fi

# Check if process is already running
if pgrep -f "npm.*run.*dev" > /dev/null || pgrep -f "node.*vite" > /dev/null; then
    echo "⚠️  Frontend is already running!"
    echo "🛑 To stop: ./setup/local/stop_all_local.sh"
    echo "📊 To view logs: tail -f /tmp/frontend.log"
    exit 0
fi

# Start frontend in background
echo "🚀 Starting frontend development server..."
cd frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

# Save PID for later cleanup
echo $FRONTEND_PID > /tmp/frontend.pid

# Wait a moment and check if it started
sleep 5

if ps -p $FRONTEND_PID > /dev/null; then
    echo "✅ Frontend started successfully (PID: $FRONTEND_PID)"
    echo "🌐 Frontend: http://localhost:3000"
    echo "📊 Log file: /tmp/frontend.log"
    echo "🛑 To stop: ./setup/local/stop_all_local.sh"
    echo ""
    echo "📊 Recent logs:"
    tail -10 /tmp/frontend.log
else
    echo "❌ Failed to start frontend"
    echo "📊 Error logs:"
    cat /tmp/frontend.log
    exit 1
fi