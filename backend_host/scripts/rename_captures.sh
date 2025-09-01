#!/bin/bash

# Set timezone to Zurich
export TZ="Europe/Zurich"

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

# Log files
RENAME_LOG="/tmp/rename.log"

# Check logs on startup
reset_log_if_large "$RENAME_LOG"

# Array of possible capture directories
CAPTURE_DIRS=(
  "/var/www/html/stream/capture1/captures"
  "/var/www/html/stream/capture2/captures"
  "/var/www/html/stream/capture3/captures"
  "/var/www/html/stream/capture4/captures"
)

# Function to process a file
process_file() {
  local filepath="$1"
  
  # Handle full resolution captures (new pattern: capture_0001.jpg)
  if [[ "$filepath" =~ capture_[0-9]+\.jpg$ ]]; then
    process_capture_file "$filepath" "full"
  # Handle thumbnail captures (new pattern: capture_0001_thumbnail.jpg)
  elif [[ "$filepath" =~ capture_[0-9]+_thumbnail\.jpg$ ]]; then
    process_capture_file "$filepath" "thumbnail"
  fi
}

# Function to process capture files with smart grouping
process_capture_file() {
  local filepath="$1"
  local file_type="$2"  # "full" or "thumbnail"
  
  if [ ! -f "$filepath" ]; then
    echo "File $filepath does not exist or is not accessible" >> "$RENAME_LOG"
    return
  fi
  
  sleep 0.01
  start_time=$(date +%s.%N)
  
  # Extract frame number from filename (e.g., capture_0001.jpg -> 0001)
  local frame_num=$(basename "$filepath" | grep -o '[0-9]\+' | head -1)
  if [ -z "$frame_num" ]; then
    echo "Could not extract frame number from $filepath" >> "$RENAME_LOG"
    return
  fi
  
  # Convert to integer for calculations
  local frame_int=$((10#$frame_num))
  
  # Determine FPS based on source (5 FPS for hardware, 2 FPS for VNC)
  local fps=5
  if [[ "$filepath" =~ capture3 ]]; then
    fps=2  # VNC display uses 2 FPS
  fi
  
  # Calculate group and suffix from frame number (simple approach)
  local group=$(( (frame_int - 1) / fps ))
  local suffix=$(( (frame_int - 1) % fps ))
  
  # Use file creation time as base timestamp (simple!)
  local final_timestamp=$(TZ="Europe/Zurich" date -r "$filepath" +%Y%m%d%H%M%S)
  
  local CAPTURE_DIR=$(dirname "$filepath")
  local base_newname="${CAPTURE_DIR}/capture_${final_timestamp}"
  
  # Determine final filename based on suffix
  if [ "$file_type" = "thumbnail" ]; then
    if [ $suffix -eq 0 ]; then
      # First file in group - no suffix
      newname="${base_newname}_thumbnail.jpg"
    else
      # Subsequent files - add suffix
      newname="${base_newname}_${suffix}_thumbnail.jpg"
    fi
  else
    if [ $suffix -eq 0 ]; then
      # First file in group - no suffix
      newname="${base_newname}.jpg"
    else
      # Subsequent files - add suffix
      newname="${base_newname}_${suffix}.jpg"
    fi
  fi
  
  # Rename the file
  if mv -f "$filepath" "$newname" 2>>"$RENAME_LOG"; then
    if [ $suffix -eq 0 ]; then
      echo "Renamed $(basename "$filepath") to $(basename "$newname") (first in group, $file_type) at $(date)" >> "$RENAME_LOG"
    else
      echo "Renamed $(basename "$filepath") to $(basename "$newname") (suffix $suffix, $file_type) at $(date)" >> "$RENAME_LOG"
    fi
    echo "Processed $file_type image: $(basename "$newname")" >> "$RENAME_LOG"
  else
    echo "Failed to rename $filepath to $newname" >> "$RENAME_LOG"
  fi
  
  end_time=$(date +%s.%N)
  echo "Processed $filepath in $(echo "$end_time - $start_time" | bc) seconds" >> "$RENAME_LOG"
  
  # Check log sizes after processing
  reset_log_if_large "$RENAME_LOG"
}

# Filter existing directories
EXISTING_DIRS=()
for CAPTURE_DIR in "${CAPTURE_DIRS[@]}"; do
  if [ -d "$CAPTURE_DIR" ]; then
    EXISTING_DIRS+=("$CAPTURE_DIR")
    echo "Will watch $CAPTURE_DIR for new files..." >> "$RENAME_LOG"
  else
    echo "Directory $CAPTURE_DIR does not exist, skipping..." >> "$RENAME_LOG"
  fi
done

# Exit if no directories exist
if [ ${#EXISTING_DIRS[@]} -eq 0 ]; then
  echo "No valid directories to watch, exiting." >> "$RENAME_LOG"
  exit 1
fi

# Watch all existing directories with a single inotifywait
inotifywait -m "${EXISTING_DIRS[@]}" -e create --format '%w%f' |
  while read -r filepath; do
    process_file "$filepath"
  done