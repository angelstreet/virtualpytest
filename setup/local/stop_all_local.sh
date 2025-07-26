#!/bin/bash

# VirtualPyTest - Stop All Local Services
# This script stops all services started by launch_all_local.sh

set -e

echo "🛑 Stopping VirtualPyTest - All Local Services"

# Check if PID file exists
if [ ! -f "/tmp/virtualpytest_pids.txt" ]; then
    echo "⚠️  No PID file found. Services might not be running via launch_all_local.sh"
    echo "🔍 Trying to find and kill VirtualPyTest processes manually..."
    
    # Kill any Python processes running our apps
    pkill -f "python.*app.py" 2>/dev/null || echo "   No Python app processes found"
    
    # Kill any npm dev processes
    pkill -f "npm.*run.*dev" 2>/dev/null || echo "   No npm dev processes found"
    
    # Kill any node processes running our frontend
    pkill -f "node.*vite" 2>/dev/null || echo "   No Vite dev server found"
    
    echo "✅ Manual cleanup completed"
    exit 0
fi

# Kill processes from PID file
echo "🔍 Reading PIDs from /tmp/virtualpytest_pids.txt..."
while read -r pid; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo "🛑 Stopping process $pid..."
        kill "$pid" 2>/dev/null || echo "   Process $pid already stopped"
    else
        echo "   Process $pid not running"
    fi
done < /tmp/virtualpytest_pids.txt

# Clean up PID file
rm -f /tmp/virtualpytest_pids.txt

# Additional cleanup for any orphaned processes
echo "🧹 Cleaning up any remaining VirtualPyTest processes..."
pkill -f "python.*app.py" 2>/dev/null || true
pkill -f "npm.*run.*dev" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true

echo ""
echo "✅ All VirtualPyTest local services have been stopped!"
echo "🔍 You can verify with: ps aux | grep -E '(python.*app|npm.*dev|node.*vite)'" 