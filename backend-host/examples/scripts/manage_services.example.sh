#!/bin/bash

# VirtualPyTest Host Services Manager
# Manage all backend-host services from one script

SERVICES=(
    "virtualpytest-ffmpeg-capture"
    "virtualpytest-rename-captures" 
    "virtualpytest-capture-monitor"
    "virtualpytest-cleanup.timer"
)

show_status() {
    echo "📊 VirtualPyTest Host Services Status:"
    echo "======================================"
    for service in "${SERVICES[@]}"; do
        status=$(systemctl is-active $service 2>/dev/null || echo "inactive")
        enabled=$(systemctl is-enabled $service 2>/dev/null || echo "disabled")
        printf "%-30s: %s (%s)\n" "$service" "$status" "$enabled"
    done
    echo ""
}

start_all() {
    echo "🚀 Starting all VirtualPyTest host services..."
    for service in "${SERVICES[@]}"; do
        echo "Starting $service..."
        sudo systemctl start $service
    done
    echo "✅ All services started"
}

stop_all() {
    echo "🛑 Stopping all VirtualPyTest host services..."
    # Stop in reverse order
    for ((i=${#SERVICES[@]}-1; i>=0; i--)); do
        service="${SERVICES[$i]}"
        echo "Stopping $service..."
        sudo systemctl stop $service
    done
    echo "✅ All services stopped"
}

restart_all() {
    echo "🔄 Restarting all VirtualPyTest host services..."
    stop_all
    sleep 2
    start_all
}

enable_all() {
    echo "🔧 Enabling all VirtualPyTest host services..."
    for service in "${SERVICES[@]}"; do
        echo "Enabling $service..."
        sudo systemctl enable $service
    done
    echo "✅ All services enabled"
}

disable_all() {
    echo "❌ Disabling all VirtualPyTest host services..."
    for service in "${SERVICES[@]}"; do
        echo "Disabling $service..."
        sudo systemctl disable $service
    done
    echo "✅ All services disabled"
}

show_logs() {
    local service="$1"
    if [ -z "$service" ]; then
        echo "📜 Recent logs from all services:"
        echo "================================="
        tail -n 10 /tmp/capture_monitor_service.log /tmp/ffmpeg_service.log /tmp/rename_service.log /tmp/cleanup_service.log
    else
        echo "📜 Logs for $service:"
        journalctl -u "$service" -n 20 --no-pager
    fi
}

case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        show_status
        ;;
    enable)
        enable_all
        ;;
    disable)
        disable_all
        ;;
    logs)
        show_logs "$2"
        ;;
    *)
        echo "VirtualPyTest Host Services Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|enable|disable|logs [service]}"
        echo ""
        echo "Commands:"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Show status of all services"
        echo "  enable    - Enable all services to start on boot"
        echo "  disable   - Disable auto-start on boot"
        echo "  logs      - Show recent logs (optionally for specific service)"
        echo ""
        echo "Available services:"
        for service in "${SERVICES[@]}"; do
            echo "  - $service"
        done
        exit 1
        ;;
esac 