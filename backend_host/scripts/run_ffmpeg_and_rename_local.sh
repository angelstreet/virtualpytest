#!/bin/bash

# Configuration array for grabbers: source|audio_device|capture_dir|fps
# Hardware video devices: /dev/video0, /dev/video2, etc.
# VNC displays: :1, :99, etc. no audio for now then pulseaudio
declare -A GRABBERS=(
  ["1"]="/dev/video2|plughw:3,0|/var/www/html/stream/capture2|10"
  ["2"]=":1|null|/var/www/html/stream/capture3|1"
)

# Simple log reset function - truncates log if over 30MB
reset_log_if_large() {
  local logfile="$1" max_size_mb=30
  
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

# Function to detect source type (hardware video device or VNC display)
detect_source_type() {
  local source="$1"
  if [[ "$source" =~ ^/dev/video[0-9]+$ ]]; then
    echo "v4l2"
  elif [[ "$source" =~ ^:[0-9]+$ ]]; then
    echo "x11grab"
  else
    echo "unknown"
  fi
}



# Function to get VNC display resolution
get_vnc_resolution() {
  local display="$1"
  local resolution=$(xdpyinfo -display "$display" 2>/dev/null | grep dimensions | awk '{print $2}')
  if [ -z "$resolution" ]; then
    resolution="1024x768"
  fi
  echo "$resolution"
}

# Function to kill existing processes for a specific grabber
kill_existing_processes() {
  local output_dir=$1 source=$2
  echo "Checking for existing processes for $source..."
  pkill -9 -f "ffmpeg.*$source" 2>/dev/null && echo "Killed existing ffmpeg for $source"
  pkill -9 -f "rename_captures.sh.*$output_dir" 2>/dev/null && echo "Killed existing rename_captures.sh for $output_dir"
  pkill -9 -f "clean_captures.sh.*$output_dir" 2>/dev/null && echo "Killed existing clean_captures.sh for $output_dir"
}

# Cleanup function
cleanup() {
  local ffmpeg_pid=$1 rename_pid=$2 clean_pid=$3 source=$4

  echo "Caught signal, cleaning up for $source..."
  [ -n "$ffmpeg_pid" ] && kill "$ffmpeg_pid" 2>/dev/null && echo "Killed ffmpeg (PID: $ffmpeg_pid)"
  [ -n "$rename_pid" ] && kill "$rename_pid" 2>/dev/null && echo "Killed rename_captures.sh (PID: $rename_pid)"
  [ -n "$clean_pid" ] && kill "$clean_pid" 2>/dev/null && echo "Killed clean_captures.sh (PID: $clean_pid)"
}

# Function to start processes for a single grabber
start_grabber() {
  local source=$1 audio_device=$2 capture_dir=$3 index=$4 fps=$5

  # Detect source type
  local source_type=$(detect_source_type "$source")
  if [ "$source_type" = "unknown" ]; then
    echo "ERROR: Unknown source type for $source"
    return 1
  fi



  # Create capture directory
  mkdir -p "$capture_dir/captures"

  # Kill existing processes
  kill_existing_processes "$capture_dir" "$source"

  # Build FFmpeg command based on source type
  if [ "$source_type" = "v4l2" ]; then
    # Hardware video device
    FFMPEG_CMD="/usr/bin/ffmpeg -y -f v4l2 -framerate \"$fps\" -video_size 1920x1080 -i $source \
      -f alsa -thread_queue_size 8192 -i \"$audio_device\" \
      -filter_complex \"[0:v]split=2[stream][capture];[stream]scale=640:360[streamout];[capture]fps=1[captureout]\" \
      -map \"[streamout]\" -map 1:a \
      -c:v libx264 -preset veryfast -tune zerolatency -crf 28 -maxrate 1200k -bufsize 2400k -g 30 \
      -pix_fmt yuv420p -profile:v baseline -level 3.0 \
      -c:a aac -b:a 64k -ar 44100 -ac 2 \
      -f hls -hls_time 2 -hls_list_size 300 -hls_flags delete_segments \
      -hls_segment_filename $capture_dir/segment_%03d.ts \
      $capture_dir/output.m3u8 \
      -map \"[captureout]\" -c:v mjpeg -q:v 5 -r 1 -f image2 \
      $capture_dir/captures/test_capture_%06d.jpg"
  elif [ "$source_type" = "x11grab" ]; then
    # VNC display - use direct access (xhost +local:www-data already configured)
    local resolution=$(get_vnc_resolution "$source")
    
    # Simple DISPLAY export - no XAUTHORITY needed with xhost +local:
    export DISPLAY="$source"
    
    FFMPEG_CMD="DISPLAY=\"$source\" /usr/bin/ffmpeg -y -f x11grab -framerate \"$fps\" -video_size $resolution -i $source \
      -an \
      -filter_complex \"[0:v]split=2[stream][capture];[stream]scale=512:384[streamout];[capture]fps=1[captureout]\" \
      -map \"[streamout]\" \
      -c:v libx264 -preset veryfast -tune zerolatency -crf 28 -maxrate 1200k -bufsize 2400k -g 30 \
      -pix_fmt yuv420p -profile:v baseline -level 3.0 \
      -f hls -hls_time 2 -hls_list_size 300 -hls_flags delete_segments \
      -hls_segment_filename $capture_dir/segment_%03d.ts \
      $capture_dir/output.m3u8 \
      -map \"[captureout]\" -c:v mjpeg -q:v 5 -r 1 -f image2 \
      $capture_dir/captures/test_capture_%06d.jpg"
  else
    echo "ERROR: Unsupported source type: $source_type"
    return 1
  fi



  # Start ffmpeg
  echo "Starting ffmpeg for $source ($source_type) with audio: $audio_device..."
  local FFMPEG_LOG="/tmp/ffmpeg_output_${index}.log"
  reset_log_if_large "$FFMPEG_LOG"
  eval $FFMPEG_CMD > "$FFMPEG_LOG" 2>&1 &
  local FFMPEG_PID=$!
  echo "Started ffmpeg for $source with PID: $FFMPEG_PID"

  # Start rename script
  /usr/local/bin/rename_captures.sh "$capture_dir" &
  local RENAME_PID=$!
  echo "Started rename_captures.sh for $capture_dir with PID: $RENAME_PID"

  # Start clean script
  while true; do
    /usr/local/bin/clean_captures.sh "$capture_dir"
    sleep 300
  done &
  local CLEAN_PID=$!
  echo "Started clean_captures.sh loop for $capture_dir with PID: $CLEAN_PID"

  # Set up trap for this grabber
  trap "cleanup $FFMPEG_PID $RENAME_PID $CLEAN_PID $source" SIGINT SIGTERM
}

# Print configuration and check availability
echo "=== Unified Capture Configuration ==="
for index in "${!GRABBERS[@]}"; do
  IFS='|' read -r source audio_device capture_dir fps <<< "${GRABBERS[$index]}"
  
  source_type=$(detect_source_type "$source")
  
  echo "Grabber $index:"
  echo "  Source: $source ($source_type)"
  if [ "$source_type" = "x11grab" ]; then
    resolution=$(get_vnc_resolution "$source" 2>/dev/null || echo "1024x768")
    echo "  Resolution: $resolution"
  fi
  echo "  Audio: $audio_device"
  echo "  Output: $capture_dir"
  echo "  FPS: $fps"
  echo
done

# Main loop to start all grabbers
PIDS=()
for index in "${!GRABBERS[@]}"; do
  IFS='|' read -r source audio_device capture_dir fps <<< "${GRABBERS[$index]}"
  start_grabber "$source" "$audio_device" "$capture_dir" "$index" "$fps" &
  PIDS+=($!)
done

# Wait for all grabber processes
wait "${PIDS[@]}"

# Keep script alive for systemd compatibility
while true; do
  sleep 3600
done