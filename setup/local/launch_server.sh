#!/bin/bash

# VirtualPyTest - Launch Backend-Server Only
# This script starts only the backend-server in the background

set -e

echo "🖥️ Launching VirtualPyTest - Backend-Server Only"

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-server" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: ./setup/local/install_server.sh"
    exit 1
fi

# Check if process is already running
if pgrep -f "python.*backend-server.*app.py" > /dev/null; then
    echo "⚠️  Backend-server is already running!"
    echo "🛑 To stop: ./setup/local/stop_all_local.sh"
    echo "📊 To view logs: tail -f /tmp/backend_server.log"
    exit 0
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Set up environment variables
export PYTHONPATH="$PROJECT_ROOT/shared/lib:$PROJECT_ROOT/backend-core/src"

# Start backend-server in background
echo "🚀 Starting backend-server..."
cd backend-server
nohup python3 src/app.py > /tmp/backend_server.log 2>&1 &
SERVER_PID=$!

# Save PID for later cleanup
echo $SERVER_PID > /tmp/backend_server.pid

# Wait a moment and check if it started
sleep 3

if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Backend-server started successfully (PID: $SERVER_PID)"
    echo "🌐 Backend-Server: http://localhost:5109"
    echo "📊 Log file: /tmp/backend_server.log"
    echo "🛑 To stop: ./setup/local/stop_all_local.sh"
    echo ""
    echo "📊 Recent logs:"
    tail -10 /tmp/backend_server.log
else
    echo "❌ Failed to start backend-server"
    echo "📊 Error logs:"
    cat /tmp/backend_server.log
    exit 1
fi