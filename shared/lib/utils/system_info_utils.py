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


def get_host_system_stats():
    """Get basic system statistics for host registration"""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
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
        
        # Determine overall status
        if status['processes_running'] > 0:
            total_recent_files = sum(dev['video_segments'] + dev['images'] for dev in status['recent_files'].values())
            if total_recent_files > 0:
                status['status'] = 'active'
            else:
                status['status'] = 'stuck'  # Processes running but no recent files
        else:
            status['status'] = 'stopped'
            
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
        
        # Determine overall status
        if status['process_running']:
            total_recent_json = sum(dev['count'] for dev in status['recent_json_files'].values())
            if total_recent_json > 0:
                status['status'] = 'active'
            else:
                status['status'] = 'stuck'  # Process running but no recent JSON files
        else:
            status['status'] = 'stopped'
            
        return status
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'process_running': False,
            'recent_json_files': {}
        } 