#!/bin/bash

# VirtualPyTest - Service Orchestrator
# Clean service starter that launches services based on environment configuration
# No legacy code - fresh implementation

set -e

# Configuration
SCRIPTS_DIR="/app/backend_host/scripts"
SERVICES_LIST_FILE="/tmp/services_list.txt"
GRABBERS_CONFIG_FILE="/tmp/grabbers_config.sh"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] start_services: $1"
}

# Function to start VNC services (always required)
start_vnc_services() {
    # Check if VNC services are already running
    if pgrep -f "Xvfb :99" > /dev/null; then
        log "VNC services already running, skipping startup"
        return 0
    fi
    
    log "Starting VNC services..."
    
    # Clean up any existing X locks
    rm -f /tmp/.X99-lock
    
    # Start Xvfb (virtual display)
    log "Starting Xvfb virtual display on :99"
    Xvfb :99 -screen 0 1280x720x24 -ac +extension GLX +render -noreset &
    XVFB_PID=$!
    
    # Wait for Xvfb to start
    sleep 2
    
    # Start window manager
    log "Starting Fluxbox window manager"
    DISPLAY=:99 fluxbox &
    FLUXBOX_PID=$!
    
    # Start x11vnc (VNC server)
    log "Starting x11vnc VNC server on :5900"
    x11vnc -display :99 -nopw -listen localhost -xkb -ncache 10 -ncache_cr -forever -q > /dev/null 2>&1 &
    X11VNC_PID=$!
    
    # Wait for VNC server to start
    sleep 2
    
    # Start NoVNC (web-based VNC client)
    log "Starting NoVNC web client on :6080"
    websockify --web=/usr/share/novnc/ 6080 localhost:5900 > /dev/null 2>&1 &
    NOVNC_PID=$!
    
    log "VNC services started successfully"
    log "  - Xvfb virtual display on :99"
    log "  - Fluxbox window manager"
    log "  - x11vnc VNC server on :5900"
    log "  - NoVNC web client on :6080"
}

# Function to start video services (conditional)
start_video_services() {
    log "Starting video services..."
    
    # Check if GRABBERS config exists
    if [ ! -f "$GRABBERS_CONFIG_FILE" ]; then
        log "Error: GRABBERS config not found at $GRABBERS_CONFIG_FILE"
        return 1
    fi
    
    # Start FFmpeg with dynamic GRABBERS config
    log "Starting FFmpeg capture with dynamic configuration"
    "$SCRIPTS_DIR/run_ffmpeg_and_rename_docker.sh" &
    FFMPEG_PID=$!
    
    log "Video services started successfully"
    log "  - FFmpeg capture service (PID: $FFMPEG_PID)"
}

# Function to start monitor service (conditional)
start_monitor_service() {
    log "Starting monitor service..."
    
    # Start capture monitor
    log "Starting capture monitor for video analysis"
    python "$SCRIPTS_DIR/capture_monitor.py" &
    MONITOR_PID=$!
    
    log "Monitor service started successfully"
    log "  - Capture monitor (PID: $MONITOR_PID)"
}

# Function to handle cleanup on exit
cleanup() {
    log "Received shutdown signal, cleaning up services..."
    
    # Kill background processes
    [ -n "$XVFB_PID" ] && kill "$XVFB_PID" 2>/dev/null && log "Stopped Xvfb"
    [ -n "$FLUXBOX_PID" ] && kill "$FLUXBOX_PID" 2>/dev/null && log "Stopped Fluxbox"
    [ -n "$X11VNC_PID" ] && kill "$X11VNC_PID" 2>/dev/null && log "Stopped x11vnc"
    [ -n "$NOVNC_PID" ] && kill "$NOVNC_PID" 2>/dev/null && log "Stopped NoVNC"
    [ -n "$FFMPEG_PID" ] && kill "$FFMPEG_PID" 2>/dev/null && log "Stopped FFmpeg"
    [ -n "$MONITOR_PID" ] && kill "$MONITOR_PID" 2>/dev/null && log "Stopped Monitor"
    
    log "Cleanup complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    log "🏠 VirtualPyTest Backend Host - Service Orchestrator"
    log "Starting service orchestration..."
    
    # Step 1: Generate service configuration
    log "Step 1: Generating service configuration from environment"
    SERVICES_OUTPUT=$("$SCRIPTS_DIR/generate_services_config.sh" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        log "Error: Failed to generate service configuration"
        exit 1
    fi
    
    # Extract only the last line (the services list)
    SERVICES=$(echo "$SERVICES_OUTPUT" | tail -n 1)
    log "Required services: $SERVICES"
    
    # Step 2: Start services based on configuration
    log "Step 2: Starting required services"
    
    for service in $SERVICES; do
        case $service in
            "vnc")
                start_vnc_services
                ;;
            "video")
                start_video_services
                ;;
            "monitor")
                start_monitor_service
                ;;
            *)
                log "Warning: Unknown service '$service'"
                ;;
        esac
    done
    
    # Step 3: Wait for services to be ready
    log "Step 3: Waiting for services to initialize"
    sleep 3
    
    # Step 4: Start Flask application
    log "Step 4: Starting Flask application"
    log "🎉 All services ready! Starting Flask API on port 6109"
    
    # Change to backend_host directory for Flask app
    cd /app/backend_host
    
    # Start Flask application (foreground process)
    exec python src/app.py
}

# Execute main function
main "$@" 