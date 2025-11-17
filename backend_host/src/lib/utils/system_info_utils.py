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
import fcntl
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from shared.src.lib.utils.supabase_utils import get_supabase_client
from shared.src.lib.utils.storage_path_utils import get_capture_storage_path, get_capture_base_directories

# Global cache for process start times
_process_start_cache = {}

# Speedtest shared cache
SPEEDTEST_CACHE = '/tmp/speedtest_cache.json'
CACHE_DURATION = 600  # 10 minutes


def count_recent_files(
    directory: str,
    pattern: str,
    max_age_seconds: int = 60,
    exclude_pattern: Optional[str] = None
) -> int:
    r"""
    Count files matching pattern modified within max_age_seconds.
    Fast O(n) scan with early filtering - no sorting or subprocess overhead.
    
    Args:
        directory: Directory path to scan
        pattern: Regex pattern to match filenames (e.g., r'^capture_.*\.jpg$')
        max_age_seconds: Only count files modified within this timeframe
        exclude_pattern: Optional regex pattern to exclude files (e.g., r'_thumbnail\.jpg$')
    
    Returns:
        Count of matching recent files
    """
    if not os.path.exists(directory):
        return 0
    
    try:
        compiled_pattern = re.compile(pattern)
        compiled_exclude = re.compile(exclude_pattern) if exclude_pattern else None
        count = 0
        now = time.time()
        
        for entry in os.scandir(directory):
            try:
                if not entry.is_file(follow_symlinks=False):
                    continue
                    
                if not compiled_pattern.match(entry.name):
                    continue
                    
                if compiled_exclude and compiled_exclude.search(entry.name):
                    continue
                
                if now - entry.stat().st_mtime < max_age_seconds:
                    count += 1
                    
            except (FileNotFoundError, OSError):
                # File deleted during scan - skip it
                continue
        
        return count
        
    except Exception:
        return 0


def get_last_file_mtime(
    directory: str,
    pattern: str,
    max_age_seconds: int = 60,
    exclude_pattern: Optional[str] = None
) -> Optional[float]:
    r"""
    Get the most recent modification time of files matching pattern.
    Fast O(n) scan with early filtering - no sorting or subprocess overhead.
    
    Args:
        directory: Directory path to scan
        pattern: Regex pattern to match filenames (e.g., r'^capture_.*\.jpg$')
        max_age_seconds: Only consider files modified within this timeframe
        exclude_pattern: Optional regex pattern to exclude files (e.g., r'_thumbnail\.jpg$')
    
    Returns:
        Most recent mtime (timestamp), or None if no matching files found
    """
    if not os.path.exists(directory):
        return None
    
    try:
        compiled_pattern = re.compile(pattern)
        compiled_exclude = re.compile(exclude_pattern) if exclude_pattern else None
        mtimes = []
        now = time.time()
        
        for entry in os.scandir(directory):
            try:
                if not entry.is_file(follow_symlinks=False):
                    continue
                    
                if not compiled_pattern.match(entry.name):
                    continue
                    
                if compiled_exclude and compiled_exclude.search(entry.name):
                    continue
                
                mtime = entry.stat().st_mtime
                if now - mtime < max_age_seconds:
                    mtimes.append(mtime)
                    
            except (FileNotFoundError, OSError):
                # File deleted during scan - skip it
                continue
        
        return max(mtimes) if mtimes else None
        
    except Exception:
        return None


def get_files_by_pattern(
    directory: str,
    pattern: str,
    exclude_pattern: Optional[str] = None,
    full_path: bool = True,
    min_mtime: Optional[float] = None,
    max_mtime: Optional[float] = None
) -> List[str]:
    r"""
    Get all files matching pattern using fast os.scandir (no subprocess overhead).
    Replacement for subprocess find commands - 2-5x faster, no timeout risk.
    
    Args:
        directory: Directory path to scan
        pattern: Regex pattern to match filenames (e.g., r'^segment_.*\.ts$')
        exclude_pattern: Optional regex pattern to exclude files
        full_path: If True, return full paths; if False, return just filenames
        min_mtime: Optional minimum modification time (Unix timestamp) - only files newer than this
        max_mtime: Optional maximum modification time (Unix timestamp) - only files older than this
    
    Returns:
        List of matching file paths (or names if full_path=False)
    
    Example:
        # Replace: subprocess.run(['find', dir, '-name', 'segment_*.ts', '-type', 'f'])
        # With: get_files_by_pattern(dir, r'^segment_.*\.ts$')
        
        # Get only files from last 24 hours:
        cutoff = time.time() - (24 * 3600)
        files = get_files_by_pattern(dir, r'^segment_.*\.ts$', min_mtime=cutoff)
    """
    if not os.path.exists(directory):
        return []
    
    try:
        compiled_pattern = re.compile(pattern)
        compiled_exclude = re.compile(exclude_pattern) if exclude_pattern else None
        files = []
        
        for entry in os.scandir(directory):
            try:
                if not entry.is_file(follow_symlinks=False):
                    continue
                    
                if not compiled_pattern.match(entry.name):
                    continue
                    
                if compiled_exclude and compiled_exclude.search(entry.name):
                    continue
                
                # Filter by modification time if specified
                if min_mtime is not None or max_mtime is not None:
                    mtime = entry.stat().st_mtime
                    if min_mtime is not None and mtime < min_mtime:
                        continue
                    if max_mtime is not None and mtime > max_mtime:
                        continue
                
                if full_path:
                    files.append(entry.path)
                else:
                    files.append(entry.name)
                    
            except (FileNotFoundError, OSError):
                # File deleted during scan - skip it
                continue
        
        return files
        
    except Exception:
        return []


def get_network_speed_cached(skip_if_no_cache=False):
    """
    Get network speed with 10-min shared cache
    
    Args:
        skip_if_no_cache: If True, return empty dict if cache doesn't exist (for startup optimization)
    """
    try:
        # Read shared cache with file locking
        if os.path.exists(SPEEDTEST_CACHE):
            try:
                with open(SPEEDTEST_CACHE, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                    try:
                        cache = json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
                
                age = time.time() - cache['timestamp']
                if age < CACHE_DURATION:
                    # Validate cached data - skip if invalid
                    download = cache.get('download_mbps')
                    upload = cache.get('upload_mbps')
                    
                    if download is None or download == 0 or upload is None or upload == 0:
                        print("⚠️ [SPEEDTEST] Cached data is invalid (0 or None) - will rerun test")
                        try:
                            os.remove(SPEEDTEST_CACHE)
                        except:
                            pass
                        # Continue to run new test below
                    else:
                        # Cache valid with good data - reuse
                        return {
                            'download_mbps': download,
                            'upload_mbps': upload,
                            'speedtest_last_run': datetime.fromtimestamp(cache['timestamp'], tz=timezone.utc).isoformat(),
                            'speedtest_age_seconds': int(age)
                        }
            except (json.JSONDecodeError, KeyError) as cache_error:
                # Cache corrupted - delete and regenerate
                print(f"⚠️ [SPEEDTEST] Corrupted cache detected: {cache_error} - regenerating...")
                try:
                    os.remove(SPEEDTEST_CACHE)
                except:
                    pass
        
        # Skip speedtest if requested (for startup optimization)
        if skip_if_no_cache:
            print("🌐 [SPEEDTEST] Skipping initial speedtest (will run in background)")
            # Start async speedtest in background thread
            import threading
            thread = threading.Thread(target=_run_speedtest_async, daemon=True)
            thread.start()
            return {}
        
        # Cache expired, missing, or corrupted - run test
        result = measure_network_speed()
        
        # Skip saving/returning if speedtest failed (returns None/0 values)
        if not result or result.get('download_mbps') is None or result.get('download_mbps') == 0:
            print("⚠️ [SPEEDTEST] Test failed - skipping cache and metrics storage")
            return {}
        
        # Save to shared cache with file locking
        with open(SPEEDTEST_CACHE, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
            try:
                json.dump({
                    'timestamp': time.time(),
                    'download_mbps': result['download_mbps'],
                    'upload_mbps': result['upload_mbps']
                }, f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
        
        return {
            'download_mbps': result['download_mbps'],
            'upload_mbps': result['upload_mbps'],
            'speedtest_last_run': datetime.now(timezone.utc).isoformat(),
            'speedtest_age_seconds': 0
        }
    except Exception as e:
        print(f"⚠️ [SPEEDTEST] Error: {e}")
        return {}  # Fail gracefully

def _run_speedtest_async():
    """Run speedtest in background and save to cache"""
    try:
        result = measure_network_speed()
        
        # Skip saving if speedtest failed
        if not result or result.get('download_mbps') is None or result.get('download_mbps') == 0:
            print("⚠️ [SPEEDTEST] Background test failed - skipping cache")
            return
        
        # Save to shared cache with file locking
        with open(SPEEDTEST_CACHE, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
            try:
                json.dump({
                    'timestamp': time.time(),
                    'download_mbps': result['download_mbps'],
                    'upload_mbps': result['upload_mbps']
                }, f)
                print("✅ [SPEEDTEST] Background test completed and cached")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
    except Exception as e:
        print(f"⚠️ [SPEEDTEST] Background test error: {e}")

def measure_network_speed():
    """Run speedtest using curl-based server discovery (works with rate-limited APIs)"""
    try:
        import speedtest
        print("🌐 [SPEEDTEST] Running network speed test...")
        
        # Fetch servers using curl (bypasses rate-limited library API)
        print("🔍 [SPEEDTEST] Fetching server list via API...")
        result = subprocess.run(
            ['curl', '-s', '-m', '10', 'https://www.speedtest.net/api/js/servers?engine=js&limit=5'],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0 or not result.stdout:
            print(f"❌ [SPEEDTEST] Failed to fetch server list")
            return {'download_mbps': None, 'upload_mbps': None}
        
        # Parse JSON response
        servers_data = json.loads(result.stdout)
        if not servers_data or len(servers_data) == 0:
            print(f"❌ [SPEEDTEST] No servers available")
            return {'download_mbps': None, 'upload_mbps': None}
        
        # Use first available server (already sorted by distance)
        best_server = servers_data[0]
        print(f"✅ [SPEEDTEST] Using server: {best_server['sponsor']} ({best_server['name']}, {best_server['country']})")
        
        # Initialize speedtest and manually set the server
        st = speedtest.Speedtest(secure=True)
        st.best = {
            'url': best_server['url'],
            'lat': best_server['lat'],
            'lon': best_server['lon'],
            'name': best_server['name'],
            'country': best_server['country'],
            'cc': best_server['cc'],
            'sponsor': best_server['sponsor'],
            'id': best_server['id'],
            'host': best_server['host'],
            'd': best_server['distance']
        }
        
        # Run speed tests
        download = round(st.download(threads=None) / 1_000_000, 2)
        upload = round(st.upload(threads=None) / 1_000_000, 2)
        
        print(f"✅ [SPEEDTEST] Download: {download} Mbps, Upload: {upload} Mbps")
        return {
            'download_mbps': download,
            'upload_mbps': upload
        }
    except subprocess.TimeoutExpired:
        print(f"⚠️ [SPEEDTEST] Timeout fetching server list")
        return {'download_mbps': None, 'upload_mbps': None}
    except json.JSONDecodeError as e:
        print(f"❌ [SPEEDTEST] Invalid server list response: {e}")
        return {'download_mbps': None, 'upload_mbps': None}
    except Exception as e:
        error_msg = str(e)
        if '403' in error_msg or 'Forbidden' in error_msg:
            print(f"⚠️ [SPEEDTEST] Blocked by network/ISP (403 Forbidden)")
        elif 'timeout' in error_msg.lower():
            print(f"⚠️ [SPEEDTEST] Timeout during speed test")
        else:
            print(f"❌ [SPEEDTEST] Failed: {e}")
        
        return {'download_mbps': None, 'upload_mbps': None}

def get_capture_folder_size(capture_folder: str) -> str:
    """Get disk usage for a single capture folder"""
    try:
        from shared.src.lib.utils.storage_path_utils import get_device_base_path
        capture_path = get_device_base_path(capture_folder)
        if not os.path.exists(capture_path):
            return 'N/A'
        result = subprocess.run(['du', '-sh', capture_path], capture_output=True, text=True, timeout=5)
        return result.stdout.split()[0] if result.returncode == 0 else 'unknown'
    except Exception:
        return 'unknown'

def get_process_start_time(capture_folder: str, process_type: str) -> float:
    """Get process start time from system"""
    try:
        # Force C locale for consistent date parsing regardless of system locale
        env = os.environ.copy()
        env['LC_ALL'] = 'C'
        
        if process_type == 'ffmpeg':
            # Find FFmpeg process for this capture folder
            result = subprocess.run(['pgrep', '-f', f'ffmpeg.*{capture_folder}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                pid = result.stdout.strip().split('\n')[0]  # Get first PID
                # Get process start time using ps with C locale for English output
                ps_result = subprocess.run(['ps', '-o', 'lstart=', '-p', pid], 
                                         capture_output=True, text=True, env=env)
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
                # Get process start time using ps with C locale for English output
                ps_result = subprocess.run(['ps', '-o', 'lstart=', '-p', pid], 
                                         capture_output=True, text=True, env=env)
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
            captures_dir = get_capture_storage_path(capture_folder, 'captures')
            last_activity_time = get_last_file_mtime(
                captures_dir,
                r'^capture_.*\.jpg$',
                max_age_seconds=20, #need to cover stream restart
                exclude_pattern=r'_thumbnail\.jpg$'
            )
                    
        elif process_type == 'monitor':
            metadata_dir = get_capture_storage_path(capture_folder, 'metadata')
            last_activity_time = get_last_file_mtime(
                metadata_dir,
                r'^capture_.*\.json$',
                max_age_seconds=20  #need to cover stream restart
            )
        
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


def get_host_system_stats(skip_speedtest=False):
    """
    Get basic system statistics for host registration
    
    Args:
        skip_speedtest: If True, skip speedtest if no cache exists (for startup optimization)
    """
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
        
        # Add disk I/O write speed tracking
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                # Store current counters for next calculation
                if hasattr(get_host_system_stats, '_last_disk_io'):
                    last_io = get_host_system_stats._last_disk_io
                    # Calculate MB written per second (uses cpu_percent's 1-sec interval)
                    bytes_written = disk_io.write_bytes - last_io.write_bytes
                    stats['disk_write_mb_per_sec'] = round(bytes_written / 1024 / 1024, 2)
                else:
                    stats['disk_write_mb_per_sec'] = 0  # First run baseline
                
                # Store for next call
                get_host_system_stats._last_disk_io = disk_io
        except Exception:
            stats['disk_write_mb_per_sec'] = 0
        
        # Add load average (1, 5, 15 minute averages)
        load_avg = os.getloadavg()
        stats['load_average_1m'] = round(load_avg[0], 2)
        stats['load_average_5m'] = round(load_avg[1], 2)
        stats['load_average_15m'] = round(load_avg[2], 2)
        
        # Add CPU temperature if available
        cpu_temp = get_cpu_temperature()
        if cpu_temp is not None:
            stats['cpu_temperature_celsius'] = round(cpu_temp, 1)
        
        # Add network speed (cached) - skip speedtest during startup if requested
        network_speed = get_network_speed_cached(skip_if_no_cache=skip_speedtest)
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
            'monitor_service_uptime_seconds': 0,
            'load_average_1m': 0,
            'load_average_5m': 0,
            'load_average_15m': 0
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

def get_enhanced_system_stats(skip_speedtest=False):
    """
    Get enhanced system statistics including uptime and process status
    
    Args:
        skip_speedtest: If True, skip speedtest if no cache exists (for startup optimization)
    """
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
        
        # Add disk I/O write speed tracking
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                # Store current counters for next calculation
                if hasattr(get_enhanced_system_stats, '_last_disk_io'):
                    last_io = get_enhanced_system_stats._last_disk_io
                    # Calculate MB written per second (uses cpu_percent's 1-sec interval)
                    bytes_written = disk_io.write_bytes - last_io.write_bytes
                    stats['disk_write_mb_per_sec'] = round(bytes_written / 1024 / 1024, 2)
                else:
                    stats['disk_write_mb_per_sec'] = 0  # First run baseline
                
                # Store for next call
                get_enhanced_system_stats._last_disk_io = disk_io
        except Exception:
            stats['disk_write_mb_per_sec'] = 0
        
        # Add load average (1, 5, 15 minute averages)
        load_avg = os.getloadavg()
        stats['load_average_1m'] = round(load_avg[0], 2)
        stats['load_average_5m'] = round(load_avg[1], 2)
        stats['load_average_15m'] = round(load_avg[2], 2)
        
        # Add CPU temperature if available
        cpu_temp = get_cpu_temperature()
        if cpu_temp is not None:
            stats['cpu_temperature_celsius'] = round(cpu_temp, 1)
        
        # Add network speed (cached) - skip speedtest during startup if requested
        network_speed = get_network_speed_cached(skip_if_no_cache=skip_speedtest)
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
            'monitor_service_uptime_seconds': 0,
            'load_average_1m': 0,
            'load_average_5m': 0,
            'load_average_15m': 0
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
        
        capture_dirs = get_capture_base_directories()
        
        for capture_dir in capture_dirs:
            if os.path.exists(capture_dir):
                device_name = os.path.basename(capture_dir)
                captures_dir = get_capture_storage_path(capture_dir, 'captures')
                recent_jpg_count = count_recent_files(
                    captures_dir,
                    r'^capture_.*\.jpg$',
                    max_age_seconds=2,
                    exclude_pattern=r'_thumbnail\.jpg$'
                )
                
                # Single line per folder with debug info including process status
                print(f"🔍 [FFMPEG] {device_name}: {recent_jpg_count} JPG files (last 10s) | Processes: {status['processes_running']}")
                
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
        
        capture_base_dirs = get_capture_base_directories()
        
        for capture_dir in capture_base_dirs:
            if os.path.exists(capture_dir):
                device_name = os.path.basename(capture_dir)
                metadata_dir = get_capture_storage_path(capture_dir, 'metadata')
                recent_json_count = count_recent_files(
                    metadata_dir,
                    r'^capture_.*\.json$',
                    max_age_seconds=2
                )
                
                # Single line per folder with debug info including process status
                print(f"🔍 [MONITOR] {device_name}: {recent_json_count} JSON files (last 10s) | Process: {'running' if status['process_running'] else 'stopped'}")
                
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