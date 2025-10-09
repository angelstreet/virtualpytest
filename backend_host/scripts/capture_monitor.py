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

# CRITICAL: Limit CPU threads BEFORE importing OpenCV/NumPy
# OpenCV/NumPy/OpenBLAS create many threads by default
import os
os.environ['OMP_NUM_THREADS'] = '2'          # OpenMP
os.environ['MKL_NUM_THREADS'] = '2'          # Intel MKL
os.environ['OPENBLAS_NUM_THREADS'] = '2'     # OpenBLAS
os.environ['NUMEXPR_NUM_THREADS'] = '2'      # NumExpr

import sys
import json
import logging
import queue
import time
from queue import LifoQueue
import threading
from datetime import datetime
import inotify.adapters

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import (
    get_capture_base_directories, 
    get_capture_storage_path, 
    get_capture_folder, 
    get_device_info_from_capture_folder,
    get_metadata_path,
    get_captures_path
)
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
        
        self.dir_to_info = {}
        self.device_queues = {}
        self.device_workers = {}
        
        for capture_dir in capture_dirs:
            # Use centralized path utilities (handles both hot and cold storage)
            capture_folder = get_capture_folder(capture_dir)
            
            # Get parent directory (device base path)
            if '/hot/' in capture_dir:
                # Hot storage: /var/www/html/stream/capture1/hot/captures
                # Parent is /var/www/html/stream/capture1
                parent_dir = '/'.join(capture_dir.split('/')[:-2])
            else:
                # Cold storage: /var/www/html/stream/capture1/captures
                # Parent is /var/www/html/stream/capture1
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
        prev_queue_size = 0
        while True:
            path, filename = work_queue.get()
            frame_count += 1
            queue_size = work_queue.qsize()
            
            if frame_count % 25 == 0 and queue_size > 50:
                logger.warning(f"[{capture_folder}] ⚠️  Queue backlog: {queue_size} frames pending")
            
            try:
                self.process_frame(path, filename, queue_size)
            except Exception as e:
                logger.error(f"[{capture_folder}] Worker error: {e}")
            finally:
                prev_queue_size = queue_size
                work_queue.task_done()
    
    def process_existing_frames(self, capture_dirs):
        """Skip startup scan - inotify catches new frames immediately"""
        logger.info("Skipping startup scan (inotify will catch new frames immediately)")
        return
    
    def _append_to_chunk(self, capture_folder, filename, analysis_data, fps=5):
        """
        INCREMENTAL ARCHIVAL: Append frame to correct 10min chunk immediately.
        
        This creates/updates chunks in real-time as frames arrive, eliminating:
        - Need to accumulate 3000 files
        - Batch merging complexity
        - Gaps from lost intermediate files
        
        Args:
            capture_folder: Device folder (e.g., 'capture1')
            filename: Frame filename (e.g., 'capture_000012345.jpg')
            analysis_data: Frame metadata to append
            fps: Frames per second (default 5)
        """
        import json
        import fcntl
        from pathlib import Path
        
        try:
            # Extract sequence from filename
            sequence = int(filename.split('_')[1].split('.')[0])
            
            # Calculate chunk location
            hour = (sequence // (3600 * fps)) % 24
            chunk_index = ((sequence % (3600 * fps)) // (600 * fps))  # 0-5
            
            # Get device base path
            from shared.src.lib.utils.storage_path_utils import get_capture_storage_path
            base_path = f"/var/www/html/stream/{capture_folder}"
            
            # Chunk path: /var/www/html/stream/capture1/metadata/13/chunk_10min_2.json
            chunk_dir = os.path.join(base_path, 'metadata', str(hour))
            os.makedirs(chunk_dir, exist_ok=True)
            chunk_path = os.path.join(chunk_dir, f'chunk_10min_{chunk_index}.json')
            
            # Prepare frame data (extract only what we need for archive)
            frame_data = {
                'sequence': sequence,
                'timestamp': analysis_data.get('timestamp'),
                'filename': analysis_data.get('filename'),
                'blackscreen': analysis_data.get('blackscreen', False),
                'blackscreen_percentage': analysis_data.get('blackscreen_percentage', 0),
                'freeze': analysis_data.get('freeze', False),
                'freeze_diffs': analysis_data.get('freeze_diffs', []),
                'audio': analysis_data.get('audio', True),
                'volume_percentage': analysis_data.get('volume_percentage', 0),
                'mean_volume_db': analysis_data.get('mean_volume_db', -100.0)
            }
            
            # Atomic append with file locking
            lock_path = chunk_path + '.lock'
            with open(lock_path, 'w') as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                
                try:
                    # Read existing chunk
                    if os.path.exists(chunk_path):
                        with open(chunk_path, 'r') as f:
                            chunk_data = json.load(f)
                    else:
                        # Create new chunk
                        chunk_data = {
                            'hour': hour,
                            'chunk_index': chunk_index,
                            'frames_count': 0,
                            'frames': []
                        }
                    
                    # Check if frame already exists (avoid duplicates)
                    existing_sequences = {f.get('sequence') for f in chunk_data['frames']}
                    if sequence not in existing_sequences:
                        # Append frame
                        chunk_data['frames'].append(frame_data)
                        chunk_data['frames_count'] = len(chunk_data['frames'])
                        
                        # Update time range
                        if chunk_data['frames']:
                            chunk_data['start_time'] = chunk_data['frames'][0].get('timestamp')
                            chunk_data['end_time'] = chunk_data['frames'][-1].get('timestamp')
                        
                        # Sort by sequence (keep chronological order)
                        chunk_data['frames'].sort(key=lambda x: x.get('sequence', 0))
                        
                        # Write back atomically
                        with open(chunk_path + '.tmp', 'w') as f:
                            json.dump(chunk_data, f, indent=2)
                        os.rename(chunk_path + '.tmp', chunk_path)
                
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            
            # Clean up lock file
            try:
                os.remove(lock_path)
            except:
                pass
                
        except Exception as e:
            # Non-critical failure - individual JSON still saved
            raise Exception(f"Chunk append error: {e}")
    
    def process_frame(self, captures_path, filename, queue_size=0):
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
        
        # Use convenience function - no manual path building!
        metadata_path = get_metadata_path(capture_folder)
        
        # Ensure metadata directory exists with correct permissions (mode=0o777 for full access)
        # This ensures the archiver (running as different user) can move files
        os.makedirs(metadata_path, mode=0o777, exist_ok=True)
        
        # JSON file goes to metadata directory with same filename
        json_filename = filename.replace('.jpg', '.json')
        json_file = os.path.join(metadata_path, json_filename)
        
        # Skip if already analyzed
        if os.path.exists(json_file):
            return
        
        try:
            detection_result = detect_issues(frame_path, queue_size=queue_size)
            
            # Get device info to check if this is the host
            device_info = get_device_info_from_capture_folder(capture_folder)
            device_id = device_info.get('device_id', capture_folder)
            is_host = (device_id == 'host')
            
            issues = []
            if detection_result and detection_result.get('blackscreen', False):
                issues.append('blackscreen')
            if detection_result and detection_result.get('freeze', False):
                issues.append('freeze')
            if not is_host and detection_result and not detection_result.get('audio', True):
                issues.append('audio_loss')
            
            if issues:
                logger.info(f"[{capture_folder}] Issues: {issues}")
            
            # Upload freeze frames to R2 ONCE per freeze event (not every frame)
            # Freeze is confirmed when detector returns 3 matching images
            freeze_urls_newly_uploaded = False  # Track if URLs are new or cached
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
                                # Use convenience function to get thumbnails path
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
                            freeze_urls_newly_uploaded = True
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
            
            try:
                if detection_result:
                    analysis_data = {
                        "analyzed": True,
                        "subtitle_ocr_pending": True,
                        **detection_result
                    }
                else:
                    analysis_data = {
                        "analyzed": True,
                        "subtitle_ocr_pending": True,
                        "error": "detection_result_was_none"
                    }
                
                # Save individual JSON (hot storage)
                with open(json_file, 'w') as f:
                    json.dump(analysis_data, f, indent=2)
                
                # IMMEDIATE ARCHIVAL: Append to 10min chunk (cold storage)
                try:
                    self._append_to_chunk(capture_folder, filename, analysis_data)
                except Exception as e:
                    logger.debug(f"[{capture_folder}] Chunk append failed (non-critical): {e}")
                    
            except Exception as e:
                logger.error(f"[{capture_folder}] Error saving: {e}")
                with open(json_file, 'w') as f:
                    f.write('{"analyzed": true, "subtitle_ocr_pending": true, "error": "failed_to_save_full_data"}')
        
        except Exception as e:
            logger.error(f"[{capture_folder}] Error: {e}")
            with open(json_file, 'w') as f:
                json.dump({"analyzed": True, "subtitle_ocr_pending": True, "error": str(e)}, f)
    
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
    
    # Kill any existing capture_monitor instances before starting
    from shared.src.lib.utils.system_utils import kill_existing_script_instances
    killed = kill_existing_script_instances('capture_monitor.py')
    if killed:
        logger.info(f"Killed existing capture_monitor instances: {killed}")
        time.sleep(1)
    
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
        # Use convenience function - no manual path building!
        capture_path = get_captures_path(device_folder)
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
