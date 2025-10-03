#!/bin/bash

# VirtualDiscard Launch Script - AI Discard Processing Service
# Usage: ./launch_virtualdiscard.sh
# Launches backend_discard service for AI-powered alert analysis

echo "🤖 Starting VirtualDiscard (AI Discard Processing Service)..."

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

# Check if all required components are installed
MISSING_COMPONENTS=""

if [ ! -d "venv" ]; then
    MISSING_COMPONENTS="$MISSING_COMPONENTS venv"
fi

if [ ! -d "backend_discard/src" ]; then
    MISSING_COMPONENTS="$MISSING_COMPONENTS backend_discard"
fi

if [ -n "$MISSING_COMPONENTS" ]; then
    echo "❌ Missing components:$MISSING_COMPONENTS"
    echo "Please install all components first"
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
export PYTHONPATH="$PROJECT_ROOT/shared/src:$PROJECT_ROOT/backend_discard/src"

# Load environment variables from .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "📝 Loading environment variables from .env..."
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo "⚠️  Warning: .env file not found at $PROJECT_ROOT/.env"
fi

# Verify required environment variables
MISSING_ENV=""

if [ -z "$UPSTASH_REDIS_REST_URL" ]; then
    MISSING_ENV="$MISSING_ENV UPSTASH_REDIS_REST_URL"
fi

if [ -z "$UPSTASH_REDIS_REST_TOKEN" ]; then
    MISSING_ENV="$MISSING_ENV UPSTASH_REDIS_REST_TOKEN"
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    MISSING_ENV="$MISSING_ENV OPENROUTER_API_KEY"
fi

if [ -n "$MISSING_ENV" ]; then
    echo "❌ Missing required environment variables:$MISSING_ENV"
    echo "Please add them to $PROJECT_ROOT/.env"
    exit 1
fi

echo "✅ Environment checks passed"

# Colors for output
CYAN='\033[0;36m'
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
    echo -e "\n${RED}🛑 Shutting down discard service...${NC}"
    
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
    rm -f /tmp/backend_discard.pid
    
    echo -e "${RED}✅ Discard service stopped${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "📺 Starting discard service with real-time logging..."
echo "💡 Press Ctrl+C to stop the service"
echo "💡 Logs will appear with colored prefix: [DISCARD]"
echo "=================================================================================="

# Start backend_discard
echo -e "${CYAN}🔵 Starting AI Discard Processing Service...${NC}"
run_with_prefix "DISCARD" "$CYAN" "$PROJECT_ROOT/backend_discard" python src/app.py
sleep 2

echo "=================================================================================="
echo -e "${NC}✅ Discard service started! Watching for logs...${NC}"
echo -e "${NC}💡 You should see logs with [DISCARD] prefix appearing below${NC}"
echo -e "${NC}🤖 Service Status:${NC}"
echo -e "${NC}   AI Queue Processing: Active${NC}"
echo -e "${NC}   Priority: P1 (alerts) → P2 (scripts) → P3 (reserved)${NC}"
echo -e "${NC}   Mode: BLPOP (blocking - efficient, no polling!)${NC}"
echo "=================================================================================="

# Wait for all background jobs
wait

