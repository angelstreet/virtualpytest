#!/usr/bin/env python3
"""
Frame detector - analyzes frames for issues with rich metadata
Returns same format as original analyze_audio_video.py
"""
import os
import sys
import subprocess
import time
import logging
from datetime import datetime

from shared.src.lib.utils.storage_path_utils import is_ram_mode

logger = logging.getLogger('capture_monitor')
from shared.src.lib.utils.image_utils import (
    load_and_downscale_image,
    analyze_blackscreen,
    analyze_freeze,
    analyze_macroblocks,
    analyze_subtitle_region
)

# Performance: Cache audio analysis results to avoid redundant FFmpeg calls
_audio_cache = {}  # {segment_path: (mtime, has_audio, volume, db)}
_latest_segment_cache = {}  # {capture_dir: (segment_path, mtime, last_check_time)}
_subtitle_cache = {}  # {image_path: (mtime, subtitle_result)}
_audio_result_cache = {}  # {capture_dir: (has_audio, volume, db)} - Last known audio state per device

def analyze_audio(capture_dir):
    """Check if audio is present in latest segment - OPTIMIZED with caching"""
    global _audio_cache, _latest_segment_cache
    
    current_time = time.time()
    latest = None
    latest_mtime = 0
    
    # Use centralized hot/cold detection - check RAM mode
    if is_ram_mode(capture_dir):
        # RAM mode: segments in /hot/segments/ (tmpfs)
        segments_dir = os.path.join(capture_dir, 'hot', 'segments')
    else:
        # SD mode: segments in /segments/ root
        segments_dir = os.path.join(capture_dir, 'segments')
    
    # CRITICAL FIX: Check cache first - only rescan directory every 5 seconds
    if capture_dir in _latest_segment_cache:
        cached_path, cached_mtime, last_check = _latest_segment_cache[capture_dir]
        
        # Reuse cached path if checked recently (within 5 seconds)
        if current_time - last_check < 5.0:
            # Verify cached file still exists and get its current mtime
            if os.path.exists(cached_path):
                try:
                    current_file_mtime = os.path.getmtime(cached_path)
                    latest = cached_path
                    latest_mtime = current_file_mtime
                except:
                    pass  # Will rescan below
    
    # Rescan if cache miss or cache expired (every 5 seconds) - HOT STORAGE ONLY
    if not latest and os.path.exists(segments_dir):
        try:
            with os.scandir(segments_dir) as it:
                for entry in it:
                    # Only check files in hot storage (root), not hour folders (max 10 files)
                    if entry.is_file() and entry.name.startswith('segment_') and entry.name.endswith('.ts'):
                        mtime = entry.stat().st_mtime
                        if mtime > latest_mtime:
                            latest = entry.path
                            latest_mtime = mtime
        except Exception:
            return True, 0, -100.0
        
        # Update cache
        if latest:
            _latest_segment_cache[capture_dir] = (latest, latest_mtime, current_time)
    
    if not latest:
        return True, 0, -100.0
    
    # Check if recent (within last 5 minutes)
    current_time = time.time()
    age_seconds = current_time - latest_mtime
    if age_seconds > 300:  # 5 minutes
        return False, 0, -100.0
    
    # PERFORMANCE: Check cache first - avoid redundant FFmpeg calls (90% reduction)
    if latest in _audio_cache:
        cached_mtime, has_audio, volume, db = _audio_cache[latest]
        if cached_mtime == latest_mtime:
            return has_audio, volume, db
    
    try:
        from shared.src.lib.utils.audio_transcription_utils import detect_audio_level
        
        has_audio, volume_percentage, mean_volume = detect_audio_level(latest, device_id="")
        
        # Cache the result
        _audio_cache[latest] = (latest_mtime, has_audio, volume_percentage, mean_volume)
        
        # Clean old cache entries to prevent memory growth
        if len(_audio_cache) > 50:
            _audio_cache = dict(list(_audio_cache.items())[-20:])
        
        return has_audio, volume_percentage, mean_volume
    except Exception as e:
        # Fallback if import fails
        return False, 0, -100.0

def analyze_subtitles(image_path, fps=5):
    """
    Analyze subtitle region on full-res capture (1280x720).
    Runs every 1 second (every 5th frame at 5fps, every 2nd frame at 2fps VNC).
    """
    global _subtitle_cache
    
    try:
        filename = os.path.basename(image_path)
        frame_number = int(filename.split('_')[1].split('.')[0])
    except:
        return None
    
    sample_interval = fps if fps >= 2 else 2
    if frame_number % sample_interval != 0:
        return None
    
    if image_path in _subtitle_cache:
        cached_mtime, cached_result = _subtitle_cache[image_path]
        try:
            current_mtime = os.path.getmtime(image_path)
            if cached_mtime == current_mtime:
                return cached_result
        except:
            pass
    
    try:
        import cv2
        
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        resized = cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA)
        result = analyze_subtitle_region(resized, extract_text=True)
        
        try:
            mtime = os.path.getmtime(image_path)
            _subtitle_cache[image_path] = (mtime, result)
            if len(_subtitle_cache) > 30:
                _subtitle_cache = dict(list(_subtitle_cache.items())[-15:])
        except:
            pass
        
        return result
        
    except ImportError:
        return None
    except Exception as e:
        return {'has_subtitles': False, 'error': str(e)}

def detect_issues(image_path, fps=5):
    """
    Main detection function - returns EXACT same format as original analyze_audio_video.py
    
    Args:
        image_path: Path to capture image
        fps: Frames per second (5 for v4l2, 2 for x11grab/VNC) - used for freeze detection
    """
    capture_dir = os.path.dirname(os.path.dirname(image_path))  # Go up from /captures/
    
    # Get thumbnails directory (handles both RAM and SD modes)
    try:
        from shared.src.lib.utils.build_url_utils import get_device_local_thumbnails_path
        thumbnails_dir = get_device_local_thumbnails_path(image_path)
    except:
        # Fallback to manual path construction
        captures_dir = os.path.dirname(image_path)
        capture_parent = os.path.dirname(captures_dir)
        thumbnails_dir = os.path.join(capture_parent, 'thumbnails')
    
    # Load and downscale image ONCE for blackscreen detection (320x180)
    # Saves: 1280x720 → 320x180 = 16× less pixels to process
    downscaled_img = load_and_downscale_image(image_path, target_size=(320, 180))
    
    # Video Analysis
    blackscreen, blackscreen_percentage = analyze_blackscreen(image_path, downscaled_img=downscaled_img)
    
    # Freeze detection using thumbnails (5fps for v4l2, 2fps for VNC)
    frozen, freeze_details = analyze_freeze(image_path, thumbnails_dir, fps)
    
    # Skip macroblock analysis if freeze or blackscreen detected (performance optimization)
    if blackscreen or frozen:
        macroblocks, quality_score = False, 0.0
    else:
        macroblocks, quality_score = analyze_macroblocks(image_path)
    
    # Audio Analysis - Sample every 5 seconds to reduce FFmpeg calls (80% reduction)
    # Extract frame number from filename (capture_000001234.jpg)
    try:
        filename = os.path.basename(image_path)
        frame_number = int(filename.split('_')[1].split('.')[0])
    except:
        frame_number = 0
    
    # Check audio every 5 seconds: every 25 frames at 5fps, every 10 frames at 2fps
    audio_check_interval = fps * 5  # 5 seconds worth of frames
    should_check_audio = (frame_number % audio_check_interval == 0)
    
    global _audio_result_cache
    
    if should_check_audio:
        # Actually check audio (calls FFmpeg)
        has_audio, volume_percentage, mean_volume_db = analyze_audio(capture_dir)
        # Cache the result for use by other frames
        _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db)
    else:
        # Use cached result from last audio check (no FFmpeg call)
        if capture_dir in _audio_result_cache:
            has_audio, volume_percentage, mean_volume_db = _audio_result_cache[capture_dir]
        else:
            # First frame or no cache yet - do one check to initialize
            has_audio, volume_percentage, mean_volume_db = analyze_audio(capture_dir)
            _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db)
    
    # Subtitle Analysis (every 1 second only)
    subtitle_result = analyze_subtitles(image_path, fps)
    
    # Get frame paths for R2 upload - freeze_details now contains thumbnail filenames
    freeze_diffs = []
    last_3_filenames = []
    last_3_thumbnails = []
    
    if freeze_details and 'frame_differences' in freeze_details:
        freeze_diffs = freeze_details['frame_differences']
        
    if freeze_details and 'frames_compared' in freeze_details:
        # frames_compared now contains thumbnail filenames (e.g., capture_000009_thumbnail.jpg)
        # Build full paths for both captures and thumbnails
        captures_dir = os.path.dirname(image_path)
        
        for thumbnail_filename in freeze_details['frames_compared']:
            # Convert thumbnail filename to capture filename by removing _thumbnail suffix
            # capture_000009_thumbnail.jpg → capture_000009.jpg
            capture_filename = thumbnail_filename.replace('_thumbnail.jpg', '.jpg')
            capture_full_path = os.path.join(captures_dir, capture_filename)
            last_3_filenames.append(capture_full_path)
            
            # Thumbnail with full path (already determined by thumbnails_dir above)
            thumbnail_full_path = os.path.join(thumbnails_dir, thumbnail_filename)
            last_3_thumbnails.append(thumbnail_full_path)
    
    result = {
        'timestamp': datetime.fromtimestamp(os.path.getmtime(image_path)).isoformat(),
        'filename': os.path.basename(image_path),
        'blackscreen': bool(blackscreen),
        'blackscreen_percentage': round(blackscreen_percentage, 1),
        'freeze': bool(frozen),
        'freeze_diffs': freeze_diffs,
        'last_3_filenames': last_3_filenames,
        'last_3_thumbnails': last_3_thumbnails,
        'macroblocks': bool(macroblocks),
        'quality_score': round(quality_score, 1),
        'audio': has_audio,
        'volume_percentage': volume_percentage,
        'mean_volume_db': mean_volume_db
    }
    
    if subtitle_result:
        result['subtitle_analysis'] = subtitle_result
    
    return result
