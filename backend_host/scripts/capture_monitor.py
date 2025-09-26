#!/usr/bin/env python3
"""
Simple incident monitoring main loop
Glues detector + incident_manager together
"""
import os
import time
import glob
import json
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
                "/var/www/html/stream/capture4/captures",
                "/var/www/html/stream/capture5/captures",
                "/var/www/html/stream/capture6/captures"
            ]
    return [d for d in base_dirs if os.path.exists(d)]

def get_capture_folder(capture_dir):
    """Extract capture folder from path"""
    # /var/www/html/stream/capture1/captures -> capture1
    return os.path.basename(os.path.dirname(capture_dir))

def update_archive_manifest(capture_dir):
    """Generate archive.m3u8 from all available segments"""
    try:
        capture_folder = get_capture_folder(capture_dir)
        stream_dir = capture_dir.replace('/captures', '')  # /var/www/html/stream/capture1
        
        # Find all segment files
        segments = glob.glob(os.path.join(stream_dir, 'segment_*.ts'))
        if not segments:
            return
            
        # Sort segments by number (segment_001.ts, segment_002.ts, etc.)
        segments.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
        
        # Generate archive manifest content
        manifest_content = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            "#EXT-X-TARGETDURATION:4",
            "#EXT-X-MEDIA-SEQUENCE:1"
        ]
        
        for segment in segments:
            segment_name = os.path.basename(segment)
            manifest_content.extend([
                "#EXTINF:1.000000,",
                segment_name
            ])
        
        manifest_content.append("#EXT-X-ENDLIST")
        
        # Write archive manifest
        archive_path = os.path.join(stream_dir, 'archive.m3u8')
        with open(archive_path + '.tmp', 'w') as f:
            f.write('\n'.join(manifest_content))
        
        # Atomic move to prevent partial reads
        os.rename(archive_path + '.tmp', archive_path)
        
        logger.debug(f"[{capture_folder}] Updated archive manifest with {len(segments)} segments")
        
    except Exception as e:
        logger.error(f"Error updating archive manifest for {capture_dir}: {e}")

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
            
            # Update archive manifest every cycle (2 seconds)
            update_archive_manifest(capture_dir)
            
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
        
        time.sleep(2)  # Check every 2 seconds
        
if __name__ == '__main__':
    main() 
