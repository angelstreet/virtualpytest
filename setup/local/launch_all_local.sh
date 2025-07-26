#!/bin/bash

# VirtualPyTest - Launch All Services Locally (No Docker)
# This script starts all services in separate terminal sessions

set -e

echo "🚀 Launching VirtualPyTest - All Services Locally (No Docker)"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-server" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "❌ Dependencies not installed. Please run: ./setup/local/install_local.sh"
    exit 1
fi

# Check if Node.js dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend dependencies not installed. Please run: ./setup/local/install_local.sh"
    exit 1
fi

echo "🔧 Starting all services in background..."

# Function to start service in background and track PID
start_service() {
    local service_name="$1"
    local script_path="$2"
    local port="$3"
    
    echo "🚀 Starting $service_name on port $port..."
    cd "$script_path"
    
    if [ "$service_name" = "Frontend" ]; then
        npm run dev &
    else
        python src/app.py &
    fi
    
    local pid=$!
    echo "$pid" >> /tmp/virtualpytest_pids.txt
    echo "✅ $service_name started (PID: $pid)"
    cd - > /dev/null
}

# Clean up any existing PID file
rm -f /tmp/virtualpytest_pids.txt

# Start all services
start_service "Backend-Server" "backend-server" "5109"
sleep 2
start_service "Backend-Host" "backend-host" "6109"
sleep 2
start_service "Frontend" "frontend" "3000"

echo ""
echo "🎉 All services are starting up!"
echo "📱 Frontend: http://localhost:3000"
echo "🖥️  Backend-Server: http://localhost:5109"
echo "🔧 Backend-Host: http://localhost:6109"
echo ""
echo "📊 To view logs: Check terminal output above"
echo "🛑 To stop all services: ./setup/local/stop_all_local.sh"
echo ""
echo "⚠️  Services are running in background. Check processes with 'ps aux | grep python'" 