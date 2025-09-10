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
        Take screenshot using FFmpeg timestamp logic.
        Returns local file path only - routes will build URLs using existing URL building functions.
        """
        try:
            import time
            from datetime import datetime
            import pytz
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
            
            # List existing files for debugging
            try:
                existing_files = os.listdir(captures_path)
                recent_files = [f for f in existing_files if f.startswith('capture_') and f.endswith('.jpg')]
                print(f"{self.capture_source}[{self.capture_source}]: Found {len(recent_files)} existing capture files")
                if recent_files:
                    # Show the 3 most recent files
                    recent_files.sort(reverse=True)
                    for i, f in enumerate(recent_files[:3]):
                        file_path = os.path.join(captures_path, f)
                        file_time = os.path.getmtime(file_path)
                        age_seconds = time.time() - file_time
                        print(f"{self.capture_source}[{self.capture_source}]:   Recent file {i+1}: {f} (age: {age_seconds:.1f}s)")
            except Exception as list_error:
                print(f"{self.capture_source}[{self.capture_source}]: ERROR - Cannot list captures directory: {list_error}")
            
            # Generate timestamp in Zurich timezone (Europe/Zurich) in format: YYYYMMDDHHMMSS
            now = datetime.now()
            zurich_tz = pytz.timezone("Europe/Zurich")
            zurich_time = now.astimezone(zurich_tz)
            
            # Format: YYYYMMDDHHMMSS (no separators)
            year = zurich_time.year
            month = str(zurich_time.month).zfill(2)
            day = str(zurich_time.day).zfill(2)
            hours = str(zurich_time.hour).zfill(2)
            minutes = str(zurich_time.minute).zfill(2)
            seconds = str(zurich_time.second).zfill(2)
            
            timestamp = f"{year}{month}{day}{hours}{minutes}{seconds}"
            screenshot_path = f'{captures_path}/capture_{timestamp}.jpg'
            
            print(f"{self.capture_source}[{self.capture_source}]: Looking for screenshot with timestamp: {timestamp}")
            print(f"{self.capture_source}[{self.capture_source}]: Expected screenshot path: {screenshot_path}")
            
            # Wait 500ms first for FFmpeg to generate the file
            print(f"{self.capture_source}[{self.capture_source}]: Waiting 500ms for FFmpeg to generate file...")
            time.sleep(0.5)
            if os.path.exists(screenshot_path):
                print(f"{self.capture_source}[{self.capture_source}]: SUCCESS - Screenshot found after 500ms")
                return screenshot_path
            
            # If not found, wait 1 more second
            print(f"{self.capture_source}[{self.capture_source}]: File not found after 500ms, waiting 1 more second...")
            time.sleep(1.0)
            if os.path.exists(screenshot_path):
                print(f"{self.capture_source}[{self.capture_source}]: SUCCESS - Screenshot found after 1.5s total")
                return screenshot_path
            
            # Not found after total 1.5s - try to find the most recent file instead
            print(f"{self.capture_source}[{self.capture_source}]: Expected file not found, looking for most recent capture...")
            try:
                all_files = os.listdir(captures_path)
                # Filter for regular capture files (not thumbnails or other files)
                capture_files = [f for f in all_files if f.startswith('capture_') and f.endswith('.jpg') and '_thumbnail' not in f]
                
                if capture_files:
                    # Sort by filename (which contains timestamp) to get most recent
                    capture_files.sort(reverse=True)
                    most_recent = capture_files[0]
                    most_recent_path = os.path.join(captures_path, most_recent)
                    
                    # Check if it's recent (within last 10 seconds)
                    file_time = os.path.getmtime(most_recent_path)
                    age_seconds = time.time() - file_time
                    
                    print(f"{self.capture_source}[{self.capture_source}]: Most recent file: {most_recent} (age: {age_seconds:.1f}s)")
                    
                    if age_seconds <= 10:  # Use recent file if it's within 10 seconds
                        print(f"{self.capture_source}[{self.capture_source}]: Using recent file as fallback: {most_recent_path}")
                        return most_recent_path
                    else:
                        print(f"{self.capture_source}[{self.capture_source}]: Most recent file is too old ({age_seconds:.1f}s)")
                else:
                    print(f"{self.capture_source}[{self.capture_source}]: No regular capture files found in directory")
                    
            except Exception as fallback_error:
                print(f"{self.capture_source}[{self.capture_source}]: ERROR in fallback logic: {fallback_error}")
            
            # Not found after total 1.5s
            print(f"{self.capture_source}[{self.capture_source}]: FAILURE - Screenshot not found: {screenshot_path}")
            return None
                
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
            
            # Extract timestamp from temp screenshot path to get the actual image file
            import re
            timestamp_match = re.search(r'capture_(\d{14})\.jpg', temp_screenshot_path)
            if not timestamp_match:
                print(f'{self.capture_source}[{self.capture_source}]: Could not extract timestamp from temp path: {temp_screenshot_path}')
                return None
            
            # The temp_screenshot_path is already the local file path we need
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

    def take_video(self, duration_seconds: float = None, test_start_time: float = None) -> Optional[str]:
        """
        Compress HLS segments to MP4 and upload to R2.
        Reduces file count from ~180 segments to 1 MP4 file.
        
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
                duration_seconds = 10.0
                
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
            
            # Detect actual segment duration from M3U8 file
            actual_segment_duration = self.HLS_SEGMENT_DURATION  # Default fallback
            for line in playlist_content.splitlines():
                if line.startswith('#EXT-X-TARGETDURATION:'):
                    try:
                        actual_segment_duration = float(line.split(':')[1])
                        print(f"{self.capture_source}[{self.capture_source}]: Detected segment duration: {actual_segment_duration}s")
                        break
                    except:
                        pass
            
            # Extract .ts segment filenames from playlist
            all_segments = []
            for line in playlist_content.splitlines():
                if line.endswith('.ts'):
                    segment_path = os.path.join(self.video_capture_path, line.strip())
                    if os.path.exists(segment_path):
                        all_segments.append((line.strip(), segment_path))
            
            # SIMPLE FILTERING: Take the last N segments based on duration
            if duration_seconds:
                # Simple calculation: duration ÷ segment_duration = segments needed
                segments_needed = int(duration_seconds / actual_segment_duration) + 2  # +2 for small buffer
                
                print(f"{self.capture_source}[{self.capture_source}]: Duration: {duration_seconds}s, Segment duration: {actual_segment_duration}s")
                print(f"{self.capture_source}[{self.capture_source}]: Segments needed: {duration_seconds}s ÷ {actual_segment_duration}s = {segments_needed} segments")
                print(f"{self.capture_source}[{self.capture_source}]: Available segments: {len(all_segments)}, taking last {segments_needed}")
                
                # Take the last N segments
                segment_files = all_segments[-segments_needed:] if len(all_segments) >= segments_needed else all_segments
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
            
            # 3. Compress HLS segments to MP4
            from shared.lib.utils.video_compression_utils import VideoCompressionUtils
            compressor = VideoCompressionUtils()
            
            # Estimate compression time and inform user
            estimated_time = compressor.estimate_compression_time(len(segment_files), duration_seconds)
            print(f"{self.capture_source}[{self.capture_source}]: Estimated compression time: {estimated_time:.1f}s")
            
            # Compress segments to MP4
            compression_result = compressor.compress_hls_to_mp4(
                m3u8_path=m3u8_path,
                segment_files=segment_files,
                compression_level="medium"  # Good balance of quality/size/speed
            )
            
            if not compression_result['success']:
                print(f"{self.capture_source}[{self.capture_source}]: Video compression failed: {compression_result['error']}")
                return None
            
            compressed_mp4_path = compression_result['output_path']
            print(f"{self.capture_source}[{self.capture_source}]: Compression complete - {compression_result['compression_ratio']:.1f}% size reduction")
            
            # 4. Upload compressed MP4 to R2
            from shared.lib.utils.cloudflare_utils import get_cloudflare_utils
            uploader = get_cloudflare_utils()
            
            timestamp = int(time.time())
            video_filename = f"test_video_{timestamp}.mp4"
            video_remote_path = f"videos/{video_filename}"
            
            file_mappings = [{
                'local_path': compressed_mp4_path,
                'remote_path': video_remote_path,
                'content_type': 'video/mp4'
            }]
            
            upload_result = uploader.upload_files(file_mappings)
            
            # Clean up compressed file
            try:
                os.unlink(compressed_mp4_path)
            except:
                pass
            
            if upload_result['uploaded_files']:
                video_url = upload_result['uploaded_files'][0]['url']
                
                # DO NOT clean up original segments - they're needed for live streaming
                print(f"{self.capture_source}[{self.capture_source}]: HLS segments preserved for live streaming")
                
                print(f"{self.capture_source}[{self.capture_source}]: MP4 uploaded: {video_url}")
                return video_url
            else:
                error_msg = upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Upload failed'
                print(f"{self.capture_source}[{self.capture_source}]: MP4 upload failed: {error_msg}")
                return None
                
        except Exception as e:
            print(f"{self.capture_source}[{self.capture_source}]: Error uploading HLS: {e}")
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