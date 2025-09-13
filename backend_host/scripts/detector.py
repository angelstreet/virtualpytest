#!/usr/bin/env python3
"""
Frame detector - analyzes frames for issues with rich metadata
Returns same format as original analyze_audio_video.py
"""
import os
import cv2
import numpy as np
import subprocess
import glob
import re
import time
from datetime import datetime

def analyze_blackscreen(image_path, threshold=10):
    """Detect if image is mostly black"""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False, 0
    
    very_dark_pixels = np.sum(img <= threshold)
    total_pixels = img.shape[0] * img.shape[1]
    dark_percentage = (very_dark_pixels / total_pixels) * 100
    
    is_blackscreen = dark_percentage > 95
    return is_blackscreen, dark_percentage

def analyze_freeze(image_path):
    """Detect if image is frozen (identical to previous frames) - SAME AS ORIGINAL"""
    directory = os.path.dirname(image_path)
    current_filename = os.path.basename(image_path)
    
    # Get all jpg files, sort by name
    all_files = [f for f in os.listdir(directory) 
                 if f.endswith('.jpg') and '_thumbnail' not in f]
    all_files.sort()
    
    if current_filename not in all_files:
        return False, None
    
    current_index = all_files.index(current_filename)
    if current_index < 2:  # Need at least 2 previous frames
        return False, None
    
    # Get current and 2 previous frames
    prev1_filename = all_files[current_index - 1]
    prev2_filename = all_files[current_index - 2]
    
    current_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    prev1_img = cv2.imread(os.path.join(directory, prev1_filename), cv2.IMREAD_GRAYSCALE)
    prev2_img = cv2.imread(os.path.join(directory, prev2_filename), cv2.IMREAD_GRAYSCALE)
    
    if current_img is None or prev1_img is None or prev2_img is None:
        return False, None
    
    if current_img.shape != prev1_img.shape or current_img.shape != prev2_img.shape:
        return False, None
    
    # Calculate differences between all 3 frames
    diff_1vs2 = cv2.absdiff(prev2_img, prev1_img)
    diff_1vs3 = cv2.absdiff(prev2_img, current_img)
    diff_2vs3 = cv2.absdiff(prev1_img, current_img)
    
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
        'threshold': freeze_threshold
    }
    
    return is_frozen, freeze_details

def analyze_audio(capture_dir):
    """Check if audio is present in latest segment - SAME AS ORIGINAL"""
    pattern = os.path.join(capture_dir, "segment_*.ts")
    segments = glob.glob(pattern)
    if not segments:
        return True, 0, -100.0  # No segments = assume audio OK
    
    latest = max(segments, key=os.path.getmtime)
    
    # Check if recent (within last 5 minutes)
    latest_mtime = os.path.getmtime(latest)
    current_time = time.time()
    age_seconds = current_time - latest_mtime
    if age_seconds > 300:  # 5 minutes
        return False, 0, -100.0
    
    try:
        cmd = ['/usr/bin/ffmpeg', '-i', latest, '-af', 'volumedetect', 
               '-vn', '-f', 'null', '/dev/null']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
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
    except:
        return False, 0, -100.0

def detect_issues(image_path):
    """Main detection function - returns EXACT same format as original analyze_audio_video.py"""
    capture_dir = os.path.dirname(os.path.dirname(image_path))  # Go up from /captures/
    
    # Video Analysis
    blackscreen, blackscreen_percentage = analyze_blackscreen(image_path)
    frozen, freeze_details = analyze_freeze(image_path)
    
    # Audio Analysis
    has_audio, volume_percentage, mean_volume_db = analyze_audio(capture_dir)
    
    # Get frame paths for R2 upload (CRITICAL - SAME AS ORIGINAL)
    freeze_diffs = []
    last_3_filenames = []
    last_3_thumbnails = []
    
    if freeze_details and 'frame_differences' in freeze_details:
        freeze_diffs = freeze_details['frame_differences']
        
    if freeze_details and 'frames_compared' in freeze_details:
        # Get directory from current image path
        image_dir = os.path.dirname(image_path)
        for frame_filename in freeze_details['frames_compared']:
            # Original filename with full path
            original_full_path = os.path.join(image_dir, frame_filename)
            last_3_filenames.append(original_full_path)
            
            # Corresponding thumbnail with full path
            thumbnail_filename = frame_filename.replace('.jpg', '_thumbnail.jpg')
            thumbnail_full_path = os.path.join(image_dir, thumbnail_filename)
            last_3_thumbnails.append(thumbnail_full_path)
    
    # Return EXACT same format as original (CRITICAL FOR R2 UPLOAD)
    return {
        'timestamp': datetime.fromtimestamp(os.path.getmtime(image_path)).isoformat(),
        'filename': os.path.basename(image_path),
        'blackscreen': bool(blackscreen),
        'blackscreen_percentage': round(blackscreen_percentage, 1),
        'freeze': bool(frozen),
        'freeze_diffs': freeze_diffs,
        'last_3_filenames': last_3_filenames,      # ← CRITICAL FOR R2 UPLOAD
        'last_3_thumbnails': last_3_thumbnails,   # ← CRITICAL FOR R2 UPLOAD
        'audio': has_audio,
        'volume_percentage': volume_percentage,
        'mean_volume_db': mean_volume_db
    }
