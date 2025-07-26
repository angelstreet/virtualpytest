#!/bin/bash

# VirtualPyTest - Stop All Local Services
# This script stops all VirtualPyTest systemd services

set -e

echo "🛑 Stopping VirtualPyTest - All Systemd Services"

# Define service names
SERVICES=(
    "virtualpytest-backend-server"
    "virtualpytest-backend-host"
    "virtualpytest-frontend"
)

# Check if services exist and stop them
echo "🔍 Checking and stopping services..."
STOPPED_SERVICES=""
NOT_FOUND_SERVICES=""

for service in "${SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "$service.service"; then
        if systemctl is-active --quiet "$service"; then
            echo "🛑 Stopping $service..."
            sudo systemctl stop "$service"
            STOPPED_SERVICES="$STOPPED_SERVICES $service"
        else
            echo "ℹ️  $service already stopped"
        fi
    else
        echo "⚠️  $service.service not found"
        NOT_FOUND_SERVICES="$NOT_FOUND_SERVICES $service"
    fi
done

# Wait a moment for services to stop
sleep 2

# Verify services are stopped
echo ""
echo "📊 Final Service Status:"
ALL_STOPPED=true
for service in "${SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "$service.service"; then
        if systemctl is-active --quiet "$service"; then
            echo "❌ $service: still running"
            ALL_STOPPED=false
        else
            echo "✅ $service: stopped"
        fi
    fi
done

# Additional cleanup for any orphaned processes (fallback)
echo ""
echo "🧹 Cleaning up any remaining VirtualPyTest processes..."
pkill -f "python.*app.py" 2>/dev/null || echo "   No Python app processes found"
pkill -f "npm.*run.*dev" 2>/dev/null || echo "   No npm dev processes found"
pkill -f "node.*vite" 2>/dev/null || echo "   No Vite dev server found"

echo ""
if [ "$ALL_STOPPED" = true ]; then
    echo "✅ All VirtualPyTest services have been stopped!"
else
    echo "⚠️  Some services may still be running. Check individual service status:"
    for service in "${SERVICES[@]}"; do
        echo "   systemctl status $service.service"
    done
fi

echo ""
echo "🔍 To verify all processes are stopped:"
echo "   ps aux | grep -E '(python.*app|npm.*dev|node.*vite)'"
echo ""
echo "🔄 To restart all services:"
echo "   ./setup/local/launch_all.sh" 