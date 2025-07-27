#!/bin/bash

# VirtualPyTest Launch Script - Background Services with Real-time Logging
echo "🚀 Starting VirtualPyTest System with Background Services and Real-time Logging..."

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

if [ -n "$MISSING_COMPONENTS" ]; then
    echo "❌ Missing components:$MISSING_COMPONENTS"
    echo "Please install all components first:"
    echo "   ./setup/local/install_local.sh"
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
export PYTHONPATH="$PROJECT_ROOT/shared/lib:$PROJECT_ROOT/backend-core/src"

# Colors for different components
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Log directories
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# PID file locations
SERVER_PID_FILE="$LOG_DIR/backend_server.pid"
HOST_PID_FILE="$LOG_DIR/backend_host.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"

# Array to store log monitoring process PIDs (not service PIDs)
declare -a LOG_PIDS=()

# Function to start service as daemon and return its PID
start_daemon() {
    local service_name="$1"
    local directory="$2"
    local pid_file="$3"
    local log_file="$4"
    shift 4
    
    cd "$directory"
    
    if [[ "$1" == "python" ]]; then
        # For Python, use -u flag for unbuffered output
        nohup $PYTHON_CMD -u "${@:2}" > "$log_file" 2>&1 &
    elif [[ "$1" == "npm" ]]; then
        # For npm, set environment variables for unbuffered output
        nohup env FORCE_COLOR=1 "$@" > "$log_file" 2>&1 &
    else
        nohup "$@" > "$log_file" 2>&1 &
    fi
    
    local pid=$!
    echo $pid > "$pid_file"
    
    # Return to project root
    cd "$PROJECT_ROOT"
    
    return $pid
}

# Function to monitor log file with colored prefix
monitor_log() {
    local prefix="$1"
    local color="$2"
    local log_file="$3"
    
    tail -f "$log_file" 2>/dev/null | {
        while IFS= read -r line; do
            printf "${color}[${prefix}]${NC} %s\n" "$line"
        done
    } &
    
    local monitor_pid=$!
    LOG_PIDS+=($monitor_pid)
    return $monitor_pid
}

# Function to check if service is running
is_service_running() {
    local pid_file="$1"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Function to stop service
stop_service() {
    local service_name="$1"
    local pid_file="$2"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "🛑 Stopping $service_name (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                echo "🔥 Force killing $service_name..."
                kill -9 "$pid" 2>/dev/null
            fi
        fi
        rm -f "$pid_file"
    fi
}

# Enhanced cleanup function - only stops log monitoring, not backend services
cleanup() {
    echo -e "\n${CYAN}🛑 Stopping log monitoring (services will continue running in background)...${NC}"
    
    # Only kill log monitoring processes
    for pid in "${LOG_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null
        fi
    done
    
    # Stop frontend (since it's a dev server)
    if is_service_running "$FRONTEND_PID_FILE"; then
        echo -e "${YELLOW}🛑 Stopping Frontend dev server...${NC}"
        stop_service "Frontend" "$FRONTEND_PID_FILE"
    fi
    
    echo -e "${CYAN}✅ Log monitoring stopped. Backend services are still running in background.${NC}"
    echo -e "${CYAN}💡 To stop all services, run: ./setup/local/stop_all.sh${NC}"
    echo -e "${CYAN}💡 To check service status, run: ./setup/local/status.sh${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Kill any processes using required ports
echo "🔍 Checking and clearing required ports..."

# Port 5109 (Backend-Server)
if lsof -ti:5109 > /dev/null 2>&1; then
    echo "🛑 Killing processes on port 5109..."
    lsof -ti:5109 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Port 6409 (Backend-Host)
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

echo "✅ All required ports are available"

# Check if backend services are already running
if is_service_running "$SERVER_PID_FILE"; then
    echo -e "${BLUE}🔵 Backend-Server is already running${NC}"
else
    echo -e "${BLUE}🔵 Starting Backend-Server as daemon...${NC}"
    start_daemon "Backend-Server" "$PROJECT_ROOT/backend-server" "$SERVER_PID_FILE" "$LOG_DIR/backend_server.log" python src/app.py
    echo "✅ Backend-Server started (PID: $(cat $SERVER_PID_FILE))"
    sleep 3
fi

if is_service_running "$HOST_PID_FILE"; then
    echo -e "${GREEN}🟢 Backend-Host is already running${NC}"
else
    echo -e "${GREEN}🟢 Starting Backend-Host as daemon...${NC}"
    start_daemon "Backend-Host" "$PROJECT_ROOT/backend-host" "$HOST_PID_FILE" "$LOG_DIR/backend_host.log" python src/app.py
    echo "✅ Backend-Host started (PID: $(cat $HOST_PID_FILE))"
    sleep 3
fi

# Always start frontend as foreground dev server
echo -e "${YELLOW}🟡 Starting Frontend dev server...${NC}"
start_daemon "Frontend" "$PROJECT_ROOT/frontend" "$FRONTEND_PID_FILE" "$LOG_DIR/frontend.log" npm run dev
echo "✅ Frontend started (PID: $(cat $FRONTEND_PID_FILE))"
sleep 2

echo "📺 Starting real-time log monitoring..."
echo "💡 Press Ctrl+C to stop log monitoring (backend services will continue running)"
echo "💡 Logs will appear with colored prefixes: [SERVER], [HOST], [FRONTEND]"
echo "=================================================================================="

# Start log monitoring for all services
monitor_log "SERVER" "$BLUE" "$LOG_DIR/backend_server.log"
monitor_log "HOST" "$GREEN" "$LOG_DIR/backend_host.log"
monitor_log "FRONTEND" "$YELLOW" "$LOG_DIR/frontend.log"

echo "=================================================================================="
echo -e "${NC}✅ All services started and log monitoring active!${NC}"
echo -e "${NC}🌐 URLs:${NC}"
echo -e "${NC}   Frontend: http://localhost:3000${NC}"
echo -e "${NC}   Backend-Server: http://localhost:5109${NC}"
echo -e "${NC}   Backend-Host: http://localhost:6109${NC}"
echo -e "${NC}📂 Logs: $LOG_DIR/${NC}"
echo "=================================================================================="

# Wait for log monitoring processes
wait 