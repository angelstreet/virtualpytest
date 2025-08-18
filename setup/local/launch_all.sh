#!/bin/bash

# VirtualPyTest Launch Script - Real-time Unified Logging
# Usage: ./launch_all.sh [--discard]
#   --discard: Include the AI Discard Service (uses many tokens)

# Parse command line arguments
INCLUDE_DISCARD=false
for arg in "$@"; do
    case $arg in
        --discard)
            INCLUDE_DISCARD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--discard]"
            echo "  --discard    Include the AI Discard Service (uses many tokens)"
            echo "  -h, --help   Show this help message"
            exit 0
            ;;
        *)
            echo "❌ Unknown parameter: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$INCLUDE_DISCARD" = true ]; then
    echo "🚀 Starting VirtualPyTest System with Real-time Unified Logging (including AI Discard Service)..."
else
    echo "🚀 Starting VirtualPyTest System with Real-time Unified Logging (without AI Discard Service)..."
fi

set -e

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

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

if [ "$INCLUDE_DISCARD" = true ] && [ ! -d "backend_discard/src" ]; then
    MISSING_COMPONENTS="$MISSING_COMPONENTS backend_discard"
fi

if [ -n "$MISSING_COMPONENTS" ]; then
    echo "❌ Missing components:$MISSING_COMPONENTS"
    echo "Please install all components first:"
    echo "   ./setup/local/install_all.sh"
    exit 1
fi

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
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Set up environment variables
export PYTHONPATH="$PROJECT_ROOT/shared/lib:$PROJECT_ROOT/backend_core/src"

# Colors for different components
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
            # For Python, use -u flag for unbuffered output
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
    echo -e "\n${RED}🛑 Shutting down all processes...${NC}"
    
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
    
    # Clean up PID files
    rm -f /tmp/backend_server.pid /tmp/backend_host.pid /tmp/backend_discard.pid /tmp/frontend.pid
    
    echo -e "${RED}✅ All processes stopped${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Kill any processes using required ports
echo "🔍 Checking and clearing required ports..."

# Port 5109 (backend_server)
if lsof -ti:5109 > /dev/null 2>&1; then
    echo "🛑 Killing processes on port 5109..."
    lsof -ti:5109 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Port 6409 (backend_host)
if lsof -ti:6409 > /dev/null 2>&1; then
    echo "🛑 Killing processes on port 6409..."
    lsof -ti:6409 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Port 3000 (Frontend)
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "🛑 Killing processes on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Port for backend_discard (configurable via DISCARD_SERVER_PORT, default 6209)
if [ "$INCLUDE_DISCARD" = true ]; then
    DISCARD_PORT=${DISCARD_SERVER_PORT:-6209}
    if lsof -ti:$DISCARD_PORT > /dev/null 2>&1; then
        echo "🛑 Killing processes on port $DISCARD_PORT..."
        lsof -ti:$DISCARD_PORT | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
fi

echo "✅ All required ports are available"

echo "📺 Starting all processes with real-time unified logging..."
echo "💡 Press Ctrl+C to stop all processes"
if [ "$INCLUDE_DISCARD" = true ]; then
    echo "💡 Logs will appear with colored prefixes: [SERVER], [HOST], [DISCARD], [FRONTEND]"
else
    echo "💡 Logs will appear with colored prefixes: [SERVER], [HOST], [FRONTEND]"
fi
echo "=================================================================================="

# Start all processes with prefixed output and real-time logging
echo -e "${BLUE}🔵 Starting backend_server...${NC}"
run_with_prefix "SERVER" "$BLUE" "$PROJECT_ROOT/backend_server" python src/app.py
sleep 3

echo -e "${GREEN}🟢 Starting backend_host...${NC}"
run_with_prefix "HOST" "$GREEN" "$PROJECT_ROOT/backend_host" python src/app.py
sleep 3

echo -e "${YELLOW}🟡 Starting Frontend...${NC}"
run_with_prefix "FRONTEND" "$YELLOW" "$PROJECT_ROOT/frontend" npm run dev
sleep 3

if [ "$INCLUDE_DISCARD" = true ]; then
    echo -e "${RED}🔴 Starting backend_discard (AI analysis service)...${NC}"
    run_with_prefix "DISCARD" "$RED" "$PROJECT_ROOT/backend_discard" python src/app.py
fi

echo "=================================================================================="
echo -e "${NC}✅ All processes started! Watching for logs...${NC}"
echo -e "${NC}💡 You should see logs with colored prefixes appearing below${NC}"
echo -e "${NC}🌐 URLs:${NC}"
echo -e "${NC}   Frontend: http://localhost:3000${NC}"
echo -e "${NC}   backend_server: http://localhost:5109${NC}"
echo -e "${NC}   backend_host: http://localhost:6109${NC}"
if [ "$INCLUDE_DISCARD" = true ]; then
    echo -e "${NC}   backend_discard: AI analysis service (port ${DISCARD_PORT:-6209})${NC}"
fi
echo "=================================================================================="

# Wait for all background jobs
wait 