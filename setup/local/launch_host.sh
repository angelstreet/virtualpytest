#!/bin/bash

# VirtualPyTest - Launch Backend-Host Only
# This script starts only the backend-host in the background

set -e

echo "🔧 Launching VirtualPyTest - Backend-Host Only"

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-host" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: ./setup/local/install_host.sh"
    exit 1
fi

# Check if process is already running
if pgrep -f "python.*backend-host.*app.py" > /dev/null; then
    echo "⚠️  Backend-host is already running!"
    echo "🛑 To stop: ./setup/local/stop_all_local.sh"
    echo "📊 To view logs: tail -f /tmp/backend_host.log"
    exit 0
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Set up environment variables
export PYTHONPATH="$PROJECT_ROOT/shared/lib:$PROJECT_ROOT/backend-core/src"

# Start backend-host in background
echo "🚀 Starting backend-host..."
cd backend-host
nohup python3 src/app.py > /tmp/backend_host.log 2>&1 &
HOST_PID=$!

# Save PID for later cleanup
echo $HOST_PID > /tmp/backend_host.pid

# Wait a moment and check if it started
sleep 3

if ps -p $HOST_PID > /dev/null; then
    echo "✅ Backend-host started successfully (PID: $HOST_PID)"
    echo "🌐 Backend-Host: http://localhost:6109"
    echo "📊 Log file: /tmp/backend_host.log"
    echo "🛑 To stop: ./setup/local/stop_all_local.sh"
    echo ""
    echo "📊 Recent logs:"
    tail -10 /tmp/backend_host.log
else
    echo "❌ Failed to start backend-host"
    echo "📊 Error logs:"
    cat /tmp/backend_host.log
    exit 1
fi