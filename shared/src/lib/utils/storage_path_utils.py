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


def parse_active_captures_conf():
    """
    Parse /tmp/active_captures.conf and return structured data.
    CSV Format: /var/www/html/stream/capture1,PID,quality
    
    Returns:
        List of dicts with 'directory', 'pid', 'quality'
    """
    active_captures_file = '/tmp/active_captures.conf'
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

def get_capture_folder(capture_dir):
    """Extract capture folder from path"""
    # /var/www/html/stream/capture1/captures -> capture1
    return os.path.basename(os.path.dirname(capture_dir))