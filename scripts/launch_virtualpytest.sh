#!/bin/bash

# VirtualPyTest Launch Script - Delegates to setup/local/launch_all.sh
# Usage: ./launch_virtualpytest.sh [--discard]
#   --discard: Include the AI Discard Service (uses many tokens)

# Parse command line arguments
INCLUDE_DISCARD=false
for arg in "$@"; do
    case $arg in
        --discard)
            INCLUDE_DISCARD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--discard]"
            echo "  --discard    Include the AI Discard Service (uses many tokens)"
            echo "  -h, --help   Show this help message"
            exit 0
            ;;
        *)
            echo "❌ Unknown parameter: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$INCLUDE_DISCARD" = true ]; then
    echo "🚀 Starting VirtualPyTest System (including AI Discard Service)..."
else
    echo "🚀 Starting VirtualPyTest System (without AI Discard Service)..."
fi

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

# Delegate to launch_all.sh with appropriate parameters
echo "🔄 Delegating to setup/local/launch_all.sh..."
if [ "$INCLUDE_DISCARD" = true ]; then
    exec "$LAUNCH_ALL_SCRIPT" --discard --with-grafana
else
    exec "$LAUNCH_ALL_SCRIPT" --with-grafana
fi