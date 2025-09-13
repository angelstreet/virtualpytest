#!/usr/bin/env python3
"""
Simple frame detector - analyzes frames for issues
No state, no DB, no alerts - just detection
"""
import os
import cv2
import numpy as np
import subprocess
import glob
import re

def analyze_blackscreen(image_path, threshold=10):
    """Detect if image is mostly black"""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False
    
    very_dark_pixels = np.sum(img <= threshold)
    total_pixels = img.shape[0] * img.shape[1]
    dark_percentage = (very_dark_pixels / total_pixels) * 100
    
    return dark_percentage > 95

def analyze_freeze(image_path):
    """Detect if image is frozen (identical to previous frame)"""
    directory = os.path.dirname(image_path)
    current_filename = os.path.basename(image_path)
    
    # Get all jpg files, sort by name
    all_files = [f for f in os.listdir(directory) 
                 if f.endswith('.jpg') and '_thumbnail' not in f]
    all_files.sort()
    
    if current_filename not in all_files:
        return False
    
    current_index = all_files.index(current_filename)
    if current_index == 0:
        return False
    
    # Compare with previous frame
    prev_filename = all_files[current_index - 1]
    prev_path = os.path.join(directory, prev_filename)
    
    current_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    prev_img = cv2.imread(prev_path, cv2.IMREAD_GRAYSCALE)
    
    if current_img is None or prev_img is None:
        return False
    
    if current_img.shape != prev_img.shape:
        return False
    
    # Simple pixel difference
    diff = cv2.absdiff(current_img, prev_img)
    mean_diff = np.mean(diff)
    
    return mean_diff < 0.5

def analyze_audio(capture_dir):
    """Check if audio is present in latest segment"""
    pattern = os.path.join(capture_dir, "segment_*.ts")
    segments = glob.glob(pattern)
    if not segments:
        return True  # No segments = assume audio OK
    
    latest = max(segments, key=os.path.getmtime)
    
    try:
        cmd = ['/usr/bin/ffmpeg', '-i', latest, '-af', 'volumedetect', 
               '-vn', '-f', 'null', '/dev/null']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        # Parse volume from stderr
        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                match = re.search(r'mean_volume:\s*([-\d.]+)', line)
                if match:
                    volume_db = float(match.group(1))
                    return volume_db > -50  # Threshold for audio presence
        return False
    except:
        return True  # Assume OK on error

def detect_issues(image_path):
    """Main detection function - returns simple dict"""
    capture_dir = os.path.dirname(os.path.dirname(image_path))  # Go up from /captures/
    
    return {
        'blackscreen': analyze_blackscreen(image_path),
        'freeze': analyze_freeze(image_path),
        'audio_loss': not analyze_audio(capture_dir)
    }
