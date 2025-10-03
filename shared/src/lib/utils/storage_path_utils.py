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
    
    # Get script paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_host_dir = os.path.dirname(current_dir)
    project_root = os.path.dirname(backend_host_dir)
    
    # Load project root .env first
    project_env_path = os.path.join(project_root, '.env')
    if os.path.exists(project_env_path):
        load_dotenv(project_env_path)
        logger.debug(f"Loaded project environment from {project_env_path}")
    
    # Load backend_host .env second
    backend_env_path = os.path.join(backend_host_dir, 'src', '.env')
    if os.path.exists(backend_env_path):
        load_dotenv(backend_env_path)
        logger.debug(f"Loaded backend_host environment from {backend_env_path}")
        
except ImportError:
    logger.warning("python-dotenv not available, relying on system environment")


def get_device_info_from_capture_folder(capture_folder):
    """
    Get device info from .env by matching capture path - LIGHTWEIGHT (no DB)
    Extracted from IncidentManager to avoid loading incidents from database
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
        host_stream_path = os.getenv('HOST_VIDEO_STREAM_PATH')
        device_info = {
            'device_id': 'host',
            'device_name': f"{host_name}_Host",
            'stream_path': host_stream_path,
            'capture_path': capture_folder
        }
        _device_mapping_cache[capture_folder] = device_info
        return device_info
    
    # Check DEVICE1-4
    for i in range(1, 5):
        device_capture_path = os.getenv(f'DEVICE{i}_VIDEO_CAPTURE_PATH')
        device_name = os.getenv(f'DEVICE{i}_NAME', f'device{i}')
        device_stream_path = os.getenv(f'DEVICE{i}_VIDEO_STREAM_PATH')
        
        if device_capture_path == capture_path:
            device_info = {
                'device_id': f'device{i}',
                'device_name': device_name,
                'stream_path': device_stream_path,
                'capture_path': capture_folder
            }
            _device_mapping_cache[capture_folder] = device_info
            return device_info
    
    # Fallback
    device_info = {'device_id': capture_folder, 'device_name': capture_folder, 'stream_path': None, 'capture_path': capture_folder}
    _device_mapping_cache[capture_folder] = device_info
    return device_info


def get_capture_base_directories():
    """
    Get list of capture base directories from /tmp/active_captures.conf
    Returns base paths like /var/www/html/stream/capture1 (not /captures subdirectory)
    
    This is the CENTRALIZED source of truth for all capture directory lookups.
    """
    active_captures_file = '/tmp/active_captures.conf'
    base_dirs = []
    
    # Read from centralized config file written by run_ffmpeg_and_rename_local.sh
    if os.path.exists(active_captures_file):
        try:
            with open(active_captures_file, 'r') as f:
                for line in f:
                    capture_base = line.strip()
                    if capture_base and os.path.isdir(capture_base):
                        base_dirs.append(capture_base)
                
                logger.info(f"✅ Loaded {len(base_dirs)} capture directories from {active_captures_file}")
                return base_dirs
        except Exception as e:
            logger.error(f"❌ Error reading {active_captures_file}: {e}")
    
    # Auto-discover if config file doesn't exist
    logger.warning(f"⚠️ {active_captures_file} not found, auto-discovering directories")
    stream_base = get_stream_base_path()  # CENTRALIZED - No hardcoding!
    
    if os.path.exists(stream_base):
        for entry in sorted(os.listdir(stream_base)):
            if entry.startswith('capture') and os.path.isdir(os.path.join(stream_base, entry)):
                base_dirs.append(os.path.join(stream_base, entry))
    
    # Fallback to common capture folders
    if not base_dirs:
        logger.warning(f"⚠️ No directories found, using default capture folders")
        for i in range(1, 5):  # capture1-4
            capture_dir = get_device_base_path(f'capture{i}')
            if os.path.exists(capture_dir):
                base_dirs.append(capture_dir)
    
    return base_dirs


def get_capture_directories():
    """
    Get list of capture directories (with /captures subdirectory)
    Legacy function for backward compatibility with capture_monitor.py
    """
    base_dirs = get_capture_base_directories()
    return [os.path.join(d, 'captures') for d in base_dirs if os.path.exists(os.path.join(d, 'captures'))]


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

def get_capture_folder(capture_dir):
    """Extract capture folder from path"""
    # /var/www/html/stream/capture1/captures -> capture1
    return os.path.basename(os.path.dirname(capture_dir))

def generate_manifest_for_segments(stream_dir, segments, manifest_name):
    """Generate a single manifest file for given segments"""
    if not segments:
        logger.warning(f"[@generate_manifest] No segments provided for {manifest_name}")
        return False
    
    # Calculate proper media sequence number (first segment number in window)
    first_segment_num = int(os.path.basename(segments[0]).split('_')[1].split('.')[0])
    last_segment_num = int(os.path.basename(segments[-1]).split('_')[1].split('.')[0])
    
    logger.debug(f"[@generate_manifest] {manifest_name}: segments #{first_segment_num}-#{last_segment_num} ({len(segments)} files)")
    
    # Generate manifest content
    manifest_content = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:4",
        f"#EXT-X-MEDIA-SEQUENCE:{first_segment_num}"
    ]
    
    for segment in segments:
        segment_name = os.path.basename(segment)
        manifest_content.extend([
            "#EXTINF:1.000000,",
            segment_name
        ])
    
    manifest_content.append("#EXT-X-ENDLIST")
    
    # Write manifest atomically - use hot storage if RAM mode
    if is_ram_mode(stream_dir):
        hot_dir = os.path.join(stream_dir, 'hot')
        os.makedirs(hot_dir, exist_ok=True)
        manifest_path = os.path.join(hot_dir, manifest_name)
    else:
        manifest_path = os.path.join(stream_dir, manifest_name)
    
    with open(manifest_path + '.tmp', 'w') as f:
        f.write('\n'.join(manifest_content))
    
    os.rename(manifest_path + '.tmp', manifest_path)
    logger.info(f"[@generate_manifest] ✓ {manifest_name}: {len(segments)} segments (#{first_segment_num}-#{last_segment_num})")
    return True

def update_archive_manifest(capture_dir):
    """Generate dynamic 1-hour archive manifests with progressive creation (with incremental updates)"""
    try:
        capture_folder = get_capture_folder(capture_dir)
        
        # Get device base directory (parent of /captures/)
        stream_dir = os.path.dirname(capture_dir.rstrip('/'))  # /var/www/html/stream/capture1
        
        # Configuration for 1-hour manifest windows
        WINDOW_HOURS = 1
        SEGMENT_DURATION = 1  # seconds per segment (from FFmpeg config)
        SEGMENTS_PER_WINDOW = WINDOW_HOURS * 3600 // SEGMENT_DURATION  # 3,600 segments per 1h window
        MAX_MANIFESTS = 24  # Support up to 24 hours (24 manifests)
        
        # Load state for incremental updates - use hot storage if RAM mode
        if is_ram_mode(stream_dir):
            hot_dir = os.path.join(stream_dir, 'hot')
            os.makedirs(hot_dir, exist_ok=True)
            state_file = os.path.join(hot_dir, 'archive_state.json')
        else:
            state_file = os.path.join(stream_dir, 'archive_state.json')
        
        state = json.load(open(state_file, 'r')) if os.path.exists(state_file) else {}
        last_max_segment = state.get('last_max_segment', 0)
        
        # Quick check: Find max segment number (early exit if no changes)
        segment_pattern = re.compile(r'^segment_(\d+)\.ts$')
        max_segment = 0
        
        for entry in os.scandir(stream_dir):
            try:
                if entry.is_file(follow_symlinks=False):
                    match = segment_pattern.match(entry.name)
                    if match:
                        max_segment = max(max_segment, int(match.group(1)))
            except (FileNotFoundError, OSError):
                continue
        
        # No new segments? Skip entire process
        if max_segment <= last_max_segment:
            logger.debug(f"[@update_archive] [{capture_folder}] No new segments (max={max_segment}), skipping")
            return
        
        logger.info(f"[@update_archive] [{capture_folder}] New segments detected: {last_max_segment} → {max_segment} (+{max_segment - last_max_segment})")
        
        # Get segments from last 24 hours only
        cutoff_time = time.time() - (24 * 3600)
        
        # Use os.scandir directly (avoid circular import with system_info_utils)
        segments = []
        segment_pattern = re.compile(r'^segment_.*\.ts$')
        try:
            for entry in os.scandir(stream_dir):
                if entry.is_file() and segment_pattern.match(entry.name):
                    try:
                        mtime = entry.stat().st_mtime
                        if mtime >= cutoff_time:
                            segments.append(entry.path)
                    except (FileNotFoundError, OSError):
                        continue
        except (FileNotFoundError, OSError):
            pass
        
        if not segments:
            logger.debug(f"[@update_archive] [{capture_folder}] No segments in last 24h")
            return
            
        # Sort segments by mtime (chronological order - handles FFmpeg restarts & gaps)
        segments.sort(key=lambda x: os.path.getmtime(x))
        
        first_seg_num = int(os.path.basename(segments[0]).split('_')[1].split('.')[0])
        last_seg_num = int(os.path.basename(segments[-1]).split('_')[1].split('.')[0])
        total_segments = len(segments)
        
        logger.info(f"[@update_archive] [{capture_folder}] Processing {total_segments} segments (#{first_seg_num}-#{last_seg_num})")
        num_windows = (total_segments + SEGMENTS_PER_WINDOW - 1) // SEGMENTS_PER_WINDOW
        
        manifests_generated = 0
        manifest_metadata = []  # Store metadata with actual segment numbers
        
        for window_idx in range(num_windows):
            start_idx = window_idx * SEGMENTS_PER_WINDOW
            end_idx = min(start_idx + SEGMENTS_PER_WINDOW, total_segments)
            window_segments = segments[start_idx:end_idx]
            
            # Only generate if we have segments in this window
            if len(window_segments) > 0:
                manifest_name = f"archive{window_idx + 1}.m3u8"
                
                # Extract actual segment numbers from filenames
                first_seg_num = int(os.path.basename(window_segments[0]).split('_')[1].split('.')[0])
                last_seg_num = int(os.path.basename(window_segments[-1]).split('_')[1].split('.')[0])
                
                if generate_manifest_for_segments(stream_dir, window_segments, manifest_name):
                    manifests_generated += 1
                    
                    # Store metadata with actual segment numbers for this manifest
                    manifest_metadata.append({
                        "name": manifest_name,
                        "window_index": window_idx + 1,
                        "start_segment": first_seg_num,
                        "end_segment": last_seg_num,
                        "start_time_seconds": start_idx * SEGMENT_DURATION,
                        "end_time_seconds": end_idx * SEGMENT_DURATION,
                        "duration_seconds": len(window_segments) * SEGMENT_DURATION
                    })
        
        # Generate metadata JSON for frontend to know which manifests to use
        metadata = {
            "total_segments": total_segments,
            "total_duration_seconds": total_segments * SEGMENT_DURATION,
            "window_hours": WINDOW_HOURS,
            "segments_per_window": SEGMENTS_PER_WINDOW,
            "manifests": manifest_metadata
        }
        
        # Write metadata JSON - use hot storage if RAM mode
        if is_ram_mode(stream_dir):
            metadata_path = os.path.join(stream_dir, 'hot', 'archive_metadata.json')
        else:
            metadata_path = os.path.join(stream_dir, 'archive_metadata.json')
        
        try:
            with open(metadata_path + '.tmp', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            os.rename(metadata_path + '.tmp', metadata_path)
            logger.info(f"[@update_archive] [{capture_folder}] ✓ Written metadata: {metadata_path}")
        except Exception as e:
            logger.error(f"[@update_archive] [{capture_folder}] ❌ Failed to write metadata: {e}")
        
        # Legacy archive.m3u8 - points to most recent manifest for simple players
        if manifests_generated > 0:
            # Use hot storage if RAM mode
            if is_ram_mode(stream_dir):
                archive_path = os.path.join(stream_dir, 'hot', 'archive.m3u8')
                last_manifest_name = f'archive{manifests_generated}.m3u8'
                last_manifest_path = os.path.join(stream_dir, 'hot', last_manifest_name)
            else:
                archive_path = os.path.join(stream_dir, 'archive.m3u8')
                last_manifest_name = f'archive{manifests_generated}.m3u8'
                last_manifest_path = os.path.join(stream_dir, last_manifest_name)
            
            try:
                with open(archive_path + '.tmp', 'w') as f:
                    f.write(f"# Use archive_metadata.json for multi-manifest playback\n")
                    f.write(f"# This manifest points to the most recent archive window ({last_manifest_name})\n")
                    # Point to most recent manifest for simple players
                    with open(last_manifest_path, 'r') as src:
                        f.write(src.read())
                
                os.rename(archive_path + '.tmp', archive_path)
                logger.info(f"[@update_archive] [{capture_folder}] ✓ Written legacy archive.m3u8 -> {last_manifest_name}")
            except Exception as e:
                logger.error(f"[@update_archive] [{capture_folder}] ❌ Failed to write archive.m3u8: {e}")
        
        # Cleanup old manifests beyond current window
        # If we only generated 5 manifests, remove archive6-24 if they exist from previous runs
        if is_ram_mode(stream_dir):
            manifests_dir = os.path.join(stream_dir, 'hot')
        else:
            manifests_dir = stream_dir
        
        for old_idx in range(manifests_generated + 1, MAX_MANIFESTS + 1):
            old_manifest = os.path.join(manifests_dir, f'archive{old_idx}.m3u8')
            if os.path.exists(old_manifest):
                try:
                    os.remove(old_manifest)
                    logger.debug(f"[{capture_folder}] Cleaned up unused {os.path.basename(old_manifest)}")
                except Exception as e:
                    logger.warning(f"[{capture_folder}] Failed to remove {old_manifest}: {e}")
        
        total_duration_hours = total_segments * SEGMENT_DURATION / 3600
        logger.info(f"[@update_archive] [{capture_folder}] ✓ Generated {manifests_generated} manifests, {total_segments} segments ({total_duration_hours:.1f}h)")
        
        # Save state for next run (incremental updates)
        state = {'last_max_segment': max_segment, 'last_update': time.time()}
        with open(state_file + '.tmp', 'w') as f:
            json.dump(state, f, indent=2)
        os.rename(state_file + '.tmp', state_file)
        
    except Exception as e:
        logger.error(f"Error updating archive manifest for {capture_dir}: {e}")

