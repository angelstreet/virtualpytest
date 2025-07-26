#!/bin/bash

# VirtualPyTest - Launch Backend-Host Only
# This script starts only the backend-host service

set -e

echo "🔧 Launching VirtualPyTest - Backend-Host Only"

SERVICE_NAME="virtualpytest-backend-host"

echo "🚀 Starting Backend-Host via systemd..."

# Check if service exists
if ! systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
    echo "❌ Systemd service not found: $SERVICE_NAME"
    echo "Please run: ./setup/local/install_host.sh"
    exit 1
fi

# Restart the service
echo "🔄 Restarting $SERVICE_NAME service..."
sudo systemctl restart "$SERVICE_NAME"

# Check if service started successfully
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ $SERVICE_NAME started successfully"
    echo "🌐 Backend-Host: http://localhost:6109"
    echo ""
    echo "📊 Showing live logs (Press Ctrl+C to stop viewing logs):"
    echo "================================================"
    
    # Follow logs
    journalctl -u "$SERVICE_NAME.service" -f
else
    echo "❌ Failed to start $SERVICE_NAME"
    echo "📊 Recent logs:"
    journalctl -u "$SERVICE_NAME.service" -n 20 --no-pager
    exit 1
fi