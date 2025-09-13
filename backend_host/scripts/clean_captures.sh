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

# Array of possible capture directories
CAPTURE_DIRS=(
  "/var/www/html/stream/capture/captures"
  "/var/www/html/stream/capture1/captures"
  "/var/www/html/stream/capture2/captures"
  "/var/www/html/stream/capture3/captures"
  "/var/www/html/stream/capture4/captures"
)

# Process each directory - clean both parent and captures directory in one loop
for CAPTURE_DIR in "${CAPTURE_DIRS[@]}"; do
  # Get parent directory
  PARENT_DIR=$(dirname "$CAPTURE_DIR")
  
  # Clean parent directory (only files, not folders)
  if [ -d "$PARENT_DIR" ]; then
    echo "$(date): Cleaning parent directory $PARENT_DIR" >> "$CLEAN_LOG"
    # Specifically target segment files and other files in parent directory
    find "$PARENT_DIR" -maxdepth 1 -type f -name "segment_*.ts" -mmin +10 -delete -printf "$(date): Deleted segment file %p\n" >> "$CLEAN_LOG" 2>&1
    find "$PARENT_DIR" -maxdepth 1 -type f -not -name "segment_*.ts" -not -name "*.m3u8" -mmin +10 -delete -printf "$(date): Deleted other parent file %p\n" >> "$CLEAN_LOG" 2>&1
    reset_log_if_large "$CLEAN_LOG"
  fi
  
  # Clean captures directory
  if [ -d "$CAPTURE_DIR" ]; then
    echo "$(date): Cleaning captures directory $CAPTURE_DIR" >> "$CLEAN_LOG"
    find "$CAPTURE_DIR" -type f -mmin +10 -delete -printf "$(date): Deleted capture file %p\n" >> "$CLEAN_LOG" 2>&1
    reset_log_if_large "$CLEAN_LOG"
  fi
done