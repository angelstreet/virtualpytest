#!/bin/bash

# Simple log reset function - truncates log if over 30MB
reset_log_if_large() {
  local logfile="$1"
  local max_size_mb=30
  
  # Check if log file exists and its size
  if [ -f "$logfile" ]; then
    local size_mb=$(du -m "$logfile" | cut -f1)
    if [ "$size_mb" -ge "$max_size_mb" ]; then
      echo "$(date): Log $logfile exceeded ${max_size_mb}MB, resetting..." >> "${logfile}"
      > "$logfile"  # Truncate the file
      echo "$(date): Log reset" >> "${logfile}"
    fi
  fi
}

# Log file
CLEAN_LOG="/tmp/clean.log"

# Clear log at start of each run to show only current execution
> "$CLEAN_LOG"
echo "$(date): Starting cleanup run" >> "$CLEAN_LOG"

# Read active capture directories from centralized config file
ACTIVE_CAPTURES_FILE="/tmp/active_captures.conf"

if [ -f "$ACTIVE_CAPTURES_FILE" ]; then
  echo "$(date): Loading capture directories from $ACTIVE_CAPTURES_FILE" >> "$CLEAN_LOG"
  
  # Read capture directories from config file (one per line)
  CAPTURE_DIRS=()
  while IFS= read -r capture_base; do
    # Each line contains base capture directory (e.g., /var/www/html/stream/capture1)
    if [ -n "$capture_base" ]; then
      # Add /captures subdirectory
      CAPTURE_DIRS+=("${capture_base}/captures")
    fi
  done < "$ACTIVE_CAPTURES_FILE"
  
  echo "$(date): Loaded ${#CAPTURE_DIRS[@]} capture directories from config" >> "$CLEAN_LOG"
else
  echo "$(date): WARNING: $ACTIVE_CAPTURES_FILE not found, using fallback directories" >> "$CLEAN_LOG"
  
  # Fallback to default directories if config file doesn't exist
  CAPTURE_DIRS=(
    "/var/www/html/stream/capture1/captures"
    "/var/www/html/stream/capture2/captures"
  )
fi

# Process each directory - clean both parent and captures directory in one loop
for CAPTURE_DIR in "${CAPTURE_DIRS[@]}"; do
  # Get parent directory
  PARENT_DIR=$(dirname "$CAPTURE_DIR")
  
  # Clean parent directory - DELETE OLD SEGMENTS (24h retention - TIME-BASED)
  if [ -d "$PARENT_DIR" ]; then
    echo "$(date): Cleaning parent directory $PARENT_DIR (24h segment retention)" >> "$CLEAN_LOG"
    
    # Delete segments older than 24 hours (1440 minutes) - TIME-BASED for all segment durations
    find "$PARENT_DIR" -maxdepth 1 -name "segment_*.ts" -mmin +1440 -delete -printf "$(date): Deleted old segment %p\n" >> "$CLEAN_LOG" 2>&1
    
    # Clean other files but preserve recent segments and m3u8 files
    find "$PARENT_DIR" -maxdepth 1 -type f -not -name "segment_*.ts" -not -name "*.m3u8" -mmin +10 -delete -printf "$(date): Deleted parent file %p\n" >> "$CLEAN_LOG" 2>&1
    reset_log_if_large "$CLEAN_LOG"
  fi
  
  # Clean captures directory - DELETE OLD CAPTURE FILES (5min retention - heatmap captures them every minute)
  if [ -d "$CAPTURE_DIR" ]; then
    echo "$(date): Cleaning captures directory $CAPTURE_DIR (5min retention)" >> "$CLEAN_LOG"
    
    # Delete capture files older than 5 minutes (heatmap processor captures state every minute)
    find "$CAPTURE_DIR" -type f -name "capture_*.jpg" -mmin +5 -delete -printf "$(date): Deleted old capture %p\n" >> "$CLEAN_LOG" 2>&1
    find "$CAPTURE_DIR" -type f -name "capture_*.json" -mmin +5 -delete -printf "$(date): Deleted old analysis %p\n" >> "$CLEAN_LOG" 2>&1
    
    # Clean other old files but preserve recent ones
    find "$CAPTURE_DIR" -type f -not -name "capture_*" -mmin +10 -delete -printf "$(date): Deleted other file %p\n" >> "$CLEAN_LOG" 2>&1
    reset_log_if_large "$CLEAN_LOG"
  fi
done