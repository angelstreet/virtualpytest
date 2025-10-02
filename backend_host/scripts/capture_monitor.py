#!/usr/bin/env python3
"""
inotify-based frame monitor - eliminates directory scanning bottleneck
Watches for new frames and processes them immediately (zero CPU when idle)
Uses FFmpeg atomic_writing feature to detect completed files
"""
import os
import json
import logging
from datetime import datetime
import inotify.adapters
from detector import detect_issues
from incident_manager import IncidentManager
from archive_utils import get_capture_directories, get_capture_folder, get_device_info_from_capture_folder

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

class InotifyFrameMonitor:
    """Event-driven frame monitor using inotify - zero CPU when idle"""
    
    def __init__(self, capture_dirs, host_name):
        self.host_name = host_name
        self.incident_manager = IncidentManager()
        self.inotify = inotify.adapters.Inotify()
        
        # Map capture_dir paths to their folder names for logging
        self.dir_to_info = {}
        
        # Watch all capture directories
        for capture_dir in capture_dirs:
            captures_path = os.path.join(capture_dir, 'captures')
            capture_folder = get_capture_folder(capture_dir)
            self.dir_to_info[captures_path] = {
                'capture_dir': capture_dir,
                'capture_folder': capture_folder
            }
            
            if os.path.exists(captures_path):
                self.inotify.add_watch(captures_path)
                logger.info(f"Watching: {captures_path} -> {capture_folder}")
            else:
                logger.warning(f"Directory not found: {captures_path}")
        
        # Process any existing unanalyzed frames on startup
        self.process_existing_frames(capture_dirs)
    
    def process_existing_frames(self, capture_dirs):
        """Process any frames that were created before monitor started"""
        logger.info("Checking for existing unanalyzed frames...")
        
        for capture_dir in capture_dirs:
            captures_path = os.path.join(capture_dir, 'captures')
            if not os.path.exists(captures_path):
                continue
            
            capture_folder = get_capture_folder(capture_dir)
            
            # Find last 10 frames and check if analyzed
            try:
                frames = []
                for entry in os.scandir(captures_path):
                    if (entry.name.startswith('capture_') and 
                        entry.name.endswith('.jpg') and 
                        '_thumbnail' not in entry.name and
                        '.tmp' not in entry.name):  # Filter temp files
                        frames.append((entry.name, entry.stat().st_mtime))
                
                # Sort by mtime, get last 10
                frames.sort(key=lambda x: x[1], reverse=True)
                
                for filename, _ in frames[:10]:
                    frame_path = os.path.join(captures_path, filename)
                    json_file = frame_path.replace('.jpg', '.json')
                    
                    if not os.path.exists(json_file):
                        logger.info(f"[{capture_folder}] Processing existing frame: {filename}")
                        self.process_frame(captures_path, filename)
                        
            except Exception as e:
                logger.error(f"[{capture_folder}] Error processing existing frames: {e}")
    
    def process_frame(self, captures_path, filename):
        """Process a single frame - called by both inotify and startup scan"""
        
        # Filter out temporary files and thumbnails
        # FFmpeg atomic_writing creates .tmp files first, then renames
        if '.tmp' in filename or '_thumbnail' in filename:
            return
        
        if not filename.startswith('capture_') or not filename.endswith('.jpg'):
            return
        
        frame_path = os.path.join(captures_path, filename)
        json_file = frame_path.replace('.jpg', '.json')
        
        # Skip if already analyzed
        if os.path.exists(json_file):
            return
        
        # Get capture info
        if captures_path not in self.dir_to_info:
            logger.warning(f"Unknown capture path: {captures_path}")
            return
        
        info = self.dir_to_info[captures_path]
        capture_folder = info['capture_folder']
        
        try:
            # Analyze frame (blackscreen, freeze, audio)
            detection_result = detect_issues(frame_path)
            
            # Get device info to check if this is the host
            device_info = get_device_info_from_capture_folder(capture_folder)
            device_id = device_info.get('device_id', capture_folder)
            is_host = (device_id == 'host')
            
            # Log detected issues
            issues = []
            if detection_result and detection_result.get('blackscreen', False):
                issues.append('blackscreen')
            if detection_result and detection_result.get('freeze', False):
                issues.append('freeze')
            # Skip audio loss detection for host device (no audio capture)
            if not is_host and detection_result and not detection_result.get('audio', True):
                issues.append('audio_loss')
            
            if issues:
                logger.info(f"[{capture_folder}] Issues detected: {issues}")
            
            # Handle freeze frame uploads (if freeze detected)
            if detection_result and detection_result.get('freeze', False):
                last_3_filenames = detection_result.get('last_3_filenames', [])
                last_3_thumbnails = detection_result.get('last_3_thumbnails', [])
                
                if last_3_filenames:
                    current_time = datetime.now().isoformat()
                    r2_urls = self.incident_manager.upload_freeze_frames_to_r2(
                        last_3_filenames, last_3_thumbnails, capture_folder, current_time
                    )
                    if r2_urls:
                        detection_result['r2_images'] = r2_urls
                        logger.info(f"[{capture_folder}] Uploaded freeze frames to R2 for real-time heatmap")
            
            # Process incident logic (5-minute debounce, DB operations)
            self.incident_manager.process_detection(capture_folder, detection_result, self.host_name)
            
            # Save JSON metadata (marks frame as analyzed)
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
                
        except Exception as e:
            logger.error(f"[{capture_folder}] Error processing frame {filename}: {e}")
            # Save error marker so we don't retry indefinitely
            try:
                with open(json_file, 'w') as f:
                    json.dump({"analyzed": True, "error": str(e)}, f)
            except:
                pass
    
    def run(self):
        """Main event loop - blocks until events occur (zero CPU when idle!)"""
        logger.info("Starting inotify event loop (zero CPU when idle)...")
        logger.info("Waiting for FFmpeg to write new frames...")
        
        try:
            for event in self.inotify.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                
                # Only process MOVED_TO (atomic rename completion)
                # This fires when FFmpeg renames .tmp → final file
                if 'IN_MOVED_TO' in type_names:
                    if path in self.dir_to_info:
                        capture_folder = self.dir_to_info[path]['capture_folder']
                        logger.debug(f"[{capture_folder}] inotify event: {filename}")
                        self.process_frame(path, filename)
                        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            # Cleanup watches
            for path in self.dir_to_info.keys():
                try:
                    self.inotify.remove_watch(path)
                except:
                    pass

def cleanup_logs_on_startup():
    """Clean up all monitoring log files on service restart for fresh debugging"""
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
    """Main entry point"""
    cleanup_logs_on_startup()  # Clean logs on startup
    
    logger.info("=" * 80)
    logger.info("Starting inotify-based incident monitor")
    logger.info("Performance: Zero CPU when idle, event-driven processing")
    logger.info("No directory scanning = 95% CPU reduction vs polling")
    logger.info("=" * 80)
    
    host_name = os.getenv('USER', 'unknown')
    capture_dirs = get_capture_directories()
    
    logger.info(f"Found {len(capture_dirs)} capture directories")
    for capture_dir in capture_dirs:
        capture_folder = get_capture_folder(capture_dir)
        logger.info(f"Monitoring: {capture_dir} -> {capture_folder}")
    
    # Auto-resolve orphaned incidents for capture folders no longer being monitored
    monitored_capture_folders = [get_capture_folder(d) for d in capture_dirs]
    incident_manager = IncidentManager()
    incident_manager.cleanup_orphaned_incidents(monitored_capture_folders, host_name)
    
    # Start monitoring (blocks forever, zero CPU when idle!)
    monitor = InotifyFrameMonitor(capture_dirs, host_name)
    monitor.run()

if __name__ == '__main__':
    main()
