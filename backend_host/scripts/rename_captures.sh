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

# Optimized function to process thumbnail file and its original pair
process_thumbnail_file() {
  local thumbnail_path="$1"
  local original_path="${thumbnail_path%%_thumbnail.jpg}.jpg"
  
  local CAPTURE_DIR=$(dirname "$original_path")
  local device_name=$(basename "$(dirname "$CAPTURE_DIR")")
  
  # Check for original file (should already exist since thumbnail is created last)
  if [ ! -f "$original_path" ]; then
    sleep 0.1
    if [ ! -f "$original_path" ]; then
      return  # Skip if original still missing (rare edge case)
    fi
  fi

  # Add readiness check: confirm neither file is still open by any process
  for attempt in {1..2}; do
    if ! lsof "$original_path" >/dev/null 2>&1 && ! lsof "$thumbnail_path" >/dev/null 2>&1; then
      break  # Both closed, proceed
    fi
    if [ $attempt -eq 2 ]; then
      echo "$(date '+%H:%M:%S') [$device_name] Skipped pair due to files still open: $(basename "$original_path")" >> "$RENAME_LOG"
      return  # Still open after retry, skip
    fi
    sleep 0.05
  done
  
  # Process both files atomically
  process_capture_pair "$original_path" "$thumbnail_path"
}

# Removed wait_for_file_stability function - using close_write event instead

# Function to process capture file pairs atomically
process_capture_pair() {
  local original_path="$1"
  local thumbnail_path="$2"
  
  if [ ! -f "$original_path" ] || [ ! -f "$thumbnail_path" ]; then
    return
  fi
  
  # Extract frame number from original filename
  local frame_num=$(basename "$original_path" | grep -o '[0-9]\+' | head -1)
  if [ -z "$frame_num" ]; then
    local device_name=$(basename "$(dirname "$(dirname "$original_path")")")
    echo "$(date '+%H:%M:%S') [$device_name] No frame number found in filename: $(basename "$original_path")" >> "$RENAME_LOG"
    return
  fi
  
  # Determine FPS based on source
  local fps=5
  if [[ "$original_path" =~ capture3 ]]; then
    fps=2  # VNC display uses 2 FPS
  fi
  
  # Calculate suffix from frame number
  local frame_int=$((10#$frame_num))
  local suffix=$(( (frame_int - 1) % fps ))
  
  # Use original file creation time as timestamp
  local final_timestamp=$(TZ="Europe/Zurich" date -r "$original_path" +%Y%m%d%H%M%S)
  
  local CAPTURE_DIR=$(dirname "$original_path")
  local device_name=$(basename "$(dirname "$CAPTURE_DIR")")
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
    echo "$(date '+%H:%M:%S') [$device_name] Target files already exist, skipping: $(basename "$new_original")" >> "$RENAME_LOG"
    return
  fi
  
  # Atomic rename: both files or neither
  err=$( { mv "$original_path" "$new_original" && mv "$thumbnail_path" "$new_thumbnail"; } 2>&1 )
  if [ $? -eq 0 ]; then
    echo "$(date '+%H:%M:%S') [$device_name] Renamed pair: $(basename "$original_path") + $(basename "$thumbnail_path") -> $(basename "$new_original") + $(basename "$new_thumbnail")" >> "$RENAME_LOG"
  else
    echo "$(date '+%H:%M:%S') [$device_name] Failed to rename pair: $(basename "$original_path") + $(basename "$thumbnail_path") - Error: $err" >> "$RENAME_LOG"
    return
  fi
  
  reset_log_if_large "$RENAME_LOG"
}

# Filter existing directories
EXISTING_DIRS=()
for CAPTURE_DIR in "${CAPTURE_DIRS[@]}"; do
  if [ -d "$CAPTURE_DIR" ]; then
    EXISTING_DIRS+=("$CAPTURE_DIR")
  fi
done

# Exit if no directories exist
if [ ${#EXISTING_DIRS[@]} -eq 0 ]; then
  exit 1
fi

# Watch all existing directories with a single inotifywait
# Only trigger on thumbnail files (created last) for optimal performance
inotifywait -m "${EXISTING_DIRS[@]}" -e close_write --format '%w%f' |
  while read -r filepath; do
    # Only process thumbnail files (original should already exist)
    if [[ "$filepath" =~ capture_[0-9]+_thumbnail\.jpg$ ]]; then
      process_thumbnail_file "$filepath"
    fi
  done