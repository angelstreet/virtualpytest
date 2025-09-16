#!/bin/bash

# VirtualServer Launch Script - Server and Frontend Only
# Usage: ./launch_virtualserver.sh
# Launches backend_server and frontend components only (no host services)

echo "🚀 Starting VirtualServer (Server + Frontend only)..."

set -e

# Get the script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    exit 1
fi

# Check if launch scripts exist
LAUNCH_SERVER="$PROJECT_ROOT/setup/local/launch_server.sh"
LAUNCH_FRONTEND="$PROJECT_ROOT/setup/local/launch_frontend.sh"

if [ ! -f "$LAUNCH_SERVER" ]; then
    echo "❌ Launch server script not found: $LAUNCH_SERVER"
    exit 1
fi

if [ ! -f "$LAUNCH_FRONTEND" ]; then
    echo "❌ Launch frontend script not found: $LAUNCH_FRONTEND"
    exit 1
fi

# Make sure the scripts are executable
chmod +x "$LAUNCH_SERVER"
chmod +x "$LAUNCH_FRONTEND"

# Array to store background process PIDs
declare -a PIDS=()

# Enhanced cleanup function
cleanup() {
    echo -e "\n🛑 Shutting down all processes..."
    
    # Kill all background processes gracefully first
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping process $pid..."
            kill -TERM "$pid" 2>/dev/null
        fi
    done
    
    # Wait a moment for graceful shutdown
    sleep 3
    
    # Force kill any remaining processes
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force killing process $pid..."
            kill -9 "$pid" 2>/dev/null
        fi
    done
    
    # Kill any remaining background jobs
    jobs -p | xargs -r kill -9 2>/dev/null
    
    echo "✅ All processes stopped"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "🔄 Starting backend_server and frontend using existing launch scripts..."
echo "💡 Press Ctrl+C to stop all processes"
echo "=================================================================================="

# Start backend_server in background
echo "🔵 Starting backend_server..."
"$LAUNCH_SERVER" &
SERVER_PID=$!
PIDS+=($SERVER_PID)
echo "Started backend_server with PID: $SERVER_PID"

sleep 3

# Start frontend in background  
echo "🟡 Starting frontend..."
"$LAUNCH_FRONTEND" &
FRONTEND_PID=$!
PIDS+=($FRONTEND_PID)
echo "Started frontend with PID: $FRONTEND_PID"

echo "=================================================================================="
echo "✅ Both processes started!"
echo "🌐 URLs:"
echo "   backend_server: http://localhost:5109"
echo "   Frontend: Check frontend logs for actual port (usually http://localhost:3000)"
echo "   Grafana (built-in): http://localhost:5109/grafana/"
echo "=================================================================================="

# Wait for all background jobs
wait
