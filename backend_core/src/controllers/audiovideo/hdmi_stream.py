"""
HDMI Stream Controller Implementation

This controller handles HDMI stream acquisition by referencing continuously captured screenshots.
The host continuously takes screenshots, and this controller references them by timestamp.
No FFmpeg usage - all video capture is done by referencing timestamped screenshot URLs.
"""

import threading
import time
import os
import json
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from ..base_controller import AVControllerInterface


class HDMIStreamController(AVControllerInterface):
    """HDMI Stream controller that references continuously captured screenshots by timestamp."""
    
    def __init__(self, video_stream_path: str, video_capture_path: str, **kwargs):
        """
        Initialize the HDMI Stream controller.
        
        Args:
            video_stream_path: Stream path for URLs (e.g., "/host/stream/capture1")
            video_capture_path: Local capture path (e.g., "/var/www/html/stream/capture1")
        """
        super().__init__("HDMI Stream Controller", "HDMI")
        
        # Only the essential parameters
        self.video_stream_path = video_stream_path
        self.video_capture_path = video_capture_path
        
        # Video capture state (timestamp-based, no FFmpeg)
        self.is_capturing_video = False
        self.capture_start_time = None
        self.capture_duration = 0
        self.capture_session_id = None
        
        print(f"HDMI[{self.capture_source}]: Initialized - Stream: {self.video_stream_path}, Capture: {self.video_capture_path}")

        
    def restart_stream(self) -> bool:
        """Restart HDMI streaming using systemd service management."""
        try:
            print(f"HDMI[{self.capture_source}]: Restarting stream service")
            
            # Restart the stream service
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'stream'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"HDMI[{self.capture_source}]: Stream service restarted successfully")
                return True
            else:
                print(f"HDMI[{self.capture_source}]: Failed to restart stream service: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"HDMI[{self.capture_source}]: Error restarting stream: {e}")
            return False

    def take_screenshot(self, filename: str = None) -> Optional[str]:
        """
        Take screenshot using timestamp logic.
        Returns local file path only - routes will build URLs using existing URL building functions.
        """
        try:
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
            
            # Add 200ms delay before returning path (allows host to capture screenshot)
            time.sleep(0.2)
            
            return screenshot_path
                
        except Exception as e:
            print(f'HDMI[{self.capture_source}]: Error taking screenshot: {e}')
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
                print(f'HDMI[{self.capture_source}]: Failed to take temporary screenshot')
                return None
            
            # Extract timestamp from temp screenshot path to get the actual image file
            import re
            timestamp_match = re.search(r'capture_(\d{14})\.jpg', temp_screenshot_path)
            if not timestamp_match:
                print(f'HDMI[{self.capture_source}]: Could not extract timestamp from temp path: {temp_screenshot_path}')
                return None
            
            # The temp_screenshot_path is already the local file path we need
            local_screenshot_path = temp_screenshot_path
            
            # Check if local file exists
            import os
            if not os.path.exists(local_screenshot_path):
                print(f'HDMI[{self.capture_source}]: Local screenshot file not found: {local_screenshot_path}')
                return None
            
            # Return the local file path for the route to handle the upload
            return local_screenshot_path
            
        except Exception as e:
            print(f'HDMI[{self.capture_source}]: Error saving screenshot: {e}')
            return None

    def take_video(self, duration_seconds: float = None) -> Optional[str]:
        """
        Take video from HLS stream and upload to R2.
        Simple like take_screenshot - just returns R2 URL.
        
        Args:
            duration_seconds: How many seconds of recent video to capture (default: 10s)
            
        Returns:
            R2 URL of uploaded video, or None if failed
        """
        temp_mp4 = None
        try:
            if duration_seconds is None:
                duration_seconds = 10.0
                
            print(f"HDMI[{self.capture_source}]: Taking {duration_seconds}s video")
            
            # 1. Find the M3U8 file (HLS playlist)
            m3u8_path = os.path.join(self.video_capture_path, "output.m3u8")
            
            if not os.path.exists(m3u8_path):
                print(f"HDMI[{self.capture_source}]: No M3U8 file found")
                return None
            
            # 2. Create MP4 directly from M3U8 using FFmpeg
            timestamp = int(time.time())
            temp_mp4 = f"/tmp/video_{timestamp}.mp4"
            
            # FFmpeg command: M3U8 → MP4
            # Note: -t limits output duration, but FFmpeg will capture what's available
            # If test duration > available segments, it captures all available segments
            cmd = [
                'ffmpeg', '-y',
                '-i', m3u8_path,  # Input: M3U8 playlist
                '-t', str(duration_seconds),  # Duration limit (captures up to this much)
                '-c', 'copy',  # Don't re-encode, just copy
                '-avoid_negative_ts', 'make_zero',  # Handle timestamp issues
                temp_mp4  # Output: MP4 file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"HDMI[{self.capture_source}]: FFmpeg failed: {result.stderr}")
                return None
            
            # 3. Upload MP4 to R2
            from shared.lib.utils.cloudflare_utils import upload_file_to_r2
            
            upload_result = upload_file_to_r2(
                temp_mp4,
                f"videos/test_video_{timestamp}.mp4",
                "video/mp4"
            )
            
            if upload_result.get('success'):
                video_url = upload_result.get('url')
                print(f"HDMI[{self.capture_source}]: Video uploaded: {video_url}")
                return video_url
            else:
                print(f"HDMI[{self.capture_source}]: Upload failed")
                return None
                
        except Exception as e:
            print(f"HDMI[{self.capture_source}]: Error taking video: {e}")
            return None
            
        finally:
            # 4. Always cleanup temp file
            if temp_mp4 and os.path.exists(temp_mp4):
                try:
                    os.remove(temp_mp4)
                    print(f"HDMI[{self.capture_source}]: Cleaned up temp file: {temp_mp4}")
                except Exception as cleanup_error:
                    print(f"HDMI[{self.capture_source}]: Failed to cleanup {temp_mp4}: {cleanup_error}")
        
        
    def take_control(self) -> Dict[str, Any]:
        """
        Take control of HDMI stream and verify it's working.
        
        Returns:
            Dictionary with success status and stream information
        """
        try:
            # Check stream status
            status = self.get_status()
            is_streaming = status.get('is_streaming', False)
            
            # For HDMI stream, we just need the service to be running
            # The host continuously captures screenshots regardless
            return {
                'success': True,
                'status': 'stream_ready',
                'controller_type': 'av',
                'stream_info': status,
                'capabilities': ['video_capture', 'screenshot', 'streaming']
            }
                
        except Exception as e:
            print(f"HDMI[{self.capture_source}]: Take control error: {e}")
            return {
                'success': False,
                'status': 'error',
                'error': f'HDMI controller error: {str(e)}',
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
            # Record capture session details
            self.capture_start_time = datetime.now()
            self.capture_duration = duration
            self.capture_session_id = f"capture_{int(time.time())}"
            self.is_capturing_video = True
            
            print(f"HDMI[{self.capture_source}]: Starting video capture - Session: {self.capture_session_id}, Duration: {duration}s")
            
            # Start monitoring thread to automatically stop after duration
            monitoring_thread = threading.Thread(
                target=self._monitor_capture_duration,
                args=(duration,),
                daemon=True
            )
            monitoring_thread.start()
            
            return True
            
        except Exception as e:
            print(f"HDMI[{self.capture_source}]: Failed to start video capture: {e}")
            return False
        
    def stop_video_capture(self) -> bool:
        """Stop video capture session."""
        if not self.is_capturing_video:
            return False
            
        try:
            # Calculate actual capture duration
            if self.capture_start_time:
                actual_duration = (datetime.now() - self.capture_start_time).total_seconds()
                print(f"HDMI[{self.capture_source}]: Video capture stopped - Duration: {actual_duration:.1f}s")
            
            self.is_capturing_video = False
            self.capture_session_id = None
            
            return True
            
        except Exception as e:
            print(f"HDMI[{self.capture_source}]: Error stopping video capture: {e}")
            return False
        
    def _monitor_capture_duration(self, duration: float):
        """Monitor capture duration and automatically stop after specified time."""
        time.sleep(duration)
        
        if self.is_capturing_video:
            print(f"HDMI[{self.capture_source}]: Capture duration ({duration}s) reached, stopping automatically")
            self.stop_video_capture()
            
    def get_status(self) -> Dict[str, Any]:
        """Get controller status using systemd service status."""
        try:
            # Get systemd service status
            result = subprocess.run(
                ['sudo', 'systemctl', 'show', 'stream', '--property=ActiveState,SubState'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse systemctl output
                service_status = {}
                for line in result.stdout.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        service_status[key.lower()] = value
                
                # Check if stream service is running
                is_streaming = (service_status.get('activestate') == 'active' and 
                              service_status.get('substate') == 'running')
                
                service_status_text = f"{service_status.get('activestate', 'unknown')}_{service_status.get('substate', 'unknown')}"
                
                return {
                    'success': True,
                    'controller_type': 'av',
                    'service_status': service_status_text,
                    'is_streaming': is_streaming,
                    'is_capturing': self.is_capturing_video,
                    'capture_session_id': self.capture_session_id,
                    'service_details': service_status,
                    'message': f'HDMI controller - service is {service_status_text}'
                }
            else:
                print(f"HDMI[{self.capture_source}]: Failed to get service status: {result.stderr}")
                return {
                    'success': False,
                    'controller_type': 'av',
                    'service_status': 'error',
                    'is_streaming': False,
                    'is_capturing': self.is_capturing_video,
                    'error': f'Failed to get service status: {result.stderr}'
                }
            
        except Exception as e:
            print(f"HDMI[{self.capture_source}]: Error getting status: {e}")
            return {
                'success': False,
                'controller_type': 'av',
                'service_status': 'error',
                'is_streaming': False,
                'is_capturing': self.is_capturing_video,
                'error': f'Failed to get controller status: {str(e)}'
            }
