"""
System Information Utilities

Utility functions for system monitoring, process management, and environment validation.
"""

import os
import psutil
import hashlib
import platform
import time
import subprocess
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from shared.src.lib.utils.supabase_utils import get_supabase_client

# Global cache for process start times
_process_start_cache = {}

# Speedtest shared cache
SPEEDTEST_CACHE = '/tmp/speedtest_cache.json'
CACHE_DURATION = 600  # 10 minutes

def get_network_speed_cached():
    """Get network speed with 10-min shared cache"""
    try:
        # Read shared cache
        if os.path.exists(SPEEDTEST_CACHE):
            with open(SPEEDTEST_CACHE, 'r') as f:
                cache = json.load(f)
            
            age = time.time() - cache['timestamp']
            if age < CACHE_DURATION:
                # Cache valid - reuse
                return {
                    'download_mbps': cache['download_mbps'],
                    'upload_mbps': cache['upload_mbps'],
                    'speedtest_last_run': datetime.fromtimestamp(cache['timestamp'], tz=timezone.utc).isoformat(),
                    'speedtest_age_seconds': int(age)
                }
        
        # Cache expired or missing - run test
        result = measure_network_speed()
        
        # Save to shared cache
        with open(SPEEDTEST_CACHE, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'download_mbps': result['download_mbps'],
                'upload_mbps': result['upload_mbps']
            }, f)
        
        return {
            'download_mbps': result['download_mbps'],
            'upload_mbps': result['upload_mbps'],
            'speedtest_last_run': datetime.now(timezone.utc).isoformat(),
            'speedtest_age_seconds': 0
        }
    except Exception as e:
        print(f"⚠️ [SPEEDTEST] Error: {e}")
        return {}  # Fail gracefully

def measure_network_speed():
    """Run speedtest with fallback strategies"""
    try:
        import speedtest
        print("🌐 [SPEEDTEST] Running network speed test...")
        
        # Initialize with timeout and secure mode disabled (helps with some ISPs)
        st = speedtest.Speedtest(secure=True)
        
        # Try to get best server with timeout
        try:
            st.get_best_server()
        except Exception as server_error:
            print(f"⚠️ [SPEEDTEST] Best server failed ({server_error}), trying manual server selection...")
            # Fallback: Try to get any available server
            servers = st.get_servers()
            if servers:
                # Use first available server
                st.get_servers(list(servers.keys())[:1])
        
        # Run tests with shorter timeout
        download = round(st.download(threads=None) / 1_000_000, 2)
        upload = round(st.upload(threads=None) / 1_000_000, 2)
        
        print(f"✅ [SPEEDTEST] Download: {download} Mbps, Upload: {upload} Mbps")
        return {
            'download_mbps': download,
            'upload_mbps': upload
        }
    except Exception as e:
        error_msg = str(e)
        # Check if it's a known blocking issue
        if '403' in error_msg or 'Forbidden' in error_msg:
            print(f"⚠️ [SPEEDTEST] Blocked by network/ISP (403 Forbidden) - skipping test")
        elif 'timeout' in error_msg.lower():
            print(f"⚠️ [SPEEDTEST] Timeout - network too slow or unavailable")
        else:
            print(f"❌ [SPEEDTEST] Failed: {e}")
        
        # Return zeros on failure (graceful degradation)
        return {'download_mbps': 0, 'upload_mbps': 0}

def get_capture_folder_size(capture_folder: str) -> str:
    """Get disk usage for a single capture folder"""
    try:
        capture_path = f'/var/www/html/stream/{capture_folder}'
        if not os.path.exists(capture_path):
            return 'N/A'
        result = subprocess.run(['du', '-sh', capture_path], capture_output=True, text=True, timeout=5)
        return result.stdout.split()[0] if result.returncode == 0 else 'unknown'
    except Exception:
        return 'unknown'

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
        else:
            print(f"🔍 [CONFIG] Configuration file not found: {config_file}, auto-discovering")
            # Auto-discover all capture directories
            capture_dirs = []
            stream_base = '/var/www/html/stream'
            if os.path.exists(stream_base):
                for entry in sorted(os.listdir(stream_base)):
                    if entry.startswith('capture') and entry[7:].isdigit():
                        capture_path = os.path.join(stream_base, entry)
                        if os.path.exists(capture_path):
                            capture_dirs.append(capture_path)
            
            # If no directories found, use hardcoded fallback
            if not capture_dirs:
                capture_dirs = [
                    '/var/www/html/stream/capture1',
                    '/var/www/html/stream/capture2', 
                    '/var/www/html/stream/capture3',
                    '/var/www/html/stream/capture4'
                ]
    except Exception as e:
        # Auto-discover on error or use hardcoded fallback
        capture_dirs = []
        try:
            stream_base = '/var/www/html/stream'
            if os.path.exists(stream_base):
                for entry in sorted(os.listdir(stream_base)):
                    if entry.startswith('capture') and entry[7:].isdigit():
                        capture_path = os.path.join(stream_base, entry)
                        if os.path.exists(capture_path):
                            capture_dirs.append(capture_path)
        except:
            pass
        
        # Final hardcoded fallback if auto-discovery failed
        if not capture_dirs:
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
            # Check FFmpeg output files (only JPG images)
            capture_dir = f'/var/www/html/stream/{capture_folder}'
            if os.path.exists(capture_dir):
                captures_dir = os.path.join(capture_dir, 'captures')
                if os.path.exists(captures_dir):
                    # Use find command to get recent files (last 1 minute max) - at 5fps, even 10s (50 files) is enough
                    try:
                        result = subprocess.run([
                            'find', captures_dir, '-name', 'capture_*.jpg', 
                            '!', '-name', '*_thumbnail.jpg', '-mmin', '-1', '-type', 'f'
                        ], capture_output=True, text=True, timeout=5)
                        
                        if result.returncode == 0 and result.stdout.strip():
                            # Get mtime for each file found (already filtered by time)
                            mtimes = []
                            for filepath in result.stdout.strip().split('\n'):
                                if filepath:
                                    try:
                                        mtimes.append(os.path.getmtime(filepath))
                                    except (FileNotFoundError, OSError):
                                        # File deleted between find and getmtime - skip it
                                        continue
                            
                            if mtimes:
                                last_activity_time = max(mtimes)
                    except (subprocess.TimeoutExpired, Exception) as e:
                        print(f"⚠️ Error finding recent FFmpeg files for {capture_folder}: {e}")
                        pass
                    
        elif process_type == 'monitor':
            # Check Monitor JSON files (sequential format to avoid race condition)
            captures_dir = f'/var/www/html/stream/{capture_folder}/captures'
            if os.path.exists(captures_dir):
                # Use find command to get recent files (last 1 minute max) - at 5fps, even 10s (50 files) is enough
                try:
                    result = subprocess.run([
                        'find', captures_dir, '-name', 'capture_*.json', '-mmin', '-1', '-type', 'f'
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        # Get mtime for each file found (already filtered by time)
                        mtimes = []
                        for filepath in result.stdout.strip().split('\n'):
                            if filepath:
                                try:
                                    mtimes.append(os.path.getmtime(filepath))
                                except (FileNotFoundError, OSError):
                                    # File deleted between find and getmtime - skip it
                                    continue
                        
                        if mtimes:
                            last_activity_time = max(mtimes)
                except (subprocess.TimeoutExpired, Exception) as e:
                    print(f"⚠️ Error finding recent Monitor files for {capture_folder}: {e}")
                    pass
        
        # Calculate working uptime: start -> last activity
        if last_activity_time and process_start_time:
            working_uptime = last_activity_time - process_start_time
            return int(max(0, working_uptime))
            
        return 0
        
    except Exception as e:
        print(f"⚠️ Error calculating {process_type} working uptime for {capture_folder}: {e}")
        return 0


def get_cpu_temperature():
    """Get CPU temperature for Raspberry Pi with fallback to thermal zones"""
    try:
        # Method 1: vcgencmd (Raspberry Pi specific)
        result = subprocess.run(['vcgencmd', 'measure_temp'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            temp_str = result.stdout.strip()  # "temp=42.8'C"
            temp_value = float(temp_str.split('=')[1].replace("'C", ""))
            return temp_value
    except Exception:
        pass
    
    try:
        # Method 2: thermal zone (more universal Linux)
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_millidegrees = int(f.read().strip())
            return temp_millidegrees / 1000.0
    except Exception:
        pass
    
    return None  # Temperature not available


def get_host_system_stats():
    """Get basic system statistics for host registration"""
    try:
        # Get service uptime from status checks
        ffmpeg_status = check_ffmpeg_status()
        monitor_status = check_monitor_status()
        ffmpeg_service_uptime = ffmpeg_status.get('service_uptime_seconds', 0)
        monitor_service_uptime = monitor_status.get('service_uptime_seconds', 0)
        
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'uptime_seconds': int(time.time() - psutil.boot_time()),
            'platform': platform.system(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'ffmpeg_service_uptime_seconds': ffmpeg_service_uptime,
            'monitor_service_uptime_seconds': monitor_service_uptime
        }
        
        # Add CPU temperature if available
        cpu_temp = get_cpu_temperature()
        if cpu_temp is not None:
            stats['cpu_temperature_celsius'] = round(cpu_temp, 1)
        
        # Add network speed (cached)
        network_speed = get_network_speed_cached()
        stats.update(network_speed)
        
        return stats
    except Exception as e:
        print(f"⚠️ Error getting system stats: {e}")
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'uptime_seconds': 0,
            'platform': 'unknown',
            'architecture': 'unknown',
            'python_version': 'unknown',
            'ffmpeg_service_uptime_seconds': 0,
            'monitor_service_uptime_seconds': 0
        }


def is_host_stuck():
    """
    Check if host has any stuck processes (FFmpeg or Monitor).
    Reuses existing status checking functions to avoid code duplication.
    
    Returns:
        bool: True if any process is stuck, False otherwise
    """
    try:
        # Get status using existing functions
        ffmpeg_status = check_ffmpeg_status()
        monitor_status = check_monitor_status()
        
        # Check if either process is stuck
        ffmpeg_stuck = ffmpeg_status.get('status') == 'stuck'
        monitor_stuck = monitor_status.get('status') == 'stuck'
        
        return ffmpeg_stuck or monitor_stuck
        
    except Exception as e:
        print(f"⚠️ Error checking if host is stuck: {e}")
        return False

def get_enhanced_system_stats():
    """Get enhanced system statistics including uptime and process status"""
    try:
        # Basic system stats
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # System uptime
        boot_time = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_time)
        
        # FFmpeg status check (includes service uptime)
        ffmpeg_status = check_ffmpeg_status()
        
        # Monitor status check (includes service uptime)
        monitor_status = check_monitor_status()
        
        # Extract service uptime from status checks
        ffmpeg_service_uptime = ffmpeg_status.get('service_uptime_seconds', 0)
        monitor_service_uptime = monitor_status.get('service_uptime_seconds', 0)
        
        stats = {
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
            'monitor_status': monitor_status,
            'ffmpeg_service_uptime_seconds': ffmpeg_service_uptime,
            'monitor_service_uptime_seconds': monitor_service_uptime
        }
        
        # Add CPU temperature if available
        cpu_temp = get_cpu_temperature()
        if cpu_temp is not None:
            stats['cpu_temperature_celsius'] = round(cpu_temp, 1)
        
        # Add network speed (cached)
        network_speed = get_network_speed_cached()
        stats.update(network_speed)
        
        return stats
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
            'monitor_status': {'status': 'unknown', 'error': str(e)},
            'ffmpeg_service_uptime_seconds': 0,
            'monitor_service_uptime_seconds': 0
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
            
            # Use existing FFmpeg status data (no duplicate file checking)
            if ffmpeg_status.get('recent_files', {}).get(capture_folder):
                device_files = ffmpeg_status['recent_files'][capture_folder]
                if device_files.get('images', 0) > 0:
                    ffmpeg_device_status = 'active'
                    ffmpeg_last_activity = datetime.now(tz=timezone.utc).isoformat()
                    ffmpeg_uptime_seconds = calculate_process_working_uptime(capture_folder, 'ffmpeg')
                else:
                    # No recent files - check if process is running
                    if ffmpeg_processes_running:
                        ffmpeg_device_status = 'stuck'  # Process running but no files
                    else:
                        ffmpeg_device_status = 'stopped'  # No process running
            else:
                # No data for this capture folder
                if ffmpeg_processes_running:
                    ffmpeg_device_status = 'stuck'  # Process running but no data for device
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
            
            # Use existing Monitor status data (no duplicate file checking)
            if monitor_status.get('recent_json_files', {}).get(capture_folder):
                device_json = monitor_status['recent_json_files'][capture_folder]
                if device_json.get('count', 0) > 0:
                    monitor_device_status = 'active'
                    monitor_last_activity = datetime.now(tz=timezone.utc).isoformat()
                    monitor_uptime_seconds = calculate_process_working_uptime(capture_folder, 'monitor')
                else:
                    # No recent JSON files - check if process is running
                    if monitor_process_running:
                        monitor_device_status = 'stuck'  # Process running but no JSON files
                    else:
                        monitor_device_status = 'stopped'  # No process running
            else:
                # No data for this capture folder
                if monitor_process_running:
                    monitor_device_status = 'stuck'  # Process running but no data for device
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
                'disk_usage': get_capture_folder_size(capture_folder),  # Disk usage for capture folder
                'ffmpeg_status': ffmpeg_device_status,
                'ffmpeg_last_activity': ffmpeg_last_activity,
                'ffmpeg_working_uptime_seconds': ffmpeg_uptime_seconds,  # Per-device working time before stuck
                'monitor_status': monitor_device_status,
                'monitor_last_activity': monitor_last_activity,
                'monitor_working_uptime_seconds': monitor_uptime_seconds  # Per-device working time before stuck
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
            'status': 'unknown',
            'service_start_time': None,
            'service_uptime_seconds': 0
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
        
        # Get service start time from systemctl
        try:
            result = subprocess.run(['systemctl', 'show', 'stream', '--property=ActiveEnterTimestamp'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                timestamp_line = result.stdout.strip()
                if timestamp_line.startswith('ActiveEnterTimestamp='):
                    timestamp_str = timestamp_line.split('=', 1)[1]
                    if timestamp_str and timestamp_str != '0':
                        # Parse systemd timestamp format
                        from datetime import datetime
                        service_start_time = datetime.strptime(timestamp_str, '%a %Y-%m-%d %H:%M:%S %Z').timestamp()
                        status['service_start_time'] = service_start_time
                        status['service_uptime_seconds'] = int(time.time() - service_start_time)
        except Exception as e:
            print(f"⚠️ Could not get stream service start time: {e}")
            pass
        
        # Check recent file creation in capture directories (dynamic from config)
        capture_dirs = get_active_capture_dirs()
        
        current_time = time.time()
        cutoff_time = current_time - 300  # Look for files from last 5 minutes
        
        for capture_dir in capture_dirs:
            if os.path.exists(capture_dir):
                device_name = os.path.basename(capture_dir)
                
                # Check for recent images (.jpg files) with sequential format only
                captures_dir = os.path.join(capture_dir, 'captures')
                recent_jpg_count = 0
                if os.path.exists(captures_dir):
                    try:
                        # Use find command to count sequential format files newer than 1 minute
                        result = subprocess.run([
                            'find', captures_dir, '-name', 'capture_*.jpg', '!', '-name', '*_thumbnail.jpg', '-mmin', '-1'
                        ], capture_output=True, text=True)
                        if result.returncode == 0:
                            recent_jpg_count = len([f for f in result.stdout.strip().split('\n') if f])
                    except Exception:
                        pass
                
                # Single line per folder with debug info including process status
                print(f"🔍 [FFMPEG] {device_name}: {recent_jpg_count} JPG files (last 1m) | Processes: {status['processes_running']}")
                
                status['recent_files'][device_name] = {
                    'images': recent_jpg_count,
                    'last_activity': time.time() if recent_jpg_count > 0 else 0
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
            'recent_files': {},
            'service_start_time': None,
            'service_uptime_seconds': 0
        }


def check_monitor_status():
    """Check capture monitor process and JSON file creation"""
    try:
        status = {
            'process_running': False,
            'recent_json_files': {},
            'status': 'unknown',
            'service_start_time': None,
            'service_uptime_seconds': 0
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
        
        # Get service start time from systemctl
        try:
            result = subprocess.run(['systemctl', 'show', 'monitor', '--property=ActiveEnterTimestamp'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                timestamp_line = result.stdout.strip()
                if timestamp_line.startswith('ActiveEnterTimestamp='):
                    timestamp_str = timestamp_line.split('=', 1)[1]
                    if timestamp_str and timestamp_str != '0':
                        # Parse systemd timestamp format
                        from datetime import datetime
                        service_start_time = datetime.strptime(timestamp_str, '%a %Y-%m-%d %H:%M:%S %Z').timestamp()
                        status['service_start_time'] = service_start_time
                        status['service_uptime_seconds'] = int(time.time() - service_start_time)
        except Exception as e:
            print(f"⚠️ Could not get monitor service start time: {e}")
            pass
        
        # Check recent JSON file creation (dynamic from config)
        base_capture_dirs = get_active_capture_dirs()
        capture_dirs = [os.path.join(d, 'captures') for d in base_capture_dirs]
        
        for captures_dir in capture_dirs:
            if os.path.exists(captures_dir):
                device_name = os.path.basename(os.path.dirname(captures_dir))  # capture1, capture2, etc.
                
                # Check for recent JSON files with sequential format
                recent_json_count = 0
                try:
                    # Use find command to count sequential format files newer than 1 minute
                    result = subprocess.run([
                        'find', captures_dir, '-name', 'capture_*.json', '-mmin', '-1'
                    ], capture_output=True, text=True)
                    if result.returncode == 0:
                        recent_json_count = len([f for f in result.stdout.strip().split('\n') if f])
                except Exception:
                    pass
                
                # Single line per folder with debug info including process status
                print(f"🔍 [MONITOR] {device_name}: {recent_json_count} JSON files (last 1m) | Process: {'running' if status['process_running'] else 'stopped'}")
                
                status['recent_json_files'][device_name] = {
                    'count': recent_json_count,
                    'last_activity': time.time() if recent_json_count > 0 else 0
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
            'recent_json_files': {},
            'service_start_time': None,
            'service_uptime_seconds': 0
        } 