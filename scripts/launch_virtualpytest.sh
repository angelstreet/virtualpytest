#!/bin/bash

# VirtualPyTest Launch Script - Delegates to setup/local/launch_all.sh
echo "🚀 Starting VirtualPyTest System (including AI Discard Service)..."

# Get the script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📁 Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/README.md" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    exit 1
fi

# Check if launch_all.sh exists
LAUNCH_ALL_SCRIPT="$PROJECT_ROOT/setup/local/launch_all.sh"
if [ ! -f "$LAUNCH_ALL_SCRIPT" ]; then
    echo "❌ Launch script not found: $LAUNCH_ALL_SCRIPT"
    exit 1
fi

# Make sure the script is executable
chmod +x "$LAUNCH_ALL_SCRIPT"

# Delegate to launch_all.sh
echo "🔄 Delegating to setup/local/launch_all.sh..."
exec "$LAUNCH_ALL_SCRIPT"