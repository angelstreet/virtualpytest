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
from datetime import datetime, timezone
from typing import List, Dict, Any
from shared.lib.utils.supabase_utils import get_supabase_client

# Global cache for process start times
_process_start_cache = {}

def get_active_capture_dirs():
    """Read active capture directories from configuration file created by FFmpeg script"""
    config_file = "/tmp/active_captures.conf"
    capture_dirs = []
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    capture_dir = line.strip()
                    if capture_dir and os.path.exists(capture_dir):
                        capture_dirs.append(capture_dir)
            print(f"🔍 [CONFIG] Loaded {len(capture_dirs)} active capture directories from {config_file}")
            print(f"🔍 [CONFIG] Active directories: {capture_dirs}")
        else:
            print(f"🔍 [CONFIG] Configuration file not found: {config_file}, using fallback")
            # Fallback to hardcoded for safety
            capture_dirs = [
                '/var/www/html/stream/capture1',
                '/var/www/html/stream/capture2', 
                '/var/www/html/stream/capture3',
                '/var/www/html/stream/capture4'
            ]
    except Exception as e:
        # Silently use fallback on error
        # Fallback to hardcoded
        capture_dirs = [
            '/var/www/html/stream/capture1',
            '/var/www/html/stream/capture2', 
            '/var/www/html/stream/capture3',
            '/var/www/html/stream/capture4'
        ]
        
    return capture_dirs

def get_process_start_time(capture_folder: str, process_type: str) -> float:
    """Get process start time from system"""
    try:
        if process_type == 'ffmpeg':
            # Find FFmpeg process for this capture folder
            result = subprocess.run(['pgrep', '-f', f'ffmpeg.*{capture_folder}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                pid = result.stdout.strip().split('\n')[0]  # Get first PID
                # Get process start time using ps
                ps_result = subprocess.run(['ps', '-o', 'lstart=', '-p', pid], 
                                         capture_output=True, text=True)
                if ps_result.returncode == 0:
                    start_str = ps_result.stdout.strip()
                    # Parse start time (format: "Mon Jan 1 10:00:00 2024")
                    return datetime.strptime(start_str, '%a %b %d %H:%M:%S %Y').timestamp()
                    
        elif process_type == 'monitor':
            # Find monitor process (capture_monitor.py)
            result = subprocess.run(['pgrep', '-f', 'capture_monitor.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                pid = result.stdout.strip().split('\n')[0]  # Get first PID
                ps_result = subprocess.run(['ps', '-o', 'lstart=', '-p', pid], 
                                         capture_output=True, text=True)
                if ps_result.returncode == 0:
                    start_str = ps_result.stdout.strip()
                    return datetime.strptime(start_str, '%a %b %d %H:%M:%S %Y').timestamp()
        
        return None
        
    except Exception as e:
        print(f"⚠️ Error getting {process_type} start time for {capture_folder}: {e}")
        return None

def get_cached_process_start_time(capture_folder: str, process_type: str) -> float:
    """Get cached process start time, query only if not cached"""
    cache_key = f"{process_type}_{capture_folder}"
    
    # Return cached value if exists
    if cache_key in _process_start_cache:
        return _process_start_cache[cache_key]
    
    # Query and cache new start time
    start_time = get_process_start_time(capture_folder, process_type)
    if start_time:
        _process_start_cache[cache_key] = start_time
    
    return start_time

def clear_process_cache_if_stuck(capture_folder: str, process_type: str, status: str):
    """Clear cache when process is stuck/stopped (ready for restart detection)"""
    if status in ['stuck', 'stopped']:
        cache_key = f"{process_type}_{capture_folder}"
        _process_start_cache.pop(cache_key, None)  # Clear cache for restart

def calculate_process_working_uptime(capture_folder: str, process_type: str) -> int:
    """
    Calculate working uptime: process_start_time -> last_file_activity_time
    
    Args:
        capture_folder: Capture folder name (capture1, capture2, etc.)
        process_type: 'ffmpeg' or 'monitor'
        
    Returns:
        Working uptime in seconds (how long process worked before getting stuck)
    """
    try:
        # Get cached process start time (only queries if not cached)
        process_start_time = get_cached_process_start_time(capture_folder, process_type)
        
        if not process_start_time:
            return 0
            
        # Get last file activity time
        last_activity_time = None
        
        if process_type == 'ffmpeg':
            # Check FFmpeg output files
            capture_dir = f'/var/www/html/stream/{capture_folder}'
            if os.path.exists(capture_dir):
                # Get video segments and images
                ts_files = glob.glob(os.path.join(capture_dir, 'segment_*.ts'))
                captures_dir = os.path.join(capture_dir, 'captures')
                jpg_files = []
                if os.path.exists(captures_dir):
                    # Only use renamed files with timestamp format to avoid race condition
                    import re
                    all_jpg_files = glob.glob(os.path.join(captures_dir, '*.jpg'))
                    # Filter for renamed format: YYYYMMDD_HHMMSS_*.jpg
                    timestamp_pattern = re.compile(r'^\d{8}_\d{6}_.*\.jpg$')
                    jpg_files = [f for f in all_jpg_files if timestamp_pattern.match(os.path.basename(f))]
                
                all_files = ts_files + jpg_files
                if all_files:
                    last_activity_time = max([os.path.getmtime(f) for f in all_files])
                    
        elif process_type == 'monitor':
            # Check Monitor JSON files (only renamed ones to avoid race condition)
            captures_dir = f'/var/www/html/stream/{capture_folder}/captures'
            if os.path.exists(captures_dir):
                import re
                all_json_files = glob.glob(os.path.join(captures_dir, '*.json'))
                # Filter for renamed format: YYYYMMDD_HHMMSS_*.json
                timestamp_pattern = re.compile(r'^\d{8}_\d{6}_.*\.json$')
                json_files = [f for f in all_json_files if timestamp_pattern.match(os.path.basename(f))]
                if json_files:
                    last_activity_time = max([os.path.getmtime(f) for f in json_files])
        
        # Calculate working uptime: start -> last activity
        if last_activity_time and process_start_time:
            working_uptime = last_activity_time - process_start_time
            return int(max(0, working_uptime))
            
        return 0
        
    except Exception as e:
        print(f"⚠️ Error calculating {process_type} working uptime for {capture_folder}: {e}")
        return 0


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


def get_per_device_metrics(devices) -> List[Dict[str, Any]]:
    """
    Get per-device operational metrics WITHOUT recalculating device configurations.
    Only checks FFmpeg/Monitor status for incident detection.
    
    Args:
        devices: List of device objects (not configs)
        
    Returns:
        List of device operational metrics only
    """
    try:
        # Get FFmpeg and Monitor status once
        ffmpeg_status = check_ffmpeg_status()
        monitor_status = check_monitor_status()
        
        device_metrics = []
        
        for device in devices:
            # Use existing device properties (no recalculation)
            device_id = device.device_id
            device_name = device.device_name
            device_model = device.device_model
            device_port = getattr(device, 'device_port', 'unknown')
            
            # Extract capture folder from existing video_capture_path
            video_capture_path = getattr(device, 'video_capture_path', '')
            capture_folder = 'unknown'
            if video_capture_path:
                capture_folder = os.path.basename(video_capture_path.rstrip('/'))
            
            # Extract video device path
            video_device = getattr(device, 'video', 'unknown')
            
            # Extract per-device FFmpeg status by checking files directly in device path
            ffmpeg_device_status = 'unknown'
            ffmpeg_last_activity = None
            ffmpeg_uptime_seconds = 0
            
            # Check if FFmpeg processes are running (from overall status)
            ffmpeg_processes_running = ffmpeg_status.get('processes_running', 0) > 0
            
            # Check files directly in the device's video_capture_path
            if video_capture_path and os.path.exists(video_capture_path):
                current_time = time.time()
                cutoff_time = current_time - 10  # Only look for files from last 10 seconds
                
                # Check for recent images (.jpg files) in captures subdirectory - FFmpeg only needs JPG
                captures_dir = os.path.join(video_capture_path, 'captures')
                recent_jpg = []
                if os.path.exists(captures_dir):
                    try:
                        for entry in os.scandir(captures_dir):
                            if entry.is_file() and entry.name.endswith('.jpg'):
                                if entry.stat().st_mtime > cutoff_time:
                                    recent_jpg.append(entry.path)
                    except OSError:
                        pass
                
                total_recent_files = len(recent_jpg)
                
                if total_recent_files > 0:
                    ffmpeg_device_status = 'active'
                    # Get last activity time
                    if recent_jpg:
                        last_activity_timestamp = max([os.path.getmtime(f) for f in recent_jpg])
                        ffmpeg_last_activity = datetime.fromtimestamp(last_activity_timestamp, tz=timezone.utc).isoformat()
                        # Calculate working uptime: process start -> last file activity
                        ffmpeg_uptime_seconds = calculate_process_working_uptime(capture_folder, 'ffmpeg')
                else:
                    # No recent files - check if process is running
                    if ffmpeg_processes_running:
                        ffmpeg_device_status = 'stuck'  # Process running but no files
                    else:
                        ffmpeg_device_status = 'stopped'  # No process running
            else:
                # Video capture path doesn't exist
                if ffmpeg_processes_running:
                    ffmpeg_device_status = 'stuck'  # Process running but path doesn't exist
                else:
                    ffmpeg_device_status = 'stopped'  # No process running
            
            # Clear cache if FFmpeg is stuck/stopped (ready for restart detection)
            clear_process_cache_if_stuck(capture_folder, 'ffmpeg', ffmpeg_device_status)
            
            # Extract per-device Monitor status by checking JSON files directly in device path
            monitor_device_status = 'unknown'
            monitor_last_activity = None
            monitor_uptime_seconds = 0
            
            # Check if Monitor process is running (from overall status)
            monitor_process_running = monitor_status.get('process_running', False)
            
            # Check JSON files directly in the device's video_capture_path/captures
            if video_capture_path and os.path.exists(video_capture_path):
                captures_dir = os.path.join(video_capture_path, 'captures')
                if os.path.exists(captures_dir):
                    current_time = time.time()
                    cutoff_time = current_time - 10  # Only look for files from last 10 seconds
                    
                    # Check for recent JSON files
                    recent_json = []
                    try:
                        for entry in os.scandir(captures_dir):
                            if entry.is_file() and entry.name.endswith('.json'):
                                if entry.stat().st_mtime > cutoff_time:
                                    recent_json.append(entry.path)
                    except OSError:
                        pass
                    
                    if len(recent_json) > 0:
                        monitor_device_status = 'active'
                        # Get last activity time
                        last_activity_timestamp = max([os.path.getmtime(f) for f in recent_json])
                        monitor_last_activity = datetime.fromtimestamp(last_activity_timestamp, tz=timezone.utc).isoformat()
                        # Calculate working uptime: process start -> last file activity
                        monitor_uptime_seconds = calculate_process_working_uptime(capture_folder, 'monitor')
                    else:
                        # No recent JSON files - check if process is running
                        if monitor_process_running:
                            monitor_device_status = 'stuck'  # Process running but no JSON files
                        else:
                            monitor_device_status = 'stopped'  # No process running
                else:
                    # Captures directory doesn't exist
                    if monitor_process_running:
                        monitor_device_status = 'stuck'  # Process running but captures dir missing
                    else:
                        monitor_device_status = 'stopped'  # No process running
            else:
                # Video capture path doesn't exist
                if monitor_process_running:
                    monitor_device_status = 'stuck'  # Process running but path doesn't exist
                else:
                    monitor_device_status = 'stopped'  # No process running
            
            # Clear cache if Monitor is stuck/stopped (ready for restart detection)
            clear_process_cache_if_stuck(capture_folder, 'monitor', monitor_device_status)
            
            # Create lightweight device metrics (operational only)
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
        print(f"⚠️ Error getting lightweight device metrics: {e}")
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
        
        # Check recent file creation in capture directories (dynamic from config)
        capture_dirs = get_active_capture_dirs()
        
        current_time = time.time()
        cutoff_time = current_time - 10  # Only look for files from last 10 seconds
        
        for capture_dir in capture_dirs:
            if os.path.exists(capture_dir):
                device_name = os.path.basename(capture_dir)
                
                # Check for recent images (.jpg files) only - FFmpeg only needs JPG
                captures_dir = os.path.join(capture_dir, 'captures')
                recent_jpg = []
                if os.path.exists(captures_dir):
                    try:
                        for entry in os.scandir(captures_dir):
                            if entry.is_file() and entry.name.endswith('.jpg'):
                                if entry.stat().st_mtime > cutoff_time:
                                    recent_jpg.append(entry.path)
                    except OSError:
                        pass
                
                # Single line per folder with debug info
                print(f"🔍 [FFMPEG] {device_name}: {len(recent_jpg)} JPG files (last 10s) [path: {captures_dir}]")
                
                last_activity = max([os.path.getmtime(f) for f in recent_jpg]) if recent_jpg else 0
                status['recent_files'][device_name] = {
                    'video_segments': 0,  # Not checking TS files anymore
                    'images': len(recent_jpg),
                    'last_activity': last_activity
                }
        
        # Determine per-device status and overall status
        device_statuses = {}
        active_devices = 0
        
        for device_name, files_info in status['recent_files'].items():
            recent_files_count = files_info['images']  # Only check JPG files now
            
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
        
        # Check recent JSON file creation (dynamic from config)
        base_capture_dirs = get_active_capture_dirs()
        capture_dirs = [os.path.join(d, 'captures') for d in base_capture_dirs]
        
        current_time = time.time()
        cutoff_time = current_time - 10  # Only look for files from last 10 seconds
        
        for captures_dir in capture_dirs:
            if os.path.exists(captures_dir):
                device_name = os.path.basename(os.path.dirname(captures_dir))  # capture1, capture2, etc.
                
                # Check for recent JSON files - optimized
                recent_json = []
                try:
                    for entry in os.scandir(captures_dir):
                        if entry.is_file() and entry.name.endswith('.json'):
                            if entry.stat().st_mtime > cutoff_time:
                                recent_json.append(entry.path)
                except OSError:
                    pass
                
                # Single line per folder with debug info
                print(f"🔍 [MONITOR] {device_name}: {len(recent_json)} JSON files (last 10s) [path: {captures_dir}]")
                
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