#!/bin/bash

# VirtualPyTest - Launch All Services via Systemd
# This script starts systemd services and shows their logs

set -e

echo "🚀 Launching VirtualPyTest - All Services via Systemd"

# Get to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if systemd services are installed
SERVICES=("backend-server" "backend-host")
MISSING_SERVICES=""

for service in "${SERVICES[@]}"; do
    if ! systemctl list-unit-files | grep -q "virtualpytest-${service}.service"; then
        MISSING_SERVICES="$MISSING_SERVICES virtualpytest-${service}.service"
    fi
done

if [ -n "$MISSING_SERVICES" ]; then
    echo "❌ Systemd services not installed:$MISSING_SERVICES"
    echo "Please install systemd services first or use: ./setup/local/launch_all.sh"
    exit 1
fi

echo "🔧 Starting systemd services..."

# Start all services
sudo systemctl start virtualpytest-backend-server.service
sudo systemctl start virtualpytest-backend-host.service

echo "✅ Services started!"
echo ""
echo "📱 Frontend: Start manually with ./setup/local/launch_frontend.sh"
echo "🖥️  Backend-Server: http://localhost:5109" 
echo "🔧 Backend-Host: http://localhost:6109"
echo ""
echo "📊 Showing live logs from systemd services..."
echo "🛑 Press Ctrl+C to stop viewing logs (services will continue running)"
echo "================================================"

# Follow logs from systemd services
journalctl -u virtualpytest-backend-server.service -u virtualpytest-backend-host.service -f 