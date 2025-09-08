"""
System Information Utilities

Utility functions for system monitoring, process management, and environment validation.
"""

import os
import psutil
import hashlib
import platform
import time
import glob
import subprocess
from datetime import datetime
from typing import List, Dict, Any


def get_host_system_stats():
    """Get basic system statistics for host registration"""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'uptime_seconds': int(time.time() - psutil.boot_time()),
            'platform': platform.system(),
            'architecture': platform.machine(),
            'python_version': platform.python_version()
        }
    except Exception as e:
        print(f"⚠️ Error getting system stats: {e}")
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'uptime_seconds': 0,
            'platform': 'unknown',
            'architecture': 'unknown',
            'python_version': 'unknown'
        }


def get_enhanced_system_stats():
    """Get enhanced system statistics including uptime and process status"""
    try:
        # Basic system stats
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # System uptime
        boot_time = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_time)
        
        # FFmpeg status check
        ffmpeg_status = check_ffmpeg_status()
        
        # Monitor status check  
        monitor_status = check_monitor_status()
        
        return {
            'cpu_percent': round(psutil.cpu_percent(interval=1), 2),
            'memory_percent': round(memory.percent, 2),
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_percent': round((disk.used / disk.total) * 100, 2),
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2),
            'uptime_seconds': uptime_seconds,
            'platform': platform.system(),
            'architecture': platform.machine(),
            'ffmpeg_status': ffmpeg_status,
            'monitor_status': monitor_status
        }
    except Exception as e:
        print(f"⚠️ Error getting enhanced system stats: {e}")
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_used_gb': 0,
            'memory_total_gb': 0,
            'disk_percent': 0,
            'disk_used_gb': 0,
            'disk_total_gb': 0,
            'uptime_seconds': 0,
            'platform': 'unknown',
            'architecture': 'unknown',
            'ffmpeg_status': {'status': 'unknown', 'error': str(e)},
            'monitor_status': {'status': 'unknown', 'error': str(e)}
        }


def get_per_device_metrics(devices_config: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get per-device metrics with real device names and separate FFmpeg/Monitor tracking.
    
    Args:
        devices_config: List of device configurations from host registration
        
    Returns:
        List of device metrics with individual status and timing
    """
    try:
        # Get base system stats
        base_stats = get_host_system_stats()
        
        # Get FFmpeg and Monitor status
        ffmpeg_status = check_ffmpeg_status()
        monitor_status = check_monitor_status()
        
        device_metrics = []
        
        for device in devices_config:
            device_id = device.get('device_id', 'unknown')
            device_name = device.get('device_name', 'Unknown Device')
            device_model = device.get('device_model', 'unknown')
            device_port = device.get('device_port', 'unknown')
            
            # Extract capture folder from video_capture_path
            video_capture_path = device.get('video_capture_path', '')
            capture_folder = 'unknown'
            if video_capture_path:
                # Extract folder name from path like '/var/www/html/stream/capture1' -> 'capture1'
                capture_folder = os.path.basename(video_capture_path.rstrip('/'))
            
            # Extract video device path (e.g., '/dev/video0', '/dev/video2')
            video_device = device.get('video', 'unknown')
            
            # Extract per-device FFmpeg status using capture folder
            ffmpeg_device_status = 'unknown'
            ffmpeg_last_activity = None
            ffmpeg_uptime_seconds = 0
            
            if ffmpeg_status.get('recent_files', {}).get(capture_folder):
                device_files = ffmpeg_status['recent_files'][capture_folder]
                if device_files.get('images', 0) > 0 or device_files.get('video_segments', 0) > 0:
                    ffmpeg_device_status = 'active'
                    last_activity_timestamp = device_files.get('last_activity', 0)
                    if last_activity_timestamp > 0:
                        ffmpeg_last_activity = datetime.fromtimestamp(last_activity_timestamp).isoformat()
                        # Simple uptime calculation: time since last activity (if recent, assume continuous)
                        time_since_activity = time.time() - last_activity_timestamp
                        if time_since_activity < 300:  # If activity within 5 minutes, assume active
                            ffmpeg_uptime_seconds = min(3600, time_since_activity + 300)  # Estimate uptime (max 1 hour for now)
                else:
                    ffmpeg_device_status = 'stopped'
            
            # Extract per-device Monitor status using capture folder
            monitor_device_status = 'unknown'
            monitor_last_activity = None
            monitor_uptime_seconds = 0
            
            if monitor_status.get('recent_json_files', {}).get(capture_folder):
                device_json = monitor_status['recent_json_files'][capture_folder]
                if device_json.get('count', 0) > 0:
                    monitor_device_status = 'active'
                    last_activity_timestamp = device_json.get('last_activity', 0)
                    if last_activity_timestamp > 0:
                        monitor_last_activity = datetime.fromtimestamp(last_activity_timestamp).isoformat()
                        # Simple uptime calculation: time since last activity (if recent, assume continuous)
                        time_since_activity = time.time() - last_activity_timestamp
                        if time_since_activity < 300:  # If activity within 5 minutes, assume active
                            monitor_uptime_seconds = min(3600, time_since_activity + 300)  # Estimate uptime (max 1 hour for now)
                else:
                    monitor_device_status = 'stopped'
            
            # Create device metrics record
            device_metric = {
                'device_id': device_id,
                'device_name': device_name,
                'device_port': device_port,
                'device_model': device_model,
                'capture_folder': capture_folder,  # Add capture folder for tracking
                'video_device': video_device,  # Add video device path for hardware tracking
                'ffmpeg_status': ffmpeg_device_status,
                'ffmpeg_last_activity': ffmpeg_last_activity,
                'ffmpeg_uptime_seconds': ffmpeg_uptime_seconds,  # Will be calculated from history
                'monitor_status': monitor_device_status,
                'monitor_last_activity': monitor_last_activity,
                'monitor_uptime_seconds': monitor_uptime_seconds  # Will be calculated from history
            }
            
            device_metrics.append(device_metric)
            
        return device_metrics
        
    except Exception as e:
        print(f"⚠️ Error getting per-device metrics: {e}")
        return []


def check_ffmpeg_status():
    """Check FFmpeg process and recent file creation status"""
    try:
        status = {
            'processes_running': 0,
            'recent_files': {},
            'status': 'unknown'
        }
        
        # Check running FFmpeg processes
        ffmpeg_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'ffmpeg':
                    ffmpeg_processes.append({
                        'pid': proc.info['pid'],
                        'cmdline': ' '.join(proc.info['cmdline'][:3])  # First 3 args only
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        status['processes_running'] = len(ffmpeg_processes)
        status['processes'] = ffmpeg_processes
        
        # Check recent file creation in capture directories
        capture_dirs = [
            '/var/www/html/stream/capture1',
            '/var/www/html/stream/capture2', 
            '/var/www/html/stream/capture3',
            '/var/www/html/stream/capture4'
        ]
        
        current_time = time.time()
        for capture_dir in capture_dirs:
            if os.path.exists(capture_dir):
                device_name = os.path.basename(capture_dir)
                
                # Check for recent video segments (.ts files)
                ts_files = glob.glob(os.path.join(capture_dir, 'segment_*.ts'))
                recent_ts = [f for f in ts_files if current_time - os.path.getmtime(f) < 300]  # 5 minutes
                
                # Check for recent images (.jpg files)
                captures_dir = os.path.join(capture_dir, 'captures')
                if os.path.exists(captures_dir):
                    jpg_files = glob.glob(os.path.join(captures_dir, 'capture_*.jpg'))
                    recent_jpg = [f for f in jpg_files if current_time - os.path.getmtime(f) < 300]
                else:
                    recent_jpg = []
                
                status['recent_files'][device_name] = {
                    'video_segments': len(recent_ts),
                    'images': len(recent_jpg),
                    'last_activity': max([os.path.getmtime(f) for f in (recent_ts + recent_jpg)]) if (recent_ts + recent_jpg) else 0
                }
        
        # Determine per-device status and overall status
        device_statuses = {}
        active_devices = 0
        stuck_devices = 0
        
        for device_name, files_info in status['recent_files'].items():
            recent_files_count = files_info['video_segments'] + files_info['images']
            if recent_files_count > 0:
                device_statuses[device_name] = 'active'
                active_devices += 1
            else:
                device_statuses[device_name] = 'stopped'  # No recent files for this device
        
        status['device_statuses'] = device_statuses
        
        # Overall status logic
        if status['processes_running'] > 0:
            if active_devices > 0:
                status['status'] = 'active'  # At least one device is active
            else:
                status['status'] = 'stuck'  # Processes running but no devices producing files
        else:
            status['status'] = 'stopped'  # No processes running
            
        return status
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'processes_running': 0,
            'recent_files': {}
        }


def check_monitor_status():
    """Check capture monitor process and JSON file creation"""
    try:
        status = {
            'process_running': False,
            'recent_json_files': {},
            'status': 'unknown'
        }
        
        # Check if capture_monitor.py process is running
        monitor_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and 'capture_monitor.py' in ' '.join(proc.info['cmdline']):
                    monitor_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        status['process_running'] = len(monitor_processes) > 0
        status['processes'] = monitor_processes
        
        # Check recent JSON file creation
        capture_dirs = [
            '/var/www/html/stream/capture1/captures',
            '/var/www/html/stream/capture2/captures',
            '/var/www/html/stream/capture3/captures', 
            '/var/www/html/stream/capture4/captures'
        ]
        
        current_time = time.time()
        for captures_dir in capture_dirs:
            if os.path.exists(captures_dir):
                device_name = os.path.basename(os.path.dirname(captures_dir))  # capture1, capture2, etc.
                
                # Check for recent JSON files
                json_files = glob.glob(os.path.join(captures_dir, 'capture_*.json'))
                recent_json = [f for f in json_files if current_time - os.path.getmtime(f) < 300]  # 5 minutes
                
                status['recent_json_files'][device_name] = {
                    'count': len(recent_json),
                    'last_activity': max([os.path.getmtime(f) for f in recent_json]) if recent_json else 0
                }
        
        # Determine per-device status and overall status
        device_statuses = {}
        active_devices = 0
        
        for device_name, json_info in status['recent_json_files'].items():
            if json_info['count'] > 0:
                device_statuses[device_name] = 'active'
                active_devices += 1
            else:
                device_statuses[device_name] = 'stopped'  # No recent JSON files for this device
        
        status['device_statuses'] = device_statuses
        
        # Overall status logic
        if status['process_running']:
            if active_devices > 0:
                status['status'] = 'active'  # At least one device is active
            else:
                status['status'] = 'stuck'  # Process running but no devices producing JSON files
        else:
            status['status'] = 'stopped'  # No process running
            
        return status
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'process_running': False,
            'recent_json_files': {}
        } 