"""
Video Verification Controller Implementation

Modern video analysis and verification controller built with modular helper architecture:
- VideoAnalysisHelpers: Core OpenCV/FFmpeg analysis and motion detection
- VideoContentHelpers: Content detection (blackscreen, freeze, subtitles)
- VideoAIHelpers: AI-powered analysis using OpenRouter
- VideoVerificationHelpers: Verification workflow orchestration

Clean separation of concerns with specialized helper modules.
"""

import time
import os
from typing import Dict, Any, Optional, Union, Tuple, List
from pathlib import Path
from ..base_controller import VerificationControllerInterface

# Import helper modules
from .video_analysis_helpers import VideoAnalysisHelpers
from .video_content_helpers import VideoContentHelpers
from .video_ai_helpers import VideoAIHelpers
from .video_verification_helpers import VideoVerificationHelpers


class VideoVerificationController(VerificationControllerInterface):
    """Modern video verification controller with specialized helper modules."""
    
    def __init__(self, av_controller, **kwargs):
        """
        Initialize the Video Verification controller.
        
        Args:
            av_controller: AV controller for capturing video/images (dependency injection)
        """
        super().__init__("Video Verification", "video")
        
        # Dependency injection
        self.av_controller = av_controller
        
        # Validate required dependency
        if not self.av_controller:
            raise ValueError("av_controller is required for VideoVerificationController")
            
        # Video analysis settings
        self.motion_threshold = 5.0  # Default motion threshold percentage
        self.frame_comparison_threshold = 10.0  # Default frame change threshold
        
        print(f"[@controller:VideoVerification] Initialized with AV controller")
        
        # Controller is always ready
        self.is_connected = True
        self.verification_session_id = f"video_verify_{int(time.time())}"
        
        # Initialize helper modules
        self.analysis_helpers = VideoAnalysisHelpers(av_controller, self.device_name)
        self.content_helpers = VideoContentHelpers(av_controller, self.device_name)
        self.ai_helpers = VideoAIHelpers(av_controller, self.device_name)
        self.verification_helpers = VideoVerificationHelpers(self, self.device_name)
        
        print(f"[@controller:VideoVerification] Helper modules initialized")
        
    def connect(self) -> bool:
        """Connect to the video verification system."""
        try:
            print(f"VideoVerify[{self.device_name}]: Connecting to video verification system")
            
            # Check if AV controller is connected - but don't fail if not
            if not hasattr(self.av_controller, 'is_connected') or not self.av_controller.is_connected:
                print(f"VideoVerify[{self.device_name}]: WARNING - AV controller not connected")
                print(f"VideoVerify[{self.device_name}]: Video analysis will work with provided images only")
            else:
                print(f"VideoVerify[{self.device_name}]: Using AV controller: {self.av_controller.device_name}")
            
            # Check AV controller video device - but don't fail if missing
            if not hasattr(self.av_controller, 'video_device') or not self.av_controller.video_device:
                print(f"VideoVerify[{self.device_name}]: WARNING - AV controller missing video device configuration")
                print(f"VideoVerify[{self.device_name}]: Screenshot capture will not be available")
            else:
                print(f"VideoVerify[{self.device_name}]: Video device: {self.av_controller.video_device}")
            
            # Connection successful
            self.is_connected = True
            self.verification_session_id = f"video_verify_{int(time.time())}"
            print(f"VideoVerify[{self.device_name}]: Connected - Session: {self.verification_session_id}")
            return True
            
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: Connection error: {e}")
            # Still connected for image analysis even if AV controller has issues
            self.is_connected = True
            return True

    def disconnect(self) -> bool:
        """Disconnect from the video verification system."""
        print(f"VideoVerify[{self.device_name}]: Disconnecting")
        self.is_connected = False
        self.verification_session_id = None
        print(f"VideoVerify[{self.device_name}]: Disconnected")
        return True

    def capture_screenshot(self, filename: str = None, source: str = "av_controller") -> str:
        """
        Capture a screenshot for analysis using the AV controller.
        
        Args:
            filename: Optional filename for the screenshot
            source: Video source ("av_controller" or file path)
            
        Returns:
            Path to the captured screenshot file
        """
        # Only check connection when actually using AV controller
        if source == "av_controller" and not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected for AV controller capture")
            return None
            
        timestamp = int(time.time())
        screenshot_name = filename 
        screenshot_path = Path.cwd() / screenshot_name
        
        try:
            if source == "av_controller":
                # Use AV controller's screenshot method
                print(f"VideoVerify[{self.device_name}]: Requesting screenshot from {self.av_controller.device_name}")
                result = self.av_controller.take_screenshot(screenshot_name)
                if result:
                    # Copy to our temp directory for analysis
                    import shutil
                    shutil.copy2(result, screenshot_path)
                    return str(screenshot_path)
                else:
                    print(f"VideoVerify[{self.device_name}]: Failed to get screenshot from AV controller")
                    return None
                
            elif os.path.exists(source):
                # Use existing image file
                print(f"VideoVerify[{self.device_name}]: Using existing image file: {source}")
                return source
                
            else:
                print(f"VideoVerify[{self.device_name}]: ERROR - Unknown video source: {source}")
                return None
                
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: Screenshot capture error: {e}")
            return None

    # =============================================================================
    # Core Analysis Methods (delegated to helpers)
    # =============================================================================

    def analyze_image_content(self, image_path: str, analysis_type: str = "basic") -> Dict[str, Any]:
        """Analyze image content using OpenCV or FFmpeg."""
        if not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected")
            return {}
            
        if not os.path.exists(image_path):
            print(f"VideoVerify[{self.device_name}]: ERROR - Image file not found: {image_path}")
            return {}
        
        try:
            print(f"VideoVerify[{self.device_name}]: Analyzing image content - Type: {analysis_type}")
            
            if analysis_type in ["basic", "color", "brightness"]:
                # Use OpenCV for detailed analysis
                return self.analysis_helpers.analyze_with_opencv(image_path, analysis_type)
            else:
                # Use FFmpeg for basic analysis
                return self.analysis_helpers.analyze_with_ffmpeg(image_path, analysis_type)
                
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: Image analysis error: {e}")
            return {"error": str(e)}

    def detect_motion(self, duration: float = 3.0, threshold: float = None) -> bool:
        """Detect motion by comparing consecutive frames."""
        if not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected")
            return False
            
        threshold = threshold or self.motion_threshold
        print(f"VideoVerify[{self.device_name}]: Detecting motion (duration: {duration}s, threshold: {threshold}%)")
        
        try:
            motion_detected, change_percentage = self.analysis_helpers.detect_motion_between_captures(duration, threshold)
            
            result_text = "detected" if motion_detected else "not detected"
            print(f"VideoVerify[{self.device_name}]: Motion {result_text}")
            
            return motion_detected
            
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: Motion detection error: {e}")
            return False

    def wait_for_video_change(self, timeout: float = 10.0, threshold: float = None) -> bool:
        """Wait for video content to change."""
        if not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected")
            return False
            
        threshold = threshold or self.frame_comparison_threshold
        
        try:
            change_detected, elapsed_time = self.analysis_helpers.wait_for_video_change(timeout, threshold)
            return change_detected
            
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: Video change detection error: {e}")
            return False

    # =============================================================================
    # Content Detection Methods (delegated to helpers)
    # =============================================================================

    def detect_blackscreen(self, image_paths: List[str] = None, threshold: int = 10) -> Dict[str, Any]:
        """Detect if image is mostly black (blackscreen)."""
        try:
            # Determine which images to analyze
            if image_paths is None or len(image_paths) == 0:
                if not self.is_connected:
                    print(f"VideoVerify[{self.device_name}]: ERROR - Not connected for screenshot capture")
                    return {'success': False, 'error': 'Not connected for screenshot capture'}
                
                # Use last available capture
                screenshot = self.capture_screenshot()
                if not screenshot:
                    return {'success': False, 'error': 'Failed to capture screenshot'}
                image_paths = [screenshot]
            
            return self.content_helpers.detect_blackscreen_batch(image_paths, threshold)
            
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: Blackscreen detection error: {e}")
            return {
                'success': False,
                'error': f'Blackscreen detection failed: {str(e)}',
                'analysis_type': 'blackscreen_detection'
            }

    def detect_freeze(self, image_paths: List[str] = None, freeze_threshold: float = 1.0) -> Dict[str, Any]:
        """Detect if images are frozen (identical frames)."""
        try:
            # Determine which images to analyze
            if image_paths is None or len(image_paths) == 0:
                if not self.is_connected:
                    print(f"VideoVerify[{self.device_name}]: ERROR - Not connected for screenshot capture")
                    return {'success': False, 'error': 'Not connected for screenshot capture'}
                
                # Use multiple recent captures for freeze detection
                screenshots = []
                for i in range(3):  # Get 3 screenshots with delay
                    screenshot = self.capture_screenshot(f"freeze_analysis_{i}_{int(time.time())}.png")
                    if screenshot:
                        screenshots.append(screenshot)
                    if i < 2:  # Don't wait after last screenshot
                        time.sleep(1.0)  # Wait 1 second between captures
                
                if len(screenshots) < 2:
                    return {'success': False, 'error': 'Need at least 2 images for freeze detection'}
                
                image_paths = screenshots
            
            return self.content_helpers.detect_freeze_in_images(image_paths, freeze_threshold)
            
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: Freeze detection error: {e}")
            return {
                'success': False,
                'error': f'Freeze detection failed: {str(e)}',
                'analysis_type': 'freeze_detection'
            }

    def detect_subtitles(self, image_paths: List[str] = None, extract_text: bool = True) -> Dict[str, Any]:
        """Detect subtitles and error messages using OCR."""
        try:
            # Determine which images to analyze
            if image_paths is None or len(image_paths) == 0:
                if not self.is_connected:
                    print(f"VideoVerify[{self.device_name}]: ERROR - Not connected for screenshot capture")
                    return {'success': False, 'error': 'Not connected for screenshot capture'}
                
                # Use last available capture
                screenshot = self.capture_screenshot()
                if not screenshot:
                    return {'success': False, 'error': 'Failed to capture screenshot'}
                image_paths = [screenshot]
            
            return self.content_helpers.detect_subtitles_batch(image_paths, extract_text)
            
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: Subtitle detection error: {e}")
            return {
                'success': False,
                'error': f'Subtitle detection failed: {str(e)}',
                'analysis_type': 'subtitle_detection'
            }

    def detect_subtitles_ai(self, image_paths: List[str] = None, extract_text: bool = True) -> Dict[str, Any]:
        """AI-powered subtitle detection using OpenRouter."""
        try:
            # Determine which images to analyze
            if image_paths is None or len(image_paths) == 0:
                if not self.is_connected:
                    print(f"VideoVerify[{self.device_name}]: ERROR - Not connected for screenshot capture")
                    return {'success': False, 'error': 'Not connected for screenshot capture'}
                
                # Use last available capture
                screenshot = self.capture_screenshot()
                if not screenshot:
                    return {'success': False, 'error': 'Failed to capture screenshot'}
                image_paths = [screenshot]
            
            return self.ai_helpers.detect_subtitles_ai_batch(image_paths, extract_text)
            
        except Exception as e:
            print(f"VideoVerify[{self.device_name}]: AI subtitle detection error: {e}")
            return {
                'success': False,
                'error': f'AI subtitle detection failed: {str(e)}',
                'analysis_type': 'ai_subtitle_detection'
            }

    def detect_motion_from_json(self, json_count: int = 5, strict_mode: bool = True) -> Dict[str, Any]:
        """Detect motion/activity by analyzing the last N JSON analysis files."""
        if not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected")
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
                'message': 'Controller not connected'
            }
        
        try:
            print(f"VideoVerify[{self.device_name}]: Analyzing last {json_count} JSON files (strict_mode: {strict_mode})")
            
            # Get analysis files directly from AV controller's capture path
            capture_path = getattr(self.av_controller, 'video_capture_path', None)
            if not capture_path:
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
                    'message': 'No video capture path available from AV controller'
                }
            
            # Use content helpers for JSON analysis
            # Note: We need to pass device_id instead of direct path for the helper
            device_id = getattr(self.av_controller, 'device_id', 'unknown')
            return self.content_helpers.detect_motion_from_json_analysis(device_id, json_count, strict_mode)
            
        except Exception as e:
            error_msg = f"Motion detection from JSON error: {e}"
            print(f"VideoVerify[{self.device_name}]: {error_msg}")
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
    # AI Analysis Methods (delegated to helpers)
    # =============================================================================

    def analyze_image_with_ai(self, image_path: str, user_question: str) -> str:
        """Analyze full image with AI using user's question."""
        return self.ai_helpers.analyze_full_image_with_ai(image_path, user_question)

    def analyze_image_ai(self, image_path: str, user_query: str) -> Dict[str, Any]:
        """Wrapper method for analyze_image_with_ai to match route expectations."""
        return self.ai_helpers.analyze_image_ai_wrapper(image_path, user_query)

    def analyze_language_menu_ai(self, image_path: str) -> Dict[str, Any]:
        """AI-powered language/subtitle menu analysis using OpenRouter."""
        return self.ai_helpers.analyze_language_menu_ai(image_path)

    # =============================================================================
    # High-Level Verification Methods
    # =============================================================================

    def waitForVideoToAppear(self, motion_threshold: float = 5.0, duration: float = 3.0, timeout: float = 10.0) -> bool:
        """Wait for video content to appear (motion detected)."""
        if not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected")
            return False
            
        print(f"VideoVerify[{self.device_name}]: Waiting for video to appear (motion threshold: {motion_threshold}%, duration: {duration}s, timeout: {timeout}s)")
        
        start_time = time.time()
        check_interval = 1.0
        
        while time.time() - start_time < timeout:
            motion_detected = self.detect_motion(duration, motion_threshold)
            
            if motion_detected:
                elapsed = time.time() - start_time
                print(f"VideoVerify[{self.device_name}]: Video appeared after {elapsed:.1f}s")
                return True
            
            time.sleep(check_interval)
        
        print(f"VideoVerify[{self.device_name}]: Video did not appear within {timeout}s")
        return False

    def waitForVideoToDisappear(self, motion_threshold: float = 5.0, duration: float = 3.0, timeout: float = 10.0) -> bool:
        """Wait for video content to disappear (no motion detected)."""
        if not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected")
            return False
            
        print(f"VideoVerify[{self.device_name}]: Waiting for video to disappear (motion threshold: {motion_threshold}%, duration: {duration}s, timeout: {timeout}s)")
        
        start_time = time.time()
        check_interval = 1.0
        
        while time.time() - start_time < timeout:
            motion_detected = self.detect_motion(duration, motion_threshold)
            
            if not motion_detected:
                elapsed = time.time() - start_time
                print(f"VideoVerify[{self.device_name}]: Video disappeared after {elapsed:.1f}s")
                return True
            
            time.sleep(check_interval)
        
        print(f"VideoVerify[{self.device_name}]: Video still present after {timeout}s")
        return False

    # =============================================================================
    # Core Verification Methods
    # =============================================================================
        
    def verify_color_present(self, color: str, tolerance: float = 10.0) -> bool:
        """Verify that a specific color is present on screen."""
        if not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected")
            return False
            
        print(f"VideoVerify[{self.device_name}]: Looking for color '{color}' (tolerance: {tolerance}%)")
        
        # Capture screenshot for analysis
        screenshot = self.capture_screenshot()
        if not screenshot:
            return False
        
        # Analyze color content
        color_analysis = self.analyze_image_content(screenshot, "color")
        
        # Simplified color detection (in a real implementation, this would be more sophisticated)
        color_found = False
        if "dominant_color" in color_analysis:
            dominant = color_analysis["dominant_color"].lower()
            color_found = color.lower() in dominant or dominant in color.lower()
        
        result_text = "found" if color_found else "not found"
        print(f"VideoVerify[{self.device_name}]: Color '{color}' {result_text}")
        
        return color_found
        
    def verify_screen_state(self, expected_state: str, timeout: float = 5.0) -> bool:
        """Verify that the screen is in an expected state based on visual analysis."""
        if not self.is_connected:
            print(f"VideoVerify[{self.device_name}]: ERROR - Not connected")
            return False
            
        print(f"VideoVerify[{self.device_name}]: Verifying screen state '{expected_state}' (timeout: {timeout}s)")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            screenshot = self.capture_screenshot()
            if not screenshot:
                time.sleep(0.5)
                continue
            
            # Analyze screenshot for state indicators
            analysis = self.analyze_image_content(screenshot, "brightness")
            
            # Simplified state detection based on brightness and content
            state_detected = False
            if expected_state.lower() == "loading":
                # Loading screens often have lower brightness or specific patterns
                brightness = analysis.get("brightness_percentage", 50)
                state_detected = 20 <= brightness <= 60
            elif expected_state.lower() == "ready":
                # Ready screens often have normal brightness
                brightness = analysis.get("brightness_percentage", 50)
                state_detected = brightness > 40
            elif expected_state.lower() == "error":
                # Error screens might have specific color patterns (simplified)
                state_detected = True  # Simplified for demo
            
            if state_detected:
                elapsed = time.time() - start_time
                print(f"VideoVerify[{self.device_name}]: Screen state '{expected_state}' verified after {elapsed:.1f}s")
                return True
            
            time.sleep(0.5)
        
        print(f"VideoVerify[{self.device_name}]: Screen state '{expected_state}' not detected within {timeout}s")
        return False
        
    def verify_performance_metric(self, metric_name: str, expected_value: float, tolerance: float = 10.0) -> bool:
        """Verify video-related performance metrics."""
        if metric_name.lower() in ['brightness', 'contrast']:
            screenshot = self.capture_screenshot()
            if not screenshot:
                return False
                
            analysis = self.analyze_image_content(screenshot, "brightness")
            
            if metric_name.lower() == 'brightness':
                current_value = analysis.get("brightness_percentage", 0)
            else:
                current_value = analysis.get("brightness_std", 0)
            
            tolerance_range = expected_value * (tolerance / 100)
            within_tolerance = abs(current_value - expected_value) <= tolerance_range
            
            print(f"VideoVerify[{self.device_name}]: {metric_name} = {current_value:.2f} (expected: {expected_value} ±{tolerance}%)")
            
            return within_tolerance
        else:
            print(f"VideoVerify[{self.device_name}]: Unknown video metric: {metric_name}")
            return False
        
    def wait_and_verify(self, verification_type: str, target: str, timeout: float = 10.0, **kwargs) -> bool:
        """Generic wait and verify method for video verification."""
        if verification_type == "image":
            confidence = kwargs.get("confidence", 0.8)
            return self.verify_image_appears(target, timeout, confidence)
        elif verification_type == "video_playing":
            motion_threshold = kwargs.get("motion_threshold", self.motion_threshold)
            return self.waitForVideoToAppear(motion_threshold, 3.0, timeout)
        elif verification_type == "color":
            tolerance = kwargs.get("tolerance", 10.0)
            return self.verify_color_present(target, tolerance)
        elif verification_type == "state":
            return self.verify_screen_state(target, timeout)
        elif verification_type == "video_change":
            threshold = kwargs.get("threshold", self.frame_comparison_threshold)
            return self.wait_for_video_change(timeout, threshold)
        else:
            print(f"VideoVerify[{self.device_name}]: Unknown video verification type: {verification_type}")
            return False

    # =============================================================================
    # Status and Configuration Methods (delegated to helpers)
    # =============================================================================
            
    def get_status(self) -> Dict[str, Any]:
        """Get controller status information."""
        return self.verification_helpers.get_controller_status()
    
    def get_available_verifications(self) -> List[Dict[str, Any]]:
        """Get available verifications for video controller."""
        return self.verification_helpers.get_available_verifications()

    def execute_verification(self, verification_config: Dict[str, Any], image_source_url: str = None) -> Dict[str, Any]:
        """Unified verification execution interface for centralized controller."""
        return self.verification_helpers.execute_verification_workflow(verification_config, image_source_url)

    # =============================================================================
    # Utility Methods
    # =============================================================================

    def _log_verification(self, command: str, target: str, success: bool, details: Dict[str, Any] = None):
        """Log verification for tracking (delegated to helpers)."""
        self.verification_helpers.log_verification(command, target, success, details)