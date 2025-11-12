#!/bin/bash
# Docker entrypoint script for backend_host
# Generates .env file from environment variables and starts supervisord

set -e

echo "🚀 Starting VirtualPyTest Backend Host..."

# Generate .env file from environment variables
/app/backend_host/docker/scripts/generate_env.sh

# Check if we should auto-enable stream service
ENV_FILE="/app/backend_host/src/.env"
HOST_VIDEO_COUNT=0
DEVICE_COUNT=0

if [ -n "$HOST_VIDEO_SOURCE" ]; then
    HOST_VIDEO_COUNT=1
fi

for i in {1..10}; do
    var_name="DEVICE${i}_VIDEO"
    if [ -n "${!var_name}" ]; then
        ((DEVICE_COUNT++))
    fi
done

# Update stream service autostart in supervisord config based on device detection
if [ $((HOST_VIDEO_COUNT + DEVICE_COUNT)) -gt 0 ]; then
    echo "✅ Enabling stream service (devices detected)"
    sed -i 's/^autostart=false/autostart=true/' /etc/supervisor/conf.d/virtualpytest.conf || true
else
    echo "ℹ️  Stream service remains disabled (no devices configured)"
fi

echo "🔧 Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n

