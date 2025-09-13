"""
VirtualPyTest Controller Base Classes

to bMinimal base controller with only basic connection state.
Controllers implement their own specific functionality.
"""

from typing import Dict, Any, Optional, List
import time




class BaseController:
    """
    Minimal base controller with just connection state.
    Controllers implement their own specific methods as needed.
    """
    
    def __init__(self, controller_type: str, device_name: str = "Unknown Device"):
        self.controller_type = controller_type
        self.device_name = device_name
        self.is_connected = False
    
    def connect(self) -> bool:
        """Connect to the device/service. Optional - override if needed."""
        self.is_connected = True
        return True
    
    def disconnect(self) -> bool:
        """Disconnect from the device/service. Optional - override if needed."""
        self.is_connected = False
        return True


# Simplified interfaces for type hints only
# Controllers implement their own methods without forced inheritance

class RemoteControllerInterface(BaseController):
    """Type hint interface for remote controllers."""
    
    def __init__(self, device_name: str = "Unknown Device", device_type: str = "generic"):
        super().__init__("remote", device_name)
        self.device_type = device_type
    
    def execute_sequence(self, commands: List[Dict[str, Any]], retry_actions: List[Dict[str, Any]], failure_actions: List[Dict[str, Any]] = None) -> bool:
        """
        Execute a sequence of commands with optional retry actions.
        
        Args:
            commands: List of command dictionaries with 'command', 'params', and optional 'delay'
            retry_actions: Retry actions to execute if main commands fail (can be empty/None)
        """
        if not self.is_connected:
            print(f"Remote[{self.device_type.upper()}]: ERROR - Not connected to device")
            return False
            
        print(f"Remote[{self.device_type.upper()}]: Executing sequence of {len(commands)} commands")
        
        # Execute main commands
        main_success = True
        for i, cmd in enumerate(commands):
            command = cmd.get('command')
            params = cmd.get('params', {})
            delay = cmd.get('delay', 0)
            
            print(f"Remote[{self.device_type.upper()}]: Command {i+1}/{len(commands)}: {command}")
            
            # Execute command
            success = self.execute_command(command, params)
            
            if not success:
                print(f"Remote[{self.device_type.upper()}]: Command {i+1} failed: {command}")
                main_success = False
                break
                
            # Apply delay if specified
            if delay > 0:
                delay_seconds = delay / 1000.0
                print(f"Remote[{self.device_type.upper()}]: Waiting {delay_seconds}s after command {i+1}")
                time.sleep(delay_seconds)
        
        failure_actions = failure_actions or []
        
        # If main commands failed and retry actions provided, execute retry actions
        if not main_success and retry_actions:
            print(f"Remote[{self.device_type.upper()}]: Main commands failed, executing {len(retry_actions)} retry actions")
            
            # Stop on first retry failure
            retry_success = True  # Assume success until a retry fails
            for i, retry_cmd in enumerate(retry_actions):
                command = retry_cmd.get('command')
                params = retry_cmd.get('params', {})
                delay = retry_cmd.get('delay', 0)
                
                print(f"Remote[{self.device_type.upper()}]: Retry {i+1}/{len(retry_actions)}: {command}")
                
                # Execute retry command
                success = self.execute_command(command, params)
                
                if success:
                    print(f"Remote[{self.device_type.upper()}]: Retry {i+1} succeeded: {command}")
                else:
                    print(f"Remote[{self.device_type.upper()}]: Retry {i+1} failed: {command}")
                    retry_success = False
                    # Stop on first retry failure (default strict behavior)
                    break
                    
                # Apply delay if specified
                if delay > 0:
                    delay_seconds = delay / 1000.0
                    print(f"Remote[{self.device_type.upper()}]: Waiting {delay_seconds}s after retry {i+1}")
                    time.sleep(delay_seconds)
            
            # If retry actions also failed and failure actions provided, execute failure actions
            if not retry_success and failure_actions:
                print(f"Remote[{self.device_type.upper()}]: Retry actions failed, executing {len(failure_actions)} failure actions")
                
                failure_success = True  # Assume success until a failure action fails
                for i, failure_cmd in enumerate(failure_actions):
                    command = failure_cmd.get('command')
                    params = failure_cmd.get('params', {})
                    delay = failure_cmd.get('delay', 0)
                    
                    print(f"Remote[{self.device_type.upper()}]: Failure {i+1}/{len(failure_actions)}: {command}")
                    
                    # Execute failure command
                    success = self.execute_command(command, params)
                    
                    if success:
                        print(f"Remote[{self.device_type.upper()}]: Failure {i+1} succeeded: {command}")
                    else:
                        print(f"Remote[{self.device_type.upper()}]: Failure {i+1} failed: {command}")
                        failure_success = False
                        # Stop on first failure action failure
                        break
                        
                    # Apply delay if specified
                    if delay > 0:
                        delay_seconds = delay / 1000.0
                        print(f"Remote[{self.device_type.upper()}]: Waiting {delay_seconds}s after failure {i+1}")
                        time.sleep(delay_seconds)
                
                # Return True only if ALL failure actions succeeded
                return failure_success
            
            # Return True only if ALL retry actions succeeded
            return retry_success
        
        return main_success


class DesktopControllerInterface(BaseController):
    """Type hint interface for desktop controllers (bash, powershell, etc.)."""
    
    def __init__(self, device_name: str = "Unknown Device", desktop_type: str = "generic"):
        super().__init__("desktop", device_name)
        self.desktop_type = desktop_type
    
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a desktop command and return the result.
        
        Args:
            command: Command to execute
            params: Command parameters
            
        Returns:
            Dict with success, output, error, and exit_code
        """
        raise NotImplementedError("Desktop controllers must implement execute_command")


class WebControllerInterface(BaseController):
    """Type hint interface for web controllers (playwright, selenium, etc.)."""
    
    def __init__(self, device_name: str = "Unknown Device", web_type: str = "generic"):
        super().__init__("web", device_name)
        self.web_type = web_type
    
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """
        Execute a web automation command.
        
        Args:
            command: Command to execute
            params: Command parameters
            
        Returns:
            bool: True if command executed successfully
        """
        raise NotImplementedError("Web controllers must implement execute_command")


class AVControllerInterface(BaseController):
    """Type hint interface for AV controllers."""
    
    # Global configuration for video segments
    HLS_SEGMENT_DURATION = 1  # seconds per segment
    
    def __init__(self, device_name: str = "Unknown Device", capture_source: str = "HDMI"):
        super().__init__("av", device_name)
        self.capture_source = capture_source
    
    def take_video(self, duration_seconds: float = None, test_start_time: float = None) -> Optional[str]:
        """
        Upload HLS stream directly to R2 (no MP4 conversion).
        Fast upload with no processing time.
        
        Args:
            duration_seconds: How many seconds of video to capture (default: 10s)
            test_start_time: Unix timestamp when test started (for time sync)
            
        Returns:
            R2 URL of HLS playlist (m3u8), or None if failed
        """
        # Default implementation - override in concrete classes
        raise NotImplementedError("AV controllers must implement take_video")
    
    def start_video_capture(self, duration: float = 60.0, filename: str = None, 
                           resolution: str = None, fps: int = None) -> bool:
        """
        Start video capture by recording start time and duration.
        
        Args:
            duration: Duration in seconds (default: 60s)
            filename: Optional filename
            resolution: Video resolution
            fps: Video FPS
            
        Returns:
            bool: True if capture started successfully
        """
        # Default implementation - override in concrete classes
        raise NotImplementedError("AV controllers must implement start_video_capture")
    
    def stop_video_capture(self) -> bool:
        """Stop video capture session."""
        # Default implementation - override in concrete classes
        raise NotImplementedError("AV controllers must implement stop_video_capture")
    
    def take_screenshot(self, filename: str = None) -> Optional[str]:
        """
        Take screenshot and return local file path.
        
        Args:
            filename: Optional filename
            
        Returns:
            Local file path if successful, None if failed
        """
        # Default implementation - override in concrete classes
        raise NotImplementedError("AV controllers must implement take_screenshot")
    
    def save_screenshot(self, filename: str) -> Optional[str]:
        """
        Take screenshot and return local path for permanent storage.
        
        Args:
            filename: The filename to use for the screenshot
            
        Returns:
            Local file path if successful, None if failed
        """
        # Default implementation - override in concrete classes  
        raise NotImplementedError("AV controllers must implement save_screenshot")


class FFmpegCaptureController(AVControllerInterface):
    """
    Shared FFmpeg-based capture functionality for both HDMI and VNC controllers.
    Handles screenshot and video capture using the same host-side FFmpeg capture system.
    """
    
    def __init__(self, device_name: str, capture_source: str, video_stream_path: str, video_capture_path: str, **kwargs):
        """
        Initialize the FFmpeg capture controller.
        
        Args:
            device_name: Name of the device/controller
            capture_source: Source type (HDMI, VNC, etc.)
            video_stream_path: Stream path for URLs (e.g., "/host/stream/capture1")
            video_capture_path: Local capture path (e.g., "/var/www/html/stream/capture1")
        """
        super().__init__(device_name, capture_source)
        
        # Stream and capture paths
        self.video_stream_path = video_stream_path
        self.video_capture_path = video_capture_path
        
        # Video capture state (timestamp-based, no FFmpeg)
        self.is_capturing_video = False
        self.capture_start_time = None
        self.capture_duration = 0
        self.capture_session_id = None
        
        print(f"{capture_source}[{self.capture_source}]: Initialized - Stream: {self.video_stream_path}, Capture: {self.video_capture_path}")

    def take_screenshot(self, filename: str = None) -> Optional[str]:
        """
        Take screenshot using mtime-based lookup for sequential files.
        Returns local file path only - routes will build URLs using existing URL building functions.
        """
        try:
            import time
            import os
            
            print(f"{self.capture_source}[{self.capture_source}]: Starting take_screenshot process")
            print(f"{self.capture_source}[{self.capture_source}]: Video capture path: {self.video_capture_path}")
            
            # Check if capture path exists
            captures_path = os.path.join(self.video_capture_path, 'captures')
            if not os.path.exists(captures_path):
                print(f"{self.capture_source}[{self.capture_source}]: ERROR - Captures directory does not exist: {captures_path}")
                return None
            
            if not os.access(captures_path, os.R_OK):
                print(f"{self.capture_source}[{self.capture_source}]: ERROR - No read access to captures directory: {captures_path}")
                return None
            
            # Brief wait for FFmpeg to write the file
            time.sleep(0.5)
            
            # Find sequential capture files (not thumbnails)
            captures = [f for f in os.listdir(captures_path) if f.startswith('capture_') and f.endswith('.jpg') and '_thumbnail' not in f]
            if not captures:
                print(f"{self.capture_source}[{self.capture_source}]: ERROR - No capture files found in directory")
                return None
            
            # Find files with mtime within 2 seconds of now
            candidates = []
            now = time.time()
            for f in captures:
                path = os.path.join(captures_path, f)
                try:
                    mtime = os.path.getmtime(path)
                    age = now - mtime
                    if age <= 2:  # Within 2 seconds
                        candidates.append((age, path))
                        print(f"{self.capture_source}[{self.capture_source}]: Found candidate: {f} (age: {age:.1f}s)")
                except OSError:
                    continue  # File might have been deleted
            
            if not candidates:
                print(f"{self.capture_source}[{self.capture_source}]: ERROR - No recent files found (within 2s)")
                return None
            
            # Return the file with the smallest age (closest to now)
            candidates.sort()  # Sort by age (smallest first)
            closest_path = candidates[0][1]
            closest_age = candidates[0][0]
            
            print(f"{self.capture_source}[{self.capture_source}]: SUCCESS - Using closest file: {os.path.basename(closest_path)} (age: {closest_age:.1f}s)")
            return closest_path
                
        except Exception as e:
            print(f'{self.capture_source}[{self.capture_source}]: ERROR taking screenshot: {e}')
            import traceback
            print(f'{self.capture_source}[{self.capture_source}]: Traceback: {traceback.format_exc()}')
            return None
    
    def save_screenshot(self, filename: str) -> Optional[str]:
        """
        Take screenshot and return local path.
        Used for permanent storage in navigation nodes.
        The route should handle the R2 upload, not the controller.
        
        Args:
            filename: The filename to use for the screenshot (e.g., node name)
            
        Returns:
            Local file path if successful, None if failed
        """
        try:
            # First take a temporary screenshot to get the image
            temp_screenshot_path = self.take_screenshot()
            if not temp_screenshot_path:
                print(f'{self.capture_source}[{self.capture_source}]: Failed to take temporary screenshot')
                return None
            
            # The temp_screenshot_path is already the local file path we need (sequential naming)
            local_screenshot_path = temp_screenshot_path
            
            # Check if local file exists with retry for timing issues
            import os
            import time
            
            # First attempt
            if not os.path.exists(local_screenshot_path):
                time.sleep(1.0)
                # Retry once
                if not os.path.exists(local_screenshot_path):
                    print(f'{self.capture_source}[{self.capture_source}]: Local screenshot file not found after retry: {local_screenshot_path}')
                    return None
            
            # Return the local file path for the route to handle the upload
            return local_screenshot_path
            
        except Exception as e:
            print(f'{self.capture_source}[{self.capture_source}]: Error saving screenshot: {e}')
            return None

    def generateRestartVideoFast(self, duration_seconds: float = None, test_start_time: float = None, processing_time: float = None) -> Optional[Dict[str, Any]]:
        """
        Fast restart video generation - returns video URL + audio analysis only.
        Shows player immediately while AI analysis runs in background.
        
        Args:
            duration_seconds: How many seconds of video to capture (default: 10s)
            test_start_time: Unix timestamp when test started (for time sync)
            
        Returns:
            Dict with video_url and basic analysis_data including:
            - audio_analysis: Speech-to-text transcription (included for immediate display)
            - screenshot_urls: URLs for later AI analysis
            - video_id: Unique identifier for async analysis
        """
        try:
            import time
            import os
            import tempfile
            
            if duration_seconds is None:
                duration_seconds = 10.0  # Fixed 10 seconds for fast restart videos
                
            print(f"{self.capture_source}[{self.capture_source}]: Compressing {duration_seconds}s HLS video to MP4")
            
            # 1. Find the M3U8 file (HLS playlist)
            m3u8_path = os.path.join(self.video_capture_path, "output.m3u8")
            
            if not os.path.exists(m3u8_path):
                print(f"{self.capture_source}[{self.capture_source}]: No M3U8 file found at {m3u8_path}")
                print(f"{self.capture_source}[{self.capture_source}]: This is expected if video capture is not active. Report will continue without video.")
                return None
            
            # 2. Wait for encoder to finish and get updated playlist
            if test_start_time:
                # Wait 5 seconds for encoder to finish and write final segments (reduced from 18s)
                print(f"{self.capture_source}[{self.capture_source}]: Waiting 5s for final segments to complete...")
                time.sleep(5)
            
            # Read M3U8 playlist to get segment list and detect actual segment duration
            with open(m3u8_path, 'r') as f:
                playlist_content = f.read()
            
            # Use configured segment duration (ignore M3U8 detection)
            actual_segment_duration = self.HLS_SEGMENT_DURATION
            print(f"{self.capture_source}[{self.capture_source}]: Using configured segment duration: {actual_segment_duration}s")
            
            # Get all segment files directly from directory and sort by segment number
            import glob
            import re
            
            # Get all .ts files from directory
            segment_pattern = os.path.join(self.video_capture_path, "segment_*.ts")
            all_segment_paths = glob.glob(segment_pattern)
            
            # Sort by file modification time (most recent last)
            all_segment_paths.sort(key=lambda path: os.path.getmtime(path))
            
            # Convert to (filename, filepath) tuples
            all_segments = []
            for segment_path in all_segment_paths:
                if os.path.exists(segment_path):
                    filename = os.path.basename(segment_path)
                    all_segments.append((filename, segment_path))
            
            print(f"{self.capture_source}[{self.capture_source}]: Found {len(all_segments)} total segments in directory")
            
            # SIMPLE FILTERING: Take the last N segments based on duration
            if duration_seconds:
                # Simple calculation: duration ÷ segment_duration = segments needed
                segments_needed = int(duration_seconds / actual_segment_duration) + 2  # +2 for small buffer
                
                # Use all available segments if not enough for requested duration
                if len(all_segments) < segments_needed:
                    segment_files = all_segments
                    actual_duration = len(all_segments) * actual_segment_duration
                    print(f"{self.capture_source}[{self.capture_source}]: Only {len(all_segments)} segments available ({actual_duration}s), using all")
                else:
                    segment_files = all_segments[-segments_needed:]
                    print(f"{self.capture_source}[{self.capture_source}]: Taking last {segments_needed} segments ({duration_seconds}s)")
            else:
                # No duration provided, take all available segments
                segment_files = all_segments
            
            if not segment_files:
                print(f"{self.capture_source}[{self.capture_source}]: No video segments found")
                return None
            
            print(f"{self.capture_source}[{self.capture_source}]: Selected {len(segment_files)} segments out of {len(all_segments)} total")
            print(f"{self.capture_source}[{self.capture_source}]: Segment duration: {actual_segment_duration}s, Expected video length: {len(segment_files) * actual_segment_duration:.1f}s")
            
            # Log first and last few segments for debugging
            if len(segment_files) > 0:
                print(f"{self.capture_source}[{self.capture_source}]: First segment: {segment_files[0][0]}")
                print(f"{self.capture_source}[{self.capture_source}]: Last segment: {segment_files[-1][0]}")
                if len(segment_files) > 5:
                    print(f"{self.capture_source}[{self.capture_source}]: Using segments {segment_files[0][0]} to {segment_files[-1][0]} ({len(segment_files)} total)")
            
            # 3. Compress HLS segments to MP4 directly to final location
            from shared.lib.utils.video_compression_utils import VideoCompressionUtils
            compressor = VideoCompressionUtils()
            
            # Estimate compression time and inform user
            estimated_time = compressor.estimate_compression_time(len(segment_files), duration_seconds)
            print(f"{self.capture_source}[{self.capture_source}]: Estimated compression time: {estimated_time:.1f}s")
            
            # Set final output path directly in capture folder
            video_filename = "restart_video.mp4"  # Fixed filename - will be overwritten
            local_video_path = os.path.join(self.video_capture_path, video_filename)
            
            # Compress segments to MP4 directly to final location
            compression_result = compressor.compress_hls_to_mp4(
                m3u8_path=m3u8_path,
                segment_files=segment_files,
                output_path=local_video_path,  # Compress directly to final location
                compression_level="medium"  # Good balance of quality/size/speed
            )
            
            if not compression_result['success']:
                print(f"{self.capture_source}[{self.capture_source}]: Video compression failed: {compression_result['error']}")
                return None
            
            print(f"{self.capture_source}[{self.capture_source}]: Compression complete - {compression_result['compression_ratio']:.1f}% size reduction")
            print(f"{self.capture_source}[{self.capture_source}]: MP4 saved locally: {local_video_path}")
            
            # Build proper URL using host URL building utilities
            # The file is now at: /var/www/html/stream/capture1/restart_video.mp4
            # We need to build the full host URL, not just the path
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            try:
                host = get_host_instance()
                host_dict = host.to_dict()
                video_url = buildHostImageUrl(host_dict, local_video_path)
            except Exception as url_error:
                print(f"{self.capture_source}[{self.capture_source}]: Failed to build host URL: {url_error}")
                # Fallback to stream path
                video_url = self.video_stream_path + "/" + video_filename
            
            print(f"{self.capture_source}[{self.capture_source}]: Restart video available at: {video_url}")
            
            # Return video URL only if no analysis requested
            # Always perform full analysis for restart video
            
            # SYNCHRONOUS ANALYSIS: Process immediately and return complete results
            print(f"[RestartVideo] Starting synchronous analysis for {video_url}")
            
            # 1. Get audio transcript locally (same method as ZapController)
            def get_audio_transcript_locally():
                try:
                    from backend_core.src.controllers.verification.audio_ai_helpers import AudioAIHelpers
                    
                    # Initialize AudioAI helpers (same as ZapController)
                    audio_ai = AudioAIHelpers(self, f"RestartVideo-{self.device_name}")
                    
                    # Use the SAME segments that were used for video generation (for synchronization)
                    # For restart video, analyze the FULL duration (same as video), not just 3s like zap controller
                    video_segment_files_for_audio = segment_files  # Use ALL video segments for audio analysis
                    
                    print(f"[RestartVideo] Using SAME {len(video_segment_files_for_audio)} segments for audio as video ({duration_seconds}s):")
                    for i, (filename, _) in enumerate(video_segment_files_for_audio):
                        print(f"[RestartVideo] Audio segment {i+1}: {filename}")
                    
                    audio_files = audio_ai.extract_audio_from_segments(video_segment_files_for_audio, segment_count=len(video_segment_files_for_audio))
                    
                    if not audio_files:
                        return {
                            'success': True,
                            'speech_detected': False,
                            'combined_transcript': '',
                            'detected_language': 'unknown',
                            'confidence': 0.0,
                            'segments_analyzed': 0
                        }
                    
                    # Analyze with AI (same as ZapController) - returns results immediately
                    audio_analysis = audio_ai.analyze_audio_segments_ai(audio_files, upload_to_r2=True, early_stop=True)
                    
                    if not audio_analysis.get('success'):
                        return {
                            'success': False,
                            'speech_detected': False,
                            'combined_transcript': '',
                            'detected_language': 'unknown',
                            'confidence': 0.0,
                            'segments_analyzed': 0
                        }
                    
                    # Extract results immediately (same as ZapController)
                    return {
                        'success': True,
                        'speech_detected': audio_analysis.get('successful_segments', 0) > 0,
                        'combined_transcript': audio_analysis.get('combined_transcript', ''),
                        'detected_language': audio_analysis.get('detected_language', 'unknown'),
                        'confidence': audio_analysis.get('confidence', 0.0),
                        'segments_analyzed': audio_analysis.get('segments_analyzed', 0)
                    }
                    
                except Exception as e:
                    print(f"[RestartVideo] Audio analysis error: {e}")
                    return {
                        'success': False,
                        'speech_detected': False,
                        'combined_transcript': '',
                        'detected_language': 'unknown',
                        'confidence': 0.0,
                        'segments_analyzed': 0,
                        'error': str(e)
                    }
            
            # 2. Get screenshot URLs from the video recording period
            def get_video_screenshots(segment_count):
                try:
                    capture_folder = f"{self.video_capture_path}/captures"
                    import glob, os
                    
                    # Find screenshots from the video recording period (dynamic based on video duration)
                    pattern = os.path.join(capture_folder, "capture_*.jpg")
                    screenshots = glob.glob(pattern)
                    
                    if not screenshots:
                        return []
                    
                    # Use the EXACT same segment count as video generation (passed as parameter)
                    # No recalculation - use the actual count from video generation
                    screenshot_count = max(5, segment_count)  # Use the SAME count as video segments
                    
                    print(f"[RestartVideo] Video duration: {duration_seconds}s, video segments: {segment_count}, screenshots needed: {screenshot_count}")
                    
                    # Sort by modification time, get last N screenshots based on video duration
                    recent_screenshots = sorted(screenshots, key=os.path.getmtime)[-screenshot_count:]
                    
                    # Convert to proper host URLs for frontend using buildHostImageUrl
                    from shared.lib.utils.build_url_utils import buildHostImageUrl
                    from shared.lib.utils.host_utils import get_host_instance
                    
                    screenshot_urls = []
                    try:
                        host = get_host_instance()
                        host_dict = host.to_dict()
                        
                        for screenshot_path in recent_screenshots:
                            # Build proper host URL for each screenshot
                            screenshot_url = buildHostImageUrl(host_dict, screenshot_path)
                            screenshot_urls.append(screenshot_url)
                            
                    except Exception as url_error:
                        print(f"[RestartVideo] Failed to build screenshot URLs: {url_error}")
                        # Fallback to relative paths
                        for screenshot_path in recent_screenshots:
                            filename = os.path.basename(screenshot_path)
                            screenshot_url = f"{self.video_stream_path}/captures/{filename}"
                            screenshot_urls.append(screenshot_url)
                    
                    print(f"[RestartVideo] Found {len(screenshot_urls)} screenshots for analysis")
                    return screenshot_urls
                    
                except Exception as e:
                    print(f"[RestartVideo] Screenshot collection error: {e}")
                    return []
            
            # Execute analysis synchronously
            audio_result = get_audio_transcript_locally()
            actual_segment_count = len(segment_files)  # Get the ACTUAL count used for video generation
            screenshot_urls = get_video_screenshots(actual_segment_count)  # Pass the actual count
            
            # Execute only fast analysis (audio + screenshot collection)
            # All AI analysis (subtitles + video descriptions) will be done async via analyzeRestartVideoAsync()
            
            # Build fast response with basic analysis data
            from datetime import datetime
            import uuid
            
            # Generate unique video ID for async analysis
            video_id = f"restart_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            analysis_data = {
                'audio_analysis': {
                    'success': audio_result.get('success', False),
                    'speech_detected': audio_result.get('speech_detected', False),
                    'combined_transcript': audio_result.get('combined_transcript', ''),
                    'detected_language': audio_result.get('detected_language', 'unknown'),
                    'confidence': audio_result.get('confidence', 0.0),
                    'segments_analyzed': audio_result.get('segments_analyzed', 0),
                    'execution_time_ms': 0  # Actual time will be calculated by caller
                },
                'screenshot_urls': screenshot_urls,
                'video_analysis': {
                    'success': False,
                    'pending': True,  # Indicates analysis is pending
                    'message': 'Video analysis will be performed asynchronously'
                },
                'subtitle_analysis': {
                    'success': False,
                    'pending': True,  # Indicates analysis is pending
                    'message': 'Subtitle analysis will be performed asynchronously'
                },
                'video_id': video_id,  # For async analysis tracking
                'segment_count': actual_segment_count,  # Pass actual segment count to async analysis
                'analysis_complete': False,  # Fast analysis only
                'timestamp': time.time(),
                'created_at': datetime.now().isoformat()
            }
            
            # Log fast analysis results
            if audio_result.get('combined_transcript'):
                transcript_preview = audio_result['combined_transcript'][:100] + "..." if len(audio_result['combined_transcript']) > 100 else audio_result['combined_transcript']
                print(f"[RestartVideo] Audio transcript: '{transcript_preview}'")
            
            print(f"[RestartVideo] Fast generation complete - Video ID: {video_id}")
            print(f"[RestartVideo] Screenshots collected: {len(screenshot_urls)} frames")
            print(f"[RestartVideo] AI analysis will be performed asynchronously")
            
            # Return complete results as dict (report generation handled by route)
            return {
                'success': True,
                'video_url': video_url,
                'analysis_data': analysis_data
            }
                
        except Exception as e:
            print(f"{self.capture_source}[{self.capture_source}]: Error generating fast restart video: {e}")
            return None
    
    def analyzeRestartVideoAsync(self, video_id: str, screenshot_urls: List[str], duration_seconds: float = 10.0, segment_count: int = None) -> Optional[Dict[str, Any]]:
        """
        Async AI analysis for restart video - subtitle detection + video descriptions.
        Called by frontend after player is shown.
        
        Args:
            video_id: Unique identifier from fast generation
            screenshot_urls: URLs of screenshots to analyze
            duration_seconds: Duration of the video in seconds (default: 10.0)
            
        Returns:
            Dict with complete AI analysis results:
            - subtitle_analysis: AI-powered subtitle detection
            - video_analysis: Frame descriptions and video summary
        """
        try:
            import time
            from datetime import datetime
            
            print(f"[RestartVideoAsync] Starting async AI analysis for video ID: {video_id}")
            print(f"[RestartVideoAsync] Analyzing {len(screenshot_urls)} screenshots")
            
            # Convert URLs to local paths ONCE for consistent analysis
            from shared.lib.utils.build_url_utils import convertHostUrlToLocalPath
            
            # Use the EXACT segment count from video generation (passed as parameter)
            # If segment_count is provided, use it; otherwise fall back to screenshot count
            if segment_count is not None:
                expected_screenshot_count = segment_count
                print(f"[RestartVideoAsync] Video duration: {duration_seconds}s, using segment count: {segment_count}, analyzing {len(screenshot_urls)} screenshots")
            else:
                expected_screenshot_count = len(screenshot_urls)
                print(f"[RestartVideoAsync] Video duration: {duration_seconds}s, no segment count provided, analyzing ALL {len(screenshot_urls)} screenshots")
            
            local_screenshot_paths = []
            for url in screenshot_urls:  # Use ALL screenshots provided (already synchronized with video segments)
                if url.startswith(('http://', 'https://')):
                    local_path = convertHostUrlToLocalPath(url)
                    local_screenshot_paths.append(local_path)
                else:
                    local_screenshot_paths.append(url)
            
            print(f"[RestartVideoAsync] Converted {len(local_screenshot_paths)} screenshot URLs to local paths")
            
            # Initialize video verification controller ONCE for both analyses
            from backend_core.src.controllers.verification.video import VideoVerificationController
            video_controller = VideoVerificationController(self.device_name)
            
            # 1. Perform subtitle analysis on the consistent screenshot list
            def get_subtitle_analysis():
                try:
                    if not local_screenshot_paths:
                        return {
                            'success': False,
                            'subtitles_detected': False,
                            'extracted_text': '',
                            'detected_language': 'unknown',
                            'confidence': 0.0,
                            'frames_analyzed': 0,
                            'frame_subtitles': []
                        }
                    
                    print(f"[RestartVideoAsync] Starting subtitle analysis on {len(local_screenshot_paths)} screenshots")
                    subtitle_result = video_controller.detect_subtitles_ai_all_frames(local_screenshot_paths, extract_text=True)
                    
                    # Extract frame-by-frame subtitle data
                    frame_subtitles = []
                    if subtitle_result.get('success') and subtitle_result.get('results'):
                        for i, result in enumerate(subtitle_result.get('results', [])):
                            frame_text = result.get('extracted_text', '').strip()
                            if frame_text:
                                frame_subtitles.append(f"Frame {i+1}: {frame_text}")
                            else:
                                frame_subtitles.append(f"Frame {i+1}: No subtitles detected")
                    
                    return {
                        'success': subtitle_result.get('success', False),
                        'subtitles_detected': subtitle_result.get('subtitles_detected', False),
                        'extracted_text': subtitle_result.get('extracted_text', ''),
                        'detected_language': subtitle_result.get('detected_language', 'unknown'),
                        'confidence': subtitle_result.get('confidence', 0.0),
                        'frames_analyzed': len(local_screenshot_paths),
                        'frame_subtitles': frame_subtitles
                    }
                    
                except Exception as e:
                    print(f"[RestartVideoAsync] Subtitle analysis error: {e}")
                    return {
                        'success': False,
                        'subtitles_detected': False,
                        'extracted_text': '',
                        'detected_language': 'unknown',
                        'confidence': 0.0,
                        'frames_analyzed': 0,
                        'frame_subtitles': [],
                        'error': str(e)
                    }
            
            # 2. Perform video description analysis on the consistent screenshot list
            def get_video_description_analysis():
                try:
                    if not local_screenshot_paths:
                        return {
                            'success': False,
                            'frame_descriptions': [],
                            'video_summary': '',
                            'frames_analyzed': 0
                        }
                    
                    print(f"[RestartVideoAsync] Starting video description analysis on {len(local_screenshot_paths)} screenshots")
                    
                    frame_descriptions = []
                    for i, local_path in enumerate(local_screenshot_paths):
                        frame_query = f"Describe what is happening in this frame from a video sequence. Be concise and specific about UI elements, actions, or content visible."
                        description = video_controller.analyze_image_with_ai(local_path, frame_query)
                        if description and description.strip():
                            frame_descriptions.append(f"Frame {i+1}: {description.strip()}")
                        else:
                            frame_descriptions.append(f"Frame {i+1}: No description available")
                    
                    # Generate overall video summary
                    if frame_descriptions:
                        summary_query = f"Based on the {len(frame_descriptions)} frame descriptions, provide a concise summary of what happened in this video sequence."
                        # Use first frame for summary context (could be improved to use a composite)
                        video_summary = video_controller.analyze_image_with_ai(local_screenshot_paths[0], summary_query)
                        if not video_summary or not video_summary.strip():
                            video_summary = f"Video sequence showing {len(frame_descriptions)} frames of activity"
                    else:
                        video_summary = "No video description available"
                    
                    return {
                        'success': True,
                        'frame_descriptions': frame_descriptions,
                        'video_summary': video_summary.strip(),
                        'frames_analyzed': len(local_screenshot_paths)
                    }
                    
                except Exception as e:
                    print(f"[RestartVideoAsync] Video description analysis error: {e}")
                    return {
                        'success': False,
                        'frame_descriptions': [],
                        'video_summary': '',
                        'frames_analyzed': 0,
                        'error': str(e)
                    }
            
            # Execute async analysis
            subtitle_result = get_subtitle_analysis()
            video_description_result = get_video_description_analysis()
            
            # Build complete async analysis response
            analysis_data = {
                'video_id': video_id,
                'subtitle_analysis': {
                    'success': subtitle_result.get('success', False),
                    'subtitles_detected': subtitle_result.get('subtitles_detected', False),
                    'extracted_text': subtitle_result.get('extracted_text', ''),
                    'detected_language': subtitle_result.get('detected_language', 'unknown'),
                    'confidence': subtitle_result.get('confidence', 0.0),
                    'frames_analyzed': subtitle_result.get('frames_analyzed', 0),
                    'frames_available': len(screenshot_urls),
                    'frame_subtitles': subtitle_result.get('frame_subtitles', [])
                },
                'video_analysis': {
                    'success': video_description_result.get('success', False),
                    'frame_descriptions': video_description_result.get('frame_descriptions', []),
                    'video_summary': video_description_result.get('video_summary', ''),
                    'frames_analyzed': video_description_result.get('frames_analyzed', 0),
                    'frames_available': len(screenshot_urls)
                },
                'analysis_complete': True,
                'timestamp': time.time(),
                'created_at': datetime.now().isoformat()
            }
            
            # Log async analysis results
            if subtitle_result.get('subtitles_detected') and subtitle_result.get('extracted_text'):
                subtitle_preview = subtitle_result['extracted_text'][:100] + "..." if len(subtitle_result['extracted_text']) > 100 else subtitle_result['extracted_text']
                print(f"[RestartVideoAsync] Subtitles detected: '{subtitle_preview}'")
            
            if video_description_result.get('success') and video_description_result.get('frame_descriptions'):
                frame_count = len(video_description_result['frame_descriptions'])
                summary_preview = video_description_result.get('video_summary', '')[:100] + "..." if len(video_description_result.get('video_summary', '')) > 100 else video_description_result.get('video_summary', '')
                print(f"[RestartVideoAsync] Video analysis: {frame_count} frames analyzed, summary: '{summary_preview}'")
            
            print(f"[RestartVideoAsync] Async analysis complete for video ID: {video_id}")
            
            # Return complete async analysis results
            return {
                'success': True,
                'analysis_data': analysis_data
            }
                
        except Exception as e:
            print(f"[RestartVideoAsync] Error in async analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'video_id': video_id
            }
    
    def take_video(self, duration_seconds: float = None, test_start_time: float = None) -> Optional[str]:
        """
        Simple video capture without analysis (for script framework and other use cases).
        
        Args:
            duration_seconds: How many seconds of video to capture (default: 10s)
            test_start_time: Unix timestamp when test started (for time sync)
            
        Returns:
            R2 URL of compressed MP4 video, or None if failed
        """
        try:
            import time
            import os
            import tempfile
            
            if duration_seconds is None:
                duration_seconds = 10.0  # Fixed 10 seconds for fast restart videos
                
            print(f"{self.capture_source}[{self.capture_source}]: Compressing {duration_seconds}s HLS video to MP4")
            
            # Use configured segment duration consistently
            print(f"{self.capture_source}[{self.capture_source}]: Using configured segment duration: {self.HLS_SEGMENT_DURATION}s")
            
            # Get recent HLS segments for compression
            segment_files = self._get_recent_segments(duration_seconds)
            if not segment_files:
                print(f"{self.capture_source}[{self.capture_source}]: No HLS segments found for compression")
                return None
            
            # Compress segments to MP4
            video_filename = "restart_video.mp4"
            local_video_path = os.path.join(self.video_capture_path, video_filename)
            
            success = self._compress_segments_to_mp4(segment_files, local_video_path, duration_seconds)
            if not success:
                return None
            
            # Build video URL for access
            if self.video_stream_path.startswith('http'):
                video_url = f"{self.video_stream_path}/{video_filename}"
            else:
                video_url = self.video_stream_path + "/" + video_filename
            
            print(f"{self.capture_source}[{self.capture_source}]: Video available at: {video_url}")
            return video_url
            
        except Exception as e:
            print(f"{self.capture_source}[{self.capture_source}]: Error creating video: {e}")
            return None
        
    def take_control(self) -> Dict[str, Any]:
        """
        Take control of stream and verify it's working.
        
        Returns:
            Dictionary with success status and stream information
        """
        try:
            # Check stream status
            status = self.get_status()
            is_streaming = status.get('is_streaming', False)
            
            # For FFmpeg-based capture, we just need the service to be running
            # The host continuously captures screenshots regardless
            return {
                'success': True,
                'status': 'stream_ready',
                'controller_type': 'av',
                'stream_info': status,
                'capabilities': ['video_capture', 'screenshot', 'streaming']
            }
                
        except Exception as e:
            print(f"{self.capture_source}[{self.capture_source}]: Take control error: {e}")
            return {
                'success': False,
                'status': 'error',
                'error': f'{self.capture_source} controller error: {str(e)}',
                'controller_type': 'av'
            }
        
    def start_video_capture(self, duration: float = 60.0, filename: str = None, 
                           resolution: str = None, fps: int = None) -> bool:
        """
        Start video capture by recording start time and duration.
        No FFmpeg usage - just tracks timing for timestamp-based screenshot references.
        
        Args:
            duration: Duration in seconds (default: 60s)
            filename: Optional filename (ignored - uses timestamps)
            resolution: Video resolution (ignored - uses host stream resolution)
            fps: Video FPS (ignored - uses 1 frame per second from screenshots)
        """
        if self.is_capturing_video:
            return True
            
        try:
            import time
            import threading
            from datetime import datetime
            
            # Record capture session details
            self.capture_start_time = datetime.now()
            self.capture_duration = duration
            self.capture_session_id = f"capture_{int(time.time())}"
            self.is_capturing_video = True
            
            print(f"{self.capture_source}[{self.capture_source}]: Starting video capture - Session: {self.capture_session_id}, Duration: {duration}s")
            
            # Start monitoring thread to automatically stop after duration
            monitoring_thread = threading.Thread(
                target=self._monitor_capture_duration,
                args=(duration,),
                daemon=True
            )
            monitoring_thread.start()
            
            return True
            
        except Exception as e:
            print(f"{self.capture_source}[{self.capture_source}]: Failed to start video capture: {e}")
            return False
        
    def stop_video_capture(self) -> bool:
        """Stop video capture session."""
        if not self.is_capturing_video:
            return False
            
        try:
            from datetime import datetime
            
            # Calculate actual capture duration
            if self.capture_start_time:
                actual_duration = (datetime.now() - self.capture_start_time).total_seconds()
                print(f"{self.capture_source}[{self.capture_source}]: Video capture stopped - Duration: {actual_duration:.1f}s")
            
            self.is_capturing_video = False
            self.capture_session_id = None
            
            return True
            
        except Exception as e:
            print(f"{self.capture_source}[{self.capture_source}]: Error stopping video capture: {e}")
            return False
        
    def _monitor_capture_duration(self, duration: float):
        """Monitor capture duration and automatically stop after specified time."""
        import time
        
        time.sleep(duration)
        
        if self.is_capturing_video:
            print(f"{self.capture_source}[{self.capture_source}]: Capture duration ({duration}s) reached, stopping automatically")
            self.stop_video_capture()


class VerificationControllerInterface(BaseController):
    """Type hint interface for verification controllers."""
    
    def __init__(self, device_name: str = "Unknown Device", verification_type: str = "verification"):
        super().__init__("verification", device_name)
        self.verification_type = verification_type


class PowerControllerInterface(BaseController):
    """Type hint interface for power controllers."""
    
    def __init__(self, device_name: str = "Unknown Device"):
        super().__init__("power", device_name)