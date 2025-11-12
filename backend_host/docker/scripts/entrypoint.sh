#!/bin/bash
# Docker entrypoint script for backend_host
# Starts supervisord with backend_host services

set -e

echo "🚀 Starting VirtualPyTest Backend Host..."

echo "🔧 Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n

