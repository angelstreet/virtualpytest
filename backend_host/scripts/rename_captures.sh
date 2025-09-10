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

# Function to process a file pair atomically
process_file() {
  local filepath="$1"
  
  # Determine file type and find pair
  local original_path thumbnail_path
  if [[ "$filepath" =~ capture_[0-9]+\.jpg$ ]]; then
    original_path="$filepath"
    thumbnail_path="${filepath%%.jpg}_thumbnail.jpg"
  elif [[ "$filepath" =~ capture_[0-9]+_thumbnail\.jpg$ ]]; then
    thumbnail_path="$filepath"
    original_path="${filepath%%_thumbnail.jpg}.jpg"
  else
    return
  fi
  
  # Wait briefly for pair if missing
  if [ ! -f "$original_path" ] || [ ! -f "$thumbnail_path" ]; then
    sleep 0.1
    if [ ! -f "$original_path" ] || [ ! -f "$thumbnail_path" ]; then
      return  # Skip, will be processed on next event
    fi
  fi
  
  # Process both files atomically
  process_capture_pair "$original_path" "$thumbnail_path"
}

# Removed wait_for_file_stability function - using close_write event instead

# Function to process capture file pairs atomically
process_capture_pair() {
  local original_path="$1"
  local thumbnail_path="$2"
  
  if [ ! -f "$original_path" ] || [ ! -f "$thumbnail_path" ]; then
    echo "File pair incomplete: $original_path or $thumbnail_path missing" >> "$RENAME_LOG"
    return
  fi
  
  start_time=$(date +%s.%N)
  
  # Extract frame number from original filename
  local frame_num=$(basename "$original_path" | grep -o '[0-9]\+' | head -1)
  if [ -z "$frame_num" ]; then
    echo "Could not extract frame number from $original_path" >> "$RENAME_LOG"
    return
  fi
  
  # Validate frame number
  local frame_int=$((10#$frame_num))
  if [ "$frame_int" -lt 1 ] || [ "$frame_int" -gt 99999 ]; then
    echo "Frame number $frame_num out of valid range for $original_path" >> "$RENAME_LOG"
    return
  fi
  
  # Determine FPS based on source
  local fps=5
  if [[ "$original_path" =~ capture3 ]]; then
    fps=2  # VNC display uses 2 FPS
  fi
  
  # Calculate suffix from frame number
  local suffix=$(( (frame_int - 1) % fps ))
  
  # Use original file creation time as timestamp
  local final_timestamp=$(TZ="Europe/Zurich" date -r "$original_path" +%Y%m%d%H%M%S)
  
  local CAPTURE_DIR=$(dirname "$original_path")
  local base_newname="${CAPTURE_DIR}/capture_${final_timestamp}"
  
  # Generate new filenames
  local new_original new_thumbnail
  if [ $suffix -eq 0 ]; then
    new_original="${base_newname}.jpg"
    new_thumbnail="${base_newname}_thumbnail.jpg"
  else
    new_original="${base_newname}_${suffix}.jpg"
    new_thumbnail="${base_newname}_${suffix}_thumbnail.jpg"
  fi
  
  # Check if targets already exist
  if [ -f "$new_original" ] || [ -f "$new_thumbnail" ]; then
    echo "Target files already exist, skipping pair: $(basename "$original_path")" >> "$RENAME_LOG"
    return
  fi
  
  # Atomic rename: both files or neither
  if mv "$original_path" "$new_original" && mv "$thumbnail_path" "$new_thumbnail"; then
    echo "Renamed pair: $(basename "$original_path") + $(basename "$thumbnail_path") -> $(basename "$new_original") + $(basename "$new_thumbnail")" >> "$RENAME_LOG"
  else
    echo "Failed to rename pair atomically: $(basename "$original_path")" >> "$RENAME_LOG"
    return
  fi
  
  end_time=$(date +%s.%N)
  echo "Processed pair in $(echo "$end_time - $start_time" | bc) seconds" >> "$RENAME_LOG"
  
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
# Trigger on close_write to ensure file is fully written
inotifywait -m "${EXISTING_DIRS[@]}" -e close_write --format '%w%f' |
  while read -r filepath; do
    process_file "$filepath"
  done