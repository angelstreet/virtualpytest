#!/bin/bash

# Usage: ./run_ffmpeg_and_rename_local.sh [device_id] [quality]
# Examples:
#   ./run_ffmpeg_and_rename_local.sh              # Start all devices (systemd mode)
#   ./run_ffmpeg_and_rename_local.sh device1 hd   # Restart device1 with HD
#   ./run_ffmpeg_and_rename_local.sh host sd      # Restart host with SD

# Enable debugging
set -x  # Print commands as they execute
# set -e  # Exit on error (commented out for debugging)

# Set umask to allow world read/write for shared temp files
umask 0000

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HOST_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$BACKEND_HOST_DIR/src/.env"

echo "🔍 DEBUG: Running as user: $(whoami)"
echo "🔍 DEBUG: SCRIPT_DIR: $SCRIPT_DIR"
echo "🔍 DEBUG: ENV_FILE: $ENV_FILE"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

if [ ! -r "$ENV_FILE" ]; then
    echo "ERROR: .env file not readable by $(whoami)"
    ls -la "$ENV_FILE"
    exit 1
fi

echo "✅ .env file found and readable"

# Parse arguments
TARGET_DEVICE="${1:-all}"
TARGET_QUALITY="${2:-sd}"
SINGLE_DEVICE_MODE=false

echo "🔍 DEBUG: Script called with arguments:"
echo "  \$1 (TARGET_DEVICE): '$TARGET_DEVICE'"
echo "  \$2 (TARGET_QUALITY): '$TARGET_QUALITY'"
echo "  All args: $@"

if [ "$TARGET_DEVICE" != "all" ]; then
    SINGLE_DEVICE_MODE=true
    echo "🎯 Restarting $TARGET_DEVICE with quality: $TARGET_QUALITY"
fi

# Load .env
echo "🔍 DEBUG: Loading .env file..."
set -a
source <(grep -v '^#' "$ENV_FILE" | grep -v '^$' | grep -v '^x')
set +a
echo "✅ .env loaded successfully"

declare -A GRABBERS=()
declare -A RUNNING_QUALITY=()  # Track what quality each device is actually running

# Build GRABBERS array (filtered by target device if in single mode)
if [ -n "$HOST_VIDEO_SOURCE" ] && { [ "$SINGLE_DEVICE_MODE" = false ] || [ "$TARGET_DEVICE" = "host" ]; }; then
    GRABBERS["host"]="$HOST_VIDEO_SOURCE|${HOST_VIDEO_AUDIO:-null}|${HOST_VIDEO_CAPTURE_PATH}|${HOST_VIDEO_FPS:-2}"
fi

for i in {1..10}; do
    video_var="DEVICE${i}_VIDEO"
    audio_var="DEVICE${i}_VIDEO_AUDIO"
    capture_var="DEVICE${i}_VIDEO_CAPTURE_PATH"
    fps_var="DEVICE${i}_VIDEO_FPS"
    
    video_source="${!video_var}"
    audio_device="${!audio_var}"
    capture_path="${!capture_var}"
    fps="${!fps_var}"
    
    if [ -n "$video_source" ] && { [ "$SINGLE_DEVICE_MODE" = false ] || [ "$TARGET_DEVICE" = "device$i" ]; }; then
        GRABBERS["device$i"]="$video_source|${audio_device:-null}|${capture_path}|${fps:-10}"
    fi
done

if [ ${#GRABBERS[@]} -eq 0 ]; then
    echo "ERROR: No devices configured"
    exit 1
fi

echo "🔍 DEBUG: Found ${#GRABBERS[@]} device(s) configured"
for device in "${!GRABBERS[@]}"; do
    echo "  - $device"
done

# Clean up any stale temp files from previous runs
echo "🔍 DEBUG: Cleaning stale temp files..."
rm -f /tmp/active_captures.conf.tmp* 2>/dev/null || true

# Single device restart: kill only the specific device's process
if [ "$SINGLE_DEVICE_MODE" = true ]; then
    echo "🔍 DEBUG: Killing process for $TARGET_DEVICE..."
    for index in "${!GRABBERS[@]}"; do
        if [ "$index" = "$TARGET_DEVICE" ]; then
            IFS='|' read -r _ _ capture_dir _ <<< "${GRABBERS[$index]}"
            OLD_PID=$(get_device_info "$capture_dir" "pid")
            if [ -n "$OLD_PID" ]; then
                kill -9 "$OLD_PID" 2>/dev/null || true
                echo "✅ Killed old process PID: $OLD_PID"
            fi
            break
        fi
    done
    sleep 1
fi

# Note: For "all devices" mode, systemd ExecStartPre handles cleanup

reset_log_if_large() {
  local logfile="$1" max_size_mb=30
  if [ -f "$logfile" ]; then
    local size_mb=$(du -m "$logfile" | cut -f1)
    if [ "$size_mb" -ge "$max_size_mb" ]; then
      > "$logfile"
    fi
  fi
}

get_device_info() {
  local capture_dir="$1"
  local field="$2"  # 'pid' or 'quality'
  
  if [ ! -f "/tmp/active_captures.conf" ]; then
    echo ""
    return
  fi
  
  local line=$(grep "^${capture_dir}," /tmp/active_captures.conf)
  if [ -n "$line" ]; then
    IFS=',' read -r _ pid quality <<< "$line"
    if [ "$field" = "pid" ]; then
      echo "$pid"
    elif [ "$field" = "quality" ]; then
      echo "$quality"
    fi
  fi
}

get_device_quality() {
  local capture_dir="$1"
  if [ "$SINGLE_DEVICE_MODE" = true ]; then
    echo "$TARGET_QUALITY"
  else
    local quality=$(get_device_info "$capture_dir" "quality")
    if [ -z "$quality" ]; then
      echo "low"  # Default to LOW quality (320:180) for preview/monitoring
    else
      echo "$quality"
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
  fuser -k "$device" 2>/dev/null || true
  sleep 1
}

# Clean up playlist files for a specific capture directory
clean_playlist_files() {
  local capture_dir=$1
  echo "Cleaning playlist files in hot storage..."
  # Clean playlists in hot storage (RAM)
  rm -f "$capture_dir/hot/segments/output.m3u8" 2>/dev/null || true
  rm -f "$capture_dir/hot/segments/archive.m3u8" 2>/dev/null || true
}


# Setup capture directory structure and detect storage mode
setup_capture_directories() {
  local capture_dir=$1
  
  # Check if hot storage is mounted (RAM mode)
  if mount | grep -q "$capture_dir/hot"; then
    echo "✓ RAM hot storage detected at $capture_dir/hot"
    # Create subdirectories in RAM hot storage
    mkdir -p "$capture_dir/hot/segments"
    mkdir -p "$capture_dir/hot/captures"
    mkdir -p "$capture_dir/hot/thumbnails"
    mkdir -p "$capture_dir/hot/metadata"
    echo "✓ Using RAM mode (99% SD write reduction)"
    return 0  # RAM mode
  else
    echo "⚠️  No RAM hot storage found at $capture_dir/hot"
    echo "   Run: setup_ram_hot_storage.sh to enable RAM mode"
    # Create directories on SD card
    mkdir -p "$capture_dir/segments"
    mkdir -p "$capture_dir/captures"
    mkdir -p "$capture_dir/thumbnails"
    mkdir -p "$capture_dir/metadata"
    echo "✓ Using SD card mode (direct write)"
    return 1  # SD mode
  fi
}

# Cleanup function
cleanup() {
  local ffmpeg_pid=$1 source=$3
  echo "Caught signal, cleaning up for $source..."
  [ -n "$ffmpeg_pid" ] && kill "$ffmpeg_pid" 2>/dev/null && echo "Killed ffmpeg (PID: $ffmpeg_pid)"
  echo "Note: hot_cold_archiver.service handles cleanup independently"
}

# Check if any device needs quality change (called from main loop)
check_quality_changes() {
  [ -f "/tmp/active_captures.conf" ] || return
  
  # Read config and compare with what's actually running
  while IFS=',' read -r capture_dir pid config_quality; do
    [ -z "$capture_dir" ] && continue
    
    # Find device_id
    local device_id=""
    for index in "${!GRABBERS[@]}"; do
      IFS='|' read -r _ _ dev_capture_dir _ <<< "${GRABBERS[$index]}"
      [ "$dev_capture_dir" = "$capture_dir" ] && device_id="$index" && break
    done
    [ -z "$device_id" ] && continue
    
    # Compare config quality vs running quality
    local running_quality="${RUNNING_QUALITY[$device_id]}"
    
    if [ "$config_quality" != "$running_quality" ]; then
      echo "🔄 Quality change: $device_id ($running_quality → $config_quality)"
      kill -9 "$pid" 2>/dev/null || true
      sleep 1
      
      # Restart with new quality
      IFS='|' read -r source audio_device capture_dir input_fps <<< "${GRABBERS[$device_id]}"
      start_grabber "$source" "$audio_device" "$capture_dir" "$device_id" "$input_fps" "$config_quality"
    fi
  done < "/tmp/active_captures.conf"
}

start_grabber() {
  local source=$1 audio_device=$2 capture_dir=$3 index=$4 input_fps=$5
  local target_quality=$6  # Optional: if provided, use this quality instead of get_device_quality
  
  # Use target_quality if provided, otherwise fallback to get_device_quality
  local quality=${target_quality:-$(get_device_quality "$capture_dir")}
  local source_type=$(detect_source_type "$source")
  
  if [ "$source_type" = "unknown" ]; then
    echo "ERROR: Unknown source type for $source"
    return 1
  fi

  if setup_capture_directories "$capture_dir"; then
    local storage_base="$capture_dir/hot"
  else
    local storage_base="$capture_dir"
  fi
  
  local output_segments="$storage_base/segments"
  local output_captures="$storage_base/captures"
  local output_thumbnails="$storage_base/thumbnails"

  clean_playlist_files "$capture_dir"

  if [ "$source_type" = "v4l2" ]; then
    reset_video_device "$source"
  fi

  if [ "$source_type" = "v4l2" ]; then
    # 3-tier quality system: LOW (preview) → SD (modal opened) → HD (user clicks HD)
    # Captures always stay at 1280:720 for high-quality detection (zap, freeze, etc)
    if [ "$quality" = "hd" ]; then
      # HD: Full quality stream for single device focus
      local stream_scale="1280:720"
      local stream_bitrate="1500k"
      local stream_maxrate="1800k"
      local stream_bufsize="3600k"
      local capture_scale="1280:720"    # Captures at HD for best detection quality
    elif [ "$quality" = "sd" ]; then
      # SD: Medium quality when modal opened (single device)
      local stream_scale="640:360"
      local stream_bitrate="350k"
      local stream_maxrate="400k"
      local stream_bufsize="800k"
      local capture_scale="1280:720"    # Captures at HD for best detection quality
    else
      # LOW (default): Minimal quality for preview/monitoring (multiple devices)
      local stream_scale="320:180"
      local stream_bitrate="150k"
      local stream_maxrate="200k"
      local stream_bufsize="400k"
      local capture_scale="1280:720"    # Captures at HD for best detection quality
    fi
    # Pi5-optimized FFmpeg configuration (real-time streaming priority)
    FFMPEG_CMD="/usr/bin/ffmpeg -y \
      -fflags +nobuffer+genpts+flush_packets \
      -use_wallclock_as_timestamps 1 \
      -thread_queue_size 512 \
      -f v4l2 -input_format mjpeg -video_size 1280x720 -framerate $input_fps -i $source \
      -f alsa -thread_queue_size 2048 -async 1 -err_detect ignore_err -i \"$audio_device\" \
      -filter_complex \"[0:v]fps=5[v5];[v5]split=3[str][cap][thm]; \
        [str]scale=${stream_scale}:flags=fast_bilinear,fps=$input_fps[streamout]; \
        [cap]scale=${capture_scale}:flags=fast_bilinear,setpts=PTS-STARTPTS[captureout];[thm]scale=320:180:flags=neighbor[thumbout]\" \
      -map \"[streamout]\" -map 1:a? \
      -c:v libx264 -preset ultrafast -tune zerolatency \
      -b:v $stream_bitrate -maxrate $stream_maxrate -bufsize $stream_bufsize \
      -x264opts keyint=10:min-keyint=10:no-scenecut:bframes=0 \
      -pix_fmt yuv420p -profile:v baseline -level 3.0 \
      -c:a aac -b:a 32k -ar 48000 -ac 2 \
      -f hls -hls_time 1 -hls_list_size 150 -hls_flags delete_segments+omit_endlist+split_by_time -lhls 1 \
      -hls_segment_filename $output_segments/segment_%09d.ts \
      $output_segments/output.m3u8 \
      -map \"[captureout]\" -fps_mode passthrough -c:v mjpeg -q:v 8 -f image2 -atomic_writing 1 \
      $output_captures/capture_%09d.jpg \
      -map \"[thumbout]\" -fps_mode passthrough -c:v mjpeg -q:v 8 -f image2 -atomic_writing 1 \
      $output_thumbnails/capture_%09d_thumbnail.jpg"
  elif [ "$source_type" = "x11grab" ]; then
    # 3-tier quality system: LOW (preview) → SD (modal opened) → HD (user clicks HD)
    # Captures always stay at 1280:720 for high-quality VNC detection (aligned with v4l2)
    if [ "$quality" = "hd" ]; then
      # HD: Full quality stream for single device focus
      local stream_scale="1280:720"
      local stream_bitrate="1000k"
      local stream_maxrate="1200k"
      local stream_bufsize="2400k"
      local capture_scale="1280:720"    # Captures at HD for best detection quality
    elif [ "$quality" = "sd" ]; then
      # SD: Medium quality when modal opened (single device)
      local stream_scale="640:360"
      local stream_bitrate="350k"
      local stream_maxrate="400k"
      local stream_bufsize="800k"
      local capture_scale="1280:720"    # Captures at HD for best detection quality
    else
      # LOW (default): Minimal quality for preview/monitoring (multiple devices)
      local stream_scale="320:180"
      local stream_bitrate="120k"
      local stream_maxrate="150k"
      local stream_bufsize="300k"
      local capture_scale="1280:720"    # Captures at HD for best detection quality
    fi
    
    # X11 access is configured by vncserver.service ExecStartPost
    export DISPLAY="$source"
    local resolution=$(get_vnc_resolution "$source")

    # Pi5-optimized X11grab configuration (real-time streaming priority)
    FFMPEG_CMD="DISPLAY=\"$source\" /usr/bin/ffmpeg -loglevel error -y \
      -probesize 32M -analyzeduration 0 \
      -draw_mouse 0 -show_region 0 \
      -f x11grab -video_size $resolution -framerate $input_fps -i $source \
      -an \
      -filter_complex \"[0:v]fps=2[v2];[v2]split=3[str][cap][thm]; \
        [str]scale=${stream_scale}:flags=neighbor[streamout]; \
        [cap]scale=${capture_scale}:flags=neighbor,setpts=PTS-STARTPTS[captureout];[thm]scale=320:180:flags=neighbor[thumbout]\" \
      -map \"[streamout]\" \
      -c:v libx264 -preset ultrafast -tune zerolatency \
      -b:v $stream_bitrate -maxrate $stream_maxrate -bufsize $stream_bufsize \
      -pix_fmt yuv420p -profile:v baseline -level 3.0 \
      -x264opts keyint=8:min-keyint=8:no-scenecut:bframes=0:ref=1:me=dia:subme=0 \
      -f hls -hls_time 4 -hls_list_size 40 -hls_flags delete_segments+omit_endlist \
      -hls_segment_filename $output_segments/segment_%09d.ts \
      $output_segments/output.m3u8 \
      -map \"[captureout]\" -fps_mode passthrough -c:v mjpeg -q:v 10 -f image2 -atomic_writing 1 \
      $output_captures/capture_%09d.jpg \
      -map \"[thumbout]\" -fps_mode passthrough -c:v mjpeg -q:v 10 -f image2 -atomic_writing 1 \
      $output_thumbnails/capture_%09d_thumbnail.jpg"
  else
    echo "ERROR: Unsupported source type: $source_type"
    return 1
  fi

  local FFMPEG_LOG="/tmp/ffmpeg_output_${index}.log"
  > "$FFMPEG_LOG"
  reset_log_if_large "$FFMPEG_LOG"
  
  eval $FFMPEG_CMD > "$FFMPEG_LOG" 2>&1 &
  local FFMPEG_PID=$!
  
  # Update active_captures.conf with CSV format
  update_active_captures "$capture_dir" "$FFMPEG_PID" "$quality"
  
  # Track running quality in memory
  RUNNING_QUALITY[$index]="$quality"
  
  echo "✅ Started $index PID:$FFMPEG_PID quality:$quality"
  
  trap "cleanup $FFMPEG_PID 0 $source" SIGINT SIGTERM
}

update_active_captures() {
  local capture_dir="$1"
  local pid="$2"
  local quality="$3"
  
  echo "🔍 DEBUG: update_active_captures called with:"
  echo "  capture_dir: $capture_dir"
  echo "  pid: $pid"
  echo "  quality: $quality"
  
  local temp_file="/tmp/active_captures.conf.tmp.$$"
  local conf_file="/tmp/active_captures.conf"
  
  # Simple atomic update - no locking needed
  # Create temp file (umask 0000 ensures 777 permissions)
  > "$temp_file"
  
  if [ -f "$conf_file" ]; then
    # Remove old entry for this capture_dir
    grep -v "^${capture_dir}," "$conf_file" > "$temp_file" 2>/dev/null || true
  fi
  
  # Add new entry
  echo "${capture_dir},${pid},${quality}" >> "$temp_file"
  
  # Atomic move with explicit permissions
  mv "$temp_file" "$conf_file"
  chmod 777 "$conf_file"
  
  echo "🔍 DEBUG: Updated active_captures.conf:"
  cat "$conf_file"
}

# Initialize active captures file - ALWAYS clean start for proper permissions
if [ "$SINGLE_DEVICE_MODE" = false ]; then
  # Remove old file completely to avoid permission conflicts
  rm -f "/tmp/active_captures.conf" 2>/dev/null || true
  
  # Create fresh file with explicit 777 permissions (world read/write for all services)
  > "/tmp/active_captures.conf"
  chmod 777 "/tmp/active_captures.conf"
  
  echo "✅ Created fresh active_captures.conf with 777 permissions"
  echo "Starting ${#GRABBERS[@]} devices"
else
  # Single device mode: ensure file exists with correct permissions
  if [ ! -f "/tmp/active_captures.conf" ]; then
    > "/tmp/active_captures.conf"
    chmod 777 "/tmp/active_captures.conf"
  fi
fi

# Start grabbers (serially to avoid race condition in active_captures.conf)
echo "🔍 DEBUG: Starting grabbers..."
for index in "${!GRABBERS[@]}"; do
  IFS='|' read -r source audio_device capture_dir input_fps <<< "${GRABBERS[$index]}"
  echo "🔍 DEBUG: Starting grabber for $index (source: $source)"
  start_grabber "$source" "$audio_device" "$capture_dir" "$index" "$input_fps"
  # Note: Starts serially (no &), takes ~1-2s total for 4 devices
  # FFmpeg processes themselves run in background inside start_grabber
done

echo "✅ All grabbers started"

if [ "$SINGLE_DEVICE_MODE" = true ]; then
  echo "🔍 DEBUG: Single device mode - exiting"
  exit 0
fi

# Graceful shutdown handler for systemd stop/restart
cleanup_all() {
  echo "🛑 Received shutdown signal - cleaning up..."
  pkill -9 -f '/usr/bin/ffmpeg' 2>/dev/null || true
  # Clean up temp files (no sudo needed with umask 0000)
  rm -f /tmp/active_captures.conf.tmp* 2>/dev/null || true
  echo "✅ Cleanup complete - exiting"
  exit 0
}

# Register signal handlers for graceful shutdown
trap cleanup_all SIGTERM SIGINT

# Keep script running for systemd (Type=simple with Restart=always)
# The script must stay alive or systemd will restart it continuously
echo "🔍 DEBUG: Keeping service alive (systemd Type=simple)"
echo "Press Ctrl+C or send SIGTERM to stop gracefully"

while true; do
  # Check if any device quality changed or died
  check_quality_changes
  
  sleep 1  # Check every second
done