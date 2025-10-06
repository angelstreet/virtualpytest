#!/usr/bin/env python3
"""
inotify-based frame monitor - eliminates directory scanning bottleneck
Watches for new frames and processes them immediately (zero CPU when idle)
Uses FFmpeg atomic_writing feature to detect completed files

Per-device queue processing:
- Each device has dedicated LIFO queue (stack) and worker thread
- LIFO = Process newest frames first (prevents stale analysis when backlog exists)
- Sequential processing within device prevents CPU spikes
- Parallel processing across devices maintains performance
- Queue size logging: Tracks backlog to detect performance issues
"""
import os
import sys
import json
import logging
import queue
from queue import LifoQueue
import threading
from datetime import datetime
import inotify.adapters

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import get_capture_base_directories, get_capture_storage_path, get_capture_folder, get_device_info_from_capture_folder
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
    """Event-driven frame monitor with per-device queue processing"""
    
    def __init__(self, capture_dirs, host_name):
        self.host_name = host_name
        self.incident_manager = IncidentManager()
        self.inotify = inotify.adapters.Inotify()
        self.last_processed_folder = None
        
        self.dir_to_info = {}
        self.device_queues = {}
        self.device_workers = {}
        
        for capture_dir in capture_dirs:
            # Use centralized path utilities (handles both hot and cold storage)
            capture_folder = get_capture_folder(capture_dir)
            
            if '/hot/' in capture_dir:
                # Hot storage: parent is /var/www/html/stream/capture1
                parent_dir = '/'.join(capture_dir.split('/')[:-2])
            else:
                # Cold storage: parent is /var/www/html/stream/capture1
                parent_dir = os.path.dirname(capture_dir)
            
            self.dir_to_info[capture_dir] = {
                'capture_dir': parent_dir,
                'capture_folder': capture_folder
            }
            
            if os.path.exists(capture_dir):
                self.inotify.add_watch(capture_dir)
                logger.info(f"Watching: {capture_dir} -> {capture_folder}")
            else:
                logger.warning(f"Directory not found: {capture_dir}")
            
            # LIFO queue (stack) - process newest frames first to avoid stale analysis
            work_queue = LifoQueue(maxsize=1000)
            self.device_queues[capture_folder] = work_queue
            
            worker = threading.Thread(
                target=self._device_worker,
                args=(capture_folder, work_queue),
                daemon=True,
                name=f"worker-{capture_folder}"
            )
            worker.start()
            self.device_workers[capture_folder] = worker
            logger.info(f"Started worker thread: {capture_folder}")
        
        self.process_existing_frames(capture_dirs)
    
    def _device_worker(self, capture_folder, work_queue):
        """Worker thread for sequential frame processing per device (LIFO - newest first)"""
        frame_count = 0
        while True:
            path, filename = work_queue.get()
            frame_count += 1
            
            # Log queue status every 25 frames (5 seconds at 5fps)
            if frame_count % 25 == 0:
                queue_size = work_queue.qsize()
                if queue_size > 50:
                    logger.warning(f"[{capture_folder}] ⚠️  Queue backlog: {queue_size} frames pending")
                elif queue_size > 0:
                    logger.info(f"[{capture_folder}] 📊 Queue size: {queue_size} frames")
            
            try:
                self.process_frame(path, filename)
            except Exception as e:
                logger.error(f"[{capture_folder}] Worker error: {e}")
            finally:
                work_queue.task_done()
    
    def process_existing_frames(self, capture_dirs):
        """Skip startup scan - inotify catches new frames immediately"""
        logger.info("Skipping startup scan (inotify will catch new frames immediately)")
        return
    
    def process_frame(self, captures_path, filename):
        """Process a single frame - called by both inotify and startup scan"""
        
        # Filter out temporary files and thumbnails
        # FFmpeg atomic_writing creates .tmp files first, then renames
        if '.tmp' in filename or '_thumbnail' in filename:
            return
        
        if not filename.startswith('capture_') or not filename.endswith('.jpg'):
            return
        
        frame_path = os.path.join(captures_path, filename)
        
        # CRITICAL: Write JSON metadata to metadata/ directory, not captures/
        # Get capture info to determine device folder
        if captures_path not in self.dir_to_info:
            logger.warning(f"Unknown capture path: {captures_path}")
            return
        
        info = self.dir_to_info[captures_path]
        capture_folder = info['capture_folder']
        
        # Get metadata path using centralized storage resolution (handles hot/cold automatically)
        metadata_path = get_capture_storage_path(capture_folder, 'metadata')
        
        # Ensure metadata directory exists with correct permissions (mode=0o777 for full access)
        # This ensures the archiver (running as different user) can move files
        os.makedirs(metadata_path, mode=0o777, exist_ok=True)
        
        # JSON file goes to metadata directory with same filename
        json_filename = filename.replace('.jpg', '.json')
        json_file = os.path.join(metadata_path, json_filename)
        
        # Skip if already analyzed
        if os.path.exists(json_file):
            return
        
        # Add visual separator when switching devices
        if self.last_processed_folder != capture_folder:
            logger.info("=" * 80)
            logger.info(f"📹 PROCESSING: {capture_folder.upper()}")
            logger.info("=" * 80)
            self.last_processed_folder = capture_folder
        
        logger.info(f"[{capture_folder}] 🔍 Analyzing: {filename}")
        
        try:
            # Analyze frame (blackscreen, freeze, audio) with performance timing
            detection_result = detect_issues(frame_path)
            
            # Log performance metrics (every 25 frames = 5 seconds)
            if detection_result and 'performance_ms' in detection_result:
                frame_num = int(filename.split('_')[1].split('.')[0]) if '_' in filename else 0
                if frame_num % 25 == 0:  # Log every 5 seconds
                    perf = detection_result['performance_ms']
                    logger.info(f"[{capture_folder}] ⏱️  Performance: "
                               f"image={perf.get('image_load', 0):.1f}ms, "
                               f"blackscreen={perf.get('blackscreen', 0):.1f}ms, "
                               f"freeze={perf.get('freeze', 0):.1f}ms, "
                               f"macroblocks={perf.get('macroblocks', 0):.1f}ms, "
                               f"audio={perf.get('audio', 0):.1f}ms{'(cached)' if perf.get('audio_cached') else ''}, "
                               f"subtitles={perf.get('subtitles', 0):.1f}ms, "
                               f"TOTAL={perf.get('total', 0):.1f}ms")
            
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
            if not is_host and detection_result and not detection_result.get('audio', True):
                issues.append('audio_loss')
            
            if detection_result and detection_result.get('subtitle_analysis'):
                subtitle_data = detection_result['subtitle_analysis']
                if subtitle_data.get('has_subtitles'):
                    text = subtitle_data.get('extracted_text', '')
                    lang = subtitle_data.get('detected_language', 'unknown')
                    if text:
                        logger.info(f"[{capture_folder}] 📝 Subtitles [{lang}]: '{text}'")
            
            if issues:
                logger.info(f"[{capture_folder}] Issues detected: {issues}")
            
            # Upload freeze frames to R2 ONCE per freeze event (not every frame)
            # Freeze is confirmed when detector returns 3 matching images
            if detection_result and detection_result.get('freeze', False):
                last_3_captures = detection_result.get('last_3_filenames', [])
                if last_3_captures:
                    # Get device state from incident manager (creates if doesn't exist)
                    device_state = self.incident_manager.get_device_state(capture_folder)
                    
                    # Check if we already uploaded for this freeze event
                    cached_r2_urls = device_state.get('freeze_r2_urls')
                    
                    if not cached_r2_urls:
                        # First freeze frame - upload to R2 with HHMM-based naming
                        now = datetime.now()
                        time_key = f"{now.hour:02d}{now.minute:02d}"  # "1300"
                        
                        # Generate thumbnail paths (FFmpeg creates these in thumbnails/ directory)
                        last_3_thumbnails = []
                        for capture_path in last_3_captures:
                            if os.path.exists(capture_path):
                                # Thumbnails are in /thumbnails/ not /captures/
                                # /var/www/html/stream/capture1/hot/captures/capture_000014342.jpg
                                # -> /var/www/html/stream/capture1/hot/thumbnails/capture_000014342_thumbnail.jpg
                                thumbnail_path = capture_path.replace('/captures/', '/thumbnails/').replace('.jpg', '_thumbnail.jpg')
                                if os.path.exists(thumbnail_path):
                                    last_3_thumbnails.append(thumbnail_path)
                                else:
                                    logger.warning(f"[{capture_folder}] Thumbnail not found: {thumbnail_path}, using original")
                                    last_3_thumbnails.append(capture_path)  # Fallback to original
                        
                        logger.info(f"[{capture_folder}] 🆕 Freeze confirmed (3 matching frames) - uploading {len(last_3_thumbnails)} thumbnails to R2 with time_key={time_key}")
                        r2_urls = self.incident_manager.upload_freeze_frames_to_r2(
                            last_3_captures, last_3_thumbnails, capture_folder, time_key, thumbnails_only=True
                        )
                        if r2_urls and r2_urls.get('thumbnail_urls'):
                            # Cache R2 URLs in device state for reuse during this freeze event
                            device_state['freeze_r2_urls'] = r2_urls['thumbnail_urls']
                            device_state['freeze_r2_images'] = r2_urls
                            # Replace last_3_thumbnails with R2 URLs (keep last_3_filenames as-is for reference)
                            detection_result['last_3_thumbnails'] = r2_urls['thumbnail_urls']
                            detection_result['r2_images'] = r2_urls
                            logger.info(f"[{capture_folder}] 📤 Uploaded {len(r2_urls['thumbnail_urls'])} freeze thumbnails to R2:")
                            for i, url in enumerate(r2_urls['thumbnail_urls']):
                                logger.info(f"[{capture_folder}]   Thumbnail {i}: {url}")
                        else:
                            logger.warning(f"[{capture_folder}] R2 upload failed, keeping local paths in JSON")
                    
                    else:
                        # Freeze ongoing - reuse cached R2 URLs from first upload
                        detection_result['last_3_thumbnails'] = cached_r2_urls
                        detection_result['r2_images'] = device_state.get('freeze_r2_images', {
                            'thumbnail_urls': cached_r2_urls
                        })
                        logger.info(f"[{capture_folder}] ♻️ Freeze ongoing - reusing cached R2 thumbnail URLs")
            
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
                    
                    # Debug: Log what we're saving for freeze
                    if detection_result.get('freeze'):
                        last_3_thumbnails = detection_result.get('last_3_thumbnails', [])
                        if last_3_thumbnails and isinstance(last_3_thumbnails, list) and last_3_thumbnails[0].startswith('http'):
                            logger.info(f"[{capture_folder}] 💾 Saving JSON with freeze R2 thumbnail URLs:")
                            for i, url in enumerate(last_3_thumbnails):
                                logger.info(f"[{capture_folder}]    Thumbnail {i}: {url}")
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
        """Main event loop - enqueue frames for worker threads"""
        logger.info("Starting inotify event loop (zero CPU when idle)...")
        logger.info("Waiting for FFmpeg to write new frames...")
        
        try:
            for event in self.inotify.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                
                if 'IN_MOVED_TO' in type_names:
                    if path in self.dir_to_info:
                        capture_folder = self.dir_to_info[path]['capture_folder']
                        logger.debug(f"[{capture_folder}] inotify event: {filename}")
                        
                        try:
                            work_queue = self.device_queues[capture_folder]
                            work_queue.put_nowait((path, filename))
                            
                            # Log if queue is building up (potential performance issue)
                            queue_size = work_queue.qsize()
                            if queue_size > 100:
                                logger.warning(f"[{capture_folder}] 🔴 Queue backlog growing: {queue_size}/1000 frames (processing too slow!)")
                            elif queue_size > 50 and queue_size % 25 == 0:
                                logger.warning(f"[{capture_folder}] 🟡 Queue backlog: {queue_size}/1000 frames")
                                
                        except queue.Full:
                            logger.error(f"[{capture_folder}] 🚨 Queue FULL (1000 frames), dropping: {filename}")
                        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
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
    logger.info("Queue Strategy: LIFO (newest frames first) - ensures real-time analysis")
    logger.info("=" * 80)
    
    host_name = os.getenv('USER', 'unknown')
    
    # Get base directories and resolve hot/cold paths automatically
    base_dirs = get_capture_base_directories()
    capture_dirs = []
    
    for base_dir in base_dirs:
        # Extract device folder name (e.g., 'capture1' from '/var/www/html/stream/capture1')
        device_folder = os.path.basename(base_dir)
        # Use centralized path resolution (handles hot/cold automatically)
        capture_path = get_capture_storage_path(device_folder, 'captures')
        capture_dirs.append(capture_path)
    
    logger.info(f"Found {len(capture_dirs)} capture directories")
    for capture_dir in capture_dirs:
        # Check if it's hot or cold storage
        storage_type = "HOT (RAM)" if '/hot/' in capture_dir else "COLD (SD)"
        capture_folder = get_capture_folder(capture_dir)  # Use centralized utility
        logger.info(f"Monitoring [{storage_type}]: {capture_dir} -> {capture_folder}")
    
    # Auto-resolve orphaned incidents for capture folders no longer being monitored
    # Use centralized utility to extract capture folder names (handles both hot and cold paths)
    monitored_capture_folders = []
    for capture_dir in capture_dirs:
        capture_folder = get_capture_folder(capture_dir)  # Use centralized utility
        monitored_capture_folders.append(capture_folder)
    
    incident_manager = IncidentManager()
    incident_manager.cleanup_orphaned_incidents(monitored_capture_folders, host_name)
    
    # Start monitoring (blocks forever, zero CPU when idle!)
    monitor = InotifyFrameMonitor(capture_dirs, host_name)
    monitor.run()
        
if __name__ == '__main__':
    main() 
