#!/bin/bash

# macOS Launch Agent Installation Script
# Equivalent to systemd services for Linux

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_DIR="$PROJECT_ROOT/backend_host/config/services/mac"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "=== macOS Launch Agent Installation ==="
echo "Project root: $PROJECT_ROOT"
echo "Plist directory: $PLIST_DIR"
echo "Launch agents directory: $LAUNCH_AGENTS_DIR"
echo "User home: $HOME"
echo

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Function to install a launch agent
install_launch_agent() {
    local source_name="$1"
    local plist_file="$PLIST_DIR/$source_name"
    
    # Determine target filename based on source
    local target_name
    if [ "$source_name" = "monitor.plist" ]; then
        target_name="com.virtualpytest.monitor.plist"
    elif [ "$source_name" = "stream.plist" ]; then
        target_name="com.virtualpytest.stream.plist"
    else
        target_name="$source_name"
    fi
    
    local target_file="$LAUNCH_AGENTS_DIR/$target_name"
    local service_name="${target_name%.*}"
    
    echo "Installing $source_name -> $target_name..."
    
    # Check if plist file exists
    if [ ! -f "$plist_file" ]; then
        echo "ERROR: $plist_file not found!"
        return 1
    fi
    
    # Stop and unload existing service if running
    if launchctl list | grep -q "$service_name"; then
        echo "  Stopping existing service..."
        launchctl unload "$target_file" 2>/dev/null || true
    fi
    
    # Copy plist file
    echo "  Copying plist file..."
    cp "$plist_file" "$target_file"
    
    # Load the service
    echo "  Loading service..."
    launchctl load "$target_file"
    
    # Start the service
    echo "  Starting service..."
    launchctl start "$service_name"
    
    echo "  ✓ $source_name installed and started as $service_name"
    echo
}

# Function to check service status
check_service_status() {
    local service_name="$1"
    echo "Checking status of $service_name..."
    
    if launchctl list | grep -q "$service_name"; then
        local pid=$(launchctl list | grep "$service_name" | awk '{print $1}')
        local status=$(launchctl list | grep "$service_name" | awk '{print $2}')
        
        if [ "$pid" = "-" ]; then
            echo "  Status: Not running (exit code: $status)"
        else
            echo "  Status: Running (PID: $pid)"
        fi
    else
        echo "  Status: Not loaded"
    fi
    echo
}

# Install services
echo "Installing launch agents..."
echo

install_launch_agent "monitor.plist"
install_launch_agent "stream.plist"

echo "=== Installation Complete ==="
echo

# Check status
echo "=== Service Status ==="
check_service_status "com.virtualpytest.monitor"
check_service_status "com.virtualpytest.stream"

echo "=== Useful Commands ==="
echo "View logs:"
echo "  Monitor service: tail -f /tmp/com.virtualpytest.monitor.out"
echo "  Stream service:  tail -f /tmp/com.virtualpytest.stream.out"
echo
echo "Control services:"
echo "  Stop:    launchctl stop com.virtualpytest.monitor"
echo "  Start:   launchctl start com.virtualpytest.monitor"
echo "  Restart: launchctl kickstart -k gui/\$(id -u)/com.virtualpytest.monitor"
echo
echo "Uninstall services:"
echo "  launchctl unload ~/Library/LaunchAgents/com.virtualpytest.monitor.plist"
echo "  rm ~/Library/LaunchAgents/com.virtualpytest.monitor.plist"
echo

echo "=== Prerequisites Check ==="
echo "Make sure you have:"
echo "1. Python virtual environment activated"
echo "2. FFmpeg installed (brew install ffmpeg)"
echo "3. Required Python dependencies installed"
echo "4. Proper file paths updated for macOS"
echo
