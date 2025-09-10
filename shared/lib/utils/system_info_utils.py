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
            
            # Extract per-device FFmpeg status using capture folder
            ffmpeg_device_status = 'unknown'
            ffmpeg_last_activity = None
            ffmpeg_uptime_seconds = 0
            
            # Check if FFmpeg processes are running (from overall status)
            ffmpeg_processes_running = ffmpeg_status.get('processes_running', 0) > 0
            
            print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): FFmpeg processes running = {ffmpeg_processes_running}")
            print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): FFmpeg recent_files keys = {list(ffmpeg_status.get('recent_files', {}).keys())}")
            
            if ffmpeg_status.get('recent_files', {}).get(capture_folder):
                device_files = ffmpeg_status['recent_files'][capture_folder]
                print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Device files = {device_files}")
                
                if device_files.get('images', 0) > 0 or device_files.get('video_segments', 0) > 0:
                    ffmpeg_device_status = 'active'
                    last_activity_timestamp = device_files.get('last_activity', 0)
                    if last_activity_timestamp > 0:
                        ffmpeg_last_activity = datetime.fromtimestamp(last_activity_timestamp, tz=timezone.utc).isoformat()
                        # Calculate working uptime: process start -> last file activity
                        ffmpeg_uptime_seconds = calculate_process_working_uptime(capture_folder, 'ffmpeg')
                    print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): FFmpeg status = ACTIVE (files found)")
                else:
                    # No recent files - check if process is running
                    if ffmpeg_processes_running:
                        ffmpeg_device_status = 'stuck'  # Process running but no files
                        print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): FFmpeg status = STUCK (process running, no files)")
                    else:
                        ffmpeg_device_status = 'stopped'  # No process running
                        print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): FFmpeg status = STOPPED (no process, no files)")
            else:
                # No files data for this capture folder
                print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): No files data for this capture folder")
                if ffmpeg_processes_running:
                    ffmpeg_device_status = 'stuck'  # Process running but no files for this device
                    print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): FFmpeg status = STUCK (process running, no data for device)")
                else:
                    ffmpeg_device_status = 'stopped'  # No process running
                    print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): FFmpeg status = STOPPED (no process, no data)")
            
            # Clear cache if FFmpeg is stuck/stopped (ready for restart detection)
            clear_process_cache_if_stuck(capture_folder, 'ffmpeg', ffmpeg_device_status)
            
            # Extract per-device Monitor status using capture folder
            monitor_device_status = 'unknown'
            monitor_last_activity = None
            monitor_uptime_seconds = 0
            
            # Check if Monitor process is running (from overall status)
            monitor_process_running = monitor_status.get('process_running', False)
            
            print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Monitor process running = {monitor_process_running}")
            print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Monitor recent_json_files keys = {list(monitor_status.get('recent_json_files', {}).keys())}")
            
            if monitor_status.get('recent_json_files', {}).get(capture_folder):
                device_json = monitor_status['recent_json_files'][capture_folder]
                print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Device JSON = {device_json}")
                
                if device_json.get('count', 0) > 0:
                    monitor_device_status = 'active'
                    last_activity_timestamp = device_json.get('last_activity', 0)
                    if last_activity_timestamp > 0:
                        monitor_last_activity = datetime.fromtimestamp(last_activity_timestamp, tz=timezone.utc).isoformat()
                        # Calculate working uptime: process start -> last file activity
                        monitor_uptime_seconds = calculate_process_working_uptime(capture_folder, 'monitor')
                    print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Monitor status = ACTIVE (JSON files found)")
                else:
                    # No recent JSON files - check if process is running
                    if monitor_process_running:
                        monitor_device_status = 'stuck'  # Process running but no JSON files
                        print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Monitor status = STUCK (process running, no JSON files)")
                    else:
                        monitor_device_status = 'stopped'  # No process running
                        print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Monitor status = STOPPED (no process, no JSON files)")
            else:
                # No JSON files data for this capture folder
                print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): No JSON files data for this capture folder")
                if monitor_process_running:
                    monitor_device_status = 'stuck'  # Process running but no JSON files for this device
                    print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Monitor status = STUCK (process running, no data for device)")
                else:
                    monitor_device_status = 'stopped'  # No process running
                    print(f"🔍 [DEVICE_DEBUG] {device_name} ({capture_folder}): Monitor status = STOPPED (no process, no data)")
            
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
        
        print(f"🔍 [FFMPEG_DEBUG] Found {len(ffmpeg_processes)} FFmpeg processes running")
        
        # Check recent file creation in capture directories
        capture_dirs = [
            '/var/www/html/stream/capture1',
            '/var/www/html/stream/capture2', 
            '/var/www/html/stream/capture3',
            '/var/www/html/stream/capture4'
        ]
        
        current_time = time.time()
        print(f"🔍 [FFMPEG_DEBUG] Current time: {current_time} ({datetime.fromtimestamp(current_time)})")
        
        for capture_dir in capture_dirs:
            if os.path.exists(capture_dir):
                device_name = os.path.basename(capture_dir)
                print(f"🔍 [FFMPEG_DEBUG] Checking {device_name} in {capture_dir}")
                
                # Check for recent video segments (.ts files)
                ts_files = glob.glob(os.path.join(capture_dir, 'segment_*.ts'))
                print(f"🔍 [FFMPEG_DEBUG] {device_name}: Found {len(ts_files)} total .ts files")
                
                recent_ts = []
                for f in ts_files:
                    mtime = os.path.getmtime(f)
                    age_seconds = current_time - mtime
                    if age_seconds < 300:  # 5 minutes
                        recent_ts.append(f)
                    print(f"🔍 [FFMPEG_DEBUG] {device_name}: {os.path.basename(f)} - age: {age_seconds:.1f}s ({'RECENT' if age_seconds < 300 else 'OLD'})")
                
                # Check for recent images (.jpg files) - FIXED PATTERN
                captures_dir = os.path.join(capture_dir, 'captures')
                recent_jpg = []
                if os.path.exists(captures_dir):
                    # Use broader pattern to catch all .jpg files (not just capture_*.jpg)
                    jpg_files = glob.glob(os.path.join(captures_dir, '*.jpg'))
                    print(f"🔍 [FFMPEG_DEBUG] {device_name}: Found {len(jpg_files)} total .jpg files in captures/")
                    
                    for f in jpg_files:
                        mtime = os.path.getmtime(f)
                        age_seconds = current_time - mtime
                        if age_seconds < 300:  # 5 minutes
                            recent_jpg.append(f)
                        print(f"🔍 [FFMPEG_DEBUG] {device_name}: {os.path.basename(f)} - age: {age_seconds:.1f}s ({'RECENT' if age_seconds < 300 else 'OLD'})")
                else:
                    print(f"🔍 [FFMPEG_DEBUG] {device_name}: captures/ directory does not exist")
                
                print(f"🔍 [FFMPEG_DEBUG] {device_name}: Recent files - TS: {len(recent_ts)}, JPG: {len(recent_jpg)}")
                
                status['recent_files'][device_name] = {
                    'video_segments': len(recent_ts),
                    'images': len(recent_jpg),
                    'last_activity': max([os.path.getmtime(f) for f in (recent_ts + recent_jpg)]) if (recent_ts + recent_jpg) else 0
                }
        
        # Determine per-device status and overall status
        device_statuses = {}
        active_devices = 0
        stuck_devices = 0
        
        print(f"🔍 [FFMPEG_DEBUG] Determining device statuses...")
        for device_name, files_info in status['recent_files'].items():
            recent_files_count = files_info['video_segments'] + files_info['images']
            print(f"🔍 [FFMPEG_DEBUG] {device_name}: Recent files count = {recent_files_count} (TS: {files_info['video_segments']}, JPG: {files_info['images']})")
            
            if recent_files_count > 0:
                device_statuses[device_name] = 'active'
                active_devices += 1
                print(f"🔍 [FFMPEG_DEBUG] {device_name}: Status = ACTIVE")
            else:
                device_statuses[device_name] = 'stopped'  # No recent files for this device
                print(f"🔍 [FFMPEG_DEBUG] {device_name}: Status = STOPPED (no recent files)")
        
        status['device_statuses'] = device_statuses
        
        # Overall status logic
        print(f"🔍 [FFMPEG_DEBUG] Overall status calculation: processes_running={status['processes_running']}, active_devices={active_devices}")
        if status['processes_running'] > 0:
            if active_devices > 0:
                status['status'] = 'active'  # At least one device is active
                print(f"🔍 [FFMPEG_DEBUG] Overall status = ACTIVE (processes running + active devices)")
            else:
                status['status'] = 'stuck'  # Processes running but no devices producing files
                print(f"🔍 [FFMPEG_DEBUG] Overall status = STUCK (processes running but no active devices)")
        else:
            status['status'] = 'stopped'  # No processes running
            print(f"🔍 [FFMPEG_DEBUG] Overall status = STOPPED (no processes running)")
            
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
        
        print(f"🔍 [MONITOR_DEBUG] Found {len(monitor_processes)} monitor processes running")
        
        # Check recent JSON file creation
        capture_dirs = [
            '/var/www/html/stream/capture1/captures',
            '/var/www/html/stream/capture2/captures',
            '/var/www/html/stream/capture3/captures', 
            '/var/www/html/stream/capture4/captures'
        ]
        
        current_time = time.time()
        print(f"🔍 [MONITOR_DEBUG] Current time: {current_time} ({datetime.fromtimestamp(current_time)})")
        
        for captures_dir in capture_dirs:
            if os.path.exists(captures_dir):
                device_name = os.path.basename(os.path.dirname(captures_dir))  # capture1, capture2, etc.
                print(f"🔍 [MONITOR_DEBUG] Checking {device_name} in {captures_dir}")
                
                # Check for recent JSON files - FIXED PATTERN
                json_files = glob.glob(os.path.join(captures_dir, '*.json'))
                print(f"🔍 [MONITOR_DEBUG] {device_name}: Found {len(json_files)} total .json files")
                
                recent_json = []
                for f in json_files:
                    mtime = os.path.getmtime(f)
                    age_seconds = current_time - mtime
                    if age_seconds < 300:  # 5 minutes
                        recent_json.append(f)
                    print(f"🔍 [MONITOR_DEBUG] {device_name}: {os.path.basename(f)} - age: {age_seconds:.1f}s ({'RECENT' if age_seconds < 300 else 'OLD'})")
                
                print(f"🔍 [MONITOR_DEBUG] {device_name}: Recent JSON files: {len(recent_json)}")
                
                status['recent_json_files'][device_name] = {
                    'count': len(recent_json),
                    'last_activity': max([os.path.getmtime(f) for f in recent_json]) if recent_json else 0
                }
        
        # Determine per-device status and overall status
        device_statuses = {}
        active_devices = 0
        
        print(f"🔍 [MONITOR_DEBUG] Determining device statuses...")
        for device_name, json_info in status['recent_json_files'].items():
            print(f"🔍 [MONITOR_DEBUG] {device_name}: Recent JSON count = {json_info['count']}")
            
            if json_info['count'] > 0:
                device_statuses[device_name] = 'active'
                active_devices += 1
                print(f"🔍 [MONITOR_DEBUG] {device_name}: Status = ACTIVE")
            else:
                device_statuses[device_name] = 'stopped'  # No recent JSON files for this device
                print(f"🔍 [MONITOR_DEBUG] {device_name}: Status = STOPPED (no recent JSON files)")
        
        status['device_statuses'] = device_statuses
        
        # Overall status logic
        print(f"🔍 [MONITOR_DEBUG] Overall status calculation: process_running={status['process_running']}, active_devices={active_devices}")
        if status['process_running']:
            if active_devices > 0:
                status['status'] = 'active'  # At least one device is active
                print(f"🔍 [MONITOR_DEBUG] Overall status = ACTIVE (process running + active devices)")
            else:
                status['status'] = 'stuck'  # Process running but no devices producing JSON files
                print(f"🔍 [MONITOR_DEBUG] Overall status = STUCK (process running but no active devices)")
        else:
            status['status'] = 'stopped'  # No process running
            print(f"🔍 [MONITOR_DEBUG] Overall status = STOPPED (no process running)")
            
        return status
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'process_running': False,
            'recent_json_files': {}
        } 