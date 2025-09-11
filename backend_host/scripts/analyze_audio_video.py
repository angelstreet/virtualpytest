#!/usr/bin/env python3
"""
Unified Capture Analysis Script for HDMI Capture Monitoring
Analyzes both video frames and audio segments in a single pass
Usage: analyze_capture.py /path/to/capture_0001.jpg [host_name]
"""

import os
import sys
import json
import cv2
import numpy as np
import re
import subprocess
import glob
import time
import hashlib
import pickle
import fcntl
import logging
from datetime import datetime

# Setup logging to /tmp/analysis.log
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler('/tmp/analysis.log')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# Console handler (for backward compatibility)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# Optional import for text extraction
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Simplified sampling patterns for performance optimization
SAMPLING_PATTERNS = {
    "freeze_sample_rate": 10,     # Every 10th pixel for freeze detection
    "blackscreen_samples": 1000,  # 1000 random pixels for blackscreen
    "error_grid_rate": 15,        # Every 15th pixel in grid for errors
    "subtitle_edge_threshold": 200  # Edge detection threshold
}

def analyze_macroblocks(image_path, device_id="unknown"):
    """
    Conservative macroblock/image quality detection using strict thresholds
    Detects: green/pink pixels, severe blur, compression artifacts
    Only flags true macroblocks to avoid false positives
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"[{device_id}] Could not load image for macroblock analysis: {image_path}")
            return False, 0.0
        
        # Convert to different color spaces for analysis
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        img_height, img_width = img.shape[:2]
        
        # 1. Detect abnormal color pixels (green/pink artifacts)
        # Sample every 10th pixel for performance
        sample_rate = SAMPLING_PATTERNS["freeze_sample_rate"]  # Reuse existing pattern
        hsv_sampled = hsv[::sample_rate, ::sample_rate]
        
        # Green artifacts: High saturation in green range
        green_mask = cv2.inRange(hsv_sampled, (40, 100, 50), (80, 255, 255))
        green_pixels = np.sum(green_mask > 0)
        
        # Pink/Magenta artifacts: High saturation in magenta range  
        pink_mask = cv2.inRange(hsv_sampled, (140, 100, 50), (170, 255, 255))
        pink_pixels = np.sum(pink_mask > 0)
        
        total_sampled = hsv_sampled.shape[0] * hsv_sampled.shape[1]
        artifact_percentage = ((green_pixels + pink_pixels) / total_sampled) * 100
        
        # 2. Conservative blur detection using Laplacian variance
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_sampled = gray[::sample_rate, ::sample_rate]
        laplacian_var = cv2.Laplacian(gray_sampled, cv2.CV_64F).var()
        
        # CONSERVATIVE THRESHOLDS - Only flag obvious macroblocks
        has_severe_artifacts = artifact_percentage > 8.0  # Raised from 2% to 8% - must be obvious
        is_severely_blurry = laplacian_var < 30  # Lowered from 100 to 30 - must be very blurry
        
        # Additional validation: both conditions should be somewhat present for true macroblocks
        # If only one condition is met, require it to be very severe
        if has_severe_artifacts and is_severely_blurry:
            # Both conditions met - likely macroblocks
            macroblocks_detected = True
            confidence = "high"
        elif has_severe_artifacts and artifact_percentage > 15.0:
            # Very high artifact percentage alone
            macroblocks_detected = True
            confidence = "medium_artifacts"
        elif is_severely_blurry and laplacian_var < 15:
            # Extremely blurry alone
            macroblocks_detected = True
            confidence = "medium_blur"
        else:
            # Neither condition severe enough
            macroblocks_detected = False
            confidence = "none"
        
        quality_score = max(artifact_percentage, (200 - laplacian_var) / 2) if macroblocks_detected else 0.0
        
        # Detailed INFO logging (same format as blackscreen detection)
        logger.info(f"[{device_id}] Macroblock check: {img_width}x{img_height} | artifacts={artifact_percentage:.1f}% (threshold: 8.0%), blur_var={laplacian_var:.1f} (threshold: 30), detected={macroblocks_detected} ({confidence})")
        
        return macroblocks_detected, quality_score
        
    except Exception as e:
        logger.error(f"[{device_id}] Macroblock analysis error: {e}")
        return False, 0.0

def get_capture_directory_from_image(image_path):
    """Get capture directory from image path"""
    # Image is in /var/www/html/stream/capture1/captures/capture_*.jpg
    # Audio segments are in /var/www/html/stream/capture1/segment_*.ts
    captures_dir = os.path.dirname(image_path)  # .../captures/
    return os.path.dirname(captures_dir)  # .../capture1/

def find_latest_audio_segment(capture_dir, device_id="unknown"):
    """Find the most recent HLS segment file"""
    try:
        pattern = os.path.join(capture_dir, "segment_*.ts")
        segments = glob.glob(pattern)
        if not segments:
            return None
        
        # Sort by modification time, get newest
        latest = max(segments, key=os.path.getmtime)
        
        # Check if recent (within last 5 minutes)
        latest_mtime = os.path.getmtime(latest)
        current_time = time.time()
        age_seconds = current_time - latest_mtime
        max_age_seconds = 300  # 5 minutes
        
        if age_seconds > max_age_seconds:
            logger.debug(f"[{device_id}] Audio segment too old: {age_seconds:.1f}s > {max_age_seconds}s")
            return None
        return latest
    except Exception:
        return None

def analyze_audio_volume(segment_path, device_id="unknown"):
    """Analyze audio volume using FFmpeg volumedetect"""
    try:
        cmd = ['/usr/bin/ffmpeg', '-i', segment_path, '-af', 'volumedetect', '-vn', '-f', 'null', '/dev/null']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Parse mean_volume from stderr
        mean_volume = -100.0
        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                match = re.search(r'mean_volume:\s*([-\d.]+)\s*dB', line)
                if match:
                    mean_volume = float(match.group(1))
                    break
        
        # Convert dB to 0-100% scale: -60dB = 0%, 0dB = 100%
        volume_percentage = max(0, min(100, (mean_volume + 60) * 100 / 60))
        has_audio = volume_percentage > 5  # 5% threshold
        
        return has_audio, int(volume_percentage), mean_volume
    except Exception as e:
        logger.warning(f"[{device_id}] Audio analysis failed: {e}")
        return False, 0, -100.0

def get_cache_file_path(image_path):
    """Generate cache file path in the same directory as the image"""
    image_dir = os.path.dirname(image_path)
    return os.path.join(image_dir, 'frame_cache.pkl')

def load_frame_cache(cache_file_path):
    """Load frame cache from file with file locking"""
    if not os.path.exists(cache_file_path):
        return {}
    try:
        with open(cache_file_path, 'rb') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            cache = pickle.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return cache
    except (EOFError, pickle.PickleError, OSError):
        return {}

def save_frame_cache(cache_file_path, cache_data):
    """Save frame cache to file with file locking"""
    try:
        os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)
        with open(cache_file_path, 'wb') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            pickle.dump(cache_data, f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (OSError, pickle.PickleError):
        pass

def get_cached_frame_data(cache, filename):
    """Get frame data from cache if available"""
    for key in ['frame1', 'frame2']:
        if key in cache and cache[key]['filename'] == filename:
            return cache[key]['data']
    return None

def analyze_blackscreen(image_path, threshold=10, device_id="unknown"):
    """Detect if image is mostly black (blackscreen)"""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False
        
        # Count pixels <= threshold
        very_dark_pixels = np.sum(img <= threshold)
        total_pixels = img.shape[0] * img.shape[1]
        dark_percentage = (very_dark_pixels / total_pixels) * 100
        
        # If >95% of pixels are very dark, it's blackscreen
        is_blackscreen = dark_percentage > 95
        logger.info(f"[{device_id}] Blackscreen check: {dark_percentage:.1f}% pixels <= {threshold} ({'BLACKSCREEN' if is_blackscreen else 'Normal'})")
        return is_blackscreen
    except Exception:
        return False

def analyze_freeze(image_path, previous_frames_cache=None, device_id="unknown"):
    """Detect if image is frozen (identical to previous frames)"""
    try:
        cache_file_path = get_cache_file_path(image_path)
        cache = load_frame_cache(cache_file_path)
        
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False, None
        
        # Extract sequence number from filename
        current_match = re.search(r'capture_(\d+)(?:_thumbnail)?\.jpg', image_path)
        if not current_match:
            return False, None
        
        current_sequence = current_match.group(1)
        current_filename = os.path.basename(image_path)
        directory = os.path.dirname(image_path)
        is_thumbnail = '_thumbnail' in current_filename
        
        # Get all files of same type and sort (with filename validation)
        if is_thumbnail:
            file_pattern = lambda f: f.startswith('capture_') and f.endswith('_thumbnail.jpg')
        else:
            file_pattern = lambda f: f.startswith('capture_') and f.endswith('.jpg') and '_thumbnail' not in f
        
        # Filter files with validation to prevent FileNotFoundError on malformed filenames
        valid_files = []
        for f in os.listdir(directory):
            if file_pattern(f):
                # Extract sequence number and validate format (sequential naming)
                if is_thumbnail:
                    sequence_match = re.search(r'capture_(\d+)_thumbnail\.jpg', f)
                else:
                    sequence_match = re.search(r'capture_(\d+)\.jpg', f)
                
                # Sequential format validation - must match pattern
                if sequence_match:
                    valid_files.append(f)
        
        all_files = sorted(valid_files)
        
        if current_filename not in all_files:
            return False, None
        
        current_index = all_files.index(current_filename)
        
        # Need at least 2 previous files (total of 3 frames)
        if current_index < 2:
            # Save current frame to cache
            new_cache = {
                'frame2': {'filename': current_filename, 'data': img, 'sequence': current_sequence},
                'last_updated': current_sequence
            }
            save_frame_cache(cache_file_path, new_cache)
            return False, None
        
        # Get 2 previous frames
        prev1_filename = all_files[current_index - 1]
        prev2_filename = all_files[current_index - 2]
        
        # Load from cache or disk
        prev1_img = get_cached_frame_data(cache, prev1_filename)
        if prev1_img is None:
            prev1_path = os.path.join(directory, prev1_filename)
            prev1_img = cv2.imread(prev1_path, cv2.IMREAD_GRAYSCALE)
        
        prev2_img = get_cached_frame_data(cache, prev2_filename)
        if prev2_img is None:
            prev2_path = os.path.join(directory, prev2_filename)
            prev2_img = cv2.imread(prev2_path, cv2.IMREAD_GRAYSCALE)
        
        if prev1_img is None or prev2_img is None:
            return False, None
        
        # Check dimensions match
        if img.shape != prev1_img.shape or img.shape != prev2_img.shape:
            return False, None
        
        # Optimized sampling for performance
        sample_rate = SAMPLING_PATTERNS["freeze_sample_rate"]
        img_sampled = img[::sample_rate, ::sample_rate]
        prev1_sampled = prev1_img[::sample_rate, ::sample_rate]
        prev2_sampled = prev2_img[::sample_rate, ::sample_rate]
        
        # Calculate all three comparisons
        diff_1vs2 = cv2.absdiff(prev2_sampled, prev1_sampled)
        diff_1vs3 = cv2.absdiff(prev2_sampled, img_sampled)
        diff_2vs3 = cv2.absdiff(prev1_sampled, img_sampled)
        
        mean_diff_1vs2 = np.mean(diff_1vs2)
        mean_diff_1vs3 = np.mean(diff_1vs3)
        mean_diff_2vs3 = np.mean(diff_2vs3)
        
        # Frozen if ALL comparisons show small differences
        freeze_threshold = 0.5
        is_frozen = (mean_diff_1vs2 < freeze_threshold and 
                    mean_diff_1vs3 < freeze_threshold and 
                    mean_diff_2vs3 < freeze_threshold)
        
        freeze_details = {
            'frames_compared': [prev2_filename, prev1_filename, current_filename],
            'frame_differences': [round(mean_diff_1vs2, 2), round(mean_diff_1vs3, 2), round(mean_diff_2vs3, 2)],
            'threshold': freeze_threshold,
            'comparison_method': 'all_pairs_comparison_thumbnail' if is_thumbnail else 'all_pairs_comparison_original',
            'freeze_detected_against': 'all' if is_frozen else None
        }
        
        # Update cache
        prev1_match = re.search(r'capture_(\d+)(?:_thumbnail)?\.jpg', prev1_filename)
        prev1_sequence = prev1_match.group(1) if prev1_match else 'unknown'
        
        new_cache = {
            'frame1': {'filename': prev1_filename, 'data': prev1_img, 'sequence': prev1_sequence},
            'frame2': {'filename': current_filename, 'data': img, 'sequence': current_sequence},
            'last_updated': current_sequence
        }
        
        logger.info(f"[{device_id}] Freeze check: {'FREEZE' if is_frozen else 'Normal'} (diffs: {mean_diff_1vs2:.2f}, {mean_diff_1vs3:.2f}, {mean_diff_2vs3:.2f})")
        logger.debug(f"[{device_id}] Freeze details: {freeze_details}")
        
        # Save cache after logging results to avoid exception affecting return value
        try:
            save_frame_cache(cache_file_path, new_cache)
        except Exception as cache_error:
            logger.warning(f"[{device_id}] Failed to save frame cache: {cache_error}")
        
        return is_frozen, freeze_details
        
    except Exception as e:
        logger.error(f"[{device_id}] Freeze analysis failed: {e}")
        return False, None



def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_capture.py /path/to/capture_file.jpg [host_name] [device_id] [incident_state_json]", file=sys.stderr)
        sys.exit(1)
    
    image_path = sys.argv[1]
    host_name = sys.argv[2] if len(sys.argv) > 2 else None
    device_id = sys.argv[3] if len(sys.argv) > 3 else None
    incident_state_json = sys.argv[4] if len(sys.argv) > 4 else None
    
    if not os.path.exists(image_path) or not image_path.endswith('.jpg'):
        print(f"Error: Invalid image file: {image_path}", file=sys.stderr)
        sys.exit(1)
    
    # Sequential format: capture_0001.jpg, capture_0002.jpg, etc. (no numbered suffixes)
    
    print(f"[{device_id if device_id else 'unknown'}] Processing: {os.path.basename(image_path)} (unified analysis)")
    
    try:
        # Use thumbnail for analysis (fast and efficient)
        thumbnail_path = image_path.replace('.jpg', '_thumbnail.jpg')
        if not os.path.exists(thumbnail_path):
            print(f"[{device_id if device_id else 'unknown'}] Thumbnail not found: {os.path.basename(thumbnail_path)}")
            return
        
        print(f"[{device_id}] Analyzing: {os.path.basename(thumbnail_path)}")
        
        # Video Analysis
        blackscreen = analyze_blackscreen(thumbnail_path, device_id=device_id)
        frozen, freeze_details = analyze_freeze(thumbnail_path, device_id=device_id)
        
        # Skip macroblock analysis if freeze or blackscreen detected (performance optimization)
        if blackscreen or frozen:
            macroblocks, quality_score = False, 0.0
            logger.info(f"[{device_id}] Macroblock check: SKIPPED (freeze={frozen}, blackscreen={blackscreen}) - defaulting to False")
        else:
            macroblocks, quality_score = analyze_macroblocks(thumbnail_path, device_id=device_id)
        
        # Audio Analysis
        capture_dir = get_capture_directory_from_image(image_path)
        segment_path = find_latest_audio_segment(capture_dir, device_id=device_id)
        
        if segment_path:
            has_audio, volume_percentage, mean_volume_db = analyze_audio_volume(segment_path, device_id=device_id)
            analyzed_segment = os.path.basename(segment_path)
            logger.info(f"[{device_id}] Audio analysis: {volume_percentage}% volume, audio={'Yes' if has_audio else 'No'}")
        else:
            has_audio, volume_percentage, mean_volume_db = False, 0, -100.0
            analyzed_segment = "no_recent_segment"
            logger.warning(f"[{device_id}] Audio analysis: No recent segments found")
        
        # Get blackscreen percentage for consistency
        blackscreen_percentage = 0
        if blackscreen:
            try:
                img_gray = cv2.imread(thumbnail_path, cv2.IMREAD_GRAYSCALE)
                if img_gray is not None:
                    very_dark_pixels = np.sum(img_gray <= 10)
                    total_pixels = img_gray.shape[0] * img_gray.shape[1]
                    blackscreen_percentage = (very_dark_pixels / total_pixels) * 100
            except Exception:
                blackscreen_percentage = 0

        # Get freeze diffs and last 3 filenames for incidents
        freeze_diffs = []
        last_3_filenames = []
        last_3_thumbnails = []
        
        if freeze_details and 'frame_differences' in freeze_details:
            freeze_diffs = freeze_details['frame_differences']
            
        if freeze_details and 'frames_compared' in freeze_details:
            # Index 0 = current frame, 1 = frame-1, 2 = frame-2
            image_dir = os.path.dirname(image_path)  # Get directory from current image path
            for frame_filename in freeze_details['frames_compared']:
                # Original filename with full path
                original_filename = frame_filename.replace('_thumbnail.jpg', '.jpg')
                original_full_path = os.path.join(image_dir, original_filename)
                last_3_filenames.append(original_full_path)
                
                # Corresponding thumbnail with full path
                thumbnail_filename = original_filename.replace('.jpg', '_thumbnail.jpg')
                thumbnail_full_path = os.path.join(image_dir, thumbnail_filename)
                last_3_thumbnails.append(thumbnail_full_path)

        # Simple consistent result
        result = {
            'timestamp': datetime.fromtimestamp(os.path.getmtime(image_path)).isoformat(),
            'filename': os.path.basename(image_path),
            'thumbnail': os.path.basename(thumbnail_path),
            'blackscreen': bool(blackscreen),
            'blackscreen_percentage': round(blackscreen_percentage, 1),
            'freeze': bool(frozen),
            'macroblocks': bool(macroblocks),
            'quality_score': round(quality_score, 1),
            'freeze_diffs': freeze_diffs,
            'last_3_filenames': last_3_filenames,
            'last_3_thumbnails': last_3_thumbnails,
            'audio': has_audio,
            'volume_percentage': volume_percentage,
            'mean_volume_db': mean_volume_db
        }
        
        # Save single JSON file
        base_filename = os.path.basename(image_path)
        json_filename = base_filename.replace('.jpg', '.json')
        image_dir = os.path.dirname(image_path)
        json_path = os.path.join(image_dir, json_filename)
        
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"[{device_id}] Analysis complete: {json_filename}")
        logger.info(f"[{device_id}] Results: blackscreen={blackscreen}, freeze={frozen}, audio={has_audio}")
        
        # Process alerts with memory-based incident state
        if host_name and device_id and incident_state_json:
            try:
                # Parse incident state from memory
                incident_state = json.loads(incident_state_json)
                
                sys.path.append(os.path.dirname(__file__))
                from alert_system import process_alert_with_memory_state
                
                logger.info(f"[{device_id}] Processing alerts for host: {host_name}, device: {device_id}")
                updated_state = process_alert_with_memory_state(
                    analysis_result=result,
                    host_name=host_name,
                    device_id=device_id,  # Pass device_id directly instead of extracting from path
                    incident_state=incident_state
                )
                
                # Output updated state for capture_monitor to read
                print(f"INCIDENT_STATE:{json.dumps(updated_state)}")
                
                logger.info(f"[{device_id}] Alert processed with memory state (host: {host_name}, device: {device_id})")
            except ImportError as e:
                logger.error(f"[{device_id}] Could not import alert_system: {e}")
            except Exception as e:
                logger.error(f"[{device_id}] Alert processing failed: {e}")
        elif host_name:
            logger.warning(f"[{device_id}] Missing device_id or incident state, skipping alert processing")
        else:
            logger.warning(f"[{device_id}] Host name not provided, skipping alert processing")
        
    except Exception as e:
        print(f"[{device_id if 'device_id' in locals() else 'unknown'}] Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 