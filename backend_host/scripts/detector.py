#!/usr/bin/env python3
"""
Frame detector - analyzes frames for issues with rich metadata
Returns same format as original analyze_audio_video.py

ZAP STATE OPTIMIZATION:
- Tracks when device is zapping (blackscreen + banner detected)
- Skips expensive operations (OCR, redundant edge detection) during zap
- Marks start/end frames in JSON for zap_executor
- Saves ~99% CPU during zap sequence (2ms vs 300ms per frame)
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
# OCR Crop Method: 'smart' (dark mask-based, 60-70% smaller) or 'safe' (fixed region)
OCR_CROP_METHOD = 'safe'  # Disabled smart crop - using safe area (faster, more reliable)

# OCR Enable/Disable: Set to False to completely disable OCR processing
OCR_ENABLED = False  # Set to False to disable all OCR operations

# Add scripts directory to path for crop_subtitles import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crop_subtitles import find_subtitle_bbox

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
    analyze_macroblocks,
    analyze_subtitle_region
)

def detect_freeze_pixel_diff(current_img, thumbnails_dir, filename, fps=5):
    """
    Freeze detection using pixel difference - compares thumbnails for accuracy
    
    Compares current thumbnail with previous 3 thumbnails using cv2.absdiff.
    Uses thumbnails to avoid upscaling artifacts that cause false differences.
    
    Args:
        current_img: Current thumbnail (grayscale numpy array, 320x180)
        thumbnails_dir: Directory containing thumbnails
        filename: Current frame filename (e.g., capture_000001.jpg)
        fps: Frames per second
        
    Returns:
        (frozen: bool, details: dict)
    """
    try:
        # Extract frame number
        frame_number = int(filename.split('_')[1].split('.')[0])
    except:
        return False, {}
    
    # Need at least 3 previous frames for comparison
    if frame_number < 3:
        return False, {}
    
    # Calculate frame numbers to compare - last 3 consecutive frames
    # CRITICAL: Must check consecutive frames for fast zap detection (<200ms)
    frames_to_check = []
    for i in range(1, 4):  # Previous 3 frames (N-1, N-2, N-3)
        prev_frame_num = frame_number - i
        if prev_frame_num >= 0:
            frames_to_check.append(prev_frame_num)
    
    if len(frames_to_check) < 3:
        return False, {}
    
    # Compare with previous frames using pixel difference
    pixel_diffs = []
    frames_compared = []
    frames_checked = []  # Track which frames we tried to check
    
    # Build filename pattern (e.g., "capture" from "capture_000123.jpg")
    frame_prefix = filename.rsplit('_', 1)[0]
    frame_digits = len(filename.split('_')[1].split('.')[0])
    
    for prev_num in frames_to_check:
        # Build thumbnail filename
        prev_filename = f"{frame_prefix}_{str(prev_num).zfill(frame_digits)}_thumbnail.jpg"
        prev_path = os.path.join(thumbnails_dir, prev_filename)
        frames_checked.append(prev_filename)
        
        if not os.path.exists(prev_path):
            continue
        
        # Load previous frame thumbnail
        prev_img = cv2.imread(prev_path, cv2.IMREAD_GRAYSCALE)
        if prev_img is None:
            continue
        
        # Thumbnails should already be same size (no resize needed)
        # If sizes mismatch, skip this comparison (corrupted thumbnail)
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
        frames_compared.append(prev_filename)
        
        # EARLY EXIT: If difference > 5%, NOT frozen - stop checking more frames
        # Only continue to N-2, N-3 if N-1 shows potential freeze
        if diff_percentage > 5.0:
            break
    
    # Frozen if ALL checked frames have < 0.5% difference (VERY STRICT - reduced from 5% to avoid false positives)
    FREEZE_THRESHOLD = 0.5  # 0.5% pixel difference = frozen (was 5%, too permissive)
    frozen = len(pixel_diffs) >= 2 and all(diff < FREEZE_THRESHOLD for diff in pixel_diffs)
    
    return frozen, {
        'frame_differences': [round(d, 2) for d in pixel_diffs],
        'frames_compared': frames_compared,
        'frames_checked': frames_checked,  # Which files we tried to find
        'frames_found': len(frames_compared),
        'frames_needed': 2,
        'detection_method': 'pixel_diff',
        'threshold': FREEZE_THRESHOLD
    }

# Performance: Cache audio analysis results to avoid redundant FFmpeg calls
_audio_cache = {}  # {segment_path: (mtime, has_audio, volume, db)}
_latest_segment_cache = {}  # {capture_dir: (segment_path, mtime, last_check_time)}
_subtitle_cache = {}  # {image_path: (mtime, subtitle_result)}
_audio_result_cache = {}  # {capture_dir: (has_audio, volume, db)} - Last known audio state per device

# Zap state tracking for CPU optimization
_zap_state_cache = {}  # In-memory cache for fast access

# Language detection throttling (per device)
_language_detection_cache = {}  # {capture_dir: (last_detection_time, detected_language)}

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
    """Fast blackscreen check for zap monitoring (no edge detection needed)"""
    img_height, img_width = img.shape
    header_y = int(img_height * 0.05)
    split_y = int(img_height * 0.7)
    
    top_region = img[header_y:split_y, :]
    sample = top_region[::3, ::3]
    sample_dark = np.sum(sample <= threshold)
    sample_total = sample.shape[0] * sample.shape[1]
    dark_percentage = (sample_dark / sample_total) * 100
    
    return bool(dark_percentage > 85), dark_percentage

def analyze_audio(capture_dir):
    """Check if audio is present in latest segment - OPTIMIZED with caching"""
    global _audio_cache, _latest_segment_cache
    
    current_time = time.time()
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
        # OPTIMIZED: Fast sample method - analyze only first 0.1 seconds (ultra-fast!)
        # FFmpeg command: analyze only first 0.1s of audio, skip video decoding
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
            '-i', latest,
            '-t', '0.1',  # Only first 0.1 seconds (ultra-fast!)
            '-vn',  # Skip video decoding
            '-af', 'volumedetect',  # Audio volume detection filter
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1  # 1s timeout (should complete in ~50ms)
        )
        
        # Parse FFmpeg output for mean_volume
        # Example: [Parsed_volumedetect_0 @ 0x...] mean_volume: -25.3 dB
        output = result.stderr
        
        has_audio = False
        mean_volume = -100.0
        
        for line in output.split('\n'):
            if 'mean_volume:' in line:
                try:
                    mean_volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                    has_audio = mean_volume > -50.0  # Threshold: -50dB indicates audio
                    break
                except:
                    pass
        
        # Convert dB to percentage (approximate)
        # -50dB = 0%, -10dB = 50%, 0dB = 100%
        if mean_volume > -100:
            volume_percentage = max(0, min(100, (mean_volume + 50) * 2.5))
        else:
            volume_percentage = 0
        
        # Cache the result
        _audio_cache[latest] = (latest_mtime, has_audio, volume_percentage, mean_volume)
        
        # Clean old cache entries to prevent memory growth
        if len(_audio_cache) > 50:
            _audio_cache = dict(list(_audio_cache.items())[-20:])
        
        return has_audio, volume_percentage, mean_volume
    except Exception as e:
        # Fallback if FFmpeg fails
        logger.warning(f"Fast audio detection failed: {e}")
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

def detect_issues(image_path, fps=5, queue_size=0, debug=False):
    """
    Main detection function - OPTIMIZED WORKFLOW with zap state tracking
    
    Workflow:
    1. Check if device is zapping (state file)
       - IF zapping → FAST PATH (skip OCR, just monitor blackscreen)
       - IF NOT zapping → FULL PATH (all detections)
    2. Load image
    3. Edge detection (CORE - reused)
    4. Blackscreen + Zap detection (fast sampling)
    5. Subtitle detection (conditional - skip if zap/freeze/queue overload)
    6. Freeze detection
    7. Macroblocks (skip if freeze or blackscreen)
    8. Audio analysis (cached every 5 seconds)
    
    ZAP STATE OPTIMIZATION:
    - When zap detected: Save state, mark start frame
    - During zap: Skip expensive ops (~2ms vs 300ms)
    - When blackscreen ends: Mark end frame, clear state
    
    QUEUE OVERLOAD PROTECTION:
    - When queue > 50 frames: Disable OCR to drain queue faster
    - Auto-re-enables when queue clears
    
    Args:
        image_path: Path to capture image
        fps: Frames per second (5 for v4l2, 2 for x11grab/VNC) - used for freeze detection
        queue_size: Current queue backlog (0 = no backlog, >50 = disable OCR)
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
    global _audio_result_cache, _language_detection_cache
    
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
                
                # Get audio (cached)
                audio_check_interval = fps * 5
                should_check_audio = (frame_number % audio_check_interval == 0)
                
                if should_check_audio:
                    has_audio, volume_percentage, mean_volume_db = analyze_audio(capture_dir)
                    _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db)
                else:
                    if capture_dir in _audio_result_cache:
                        has_audio, volume_percentage, mean_volume_db = _audio_result_cache[capture_dir]
                    else:
                        has_audio, volume_percentage, mean_volume_db = analyze_audio(capture_dir)
                        _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db)
                
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
                    'subtitle_analysis': {
                        'has_subtitles': False,
                        'extracted_text': '',
                        'detected_language': None,
                        'confidence': 0.0,
                        'box': None,
                        'skipped': True,
                        'skip_reason': 'zap_just_ended'
                    },
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
                    'subtitle_analysis': {
                        'has_subtitles': False,
                        'extracted_text': '',
                        'detected_language': None,
                        'confidence': 0.0,
                        'box': None,
                        'skipped': True,
                        'skip_reason': 'zap_in_progress'
                    },
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
    
    # === STEP 2: Blackscreen Detection (fast sampling) ===
    start = time.perf_counter()
    # Analyze 5% to 70% (skip header, skip bottom banner)
    top_region = img[header_y:split_y, :]
    
    # Sample every 3rd pixel (11% sample)
    # Threshold = 10 (matches production - accounts for compression artifacts)
    threshold = 10
    sample = top_region[::3, ::3]
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
    
    # === STEP 5: Subtitle Detection (SKIP if zap/freeze/queue overload/audio frame) ===
    subtitle_result = None
    start = time.perf_counter()
    
    sample_interval = fps if fps >= 2 else 2
    should_check_subtitles = (frame_number % sample_interval == 0)
    
    # Check if this is an audio analysis frame (to avoid doing both OCR and audio)
    # Dynamic interval: 5s if audio present, 10s if no audio (silence less critical)
    if capture_dir in _audio_result_cache:
        last_has_audio, _, _ = _audio_result_cache[capture_dir]
        audio_check_interval = fps * 5 if last_has_audio else fps * 10
    else:
        # First check - use 5s interval
        audio_check_interval = fps * 5
    
    is_audio_frame = (frame_number % audio_check_interval == 0)
    
    # Check if we have audio (from cache or will check this frame)
    has_audio_cached = False
    if capture_dir in _audio_result_cache:
        has_audio_cached, _, _ = _audio_result_cache[capture_dir]
    
    if not OCR_ENABLED:
        # OCR globally disabled - skip all OCR operations
        timings['subtitle_area_check'] = 0.0
        timings['subtitle_ocr'] = 0.0
        subtitle_result = {
            'has_subtitles': False,
            'extracted_text': '',
            'detected_language': None,
            'confidence': 0.0,
            'box': None,
            'ocr_method': None,
            'downscaled_to_height': None,
            'psm_mode': None,
            'subtitle_edge_density': 0.0,
            'skipped': True,
            'skip_reason': 'ocr_disabled'
        }
    elif is_audio_frame:
        # Audio analysis frame - skip OCR to spread expensive operations
        timings['subtitle_area_check'] = 0.0
        timings['subtitle_ocr'] = 0.0
        subtitle_result = {
            'has_subtitles': False,
            'extracted_text': '',
            'detected_language': None,
            'confidence': 0.0,
            'box': None,
            'ocr_method': None,
            'downscaled_to_height': None,
            'psm_mode': None,
            'subtitle_edge_density': 0.0,
            'skipped': True,
            'skip_reason': 'audio_frame'
        }
    elif not has_audio_cached and capture_dir in _audio_result_cache:
        # No audio detected (from cache) - skip OCR since no content playing
        timings['subtitle_area_check'] = 0.0
        timings['subtitle_ocr'] = 0.0
        subtitle_result = {
            'has_subtitles': False,
            'extracted_text': '',
            'detected_language': None,
            'confidence': 0.0,
            'box': None,
            'ocr_method': None,
            'downscaled_to_height': None,
            'psm_mode': None,
            'subtitle_edge_density': 0.0,
            'skipped': True,
            'skip_reason': 'no_audio'
        }
    elif queue_size > 50:
        # Queue overload - disable OCR to drain queue faster
        timings['subtitle_area_check'] = 0.0
        timings['subtitle_ocr'] = 0.0
        subtitle_result = {
            'has_subtitles': False,
            'extracted_text': '',
            'detected_language': None,
            'confidence': 0.0,
            'box': None,
            'ocr_method': None,
            'downscaled_to_height': None,
            'psm_mode': None,
            'subtitle_edge_density': 0.0,
            'skipped': True,
            'skip_reason': f'queue_overload_{queue_size}'
        }
    elif zap:
        # Zapping = blackscreen with bottom content (not subtitles) - skip OCR
        timings['subtitle_area_check'] = 0.0
        timings['subtitle_ocr'] = 0.0
        subtitle_result = {
            'has_subtitles': False,
            'extracted_text': '',
            'detected_language': None,
            'confidence': 0.0,
            'box': None,
            'ocr_method': None,
            'downscaled_to_height': None,
            'psm_mode': None,
            'subtitle_edge_density': 0.0,
            'skipped': True,
            'skip_reason': 'zap'
        }
    elif frozen or blackscreen:
        # Skip OCR during freeze or blackscreen - saves CPU
        timings['subtitle_area_check'] = 0.0
        timings['subtitle_ocr'] = 0.0
        subtitle_result = {
            'has_subtitles': False,
            'extracted_text': '',
            'detected_language': None,
            'confidence': 0.0,
            'box': None,
            'ocr_method': None,
            'downscaled_to_height': None,
            'psm_mode': None,
            'subtitle_edge_density': 0.0,
            'skipped': True,
            'skip_reason': 'freeze' if frozen else 'blackscreen'
        }
    elif should_check_subtitles:
        # Check subtitle area (bottom 15%)
        subtitle_y = int(img_height * 0.85)
        edges_subtitle = edges[subtitle_y:img_height, :]
        
        subtitle_edge_density = np.sum(edges_subtitle > 0) / edges_subtitle.size * 100
        # Threshold: 1.5-8% (catch subtitles with black backgrounds, avoid UI/menus)
        has_subtitle_area = bool(1.5 < subtitle_edge_density < 8)
        timings['subtitle_area_check'] = (time.perf_counter() - start) * 1000
        
        # OCR only if subtitle edges detected
        if has_subtitle_area:
            ocr_start = time.perf_counter()
            ocr_timings = {}  # Detailed timing for each OCR step
            
            try:
                # STEP 1: Calculate crop boundaries (smart or safe area)
                step_start = time.perf_counter()
                
                if OCR_CROP_METHOD == 'smart':
                    # SMART CROP: Dark mask-based (proven implementation from crop_subtitles.py)
                    try:
                        bbox = find_subtitle_bbox(img)
                        x, y, w, h = bbox.x, bbox.y, bbox.w, bbox.h
                        crop_method = "smart_dark_mask"
                    except (ValueError, Exception) as e:
                        # Fall back to safe area if smart crop fails
                        x = int(img_width * 0.10)
                        y = int(img_height * 0.60)
                        w = int(img_width * 0.80)
                        h = int(img_height * 0.35)
                        crop_method = f"smart_fallback_safe ({str(e)[:30]})"
                        # LOG WARNING: Smart crop failed
                        logger.warning(f"Smart crop failed: {str(e)[:50]} - using safe area {w}x{h}")
                else:
                    # SAFE AREA: Fixed region (60-95% height, 10-90% width)
                    x = int(img_width * 0.10)   # 10% from left
                    y = int(img_height * 0.60)  # Start at 60% height (bottom 40%)
                    w = int(img_width * 0.80)   # 80% width (centered)
                    h = int(img_height * 0.35)  # 35% height (60-95%)
                    crop_method = "safe_area_fixed"
                
                ocr_timings['crop_calc'] = (time.perf_counter() - step_start) * 1000
                
                # STEP 2: Extract crop region
                step_start = time.perf_counter()
                subtitle_box_region = img[y:y+h, x:x+w]
                ocr_timings['crop_extract'] = (time.perf_counter() - step_start) * 1000
                
                # STEP 3: Save debug crop if enabled
                step_start = time.perf_counter()
                if debug:
                    # Fixed filename per device to avoid disk space issues
                    device_name = os.path.basename(capture_dir)
                    debug_filename = f"subtitle_crop_debug_{device_name}.jpg"
                    debug_path = os.path.join('/tmp', debug_filename)
                    cv2.imwrite(debug_path, subtitle_box_region)
                    print(f"   🔍 Saved subtitle crop: {debug_path}")
                    ocr_timings['debug_save'] = (time.perf_counter() - step_start) * 1000
                else:
                    ocr_timings['debug_save'] = 0.0
                
                # STEP 4: Run Tesseract OCR
                step_start = time.perf_counter()
                subtitle_text_raw = ""
                ocr_method_used = "pytesseract"
                try:
                    import pytesseract
                    ocr_config = '--psm 6 --oem 3 -l eng+fra+ita+deu+spa'
                    subtitle_text_raw = pytesseract.image_to_string(
                        subtitle_box_region, 
                        config=ocr_config
                    ).strip()
                    subtitle_text = subtitle_text_raw
                    ocr_timings['tesseract_ocr'] = (time.perf_counter() - step_start) * 1000
                except Exception as ocr_error:
                    ocr_timings['tesseract_ocr'] = (time.perf_counter() - step_start) * 1000
                    # Fallback to standard method
                    ocr_method_used = "fallback"
                    step_start = time.perf_counter()
                    try:
                        from shared.src.lib.utils.image_utils import extract_text_from_region
                        subtitle_text_raw = extract_text_from_region(subtitle_box_region)
                        subtitle_text = subtitle_text_raw
                        ocr_timings['fallback_ocr'] = (time.perf_counter() - step_start) * 1000
                    except Exception as fallback_error:
                        subtitle_text_raw = ""
                        subtitle_text = ""
                        ocr_method_used = f"error: {str(fallback_error)}"
                        ocr_timings['fallback_ocr'] = (time.perf_counter() - step_start) * 1000
                
                # STEP 5: Clean OCR noise (regex filter)
                step_start = time.perf_counter()
                if subtitle_text:
                    import re
                    lines = subtitle_text.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        words = line.split()
                        real_words = [w for w in words if len(re.sub(r'[^a-zA-Z]', '', w)) >= 3]
                        if real_words:
                            cleaned = re.sub(r'[\s,\.;:\-\|~\*]+$', '', line)
                            cleaned = re.sub(r'^[\s,\.;:\-\|~\*]+', '', cleaned)
                            cleaned_lines.append(cleaned)
                    subtitle_text = '\n'.join(cleaned_lines).strip()
                ocr_timings['noise_cleaning'] = (time.perf_counter() - step_start) * 1000
                
                # STEP 6: Detect language if text found
                step_start = time.perf_counter()
                detected_language = None
                confidence = 0.0
                
                # CRITICAL: If OCR was already slow (>200ms), SKIP language detection to save time
                tesseract_time = ocr_timings.get('tesseract_ocr', 0)
                if tesseract_time > 200:
                    # OCR took >200ms, skip language detection to avoid further slowdown
                    detected_language = 'skipped_slow_ocr'
                    confidence = 0.6
                else:
                    # Quick garbage filter: if text is mostly nonsense, skip language detection
                    if subtitle_text and len(subtitle_text.strip()) > 0:
                        # Check if text has reasonable characters (letters, spaces, punctuation)
                        clean_text = subtitle_text.strip()
                        alpha_count = sum(c.isalpha() or c.isspace() for c in clean_text)
                        if len(clean_text) > 0 and alpha_count / len(clean_text) < 0.5:
                            # More than 50% garbage characters - likely noise
                            subtitle_text = None
                    
                    # OPTIMIZATION: Only detect language if we have 3+ real words AND it's been 30+ seconds
                    if subtitle_text and len(subtitle_text.strip()) > 0:
                        # Count real words (2+ characters, alpha only)
                        words = [w for w in subtitle_text.split() if len(w) >= 2 and any(c.isalpha() for c in w)]
                        
                        # Check throttling: only detect language every 30 seconds per device
                        current_time = time.time()
                        
                        # Get cached data (timestamp and language)
                        cached_data = _language_detection_cache.get(capture_dir)
                        if cached_data:
                            last_detection_time, cached_language = cached_data
                            time_since_last = current_time - last_detection_time
                        else:
                            last_detection_time = 0
                            cached_language = None
                            time_since_last = float('inf')
                        
                        # Only detect if: 3+ words AND 30+ seconds since last detection
                        if len(words) >= 3 and time_since_last >= 30.0:
                            try:
                                from shared.src.lib.utils.image_utils import detect_language
                                detected_language = detect_language(subtitle_text)
                                
                                # Update throttle cache with both timestamp and language
                                _language_detection_cache[capture_dir] = (current_time, detected_language)
                                
                                # If language detected successfully, trust the OCR
                                if detected_language and detected_language != 'unknown':
                                    confidence = 1.0
                                else:
                                    # Language unknown but text extracted - medium confidence
                                    confidence = 0.75
                            except:
                                detected_language = 'unknown'
                                confidence = 0.75
                        else:
                            # Throttled - use cached language if available
                            if cached_language:
                                detected_language = cached_language
                                confidence = 0.8  # Slightly lower confidence for cached
                            else:
                                # No cached language yet (< 3 words or first detection)
                                detected_language = 'skipped'
                                confidence = 0.5
                
                ocr_timings['language_detection'] = (time.perf_counter() - step_start) * 1000
                
                ocr_time_ms = (time.perf_counter() - ocr_start) * 1000
                
                # LOG WARNING: OCR is slow (>1 second)
                if ocr_time_ms > 1000:
                    logger.warning(f"⚠️  OCR took {ocr_time_ms:.0f}ms (crop={w}x{h}, method={crop_method}) - TEXT: '{subtitle_text[:50] if subtitle_text else 'none'}'")
                
                subtitle_result = {
                    'has_subtitles': bool(subtitle_text and len(subtitle_text.strip()) > 0),
                    'extracted_text': subtitle_text if subtitle_text else '',
                    'detected_language': detected_language,
                    'confidence': confidence,
                    'box': {'x': x, 'y': y, 'width': w, 'height': h},
                    'ocr_method': crop_method,
                    'downscaled_to_height': None,
                    'psm_mode': 6,
                    'subtitle_edge_density': round(subtitle_edge_density, 1),
                    'skipped': False,
                    'skip_reason': None,
                    # DEBUG: Detailed OCR info with step-by-step timings
                    'debug': {
                        'total_ocr_time_ms': round(ocr_time_ms, 2),
                        'step_timings': {
                            '1_crop_calc_ms': round(ocr_timings.get('crop_calc', 0), 2),
                            '2_crop_extract_ms': round(ocr_timings.get('crop_extract', 0), 2),
                            '3_debug_save_ms': round(ocr_timings.get('debug_save', 0), 2),
                            '4_tesseract_ocr_ms': round(ocr_timings.get('tesseract_ocr', 0), 2),
                            '5_noise_cleaning_ms': round(ocr_timings.get('noise_cleaning', 0), 2),
                            '6_language_detection_ms': round(ocr_timings.get('language_detection', 0), 2)
                        },
                        'context_timings': {
                            'image_load_ms': round(timings.get('image_load', 0), 2),
                            'edge_detection_ms': round(timings.get('edge_detection', 0), 2),
                            'blackscreen_ms': round(timings.get('blackscreen', 0), 2),
                            'subtitle_area_check_ms': round(timings.get('subtitle_area_check', 0), 2)
                        },
                        'crop_method': crop_method,
                        'crop_size': f"{w}x{h}",
                        'crop_position': f"({x},{y})",
                        'raw_text': subtitle_text_raw,
                        'raw_text_length': len(subtitle_text_raw),
                        'cleaned_text_length': len(subtitle_text) if subtitle_text else 0,
                        'chars_removed': len(subtitle_text_raw) - (len(subtitle_text) if subtitle_text else 0),
                        'ocr_engine': ocr_method_used,
                        'tesseract_config': '--psm 6 --oem 3 -l eng+fra+ita+deu+spa',
                        'edge_density_percent': round(subtitle_edge_density, 2)
                    }
                }
                
                timings['subtitle_ocr'] = ocr_time_ms
            except Exception as e:
                subtitle_result = {
                    'has_subtitles': False,
                    'extracted_text': '',
                    'detected_language': None,
                    'confidence': 0.0,
                    'box': None,
                    'error': str(e),
                    'subtitle_edge_density': round(subtitle_edge_density, 1),
                    'skipped': False,
                    'skip_reason': f'error: {str(e)}'
                }
                timings['subtitle_ocr'] = (time.perf_counter() - ocr_start) * 1000
        else:
            # No subtitle edges detected
            subtitle_result = {
                'has_subtitles': False,
                'extracted_text': '',
                'detected_language': None,
                'confidence': 0.0,
                'box': None,
                'ocr_method': None,
                'downscaled_to_height': None,
                'psm_mode': None,
                'subtitle_edge_density': round(subtitle_edge_density, 1),
                'skipped': True,
                'skip_reason': 'no_edges'
            }
            timings['subtitle_ocr'] = 0.0
    else:
        # Not sampled this frame (checked every 1 second)
        timings['subtitle_area_check'] = 0.0
        timings['subtitle_ocr'] = 0.0
        subtitle_result = {
            'has_subtitles': False,
            'extracted_text': '',
            'detected_language': None,
            'confidence': 0.0,
            'box': None,
            'ocr_method': None,
            'downscaled_to_height': None,
            'psm_mode': None,
            'subtitle_edge_density': 0.0,
            'skipped': True,
            'skip_reason': f'not_sampled_frame (checks every {sample_interval} frames = 1s)'
        }
    
    # === STEP 6: Macroblock Analysis (skip if freeze or blackscreen) ===
    start = time.perf_counter()
    if blackscreen or frozen:
        macroblocks, quality_score = False, 0.0
        timings['macroblocks'] = 0.0  # Skipped
    else:
        macroblocks, quality_score = analyze_macroblocks(image_path)
        timings['macroblocks'] = (time.perf_counter() - start) * 1000
    
    # === STEP 7: Audio Analysis - Sample every 5 seconds ===
    # audio_check_interval already defined above (line 663)
    should_check_audio = is_audio_frame  # Reuse the check from subtitle section
    
    start = time.perf_counter()
    if should_check_audio:
        # Actually check audio (calls FFmpeg)
        has_audio, volume_percentage, mean_volume_db = analyze_audio(capture_dir)
        # Cache the result for use by other frames
        _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db)
        timings['audio'] = (time.perf_counter() - start) * 1000
        timings['audio_cached'] = False
    else:
        # Use cached result from last audio check (no FFmpeg call)
        if capture_dir in _audio_result_cache:
            has_audio, volume_percentage, mean_volume_db = _audio_result_cache[capture_dir]
            timings['audio'] = (time.perf_counter() - start) * 1000
            timings['audio_cached'] = True
        else:
            # First frame or no cache yet - do one check to initialize
            has_audio, volume_percentage, mean_volume_db = analyze_audio(capture_dir)
            _audio_result_cache[capture_dir] = (has_audio, volume_percentage, mean_volume_db)
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
        
        # Audio (unchanged)
        'audio': has_audio,
        'volume_percentage': volume_percentage,
        'mean_volume_db': mean_volume_db,
        
        # Performance (enhanced)
        'performance_ms': {k: round(v, 2) for k, v in timings.items()}
    }
    
    # Add subtitle analysis if available
    if subtitle_result:
        result['subtitle_analysis'] = subtitle_result
    
    return result
