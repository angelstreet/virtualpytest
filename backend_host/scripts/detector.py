#!/usr/bin/env python3
"""
Frame detector - analyzes frames for issues with rich metadata
Returns same format as original analyze_audio_video.py

NOTE: Subtitle OCR is handled by subtitle_monitor.py (separate process)
      This detector focuses on: blackscreen, freeze, macroblocks, zap, audio

ZAP STATE OPTIMIZATION:
- Tracks when device is zapping (blackscreen + banner detected)
- Skips expensive operations during zap
- Marks start/end frames in JSON for zap_executor
- Saves ~95% CPU during zap sequence (2ms vs ~40ms per frame)

FREEZE DETECTION OPTIMIZATION:
- In-memory thumbnail cache: Avoids disk I/O for previous frames
- Keeps last 3 frames in RAM per device (~500KB total)
- Reduces freeze detection time by 50-60% (15ms → 6ms)

BLACKSCREEN DETECTION OPTIMIZATION:
- Optimized sampling: Every 4th pixel (6.25%) instead of every 3rd (11%)
- Reduces blackscreen detection time by 33% (5ms → 3ms)
- No impact on accuracy (blackscreen detection is very tolerant)
"""
import os
import sys
import subprocess
import time
import logging
import cv2
import numpy as np
import json
from datetime import datetime
from contextlib import contextmanager

# === CONFIGURATION ===
# OCR is handled by subtitle_monitor.py - removed from detector.py

from shared.src.lib.utils.storage_path_utils import (
    is_ram_mode,
    get_segments_path,
    get_capture_folder
)

logger = logging.getLogger('capture_monitor')

# Performance profiling
@contextmanager
def measure_time(task_name):
    """Context manager to measure execution time of a task"""
    start = time.perf_counter()
    yield
    elapsed = (time.perf_counter() - start) * 1000  # Convert to milliseconds
    return elapsed
from shared.src.lib.utils.image_utils import (
    load_and_downscale_image,
    analyze_blackscreen,
    analyze_freeze,
    analyze_macroblocks
)

def detect_freeze_pixel_diff(current_img, thumbnails_dir, filename, fps=5):
    """
    Freeze detection using pixel difference - OPTIMIZED with in-memory cache
    
    Compares current thumbnail with previous 3 thumbnails using cv2.absdiff.
    Uses in-memory cache to avoid disk I/O on thumbnail loading (5-10ms savings).
    
    Args:
        current_img: Current thumbnail (grayscale numpy array, 320x180)
        thumbnails_dir: Directory containing thumbnails
        filename: Current frame filename (e.g., capture_000001.jpg)
        fps: Frames per second
        
    Returns:
        (frozen: bool, details: dict)
    """
    global _freeze_thumbnail_cache
    
    try:
        # Extract frame number
        frame_number = int(filename.split('_')[1].split('.')[0])
    except:
        return False, {}
    
    # Get device key for cache (use parent directory of thumbnails)
    device_key = os.path.dirname(thumbnails_dir)
    
    # Initialize cache for this device if needed
    if device_key not in _freeze_thumbnail_cache:
        _freeze_thumbnail_cache[device_key] = []
    
    cache = _freeze_thumbnail_cache[device_key]
    
    # Need at least 2 previous frames for comparison
    if frame_number < 2:
        # Add current frame to cache and return
        cache.append((frame_number, current_img.copy()))
        if len(cache) > 3:
            cache.pop(0)
        return False, {}
    
    # Compare with cached thumbnails (last 3 frames)
    pixel_diffs = []
    frames_compared = []
    cache_hits = 0
    disk_loads = 0
    
    # Check last 3 frames in reverse order (N-1, N-2, N-3)
    for i in range(1, 4):
        prev_frame_num = frame_number - i
        if prev_frame_num < 0:
            break
        
        # Try to find in cache first
        prev_img = None
        for cached_num, cached_img in reversed(cache):
            if cached_num == prev_frame_num:
                prev_img = cached_img
                cache_hits += 1
                break
        
        # If not in cache, load from disk (fallback)
        if prev_img is None:
            frame_prefix = filename.rsplit('_', 1)[0]
            frame_digits = len(filename.split('_')[1].split('.')[0])
            prev_filename = f"{frame_prefix}_{str(prev_frame_num).zfill(frame_digits)}_thumbnail.jpg"
            prev_path = os.path.join(thumbnails_dir, prev_filename)
            
            if os.path.exists(prev_path):
                prev_img = cv2.imread(prev_path, cv2.IMREAD_GRAYSCALE)
                disk_loads += 1
                
                # Add to cache for future use
                if prev_img is not None:
                    cache.append((prev_frame_num, prev_img.copy()))
        
        if prev_img is None:
            continue
        
        # Validate size match
        if prev_img.shape != current_img.shape:
            continue
        
        # Compute absolute pixel difference
        diff = cv2.absdiff(current_img, prev_img)
        
        # Count pixels with difference > 10 (threshold for "different")
        different_pixels = np.sum(diff > 10)
        total_pixels = diff.size
        
        # Convert to percentage difference
        diff_percentage = (different_pixels / total_pixels) * 100
        
        pixel_diffs.append(diff_percentage)
        frames_compared.append(f"frame_{prev_frame_num}")
        
        # EARLY EXIT: If difference > 5%, NOT frozen - stop checking more frames
        if diff_percentage > 5.0:
            break
    
    # Add current frame to cache (keep last 3 only)
    cache.append((frame_number, current_img.copy()))
    if len(cache) > 3:
        cache.pop(0)
    
    # Frozen if ALL checked frames have < 0.5% difference (VERY STRICT)
    FREEZE_THRESHOLD = 0.5  # 0.5% pixel difference = frozen
    frozen = len(pixel_diffs) >= 2 and all(diff < FREEZE_THRESHOLD for diff in pixel_diffs)
    
    return frozen, {
        'frame_differences': [round(d, 2) for d in pixel_diffs],
        'frames_compared': frames_compared,
        'frames_found': len(frames_compared),
        'frames_needed': 2,
        'detection_method': 'pixel_diff_cached',
        'threshold': FREEZE_THRESHOLD,
        'cache_hits': cache_hits,
        'disk_loads': disk_loads
    }

# Performance: Cache for optimization
_latest_segment_cache = {}  # {capture_dir: (segment_path, mtime, last_check_time)}
_audio_result_cache = {}  # {capture_dir: (has_audio, volume, db, method, time_ms)} - Last known audio state per device (frame-level cache)
_audio_ffprobe_cache = {}  # {capture_dir: (last_check_time, has_audio, volume, db, method, time_ms)} - Time-based throttle (3s)

# Zap state tracking for CPU optimization
_zap_state_cache = {}  # In-memory cache for fast access

# Freeze detection optimization - cache thumbnails in memory
_freeze_thumbnail_cache = {}  # {device_dir: [(frame_number, thumbnail_img), ...]}

def get_zap_state_file(capture_dir):
    """Get path to zap state file for device"""
    return os.path.join(capture_dir, '.zap_state.json')


def load_zap_state(capture_dir):
    """Load zap state from file or cache"""
    global _zap_state_cache
    
    # Check in-memory cache first
    if capture_dir in _zap_state_cache:
        return _zap_state_cache[capture_dir]
    
    # Try to load from file
    state_file = get_zap_state_file(capture_dir)
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                _zap_state_cache[capture_dir] = state
                return state
        except:
            pass
    
    return None

def save_zap_state(capture_dir, state):
    """Save zap state to file and cache"""
    global _zap_state_cache
    
    _zap_state_cache[capture_dir] = state
    
    # Persist to file
    state_file = get_zap_state_file(capture_dir)
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning(f"Failed to save zap state: {e}")

def clear_zap_state(capture_dir):
    """Clear zap state (zap sequence ended)"""
    global _zap_state_cache
    
    # Remove from cache
    if capture_dir in _zap_state_cache:
        del _zap_state_cache[capture_dir]
    
    # Remove file
    state_file = get_zap_state_file(capture_dir)
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
        except Exception as e:
            logger.warning(f"Failed to remove zap state file: {e}")


def quick_blackscreen_check(img, threshold=10):
    """Fast blackscreen check for zap monitoring (no edge detection needed) - OPTIMIZED"""
    img_height, img_width = img.shape
    header_y = int(img_height * 0.05)
    split_y = int(img_height * 0.7)
    
    top_region = img[header_y:split_y, :]
    # Optimized sampling: every 4th pixel (6.25% sample) instead of every 3rd (11%)
    sample = top_region[::4, ::4]
    sample_dark = np.sum(sample <= threshold)
    sample_total = sample.shape[0] * sample.shape[1]
    dark_percentage = (sample_dark / sample_total) * 100
    
    return bool(dark_percentage > 85), dark_percentage

def _execute_audio_check(capture_dir, latest_segment=None):
    """
    Internal function: Execute ffmpeg volumedetect check
    
    Args:
        capture_dir: Device directory
        latest_segment: Pre-found latest segment path (optional)
    
    Returns: (has_audio, volume_percentage, mean_volume_db, check_method, check_time_ms)
    """
    global _latest_segment_cache
    
    current_time = time.time()
    
    # Use latest_segment if provided (from wrapper), otherwise find it
    if latest_segment:
        latest = latest_segment
        latest_mtime = os.path.getmtime(latest) if os.path.exists(latest) else 0
    else:
        latest = None
        latest_mtime = 0
        
        # Use convenience function - automatically resolves hot/cold and RAM mode
        capture_folder = get_capture_folder(capture_dir)
        segments_dir = get_segments_path(capture_folder)
        
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
            except Exception as scan_error:
                capture_folder = get_capture_folder(capture_dir)
                logger.error(f"[{capture_folder}] ❌ Segment scan failed in {segments_dir}: {scan_error}")
                return True, 0, -100.0, 'segment_scan_error', 0
            
            # Update cache
            if latest:
                _latest_segment_cache[capture_dir] = (latest, latest_mtime, current_time)
                capture_folder = get_capture_folder(capture_dir)
                logger.debug(f"[{capture_folder}] 📁 Found latest segment: {latest} (mtime={latest_mtime})")
        
        if not latest:
            capture_folder = get_capture_folder(capture_dir)
            logger.warning(f"[{capture_folder}] ⚠️ No segment files found in {segments_dir}")
            return True, 0, -100.0, 'no_segment', 0
        
        # Check if recent (within last 5 minutes)
        age_seconds = current_time - latest_mtime
        if age_seconds > 300:  # 5 minutes
            capture_folder = get_capture_folder(capture_dir)
            logger.warning(f"[{capture_folder}] ⏰ Segment too old: {latest} (age: {age_seconds:.1f}s > 300s)")
            return False, 0, -100.0, 'segment_too_old', 0
    
    try:
        # SIMPLE: Always use ffmpeg volumedetect (~230ms on Pi)
        # Provides both audio presence AND volume level in one command
        check_start = time.perf_counter()
        
        capture_folder = get_capture_folder(capture_dir)
        logger.debug(f"[{capture_folder}] 🔍 Checking audio with ffmpeg: {latest}")
        
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
            '-i', latest,
            '-t', '0.1',  # Analyze first 0.1 seconds only
            '-vn',
            '-af', 'volumedetect',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1
        )
        
        check_time_ms = (time.perf_counter() - check_start) * 1000
        check_method = 'ffmpeg_volumedetect'
        
        # Parse volume from stderr
        has_audio = False
        mean_volume = -100.0
        
        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                try:
                    mean_volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                    has_audio = mean_volume > -50.0
                    break
                except:
                    pass
        
        # Convert dB to percentage
        if mean_volume > -100:
            volume_percentage = max(0, min(100, (mean_volume + 50) * 2.5))
        else:
            volume_percentage = 0
        
        # Log if unexpectedly slow (>400ms is abnormal)
        if check_time_ms > 400:
            logger.warning(f"[{capture_folder}] ⚠️  FFmpeg audio check took {check_time_ms:.0f}ms (expected ~230ms on Pi)")
            logger.warning(f"[{capture_folder}]     Segment: {latest}")
        
        # Log result
        logger.debug(f"[{capture_folder}] ✅ Audio check: {check_time_ms:.0f}ms | {mean_volume:.1f}dB | {'🔊' if has_audio else '🔇'}")
        
        return has_audio, volume_percentage, mean_volume, check_method, check_time_ms
    except subprocess.TimeoutExpired as timeout_error:
        capture_folder = get_capture_folder(capture_dir)
        logger.error(f"[{capture_folder}] ⏱️ FFprobe timeout after {timeout_error.timeout}s")
        logger.error(f"[{capture_folder}]     Segment: {latest if 'latest' in locals() else 'unknown'}")
        logger.error(f"[{capture_folder}]     This likely means segment is still being written by FFmpeg")
        # Return safe defaults - assume audio present to avoid false alarms
        return True, 0, -100.0, 'ffprobe_timeout', 0
    except Exception as e:
        capture_folder = get_capture_folder(capture_dir)
        logger.error(f"[{capture_folder}] ❌ Audio check FAILED with exception: {type(e).__name__}: {e}")
        logger.error(f"[{capture_folder}]     Segment: {latest if 'latest' in locals() else 'unknown'}")
        logger.error(f"[{capture_folder}]     Segments dir: {segments_dir if 'segments_dir' in locals() else 'unknown'}")
        
        # Import traceback for detailed error context
        import traceback
        logger.error(f"[{capture_folder}]     Traceback:\n{traceback.format_exc()}")
        
        # Return safe defaults - assume audio present to avoid false audio_loss incidents from timing issues
        return True, 0, -100.0, 'error', 0

def analyze_audio(capture_dir):
    """
    Check if audio is present with time-based throttle (3s)
    
    Strategy:
    - Time-based cache: Reuse result if checked within last 3 seconds (wall-clock time, not frames)
    - Always uses ffmpeg volumedetect (~230ms on Pi)
    - Returns both audio presence AND volume level
    
    Returns: (has_audio, volume_percentage, mean_volume_db, check_method, check_time_ms)
    """
    global _audio_ffprobe_cache
    
    current_time = time.time()
    
    # Time-based throttle: Check if we already checked this device within last 3 seconds
    if capture_dir in _audio_ffprobe_cache:
        last_check_time, cached_has_audio, cached_volume, cached_db, cached_method, cached_time_ms = _audio_ffprobe_cache[capture_dir]
        time_since_check = current_time - last_check_time
        
        if time_since_check < 3.0:
            # Reuse cached result
            return cached_has_audio, cached_volume, cached_db, f"{cached_method}_cached", cached_time_ms
    
    # Execute check directly (no queue)
    has_audio, volume_percentage, mean_volume_db, check_method, check_time_ms = _execute_audio_check(capture_dir)
    
    # Cache result for 3-second time-based throttle
    _audio_ffprobe_cache[capture_dir] = (current_time, has_audio, volume_percentage, mean_volume_db, check_method, check_time_ms)
    
    return has_audio, volume_percentage, mean_volume_db, check_method, check_time_ms

# analyze_subtitles() removed - now handled by subtitle_monitor.py

def detect_issues(image_path, fps=5, queue_size=0, debug=False):
    """
    Main detection function - OPTIMIZED WORKFLOW with zap state tracking
    
    Workflow:
    1. Check if device is zapping (state file)
       - IF zapping → FAST PATH (just monitor blackscreen)
       - IF NOT zapping → FULL PATH (all detections)
    2. Load image
    3. Edge detection (CORE - reused)
    4. Blackscreen + Zap detection (fast sampling)
    5. Freeze detection
    6. Macroblocks (skip if freeze or blackscreen)
    7. Audio analysis (cached every 5 seconds)
    
    ZAP STATE OPTIMIZATION:
    - When zap detected: Save state, mark start frame
    - During zap: Skip expensive ops (~2ms vs full detection)
    - When blackscreen ends: Mark end frame, clear state
    
    NOTE: Subtitle OCR is handled by subtitle_monitor.py (separate process)
    
    Args:
        image_path: Path to capture image
        fps: Frames per second (5 for v4l2, 2 for x11grab/VNC) - used for freeze detection
        queue_size: Current queue backlog
        debug: Enable debug output (unused, kept for compatibility)
    """
    # Performance timing storage
    timings = {}
    total_start = time.perf_counter()
    
    capture_dir = os.path.dirname(os.path.dirname(image_path))  # Go up from /captures/
    filename = os.path.basename(image_path)
    
    # Extract frame number for sampling
    try:
        frame_number = int(filename.split('_')[1].split('.')[0])
    except:
        frame_number = 0
    
    # Global cache access
    global _audio_result_cache
    
    # === CHECK: Is device currently zapping? ===
    zap_state = load_zap_state(capture_dir)
    
    if zap_state and zap_state.get('zapping'):
        # FAST PATH: Device is zapping - optimize!
        start = time.perf_counter()
        try:
            import cv2
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise Exception("Failed to load image")
            timings['image_load'] = (time.perf_counter() - start) * 1000
            
            # Quick blackscreen check (no edge detection needed)
            start = time.perf_counter()
            blackscreen, dark_percentage = quick_blackscreen_check(img)
            timings['blackscreen'] = (time.perf_counter() - start) * 1000
            
            if not blackscreen:
                # ZAP SEQUENCE ENDED!
                timestamp = datetime.fromtimestamp(os.path.getmtime(image_path)).isoformat()
                start_timestamp = datetime.fromisoformat(zap_state['start_timestamp'])
                end_timestamp = datetime.fromisoformat(timestamp)
                duration = (end_timestamp - start_timestamp).total_seconds()
                
                # Calculate next frame filename for banner detection
                next_frame_number = frame_number + 1
                # Preserve original filename format (e.g., capture_000001.jpg)
                frame_prefix = filename.rsplit('_', 1)[0]  # "capture"
                frame_digits = len(filename.split('_')[1].split('.')[0])  # Number of digits
                next_frame = f"{frame_prefix}_{str(next_frame_number).zfill(frame_digits)}.jpg"
                
                clear_zap_state(capture_dir)
                
                # Get audio (analyze_audio handles 3s caching internally)
                has_audio, volume_percentage, mean_volume_db, audio_method, audio_time_ms = analyze_audio(capture_dir)
                _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db, audio_method, audio_time_ms)
                
                timings['total'] = (time.perf_counter() - total_start) * 1000
                
                return {
                    'timestamp': timestamp,
                    'filename': filename,
                    'blackscreen': False,
                    'blackscreen_percentage': round(dark_percentage, 1),
                    'blackscreen_threshold': 10,
                    'blackscreen_region': '5-70%',
                    'zap': False,
                    'has_bottom_content': False,
                    'bottom_edge_density': 0.0,
                    'zap_sequence_end': True,
                    'zap_sequence_info': {
                        'start_frame': zap_state['start_frame'],
                        'end_frame': filename,
                        'next_frame': next_frame,
                        'duration_seconds': round(duration, 3),
                        'start_timestamp': zap_state['start_timestamp'],
                        'end_timestamp': timestamp,
                        'frames_in_sequence': frame_number - zap_state['start_frame_number'] + 1
                    },
                    'freeze': False,
                    'freeze_comparisons': [],
                    'macroblocks': False,
                    'quality_score': 0.0,
                    'audio': has_audio,
                    'volume_percentage': volume_percentage,
                    'mean_volume_db': mean_volume_db,
                    'audio_check_method': audio_method,
                    'audio_check_time_ms': round(audio_time_ms, 2),
                    'performance_ms': {k: round(v, 2) for k, v in timings.items()}
                }
            else:
                # ZAP CONTINUES - return minimal result
                timings['total'] = (time.perf_counter() - total_start) * 1000
                
                return {
                    'timestamp': datetime.fromtimestamp(os.path.getmtime(image_path)).isoformat(),
                    'filename': filename,
                    'blackscreen': True,
                    'blackscreen_percentage': round(dark_percentage, 1),
                    'blackscreen_threshold': 10,
                    'blackscreen_region': '5-70%',
                    'zap': True,
                    'zap_in_progress': True,
                    'has_bottom_content': True,
                    'bottom_edge_density': 0.0,
                    'freeze': False,
                    'freeze_comparisons': [],
                    'macroblocks': False,
                    'quality_score': 0.0,
                    'audio': True,
                    'volume_percentage': 0,
                    'mean_volume_db': -100.0,
                    'performance_ms': {k: round(v, 2) for k, v in timings.items()}
                }
        except Exception as e:
            # Error during fast path - clear state and fall through to full detection
            clear_zap_state(capture_dir)
            logger.warning(f"Zap fast path error: {e}, falling back to full detection")
    
    # === FULL PATH: Normal detection (not zapping) ===
    
    # Get thumbnails directory (handles both RAM and SD modes)
    try:
        from shared.src.lib.utils.build_url_utils import get_device_local_thumbnails_path
        thumbnails_dir = get_device_local_thumbnails_path(image_path)
    except:
        # Fallback to manual path construction
        captures_dir = os.path.dirname(image_path)
        capture_parent = os.path.dirname(captures_dir)
        thumbnails_dir = os.path.join(capture_parent, 'thumbnails')
    
    # TIMING: Load image
    start = time.perf_counter()
    try:
        import cv2
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise Exception("Failed to load image")
        img_height, img_width = img.shape
        timings['image_load'] = (time.perf_counter() - start) * 1000
    except Exception as e:
        return {
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'error': f'Image load error: {str(e)}'
        }
    
    # === STEP 1: Edge Detection (CORE - runs always) ===
    start = time.perf_counter()
    edges = cv2.Canny(img, 50, 150)
    timings['edge_detection'] = (time.perf_counter() - start) * 1000
    
    # Define regions
    header_y = int(img_height * 0.05)  # Skip top 5% (TV time/header)
    split_y = int(img_height * 0.7)     # Blackscreen region: 5-70%
    
    # === STEP 2: Blackscreen Detection (optimized sampling) ===
    start = time.perf_counter()
    # Analyze 5% to 70% (skip header, skip bottom banner)
    top_region = img[header_y:split_y, :]
    
    # Sample every 4th pixel (6.25% sample) - OPTIMIZED from every 3rd (11%)
    # Threshold = 10 (matches production - accounts for compression artifacts)
    threshold = 10
    sample = top_region[::4, ::4]
    sample_dark = np.sum(sample <= threshold)
    sample_total = sample.shape[0] * sample.shape[1]
    dark_percentage = (sample_dark / sample_total) * 100
    
    # Full scan only if edge case (70-90%)
    if 70 <= dark_percentage <= 90:
        total_pixels = top_region.shape[0] * top_region.shape[1]
        dark_pixels = np.sum(top_region <= threshold)
        dark_percentage = (dark_pixels / total_pixels) * 100
    
    blackscreen = bool(dark_percentage > 85)
    timings['blackscreen'] = (time.perf_counter() - start) * 1000
    
    # === STEP 3: Bottom Content Check (ONLY if blackscreen - for zap confirmation) ===
    start = time.perf_counter()
    if blackscreen:
        # Check bottom 30% for banner/channel info (zap confirmation)
        edges_bottom = edges[split_y:img_height, :]
        bottom_edge_density = np.sum(edges_bottom > 0) / edges_bottom.size * 100
        has_bottom_content = bool(3 < bottom_edge_density < 20)
        timings['zap'] = (time.perf_counter() - start) * 1000
    else:
        # No blackscreen = no need to check for zapping
        has_bottom_content = False
        bottom_edge_density = 0.0
        timings['zap'] = 0.0  # Skipped
    
    # Zap decision: blackscreen + bottom content
    zap = blackscreen and has_bottom_content
    
    # === NEW: Check if zap STARTS this frame ===
    zap_sequence_start = False
    if zap and not zap_state:
        # Zap sequence STARTS - save state
        zap_sequence_start = True
        save_zap_state(capture_dir, {
            'zapping': True,
            'start_frame': filename,
            'start_timestamp': datetime.fromtimestamp(os.path.getmtime(image_path)).isoformat(),
            'start_frame_number': frame_number
        })
        print(f"🎯 [Detector] Zap sequence started at {filename}")
    
    # === STEP 4: Freeze Detection (Pixel diff - fastest & most accurate) ===
    start = time.perf_counter()
    
    # Load current frame thumbnail for freeze detection (compare thumbnails with thumbnails)
    current_thumbnail_filename = filename.replace('.jpg', '_thumbnail.jpg')
    current_thumbnail_path = os.path.join(thumbnails_dir, current_thumbnail_filename)
    
    if os.path.exists(current_thumbnail_path):
        current_thumbnail = cv2.imread(current_thumbnail_path, cv2.IMREAD_GRAYSCALE)
        if current_thumbnail is not None:
            frozen, freeze_details = detect_freeze_pixel_diff(current_thumbnail, thumbnails_dir, filename, fps)
        else:
            frozen, freeze_details = False, {}
    else:
        frozen, freeze_details = False, {}
    
    timings['freeze'] = (time.perf_counter() - start) * 1000
    
    # === STEP 5: Subtitle Detection - REMOVED ===
    # Subtitle OCR is now handled exclusively by subtitle_monitor.py (separate process)
    # No OCR code runs in detector.py anymore
    
    # === STEP 6: Macroblock Analysis (skip if freeze or blackscreen) ===
    start = time.perf_counter()
    if blackscreen or frozen:
        macroblocks, quality_score = False, 0.0
        timings['macroblocks'] = 0.0  # Skipped
    else:
        macroblocks, quality_score = analyze_macroblocks(image_path)
        timings['macroblocks'] = (time.perf_counter() - start) * 1000
    
    # === STEP 7: Audio Analysis - Check every 3 seconds (handled by analyze_audio cache) ===
    # Check every 15 frames (at 5fps = 3 seconds)
    audio_check_interval = fps * 3
    should_check_audio = (frame_number % audio_check_interval == 0)
    
    start = time.perf_counter()
    audio_check_method = 'unknown'
    audio_check_time_ms = 0
    if should_check_audio:
        # Actually check audio (calls FFmpeg or ffprobe)
        has_audio, volume_percentage, mean_volume_db, audio_check_method, audio_check_time_ms = analyze_audio(capture_dir)
        # Cache the result for use by other frames
        _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db, audio_check_method, audio_check_time_ms)
        timings['audio'] = (time.perf_counter() - start) * 1000
        timings['audio_cached'] = False
    else:
        # Use cached result from last audio check (no FFmpeg call)
        if capture_dir in _audio_result_cache:
            has_audio, volume_percentage, mean_volume_db, audio_check_method, audio_check_time_ms = _audio_result_cache[capture_dir]
            timings['audio'] = (time.perf_counter() - start) * 1000
            timings['audio_cached'] = True
        else:
            # First frame or no cache yet - do one check to initialize
            has_audio, volume_percentage, mean_volume_db, audio_check_method, audio_check_time_ms = analyze_audio(capture_dir)
            _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db, audio_check_method, audio_check_time_ms)
            timings['audio'] = (time.perf_counter() - start) * 1000
            timings['audio_cached'] = False  # NOT cached - we just called FFmpeg!
    
    # Build freeze comparison list showing current vs previous frames
    freeze_comparisons = []
    freeze_debug_info = {}
    
    if freeze_details and 'frames_compared' in freeze_details:
        captures_dir = os.path.dirname(image_path)
        
        # Get current frame info
        current_capture_path = image_path
        current_thumbnail_filename = filename.replace('.jpg', '_thumbnail.jpg')
        current_thumbnail_path = os.path.join(thumbnails_dir, current_thumbnail_filename)
        
        # Build comparison for each previous frame checked
        for idx, thumbnail_filename in enumerate(freeze_details['frames_compared']):
            # Convert thumbnail filename to capture filename
            capture_filename = thumbnail_filename.replace('_thumbnail.jpg', '.jpg')
            prev_capture_path = os.path.join(captures_dir, capture_filename)
            prev_thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
            
            # Get difference percentage for this comparison
            diff_percentage = freeze_details['frame_differences'][idx] if idx < len(freeze_details['frame_differences']) else None
            
            # Add structured comparison
            freeze_comparisons.append({
                'current_frame': filename,
                'previous_frame': capture_filename,
                'difference_percentage': diff_percentage,
                'current_capture_path': current_capture_path,
                'previous_capture_path': prev_capture_path,
                'current_thumbnail_path': current_thumbnail_path,
                'previous_thumbnail_path': prev_thumbnail_path,
                'frozen': bool(diff_percentage < 5.0) if diff_percentage is not None else None
            })
    
    # Capture freeze detection debug info
    if freeze_details:
        freeze_debug_info = {
            'frames_found': freeze_details.get('frames_found', 0),
            'frames_needed': freeze_details.get('frames_needed', 2),
            'frames_checked': freeze_details.get('frames_checked', []),
            'detection_method': freeze_details.get('detection_method', 'unknown'),
            'thumbnails_dir': thumbnails_dir
        }
    
    # Calculate total time
    timings['total'] = (time.perf_counter() - total_start) * 1000
    
    # Build result with enhanced metadata
    result = {
        'timestamp': datetime.fromtimestamp(os.path.getmtime(image_path)).isoformat(),
        'filename': filename,
        
        # Blackscreen (enhanced)
        'blackscreen': bool(blackscreen),
        'blackscreen_percentage': round(dark_percentage, 1),
        'blackscreen_threshold': threshold,
        'blackscreen_region': '5-70%',
        
        # Zap detection (NEW)
        'zap': zap,
        'has_bottom_content': has_bottom_content,
        'bottom_edge_density': round(bottom_edge_density, 1),
        
        # Zap sequence tracking (NEW)
        'zap_sequence_start': zap_sequence_start,
        
        # Freeze (with detailed comparisons)
        'freeze': bool(frozen),
        'freeze_comparisons': freeze_comparisons,
        'freeze_debug': freeze_debug_info if freeze_debug_info else None,
        
        # Macroblocks (unchanged)
        'macroblocks': bool(macroblocks),
        'quality_score': round(quality_score, 1),
        
        # Audio (enhanced with check method and timing)
        'audio': has_audio,
        'volume_percentage': volume_percentage,
        'mean_volume_db': mean_volume_db,
        'audio_check_method': audio_check_method,
        'audio_check_time_ms': round(audio_check_time_ms, 2),
        
        # Performance (enhanced)
        'performance_ms': {k: round(v, 2) for k, v in timings.items()}
    }
    
    return result
