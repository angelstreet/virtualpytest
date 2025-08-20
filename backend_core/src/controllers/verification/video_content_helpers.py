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
        
        # Initialize AI helpers for channel analysis
        from .video_ai_helpers import VideoAIHelpers
        self.ai_helpers = VideoAIHelpers(av_controller, device_name)
    
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
            
            # If more than 80% of pixels are very dark, it's a blackscreen
            is_blackscreen = bool(dark_percentage > 80)
            
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
            subtitle_height_start = int(height * 0.62)
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
                has_subtitles = False
            
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
    
    def detect_motion_from_json_analysis(self, capture_path: str, json_count: int = 5, strict_mode: bool = True) -> Dict[str, Any]:
        """
        Helper method to detect motion/activity from JSON analysis files.
        Uses shared analysis utility to avoid code duplication.
        
        Args:
            capture_path: Direct path to the capture folder containing analysis files
            json_count: Number of recent JSON files to analyze (default: 5)
            strict_mode: If True, ALL files must show no errors. If False, majority must show no errors (default: True)
            
        Returns:
            Dict with detailed analysis similar to controller methods
        """
        try:
            # Import shared analysis utility
            from shared.lib.utils.analysis_utils import load_recent_analysis_data_from_path, analyze_motion_from_loaded_data
            
            # Load recent analysis data using direct capture path (5 minutes timeframe)
            data_result = load_recent_analysis_data_from_path(capture_path, timeframe_minutes=5, max_count=json_count)
            
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

    # =============================================================================
    # Zapping Detection
    # =============================================================================
    
    def detect_zapping_sequence(self, folder_path: str, key_release_timestamp: float, 
                               analysis_rectangle: Dict[str, int] = None, max_images: int = 10, 
                               banner_region: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Simple zapping detection using existing components and direct file access.
        
        Args:
            folder_path: Path to folder containing captured images
            key_release_timestamp: Timestamp when zapping key was released (Unix timestamp)
            analysis_rectangle: Rectangle to analyze for blackscreen (exclude banner area)
            max_images: Maximum number of images to analyze (default: 10)
            
        Returns:
            Dictionary with zapping analysis results
        """
        try:
            print(f"VideoContent[{self.device_name}]: Starting simple zapping detection in {folder_path}")
            
            # Convert Unix timestamp to capture format for display consistency
            capture_format_timestamp = self._convert_unix_to_capture_format(key_release_timestamp)
            print(f"VideoContent[{self.device_name}]: Key release timestamp: {capture_format_timestamp} (Unix: {key_release_timestamp})")
            
            # Step 1: Get images after timestamp using direct file scanning
            image_data = self._get_images_after_timestamp(folder_path, key_release_timestamp, max_images)
            
            if not image_data:
                return {
                    'success': False,
                    'error': 'No images found after key release timestamp',
                    'zapping_detected': False,
                    'blackscreen_duration': 0.0,
                    'debug_images': [],  # No images to debug
                    'analysis_type': 'simple_zapping_detection'
                }
            
            print(f"VideoContent[{self.device_name}]: Found {len(image_data)} images to analyze")
            
            # Step 2: Batch blackscreen detection using proven algorithm
            blackscreen_results = self._detect_blackscreen_batch(image_data, analysis_rectangle)
            
            # Step 3: Find blackscreen sequence
            sequence = self._find_blackscreen_sequence(blackscreen_results)
            
            # Step 4: Calculate durations (both blackscreen and zapping)
            blackscreen_duration = 0.0
            zapping_duration = 0.0
            
            if sequence['zapping_detected']:
                # Zapping duration: from first image (action completion) to blackscreen disappearance
                first_image_time = image_data[0]['timestamp']
                
                if sequence.get('single_image_case', False):
                    # Single blackscreen image case (fast zapping under 2s)
                    # Assume 1-second blackscreen duration as specified
                    blackscreen_duration = 1.0
                    blackscreen_start_time = image_data[sequence['blackscreen_start_index']]['timestamp']
                    
                    # If blackscreen appears before our action timestamp, start zapping 1s before blackscreen
                    if blackscreen_start_time < key_release_timestamp:
                        adjusted_zapping_start = blackscreen_start_time - 1.0
                        zapping_duration = (blackscreen_start_time + blackscreen_duration) - adjusted_zapping_start
                    else:
                        time_to_blackscreen = blackscreen_start_time - first_image_time
                        zapping_duration = time_to_blackscreen + blackscreen_duration
                    print(f"VideoContent[{self.device_name}]: Single image case - assumed 1s blackscreen, total zapping: {zapping_duration:.1f}s")
                    
                elif sequence['blackscreen_end_index'] is not None:
                    # Normal case: blackscreen ended - zapping duration is from start to blackscreen end
                    blackscreen_end_time = image_data[sequence['blackscreen_end_index']]['timestamp']
                    
                    # If blackscreen appears before our action timestamp, adjust zapping start time
                    if sequence['blackscreen_start_index'] is not None:
                        blackscreen_start_time = image_data[sequence['blackscreen_start_index']]['timestamp']
                        if blackscreen_start_time < key_release_timestamp:
                            # Blackscreen detected before action timestamp - start zapping 1s before blackscreen
                            adjusted_zapping_start = blackscreen_start_time - 1.0
                            zapping_duration = blackscreen_end_time - adjusted_zapping_start
                        else:
                            zapping_duration = blackscreen_end_time - first_image_time
                        
                        # Blackscreen duration: from blackscreen start to blackscreen end
                        blackscreen_duration = blackscreen_end_time - blackscreen_start_time
                    else:
                        zapping_duration = blackscreen_end_time - first_image_time
                else:
                    # Blackscreen didn't end in our window - use last image
                    last_image_time = image_data[-1]['timestamp']
                    zapping_duration = last_image_time - first_image_time
                    
                    if sequence['blackscreen_start_index'] is not None:
                        blackscreen_start_time = image_data[sequence['blackscreen_start_index']]['timestamp']
                        blackscreen_duration = last_image_time - blackscreen_start_time
            
            # Step 5: Extract channel information using AI (if blackscreen ended)
            channel_info = {
                'channel_name': '',
                'channel_number': '',
                'program_name': '',
                'start_time': '',
                'end_time': '',
                'confidence': 0.0
            }
            
            # Try AI analysis if we have blackscreen end OR single image case
            if sequence['zapping_detected']:
                if sequence.get('single_image_case', False):
                    # For single image case, try to extract channel info from images after the blackscreen image
                    blackscreen_index = sequence['blackscreen_start_index']
                    if blackscreen_index < len(image_data) - 1:
                        print(f"VideoContent[{self.device_name}]: Single image case - analyzing images after blackscreen for channel info")
                        channel_info = self._extract_channel_info_from_images(
                            image_data, blackscreen_index + 1, banner_region
                        )
                elif (sequence['blackscreen_end_index'] is not None and 
                      sequence['blackscreen_end_index'] < len(image_data) - 1):
                    # Normal case: analyze images after blackscreen ends
                    channel_info = self._extract_channel_info_from_images(
                        image_data, sequence['blackscreen_end_index'], banner_region
                    )
            
            # Compile complete results with all information
            overall_result = {
                # Core zapping detection results
                'success': True,
                'zapping_detected': sequence['zapping_detected'],
                
                # Duration information
                'zapping_duration': round(zapping_duration, 2),          # Total time from action to blackscreen end
                'blackscreen_duration': round(blackscreen_duration, 2), # Time blackscreen was visible
                
                # Channel information
                'channel_name': channel_info.get('channel_name', ''),
                'channel_number': channel_info.get('channel_number', ''),
                'program_name': channel_info.get('program_name', ''),
                'program_start_time': channel_info.get('start_time', ''),
                'program_end_time': channel_info.get('end_time', ''),
                'channel_confidence': channel_info.get('confidence', 0.0),
                
                # Image sequence information
                'first_image': image_data[0]['filename'] if image_data else None,
                'blackscreen_start_image': image_data[sequence['blackscreen_start_index']]['filename'] if sequence.get('blackscreen_start_index') is not None else None,
                'blackscreen_end_image': self._get_blackscreen_end_image(image_data, sequence),
                'first_content_after_blackscreen': self._get_first_content_after_blackscreen(image_data, sequence),
                'last_image': image_data[-1]['filename'] if image_data else None,
                
                # Debug images for analysis (all analyzed images for debugging)
                'debug_images': [result['filename'] for result in blackscreen_results],
                
                # Analysis metadata
                'analyzed_images': len(blackscreen_results),
                'total_images_available': len(image_data),
                'key_release_timestamp': key_release_timestamp,
                'analysis_rectangle': analysis_rectangle,
                
                # Detailed results for debugging
                'details': {
                    'images_analyzed': [result['filename'] for result in blackscreen_results],
                    'blackscreen_percentages': [result.get('blackscreen_percentage', 0) for result in blackscreen_results],
                    'blackscreen_sequence': {
                        'start_index': sequence['blackscreen_start_index'],
                        'end_index': sequence['blackscreen_end_index']
                    },
                    'timestamps': {
                        'first_image': image_data[0]['timestamp'] if image_data else None,
                        'blackscreen_start': image_data[sequence['blackscreen_start_index']]['timestamp'] if sequence.get('blackscreen_start_index') is not None else None,
                        'blackscreen_end': image_data[sequence['blackscreen_end_index']]['timestamp'] if sequence.get('blackscreen_end_index') is not None else None,
                        'last_image': image_data[-1]['timestamp'] if image_data else None
                    },
                    'channel_analysis': channel_info,
                    'blackscreen_results': blackscreen_results
                },
                'analysis_type': 'simple_zapping_detection',
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"VideoContent[{self.device_name}]: Simple zapping detection complete - detected={sequence['zapping_detected']}, duration={blackscreen_duration}s")
            return overall_result
            
        except Exception as e:
            print(f"VideoContent[{self.device_name}]: Simple zapping detection error: {e}")
            
            # Try to get debug images even if analysis failed
            debug_images = []
            try:
                if 'image_data' in locals() and image_data:
                    debug_images = [img['filename'] for img in image_data]
                elif 'blackscreen_results' in locals() and blackscreen_results:
                    debug_images = [result['filename'] for result in blackscreen_results]
            except:
                pass  # If we can't get debug images, just use empty list
            
            return {
                'success': False,
                'error': f'Simple zapping detection failed: {str(e)}',
                'analysis_type': 'simple_zapping_detection',
                'zapping_detected': False,
                'blackscreen_duration': 0.0,
                'debug_images': debug_images
            }

    def _get_images_after_timestamp(self, folder_path: str, start_timestamp: float, max_count: int = 10) -> List[Dict]:
        """
        Simple approach: Get images by incrementing timestamp by 1 second to get next 10 images.
        
        Args:
            folder_path: Path to main folder (we'll add /captures)
            start_timestamp: Start timestamp (Unix timestamp)
            max_count: Maximum number of images to return (default: 10)
            
        Returns:
            List of image data dictionaries
        """
        try:
            # Images are in the captures subfolder
            captures_folder = os.path.join(folder_path, 'captures')
            
            if not os.path.exists(captures_folder):
                print(f"VideoContent[{self.device_name}]: Captures folder not found: {captures_folder}")
                return []
            
            images = []
            
            # Simple plan: Start from action timestamp and increment by 1 second to get 10 images
            for i in range(max_count):
                # Calculate timestamp for this second (start + i seconds)
                target_timestamp = start_timestamp + i
                
                # Convert to capture filename format: capture_YYYYMMDDHHMMSS.jpg
                target_datetime = datetime.fromtimestamp(target_timestamp)
                target_filename = f"capture_{target_datetime.strftime('%Y%m%d%H%M%S')}.jpg"
                target_path = os.path.join(captures_folder, target_filename)
                
                # Check if this image exists
                if os.path.exists(target_path):
                    images.append({
                        'path': target_path,
                        'timestamp': target_timestamp,
                        'filename': target_filename
                    })
                    print(f"VideoContent[{self.device_name}]: Found image {target_filename}")
                else:
                    print(f"VideoContent[{self.device_name}]: Missing image {target_filename}")
            
            print(f"VideoContent[{self.device_name}]: Found {len(images)} images starting from timestamp")
            return images
            
        except Exception as e:
            print(f"VideoContent[{self.device_name}]: Error getting images: {e}")
            return []

    def _convert_unix_to_capture_format(self, unix_timestamp: float) -> str:
        """
        Convert Unix timestamp to capture filename format: YYYYMMDDHHMMSS
        
        Args:
            unix_timestamp: Unix timestamp (float)
            
        Returns:
            Timestamp string in YYYYMMDDHHMMSS format
        """
        try:
            dt = datetime.fromtimestamp(unix_timestamp)
            return dt.strftime('%Y%m%d%H%M%S')
        except (ValueError, OSError) as e:
            print(f"VideoContent[{self.device_name}]: Failed to convert timestamp {unix_timestamp}: {e}")
            return ""

    def _detect_blackscreen_batch(self, image_data: List[Dict], analysis_rectangle: Dict[str, int] = None) -> List[Dict]:
        """
        Batch blackscreen detection using proven algorithm from analyze_audio_video.py
        
        Args:
            image_data: List of image data dictionaries
            analysis_rectangle: Optional rectangle to analyze (exclude banner area)
            
        Returns:
            List of blackscreen analysis results
        """
        results = []
        
        for img_data in image_data:
            image_path = img_data['path']
            
            try:
                # Use proven blackscreen detection algorithm (copied from analyze_audio_video.py)
                is_blackscreen, blackscreen_percentage = self._analyze_blackscreen_simple(image_path, analysis_rectangle)
                
                results.append({
                    'path': image_path,
                    'filename': img_data['filename'],
                    'timestamp': img_data['timestamp'],
                    'is_blackscreen': is_blackscreen,
                    'blackscreen_percentage': blackscreen_percentage,
                    'success': True
                })
                
                print(f"VideoContent[{self.device_name}]: {img_data['filename']} - blackscreen={is_blackscreen} ({blackscreen_percentage:.1f}%)")
                
            except Exception as e:
                print(f"VideoContent[{self.device_name}]: Failed to analyze {img_data['filename']}: {e}")
                results.append({
                    'path': image_path,
                    'filename': img_data['filename'],
                    'timestamp': img_data['timestamp'],
                    'is_blackscreen': False,
                    'blackscreen_percentage': 0.0,
                    'success': False,
                    'error': str(e)
                })
        
        return results

    def _analyze_blackscreen_simple(self, image_path: str, analysis_rectangle: Dict[str, int] = None, threshold: int = 30) -> Tuple[bool, float]:
        """
        Simple blackscreen detection optimized for mobile TV interfaces
        
        Args:
            image_path: Path to image file
            analysis_rectangle: Optional rectangle to analyze
            threshold: Pixel intensity threshold (0-255, default: 30 for mobile)
            
        Returns:
            Tuple of (is_blackscreen, blackscreen_percentage)
        """
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False, 0.0
            
            # Crop to analysis rectangle if specified (to exclude banner area)
            if analysis_rectangle:
                x = analysis_rectangle.get('x', 0)
                y = analysis_rectangle.get('y', 0)
                width = analysis_rectangle.get('width', img.shape[1])
                height = analysis_rectangle.get('height', img.shape[0])
                
                # Validate rectangle bounds
                img_height, img_width = img.shape
                if x < 0 or y < 0 or x + width > img_width or y + height > img_height:
                    print(f"VideoContent[{self.device_name}]: Analysis rectangle out of bounds, using full image")
                else:
                    img = img[y:y+height, x:x+width]
            
            # Count pixels <= threshold (optimized for mobile TV)
            very_dark_pixels = np.sum(img <= threshold)
            total_pixels = img.shape[0] * img.shape[1]
            dark_percentage = (very_dark_pixels / total_pixels) * 100
            
            # Mobile TV interfaces need lower threshold (85-90% instead of 95%)
            is_blackscreen = dark_percentage > 85
            
            return is_blackscreen, dark_percentage
            
        except Exception as e:
            print(f"VideoContent[{self.device_name}]: Blackscreen analysis error: {e}")
            return False, 0.0

    def _find_blackscreen_sequence(self, blackscreen_results: List[Dict]) -> Dict[str, Any]:
        """
        Find blackscreen start and end in the sequence of results.
        Handles both full sequences and single blackscreen images (fast zapping).
        
        Args:
            blackscreen_results: List of blackscreen analysis results
            
        Returns:
            Dictionary with sequence information
        """
        blackscreen_start_index = None
        blackscreen_end_index = None
        blackscreen_images = []
        
        # First pass: identify all blackscreen images
        for i, result in enumerate(blackscreen_results):
            if result.get('success', False) and result.get('is_blackscreen', False):
                blackscreen_images.append(i)
        
        if not blackscreen_images:
            # No blackscreen detected
            return {
                'blackscreen_start_index': None,
                'blackscreen_end_index': None,
                'zapping_detected': False,
                'single_image_case': False
            }
        
        # Find sequence boundaries
        blackscreen_start_index = blackscreen_images[0]
        print(f"VideoContent[{self.device_name}]: Blackscreen started at {blackscreen_results[blackscreen_start_index]['filename']}")
        
        # Look for blackscreen end (first non-blackscreen after start)
        for i in range(blackscreen_start_index + 1, len(blackscreen_results)):
            result = blackscreen_results[i]
            if result.get('success', False) and not result.get('is_blackscreen', False):
                blackscreen_end_index = i
                print(f"VideoContent[{self.device_name}]: Blackscreen ended at {result['filename']}")
                break
        
        # Handle single blackscreen image case (fast zapping under 2s)
        single_image_case = len(blackscreen_images) == 1 and blackscreen_end_index is None
        if single_image_case:
            print(f"VideoContent[{self.device_name}]: Single blackscreen image detected - assuming fast zapping (1s duration)")
        
        zapping_detected = blackscreen_start_index is not None
        
        return {
            'blackscreen_start_index': blackscreen_start_index,
            'blackscreen_end_index': blackscreen_end_index,
            'zapping_detected': zapping_detected,
            'single_image_case': single_image_case
        }

    def _get_blackscreen_end_image(self, image_data: List[Dict], sequence: Dict[str, Any]) -> Optional[str]:
        """Get the last blackscreen image filename (the actual last black frame)."""
        if sequence.get('single_image_case', False):
            # For single blackscreen image, end image is the same as start image
            start_index = sequence.get('blackscreen_start_index')
            if start_index is not None and start_index < len(image_data):
                return image_data[start_index]['filename']
        else:
            # Normal case: blackscreen_end_index points to first content, so last black is end_index - 1
            end_index = sequence.get('blackscreen_end_index')
            if end_index is not None and end_index > 0:
                return image_data[end_index - 1]['filename']
        return None

    def _get_first_content_after_blackscreen(self, image_data: List[Dict], sequence: Dict[str, Any]) -> Optional[str]:
        """Get the first content image after blackscreen, handling single image case."""
        if sequence.get('single_image_case', False):
            # For single blackscreen image, first content is the next image after the blackscreen
            start_index = sequence.get('blackscreen_start_index')
            if start_index is not None and start_index + 1 < len(image_data):
                return image_data[start_index + 1]['filename']
        else:
            # Normal case: blackscreen_end_index already points to the first content image
            end_index = sequence.get('blackscreen_end_index')
            if end_index is not None and end_index < len(image_data):
                return image_data[end_index]['filename']
        return None

    def _extract_channel_info_from_images(self, image_data: List[Dict], blackscreen_end_index: int, 
                                         banner_region: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Extract channel information from images after blackscreen ends using AI analysis.
        
        Args:
            image_data: List of image data dictionaries
            blackscreen_end_index: Index where blackscreen ended
            banner_region: Hardcoded banner region passed from zap_controller
            
        Returns:
            Dictionary with channel information
        """
        try:
            # Use the passed banner region from zap_controller (now properly hardcoded per device type)
            if not banner_region:
                print(f"VideoContent[{self.device_name}]: No banner region provided, skipping channel analysis")
                return {
                    'channel_name': '',
                    'channel_number': '',
                    'program_name': '',
                    'start_time': '',
                    'end_time': '',
                    'confidence': 0.0
                }
            
            print(f"VideoContent[{self.device_name}]: Using banner region: {banner_region}")
            
            # Try to extract channel info from images AFTER blackscreen ends
            # Banner might take a few seconds to appear, so try multiple images
            # Start from blackscreen_end_index + 1 to skip the blackscreen end image itself
            start_index = blackscreen_end_index + 1
            max_attempts = min(3, len(image_data) - start_index)
            
            for i in range(max_attempts):
                image_index = start_index + i
                if image_index >= len(image_data):
                    break
                
                image_path = image_data[image_index]['path']
                filename = image_data[image_index]['filename']
                
                print(f"VideoContent[{self.device_name}]: Trying AI analysis on {filename} for channel info (image {i+1} after blackscreen)")
                print(f"VideoContent[{self.device_name}]: Using banner region: {banner_region}")
                
                # Use AI helper for channel banner analysis with cropped region first
                channel_result = self.ai_helpers.analyze_channel_banner_ai(image_path, banner_region)
                print(f"VideoContent[{self.device_name}]: AI analysis result: {channel_result}")
                
                # If banner region analysis fails, try with full image as fallback
                if not (channel_result.get('success', False) and channel_result.get('banner_detected', False)):
                    print(f"VideoContent[{self.device_name}]: Banner region analysis failed, trying full image analysis on {filename}")
                    full_image_result = self.ai_helpers.analyze_channel_banner_ai(image_path, None)
                    print(f"VideoContent[{self.device_name}]: Full image AI analysis result: {full_image_result}")
                    
                    # Use full image result if it has useful information (regardless of banner_detected flag)
                    if full_image_result.get('success', False):
                        full_info = full_image_result.get('channel_info', {})
                        full_has_useful_info = any([
                            full_info.get('channel_name'),
                            full_info.get('program_name'),
                            full_info.get('start_time'),
                            full_info.get('end_time')
                        ])
                        
                        if full_has_useful_info:
                            channel_result = full_image_result
                            print(f"VideoContent[{self.device_name}]: Using full image analysis result for {filename}")
                
                # Check if we have any useful channel information (regardless of banner_detected flag)
                if channel_result.get('success', False):
                    channel_info = channel_result.get('channel_info', {})
                    has_useful_info = any([
                        channel_info.get('channel_name'),
                        channel_info.get('program_name'),
                        channel_info.get('start_time'),
                        channel_info.get('end_time')
                    ])
                    
                    if has_useful_info:
                        banner_status = "detected" if channel_result.get('banner_detected', False) else "partial info found"
                        print(f"VideoContent[{self.device_name}]: Channel info {banner_status} from {filename}: {channel_info}")
                    
                    return {
                        'channel_name': channel_info.get('channel_name', ''),
                        'channel_number': channel_info.get('channel_number', ''),
                        'program_name': channel_info.get('program_name', ''),
                        'start_time': channel_info.get('start_time', ''),
                        'end_time': channel_info.get('end_time', ''),
                        'confidence': channel_result.get('confidence', 0.0),
                        'analyzed_image': filename,
                        'banner_region': banner_region
                    }
            
            print(f"VideoContent[{self.device_name}]: No channel information found in {max_attempts} images after blackscreen")
            return {
                'channel_name': '',
                'channel_number': '',
                'program_name': '',
                'start_time': '',
                'end_time': '',
                'confidence': 0.0,
                'analyzed_image': '',
                'banner_region': banner_region
            }
            
        except Exception as e:
            print(f"VideoContent[{self.device_name}]: Channel info extraction error: {e}")
            return {
                'channel_name': '',
                'channel_number': '',
                'program_name': '',
                'start_time': '',
                'end_time': '',
                'confidence': 0.0,
                'error': str(e)
            }



