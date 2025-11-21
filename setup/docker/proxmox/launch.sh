#!/bin/bash
# VirtualPyTest Proxmox VM Management
# Start, stop, restart, and manage the VM

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load config
if [ ! -f "config.env" ]; then
    echo "❌ Error: config.env not found"
    echo "   Run ./setup.sh first"
    exit 1
fi

source config.env

# ============================================
# FUNCTIONS
# ============================================

show_usage() {
    cat << EOF
VirtualPyTest Proxmox VM Management

Usage: ./launch.sh <command>

Commands:
    start       Start the VM
    stop        Stop the VM gracefully
    restart     Restart the VM
    status      Show VM status and info
    console     Open VM console (Ctrl+O to exit)
    ssh         SSH into VM
    snapshot    Create a snapshot
    rollback    Rollback to a snapshot
    backup      Create a backup
    info        Show detailed VM information
    logs        Show VM logs
    resize      Resize VM resources
    help        Show this help message

Examples:
    ./launch.sh start
    ./launch.sh status
    ./launch.sh snapshot before-update
    ./launch.sh ssh

EOF
}

check_vm_exists() {
    if ! qm status $VM_ID &>/dev/null; then
        echo "❌ Error: VM $VM_ID does not exist"
        echo "   Run ./setup.sh to create it"
        exit 1
    fi
}

get_vm_status() {
    qm status $VM_ID | grep -oP 'status: \K\w+'
}

get_vm_ip() {
    qm guest exec $VM_ID -- ip -4 addr show 2>/dev/null | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -1 || echo ""
}

wait_for_vm() {
    local timeout=$1
    local target_status=$2
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        local current_status=$(get_vm_status)
        if [ "$current_status" = "$target_status" ]; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        echo -n "."
    done
    
    echo ""
    return 1
}

cmd_start() {
    echo "🚀 Starting VM $VM_ID ($VM_NAME)..."
    
    check_vm_exists
    
    local status=$(get_vm_status)
    
    if [ "$status" = "running" ]; then
        echo "✅ VM is already running"
        return 0
    fi
    
    qm start $VM_ID
    
    echo -n "⏳ Waiting for VM to start"
    if wait_for_vm 60 "running"; then
        echo ""
        echo "✅ VM started successfully"
        
        # Wait a bit for network
        sleep 5
        
        local vm_ip=$(get_vm_ip)
        if [ -n "$vm_ip" ]; then
            echo "🌐 VM IP: $vm_ip"
            echo ""
            echo "SSH: ssh $VM_USER@$vm_ip"
        fi
    else
        echo ""
        echo "⚠️  VM start timeout - check status manually"
    fi
}

cmd_stop() {
    echo "🛑 Stopping VM $VM_ID ($VM_NAME)..."
    
    check_vm_exists
    
    local status=$(get_vm_status)
    
    if [ "$status" = "stopped" ]; then
        echo "✅ VM is already stopped"
        return 0
    fi
    
    # Try graceful shutdown
    qm shutdown $VM_ID
    
    echo -n "⏳ Waiting for graceful shutdown"
    if wait_for_vm 60 "stopped"; then
        echo ""
        echo "✅ VM stopped gracefully"
    else
        echo ""
        echo "⚠️  Graceful shutdown timeout, forcing stop..."
        qm stop $VM_ID
        
        echo -n "⏳ Waiting for force stop"
        if wait_for_vm 30 "stopped"; then
            echo ""
            echo "✅ VM stopped (forced)"
        else
            echo ""
            echo "❌ Failed to stop VM - check manually"
            exit 1
        fi
    fi
}

cmd_restart() {
    echo "🔄 Restarting VM $VM_ID ($VM_NAME)..."
    
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    echo "📊 VM Status: $VM_ID ($VM_NAME)"
    echo "================================"
    echo ""
    
    check_vm_exists
    
    local status=$(get_vm_status)
    
    echo "Status: $status"
    
    if [ "$status" = "running" ]; then
        echo ""
        
        # Get IP
        local vm_ip=$(get_vm_ip)
        if [ -n "$vm_ip" ]; then
            echo "IP Address: $vm_ip"
        else
            echo "IP Address: (detecting...)"
        fi
        
        # Get uptime
        local uptime=$(qm status $VM_ID | grep -oP 'uptime: \K.*' || echo "unknown")
        echo "Uptime: $uptime"
        
        # Get CPU usage
        echo ""
        echo "Resources:"
        qm status $VM_ID | grep -E '(cpu|mem|disk|net)' || true
        
        echo ""
        echo "🌐 Access:"
        if [ -n "$vm_ip" ]; then
            echo "   SSH: ssh $VM_USER@$vm_ip"
            echo "   VNC: https://$DOMAIN/host1/vnc/vnc_lite.html"
        fi
    fi
    
    echo ""
    echo "Configuration:"
    echo "   Memory: ${VM_MEMORY}MB"
    echo "   Cores: $VM_CORES"
    echo "   Disk: $VM_DISK_SIZE"
    echo "   Bridge: $VM_BRIDGE"
    
    echo ""
    echo "📝 Quick commands:"
    echo "   Console: ./launch.sh console"
    echo "   SSH: ./launch.sh ssh"
    echo "   Stop: ./launch.sh stop"
}

cmd_console() {
    echo "🖥️  Opening VM console..."
    echo "   Press Ctrl+O to exit"
    echo ""
    
    check_vm_exists
    
    qm terminal $VM_ID
}

cmd_ssh() {
    echo "🔐 Connecting to VM via SSH..."
    
    check_vm_exists
    
    local status=$(get_vm_status)
    if [ "$status" != "running" ]; then
        echo "❌ VM is not running"
        echo "   Start it with: ./launch.sh start"
        exit 1
    fi
    
    local vm_ip=$(get_vm_ip)
    
    if [ -z "$vm_ip" ]; then
        echo "❌ Unable to detect VM IP"
        echo "   Options:"
        echo "   1. Wait a few seconds and try again"
        echo "   2. Check console: ./launch.sh console"
        echo "   3. Check DHCP server"
        exit 1
    fi
    
    echo "🌐 Connecting to $VM_USER@$vm_ip..."
    echo ""
    
    ssh "$VM_USER@$vm_ip"
}

cmd_snapshot() {
    local snapshot_name=$1
    
    if [ -z "$snapshot_name" ]; then
        echo "❌ Error: Snapshot name required"
        echo "   Usage: ./launch.sh snapshot <name>"
        echo "   Example: ./launch.sh snapshot before-update"
        exit 1
    fi
    
    echo "📸 Creating snapshot: $snapshot_name"
    
    check_vm_exists
    
    qm snapshot $VM_ID "$snapshot_name" --description "Created: $(date '+%Y-%m-%d %H:%M:%S')"
    
    echo "✅ Snapshot created"
    echo ""
    echo "📋 All snapshots:"
    qm listsnapshot $VM_ID
    echo ""
    echo "📝 To rollback: ./launch.sh rollback $snapshot_name"
}

cmd_rollback() {
    local snapshot_name=$1
    
    if [ -z "$snapshot_name" ]; then
        echo "📋 Available snapshots for VM $VM_ID:"
        echo ""
        qm listsnapshot $VM_ID
        echo ""
        echo "Usage: ./launch.sh rollback <snapshot-name>"
        exit 1
    fi
    
    echo "⏪ Rolling back to snapshot: $snapshot_name"
    echo "   ⚠️  This will revert VM to snapshot state"
    echo ""
    read -p "Continue? (y/N) " -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
    
    check_vm_exists
    
    # Stop VM if running
    local status=$(get_vm_status)
    if [ "$status" = "running" ]; then
        echo "🛑 Stopping VM..."
        qm shutdown $VM_ID
        wait_for_vm 60 "stopped"
    fi
    
    echo "⏪ Rolling back..."
    qm rollback $VM_ID "$snapshot_name"
    
    echo "✅ Rollback complete"
    echo ""
    read -p "Start VM now? (Y/n) " -r
    echo
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cmd_start
    fi
}

cmd_backup() {
    echo "💾 Creating backup of VM $VM_ID..."
    
    check_vm_exists
    
    local backup_dir="/var/lib/vz/dump"
    local backup_file="vzdump-qemu-${VM_ID}-$(date +%Y_%m_%d-%H_%M_%S).vma.zst"
    
    echo "   File: $backup_dir/$backup_file"
    echo "   Compression: zstd"
    echo ""
    
    vzdump $VM_ID --mode snapshot --compress zstd --dumpdir "$backup_dir"
    
    echo ""
    echo "✅ Backup complete"
    echo ""
    echo "📋 Backup location:"
    ls -lh "$backup_dir" | grep "vzdump-qemu-${VM_ID}" | tail -1
}

cmd_info() {
    echo "ℹ️  VM Information: $VM_ID ($VM_NAME)"
    echo "========================================"
    echo ""
    
    check_vm_exists
    
    qm config $VM_ID
    
    echo ""
    echo "📊 Current Status:"
    qm status $VM_ID
    
    echo ""
    echo "📸 Snapshots:"
    qm listsnapshot $VM_ID 2>/dev/null || echo "   No snapshots"
}

cmd_logs() {
    echo "📜 VM Logs: $VM_ID ($VM_NAME)"
    echo "============================="
    echo ""
    
    check_vm_exists
    
    echo "Recent VM events (from syslog):"
    echo ""
    tail -n 50 /var/log/syslog | grep "qemu\[$VM_ID\]" || echo "No recent logs found"
}

cmd_resize() {
    echo "📏 Resize VM Resources"
    echo "======================"
    echo ""
    echo "Current configuration:"
    echo "   Memory: ${VM_MEMORY}MB"
    echo "   Cores: $VM_CORES"
    echo "   Disk: $VM_DISK_SIZE"
    echo ""
    echo "What would you like to resize?"
    echo "   1) Memory (RAM)"
    echo "   2) CPU cores"
    echo "   3) Disk size"
    echo "   4) Cancel"
    echo ""
    read -p "Choice (1-4): " choice
    
    case $choice in
        1)
            read -p "New memory size in MB (current: $VM_MEMORY): " new_mem
            if [ -n "$new_mem" ]; then
                echo "🛑 Stopping VM..."
                cmd_stop
                echo "📏 Resizing memory to ${new_mem}MB..."
                qm set $VM_ID --memory $new_mem
                echo "✅ Memory resized"
                read -p "Start VM now? (Y/n) " -r
                if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                    cmd_start
                fi
            fi
            ;;
        2)
            read -p "New CPU cores (current: $VM_CORES): " new_cores
            if [ -n "$new_cores" ]; then
                echo "🛑 Stopping VM..."
                cmd_stop
                echo "📏 Resizing CPU to ${new_cores} cores..."
                qm set $VM_ID --cores $new_cores
                echo "✅ CPU resized"
                read -p "Start VM now? (Y/n) " -r
                if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                    cmd_start
                fi
            fi
            ;;
        3)
            read -p "Increase disk by (e.g., +10G): " disk_increase
            if [ -n "$disk_increase" ]; then
                echo "📏 Resizing disk by $disk_increase..."
                qm resize $VM_ID scsi0 $disk_increase
                echo "✅ Disk resized"
                echo ""
                echo "📝 Inside VM, run:"
                echo "   sudo growpart /dev/sda 1"
                echo "   sudo resize2fs /dev/sda1"
            fi
            ;;
        *)
            echo "Cancelled"
            ;;
    esac
}

# ============================================
# MAIN
# ============================================

COMMAND=${1:-help}

case $COMMAND in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    console)
        cmd_console
        ;;
    ssh)
        cmd_ssh
        ;;
    snapshot)
        cmd_snapshot "$2"
        ;;
    rollback)
        cmd_rollback "$2"
        ;;
    backup)
        cmd_backup
        ;;
    info)
        cmd_info
        ;;
    logs)
        cmd_logs
        ;;
    resize)
        cmd_resize
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        show_usage
        exit 1
        ;;
esac

