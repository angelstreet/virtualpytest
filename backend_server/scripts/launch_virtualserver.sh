#!/bin/bash

# VirtualPyTest Launch Script - Server + Frontend
echo "🚀 Starting VirtualPyTest Server + Frontend..."

# Get the script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📁 Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/README.md" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    exit 1
fi

# Check if required launch scripts exist
LAUNCH_SERVER_SCRIPT="$PROJECT_ROOT/setup/local/launch_server.sh"
LAUNCH_FRONTEND_SCRIPT="$PROJECT_ROOT/setup/local/launch_frontend.sh"

if [ ! -f "$LAUNCH_SERVER_SCRIPT" ]; then
    echo "❌ Server launch script not found: $LAUNCH_SERVER_SCRIPT"
    exit 1
fi

if [ ! -f "$LAUNCH_FRONTEND_SCRIPT" ]; then
    echo "❌ Frontend launch script not found: $LAUNCH_FRONTEND_SCRIPT"
    exit 1
fi

# Make sure the scripts are executable
chmod +x "$LAUNCH_SERVER_SCRIPT"
chmod +x "$LAUNCH_FRONTEND_SCRIPT"

# Colors for output
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Array to store background process PIDs
declare -a PIDS=()

# Enhanced cleanup function
cleanup() {
    echo -e "\n${RED}🛑 Shutting down all services...${NC}"
    
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
    
    echo -e "${RED}✅ All services stopped${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "📺 Starting services with real-time unified logging..."
echo "💡 Press Ctrl+C to stop all services"
echo "💡 Logs will appear with colored prefixes: [SERVER], [FRONTEND]"
echo "=================================================================================="

# Start server in background
echo -e "${BLUE}🔵 Starting Backend Server...${NC}"
"$LAUNCH_SERVER_SCRIPT" &
SERVER_PID=$!
PIDS+=($SERVER_PID)
echo "Started Server with PID: $SERVER_PID"
sleep 3

# Start frontend in background
echo -e "${YELLOW}🟡 Starting Frontend...${NC}"
"$LAUNCH_FRONTEND_SCRIPT" &
FRONTEND_PID=$!
PIDS+=($FRONTEND_PID)
echo "Started Frontend with PID: $FRONTEND_PID"

echo "=================================================================================="
echo -e "${NC}✅ All services started! Watching for logs...${NC}"
echo -e "${NC}💡 You should see logs with colored prefixes appearing above${NC}"
echo -e "${NC}🌐 URLs:${NC}"
echo -e "${NC}   Frontend: http://localhost:3000${NC}"
echo -e "${NC}   backend_server: http://localhost:5109${NC}"
echo "=================================================================================="

# Wait for all background jobs
wait