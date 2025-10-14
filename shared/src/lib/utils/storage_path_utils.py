#!/usr/bin/env python3
"""
Centralized Storage Path Utilities

Single source of truth for hot/cold storage path resolution.
Eliminates path duplication across the codebase.

HOT/COLD ARCHITECTURE:
- RAM MODE: Files in /hot/ subdirectory (tmpfs mounted)
- SD MODE: Files in root directory (traditional)

This module provides functions to:
- Detect storage mode (RAM vs SD)
- Resolve correct paths automatically
- Get device mappings from .env
"""
import os
import sys
import json
import logging
import re
import time

logger = logging.getLogger(__name__)

# =====================================================
# BASE PATH CONFIGURATION (NO HARDCODING!)
# =====================================================

# Single source of truth for stream base path
# Can be overridden via environment variable
_STREAM_BASE_PATH = os.getenv('STREAM_BASE_PATH', '/var/www/html/stream')

def get_stream_base_path():
    """
    Get the base stream path (configurable via environment).
    CENTRALIZED - Use this instead of hardcoding '/var/www/html/stream'!
    
    Returns:
        Base stream path (e.g., '/var/www/html/stream')
    """
    return _STREAM_BASE_PATH

def get_active_captures_conf_path():
    """
    Get the path to active_captures.conf file.
    CENTRALIZED - Single source of truth for capture config location!
    
    This file tracks FFmpeg processes and their quality settings.
    CSV Format: /var/www/html/stream/capture1,PID,quality
    
    Returns:
        Full path to active_captures.conf (e.g., '/var/www/html/stream/active_captures.conf')
    """
    return os.path.join(get_stream_base_path(), 'active_captures.conf')

def get_device_base_path(device_folder):
    """
    Get device base directory path.
    CENTRALIZED - No more hardcoding!
    
    Args:
        device_folder: Device folder name (e.g., 'capture1', 'capture2')
        
    Returns:
        Full device base path (e.g., '/var/www/html/stream/capture1')
    """
    return os.path.join(get_stream_base_path(), device_folder)

# Cache for device mappings to avoid repeated .env lookups
_device_mapping_cache = {}

# Load environment variables using same approach as incident_manager.py
try:
    from dotenv import load_dotenv
    
    # Get script paths (storage_path_utils.py is in shared/src/lib/utils/)
    current_dir = os.path.dirname(os.path.abspath(__file__))  # shared/src/lib/utils/
    shared_lib_dir = os.path.dirname(current_dir)  # shared/src/lib/
    shared_src_dir = os.path.dirname(shared_lib_dir)  # shared/src/
    shared_dir = os.path.dirname(shared_src_dir)  # shared/
    project_root = os.path.dirname(shared_dir)  # project root
    
    # Load project root .env first
    project_env_path = os.path.join(project_root, '.env')
    if os.path.exists(project_env_path):
        load_dotenv(project_env_path)
        logger.debug(f"Loaded project environment from {project_env_path}")
    
    # Load backend_host .env second (correct path from project root)
    backend_env_path = os.path.join(project_root, 'backend_host', 'src', '.env')
    if os.path.exists(backend_env_path):
        load_dotenv(backend_env_path)
        logger.debug(f"Loaded backend_host environment from {backend_env_path}")
        
        # Log critical variables for debugging
        host_capture = os.getenv('HOST_VIDEO_CAPTURE_PATH')
        logger.debug(f"HOST_VIDEO_CAPTURE_PATH={host_capture}")
    else:
        logger.warning(f"backend_host .env not found at {backend_env_path}")
        
except ImportError:
    logger.warning("python-dotenv not available, relying on system environment")


def get_capture_folder_from_device_id(device_id: str):
    """
    Get capture folder name from device_id (reverse lookup).
    Used by live events API to find metadata path from device_id.
    
    Args:
        device_id: Device identifier (e.g., 'host', 'device1', 'device2')
    
    Returns:
        Capture folder name (e.g., 'capture1') or None if not found
    """
    # Check HOST
    if device_id == 'host':
        host_capture_path = os.getenv('HOST_VIDEO_CAPTURE_PATH')
        if host_capture_path:
            # Extract folder name from path: '/var/www/html/stream/capture1' -> 'capture1'
            return os.path.basename(host_capture_path)
    
    # Check DEVICE_1 through DEVICE_8
    for i in range(1, 9):
        device_key = f'DEVICE_{i}'
        device_capture_path = os.getenv(f'{device_key}_VIDEO_CAPTURE_PATH')
        device_env_id = os.getenv(f'{device_key}_ID')
        
        if device_env_id == device_id and device_capture_path:
            # Extract folder name from path
            return os.path.basename(device_capture_path)
    
    logger.warning(f"[get_capture_folder_from_device_id] Device {device_id} not found in .env")
    return None

def get_device_info_from_capture_folder(capture_folder):
    """
    Get device info from .env by matching capture path - LIGHTWEIGHT (no DB)
    Extracted from IncidentManager to avoid loading incidents from database
    
    Returns:
        dict: Device info with keys:
            - device_id: Device identifier (e.g., 'device1', 'host')
            - device_name: Human-readable device name from env (e.g., 'Device 1')
            - device_model: Device model from env (e.g., 'H96_MAX', 'X96_MAX_PLUS')
            - stream_path: Video stream path
            - capture_path: Capture folder name (e.g., 'capture1')
    """
    # Check cache first
    if capture_folder in _device_mapping_cache:
        return _device_mapping_cache[capture_folder]
    
    capture_path = f"/var/www/html/stream/{capture_folder}"
    logger.debug(f"[get_device_info] Looking up {capture_folder} -> {capture_path}")
    
    # Check HOST first
    host_capture_path = os.getenv('HOST_VIDEO_CAPTURE_PATH')
    logger.debug(f"[get_device_info] HOST_VIDEO_CAPTURE_PATH={host_capture_path}")
    
    if host_capture_path == capture_path:
        host_name = os.getenv('HOST_NAME', 'unknown')
        host_model = os.getenv('HOST_MODEL', 'unknown')
        host_stream_path = os.getenv('HOST_VIDEO_STREAM_PATH')
        device_info = {
            'device_id': 'host',
            'device_name': f"{host_name}_Host",
            'device_model': host_model,
            'stream_path': host_stream_path,
            'capture_path': capture_folder
        }
        _device_mapping_cache[capture_folder] = device_info
        return device_info
    
    # Check DEVICE1-4
    for i in range(1, 5):
        device_capture_path = os.getenv(f'DEVICE{i}_VIDEO_CAPTURE_PATH')
        device_name = os.getenv(f'DEVICE{i}_NAME', f'device{i}')
        device_model = os.getenv(f'DEVICE{i}_MODEL', 'unknown')
        device_stream_path = os.getenv(f'DEVICE{i}_VIDEO_STREAM_PATH')
        
        if device_capture_path == capture_path:
            device_info = {
                'device_id': f'device{i}',
                'device_name': device_name,
                'device_model': device_model,
                'stream_path': device_stream_path,
                'capture_path': capture_folder
            }
            _device_mapping_cache[capture_folder] = device_info
            return device_info
    
    # Fallback
    device_info = {'device_id': capture_folder, 'device_name': capture_folder, 'device_model': 'unknown', 'stream_path': None, 'capture_path': capture_folder}
    _device_mapping_cache[capture_folder] = device_info
    return device_info


def parse_active_captures_conf():
    """
    Parse active_captures.conf and return structured data.
    CSV Format: /var/www/html/stream/capture1,PID,quality
    
    Returns:
        List of dicts with 'directory', 'pid', 'quality'
    """
    active_captures_file = get_active_captures_conf_path()
    captures = []
    
    if os.path.exists(active_captures_file):
        try:
            with open(active_captures_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split(',')
                    captures.append({
                        'directory': parts[0],
                        'pid': parts[1],
                        'quality': parts[2]
                    })
            
            logger.debug(f"Parsed {len(captures)} capture entries from {active_captures_file}")
        except Exception as e:
            logger.error(f"❌ Error reading {active_captures_file}: {e}")
    
    return captures


def get_capture_base_directories():
    """
    Get list of capture base directories from /tmp/active_captures.conf
    Returns base paths like /var/www/html/stream/capture1 (not /captures subdirectory)
    
    This is the CENTRALIZED source of truth for all capture directory lookups.
    """
    captures = parse_active_captures_conf()
    base_dirs = [c['directory'] for c in captures if os.path.isdir(c['directory'])]
    
    if base_dirs:
        logger.info(f"✅ Loaded {len(base_dirs)} capture directories from active_captures.conf")
    
    return base_dirs


def is_ram_mode(capture_base_dir):
    """
    Check if capture directory uses RAM hot storage
    Returns True if /hot/ exists and is mounted as tmpfs
    
    Args:
        capture_base_dir: Base directory like /var/www/html/stream/capture1
        
    Returns:
        True if RAM mode is active, False otherwise
    """
    hot_path = os.path.join(capture_base_dir, 'hot')
    
    if not os.path.exists(hot_path):
        return False
    
    # Check if it's a tmpfs mount (RAM)
    try:
        with open('/proc/mounts', 'r') as f:
            mounts = f.read()
            if hot_path in mounts and 'tmpfs' in mounts:
                return True
    except Exception:
        pass
    
    # If /hot/ exists but isn't tmpfs, still treat as RAM mode
    # (for development/testing)
    return True

def get_capture_storage_path(device_folder_or_path, subfolder):
    """
    Get the correct storage path based on hot/cold architecture.
    CENTRALIZED PATH RESOLUTION - Use this everywhere!
    
    Args:
        device_folder_or_path: Either:
            - Device folder name (e.g., 'capture1') - RECOMMENDED
            - Full base path (e.g., '/var/www/html/stream/capture1') - backward compatible
        subfolder: Subfolder name ('captures', 'thumbnails', 'segments', 'metadata')
        
    Returns:
        Path to the active storage location (hot if RAM mode, cold otherwise)
        
    Examples:
        # Recommended usage (just device name):
        get_capture_storage_path('capture1', 'captures')
        -> '/var/www/html/stream/capture1/hot/captures' (RAM mode)
        -> '/var/www/html/stream/capture1/captures' (SD mode)
        
        # Backward compatible (full path):
        get_capture_storage_path('/var/www/html/stream/capture1', 'captures')
        -> Same result as above
    """
    # Auto-detect if we got a device name or full path
    if '/' in device_folder_or_path:
        # Full path provided (backward compatible)
        capture_base_dir = device_folder_or_path
    else:
        # Device name provided (recommended) - build full path
        capture_base_dir = get_device_base_path(device_folder_or_path)
    
    # Check RAM mode and return appropriate path
    if is_ram_mode(capture_base_dir):
        # RAM mode: files in /hot/ subdirectory
        return os.path.join(capture_base_dir, 'hot', subfolder)
    else:
        # SD mode: files in root directory
        return os.path.join(capture_base_dir, subfolder)

def get_cold_storage_path(device_folder_or_path, subfolder):
    """
    Get COLD storage path (never uses /hot/ even in RAM mode).
    
    Used for:
    - Audio (MP3 chunks extracted directly to cold)
    - Transcripts (JSON files saved directly to cold)
    - Segments/metadata hour folders (final chunks in cold)
    
    Args:
        device_folder_or_path: Device folder name (e.g., 'capture1') or full path
        subfolder: Subfolder name ('audio', 'transcript', 'segments', 'metadata')
        
    Returns:
        Path to cold storage location (always device_base_path/subfolder)
        
    Examples:
        get_cold_storage_path('capture1', 'audio')
        -> '/var/www/html/stream/capture1/audio' (regardless of RAM mode)
    """
    # Auto-detect if we got a device name or full path
    if '/' in device_folder_or_path:
        # Full path provided
        capture_base_dir = device_folder_or_path
    else:
        # Device name provided - build full path
        capture_base_dir = get_device_base_path(device_folder_or_path)
    
    # Always return cold path (no /hot/ prefix)
    return os.path.join(capture_base_dir, subfolder)


# =====================================================
# HIGH-LEVEL CONVENIENCE FUNCTIONS
# =====================================================
# These functions provide direct access to specific storage paths.
# Other files should use these instead of building paths manually!
# =====================================================

def get_audio_path(device_folder):
    """
    Get audio storage path (HOT or COLD depending on mode).
    
    - HOT: Live MP3 chunks being created/appended in RAM
    - COLD: Final archived audio (SD mode only)
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Path to audio directory:
        - RAM mode: '/var/www/html/stream/capture1/hot/audio'
        - SD mode: '/var/www/html/stream/capture1/audio'
    """
    return get_capture_storage_path(device_folder, 'audio')


def get_transcript_path(device_folder):
    """
    Get transcript storage path (ALWAYS COLD).
    
    Transcript JSON files are saved directly to cold storage by transcript_accumulator.
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Path to transcript directory (e.g., '/var/www/html/stream/capture1/transcript')
    """
    return get_cold_storage_path(device_folder, 'transcript')


def get_segments_path(device_folder):
    """
    Get segments storage path (HOT or COLD depending on mode).
    
    - HOT: Live TS segments being recorded by FFmpeg
    - COLD: Final 10-min MP4 chunks in hour folders
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Path to segments directory:
        - RAM mode: '/var/www/html/stream/capture1/hot/segments'
        - SD mode: '/var/www/html/stream/capture1/segments'
    """
    return get_capture_storage_path(device_folder, 'segments')


def get_cold_segments_path(device_folder):
    """
    Get COLD segments storage path (ALWAYS COLD, never hot).
    
    Used for final 10-minute MP4 chunks that are archived by hot_cold_archiver.
    These chunks are always written to cold storage in hour folders.
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Path to cold segments directory (e.g., '/var/www/html/stream/capture1/segments')
    """
    return get_cold_storage_path(device_folder, 'segments')


def get_captures_path(device_folder):
    """
    Get captures storage path (HOT or COLD depending on mode).
    
    - HOT: Live captures being generated by FFmpeg
    - COLD: Available for scripts/R2 upload
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Path to captures directory:
        - RAM mode: '/var/www/html/stream/capture1/hot/captures'
        - SD mode: '/var/www/html/stream/capture1/captures'
    """
    return get_capture_storage_path(device_folder, 'captures')


def get_thumbnails_path(device_folder):
    """
    Get thumbnails storage path (HOT or COLD depending on mode).
    
    - HOT: Live thumbnails being generated by FFmpeg for freeze detection
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Path to thumbnails directory:
        - RAM mode: '/var/www/html/stream/capture1/hot/thumbnails'
        - SD mode: '/var/www/html/stream/capture1/thumbnails'
    """
    return get_capture_storage_path(device_folder, 'thumbnails')


def get_metadata_path(device_folder):
    """
    Get metadata storage path (HOT or COLD depending on mode).
    
    - HOT: Live individual frame metadata JSONs
    - COLD: Final 10-min grouped metadata chunks in hour folders
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Path to metadata directory:
        - RAM mode: '/var/www/html/stream/capture1/hot/metadata'
        - SD mode: '/var/www/html/stream/capture1/metadata'
    """
    return get_capture_storage_path(device_folder, 'metadata')


def get_transcript_chunk_path(device_folder, hour, chunk_index, language='original'):
    """
    Get path to specific transcript chunk JSON file.
    CENTRALIZED - Use this instead of building paths manually!
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        hour: Hour (0-23)
        chunk_index: Chunk index within hour (0-5 for 10-min chunks)
        language: Language code ('original', 'es', 'fr', etc.)
        
    Returns:
        Full path to transcript JSON file
        (e.g., '/var/www/html/stream/capture1/transcript/1/chunk_10min_0.json')
        (e.g., '/var/www/html/stream/capture1/transcript/1/chunk_10min_0_es.json')
    """
    transcript_base = get_transcript_path(device_folder)
    lang_suffix = '' if language == 'original' else f'_{language}'
    return os.path.join(transcript_base, str(hour), f'chunk_10min_{chunk_index}{lang_suffix}.json')


def get_audio_chunk_path(device_folder, hour, chunk_index, language='original'):
    """
    Get path to specific audio chunk MP3 file.
    CENTRALIZED - Use this instead of building paths manually!
    
    Args:
        device_folder: Device folder name (e.g., 'capture1')
        hour: Hour (0-23)
        chunk_index: Chunk index within hour (0-5 for 10-min chunks)
        language: Language code ('original' for source audio, 'es', 'fr' for dubbed)
        
    Returns:
        Full path to audio MP3 file
        (e.g., '/var/www/html/stream/capture1/audio/1/chunk_10min_0.mp3')
        (e.g., '/var/www/html/stream/capture1/audio/1/chunk_10min_0_es.mp3')
    """
    audio_base = get_cold_storage_path(device_folder, 'audio')
    lang_suffix = '' if language == 'original' else f'_{language}'
    return os.path.join(audio_base, str(hour), f'chunk_10min_{chunk_index}{lang_suffix}.mp3')


def get_capture_folder(capture_dir):
    """
    Extract capture folder name from path (handles both HOT and COLD storage)
    
    Examples:
        /var/www/html/stream/capture1/captures -> capture1
        /var/www/html/stream/capture1/hot/captures -> capture1
        /var/www/html/stream/capture4/hot/segments -> capture4
        /var/www/html/stream/capture4 -> capture4  (base path)
        /var/www/html/stream/capture4/captures/capture_000001.jpg -> capture4  (file path)
    """
    if not capture_dir:
        return None
    
    # Check if this is a hot storage path
    if '/hot/' in capture_dir:
        # Hot path: /var/www/html/stream/capture1/hot/captures
        # Split and get the part before /hot/
        parts = capture_dir.split('/')
        # Find the index of 'hot'
        try:
            hot_index = parts.index('hot')
            # Device folder is one level before 'hot'
            return parts[hot_index - 1]
        except (ValueError, IndexError):
            # Fallback to old logic if 'hot' not found
            return os.path.basename(os.path.dirname(capture_dir))
    else:
        # Check if this is a file path (has extension)
        basename = os.path.basename(capture_dir)
        if '.' in basename:
            # File path: /var/www/html/stream/capture4/captures/capture_000001.jpg
            # Need to go up to find capture folder
            parent_dir = os.path.dirname(capture_dir)  # /var/www/html/stream/capture4/captures
            parent_basename = os.path.basename(parent_dir)  # captures
            if parent_basename in ['captures', 'segments', 'thumbnails', 'metadata', 'audio', 'transcript']:
                # Go up one more level to get capture folder
                return os.path.basename(os.path.dirname(parent_dir))  # capture4
            else:
                # Might already be at capture folder level
                return parent_basename
        elif basename.startswith('capture') and not basename.endswith('s'):
            # Base path like /var/www/html/stream/capture4 -> capture4
            # (check not ending with 's' to avoid matching 'captures' folder)
            return basename
        else:
            # Subfolder path: /var/www/html/stream/capture1/captures -> capture1
            return os.path.basename(os.path.dirname(capture_dir))


def get_capture_number_from_segment(segment_number: int, fps: int) -> int:
    """
    Calculate capture/image number from video segment number based on FPS.
    
    Args:
        segment_number: Video segment number (e.g., 78741 from segment_000078741.ts)
        fps: Frames per second / capture rate (e.g., 5, 2)
        
    Returns:
        Capture number for the corresponding image
        
    Examples:
        >>> get_capture_number_from_segment(78741, 5)
        393705
    """
    return segment_number * fps


def get_segment_number_from_capture(frame_number: int, fps: int) -> int:
    """
    Calculate video segment number from capture/frame number based on FPS.
    (Inverse of get_capture_number_from_segment)
    
    Args:
        frame_number: Frame/capture number (e.g., 2497 from capture_000002497.jpg)
        fps: Frames per second / capture rate (e.g., 5 for v4l2, 2 for x11grab)
        
    Returns:
        Segment number that contains this frame
        
    Examples:
        >>> get_segment_number_from_capture(2497, 5)  # v4l2 device
        499  # segment_000000499.ts
        
        >>> get_segment_number_from_capture(1200, 2)  # x11grab device
        600  # segment_000000600.ts
        
    Note:
        - Each 1-second segment contains exactly FPS frames
        - FPS=5: frames 2495-2499 → segment 499
        - FPS=2: frames 1200-1201 → segment 600
    """
    return frame_number // fps


def get_device_fps(capture_folder: str) -> int:
    """
    Get FPS for a device based on its device model.
    
    Args:
        capture_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        FPS: 5 for hardware devices (v4l2), 2 for VNC devices (x11grab)
        
    Examples:
        >>> get_device_fps('capture1')  # HDMI device
        5
        
        >>> get_device_fps('capture3')  # VNC device
        2
    """
    try:
        device_info = get_device_info_from_capture_folder(capture_folder)
        device_model = device_info.get('device_model', '').lower()
        
        # VNC devices use 2fps, hardware devices use 5fps
        if 'vnc' in device_model or 'x11grab' in device_model or 'host' in device_model:
            return 2
        else:
            return 5  # Default for hardware devices (HDMI, v4l2)
    except Exception as e:
        logger.warning(f"Could not determine FPS for {capture_folder}: {e}, defaulting to 5")
        return 5  # Safe default (most common)


def get_device_segment_duration(capture_folder: str) -> float:
    """
    Get HLS segment duration for a device based on its device model.
    
    Args:
        capture_folder: Device folder name (e.g., 'capture1')
        
    Returns:
        Segment duration in seconds: 1.0 for HDMI devices, 4.0 for VNC devices
        
    Examples:
        >>> get_device_segment_duration('capture1')  # HDMI device
        1.0
        
        >>> get_device_segment_duration('capture3')  # VNC device  
        4.0
        
    Note:
        - HDMI (v4l2): hls_time 1 → 1-second segments (5 fps × 1s = 5 frames)
        - VNC (x11grab): hls_time 4 → 4-second segments (2 fps × 4s = 8 frames)
    """
    try:
        device_info = get_device_info_from_capture_folder(capture_folder)
        device_model = device_info.get('device_model', '').lower()
        
        # VNC devices use 4-second segments, hardware devices use 1-second segments
        if 'vnc' in device_model or 'x11grab' in device_model or 'host' in device_model:
            return 4.0
        else:
            return 1.0  # Default for hardware devices (HDMI, v4l2)
    except Exception as e:
        logger.warning(f"Could not determine segment duration for {capture_folder}: {e}, defaulting to 1.0s")
        return 1.0  # Safe default (most common)


def get_segment_path_from_frame(capture_folder: str, frame_filename: str) -> str:
    """
    Get the segment path for a given frame filename.
    HIGH-LEVEL UTILITY - Handles all the complexity internally!
    
    This function:
    1. Extracts frame number from filename
    2. Determines device FPS automatically (5 for HDMI, 2 for VNC)
    3. Calculates segment number (frame // fps)
    4. Finds segment file (.ts or .mp4)
    5. Returns full path to segment
    
    Args:
        capture_folder: Device folder name (e.g., 'capture1')
        frame_filename: Frame filename (e.g., 'capture_000002497.jpg')
        
    Returns:
        Full path to segment file, or None if not found
        
    Examples:
        >>> get_segment_path_from_frame('capture1', 'capture_000002497.jpg')
        '/var/www/html/stream/capture1/hot/segments/segment_000000499.ts'
        
        >>> get_segment_path_from_frame('capture3', 'capture_000001200.jpg')  # VNC device
        '/var/www/html/stream/capture3/segments/segment_000000600.ts'
        
    Note:
        - Automatically handles hot/cold storage
        - Automatically determines FPS based on device model
        - Tries both .ts and .mp4 extensions
    """
    try:
        # Extract frame number from filename
        frame_number = int(frame_filename.split('_')[1].split('.')[0])
        
        # Get device FPS (automatic)
        device_fps = get_device_fps(capture_folder)
        
        # Calculate segment number (automatic)
        segment_number = get_segment_number_from_capture(frame_number, device_fps)
        
        # Get segments directory (automatic hot/cold detection)
        segments_dir = get_segments_path(capture_folder)
        
        if not os.path.exists(segments_dir):
            logger.warning(f"Segments directory not found: {segments_dir}")
            return None
        
        # Try both .ts and .mp4 extensions
        segment_name_ts = f"segment_{segment_number:09d}.ts"
        segment_name_mp4 = f"segment_{segment_number:09d}.mp4"
        
        segment_path_ts = os.path.join(segments_dir, segment_name_ts)
        segment_path_mp4 = os.path.join(segments_dir, segment_name_mp4)
        
        if os.path.exists(segment_path_ts):
            return segment_path_ts
        elif os.path.exists(segment_path_mp4):
            return segment_path_mp4
        else:
            logger.debug(f"Segment not found for frame {frame_number} (tried {segment_name_ts}, {segment_name_mp4})")
            return None
            
    except Exception as e:
        logger.warning(f"Failed to get segment path from frame {frame_filename}: {e}")
        return None


def calculate_chunk_location(timestamp):
    """
    Calculate hour and chunk_index from timestamp for 10-minute chunks.
    CENTRALIZED - Use this for both metadata and MP4 chunk placement!
    
    Args:
        timestamp: datetime object or ISO format string
        
    Returns:
        Tuple of (hour, chunk_index) where:
        - hour: 0-23 (hour of day)
        - chunk_index: 0-5 (which 10-minute window within the hour)
        
    Examples:
        >>> from datetime import datetime
        >>> calculate_chunk_location(datetime(2025, 10, 9, 15, 4))
        (15, 0)  # 15:00-15:10
        >>> calculate_chunk_location(datetime(2025, 10, 9, 15, 25))
        (15, 2)  # 15:20-15:30
    """
    from datetime import datetime
    
    # Handle string timestamps
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)
    
    hour = timestamp.hour
    chunk_index = timestamp.minute // 10  # 0-5 for 10-minute windows
    
    return hour, chunk_index


def copy_to_cold_storage(hot_or_cold_path):
    """
    Copy file from hot to cold storage if needed. If already in cold, return as-is.
    
    Args:
        hot_or_cold_path: File path (hot or cold storage)
        
    Returns:
        Cold storage path, or None if copy failed
    """
    import shutil
    
    if '/hot/' not in hot_or_cold_path:
        return hot_or_cold_path  # Already in cold
    
    cold_path = hot_or_cold_path.replace('/hot/', '/')
    os.makedirs(os.path.dirname(cold_path), exist_ok=True)
    
    if os.path.exists(hot_or_cold_path):
        shutil.copy2(hot_or_cold_path, cold_path)
        return cold_path
    
    return None