#!/bin/bash

# VirtualPyTest Launch Script - Real-time Unified Logging
echo "🚀 Starting VirtualPyTest System with Real-time Unified Logging..."

# Get the script directory and navigate to the correct paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "$(dirname "$SCRIPT_DIR")")" && pwd)"
SERVER_DIR="$PROJECT_ROOT/backend_server/src"
HOST_DIR="$PROJECT_ROOT/backend_host/src"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "📁 Script directory: $SCRIPT_DIR"
echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Server directory: $SERVER_DIR"
echo "📁 Host directory: $HOST_DIR"
echo "📁 Frontend directory: $FRONTEND_DIR"

# Detect Python executable
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ No Python executable found!"
    exit 1
fi
echo "🐍 Using Python: $PYTHON_CMD"

# Check if we have a virtual environment to activate
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo "🐍 Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
elif [ -f "$HOME/myvenv/bin/activate" ]; then
    echo "🐍 Activating virtual environment from home..."
    source "$HOME/myvenv/bin/activate"
else
    echo "⚠️  No virtual environment found, proceeding without activation"
fi

# Check directories exist
if [ ! -d "$SERVER_DIR" ]; then
    echo "❌ Server directory not found: $SERVER_DIR"
    exit 1
fi

if [ ! -d "$HOST_DIR" ]; then
    echo "❌ Host directory not found: $HOST_DIR"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

# Colors for different services
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Array to store background process PIDs
declare -a PIDS=()

# Function to run command with colored prefix and real-time output
run_with_prefix() {
    local prefix="$1"
    local color="$2"
    local directory="$3"
    shift 3
    
    cd "$directory"
    
    # Use exec to run command and pipe output with real-time processing
    {
        if [[ "$1" == "python" ]]; then
            # For Python, use -u flag for unbuffered output and the detected Python command
            exec $PYTHON_CMD -u "${@:2}" 2>&1
        elif [[ "$1" == "npm" ]]; then
            # For npm, set environment variables for unbuffered output
            exec env FORCE_COLOR=1 "$@" 2>&1
        else
            exec "$@" 2>&1
        fi
    } | {
        while IFS= read -r line; do
            printf "${color}[${prefix}]${NC} %s\n" "$line"
        done
    } &
    
    local pid=$!
    PIDS+=($pid)
    echo "Started $prefix with PID: $pid"
    
    # Return to project root
    cd "$PROJECT_ROOT"
}

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
echo "💡 Logs will appear with colored prefixes: [SERVER], [HOST], [FRONTEND]"
echo "=================================================================================="

# Start all services with prefixed output and real-time logging
echo -e "${BLUE}🔵 Starting Backend Server...${NC}"
run_with_prefix "SERVER" "$BLUE" "$SERVER_DIR" python app.py
sleep 3

echo -e "${GREEN}🟢 Starting Backend Host...${NC}"
run_with_prefix "HOST" "$GREEN" "$HOST_DIR" python app.py
sleep 3

echo -e "${YELLOW}🟡 Starting Frontend Dev Server...${NC}"
run_with_prefix "FRONTEND" "$YELLOW" "$FRONTEND_DIR" npm run dev

echo "=================================================================================="
echo -e "${NC}✅ All services started! Watching for logs...${NC}"
echo -e "${NC}💡 You should see logs with colored prefixes appearing below${NC}"
echo "=================================================================================="

# Wait for all background jobs
wait