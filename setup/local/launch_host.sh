#!/bin/bash

# VirtualPyTest - Launch Backend-Host with Real-time Logs
echo "🔧 Starting VirtualPyTest Backend-Host with Real-time Logs..."

set -e

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

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

# Kill any process using port 6409
echo "🔍 Checking for processes using port 6409..."
if lsof -ti:6409 > /dev/null 2>&1; then
    echo "🛑 Killing processes on port 6409..."
    lsof -ti:6409 | xargs kill -9 2>/dev/null || true
    sleep 1
fi
echo "✅ Port 6409 is available"

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

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Set up environment variables
export PYTHONPATH="$PROJECT_ROOT/shared/lib:$PROJECT_ROOT/backend-core/src"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo -e "\n${RED}🛑 Shutting down backend-host...${NC}"
    if [ -f /tmp/backend_host.pid ]; then
        PID=$(cat /tmp/backend_host.pid)
        if kill -0 "$PID" 2>/dev/null; then
            kill -TERM "$PID" 2>/dev/null
            sleep 2
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID" 2>/dev/null
            fi
        fi
        rm -f /tmp/backend_host.pid
    fi
    echo -e "${RED}✅ Backend-host stopped${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "📺 Starting backend-host with real-time logging..."
echo "💡 Press Ctrl+C to stop"
echo "=================================================================================="

# Start backend-host with real-time output
cd backend-host
echo -e "${GREEN}🟢 Starting Backend-Host...${NC}"

# Start the process and capture PID
$PYTHON_CMD -u src/app.py 2>&1 | {
    while IFS= read -r line; do
        printf "${GREEN}[HOST]${NC} %s\n" "$line"
    done
} &

HOST_PID=$!
echo $HOST_PID > /tmp/backend_host.pid

echo "Started Backend-Host with PID: $HOST_PID"
echo "🌐 Backend-Host: http://localhost:6109"
echo "💡 Logs will appear with [HOST] prefix below"
echo "=================================================================================="

# Wait for the process
wait $HOST_PID