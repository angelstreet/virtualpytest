#!/bin/bash

# VirtualPyTest - Stop All Local Services
# This script stops all VirtualPyTest background processes

set -e

echo "🛑 Stopping VirtualPyTest - All Background Processes"

# Stop processes and clean up PID files
STOPPED_SERVICES=""
FAILED_STOPS=""

echo "🔍 Stopping backend-server..."
if [ -f "/tmp/backend_server.pid" ]; then
    PID=$(cat /tmp/backend_server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null && echo "✅ Backend-server stopped (PID: $PID)" || echo "⚠️  Failed to stop backend-server (PID: $PID)"
        STOPPED_SERVICES="$STOPPED_SERVICES backend-server"
    else
        echo "ℹ️  Backend-server not running (stale PID file)"
    fi
    rm -f /tmp/backend_server.pid
else
    # Fallback: kill by process name
    if pgrep -f "python.*backend-server.*app.py" > /dev/null; then
        pkill -f "python.*backend-server.*app.py" && echo "✅ Backend-server stopped (by process name)" || echo "⚠️  Failed to stop backend-server"
    else
        echo "ℹ️  Backend-server not running"
    fi
fi

echo "🔍 Stopping backend-host..."
if [ -f "/tmp/backend_host.pid" ]; then
    PID=$(cat /tmp/backend_host.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null && echo "✅ Backend-host stopped (PID: $PID)" || echo "⚠️  Failed to stop backend-host (PID: $PID)"
        STOPPED_SERVICES="$STOPPED_SERVICES backend-host"
    else
        echo "ℹ️  Backend-host not running (stale PID file)"
    fi
    rm -f /tmp/backend_host.pid
else
    # Fallback: kill by process name
    if pgrep -f "python.*backend-host.*app.py" > /dev/null; then
        pkill -f "python.*backend-host.*app.py" && echo "✅ Backend-host stopped (by process name)" || echo "⚠️  Failed to stop backend-host"
    else
        echo "ℹ️  Backend-host not running"
    fi
fi

echo "🔍 Stopping frontend..."
if [ -f "/tmp/frontend.pid" ]; then
    PID=$(cat /tmp/frontend.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null && echo "✅ Frontend stopped (PID: $PID)" || echo "⚠️  Failed to stop frontend (PID: $PID)"
        STOPPED_SERVICES="$STOPPED_SERVICES frontend"
    else
        echo "ℹ️  Frontend not running (stale PID file)"
    fi
    rm -f /tmp/frontend.pid
else
    # Fallback: kill by process name
    if pgrep -f "npm.*run.*dev" > /dev/null || pgrep -f "node.*vite" > /dev/null; then
        pkill -f "npm.*run.*dev" 2>/dev/null || true
        pkill -f "node.*vite" 2>/dev/null || true
        echo "✅ Frontend stopped (by process name)"
    else
        echo "ℹ️  Frontend not running"
    fi
fi

# Additional cleanup for any orphaned processes
echo ""
echo "🧹 Cleaning up any remaining VirtualPyTest processes..."
pkill -f "python.*app.py" 2>/dev/null && echo "   Stopped additional Python app processes" || echo "   No additional Python app processes found"
pkill -f "npm.*run.*dev" 2>/dev/null && echo "   Stopped additional npm dev processes" || echo "   No additional npm dev processes found"
pkill -f "node.*vite" 2>/dev/null && echo "   Stopped additional Vite processes" || echo "   No additional Vite processes found"

# Wait a moment for processes to stop
sleep 2

# Verify all processes are stopped
echo ""
echo "📊 Final Process Status:"
ALL_STOPPED=true

# Check backend-server
if pgrep -f "python.*backend-server.*app.py" > /dev/null; then
    echo "❌ Backend-server: still running"
    ALL_STOPPED=false
else
    echo "✅ Backend-server: stopped"
fi

# Check backend-host
if pgrep -f "python.*backend-host.*app.py" > /dev/null; then
    echo "❌ Backend-host: still running"
    ALL_STOPPED=false
else
    echo "✅ Backend-host: stopped"
fi

# Check frontend
if pgrep -f "npm.*run.*dev" > /dev/null || pgrep -f "node.*vite" > /dev/null; then
    echo "❌ Frontend: still running"
    ALL_STOPPED=false
else
    echo "✅ Frontend: stopped"
fi

echo ""
if [ "$ALL_STOPPED" = true ]; then
    echo "✅ All VirtualPyTest services have been stopped!"
else
    echo "⚠️  Some processes may still be running."
    echo "🔍 To verify manually: ps aux | grep -E '(python.*app|npm.*dev|node.*vite)'"
fi

echo ""
echo "🔄 To restart all services: ./setup/local/launch_all.sh" 