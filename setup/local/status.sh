#!/bin/bash

# VirtualPyTest Status Check Script
echo "📊 Checking VirtualPyTest services status..."

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Log directories
LOG_DIR="$PROJECT_ROOT/logs"

# PID file locations
SERVER_PID_FILE="$LOG_DIR/backend_server.pid"
HOST_PID_FILE="$LOG_DIR/backend_host.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"

# Function to check service status
check_service_status() {
    local service_name="$1"
    local pid_file="$2"
    local port="$3"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ $service_name: RUNNING (PID: $pid)${NC}"
            
            # Check if port is actually in use
            if lsof -ti:$port > /dev/null 2>&1; then
                echo -e "   ${BLUE}🌐 Port $port: ACTIVE${NC}"
            else
                echo -e "   ${YELLOW}⚠️  Port $port: NOT ACTIVE${NC}"
            fi
        else
            echo -e "${RED}❌ $service_name: STOPPED (stale PID file)${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${RED}❌ $service_name: STOPPED (no PID file)${NC}"
        
        # Check if something else is using the port
        if lsof -ti:$port > /dev/null 2>&1; then
            local port_pid=$(lsof -ti:$port)
            echo -e "   ${YELLOW}⚠️  Port $port: OCCUPIED by PID $port_pid${NC}"
        fi
    fi
}

echo "=================================================================================="

# Check all services
check_service_status "Backend-Server" "$SERVER_PID_FILE" "5109"
check_service_status "Backend-Host" "$HOST_PID_FILE" "6409"
check_service_status "Frontend" "$FRONTEND_PID_FILE" "3000"

echo "=================================================================================="

# Show URLs if services are running
echo -e "${BLUE}🌐 Service URLs:${NC}"
echo -e "   Frontend: http://localhost:3000"
echo -e "   Backend-Server: http://localhost:5109"
echo -e "   Backend-Host: http://localhost:6409"

# Show log files
if [ -d "$LOG_DIR" ]; then
    echo -e "\n${BLUE}📂 Log files:${NC}"
    if [ -f "$LOG_DIR/backend_server.log" ]; then
        echo -e "   Server: $LOG_DIR/backend_server.log"
    fi
    if [ -f "$LOG_DIR/backend_host.log" ]; then
        echo -e "   Host: $LOG_DIR/backend_host.log"
    fi
    if [ -f "$LOG_DIR/frontend.log" ]; then
        echo -e "   Frontend: $LOG_DIR/frontend.log"
    fi
fi

echo "=================================================================================="
echo -e "${YELLOW}💡 Commands:${NC}"
echo -e "   Start services: ./setup/local/launch_all.sh"
echo -e "   Stop services: ./setup/local/stop_all.sh"
echo -e "   View logs: tail -f logs/<service>.log" 