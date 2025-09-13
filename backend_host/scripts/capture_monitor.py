#!/usr/bin/env python3
"""
Simple incident monitoring main loop
Glues detector + incident_manager together
"""
import os
import time
import glob
import logging
from datetime import datetime
from detector import detect_issues
from incident_manager import IncidentManager

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

def get_capture_directories():
    """Find active capture directories"""
    base_dirs = [
                "/var/www/html/stream/capture1/captures",
                "/var/www/html/stream/capture2/captures", 
                "/var/www/html/stream/capture3/captures",
                "/var/www/html/stream/capture4/captures"
            ]
    return [d for d in base_dirs if os.path.exists(d)]

def get_capture_folder(capture_dir):
    """Extract capture folder from path"""
    # /var/www/html/stream/capture1/captures -> capture1
    return os.path.basename(os.path.dirname(capture_dir))

def find_latest_frame(capture_dir):
    """Find most recent unanalyzed frame"""
    pattern = os.path.join(capture_dir, "capture_*.jpg")
    frames = [f for f in glob.glob(pattern) if '_thumbnail' not in f]
    
    if not frames:
        return None
    
    # Get most recent frame that doesn't have a JSON file
    frames.sort(key=os.path.getmtime, reverse=True)
    for frame in frames[:3]:  # Check last 3 frames
        json_file = frame.replace('.jpg', '.json')
        if not os.path.exists(json_file):
            return frame
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
    
    while True:
        for capture_dir in capture_dirs:
            capture_folder = get_capture_folder(capture_dir)
            frame_path = find_latest_frame(capture_dir)
            
            if frame_path:
                detection_result = detect_issues(frame_path)
                
                issues = []
                if detection_result.get('blackscreen', False):
                    issues.append('blackscreen')
                if detection_result.get('freeze', False):
                    issues.append('freeze')
                if not detection_result.get('audio', True):
                    issues.append('audio_loss')
                
                if issues:
                    logger.info(f"[{capture_folder}] Issues detected: {issues}")
                
                incident_manager.process_detection(capture_folder, capture_folder, detection_result, host_name)
                
                # Mark frame as analyzed
                json_file = frame_path.replace('.jpg', '.json')
                with open(json_file, 'w') as f:
                    f.write('{"analyzed": true}')
        
        time.sleep(2)  # Check every 2 seconds
        
if __name__ == '__main__':
    main() 
