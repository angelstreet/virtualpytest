#!/bin/bash
# Docker entrypoint script for backend_host
# Starts supervisord with backend_host services
# NOTE: This script runs on EVERY container start to ensure RAM storage is initialized

set -e

echo "🚀 Starting VirtualPyTest Backend Host..."
echo "   Container: $(hostname)"
echo "   Timestamp: $(date)"

# Initialize storage directories from .env
ENV_FILE="/app/backend_host/src/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

echo ""
echo "📁 Initializing storage directories..."

# Parse HOST_VIDEO_CAPTURE_PATH
CAPTURE_PATH=$(grep "^HOST_VIDEO_CAPTURE_PATH=" "$ENV_FILE" | cut -d '=' -f 2- | tr -d '"' | tr -d "'")

if [ -z "$CAPTURE_PATH" ]; then
    echo "❌ ERROR: HOST_VIDEO_CAPTURE_PATH not found in .env"
    exit 1
fi

echo "   Storage path: $CAPTURE_PATH"

# Verify tmpfs mount exists (should be mounted by docker-compose.yml)
if mountpoint -q "$CAPTURE_PATH/hot"; then
    HOT_SIZE=$(df -h "$CAPTURE_PATH/hot" | tail -1 | awk '{print $2}')
    echo "   ✅ tmpfs mounted at $CAPTURE_PATH/hot (size: $HOT_SIZE)"
else
    echo "   ⚠️  WARNING: $CAPTURE_PATH/hot is NOT mounted as tmpfs!"
    echo "   This may cause performance issues. Check docker-compose.yml"
fi

# Create HOT subdirectories (tmpfs loses all data on container restart)
echo "   Creating HOT directories (RAM)..."
mkdir -p "$CAPTURE_PATH/hot/captures"
mkdir -p "$CAPTURE_PATH/hot/thumbnails"
mkdir -p "$CAPTURE_PATH/hot/segments"
mkdir -p "$CAPTURE_PATH/hot/metadata"
chmod -R 777 "$CAPTURE_PATH/hot"

# Create COLD subdirectories (persistent disk)
echo "   Creating COLD directories (disk)..."
mkdir -p "$CAPTURE_PATH/captures"
mkdir -p "$CAPTURE_PATH/segments"
mkdir -p "$CAPTURE_PATH/metadata"
mkdir -p "$CAPTURE_PATH/audio"
mkdir -p "$CAPTURE_PATH/thumbnails"

# Create hour folders (0-23) for rolling 24h storage
for hour in {0..23}; do
    mkdir -p "$CAPTURE_PATH/segments/$hour"
    mkdir -p "$CAPTURE_PATH/metadata/$hour"
    mkdir -p "$CAPTURE_PATH/audio/$hour"
done

# Create temp directories
mkdir -p "$CAPTURE_PATH/segments/temp"
mkdir -p "$CAPTURE_PATH/metadata/temp"

# Set all permissions to 777 for cross-service access
chmod -R 777 "$CAPTURE_PATH"

echo "   ✅ Storage initialized successfully"
echo ""
echo "📊 Storage summary:"
echo "   HOT (RAM):  $CAPTURE_PATH/hot/{captures,thumbnails,segments,metadata}"
echo "   COLD (disk): $CAPTURE_PATH/{captures,segments,metadata,audio}"
echo "   Hour folders: 0-23 in segments/metadata/audio"
echo ""

echo "🔧 Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n

