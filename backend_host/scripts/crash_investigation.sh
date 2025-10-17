#!/bin/bash
# Crash Investigation & Monitoring Setup Script
# Run this on any Raspberry Pi host to investigate crashes and setup monitoring
# Usage: ./crash_investigation.sh

set -e

LOG_DIR="${HOME}/crash_monitoring"
REPORT_FILE="${LOG_DIR}/investigation_$(date +%Y%m%d_%H%M%S).txt"

mkdir -p "${LOG_DIR}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "$1" | tee -a "${REPORT_FILE}"
}

header() {
    log "\n${GREEN}=== $1 ===${NC}"
}

alert() {
    log "${RED}⚠️  $1${NC}"
}

warn() {
    log "${YELLOW}⚠️  $1${NC}"
}

success() {
    log "${GREEN}✅ $1${NC}"
}

log "CRASH INVESTIGATION REPORT - $(hostname)"
log "Generated: $(date)"
log "User: ${USER}"

# 1. CURRENT SYSTEM STATUS
header "CURRENT SYSTEM STATUS"
log "Uptime: $(uptime)"
log "Temperature: $(vcgencmd measure_temp 2>/dev/null || echo 'N/A')"
THROTTLED=$(vcgencmd get_throttled 2>/dev/null | cut -d'=' -f2 || echo 'N/A')
log "Throttled: ${THROTTLED}"

if [ "$THROTTLED" != "0x0" ] && [ "$THROTTLED" != "N/A" ]; then
    alert "THROTTLING DETECTED! Code: ${THROTTLED}"
fi

# 2. MEMORY CHECK
header "MEMORY STATUS"
MEM_INFO=$(free | grep Mem)
MEM_TOTAL=$(echo $MEM_INFO | awk '{print $2}')
MEM_USED=$(echo $MEM_INFO | awk '{print $3}')
MEM_PERCENT=$(echo "scale=2; $MEM_USED * 100 / $MEM_TOTAL" | bc)
SWAP_USED=$(free | grep Swap | awk '{print $3}')

log "Memory: ${MEM_PERCENT}% used"
log "Swap: ${SWAP_USED}KB used"

if (( $(echo "$MEM_PERCENT > 90" | bc -l) )); then
    alert "CRITICAL: Memory usage ${MEM_PERCENT}% is very high!"
elif (( $(echo "$MEM_PERCENT > 80" | bc -l) )); then
    warn "WARNING: Memory usage ${MEM_PERCENT}% is high"
fi

if [ "$SWAP_USED" != "0" ]; then
    warn "Swap is being used (${SWAP_USED}KB) - possible memory pressure"
fi

# 3. CPU LOAD
header "CPU LOAD"
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
CPU_COUNT=$(nproc)
log "Load average: ${LOAD_AVG} on ${CPU_COUNT} cores"

if (( $(echo "$LOAD_AVG > 8" | bc -l) )); then
    alert "CRITICAL: Load average ${LOAD_AVG} is very high!"
elif (( $(echo "$LOAD_AVG > 6" | bc -l) )); then
    warn "WARNING: Load average ${LOAD_AVG} is high"
fi

# 4. TOP PROCESSES
header "TOP CPU CONSUMERS"
ps aux --sort=-%cpu | head -6 | tee -a "${REPORT_FILE}"

CAPTURE_CPU=$(ps aux | grep "[c]apture_monitor.py" | awk '{print $3}')
if [ -n "$CAPTURE_CPU" ]; then
    log "\ncapture_monitor.py CPU: ${CAPTURE_CPU}%"
    if (( $(echo "$CAPTURE_CPU > 120" | bc -l) )); then
        alert "capture_monitor.py is using ${CAPTURE_CPU}% CPU - EXCESSIVE!"
    fi
fi

header "TOP MEMORY CONSUMERS"
ps aux --sort=-%mem | head -6 | tee -a "${REPORT_FILE}"

# 5. DISK SPACE
header "DISK SPACE"
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
log "Disk usage: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -gt 90 ]; then
    alert "CRITICAL: Disk usage ${DISK_USAGE}% exceeds 90%"
elif [ "$DISK_USAGE" -gt 80 ]; then
    warn "WARNING: Disk usage ${DISK_USAGE}% exceeds 80%"
fi

# 6. CHECK FOR OOM KILLER
header "OOM KILLER CHECK"
OOM_COUNT=$(dmesg -T 2>/dev/null | grep -c "Out of memory\|oom-killer\|Killed process" || echo 0)
if [ "$OOM_COUNT" -gt 0 ]; then
    alert "OOM KILLER DETECTED! ${OOM_COUNT} events found"
    dmesg -T | grep "Out of memory\|oom-killer\|Killed process" | tail -5 | tee -a "${REPORT_FILE}"
else
    success "No OOM killer activity detected"
fi

# 7. CHECK JOURNAL PERSISTENCE
header "LOG PERSISTENCE CHECK"
if [ -d "/var/log/journal" ]; then
    JOURNAL_SIZE=$(du -sh /var/log/journal 2>/dev/null | awk '{print $1}')
    success "Persistent journal enabled (${JOURNAL_SIZE})"
else
    alert "Persistent journal NOT enabled - logs lost on reboot!"
fi

# 8. BOOT HISTORY
header "BOOT HISTORY"
last reboot | head -5 | tee -a "${REPORT_FILE}"

BOOTS=$(journalctl --list-boots 2>/dev/null | wc -l || echo 0)
log "\nAvailable boot logs: ${BOOTS}"

if [ "$BOOTS" -le 1 ]; then
    warn "Only current boot available - cannot analyze previous crash"
else
    success "${BOOTS} boots available for analysis"
fi

# 9. CHECK CRITICAL SERVICES
header "CRITICAL SERVICES CHECK"
if pgrep -f "capture_monitor.py" > /dev/null; then
    success "capture_monitor.py is running"
else
    alert "capture_monitor.py is NOT running!"
fi

if pgrep -f "transcript_accumulator.py" > /dev/null; then
    success "transcript_accumulator.py is running"
else
    alert "transcript_accumulator.py is NOT running!"
fi

FFMPEG_COUNT=$(pgrep -c ffmpeg || echo 0)
log "FFmpeg processes: ${FFMPEG_COUNT}"
if [ "$FFMPEG_COUNT" -lt 4 ]; then
    warn "Only ${FFMPEG_COUNT} ffmpeg processes (expected 4)"
fi

# Check FFmpeg logs for specific errors (always run)
header "FFMPEG LOGS CHECK"
log "Checking FFmpeg logs for errors (last 300 lines)..."

for logfile in /tmp/ffmpeg_output_*.log; do
    if [ -f "$logfile" ]; then
        log "\n--- $(basename $logfile) ---"
        LAST_LINES=$(tail -300 "$logfile" 2>/dev/null || true)
        ERROR_FOUND=false
        
        # Check for disk space error
        if echo "$LAST_LINES" | grep -q "No space left on device"; then
            alert "$(basename $logfile): No space left on device!"
            echo "$LAST_LINES" | grep "No space left on device" | tail -2 | tee -a "${REPORT_FILE}"
            ERROR_FOUND=true
        fi
        
        # Check for ALSA errors
        if echo "$LAST_LINES" | grep -qi "alsa"; then
            alert "$(basename $logfile): ALSA audio codec issue detected!"
            echo "$LAST_LINES" | grep -i "alsa" | tail -3 | tee -a "${REPORT_FILE}"
            ERROR_FOUND=true
        fi
        
        # Check for video device errors
        if echo "$LAST_LINES" | grep -qE "/dev/video[0-9]|Cannot open video device|No such device"; then
            alert "$(basename $logfile): Video device not found!"
            echo "$LAST_LINES" | grep -E "/dev/video[0-9]|Cannot open video device|No such device" | tail -2 | tee -a "${REPORT_FILE}"
            ERROR_FOUND=true
        fi
        
        # Check for audio device (plughw) errors
        if echo "$LAST_LINES" | grep -qE "plughw:[0-9],0|Cannot open audio device"; then
            alert "$(basename $logfile): Audio device (plughw) not found!"
            echo "$LAST_LINES" | grep -E "plughw:[0-9],0|Cannot open audio device" | tail -2 | tee -a "${REPORT_FILE}"
            ERROR_FOUND=true
        fi
        
        if [ "$ERROR_FOUND" = false ]; then
            success "$(basename $logfile): No errors detected"
        fi
    fi
done

if ! ls /tmp/ffmpeg_output_*.log >/dev/null 2>&1; then
    warn "No FFmpeg log files found in /tmp/"
fi

# 10. CHECK IF MONITORING IS INSTALLED
header "MONITORING SYSTEM CHECK"

# Check if timer exists and is enabled (not just active, since timers wait for triggers)
if systemctl list-unit-files crash-monitor.timer 2>/dev/null | grep -q crash-monitor.timer; then
    TIMER_ENABLED=$(systemctl is-enabled crash-monitor.timer 2>/dev/null || echo "disabled")
    TIMER_ACTIVE=$(systemctl is-active crash-monitor.timer 2>/dev/null || echo "inactive")
    
    if [ "$TIMER_ENABLED" = "enabled" ]; then
        success "Crash monitoring is INSTALLED and ENABLED"
        log "Timer status: ${TIMER_ACTIVE}"
        systemctl status crash-monitor.timer --no-pager -l 2>/dev/null | head -10 | tee -a "${REPORT_FILE}"
    else
        warn "Crash monitoring timer exists but is NOT enabled"
        log "Enabling timer..."
        sudo systemctl enable crash-monitor.timer
        sudo systemctl start crash-monitor.timer
        success "Timer enabled and started"
    fi
else
    warn "Crash monitoring is NOT installed"
    log "\nInstalling crash monitoring..."
    
    # Enable persistent journald
    sudo mkdir -p /var/log/journal
    sudo systemd-tmpfiles --create --prefix /var/log/journal 2>/dev/null || true
    
    if ! grep -q "^Storage=persistent" /etc/systemd/journald.conf 2>/dev/null; then
        echo "Storage=persistent" | sudo tee -a /etc/systemd/journald.conf > /dev/null
        echo "SystemMaxUse=500M" | sudo tee -a /etc/systemd/journald.conf > /dev/null
        sudo systemctl restart systemd-journald
        success "Persistent journald enabled"
    fi
    
    # Create monitoring service
    MONITOR_SCRIPT="${LOG_DIR}/health_monitor.sh"
    cat > "${MONITOR_SCRIPT}" << 'EOFMONITOR'
#!/bin/bash
LOG_FILE="${HOME}/crash_monitoring/health_$(date +%Y%m%d).log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Temp: $(vcgencmd measure_temp) | Load: $(uptime | awk -F'load average:' '{print $2}') | Mem: $(free -h | grep Mem | awk '{print $3"/"$2}') | Disk: $(df -h / | tail -1 | awk '{print $5}')" >> "${LOG_FILE}"
ps aux --sort=-%cpu | head -5 >> "${LOG_FILE}"
dmesg -T | grep -i "oom\|killed" | tail -3 >> "${LOG_FILE}" 2>/dev/null || true
EOFMONITOR
    chmod +x "${MONITOR_SCRIPT}"
    
    # Create systemd service
    sudo tee /etc/systemd/system/crash-monitor.service > /dev/null << EOF
[Unit]
Description=System Health Monitor
[Service]
Type=oneshot
ExecStart=${MONITOR_SCRIPT}
User=${USER}
EOF

    sudo tee /etc/systemd/system/crash-monitor.timer > /dev/null << 'EOF'
[Unit]
Description=Health Monitor Timer
[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable crash-monitor.timer
    sudo systemctl start crash-monitor.timer
    
    success "Crash monitoring installed and started!"
fi

# 11. FINAL DIAGNOSIS
header "DIAGNOSIS SUMMARY"

if [ "$OOM_COUNT" -gt 0 ]; then
    alert "LIKELY CAUSE: Out of Memory (OOM) - System ran out of RAM"
    log "   → Check which processes were killed in dmesg"
    log "   → Consider reducing video quality or number of streams"
elif [ "$THROTTLED" != "0x0" ] && [ "$THROTTLED" != "N/A" ]; then
    alert "LIKELY CAUSE: Thermal throttling or power issues"
    log "   → Improve cooling or check power supply"
elif (( $(echo "$LOAD_AVG > 8" | bc -l) )); then
    alert "LIKELY CAUSE: CPU overload"
    log "   → Check capture_monitor.py CPU usage"
    log "   → Consider optimizing video processing"
elif (( $(echo "$MEM_PERCENT > 85" | bc -l) )); then
    warn "LIKELY CAUSE: High memory usage"
    log "   → Monitor for OOM events"
    log "   → Check memory leaks in Python processes"
else
    success "System appears healthy - crash cause unknown without previous boot logs"
    log "   → Wait for next crash with monitoring enabled"
    log "   → Then run: journalctl --boot=-1 --priority=0..3"
fi

log "\n${GREEN}=== INVESTIGATION COMPLETE ===${NC}"
log "Report saved: ${REPORT_FILE}"
log "\nNext steps:"
log "  1. Review findings above"
log "  2. Monitor: tail -f ${LOG_DIR}/health_\$(date +%Y%m%d).log"
log "  3. Check timer: systemctl list-timers crash-monitor.timer"
log "  4. After crash: journalctl --boot=-1 | grep -i error"
log "\nUseful commands:"
log "  • systemctl status crash-monitor.timer"
log "  • journalctl -u crash-monitor.service -f"
log "  • cat ${LOG_DIR}/health_\$(date +%Y%m%d).log"

echo ""
cat "${REPORT_FILE}"

