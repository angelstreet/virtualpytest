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
        """Update quality in config - stream.service will detect and restart."""
        try:
            import os
            import fcntl
            device_id = self.device_id
            capture_dir = self.video_capture_path
            config_file = '/tmp/active_captures.conf'
            lock_file = f'{config_file}.lock'
            
            print(f"[HDMI] Updating quality for {device_id} to {quality}")
            
            # Atomic update with file lock
            with open(lock_file, 'w') as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                
                # Read existing entries
                entries = []
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        entries = [line.strip() for line in f if line.strip()]
                
                # Update quality for this device
                found = False
                for i, entry in enumerate(entries):
                    parts = entry.split(',')
                    if len(parts) == 3 and parts[0] == capture_dir:
                        entries[i] = f"{parts[0]},{parts[1]},{quality}"
                        found = True
                        break
                
                if not found:
                    print(f"[HDMI] Device {device_id} not running yet")
                    return False
                
                # Write back
                with open(config_file, 'w') as f:
                    f.write('\n'.join(entries) + '\n')
                os.chmod(config_file, 0o777)
            
            print(f"[HDMI] Quality updated: {device_id} → {quality}")
            return True
            
        except Exception as e:
            print(f"[HDMI] Error updating quality: {e}")
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
