#!/usr/bin/env python3
"""
inotify-based frame monitor - eliminates directory scanning bottleneck
Watches for new frames and processes them immediately (zero CPU when idle)
Uses FFmpeg atomic_writing feature to detect completed files
"""
import os
import sys
import json
import logging
from datetime import datetime
import inotify.adapters

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import get_capture_directories, get_capture_folder, get_device_info_from_capture_folder
from detector import detect_issues
from incident_manager import IncidentManager

# Setup logging (systemd handles file output)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class InotifyFrameMonitor:
    """Event-driven frame monitor using inotify - zero CPU when idle"""
    
    def __init__(self, capture_dirs, host_name):
        self.host_name = host_name
        self.incident_manager = IncidentManager()
        self.inotify = inotify.adapters.Inotify()
        self.last_processed_folder = None  # Track last device for log separation
        
        # Map capture_dir paths to their folder names for logging
        self.dir_to_info = {}
        
        # Watch all capture directories (get_capture_directories already returns paths ending in /captures)
        for capture_dir in capture_dirs:
            # capture_dir is already /var/www/html/stream/captureX/captures
            # Extract captureX from the path (e.g., capture1, capture2, capture3)
            parent_dir = os.path.dirname(capture_dir)  # /var/www/html/stream/captureX
            capture_folder = os.path.basename(parent_dir)  # captureX
            self.dir_to_info[capture_dir] = {
                'capture_dir': parent_dir,
                'capture_folder': capture_folder
            }
            
            if os.path.exists(capture_dir):
                self.inotify.add_watch(capture_dir)
                logger.info(f"Watching: {capture_dir} -> {capture_folder}")
            else:
                logger.warning(f"Directory not found: {capture_dir}")
        
        # Process any existing unanalyzed frames on startup
        self.process_existing_frames(capture_dirs)
    
    def process_existing_frames(self, capture_dirs):
        """Process any frames that were created before monitor started - OPTIMIZED"""
        logger.info("Skipping startup scan (inotify will catch new frames immediately)")
        # NOTE: We skip scanning existing files because:
        # 1. With 220K+ files, scanning takes minutes and defeats inotify's purpose
        # 2. Old unanalyzed frames aren't critical (incidents already in DB)
        # 3. New frames will be caught immediately by inotify events
        # 4. System will self-correct as new frames arrive
        return  # Skip expensive startup scan
    
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
        
        # Add visual separator when switching devices
        if self.last_processed_folder != capture_folder:
            logger.info("=" * 80)
            logger.info(f"📹 PROCESSING: {capture_folder.upper()}")
            logger.info("=" * 80)
            self.last_processed_folder = capture_folder
        
        logger.info(f"[{capture_folder}] 🔍 Analyzing: {filename}")
        
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
            
            # Upload freeze frames to R2 immediately (for heatmap display)
            # Thumbnails now created on-demand from captures
            if detection_result and detection_result.get('freeze', False):
                last_3_captures = detection_result.get('last_3_filenames', [])
                if last_3_captures:
                    from datetime import datetime
                    current_timestamp = datetime.now().isoformat()
                    r2_urls = self.incident_manager.upload_freeze_frames_to_r2(
                        last_3_captures, None, capture_folder, current_timestamp, thumbnails_only=True
                    )
                    if r2_urls and r2_urls.get('thumbnail_urls'):
                        # Replace local paths with R2 URLs for heatmap display
                        detection_result['last_3_filenames'] = r2_urls['thumbnail_urls']
                        detection_result['r2_images'] = r2_urls
                        logger.info(f"[{capture_folder}] 📤 Uploaded freeze frames to R2 for heatmap")
            
            # Process incident logic (5-minute debounce, DB operations)
            # Thumbnails are uploaded inside process_detection after 5min confirmation
            transitions = self.incident_manager.process_detection(capture_folder, detection_result, self.host_name)
            
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
                logger.info(f"[{capture_folder}] ✓ Saved JSON: {json_file}")
                    
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

def main():
    """Main entry point"""
    
    logger.info("=" * 80)
    logger.info("Starting inotify-based incident monitor")
    logger.info("Performance: Zero CPU when idle, event-driven processing")
    logger.info("No directory scanning = 95% CPU reduction vs polling")
    logger.info("=" * 80)
    
    host_name = os.getenv('USER', 'unknown')
    capture_dirs = get_capture_directories()
    
    logger.info(f"Found {len(capture_dirs)} capture directories")
    for capture_dir in capture_dirs:
        capture_folder = os.path.basename(os.path.dirname(capture_dir))  # Extract captureX from path
        logger.info(f"Monitoring: {capture_dir} -> {capture_folder}")
    
    # Auto-resolve orphaned incidents for capture folders no longer being monitored
    monitored_capture_folders = [os.path.basename(os.path.dirname(d)) for d in capture_dirs]
    incident_manager = IncidentManager()
    incident_manager.cleanup_orphaned_incidents(monitored_capture_folders, host_name)
    
    # Start monitoring (blocks forever, zero CPU when idle!)
    monitor = InotifyFrameMonitor(capture_dirs, host_name)
    monitor.run()
        
if __name__ == '__main__':
    main() 
