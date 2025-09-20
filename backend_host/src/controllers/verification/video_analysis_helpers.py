"""
Video Analysis Helpers

Core video analysis functionality for the VideoVerificationController:
1. OpenCV-based image analysis
2. FFmpeg-based analysis  
3. Motion detection and frame comparison
4. Basic image processing utilities

This helper handles the fundamental analysis operations that don't require
specialized domain knowledge (AI, content detection, etc.).
"""

import subprocess
import time
import os
import cv2
import numpy as np
import json
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

# Simplified sampling patterns for performance optimization
SAMPLING_PATTERNS = {
    "freeze_sample_rate": 10,     # Every 10th pixel for freeze detection
    "blackscreen_samples": 1000,  # 1000 random pixels for blackscreen
    "error_grid_rate": 15,        # Every 15th pixel in grid for errors
    "subtitle_edge_threshold": 200  # Edge detection threshold
}


class VideoAnalysisHelpers:
    """Core video analysis operations using OpenCV and FFmpeg."""
    
    def __init__(self, av_controller, device_name: str = "VideoAnalysis"):
        """
        Initialize video analysis helpers.
        
        Args:
            av_controller: AV controller for capturing video/images
            device_name: Name for logging purposes
        """
        self.av_controller = av_controller
        self.device_name = device_name
    
    # =============================================================================
    # Core Analysis Methods
    # =============================================================================
    
    def analyze_with_opencv(self, image_path: str, analysis_type: str) -> Dict[str, Any]:
        """
        Analyze image using OpenCV.
        
        Args:
            image_path: Path to the image file
            analysis_type: Type of analysis (basic, color, brightness)
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return {"error": "Could not load image"}
            
            height, width, channels = image.shape
            
            if analysis_type == "basic":
                # Basic image properties
                return {
                    "width": width,
                    "height": height,
                    "channels": channels,
                    "total_pixels": width * height,
                    "analysis_type": "basic",
                    "image_path": image_path
                }
                
            elif analysis_type == "color":
                # Color analysis
                mean_color = cv2.mean(image)
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                
                # Dominant color detection (simplified)
                colors = {
                    "blue": mean_color[0],
                    "green": mean_color[1], 
                    "red": mean_color[2]
                }
                dominant_color = max(colors, key=colors.get)
                
                return {
                    "mean_bgr": mean_color[:3],
                    "dominant_color": dominant_color,
                    "color_variance": np.var(image),
                    "analysis_type": "color",
                    "image_path": image_path
                }
                
            elif analysis_type == "brightness":
                # Brightness analysis
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                mean_brightness = np.mean(gray)
                brightness_std = np.std(gray)
                
                return {
                    "mean_brightness": float(mean_brightness),
                    "brightness_std": float(brightness_std),
                    "brightness_percentage": float(mean_brightness / 255 * 100),
                    "analysis_type": "brightness",
                    "image_path": image_path
                }
                
            return {"error": f"Unknown OpenCV analysis type: {analysis_type}"}
            
        except Exception as e:
            print(f"VideoAnalysis[{self.device_name}]: OpenCV analysis error: {e}")
            return {"error": str(e)}

    def analyze_with_ffmpeg(self, image_path: str, analysis_type: str) -> Dict[str, Any]:
        """
        Analyze image using FFmpeg.
        
        Args:
            image_path: Path to the image file
            analysis_type: Type of analysis
            
        Returns:
            Dictionary with analysis results
        """
        try:
            if analysis_type == "basic":
                # Get basic image info
                cmd = [
                    '/usr/bin/ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_streams',
                    image_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if 'streams' in data and len(data['streams']) > 0:
                        stream = data['streams'][0]
                        return {
                            "width": stream.get('width', 0),
                            "height": stream.get('height', 0),
                            "pixel_format": stream.get('pix_fmt', 'unknown'),
                            "analysis_type": "basic",
                            "image_path": image_path
                        }
                        
            # For other analysis types, return basic info
            return {
                "analysis_type": analysis_type,
                "image_path": image_path,
                "note": "Limited analysis without OpenCV"
            }
            
        except Exception as e:
            print(f"VideoAnalysis[{self.device_name}]: FFmpeg analysis error: {e}")
            return {"error": f"FFmpeg analysis failed: {e}"}

    # =============================================================================
    # Motion Detection Methods
    # =============================================================================
    
    def compare_images_for_motion(self, image1_path: str, image2_path: str, threshold: float) -> Tuple[bool, float]:
        """
        Compare two images to detect motion.
        
        Args:
            image1_path: Path to first image
            image2_path: Path to second image
            threshold: Motion threshold percentage
            
        Returns:
            Tuple of (motion_detected, change_percentage)
        """
        try:
            # Load images
            img1 = cv2.imread(image1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(image2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                print(f"VideoAnalysis[{self.device_name}]: Could not load images for comparison")
                return False, 0.0
            
            # Resize images to same size if needed
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            # Calculate absolute difference
            diff = cv2.absdiff(img1, img2)
            
            # Calculate percentage of changed pixels
            total_pixels = img1.shape[0] * img1.shape[1]
            changed_pixels = np.count_nonzero(diff > 30)  # Threshold for significant change
            change_percentage = (changed_pixels / total_pixels) * 100
            
            motion_detected = change_percentage > threshold
            
            print(f"VideoAnalysis[{self.device_name}]: Frame change: {change_percentage:.1f}% (threshold: {threshold}%)")
            return motion_detected, change_percentage
            
        except Exception as e:
            print(f"VideoAnalysis[{self.device_name}]: Image comparison error: {e}")
            return False, 0.0

    def detect_motion_between_captures(self, duration: float = 3.0, threshold: float = 5.0) -> Tuple[bool, float]:
        """
        Detect motion by capturing and comparing two screenshots.
        
        Args:
            duration: Time to wait between captures
            threshold: Motion threshold percentage
            
        Returns:
            Tuple of (motion_detected, change_percentage)
        """
        try:
            if not self.av_controller:
                print(f"VideoAnalysis[{self.device_name}]: No AV controller available")
                return False, 0.0
            
            # Capture two screenshots with a delay
            screenshot1 = self._capture_screenshot_for_analysis(f"motion_frame1_{int(time.time())}.png")
            if not screenshot1:
                return False, 0.0
                
            time.sleep(min(duration, 2.0))  # Wait for motion
            
            screenshot2 = self._capture_screenshot_for_analysis(f"motion_frame2_{int(time.time())}.png")
            if not screenshot2:
                return False, 0.0
            
            # Compare the two images
            motion_detected, change_percentage = self.compare_images_for_motion(screenshot1, screenshot2, threshold)
            
            return motion_detected, change_percentage
            
        except Exception as e:
            print(f"VideoAnalysis[{self.device_name}]: Motion detection error: {e}")
            return False, 0.0

    def wait_for_video_change(self, timeout: float = 10.0, threshold: float = 10.0) -> Tuple[bool, float]:
        """
        Wait for video content to change.
        
        Args:
            timeout: Maximum time to wait in seconds
            threshold: Change threshold as percentage
            
        Returns:
            Tuple of (change_detected, elapsed_time)
        """
        try:
            if not self.av_controller:
                print(f"VideoAnalysis[{self.device_name}]: No AV controller available")
                return False, 0.0
            
            print(f"VideoAnalysis[{self.device_name}]: Waiting for video change (timeout: {timeout}s, threshold: {threshold}%)")
            
            # Capture initial frame
            initial_frame = self._capture_screenshot_for_analysis(f"initial_frame_{int(time.time())}.png")
            if not initial_frame:
                return False, 0.0
            
            start_time = time.time()
            check_interval = 1.0  # Check every second
            
            while time.time() - start_time < timeout:
                time.sleep(check_interval)
                
                # Capture current frame
                current_frame = self._capture_screenshot_for_analysis(f"current_frame_{int(time.time())}.png")
                if not current_frame:
                    continue
                
                # Compare frames
                change_detected, change_percentage = self.compare_images_for_motion(initial_frame, current_frame, threshold)
                if change_detected:
                    elapsed = time.time() - start_time
                    print(f"VideoAnalysis[{self.device_name}]: Video change detected after {elapsed:.1f}s ({change_percentage:.1f}%)")
                    return True, elapsed
            
            elapsed = time.time() - start_time
            print(f"VideoAnalysis[{self.device_name}]: No video change detected within {timeout}s")
            return False, elapsed
            
        except Exception as e:
            print(f"VideoAnalysis[{self.device_name}]: Video change detection error: {e}")
            return False, 0.0

    # =============================================================================
    # Frame Comparison Utilities
    # =============================================================================
    
    def compare_consecutive_frames(self, images: List[Dict], freeze_threshold: float) -> List[Dict]:
        """
        Compare consecutive frames for freeze detection.
        
        Args:
            images: List of image dictionaries with 'path', 'image', 'filename'
            freeze_threshold: Threshold for frame difference detection
            
        Returns:
            List of comparison results
        """
        comparisons = []
        
        try:
            # Compare consecutive frames
            for i in range(len(images) - 1):
                img1 = images[i]
                img2 = images[i + 1]
                
                # Check if images have same dimensions
                if img1['image'].shape != img2['image'].shape:
                    print(f"VideoAnalysis[{self.device_name}]: Image dimensions don't match: {img1['image'].shape} vs {img2['image'].shape}")
                    continue
                
                # Optimized sampling for pixel difference (every 10th pixel for performance)
                sample_rate = SAMPLING_PATTERNS["freeze_sample_rate"]
                img1_sampled = img1['image'][::sample_rate, ::sample_rate]
                img2_sampled = img2['image'][::sample_rate, ::sample_rate]
                
                # Calculate difference
                diff = cv2.absdiff(img1_sampled, img2_sampled)
                mean_diff = np.mean(diff)
                
                comparison = {
                    'frame1': img1['filename'],
                    'frame2': img2['filename'],
                    'mean_difference': round(float(mean_diff), 2),
                    'is_frozen': bool(mean_diff < freeze_threshold),
                    'threshold': freeze_threshold
                }
                
                comparisons.append(comparison)
                
                print(f"VideoAnalysis[{self.device_name}]: Frame comparison {img1['filename']} vs {img2['filename']}: diff={mean_diff:.2f}")
            
            return comparisons
            
        except Exception as e:
            print(f"VideoAnalysis[{self.device_name}]: Frame comparison error: {e}")
            return []

    # =============================================================================
    # Utility Methods
    # =============================================================================
    
    def _capture_screenshot_for_analysis(self, filename: str) -> Optional[str]:
        """
        Capture a screenshot using the AV controller for analysis purposes.
        
        Args:
            filename: Name for the screenshot file
            
        Returns:
            Path to the captured screenshot or None if failed
        """
        try:
            if not self.av_controller or not hasattr(self.av_controller, 'take_screenshot'):
                print(f"VideoAnalysis[{self.device_name}]: AV controller not available for screenshot")
                return None
            
            # Use AV controller's screenshot method
            result = self.av_controller.take_screenshot(filename)
            if result and os.path.exists(result):
                return result
            else:
                print(f"VideoAnalysis[{self.device_name}]: Failed to capture screenshot")
                return None
                
        except Exception as e:
            print(f"VideoAnalysis[{self.device_name}]: Screenshot capture error: {e}")
            return None

    def load_images_for_analysis(self, image_paths: List[str]) -> List[Dict]:
        """
        Load multiple images for analysis.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            List of image dictionaries with loaded OpenCV images
        """
        images = []
        
        for image_path in image_paths:
            if not os.path.exists(image_path):
                print(f"VideoAnalysis[{self.device_name}]: Image file not found: {image_path}")
                continue
            
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"VideoAnalysis[{self.device_name}]: Could not load image: {image_path}")
                continue
            
            images.append({
                'path': image_path,
                'image': img,
                'filename': os.path.basename(image_path)
            })
        
        return images

    def get_image_basic_info(self, image_path: str) -> Dict[str, Any]:
        """
        Get basic information about an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with basic image information
        """
        try:
            if not os.path.exists(image_path):
                return {"error": "Image file not found"}
            
            img = cv2.imread(image_path)
            if img is None:
                return {"error": "Could not load image"}
            
            height, width, channels = img.shape
            file_size = os.path.getsize(image_path)
            
            return {
                "width": width,
                "height": height,
                "channels": channels,
                "total_pixels": width * height,
                "file_size_bytes": file_size,
                "file_path": image_path,
                "filename": os.path.basename(image_path)
            }
            
        except Exception as e:
            print(f"VideoAnalysis[{self.device_name}]: Image info error: {e}")
            return {"error": str(e)}