#!/bin/bash

# VirtualPyTest - Launch All Services via Systemd
# This script restarts all systemd services and shows combined logs

set -e

echo "🚀 Launching VirtualPyTest - All Services via Systemd"

# Define service names
SERVICES=(
    "virtualpytest-backend-server"
    "virtualpytest-backend-host"
    "virtualpytest-frontend"
)

# Check if all services exist
MISSING_SERVICES=""
for service in "${SERVICES[@]}"; do
    if ! systemctl list-unit-files | grep -q "$service.service"; then
        MISSING_SERVICES="$MISSING_SERVICES $service"
    fi
done

if [ -n "$MISSING_SERVICES" ]; then
    echo "❌ Missing systemd services:$MISSING_SERVICES"
    echo "Please install services first:"
    echo "   ./setup/local/install_local.sh"
    exit 1
fi

echo "🔄 Restarting all services..."

# Restart all services
for service in "${SERVICES[@]}"; do
    echo "🔄 Restarting $service..."
    sudo systemctl restart "$service"
done

# Wait for services to start
sleep 3

# Check service status
echo ""
echo "📊 Service Status:"
FAILED_SERVICES=""
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo "✅ $service: running"
    else
        echo "❌ $service: failed"
        FAILED_SERVICES="$FAILED_SERVICES $service"
    fi
done

# Stop if any services failed
if [ -n "$FAILED_SERVICES" ]; then
    echo ""
    echo "💥 Service startup failed!"
    echo "❌ Failed services:$FAILED_SERVICES"
    echo ""
    echo "🔍 Check service logs:"
    for service in $FAILED_SERVICES; do
        echo "   journalctl -u $service.service -n 50"
    done
    echo ""
    echo "🛠️ Troubleshooting:"
    echo "   1. Check .env files are configured"
    echo "   2. Re-run installation: ./setup/local/install_local.sh"
    echo "   3. Check individual service logs above"
    exit 1
fi

echo ""
echo "🎉 All services running successfully!"
echo "📱 Frontend: http://localhost:3000"
echo "🖥️  Backend-Server: http://localhost:5109" 
echo "🔧 Backend-Host: http://localhost:6109"
echo ""
echo "📊 Showing live logs from all services..."
echo "🛑 Press Ctrl+C to stop viewing logs (services will continue running)"
echo "================================================"

# Follow logs from all services
journalctl -u virtualpytest-backend-server.service -u virtualpytest-backend-host.service -u virtualpytest-frontend.service -f 