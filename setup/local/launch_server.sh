#!/bin/bash

# VirtualPyTest - Launch backend_server with Real-time Logs
echo "🖥️ Starting VirtualPyTest backend_server with Real-time Logs..."

set -e

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend_server" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: ./setup/local/install_server.sh"
    exit 1
fi

# Source port checking functions
source "$PROJECT_ROOT/setup/local/check_and_open_port.sh"

# Get SERVER_PORT from environment (check .env file or use default)
SERVER_ENV_FILE="$PROJECT_ROOT/.env"
SERVER_PORT=$(get_port_from_env "$SERVER_ENV_FILE" "SERVER_PORT" "5109")

echo "📋 Backend Server Configuration:"
echo "   Port: $SERVER_PORT (from $SERVER_ENV_FILE)"
echo "   Service: backend_server"

# Check port availability and kill conflicting processes
check_port_availability "$SERVER_PORT" "backend_server"

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
export PYTHONPATH="$PROJECT_ROOT/shared/lib:$PROJECT_ROOT/backend_host/src"

# Check if Redis is running (required for Event Bus)
echo "🔍 Checking Redis status..."
if command -v redis-cli &> /dev/null; then
    if ! redis-cli ping &> /dev/null; then
        echo "⚠️  Redis is not running. The agent system requires Redis for the Event Bus."
        echo "🚀 Starting Redis..."
        
        # Try to start Redis based on OS
        if command -v systemctl &> /dev/null; then
            # Linux with systemd
            echo "Using systemctl to start Redis..."
            sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null
            sleep 2
            if redis-cli ping &> /dev/null; then
                echo "✅ Redis started successfully"
                # Enable to start on boot
                sudo systemctl enable redis-server 2>/dev/null || sudo systemctl enable redis 2>/dev/null
            else
                echo "❌ Failed to start Redis via systemctl"
                exit 1
            fi
        elif command -v service &> /dev/null; then
            # Linux with service command
            echo "Using service command to start Redis..."
            sudo service redis-server start 2>/dev/null || sudo service redis start 2>/dev/null
            sleep 2
            if redis-cli ping &> /dev/null; then
                echo "✅ Redis started successfully"
            else
                echo "❌ Failed to start Redis via service"
                exit 1
            fi
        elif command -v redis-server &> /dev/null; then
            # Start Redis directly in background
            redis-server --daemonize yes
            sleep 2
            if redis-cli ping &> /dev/null; then
                echo "✅ Redis started successfully"
            else
                echo "❌ Failed to start Redis"
                exit 1
            fi
        else
            echo "❌ Could not start Redis. Please start it manually:"
            echo "   sudo systemctl start redis-server"
            echo "   OR: redis-server --daemonize yes"
            exit 1
        fi
    else
        echo "✅ Redis is running"
    fi
else
    echo "❌ Redis is not installed. The agent system requires Redis."
    echo "   Install with:"
    echo "   - Ubuntu/Debian: sudo apt-get install redis-server"
    echo "   - RHEL/CentOS:   sudo yum install redis"
    echo "   - Fedora:        sudo dnf install redis"
    echo "   Then start with: sudo systemctl start redis-server"
    exit 1
fi

# Colors for output
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo -e "\n${RED}🛑 Shutting down backend_server...${NC}"
    if [ -f /tmp/backend_server.pid ]; then
        PID=$(cat /tmp/backend_server.pid)
        if kill -0 "$PID" 2>/dev/null; then
            kill -TERM "$PID" 2>/dev/null
            sleep 2
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID" 2>/dev/null
            fi
        fi
        rm -f /tmp/backend_server.pid
    fi
    echo -e "${RED}✅ backend_server stopped${NC}"
    
    # Note: Redis is left running as it may be used by other services
    # To stop Redis manually: sudo systemctl stop redis-server (or redis-cli shutdown)
    
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "📺 Starting backend_server with real-time logging..."
echo "💡 Press Ctrl+C to stop"
echo "=================================================================================="

# Start backend_server with real-time output
cd backend_server
echo -e "${BLUE}🔵 Starting backend_server...${NC}"

# Start the process and capture PID
$PYTHON_CMD -u src/app.py 2>&1 | {
    while IFS= read -r line; do
        printf "${BLUE}[SERVER]${NC} %s\n" "$line"
    done
} &

SERVER_PID=$!
echo $SERVER_PID > /tmp/backend_server.pid

echo "Started backend_server with PID: $SERVER_PID"
echo "🌐 backend_server: http://localhost:$SERVER_PORT"
echo "💡 Logs will appear with [SERVER] prefix below"
echo "=================================================================================="

# Wait for the process
wait $SERVER_PID