"""
Image Utilities - Image Analysis

Provides utilities for:
- Image analysis functions (blackscreen, freeze, macroblocks detection)
- Image preprocessing for detection algorithms
"""

import os
import re
from typing import Optional, Tuple
import cv2
import numpy as np


# =============================================================================
# Image Analysis Functions
# =============================================================================

def load_and_downscale_image(image_path: str, target_size: Tuple[int, int] = (320, 180)):
    """
    Load image and downscale for efficient analysis.
    Reusable for freeze, blackscreen, and macroblocks detection.
    
    Args:
        image_path: Path to image file
        target_size: Target size (width, height)
    
    Returns:
        Downscaled grayscale image or None if error
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        
        # Downscale using INTER_AREA (best for downsampling)
        img_small = cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)
        return img_small
    except Exception as e:
        print(f"[@image_utils] Error loading/downscaling {image_path}: {e}")
        return None


def analyze_blackscreen(image_path: str, threshold: int = 10, downscaled_img=None) -> Tuple[bool, float]:
    """
    Detect if image is mostly black - OPTIMIZED with optional downscaled input
    
    Args:
        image_path: Path to image (used if downscaled_img not provided)
        threshold: Darkness threshold (0-255)
        downscaled_img: Pre-downscaled image to reuse (saves computation)
    
    Returns:
        Tuple of (is_blackscreen, dark_percentage)
    """
    if downscaled_img is not None:
        img = downscaled_img
    else:
        img = load_and_downscale_image(image_path)
    
    if img is None:
        return False, 0.0
    
    very_dark_pixels = np.sum(img <= threshold)
    total_pixels = img.shape[0] * img.shape[1]
    dark_percentage = (very_dark_pixels / total_pixels) * 100
    
    is_blackscreen = dark_percentage > 95
    return is_blackscreen, dark_percentage


def analyze_freeze(capture_path: str, thumbnails_dir: str, fps: int = 5) -> Tuple[bool, Optional[dict]]:
    """
    Detect if image is frozen using thumbnails (5fps for v4l2, 2fps for VNC) - SIMPLE and EFFICIENT
    
    Takes last 3 thumbnails spaced 1 second apart.
    At 5fps: current, -5, -10 (1s apart each)
    At 2fps: current, -2, -4 (1s apart each)
    
    Args:
        capture_path: Path to current capture (e.g., /path/captures/capture_000009.jpg)
        thumbnails_dir: Path to thumbnails directory
        fps: Frames per second (5 for v4l2, 2 for x11grab/VNC)
    
    Returns:
        Tuple of (is_frozen, freeze_details)
    """
    # Extract frame number from capture filename
    current_filename = os.path.basename(capture_path)
    match = re.match(r'capture_(\d+)\.jpg', current_filename)
    if not match:
        return False, None
    
    current_num_str = match.group(1)
    current_num = int(current_num_str)
    num_digits = len(current_num_str)
    
    # Need at least 2 seconds of history (2 * fps frames)
    if current_num < (2 * fps):
        return False, None
    
    # Get last 3 thumbnails spaced 1 second apart
    thumb_current_num = current_num
    thumb_prev1_num = current_num - fps        # 1 second ago
    thumb_prev2_num = current_num - (2 * fps)  # 2 seconds ago
    
    thumb_current_filename = f"capture_{thumb_current_num:0{num_digits}d}_thumbnail.jpg"
    thumb_prev1_filename = f"capture_{thumb_prev1_num:0{num_digits}d}_thumbnail.jpg"
    thumb_prev2_filename = f"capture_{thumb_prev2_num:0{num_digits}d}_thumbnail.jpg"
    
    thumb_current_path = os.path.join(thumbnails_dir, thumb_current_filename)
    thumb_prev1_path = os.path.join(thumbnails_dir, thumb_prev1_filename)
    thumb_prev2_path = os.path.join(thumbnails_dir, thumb_prev2_filename)
    
    # Check if all 3 thumbnails exist
    if not os.path.exists(thumb_current_path) or not os.path.exists(thumb_prev1_path) or not os.path.exists(thumb_prev2_path):
        return False, None
    
    # Load thumbnails (already small at 320x180, no need to downscale further!)
    thumb_current = cv2.imread(thumb_current_path, cv2.IMREAD_GRAYSCALE)
    thumb_prev1 = cv2.imread(thumb_prev1_path, cv2.IMREAD_GRAYSCALE)
    thumb_prev2 = cv2.imread(thumb_prev2_path, cv2.IMREAD_GRAYSCALE)
    
    if thumb_current is None or thumb_prev1 is None or thumb_prev2 is None:
        return False, None
    
    # Calculate differences between all 3 thumbnails (1 second apart each)
    diff_1vs2 = cv2.absdiff(thumb_prev2, thumb_prev1)
    diff_1vs3 = cv2.absdiff(thumb_prev2, thumb_current)
    diff_2vs3 = cv2.absdiff(thumb_prev1, thumb_current)
    
    mean_diff_1vs2 = np.mean(diff_1vs2)
    mean_diff_1vs3 = np.mean(diff_1vs3)
    mean_diff_2vs3 = np.mean(diff_2vs3)
    
    # Frozen if ALL comparisons show small differences over 2 seconds
    freeze_threshold = 0.5
    is_frozen = (mean_diff_1vs2 < freeze_threshold and 
                mean_diff_1vs3 < freeze_threshold and 
                mean_diff_2vs3 < freeze_threshold)
    
    freeze_details = {
        'frames_compared': [thumb_prev2_filename, thumb_prev1_filename, thumb_current_filename],
        'frame_differences': [round(mean_diff_1vs2, 2), round(mean_diff_1vs3, 2), round(mean_diff_2vs3, 2)],
        'threshold': freeze_threshold,
        'time_spacing': f'{fps} frames = 1 second'
    }
    
    return is_frozen, freeze_details


def analyze_macroblocks(image_path: str) -> Tuple[bool, float]:
    """
    Conservative macroblock/image quality detection using strict thresholds.
    Detects: green/pink pixels, severe blur, compression artifacts.
    Only flags true macroblocks to avoid false positives.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Tuple of (macroblocks_detected, quality_score)
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False, 0.0
        
        # Convert to different color spaces for analysis
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Sample every 10th pixel for performance
        sample_rate = 10
        hsv_sampled = hsv[::sample_rate, ::sample_rate]
        
        # Green artifacts: High saturation in green range
        green_mask = cv2.inRange(hsv_sampled, (40, 100, 50), (80, 255, 255))
        green_pixels = np.sum(green_mask > 0)
        
        # Pink/Magenta artifacts: High saturation in magenta range  
        pink_mask = cv2.inRange(hsv_sampled, (140, 100, 50), (170, 255, 255))
        pink_pixels = np.sum(pink_mask > 0)
        
        total_sampled = hsv_sampled.shape[0] * hsv_sampled.shape[1]
        artifact_percentage = ((green_pixels + pink_pixels) / total_sampled) * 100
        
        # Conservative blur detection using Laplacian variance
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_sampled = gray[::sample_rate, ::sample_rate]
        laplacian_var = cv2.Laplacian(gray_sampled, cv2.CV_64F).var()
        
        # CONSERVATIVE THRESHOLDS - Only flag obvious macroblocks
        has_severe_artifacts = artifact_percentage > 8.0
        is_severely_blurry = laplacian_var < 30
        
        # Both conditions should be somewhat present for true macroblocks
        if has_severe_artifacts and is_severely_blurry:
            macroblocks_detected = True
        elif has_severe_artifacts and artifact_percentage > 15.0:
            macroblocks_detected = True
        elif is_severely_blurry and laplacian_var < 15:
            macroblocks_detected = True
        else:
            macroblocks_detected = False
        
        quality_score = max(artifact_percentage, (200 - laplacian_var) / 2) if macroblocks_detected else 0.0
        
        return macroblocks_detected, quality_score
        
    except Exception as e:
        print(f"[@image_utils] Error in macroblocks detection: {e}")
        return False, 0.0

