#!/bin/bash

# Usage: ./run_ffmpeg_and_rename_local.sh [device_id] [quality]
# Examples:
#   ./run_ffmpeg_and_rename_local.sh              # Start all devices (systemd mode)
#   ./run_ffmpeg_and_rename_local.sh device1 hd   # Restart device1 with HD
#   ./run_ffmpeg_and_rename_local.sh host sd      # Restart host with SD

# Enable debugging
set -x  # Print commands as they execute
# set -e  # Exit on error (commented out for debugging)

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

# Kill existing ffmpeg processes once at start
echo "🔍 DEBUG: Killing existing processes..."
if [ "$SINGLE_DEVICE_MODE" = true ]; then
    for index in "${!GRABBERS[@]}"; do
        if [ "$index" = "$TARGET_DEVICE" ]; then
            IFS='|' read -r _ _ capture_dir _ <<< "${GRABBERS[$index]}"
            OLD_PID=$(get_device_info "$capture_dir" "pid")
            if [ -n "$OLD_PID" ]; then
                sudo kill -9 "$OLD_PID" 2>/dev/null || true
            fi
            break
        fi
    done
else
    # Kill all ffmpeg processes (use full path to avoid matching this script's filename)
    sudo pkill -9 -f '/usr/bin/ffmpeg' 2>/dev/null || true
fi

sleep 1
echo "✅ Process cleanup complete"

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
      echo "sd"
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
  sudo fuser -k "$device" 2>/dev/null || true
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

start_grabber() {
  local source=$1 audio_device=$2 capture_dir=$3 index=$4 input_fps=$5
  local quality=$(get_device_quality "$capture_dir")
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
    # HD mode: Only upgrade STREAM quality, keep captures at SD for RAM efficiency
    if [ "$quality" = "hd" ]; then
      local stream_scale="1280:720"
      local stream_bitrate="1500k"
      local stream_maxrate="1800k"
      local stream_bufsize="3600k"
      local capture_scale="640:360"    # Captures stay SD (saves 66% RAM!)
    else
      local stream_scale="640:360"
      local stream_bitrate="350k"
      local stream_maxrate="400k"
      local stream_bufsize="800k"
      local capture_scale="640:360"    # Captures SD
    fi
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
      -f hls -hls_time 1 -hls_list_size 10 -hls_flags omit_endlist+split_by_time -lhls 1 \
      -hls_segment_filename $output_segments/segment_%09d.ts \
      $output_segments/output.m3u8 \
      -map \"[captureout]\" -fps_mode passthrough -c:v mjpeg -q:v 5 -f image2 -atomic_writing 1 \
      $output_captures/capture_%09d.jpg \
      -map \"[thumbout]\" -fps_mode passthrough -c:v mjpeg -q:v 5 -f image2 -atomic_writing 1 \
      $output_thumbnails/capture_%09d_thumbnail.jpg"
  elif [ "$source_type" = "x11grab" ]; then
    # HD mode: Only upgrade STREAM quality, keep captures at SD for RAM efficiency
    if [ "$quality" = "hd" ]; then
      local stream_scale="1280:720"
      local stream_bitrate="1000k"
      local stream_maxrate="1200k"
      local stream_bufsize="2400k"
      local capture_scale="480:360"    # Captures stay SD (saves RAM!)
    else
      local stream_scale="480:360"
      local stream_bitrate="250k"
      local stream_maxrate="300k"
      local stream_bufsize="600k"
      local capture_scale="480:360"    # Captures SD
    fi
    
    export DISPLAY="$source"
    export XAUTHORITY=~/.Xauthority
    xhost +local: 2>/dev/null
    xrandr -display "$source" -s 1280x720 2>/dev/null
    local resolution=$(get_vnc_resolution "$source")

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
      -f hls -hls_time 4 -hls_list_size 10 -hls_flags omit_endlist \
      -hls_segment_filename $output_segments/segment_%09d.ts \
      $output_segments/output.m3u8 \
      -map \"[captureout]\" -fps_mode passthrough -c:v mjpeg -q:v 8 -f image2 -atomic_writing 1 \
      $output_captures/capture_%09d.jpg \
      -map \"[thumbout]\" -fps_mode passthrough -c:v mjpeg -q:v 8 -f image2 -atomic_writing 1 \
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
  
  echo "✅ Started $index PID:$FFMPEG_PID quality:$quality"
  
  trap "cleanup $FFMPEG_PID 0 $source" SIGINT SIGTERM
}

update_active_captures() {
  local capture_dir="$1"
  local pid="$2"
  local quality="$3"
  
  local temp_file="/tmp/active_captures.conf.tmp"
  
  if [ -f "/tmp/active_captures.conf" ]; then
    # Remove old entry for this capture_dir
    grep -v "^${capture_dir}," /tmp/active_captures.conf > "$temp_file" 2>/dev/null || true
  else
    > "$temp_file"
  fi
  
  # Add new entry
  echo "${capture_dir},${pid},${quality}" >> "$temp_file"
  
  mv "$temp_file" /tmp/active_captures.conf
}

# Initialize active captures file (will be populated by start_grabber)
if [ "$SINGLE_DEVICE_MODE" = false ]; then
  > "/tmp/active_captures.conf"
  echo "Starting ${#GRABBERS[@]} devices"
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

# Script exits after starting background ffmpeg processes
# Systemd Type=forking will track the ffmpeg PIDs
echo "🔍 DEBUG: Script complete - ffmpeg processes running in background"
exit 0