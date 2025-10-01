#!/usr/bin/env python3
"""
Simple incident monitoring main loop
Glues detector + incident_manager together
"""
import os
import time
import json
import logging
from datetime import datetime
from detector import detect_issues
from incident_manager import IncidentManager
from archive_utils import get_capture_directories, get_capture_folder

# Setup logging to /tmp/capture_monitor.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/capture_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def find_latest_frame(capture_dir):
    """Find most recent unanalyzed frame - OPTIMIZED with scandir"""
    try:
        entries = []
        with os.scandir(capture_dir) as it:
            for entry in it:
                if (entry.name.startswith('capture_') and 
                    entry.name.endswith('.jpg') and 
                    '_thumbnail' not in entry.name):
                    # Get stat info once during scandir (faster than separate os.path.getmtime)
                    entries.append((entry.path, entry.stat().st_mtime))
        
        if not entries:
            return None
        
        # Sort by mtime (already retrieved during scandir)
        entries.sort(key=lambda x: x[1], reverse=True)
        
        # Check last 3 frames for unanalyzed
        for frame_path, _ in entries[:3]:
            json_file = frame_path.replace('.jpg', '.json')
            if not os.path.exists(json_file):
                return frame_path
        return None
    except Exception as e:
        logger.error(f"Error finding latest frame in {capture_dir}: {e}")
        return None

def cleanup_logs_on_startup():
    """Clean up all monitoring log files on service restart for fresh debugging - EXACT COPY"""
    try:
        log_files = [
            '/tmp/capture_monitor.log',  # This service's log
            '/tmp/analysis.log',         # analyze_audio_video.py log
            '/tmp/alerts.log'            # alert_system.py log
        ]
        
        print(f"[@capture_monitor] Cleaning monitoring logs on service restart...")
        
        for log_file in log_files:
            if os.path.exists(log_file):
                # Truncate the file instead of deleting to avoid permission issues
                with open(log_file, 'w') as f:
                    f.write(f"=== LOG CLEANED ON MONITOR RESTART: {datetime.now().isoformat()} ===\n")
                print(f"[@capture_monitor] ✓ Cleaned: {log_file}")
            else:
                print(f"[@capture_monitor] ○ Not found (will be created): {log_file}")
                
        print(f"[@capture_monitor] Log cleanup complete - fresh logs for debugging")
                
    except Exception as e:
        print(f"[@capture_monitor] Warning: Could not clean log files: {e}")

def main():
    """Main monitoring loop"""
    cleanup_logs_on_startup()  # Clean logs on startup - EXACT COPY
    
    logger.info("Starting simple incident monitor...")
    
    host_name = os.getenv('USER', 'unknown')
    incident_manager = IncidentManager()
    capture_dirs = get_capture_directories()
    
    logger.info(f"Monitoring {len(capture_dirs)} capture directories")
    for capture_dir in capture_dirs:
        capture_folder = get_capture_folder(capture_dir)
        logger.info(f"Monitoring: {capture_dir} -> {capture_folder}")
    
    # Auto-resolve orphaned incidents for capture folders no longer being monitored
    monitored_capture_folders = [get_capture_folder(d) for d in capture_dirs]
    incident_manager.cleanup_orphaned_incidents(monitored_capture_folders, host_name)
    
    while True:
        for capture_dir in capture_dirs:
            capture_folder = get_capture_folder(capture_dir)
            frame_path = find_latest_frame(capture_dir)
            
            if frame_path:
                detection_result = detect_issues(frame_path)
                
                issues = []
                if detection_result and detection_result.get('blackscreen', False):
                    issues.append('blackscreen')
                if detection_result and detection_result.get('freeze', False):
                    issues.append('freeze')
                if detection_result and not detection_result.get('audio', True):
                    issues.append('audio_loss')
                
                if issues:
                    logger.info(f"[{capture_folder}] Issues detected: {issues}")
                
                incident_manager.process_detection(capture_folder, detection_result, host_name)
                
                # Save complete analysis data to JSON file
                json_file = frame_path.replace('.jpg', '.json')
                try:
                    if detection_result:
                        analysis_data = {
                            "analyzed": True,
                            **detection_result  # Include all detection data (freeze, blackscreen, audio, etc.)
                        }
                    else:
                        logger.error(f"[{capture_folder}] ERROR: detection_result is None/empty, saving fallback")
                        analysis_data = {
                            "analyzed": True,
                            "error": "detection_result_was_none"
                        }
                    
                    with open(json_file, 'w') as f:
                        json.dump(analysis_data, f, indent=2)
                        
                except Exception as e:
                    logger.error(f"[{capture_folder}] Error saving analysis data: {e}")
                    # Fallback to simple marker
                    with open(json_file, 'w') as f:
                        f.write('{"analyzed": true, "error": "failed_to_save_full_data"}')
        
        time.sleep(1)  # Check every 1 seconds
        
if __name__ == '__main__':
    main() 
