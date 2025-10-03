"""
Image Utilities - Thumbnail Generation and Image Analysis

Provides utilities for:
- Creating thumbnails from capture images on-demand
- Image analysis functions (blackscreen, freeze, macroblocks detection)
"""

import os
import re
from typing import Optional, Tuple
from PIL import Image
import io
import cv2
import numpy as np


def create_thumbnail_from_capture(
    capture_path: str,
    thumbnail_size: Tuple[int, int] = (320, 180),
    quality: int = 85
) -> Optional[bytes]:
    """
    Create thumbnail from capture image on-demand.
    
    This replaces continuous FFmpeg thumbnail generation with on-demand creation
    only when needed (freeze uploads, reports, etc).
    
    Args:
        capture_path: Full path to capture image (e.g., /path/to/capture_001.jpg)
        thumbnail_size: Target size as (width, height). Default (320, 180)
        quality: JPEG quality (1-100). Default 85
    
    Returns:
        Thumbnail image as bytes (ready for upload/save), or None if error
        
    Example:
        >>> thumb_bytes = create_thumbnail_from_capture('/path/to/capture_001.jpg')
        >>> with open('thumb.jpg', 'wb') as f:
        ...     f.write(thumb_bytes)
    """
    try:
        if not os.path.exists(capture_path):
            print(f"[@image_utils] Error: Capture file not found: {capture_path}")
            return None
        
        # Load and resize image
        img = Image.open(capture_path)
        
        # Use thumbnail() for aspect-ratio preserving resize
        # BILINEAR is faster than LANCZOS with minimal quality loss for small images
        img.thumbnail(thumbnail_size, Image.Resampling.BILINEAR)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality)
        
        return buffer.getvalue()
        
    except Exception as e:
        print(f"[@image_utils] Error creating thumbnail from {capture_path}: {e}")
        return None


def create_thumbnail_file(
    capture_path: str,
    output_path: Optional[str] = None,
    thumbnail_size: Tuple[int, int] = (320, 180),
    quality: int = 85
) -> Optional[str]:
    """
    Create thumbnail file from capture image.
    
    Args:
        capture_path: Full path to capture image
        output_path: Output path for thumbnail. If None, uses capture_path with _thumbnail suffix
        thumbnail_size: Target size as (width, height)
        quality: JPEG quality (1-100)
    
    Returns:
        Path to created thumbnail file, or None if error
        
    Example:
        >>> thumb_path = create_thumbnail_file('/path/to/capture_001.jpg')
        >>> # Creates /path/to/capture_001_thumbnail.jpg
    """
    try:
        # Generate output path if not provided
        if output_path is None:
            base, ext = os.path.splitext(capture_path)
            output_path = f"{base}_thumbnail{ext}"
        
        # Create thumbnail bytes
        thumb_bytes = create_thumbnail_from_capture(capture_path, thumbnail_size, quality)
        
        if thumb_bytes is None:
            return None
        
        # Write to file
        with open(output_path, 'wb') as f:
            f.write(thumb_bytes)
        
        return output_path
        
    except Exception as e:
        print(f"[@image_utils] Error saving thumbnail to {output_path}: {e}")
        return None


def resize_image_for_upload(
    image_path: str,
    max_size: Tuple[int, int] = (320, 180),
    quality: int = 85
) -> Optional[bytes]:
    """
    Resize image for efficient R2 upload.
    
    Alias for create_thumbnail_from_capture() with clearer naming for upload context.
    
    Args:
        image_path: Full path to image
        max_size: Maximum size as (width, height)
        quality: JPEG quality (1-100)
    
    Returns:
        Resized image as bytes, or None if error
    """
    return create_thumbnail_from_capture(image_path, max_size, quality)


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


def analyze_freeze(image_path: str, fps: int = 5) -> Tuple[bool, Optional[dict]]:
    """
    Detect if image is frozen - OPTIMIZED with 1-second spacing and downscaling
    
    Improvements:
    - Compares frames 1 second apart (not consecutive 200ms frames)
    - Downscales 1280x720 → 320x180 before comparison (16× faster)
    - More accurate freeze detection with meaningful time gaps
    
    Args:
        image_path: Path to current frame
        fps: Frames per second (5 for v4l2, 2 for x11grab)
    
    Returns:
        Tuple of (is_frozen, freeze_details)
    """
    directory = os.path.dirname(image_path)
    current_filename = os.path.basename(image_path)
    
    # Extract frame number and format
    match = re.match(r'capture_(\d+)\.jpg', current_filename)
    if not match:
        return False, None
    
    current_num_str = match.group(1)
    current_num = int(current_num_str)
    num_digits = len(current_num_str)
    
    # Need at least 2 seconds of history (2 * fps frames)
    if current_num < (2 * fps):
        return False, None
    
    # Compare frames 1 SECOND apart (not consecutive!)
    # Example at 5 FPS: frame 15 vs 10 vs 5 (3s, 2s, 1s)
    prev1_num = current_num - fps      # 1 second ago
    prev2_num = current_num - (2 * fps) # 2 seconds ago
    
    prev1_filename = f"capture_{prev1_num:0{num_digits}d}.jpg"
    prev2_filename = f"capture_{prev2_num:0{num_digits}d}.jpg"
    
    prev1_path = os.path.join(directory, prev1_filename)
    prev2_path = os.path.join(directory, prev2_filename)
    
    # Check if files exist
    if not os.path.exists(prev1_path) or not os.path.exists(prev2_path):
        return False, None
    
    # Load and downscale images to 320x180 for faster comparison
    # Downscaling 1280x720 → 320x180 reduces pixels by 16×!
    current_img = load_and_downscale_image(image_path, target_size=(320, 180))
    prev1_img = load_and_downscale_image(prev1_path, target_size=(320, 180))
    prev2_img = load_and_downscale_image(prev2_path, target_size=(320, 180))
    
    if current_img is None or prev1_img is None or prev2_img is None:
        return False, None
    
    # Calculate differences between all 3 frames (1 second apart each)
    diff_1vs2 = cv2.absdiff(prev2_img, prev1_img)
    diff_1vs3 = cv2.absdiff(prev2_img, current_img)
    diff_2vs3 = cv2.absdiff(prev1_img, current_img)
    
    mean_diff_1vs2 = np.mean(diff_1vs2)
    mean_diff_1vs3 = np.mean(diff_1vs3)
    mean_diff_2vs3 = np.mean(diff_2vs3)
    
    # Frozen if ALL comparisons show small differences over 2 seconds
    freeze_threshold = 0.5
    is_frozen = (mean_diff_1vs2 < freeze_threshold and 
                mean_diff_1vs3 < freeze_threshold and 
                mean_diff_2vs3 < freeze_threshold)
    
    freeze_details = {
        'frames_compared': [prev2_filename, prev1_filename, current_filename],
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

