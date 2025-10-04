"""
HDMI Stream Controller Implementation

This controller handles HDMI stream acquisition by referencing continuously captured screenshots.
The host continuously takes screenshots using FFmpeg, and this controller references them by timestamp.
Uses shared FFmpeg-based capture functionality.
"""

import subprocess
from typing import Dict, Any, Optional
from ..base_controller import FFmpegCaptureController


class HDMIStreamController(FFmpegCaptureController):
    """HDMI Stream controller that references continuously captured screenshots by timestamp."""
    
    def __init__(self, video_stream_path: str, video_capture_path: str, **kwargs):
        """
        Initialize the HDMI Stream controller.
        
        Args:
            video_stream_path: Stream path for URLs (e.g., "/host/stream/capture1")
            video_capture_path: Local capture path (e.g., "/var/www/html/stream/capture1")
        """
        super().__init__("HDMI Stream Controller", "HDMI", video_stream_path, video_capture_path, **kwargs)

        
    def restart_stream(self, quality: str = 'sd') -> bool:
        """Restart HDMI streaming with quality parameter."""
        try:
            import os
            device_id = self.device_id
            print(f"[HDMI_CONTROLLER] restart_stream called with quality={quality} (type: {type(quality).__name__})")
            print(f"[HDMI_CONTROLLER] device_id={device_id}")
            
            # Get script path relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_host_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            script_path = os.path.join(backend_host_dir, 'scripts', 'run_ffmpeg_and_rename_local.sh')
            
            # Run as www-data to match stream.service user (ensures consistent file permissions)
            cmd = ['sudo', '-u', 'www-data', script_path, device_id, quality]
            print(f"[HDMI_CONTROLLER] Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"HDMI[{device_id}]: Restarted successfully")
                return True
            else:
                print(f"HDMI[{device_id}]: Failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"HDMI[{self.capture_source}]: Error: {e}")
            return False


            
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
