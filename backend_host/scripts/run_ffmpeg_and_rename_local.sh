#!/bin/bash

# ============================================================================
# MASTER CAPTURE CONFIGURATION - READS FROM .env FILE
# ============================================================================
# This script reads capture configuration from backend_host/src/.env file.
# The .env file is the SINGLE SOURCE OF TRUTH for all capture settings.
#
# To add a new capture: Edit backend_host/src/.env and restart service.
# To disable a capture: Prefix variable name with 'x' or comment with '#'
#
# Required .env variables per device:
#   HOST_VIDEO_SOURCE, HOST_VIDEO_AUDIO, HOST_VIDEO_CAPTURE_PATH, HOST_VIDEO_FPS
#   DEVICE*_VIDEO, DEVICE*_VIDEO_AUDIO, DEVICE*_VIDEO_CAPTURE_PATH, DEVICE*_VIDEO_FPS
#
# See CAPTURE_CONFIG.md for details.
# ============================================================================

# Find and load .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HOST_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$BACKEND_HOST_DIR/src/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

echo "Loading configuration from $ENV_FILE..."

# Load .env file (filter out comments and empty lines)
set -a
source <(grep -v '^#' "$ENV_FILE" | grep -v '^$' | grep -v '^x')
set +a

# Build GRABBERS array dynamically from .env
# Format: source|audio_device|capture_dir|input_fps
declare -A GRABBERS=()

# Check HOST configuration (if VIDEO_SOURCE is set and not disabled)
if [ -n "$HOST_VIDEO_SOURCE" ]; then
    GRABBERS["host"]="$HOST_VIDEO_SOURCE|${HOST_VIDEO_AUDIO:-null}|${HOST_VIDEO_CAPTURE_PATH}|${HOST_VIDEO_FPS:-2}"
    echo "✓ Added HOST: $HOST_VIDEO_SOURCE -> $HOST_VIDEO_CAPTURE_PATH (${HOST_VIDEO_FPS:-2} FPS)"
fi

# Check DEVICE1-10 configuration
for i in {1..10}; do
    # Use indirect variable expansion to get DEVICE*_VIDEO value
    video_var="DEVICE${i}_VIDEO"
    audio_var="DEVICE${i}_VIDEO_AUDIO"
    capture_var="DEVICE${i}_VIDEO_CAPTURE_PATH"
    fps_var="DEVICE${i}_VIDEO_FPS"
    name_var="DEVICE${i}_NAME"
    
    video_source="${!video_var}"
    audio_device="${!audio_var}"
    capture_path="${!capture_var}"
    fps="${!fps_var}"
    device_name="${!name_var:-device$i}"
    
    # Only add if VIDEO source is defined and not empty
    if [ -n "$video_source" ]; then
        GRABBERS["device$i"]="$video_source|${audio_device:-null}|${capture_path}|${fps:-10}"
        echo "✓ Added DEVICE$i ($device_name): $video_source -> $capture_path (${fps:-10} FPS)"
    fi
done

# Check if we have any grabbers configured
if [ ${#GRABBERS[@]} -eq 0 ]; then
    echo "ERROR: No capture devices configured in .env file!"
    exit 1
fi

echo "Total active captures: ${#GRABBERS[@]}"

# Kill all existing ffmpeg and clean_captures processes
echo "Stopping all existing capture processes..."
sudo pkill -f ffmpeg 2>/dev/null && echo "Killed all ffmpeg processes" || echo "No ffmpeg processes found"
sudo pkill -f clean_captures.sh 2>/dev/null && echo "Killed all clean_captures processes" || echo "No clean_captures processes found"
sleep 3

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

# Function to reset video device before capture
reset_video_device() {
  local device="$1"
  sudo fuser -k "$device" 2>/dev/null || true
  sleep 3
}

# Clean up playlist files for a specific capture directory
clean_playlist_files() {
  local output_dir=$1
  echo "Cleaning playlist files for $output_dir (preserving segments for 24h retention)..."
  rm -f "$output_dir"/output.m3u8
  rm -f "$output_dir"/archive.m3u8
}

# Get last segment number to continue from where we left off
get_last_segment_number() {
  local capture_dir="$1"
  local last_segment=$(ls -1 "$capture_dir"/segment_*.ts 2>/dev/null | \
    sed 's/.*segment_\([0-9]*\)\.ts/\1/' | \
    sort -n | tail -1)
  
  if [ -n "$last_segment" ]; then
    # Add 1 to continue from next number (remove leading zeros with 10#)
    echo $((10#$last_segment + 1))
  else
    echo 0
  fi
}

# Cleanup function
cleanup() {
  local ffmpeg_pid=$1 clean_pid=$2 source=$3
  echo "Caught signal, cleaning up for $source..."
  [ -n "$ffmpeg_pid" ] && kill "$ffmpeg_pid" 2>/dev/null && echo "Killed ffmpeg (PID: $ffmpeg_pid)"
  [ -n "$clean_pid" ] && kill "$clean_pid" 2>/dev/null && echo "Killed clean_captures.sh (PID: $clean_pid)"
}

# Function to start processes for a single grabber
start_grabber() {
  local source=$1 audio_device=$2 capture_dir=$3 index=$4 input_fps=$5

  # Detect source type
  local source_type=$(detect_source_type "$source")
  if [ "$source_type" = "unknown" ]; then
    echo "ERROR: Unknown source type for $source"
    return 1
  fi

  # Create capture directory
  mkdir -p "$capture_dir/captures"

  # Clean playlist files for fresh start
  clean_playlist_files "$capture_dir"

  # Get last segment number to continue from
  local start_num=$(get_last_segment_number "$capture_dir")
  echo "Starting segment numbering from: $start_num"

  # Reset video device if it's a hardware device
  if [ "$source_type" = "v4l2" ]; then
    reset_video_device "$source"
  fi

  # Build FFmpeg command based on source type
  if [ "$source_type" = "v4l2" ]; then
    # Hardware video device - Triple output: stream, full-res captures, thumbnails (5 FPS controlled)
    # Optimized: single fps operation, balanced queues, CBR encoding for stable streaming
    FFMPEG_CMD="/usr/bin/ffmpeg -loglevel error -y \
      -fflags +nobuffer+genpts+flush_packets \
      -use_wallclock_as_timestamps 1 \
      -thread_queue_size 1024 \
      -f v4l2 -input_format mjpeg -video_size 1280x720 -framerate $input_fps -i $source \
      -f alsa -thread_queue_size 4096 -async 1 -i \"$audio_device\" \
      -filter_complex \"[0:v]fps=5[v5];[v5]split=3[str][cap][thm]; \
        [str]scale=640:360:flags=fast_bilinear,fps=$input_fps[streamout]; \
        [cap]setpts=PTS-STARTPTS[captureout];[thm]scale=320:180:flags=neighbor[thumbout]\" \
      -map \"[streamout]\" -map 1:a \
      -c:v libx264 -preset ultrafast -tune zerolatency \
      -b:v 350k -maxrate 400k -bufsize 800k \
      -x264opts keyint=10:min-keyint=10:no-scenecut:bframes=0 \
      -pix_fmt yuv420p -profile:v baseline -level 3.0 \
      -c:a aac -b:a 32k -ar 48000 -ac 2 \
      -f hls -hls_time 1 -hls_list_size 10 -segment_wrap 86400 -hls_flags omit_endlist+split_by_time -lhls 1 \
      -hls_start_number_source generic -start_number $start_num \
      -hls_segment_filename $capture_dir/segment_%05d.ts \
      $capture_dir/output.m3u8 \
      -map \"[captureout]\" -vsync 0 -c:v mjpeg -q:v 5 -f image2 \
      $capture_dir/captures/capture_%04d.jpg \
      -map \"[thumbout]\" -vsync 0 -c:v mjpeg -q:v 8 -f image2 \
      $capture_dir/captures/capture_%04d_thumbnail.jpg"
  elif [ "$source_type" = "x11grab" ]; then
    # VNC display - Optimized for low CPU usage: triple output (stream + captures + thumbnails)
    # Optimized: single fps operation, no mouse cursor, CBR encoding, faster scaling
    # Setup X11 display environment
    export DISPLAY="$source"
    export XAUTHORITY=~/.Xauthority
    # Allow local connections and set resolution
    echo "Setting up X11 display $source..."
    xhost +local: 2>/dev/null || echo "Warning: xhost command failed"
    xrandr -display "$source" -s 1280x720 2>/dev/null || echo "Warning: xrandr resolution set failed"
    local resolution=$(get_vnc_resolution "$source")

    FFMPEG_CMD="DISPLAY=\"$source\" /usr/bin/ffmpeg -loglevel error -y \
      -probesize 32M -analyzeduration 0 \
      -draw_mouse 0 -show_region 0 \
      -f x11grab -video_size $resolution -framerate $input_fps -i $source \
      -an \
      -filter_complex \"[0:v]fps=2[v2];[v2]split=3[str][cap][thm]; \
        [str]scale=480:360:flags=neighbor[streamout]; \
        [cap]setpts=PTS-STARTPTS[captureout];[thm]scale=320:180:flags=neighbor[thumbout]\" \
      -map \"[streamout]\" \
      -c:v libx264 -preset ultrafast -tune zerolatency \
      -b:v 250k -maxrate 300k -bufsize 600k \
      -pix_fmt yuv420p -profile:v baseline -level 3.0 \
      -x264opts keyint=8:min-keyint=8:no-scenecut:bframes=0:ref=1:me=dia:subme=0 \
      -f hls -hls_time 4 -hls_list_size 10 -segment_wrap 86400 -hls_flags omit_endlist \
      -hls_start_number_source generic -start_number $start_num \
      -hls_segment_filename $capture_dir/segment_%05d.ts \
      $capture_dir/output.m3u8 \
      -map \"[captureout]\" -fps_mode passthrough -c:v mjpeg -q:v 8 -f image2 \
      $capture_dir/captures/capture_%04d.jpg \
      -map \"[thumbout]\" -fps_mode passthrough -c:v mjpeg -q:v 10 -f image2 \
      $capture_dir/captures/capture_%04d_thumbnail.jpg"
  else
    echo "ERROR: Unsupported source type: $source_type"
    return 1
  fi

  # Start ffmpeg
  echo "Starting ffmpeg for $source ($source_type) with audio: $audio_device..."
  local FFMPEG_LOG="/tmp/ffmpeg_output_${index}.log"
  
  # Clean log file for fresh start
  echo "Cleaning log file for fresh start: $FFMPEG_LOG"
  > "$FFMPEG_LOG"
  
  # Also set up log size management for long-running sessions
  reset_log_if_large "$FFMPEG_LOG"
  
  eval $FFMPEG_CMD > "$FFMPEG_LOG" 2>&1 &
  local FFMPEG_PID=$!
  echo "Started ffmpeg for $source with PID: $FFMPEG_PID"

  # Start clean script (using relative path - same directory)
  while true; do
    "$SCRIPT_DIR/clean_captures.sh" "$capture_dir"
    sleep 300
  done &
  local CLEAN_PID=$!
  echo "Started clean_captures.sh loop for $capture_dir with PID: $CLEAN_PID"

  # Set up trap for this grabber
  trap "cleanup $FFMPEG_PID $CLEAN_PID $source" SIGINT SIGTERM
}

# Create active captures configuration file
ACTIVE_CAPTURES_FILE="/tmp/active_captures.conf"
> "$ACTIVE_CAPTURES_FILE"
for index in "${!GRABBERS[@]}"; do
  IFS='|' read -r source audio_device capture_dir input_fps <<< "${GRABBERS[$index]}"
  echo "$capture_dir" >> "$ACTIVE_CAPTURES_FILE"
done

# Print configuration and check availability
echo "=== Unified Capture Configuration ==="
for index in "${!GRABBERS[@]}"; do
  IFS='|' read -r source audio_device capture_dir input_fps <<< "${GRABBERS[$index]}"

  source_type=$(detect_source_type "$source")
  last_segment=$(get_last_segment_number "$capture_dir")

  echo "Grabber $index:"
  echo "  Source: $source ($source_type)"
  if [ "$source_type" = "x11grab" ]; then
    resolution=$(get_vnc_resolution "$source" 2>/dev/null || echo "1024x768")
    echo "  Resolution: $resolution"
  fi
  echo "  Audio: $audio_device"
  echo "  Output: $capture_dir"
  echo "  Input FPS: $input_fps"
  echo "  Last segment: $last_segment (will start from $last_segment)"
  echo
done

# Main loop to start all grabbers
PIDS=()
for index in "${!GRABBERS[@]}"; do
  IFS='|' read -r source audio_device capture_dir input_fps <<< "${GRABBERS[$index]}"
  start_grabber "$source" "$audio_device" "$capture_dir" "$index" "$input_fps" &
  PIDS+=($!)
done

# Wait for all grabber processes
wait "${PIDS[@]}"

# Keep script alive for systemd compatibility
while true; do
  sleep 3600
done