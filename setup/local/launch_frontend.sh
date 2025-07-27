#!/bin/bash

# VirtualPyTest - Launch Frontend with Real-time Logs
echo "⚛️ Starting VirtualPyTest Frontend with Real-time Logs..."

set -e

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

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
    exit 0
fi

# Colors for output
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo -e "\n${RED}🛑 Shutting down frontend...${NC}"
    if [ -f /tmp/frontend.pid ]; then
        PID=$(cat /tmp/frontend.pid)
        if kill -0 "$PID" 2>/dev/null; then
            kill -TERM "$PID" 2>/dev/null
            sleep 2
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID" 2>/dev/null
            fi
        fi
        rm -f /tmp/frontend.pid
    fi
    echo -e "${RED}✅ Frontend stopped${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "📺 Starting frontend with real-time logging..."
echo "💡 Press Ctrl+C to stop"
echo "=================================================================================="

# Start frontend with real-time output
cd frontend
echo -e "${YELLOW}🟡 Starting Frontend...${NC}"

# Start the process and capture PID
env FORCE_COLOR=1 npm run dev 2>&1 | {
    while IFS= read -r line; do
        printf "${YELLOW}[FRONTEND]${NC} %s\n" "$line"
    done
} &

FRONTEND_PID=$!
echo $FRONTEND_PID > /tmp/frontend.pid

echo "Started Frontend with PID: $FRONTEND_PID"
echo "🌐 Frontend: http://localhost:3000"
echo "💡 Logs will appear with [FRONTEND] prefix below"
echo "=================================================================================="

# Wait for the process
wait $FRONTEND_PID