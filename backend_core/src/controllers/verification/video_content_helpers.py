"""
Video Content Detection Helpers

Specialized content detection functionality for the VideoVerificationController:
1. Blackscreen detection
2. Freeze detection  
3. Subtitle detection with OCR
4. Text extraction and language detection
5. Error content detection

This helper handles content-specific analysis that requires domain knowledge
about video artifacts, subtitles, and visual content patterns.
"""

import os
import time
import cv2
import numpy as np
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

# Optional imports for text extraction and language detection
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from langdetect import detect, LangDetectException
    LANG_DETECT_AVAILABLE = True
except ImportError:
    LANG_DETECT_AVAILABLE = False

# Simplified sampling patterns for performance optimization
SAMPLING_PATTERNS = {
    "freeze_sample_rate": 10,     # Every 10th pixel for freeze detection
    "blackscreen_samples": 1000,  # 1000 random pixels for blackscreen
    "error_grid_rate": 15,        # Every 15th pixel in grid for errors
    "subtitle_edge_threshold": 200  # Edge detection threshold
}


class VideoContentHelpers:
    """Content detection and analysis for video verification."""
    
    def __init__(self, av_controller, device_name: str = "VideoContent"):
        """
        Initialize video content helpers.
        
        Args:
            av_controller: AV controller for capturing video/images
            device_name: Name for logging purposes
        """
        self.av_controller = av_controller
        self.device_name = device_name
    
    # =============================================================================
    # Blackscreen Detection
    # =============================================================================
    
    def detect_blackscreen_in_image(self, image_path: str, threshold: int = 10) -> Dict[str, Any]:
        """
        Detect if image is mostly black (blackscreen) - Simple and reliable.
        
        Args:
            image_path: Path to image file
            threshold: Pixel intensity threshold (0-255)
            
        Returns:
            Dictionary with blackscreen analysis results
        """
        try:
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': 'Image file not found',
                    'image_path': image_path
                }
            
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return {
                    'success': False,
                    'error': 'Could not load image',
                    'image_path': image_path
                }
            
            # Simple approach: count how many pixels are very dark (0-threshold)
            very_dark_pixels = np.sum(img <= threshold)
            total_pixels = img.shape[0] * img.shape[1]
            dark_percentage = (very_dark_pixels / total_pixels) * 100
            
            # If more than 95% of pixels are very dark, it's a blackscreen
            is_blackscreen = bool(dark_percentage > 95)
            
            result = {
                'success': True,
                'is_blackscreen': is_blackscreen,
                'dark_percentage': round(float(dark_percentage), 2),
                'threshold': threshold,
                'very_dark_pixels': int(very_dark_pixels),
                'total_pixels': int(total_pixels),
                'image_size': f"{img.shape[1]}x{img.shape[0]}",
                'confidence': 0.9 if is_blackscreen else 0.1,
                'image_path': os.path.basename(image_path)
            }
            
            print(f"VideoContent[{self.device_name}]: Blackscreen analysis - {dark_percentage:.1f}% dark pixels, blackscreen={is_blackscreen}")
            return result
            
        except Exception as e:
            print(f"VideoContent[{self.device_name}]: Blackscreen detection error: {e}")
            return {
                'success': False,
                'error': f'Analysis error: {str(e)}',
                'image_path': image_path
            }

    def detect_blackscreen_batch(self, image_paths: List[str], threshold: int = 10) -> Dict[str, Any]:
        """
        Detect blackscreen in multiple images.
        
        Args:
            image_paths: List of image paths to analyze
            threshold: Pixel intensity threshold (0-255)
            
        Returns:
            Dictionary with overall blackscreen analysis results
        """
        results = []
        
        for image_path in image_paths:
            result = self.detect_blackscreen_in_image(image_path, threshold)
            results.append(result)
        
        # Calculate overall result
        successful_analyses = [r for r in results if r.get('success')]
        blackscreen_detected = any(r.get('is_blackscreen', False) for r in successful_analyses)
        
        overall_result = {
            'success': len(successful_analyses) > 0,
            'blackscreen_detected': blackscreen_detected,
            'analyzed_images': len(results),
            'successful_analyses': len(successful_analyses),
            'results': results,
            'analysis_type': 'blackscreen_detection',
            'timestamp': datetime.now().isoformat()
        }
        
        return overall_result

    # =============================================================================
    # Freeze Detection
    # =============================================================================
    
    def detect_freeze_in_images(self, image_paths: List[str], freeze_threshold: float = 1.0) -> Dict[str, Any]:
        """
        Detect if images are frozen (identical frames) - Check multiple frames with caching.
        
        Args:
            image_paths: List of image paths to analyze
            freeze_threshold: Threshold for frame difference detection
            
        Returns:
            Dictionary with freeze analysis results
        """
        try:
            if len(image_paths) < 2:
                return {
                    'success': False,
                    'error': 'Need at least 2 images for freeze detection',
                    'freeze_detected': False
                }
            
            # Load all images first
            images = []
            for image_path in image_paths:
                if not os.path.exists(image_path):
                    return {
                        'success': False,
                        'error': f'Image file not found: {image_path}',
                        'freeze_detected': False
                    }
                
                img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    return {
                        'success': False,
                        'error': f'Could not load image: {image_path}',
                        'freeze_detected': False
                    }
                
                images.append({
                    'path': image_path,
                    'image': img,
                    'filename': os.path.basename(image_path)
                })
            
            # Compare consecutive frames
            comparisons = []
            for i in range(len(images) - 1):
                img1 = images[i]
                img2 = images[i + 1]
                
                # Check if images have same dimensions
                if img1['image'].shape != img2['image'].shape:
                    return {
                        'success': False,
                        'error': f'Image dimensions don\'t match: {img1["image"].shape} vs {img2["image"].shape}',
                        'freeze_detected': False
                    }
                
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
                
                print(f"VideoContent[{self.device_name}]: Frame comparison {img1['filename']} vs {img2['filename']}: diff={mean_diff:.2f}")
            
            # Determine overall freeze status
            # Frames are considered frozen if ALL comparisons show very small differences
            all_frozen = all(comp['is_frozen'] for comp in comparisons)
            frozen_count = sum(1 for comp in comparisons if comp['is_frozen'])
            
            overall_result = {
                'success': True,
                'freeze_detected': all_frozen,
                'analyzed_images': len(images),
                'frame_comparisons': len(comparisons),
                'frozen_comparisons': frozen_count,
                'freeze_threshold': freeze_threshold,
                'comparisons': comparisons,
                'confidence': 0.9 if all_frozen else 0.1,
                'analysis_type': 'freeze_detection',
                'timestamp': datetime.now().isoformat()
            }
            
            return overall_result
            
        except Exception as e:
            print(f"VideoContent[{self.device_name}]: Freeze detection error: {e}")
            return {
                'success': False,
                'error': f'Freeze detection failed: {str(e)}',
                'analysis_type': 'freeze_detection',
                'freeze_detected': False
            }

    # =============================================================================
    # Subtitle Detection with OCR
    # =============================================================================
    
    def analyze_subtitle_region(self, img, extract_text: bool = True) -> Dict[str, Any]:
        """
        Analyze subtitle region for text content and errors.
        
        Args:
            img: OpenCV image (BGR format)
            extract_text: Whether to extract text using OCR
            
        Returns:
            Dictionary with subtitle analysis results
        """
        try:
            height, width = img.shape[:2]
            
            # Enhanced subtitle detection with adaptive region processing
            # Expanded to capture 2-line subtitles - start from 70% to bottom (30% of screen height)
            subtitle_height_start = int(height * 0.7)
            subtitle_width_start = int(width * 0.2)  # Skip left 20%
            subtitle_width_end = int(width * 0.8)    # Skip right 20%
            
            subtitle_region = img[subtitle_height_start:, subtitle_width_start:subtitle_width_end]
            gray_subtitle = cv2.cvtColor(subtitle_region, cv2.COLOR_BGR2GRAY)
            
            # Apply adaptive thresholding before edge detection for better text extraction
            adaptive_thresh = cv2.adaptiveThreshold(gray_subtitle, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                  cv2.THRESH_BINARY, 11, 2)
            edges = cv2.Canny(adaptive_thresh, 50, 150)
            subtitle_edges = np.sum(edges > 0)
            
            # Dynamic threshold based on region size
            region_pixels = subtitle_region.shape[0] * subtitle_region.shape[1]
            adaptive_threshold = max(SAMPLING_PATTERNS["subtitle_edge_threshold"], region_pixels * 0.002)
            has_subtitles = bool(subtitle_edges > adaptive_threshold)
            
            # Error detection - look for prominent red content
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Use configurable grid sampling rate
            grid_rate = SAMPLING_PATTERNS["error_grid_rate"]
            sampled_hsv = hsv[::grid_rate, ::grid_rate]
            
            # Red color range in HSV - more restrictive for actual error messages
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 100, 100])
            upper_red2 = np.array([180, 255, 255])
            
            mask1 = cv2.inRange(sampled_hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(sampled_hsv, lower_red2, upper_red2)
            red_mask = mask1 + mask2
            
            red_pixels = np.sum(red_mask > 0)
            total_sampled_pixels = sampled_hsv.shape[0] * sampled_hsv.shape[1]
            red_percentage = float((red_pixels / total_sampled_pixels) * 100)
            
            # Higher threshold for error detection
            has_errors = bool(red_percentage > 8.0)
            
            # Extract text if requested and subtitles detected
            extracted_text = ""
            detected_language = "unknown"
            if extract_text and has_subtitles and OCR_AVAILABLE:
                extracted_text = self.extract_text_from_region(subtitle_region)
                if extracted_text:
                    detected_language = self.detect_language(extracted_text)
                    print(f"VideoContent[{self.device_name}]: Extracted subtitle text: '{extracted_text}' -> Language: {detected_language}")
                else:
                    # If no text extracted, then no real subtitles detected
                    print(f"VideoContent[{self.device_name}]: Edge detection found {subtitle_edges} edges (threshold: {adaptive_threshold:.0f}) but OCR found no text - likely false positive")
                    has_subtitles = False
            elif extract_text and has_subtitles and not OCR_AVAILABLE:
                # If OCR is not available but we want text extraction, we can't verify subtitles
                print(f"VideoContent[{self.device_name}]: OCR not available - cannot verify subtitle text")
                # Keep has_subtitles as True since we detected edges but can't verify text
            
            # Calculate confidence based on actual findings
            if has_subtitles and extracted_text:
                confidence = 0.9  # High confidence when we have both edges and text
            elif has_subtitles and not extract_text:
                confidence = 0.7  # Medium confidence when we have edges but didn't try OCR
            elif has_errors:
                confidence = 0.8  # High confidence for error detection
            elif subtitle_edges > adaptive_threshold and not extracted_text and extract_text:
                confidence = 0.2  # Low confidence when edges detected but no text found (likely false positive)
            else:
                confidence = 0.1  # Low confidence when nothing detected
            
            return {
                'has_subtitles': has_subtitles,
                'has_errors': has_errors,
                'subtitle_edges': int(subtitle_edges),
                'subtitle_threshold': float(adaptive_threshold),
                'red_percentage': round(red_percentage, 2),
                'error_threshold': 8.0,
                'extracted_text': extracted_text,
                'detected_language': detected_language,
                'subtitle_region_size': f"{subtitle_region.shape[1]}x{subtitle_region.shape[0]}",
                'image_size': f"{width}x{height}",
                'confidence': confidence,
                'ocr_available': OCR_AVAILABLE
            }
            
        except Exception as e:
            print(f"VideoContent[{self.device_name}]: Subtitle region analysis error: {e}")
            return {
                'has_subtitles': False,
                'has_errors': False,
                'error': str(e),
                'confidence': 0.0
            }

    def detect_subtitles_batch(self, image_paths: List[str], extract_text: bool = True) -> Dict[str, Any]:
        """
        Detect subtitles and error messages in multiple images.
        
        Args:
            image_paths: List of image paths to analyze
            extract_text: Whether to extract text using OCR
            
        Returns:
            Dictionary with subtitle analysis results
        """
        results = []
        
        for image_path in image_paths:
            if not os.path.exists(image_path):
                results.append({
                    'image_path': image_path,
                    'success': False,
                    'error': 'Image file not found'
                })
                continue
            
            try:
                img = cv2.imread(image_path)
                if img is None:
                    results.append({
                        'image_path': image_path,
                        'success': False,
                        'error': 'Could not load image'
                    })
                    continue
                
                # Analyze subtitle region
                analysis = self.analyze_subtitle_region(img, extract_text)
                analysis['image_path'] = os.path.basename(image_path)
                analysis['success'] = True
                
                results.append(analysis)
                
                text_preview = analysis.get('extracted_text', '')[:50]
                if len(analysis.get('extracted_text', '')) > 50:
                    text_preview += "..."
                print(f"VideoContent[{self.device_name}]: Subtitle analysis - edges={analysis.get('subtitle_edges', 0)}, subtitles={analysis.get('has_subtitles', False)}, errors={analysis.get('has_errors', False)}, text='{text_preview}', confidence={analysis.get('confidence', 0)}")
                
            except Exception as e:
                results.append({
                    'image_path': image_path,
                    'success': False,
                    'error': f'Analysis error: {str(e)}'
                })
        
        # Calculate overall result
        successful_analyses = [r for r in results if r.get('success')]
        subtitles_detected = any(r.get('has_subtitles', False) for r in successful_analyses)
        errors_detected = any(r.get('has_errors', False) for r in successful_analyses)
        
        # Combine all extracted text and find the most confident language detection
        all_extracted_text = " ".join([r.get('extracted_text', '') for r in successful_analyses if r.get('extracted_text')])
        
        # Get the language from the result with highest confidence and subtitles detected
        detected_language = 'unknown'
        for result in successful_analyses:
            if result.get('has_subtitles') and result.get('detected_language') != 'unknown':
                detected_language = result.get('detected_language')
                break
        
        overall_result = {
            'success': len(successful_analyses) > 0,
            'subtitles_detected': subtitles_detected,
            'errors_detected': errors_detected,
            'analyzed_images': len(results),
            'successful_analyses': len(successful_analyses),
            'combined_extracted_text': all_extracted_text.strip(),
            'detected_language': detected_language,
            'results': results,
            'analysis_type': 'subtitle_detection',
            'timestamp': datetime.now().isoformat()
        }
        
        return overall_result

    # =============================================================================
    # Text Extraction and Language Detection
    # =============================================================================
    
    def extract_text_from_region(self, region_image) -> str:
        """Extract text from subtitle region using OCR"""
        if not OCR_AVAILABLE:
            return ''
        
        try:
            # Convert to grayscale for better OCR
            gray_region = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
            
            # Enhance contrast for better text recognition
            enhanced = cv2.convertScaleAbs(gray_region, alpha=2.0, beta=0)
            
            # Apply threshold to get better text
            _, thresh = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(thresh, config='--psm 6')
            text = text.strip()
            
            # Basic text validation
            if len(text) < 3:
                return ''
            
            # Clean and filter the text for better language detection
            cleaned_text = self.clean_ocr_text(text)
            
            # Return cleaned text if it has meaningful content
            if len(cleaned_text) >= 3:
                return cleaned_text
            else:
                # If cleaned text is too short, return original for display but it won't be good for language detection
                return text
            
        except Exception as e:
            print(f"VideoContent[{self.device_name}]: Text extraction error: {e}")
            return ''

    def clean_ocr_text(self, text: str) -> str:
        """Clean OCR text by removing noise and keeping only meaningful words"""
        if not text:
            return ''
        
        # Remove newlines and extra whitespace
        text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
        
        # Split into words and filter out noise
        words = text.split()
        cleaned_words = []
        
        for word in words:
            # Remove common OCR noise patterns
            cleaned_word = re.sub(r'[^\w\s\'-]', '', word)  # Keep letters, numbers, apostrophes, hyphens
            cleaned_word = cleaned_word.strip()
            
            # Keep words that are:
            # - At least 2 characters long
            # - Contain at least one letter
            # - Are not just numbers or symbols
            if (len(cleaned_word) >= 2 and 
                re.search(r'[a-zA-ZÀ-ÿ]', cleaned_word) and  # Contains letters (including accented)
                not cleaned_word.isdigit()):  # Not just numbers
                cleaned_words.append(cleaned_word)
        
        return ' '.join(cleaned_words)

    def detect_language(self, text: str) -> str:
        """Detect language of extracted text"""
        if not LANG_DETECT_AVAILABLE or not text:
            return 'unknown'
        
        try:
            # Clean the text for better language detection
            cleaned_text = self.clean_ocr_text(text)
            
            # Use cleaned text for detection, but fall back to original if cleaning removed too much
            detection_text = cleaned_text if len(cleaned_text) >= 6 else text
            
            # Check word count - need at least 3 meaningful words for detection
            words = detection_text.split()
            if len(words) < 3:
                return 'unknown'
            
            print(f"VideoContent[{self.device_name}]: Language detection - original: '{text[:50]}...', cleaned: '{detection_text[:50]}...', words: {len(words)}")
            
            # Detect language
            detected_lang = detect(detection_text)
            
            # Only allow specific languages - map to full names
            allowed_languages = {
                'en': 'English',
                'fr': 'French', 
                'de': 'German',
                'it': 'Italian',
                'es': 'Spanish',
                'pt': 'Portuguese',
                'nl': 'Dutch'
            }
            
            result = allowed_languages.get(detected_lang, 'unknown')
            print(f"VideoContent[{self.device_name}]: Language detected: {detected_lang} -> {result}")
            
            return result
            
        except (LangDetectException, Exception) as e:
            print(f"VideoContent[{self.device_name}]: Language detection error: {e}")
            return 'unknown'

    # =============================================================================
    # Motion Analysis from JSON Files
    # =============================================================================
    
    def detect_motion_from_json_analysis(self, device_id: str, json_count: int = 5, strict_mode: bool = True) -> Dict[str, Any]:
        """
        Helper method to detect motion/activity from JSON analysis files.
        Uses shared analysis utility to avoid code duplication.
        
        Args:
            device_id: Device ID to analyze (instead of direct folder path)
            json_count: Number of recent JSON files to analyze (default: 5)
            strict_mode: If True, ALL files must show no errors. If False, majority must show no errors (default: True)
            
        Returns:
            Dict with detailed analysis similar to controller methods
        """
        try:
            # Import shared analysis utility
            from shared.lib.utils.analysis_utils import load_recent_analysis_data, analyze_motion_from_loaded_data
            
            # Load recent analysis data using shared utility (5 minutes timeframe)
            data_result = load_recent_analysis_data(device_id, timeframe_minutes=5, max_count=json_count)
            
            if not data_result['success']:
                return {
                    'success': False,
                    'video_ok': False,
                    'audio_ok': False,
                    'blackscreen_count': 0,
                    'freeze_count': 0,
                    'audio_loss_count': 0,
                    'total_analyzed': 0,
                    'details': [],
                    'strict_mode': strict_mode,
                    'message': data_result.get('error', 'Failed to load analysis data')
                }
            
            # Analyze motion from loaded data using shared utility
            result = analyze_motion_from_loaded_data(data_result['analysis_data'], json_count, strict_mode)
            
            print(f"VideoContent[{self.device_name}]: Motion detection result: {result.get('message', 'Unknown')}")
            return result
            
        except Exception as e:
            error_msg = f"Motion detection from JSON error: {e}"
            print(f"VideoContent[{self.device_name}]: {error_msg}")
            return {
                'success': False,
                'video_ok': False,
                'audio_ok': False,
                'blackscreen_count': 0,
                'freeze_count': 0,
                'audio_loss_count': 0,
                'total_analyzed': 0,
                'details': [],
                'strict_mode': strict_mode,
                'message': error_msg
            }