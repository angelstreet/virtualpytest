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
    
    def __init__(self, device_name: str = "Unknown Device", capture_source: str = "HDMI"):
        super().__init__("av", device_name)
        self.capture_source = capture_source


class FFmpegCaptureController(AVControllerInterface):
    """
    Shared FFmpeg-based capture functionality for both HDMI and VNC controllers.
    Handles screenshot and video capture using the same host-side FFmpeg capture system.
    """
    
    # Global configuration for video segments
    HLS_SEGMENT_DURATION = 6  # seconds per segment
    
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
            
            # Build local screenshot file path using capture path
            captures_path = os.path.join(self.video_capture_path, 'captures')
            screenshot_path = f'{captures_path}/capture_{timestamp}.jpg'
            
            # Wait 500ms first for FFmpeg to generate the file
            time.sleep(0.5)
            if os.path.exists(screenshot_path):
                return screenshot_path
            
            # If not found, wait 1 more second
            time.sleep(1.0)
            if os.path.exists(screenshot_path):
                return screenshot_path
            
            # Not found after total 1.5s
            print(f"{self.capture_source}[{self.capture_source}]: Screenshot not found: {screenshot_path}")
            return None
                
        except Exception as e:
            print(f'{self.capture_source}[{self.capture_source}]: Error taking screenshot: {e}')
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
        Upload HLS stream directly to R2 (no MP4 conversion).
        Fast upload with no processing time.
        
        Args:
            duration_seconds: How many seconds of video to capture (default: 10s)
            test_start_time: Unix timestamp when test started (for time sync)
            
        Returns:
            R2 URL of HLS playlist (m3u8), or None if failed
        """
        try:
            import time
            import os
            import tempfile
            
            if duration_seconds is None:
                duration_seconds = 10.0
                
            print(f"{self.capture_source}[{self.capture_source}]: Uploading {duration_seconds}s HLS video (no conversion)")
            
            # 1. Find the M3U8 file (HLS playlist)
            m3u8_path = os.path.join(self.video_capture_path, "output.m3u8")
            
            if not os.path.exists(m3u8_path):
                print(f"{self.capture_source}[{self.capture_source}]: No M3U8 file found at {m3u8_path}")
                print(f"{self.capture_source}[{self.capture_source}]: This is expected if video capture is not active. Report will continue without video.")
                return None
            
            # 2. Wait for encoder to finish and get updated playlist
            if test_start_time:
                # Wait 18 seconds for encoder to finish and write final segments (3 segments)
                print(f"{self.capture_source}[{self.capture_source}]: Waiting 18s for final segments to complete...")
                time.sleep(18)
            
            # Read M3U8 playlist to get segment list
            with open(m3u8_path, 'r') as f:
                playlist_content = f.read()
            
            # Extract .ts segment filenames from playlist
            all_segments = []
            for line in playlist_content.splitlines():
                if line.endswith('.ts'):
                    segment_path = os.path.join(self.video_capture_path, line.strip())
                    if os.path.exists(segment_path):
                        all_segments.append((line.strip(), segment_path))
            
            # DURATION-BASED FILTERING: Take last N segments based on test duration + buffer
            segment_files = []
            if test_start_time and duration_seconds:
                # Calculate segments needed: test duration + buffer, using configurable segment duration
                buffer_seconds = self.HLS_SEGMENT_DURATION * 3  # 3 segments buffer (before + after)
                total_duration = duration_seconds + buffer_seconds
                segments_needed = int(total_duration / self.HLS_SEGMENT_DURATION) + 1  # +1 for safety
                
                print(f"{self.capture_source}[{self.capture_source}]: Test duration: {duration_seconds}s, taking last {segments_needed} segments")
                
                # Take the last N segments (most recent)
                segment_files = all_segments[-segments_needed:] if len(all_segments) >= segments_needed else all_segments
            else:
                # No duration provided, take all available segments
                segment_files = all_segments
            
            if not segment_files:
                print(f"{self.capture_source}[{self.capture_source}]: No video segments found")
                return None
            
            print(f"{self.capture_source}[{self.capture_source}]: Found {len(segment_files)} segments")
            
            # 3. Create unique folder for this video
            timestamp = int(time.time())
            video_folder = f"videos/test_video_{timestamp}"
            
            # 4. Upload HLS files to R2
            from shared.lib.utils.cloudflare_utils import get_cloudflare_utils
            uploader = get_cloudflare_utils()
            
            # Create new M3U8 playlist with only our selected segments
            new_playlist_content = f"#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:{self.HLS_SEGMENT_DURATION}\n"
            for segment_name, segment_path in segment_files:
                new_playlist_content += f"#EXTINF:{self.HLS_SEGMENT_DURATION}.0,\n"
                new_playlist_content += f"{segment_name}\n"
            new_playlist_content += "#EXT-X-ENDLIST\n"
            
            # Write new playlist to temp file and upload
            with tempfile.NamedTemporaryFile(mode='w', suffix='.m3u8', delete=False) as temp_file:
                temp_file.write(new_playlist_content)
                temp_playlist_path = temp_file.name
            
            playlist_remote_path = f"{video_folder}/playlist.m3u8"
            file_mappings = [{'local_path': temp_playlist_path, 'remote_path': playlist_remote_path}]
            upload_result = uploader.upload_files(file_mappings)
            
            # Convert to single file result
            if upload_result['uploaded_files']:
                playlist_result = {
                    'success': True,
                    'url': upload_result['uploaded_files'][0]['url']
                }
            else:
                playlist_result = {
                    'success': False,
                    'error': upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Upload failed'
                }
            
            # Clean up temp file
            try:
                os.unlink(temp_playlist_path)
            except:
                pass
            
            if not playlist_result.get('success'):
                print(f"{self.capture_source}[{self.capture_source}]: Failed to upload playlist")
                return None
            
            # Upload all segment files
            uploaded_segments = 0
            for segment_name, segment_path in segment_files:
                segment_remote_path = f"{video_folder}/{segment_name}"
                file_mappings = [{'local_path': segment_path, 'remote_path': segment_remote_path}]
                upload_result = uploader.upload_files(file_mappings)
                
                # Convert to single file result
                if upload_result['uploaded_files']:
                    segment_result = {'success': True}
                else:
                    segment_result = {'success': False}
                
                if segment_result.get('success'):
                    uploaded_segments += 1
                else:
                    print(f"{self.capture_source}[{self.capture_source}]: Failed to upload segment {segment_name}")
            
            if uploaded_segments == 0:
                print(f"{self.capture_source}[{self.capture_source}]: No segments uploaded successfully")
                return None
            
            # 5. Return playlist URL for HLS playback
            playlist_url = playlist_result.get('url')
            print(f"{self.capture_source}[{self.capture_source}]: HLS uploaded: {playlist_url} ({uploaded_segments}/{len(segment_files)} segments)")
            return playlist_url
                
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