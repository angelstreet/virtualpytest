#!/bin/bash

# VirtualPyTest Stop All Services Script
echo "🛑 Stopping all VirtualPyTest services..."

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log directories
LOG_DIR="$PROJECT_ROOT/logs"

# PID file locations
SERVER_PID_FILE="$LOG_DIR/backend_server.pid"
HOST_PID_FILE="$LOG_DIR/backend_host.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"

# Function to stop service
stop_service() {
    local service_name="$1"
    local pid_file="$2"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}🛑 Stopping $service_name (PID: $pid)...${NC}"
            kill -TERM "$pid" 2>/dev/null
            sleep 3
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${RED}🔥 Force killing $service_name...${NC}"
                kill -9 "$pid" 2>/dev/null
            fi
            echo -e "${GREEN}✅ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $service_name was not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠️  $service_name PID file not found${NC}"
    fi
}

# Stop all services
stop_service "Backend-Server" "$SERVER_PID_FILE"
stop_service "Backend-Host" "$HOST_PID_FILE"
stop_service "Frontend" "$FRONTEND_PID_FILE"

# Also kill any processes on the known ports as fallback
echo "🔍 Checking for any remaining processes on service ports..."

# Port 5109 (Backend-Server)
if lsof -ti:5109 > /dev/null 2>&1; then
    echo "🛑 Killing remaining processes on port 5109..."
    lsof -ti:5109 | xargs kill -9 2>/dev/null || true
fi

# Port 6409 (Backend-Host)
if lsof -ti:6409 > /dev/null 2>&1; then
    echo "🛑 Killing remaining processes on port 6409..."
    lsof -ti:6409 | xargs kill -9 2>/dev/null || true
fi

# Port 3000 (Frontend)
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "🛑 Killing remaining processes on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

echo -e "${GREEN}✅ All VirtualPyTest services stopped${NC}" 