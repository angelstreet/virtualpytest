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

Zapping detection concurrency control:
- Per-device locks prevent concurrent processing of multiple blackscreens
- If a blackscreen is already being analyzed, subsequent ones are skipped
- This prevents race conditions where multiple workers read last_action.json
- Ensures each action is matched to only ONE blackscreen detection
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
import subprocess
import inotify.adapters

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import (
    get_capture_base_directories, 
    get_capture_storage_path, 
    get_capture_folder, 
    get_device_info_from_capture_folder,
    get_metadata_path,
    get_captures_path,
    get_segments_path,
    get_segment_path_from_frame,
    get_device_segment_duration,
    get_capture_folder_from_device_id
)
from shared.src.lib.utils.audio_transcription_utils import check_audio_continuous
from shared.src.lib.utils.zapping_detector_utils import detect_and_record_zapping
from detector import detect_issues
from incident_manager import IncidentManager

# Setup logging (systemd handles file output)
# Use INFO for important events, DEBUG for repetitive per-frame logs
logging.basicConfig(
    level=logging.INFO,  # INFO = important events only (incidents, state changes)
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Log memory usage periodically (every hour)
_last_memory_log = 0
MEMORY_LOG_INTERVAL = 3600  # 1 hour

def log_memory_usage():
    """Log memory usage periodically to help track memory leaks"""
    global _last_memory_log
    current_time = time.time()
    
    if current_time - _last_memory_log < MEMORY_LOG_INTERVAL:
        return
    
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        logger.info(f"📊 [MEMORY] capture_monitor.py using {memory_mb:.1f}MB RAM")
        
        # Alert if memory exceeds 1GB
        if memory_mb > 1024:
            logger.warning(f"⚠️  [MEMORY] capture_monitor.py exceeds 1GB ({memory_mb:.1f}MB) - possible memory leak!")
        
        _last_memory_log = current_time
    except Exception as e:
        logger.warning(f"Failed to log memory usage: {e}")

class InotifyFrameMonitor:
    """Event-driven frame monitor with per-device queue processing"""
    
    def __init__(self, capture_dirs, host_name):
        self.host_name = host_name
        self.incident_manager = IncidentManager()
        self.inotify = inotify.adapters.Inotify()
        
        self.dir_to_info = {}
        self.device_queues = {}
        self.device_workers = {}
        
        # Audio cache: last known audio status per device (updated every 5s by transcript_accumulator)
        self.audio_cache = {}  # {capture_folder: {'audio': bool, 'mean_volume_db': float, 'timestamp': str}}
        
        # Zapping cache: track recent zapping events to add cache to next frames
        # {capture_folder: {'zap_data': {...}, 'frames_written': 0, 'max_frames': 6}}
        self.zapping_cache = {}
        
        # Zapping detection locks: prevent concurrent processing of multiple blackscreens on same device
        # {capture_folder: threading.Lock()} - one lock per device
        self.zapping_locks = {}
        
        # Zapping detection thread pool (prevents blocking frame processing)
        # AI banner analysis takes ~5s - run in background to avoid queue backlog
        from concurrent.futures import ThreadPoolExecutor
        self.zapping_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="zapping-worker")
        
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
            
            # Initialize lock for this device (one lock per device)
            self.zapping_locks[capture_folder] = threading.Lock()
            
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
        max_queue_size_seen = 0
        last_backlog_warning = 0
        
        while True:
            path, filename = work_queue.get()
            frame_count += 1
            queue_size = work_queue.qsize()
            
            # 🔍 TRACE: Extract sequence and log when pulled from queue
            try:
                sequence = int(filename.split('_')[1].split('.')[0])
                logger.info(f"[{capture_folder}] 🔄 PROCESSING: {filename} (seq={sequence}, queue_size={queue_size})")
            except:
                sequence = None
            
            # Track maximum backlog for diagnostics
            if queue_size > max_queue_size_seen:
                max_queue_size_seen = queue_size
                logger.warning(f"[{capture_folder}] 📈 BACKLOG PEAK: {queue_size} frames (new max)")
            
            # Log backlog more frequently during high load
            current_time = time.time()
            if queue_size > 50 and (current_time - last_backlog_warning) > 5:
                logger.warning(f"[{capture_folder}] ⚠️  BACKLOG: {queue_size} frames pending (peak: {max_queue_size_seen})")
                logger.warning(f"[{capture_folder}]     ⚠️  LIFO processing: Newest frames processed first!")
                logger.warning(f"[{capture_folder}]     ⚠️  Events may be processed OUT OF ORDER")
                last_backlog_warning = current_time
            elif queue_size > 20 and (current_time - last_backlog_warning) > 10:
                logger.info(f"[{capture_folder}] 📊 Queue: {queue_size} frames (peak: {max_queue_size_seen})")
                last_backlog_warning = current_time
            
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
        """Append frame to 10min chunk (called for 1 frame per second only)"""
        import json
        import fcntl
        from pathlib import Path
        
        try:
            # Extract sequence from filename
            sequence = int(filename.split('_')[1].split('.')[0])
            
            # Calculate chunk location using ACTUAL timestamp (centralized function)
            from shared.src.lib.utils.storage_path_utils import calculate_chunk_location
            from datetime import datetime
            
            timestamp = analysis_data.get('timestamp') or datetime.now().isoformat()
            hour, chunk_index = calculate_chunk_location(timestamp)
            
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
                'freeze_diffs': analysis_data.get('freeze_diffs', [])
            }
            
            # ✅ OPTIMIZATION: Add action timestamp for zap_executor matching (1 chunk read vs 100 frame JSONs)
            if analysis_data.get('last_action_timestamp'):
                frame_data['last_action_timestamp'] = analysis_data.get('last_action_timestamp')
                frame_data['last_action_executed'] = analysis_data.get('last_action_executed')
            
            # ✅ OPTIMIZATION: Add complete zapping metadata for zap_executor (avoids reading 100 individual JSONs)
            if analysis_data.get('zapping_detected'):
                frame_data['zapping_detected'] = True
                frame_data['zapping_id'] = analysis_data.get('zapping_id')
                frame_data['zapping_channel_name'] = analysis_data.get('zapping_channel_name', '')
                frame_data['zapping_channel_number'] = analysis_data.get('zapping_channel_number', '')
                frame_data['zapping_program_name'] = analysis_data.get('zapping_program_name', '')
                frame_data['zapping_program_start_time'] = analysis_data.get('zapping_program_start_time', '')
                frame_data['zapping_program_end_time'] = analysis_data.get('zapping_program_end_time', '')
                frame_data['zapping_blackscreen_duration_ms'] = analysis_data.get('zapping_blackscreen_duration_ms', 0)
                frame_data['zapping_detection_type'] = analysis_data.get('zapping_detection_type', 'unknown')
                frame_data['zapping_confidence'] = analysis_data.get('zapping_confidence', 0.0)
                frame_data['zapping_detected_at'] = analysis_data.get('zapping_detected_at')
            
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
                        
                        # Update zapping events summary (just count and references)
                        zapping_frames = [f for f in chunk_data['frames'] if f.get('zapping')]
                        chunk_data['zapping_count'] = len(zapping_frames)
                        if zapping_frames:
                            # Store sequence numbers for quick lookup (executor reads full frame JSON for details)
                            chunk_data['zapping_sequences'] = [f['sequence'] for f in zapping_frames]
                        
                        # Write back atomically
                        with open(chunk_path + '.tmp', 'w') as f:
                            json.dump(chunk_data, f, indent=2)
                        os.rename(chunk_path + '.tmp', chunk_path)
                        
                        # Log success with zapping indicator
                        zap_indicator = ""
                        if frame_data.get('zapping'):
                            channel = frame_data.get('zapping_channel', 'Unknown')
                            zap_indicator = f", 📺 ZAP→{channel}"
                        logger.info(f"[{capture_folder}] ✓ Merged JSON → {chunk_path} (seq={sequence}, frames={chunk_data['frames_count']}{zap_indicator})")
                
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            
            # Clean up lock file
            try:
                os.remove(lock_path)
            except:
                pass
                
        except Exception as e:
            # Non-critical failure - individual JSON still saved
            logger.error(f"[{capture_folder}] ✗ Chunk append FAILED → {chunk_path if 'chunk_path' in locals() else 'unknown'}: {e}")
            raise Exception(f"Chunk append error: {e}")
    
    def _add_event_duration_metadata(self, capture_folder, detection_result, current_filename, queue_size=0):
        """Add event duration tracking for all event types"""
        from datetime import datetime
        
        device_info = get_device_info_from_capture_folder(capture_folder)
        device_id = device_info.get('device_id', capture_folder)
        device_model = device_info.get('device_model', 'unknown')
        device_state = self.incident_manager.get_device_state(device_id)
        current_time = datetime.now()
        
        # Track all event types with same logic
        for event_type in ['blackscreen', 'freeze', 'audio', 'macroblocks']:
            # For audio: True=good, False=problem (inverse of other events)
            if event_type == 'audio':
                # Track audio_loss (absence of audio)
                event_active = not detection_result.get(event_type, True)  # No audio = problem
            else:
                event_active = detection_result.get(event_type, False)
            
            event_start_key = f'{event_type}_event_start'
            
            if event_active:
                if not device_state.get(event_start_key):
                    # Event START
                    device_state[event_start_key] = current_time.isoformat()
                    detection_result[f'{event_type}_event_start'] = device_state[event_start_key]
                    detection_result[f'{event_type}_event_duration_ms'] = 0
                    
                    # ✅ ZAPPING: Copy BEFORE + FIRST frames (original + thumbnail) to cold storage
                    if event_type == 'blackscreen':
                        try:
                            from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, get_captures_path, copy_to_cold_storage
                            
                            current_sequence = int(current_filename.split('_')[1].split('.')[0])
                            
                            # BEFORE frame (current - 1)
                            before_filename = f"capture_{current_sequence-1:09d}.jpg"
                            before_thumbnail_filename = f"capture_{current_sequence-1:09d}_thumbnail.jpg"
                            
                            captures_dir = get_captures_path(capture_folder)
                            thumbnails_dir = get_thumbnails_path(capture_folder)
                            
                            before_original_path = os.path.join(captures_dir, before_filename)
                            before_thumbnail_path = os.path.join(thumbnails_dir, before_thumbnail_filename)
                            
                            copied_count = 0
                            
                            # Copy BEFORE original + thumbnail
                            if os.path.exists(before_original_path):
                                before_original_cold = copy_to_cold_storage(before_original_path)
                                if before_original_cold:
                                    device_state['blackscreen_before_original_cold'] = before_original_cold
                                    copied_count += 1
                            if os.path.exists(before_thumbnail_path):
                                before_thumbnail_cold = copy_to_cold_storage(before_thumbnail_path)
                                if before_thumbnail_cold:
                                    device_state['blackscreen_before_thumbnail_cold'] = before_thumbnail_cold
                                    copied_count += 1
                            device_state['blackscreen_before_filename'] = before_filename
                            
                            # FIRST blackscreen frame (current)
                            first_filename = current_filename
                            first_thumbnail_filename = current_filename.replace('.jpg', '_thumbnail.jpg')
                            
                            first_original_path = os.path.join(captures_dir, first_filename)
                            first_thumbnail_path = os.path.join(thumbnails_dir, first_thumbnail_filename)
                            
                            # Copy FIRST original + thumbnail
                            if os.path.exists(first_original_path):
                                first_original_cold = copy_to_cold_storage(first_original_path)
                                if first_original_cold:
                                    device_state['blackscreen_start_original_cold'] = first_original_cold
                                    copied_count += 1
                            if os.path.exists(first_thumbnail_path):
                                first_thumbnail_cold = copy_to_cold_storage(first_thumbnail_path)
                                if first_thumbnail_cold:
                                    device_state['blackscreen_start_thumbnail_cold'] = first_thumbnail_cold
                                    copied_count += 1
                                else:
                                    logger.warning(f"[{capture_folder}] ⚠️  Failed to copy FIRST thumbnail: {first_thumbnail_path}")
                            else:
                                logger.warning(f"[{capture_folder}] ⚠️  FIRST thumbnail not found: {first_thumbnail_path}")
                            device_state['blackscreen_start_filename'] = first_filename
                            device_state['blackscreen_start_sequence'] = current_sequence  # 🔒 VALIDATION: Store sequence for chronological check
                            
                            logger.info(f"[{capture_folder}] 📋 BLACKSCREEN START: Copied {copied_count}/4 images to cold")
                            logger.info(f"[{capture_folder}] 📋 STORED: blackscreen_start_sequence={current_sequence}, queue_size={queue_size}")
                        except Exception as e:
                            logger.warning(f"[{capture_folder}] ⚠️  Failed to capture blackscreen START images: {e}")
                    
                    elif event_type == 'freeze':
                        try:
                            from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, get_captures_path, copy_to_cold_storage
                            
                            current_sequence = int(current_filename.split('_')[1].split('.')[0])
                            
                            # BEFORE frame (current - 1)
                            before_filename = f"capture_{current_sequence-1:09d}.jpg"
                            before_thumbnail_filename = f"capture_{current_sequence-1:09d}_thumbnail.jpg"
                            
                            captures_dir = get_captures_path(capture_folder)
                            thumbnails_dir = get_thumbnails_path(capture_folder)
                            
                            before_original_path = os.path.join(captures_dir, before_filename)
                            before_thumbnail_path = os.path.join(thumbnails_dir, before_thumbnail_filename)
                            
                            copied_count = 0
                            
                            # Copy BEFORE original + thumbnail
                            if os.path.exists(before_original_path):
                                before_original_cold = copy_to_cold_storage(before_original_path)
                                if before_original_cold:
                                    device_state['freeze_before_original_cold'] = before_original_cold
                                    copied_count += 1
                            if os.path.exists(before_thumbnail_path):
                                before_thumbnail_cold = copy_to_cold_storage(before_thumbnail_path)
                                if before_thumbnail_cold:
                                    device_state['freeze_before_thumbnail_cold'] = before_thumbnail_cold
                                    copied_count += 1
                            device_state['freeze_before_filename'] = before_filename
                            
                            # FIRST freeze frame (current)
                            first_filename = current_filename
                            first_thumbnail_filename = current_filename.replace('.jpg', '_thumbnail.jpg')
                            
                            first_original_path = os.path.join(captures_dir, first_filename)
                            first_thumbnail_path = os.path.join(thumbnails_dir, first_thumbnail_filename)
                            
                            # Copy FIRST original + thumbnail
                            if os.path.exists(first_original_path):
                                first_original_cold = copy_to_cold_storage(first_original_path)
                                if first_original_cold:
                                    device_state['freeze_start_original_cold'] = first_original_cold
                                    copied_count += 1
                            if os.path.exists(first_thumbnail_path):
                                first_thumbnail_cold = copy_to_cold_storage(first_thumbnail_path)
                                if first_thumbnail_cold:
                                    device_state['freeze_start_thumbnail_cold'] = first_thumbnail_cold
                                    copied_count += 1
                                else:
                                    logger.warning(f"[{capture_folder}] ⚠️  Failed to copy FIRST freeze thumbnail: {first_thumbnail_path}")
                            else:
                                logger.warning(f"[{capture_folder}] ⚠️  FIRST freeze thumbnail not found: {first_thumbnail_path}")
                            device_state['freeze_start_filename'] = first_filename
                            device_state['freeze_start_sequence'] = current_sequence  # 🔒 VALIDATION: Store sequence for chronological check
                            
                            # 🔍 DEBUG: Log stored filenames with frame numbers
                            logger.info(f"[{capture_folder}] 📋 FREEZE START: Copied {copied_count}/4 images to cold")
                            logger.info(f"[{capture_folder}] 📋 STORED in device_state:")
                            logger.info(f"[{capture_folder}]     freeze_before_filename: {before_filename}")
                            logger.info(f"[{capture_folder}]     freeze_start_filename: {first_filename}")
                            logger.info(f"[{capture_folder}]     freeze_start_sequence: {current_sequence}")
                            logger.info(f"[{capture_folder}]     current_queue_size: {queue_size}")
                        except Exception as e:
                            logger.warning(f"[{capture_folder}] ⚠️  Failed to capture freeze START images: {e}")
                    
                    # Log event start
                    if event_type == 'audio':
                        volume = detection_result.get('mean_volume_db', -100)
                        logger.info(f"[{capture_folder}] 🔇 AUDIO LOSS started (volume={volume:.1f}dB)")
                    elif event_type == 'freeze':
                        freeze_comparisons = detection_result.get('freeze_comparisons', [])
                        freeze_diffs = [c.get('difference_percentage', 0) for c in freeze_comparisons]
                        diffs_str = f"diffs={freeze_diffs}" if freeze_diffs else "diffs=[]"
                        logger.info(f"[{capture_folder}] ⚠️  FREEZE started ({diffs_str})")
                    else:
                        logger.info(f"[{capture_folder}] ⚠️  {event_type.upper()} started")
                else:
                    # Event ONGOING
                    start = datetime.fromisoformat(device_state[event_start_key])
                    detection_result[f'{event_type}_event_start'] = device_state[event_start_key]
                    duration_ms = int((current_time - start).total_seconds() * 1000)
                    detection_result[f'{event_type}_event_duration_ms'] = duration_ms
                    
                    # Log ongoing event every 10 seconds
                    if duration_ms % 10000 < 200:  # Log approximately every 10s
                        if event_type == 'audio':
                            volume = detection_result.get('mean_volume_db', -100)
                            logger.info(f"[{capture_folder}] 🔇 AUDIO LOSS ongoing: {duration_ms/1000:.1f}s (volume={volume:.1f}dB)")
                        else:
                            logger.info(f"[{capture_folder}] ⚠️  {event_type.upper()} ongoing: {duration_ms/1000:.1f}s")
            elif device_state.get(event_start_key):
                # Event END
                start = datetime.fromisoformat(device_state[event_start_key])
                detection_result[f'{event_type}_event_end'] = current_time.isoformat()
                total_duration_ms = int((current_time - start).total_seconds() * 1000)
                detection_result[f'{event_type}_event_total_duration_ms'] = total_duration_ms
                device_state[event_start_key] = None
                
                # ✅ ZAPPING: Copy LAST + AFTER frames (original + thumbnail) to cold storage
                if event_type == 'blackscreen':
                    try:
                        from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, get_captures_path, copy_to_cold_storage
                        
                        current_sequence = int(current_filename.split('_')[1].split('.')[0])
                        
                        captures_dir = get_captures_path(capture_folder)
                        thumbnails_dir = get_thumbnails_path(capture_folder)
                        
                        copied_count = 0
                        
                        # LAST blackscreen frame (current - 1)
                        last_filename = f"capture_{current_sequence-1:09d}.jpg"
                        last_thumbnail_filename = f"capture_{current_sequence-1:09d}_thumbnail.jpg"
                        
                        last_original_path = os.path.join(captures_dir, last_filename)
                        last_thumbnail_path = os.path.join(thumbnails_dir, last_thumbnail_filename)
                        
                        # Copy LAST original + thumbnail
                        if os.path.exists(last_original_path):
                            last_original_cold = copy_to_cold_storage(last_original_path)
                            if last_original_cold:
                                device_state['blackscreen_last_original_cold'] = last_original_cold
                                copied_count += 1
                        if os.path.exists(last_thumbnail_path):
                            last_thumbnail_cold = copy_to_cold_storage(last_thumbnail_path)
                            if last_thumbnail_cold:
                                device_state['blackscreen_last_thumbnail_cold'] = last_thumbnail_cold
                                copied_count += 1
                        device_state['blackscreen_last_filename'] = last_filename
                        
                        # AFTER frame will be handled by zapping_detector (it's the analyzed frame)
                        # Just store the filename for reference
                        device_state['blackscreen_closure_filename'] = current_filename
                        
                        logger.info(f"[{capture_folder}] 📋 BLACKSCREEN END: Copied {copied_count}/2 LAST images (AFTER=analyzed frame, copied during banner detection)")
                    except Exception as e:
                        logger.warning(f"[{capture_folder}] ⚠️  Failed to capture blackscreen END images: {e}")
                
                elif event_type == 'freeze':
                    try:
                        from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, get_captures_path, copy_to_cold_storage
                        
                        current_sequence = int(current_filename.split('_')[1].split('.')[0])
                        
                        captures_dir = get_captures_path(capture_folder)
                        thumbnails_dir = get_thumbnails_path(capture_folder)
                        
                        copied_count = 0
                        
                        # LAST freeze frame (current - 1)
                        last_filename = f"capture_{current_sequence-1:09d}.jpg"
                        last_thumbnail_filename = f"capture_{current_sequence-1:09d}_thumbnail.jpg"
                        
                        last_original_path = os.path.join(captures_dir, last_filename)
                        last_thumbnail_path = os.path.join(thumbnails_dir, last_thumbnail_filename)
                        
                        # Copy LAST original + thumbnail
                        if os.path.exists(last_original_path):
                            last_original_cold = copy_to_cold_storage(last_original_path)
                            if last_original_cold:
                                device_state['freeze_last_original_cold'] = last_original_cold
                                copied_count += 1
                        if os.path.exists(last_thumbnail_path):
                            last_thumbnail_cold = copy_to_cold_storage(last_thumbnail_path)
                            if last_thumbnail_cold:
                                device_state['freeze_last_thumbnail_cold'] = last_thumbnail_cold
                                copied_count += 1
                        device_state['freeze_last_filename'] = last_filename
                        
                        # AFTER frame will be handled by zapping_detector (it's the analyzed frame)
                        # Just store the filename for reference
                        device_state['freeze_closure_filename'] = current_filename
                        
                        # 🔍 DEBUG: Log stored filenames with frame numbers
                        logger.info(f"[{capture_folder}] 📋 FREEZE END: Copied {copied_count}/2 LAST images (AFTER=analyzed frame, copied during banner detection)")
                        logger.info(f"[{capture_folder}] 📋 STORED in device_state:")
                        logger.info(f"[{capture_folder}]     freeze_last_filename: {last_filename}")
                        logger.info(f"[{capture_folder}]     freeze_closure_filename: {current_filename}")
                        logger.info(f"[{capture_folder}]     freeze_end_sequence: {current_sequence}")
                        logger.info(f"[{capture_folder}]     current_queue_size: {queue_size}")
                    except Exception as e:
                        logger.warning(f"[{capture_folder}] ⚠️  Failed to capture freeze END images: {e}")
                
                # Log event end
                if event_type == 'audio':
                    volume = detection_result.get('mean_volume_db', -100)
                    logger.info(f"[{capture_folder}] 🔊 AUDIO RESTORED after {total_duration_ms/1000:.1f}s (volume={volume:.1f}dB)")
                elif event_type == 'freeze':
                    freeze_comparisons = detection_result.get('freeze_comparisons', [])
                    freeze_diffs = [c.get('difference_percentage', 0) for c in freeze_comparisons]
                    diffs_str = f"diffs={freeze_diffs}" if freeze_diffs else "diffs=[]"
                    logger.info(f"[{capture_folder}] ✅ FREEZE ended after {total_duration_ms/1000:.1f}s ({diffs_str})")
                else:
                    logger.info(f"[{capture_folder}] ✅ {event_type.upper()} ended after {total_duration_ms/1000:.1f}s")
                
                # ✅ Automatic zapping detection when blackscreen ends
                if event_type == 'blackscreen' and total_duration_ms < 10000:
                    # Trigger for blackscreens up to 10s (zapping can take time depending on signal/TV)
                    # Blackscreens > 10s are likely real incidents, not channel changes
                    logger.info(f"[{capture_folder}] Blackscreen ended ({total_duration_ms}ms) - checking for zapping...")
                    
                    # Get start filename and sequence for validation
                    blackscreen_start_filename = device_state.get('blackscreen_start_filename')
                    blackscreen_start_sequence = device_state.get('blackscreen_start_sequence', 0)
                    
                    # 🔍 DEBUG: Log what we're passing to audio check
                    logger.info(f"[{capture_folder}] 📋 RETRIEVED from device_state for audio check:")
                    logger.info(f"[{capture_folder}]     blackscreen_start_filename: {blackscreen_start_filename}")
                    logger.info(f"[{capture_folder}]     blackscreen_start_sequence: {blackscreen_start_sequence}")
                    logger.info(f"[{capture_folder}]     current_filename (END): {current_filename}")
                    
                    # 🔒 SEQUENCE VALIDATION: Ensure chronological order
                    if blackscreen_start_filename and current_filename:
                        try:
                            start_frame_num = int(blackscreen_start_filename.split('_')[1].split('.')[0])
                            end_frame_num = int(current_filename.split('_')[1].split('.')[0])
                            logger.info(f"[{capture_folder}]     start_frame_number: {start_frame_num}")
                            logger.info(f"[{capture_folder}]     end_frame_number: {end_frame_num}")
                            
                            # ❌ CRITICAL VALIDATION: Detect non-chronological processing
                            if start_frame_num > end_frame_num:
                                logger.error(f"[{capture_folder}] ❌ NON-CHRONOLOGICAL EVENT DETECTED!")
                                logger.error(f"[{capture_folder}]     start_frame ({start_frame_num}) > end_frame ({end_frame_num})")
                                logger.error(f"[{capture_folder}]     Frame difference: {start_frame_num - end_frame_num} frames")
                                logger.error(f"[{capture_folder}]     ROOT CAUSE: LIFO queue processing + backlog")
                                logger.error(f"[{capture_folder}]     IMPACT: Event processed backwards, audio check will fail")
                                logger.error(f"[{capture_folder}]     SOLUTION: Clearing stale state and ABORTING this event")
                                
                                # Clear stale blackscreen state
                                device_state['blackscreen_start_filename'] = None
                                device_state['blackscreen_start_sequence'] = None
                                device_state['blackscreen_start_time'] = None
                                
                                # Don't process this event - it's invalid
                                logger.warning(f"[{capture_folder}] ⏭️  SKIPPING zapping detection for non-chronological event")
                                continue  # Skip to next iteration (don't submit to executor)
                                
                            elif blackscreen_start_sequence and blackscreen_start_sequence >= end_frame_num:
                                # Extra validation using stored sequence
                                logger.error(f"[{capture_folder}] ❌ SEQUENCE VALIDATION FAILED!")
                                logger.error(f"[{capture_folder}]     stored_start_sequence ({blackscreen_start_sequence}) >= end_frame ({end_frame_num})")
                                logger.error(f"[{capture_folder}]     This confirms LIFO processing issue")
                                
                                # Clear stale state
                                device_state['blackscreen_start_filename'] = None
                                device_state['blackscreen_start_sequence'] = None
                                device_state['blackscreen_start_time'] = None
                                
                                logger.warning(f"[{capture_folder}] ⏭️  SKIPPING zapping detection for invalid sequence")
                                continue
                                
                        except Exception as e:
                            logger.warning(f"[{capture_folder}] Failed to parse frame numbers: {e}")
                    
                    # ✅ SKIP if already learned different pattern (e.g., device zaps on freeze, not blackscreen)
                    learned_type = device_state.get('zapping_event_type')
                    if learned_type and learned_type != 'blackscreen':
                        logger.info(f"[{capture_folder}] ⏭️  SKIP zapping check (device zaps on {learned_type}, not blackscreen)")
                        continue
                    
                    # ✅ NON-BLOCKING: Submit to thread pool (AI analysis takes ~5s, don't block frame queue!)
                    self.zapping_executor.submit(
                        self._check_for_zapping_async,
                        capture_folder=capture_folder,
                        device_id=device_id,
                        device_model=device_model,
                        current_filename=current_filename,
                        blackscreen_duration_ms=total_duration_ms,
                        blackscreen_start_filename=blackscreen_start_filename,
                        event_type='blackscreen'
                    )
                
                # ✅ Automatic zapping detection when freeze ends
                elif event_type == 'freeze' and total_duration_ms < 10000:
                    # Trigger for freezes up to 10s (zapping can take time depending on signal/TV)
                    # Freezes > 10s are likely real incidents, not channel changes
                    logger.info(f"[{capture_folder}] Freeze ended ({total_duration_ms}ms) - checking for zapping...")
                    
                    # Get start filename and sequence for validation
                    freeze_start_filename = device_state.get('freeze_start_filename')
                    freeze_start_sequence = device_state.get('freeze_start_sequence', 0)
                    
                    # 🔍 DEBUG: Log what we're passing to audio check
                    logger.info(f"[{capture_folder}] 📋 RETRIEVED from device_state for audio check:")
                    logger.info(f"[{capture_folder}]     freeze_start_filename: {freeze_start_filename}")
                    logger.info(f"[{capture_folder}]     freeze_start_sequence: {freeze_start_sequence}")
                    logger.info(f"[{capture_folder}]     current_filename (END): {current_filename}")
                    
                    # 🔒 SEQUENCE VALIDATION: Ensure chronological order
                    if freeze_start_filename and current_filename:
                        try:
                            start_frame_num = int(freeze_start_filename.split('_')[1].split('.')[0])
                            end_frame_num = int(current_filename.split('_')[1].split('.')[0])
                            logger.info(f"[{capture_folder}]     start_frame_number: {start_frame_num}")
                            logger.info(f"[{capture_folder}]     end_frame_number: {end_frame_num}")
                            
                            # ❌ CRITICAL VALIDATION: Detect non-chronological processing
                            if start_frame_num > end_frame_num:
                                logger.error(f"[{capture_folder}] ❌ NON-CHRONOLOGICAL EVENT DETECTED!")
                                logger.error(f"[{capture_folder}]     start_frame ({start_frame_num}) > end_frame ({end_frame_num})")
                                logger.error(f"[{capture_folder}]     Frame difference: {start_frame_num - end_frame_num} frames")
                                logger.error(f"[{capture_folder}]     ROOT CAUSE: LIFO queue processing + backlog")
                                logger.error(f"[{capture_folder}]     IMPACT: Event processed backwards, audio check will fail")
                                logger.error(f"[{capture_folder}]     SOLUTION: Clearing stale state and ABORTING this event")
                                
                                # Clear stale freeze state
                                device_state['freeze_start_filename'] = None
                                device_state['freeze_start_sequence'] = None
                                device_state['freeze_start_time'] = None
                                
                                # Don't process this event - it's invalid
                                logger.warning(f"[{capture_folder}] ⏭️  SKIPPING zapping detection for non-chronological event")
                                continue  # Skip to next iteration (don't submit to executor)
                                
                            elif freeze_start_sequence and freeze_start_sequence >= end_frame_num:
                                # Extra validation using stored sequence
                                logger.error(f"[{capture_folder}] ❌ SEQUENCE VALIDATION FAILED!")
                                logger.error(f"[{capture_folder}]     stored_start_sequence ({freeze_start_sequence}) >= end_frame ({end_frame_num})")
                                logger.error(f"[{capture_folder}]     This confirms LIFO processing issue")
                                
                                # Clear stale state
                                device_state['freeze_start_filename'] = None
                                device_state['freeze_start_sequence'] = None
                                device_state['freeze_start_time'] = None
                                
                                logger.warning(f"[{capture_folder}] ⏭️  SKIPPING zapping detection for invalid sequence")
                                continue
                                
                        except Exception as e:
                            logger.warning(f"[{capture_folder}] Failed to parse frame numbers: {e}")
                    
                    # ✅ SKIP if already learned different pattern (e.g., device zaps on blackscreen, not freeze)
                    learned_type = device_state.get('zapping_event_type')
                    if learned_type and learned_type != 'freeze':
                        logger.info(f"[{capture_folder}] ⏭️  SKIP zapping check (device zaps on {learned_type}, not freeze)")
                        continue
                    
                    # ✅ NON-BLOCKING: Submit to thread pool (AI analysis takes ~5s, don't block frame queue!)
                    self.zapping_executor.submit(
                        self._check_for_zapping_async,
                        capture_folder=capture_folder,
                        device_id=device_id,
                        device_model=device_model,
                        current_filename=current_filename,
                        blackscreen_duration_ms=total_duration_ms,  # Keep same param name (it's just event_duration)
                        blackscreen_start_filename=freeze_start_filename,  # Keep same param name (it's just event_start)
                        event_type='freeze'
                    )
        
        return detection_result
    
    def _check_for_zapping_async(self, capture_folder, device_id, device_model, current_filename, blackscreen_duration_ms, blackscreen_start_filename=None, event_type='blackscreen'):
        """
        Check if blackscreen/freeze was caused by zapping (channel change).
        This happens AFTER event ends, analyzing the first normal frame.
        
        ✅ ASYNC: Runs in background thread pool to avoid blocking frame processing queue
        (AI banner analysis takes ~5 seconds - would cause major queue backlog if synchronous)
        
        ✅ LOCKING: Uses per-device lock to prevent concurrent processing of multiple events
        - If lock is already held (another event being processed), skip this one
        - Prevents race conditions where multiple events try to read last_action.json
        
        ✅ AUDIO PRE-CHECK: Checks audio in SAME 1-second TS segment where event occurred
        - If audio present → proceed with banner detection (likely zapping - TV audio during channel switch)
        - If no audio → abort (likely freeze/signal loss, not zapping)
        
        ✅ SUPPORTS: Both blackscreen and freeze event types (identical processing flow)
        
        Uses shared zapping detection utility (reuses existing banner detection AI).
        """
        # ✅ TRY TO ACQUIRE LOCK (non-blocking)
        lock = self.zapping_locks.get(capture_folder)
        if not lock:
            logger.error(f"[{capture_folder}] No lock found for device - this should not happen!")
            return
        
        # Try to acquire lock without blocking
        lock_acquired = lock.acquire(blocking=False)
        if not lock_acquired:
            logger.info(f"[{capture_folder}] ⏭️  SKIP: Another event is already being processed (frame: {current_filename})")
            logger.info(f"[{capture_folder}]     This prevents race conditions and stale action reads")
            return
        
        try:
            event_name = event_type.upper()
            logger.info(f"[{capture_folder}] 🔒 LOCK ACQUIRED - Zapping worker started for {current_filename} ({event_name} event)")
            
            # ✅ FIRST CHECK: Only detect zapping for system-triggered actions (within 10s)
            # This prevents wasting resources (audio analysis, FFmpeg, AI tokens) on manual user zaps
            action_info = self._get_action_from_device_state(capture_folder)
            
            if not action_info:
                logger.info(f"[{capture_folder}] ⏭️  ABORT: No recent action found (> 10s old or missing)")
                logger.info(f"[{capture_folder}]     Only monitoring zaps triggered by our system")
                logger.info(f"[{capture_folder}]     Manual user zaps are not tracked")
                logger.info(f"[{capture_folder}]     Skipping all analysis (audio + banner detection)")
                
                # ✅ Write "aborted" status so zap_executor doesn't timeout
                self._write_zapping_aborted(capture_folder, current_filename, 'No recent action - not system-triggered zap')
                return
            
            # ✅ WRITE "in_progress" marker (after action check - only if we're proceeding)
            # This allows zap_executor to wait instead of reading stale data
            self._write_zapping_in_progress(capture_folder, current_filename, blackscreen_duration_ms)
            
            # ✅ PRE-CHECK: Audio DROPOUT detection across ALL segments during event + 1 extra after
            # We merge segments from event start to end + 1 more to check if audio comes back
            logger.info(f"[{capture_folder}] 🔊 Pre-check: Checking for audio dropout across {event_name} period...")
            audio_info = self._check_segment_audio(
                capture_folder, 
                blackscreen_start_filename=blackscreen_start_filename,
                blackscreen_end_filename=current_filename  # End of blackscreen
            )
            
            # ✅ CRITICAL: Validate audio check succeeded before making decisions
            # If segments_checked is empty, audio analysis FAILED - we cannot determine if zapping
            segments_checked = audio_info.get('segments_checked', [])
            if not segments_checked or len(segments_checked) == 0:
                logger.warning(f"[{capture_folder}] ⏭️  ABORT: Audio check FAILED (no segments analyzed) - cannot determine if zapping")
                logger.warning(f"[{capture_folder}]     Possible causes: segments not found, ffmpeg error, timeout")
                logger.warning(f"[{capture_folder}]     This prevents wasting AI tokens on uncertain events")
                self._write_zapping_aborted(capture_folder, current_filename, 'Audio check failed - no segments analyzed')
                return
            
            if audio_info['has_continuous_audio']:
                # Check if it's actual audio or just constant silence
                mean_volume = audio_info.get('mean_volume_db', 0)
                silence_duration = audio_info.get('silence_duration', 0)
                
                # ✅ PROTECTION: Silence > 2s = real incident, not zapping
                # Zapping causes brief silence (0.1-1s), not extended silence
                MAX_ZAPPING_SILENCE = 2.0
                
                if silence_duration > MAX_ZAPPING_SILENCE:
                    logger.info(f"[{capture_folder}] ⏭️  ABORT: Silence too long ({silence_duration:.1f}s > {MAX_ZAPPING_SILENCE}s)")
                    logger.info(f"[{capture_folder}]     This is a REAL incident (freeze/blackscreen), not zapping")
                    logger.info(f"[{capture_folder}]     mean_volume={mean_volume:.1f}dB")
                    logger.info(f"[{capture_folder}]     Skipping banner detection to avoid wasting AI tokens")
                    
                    # ✅ Write "aborted" status so zap_executor doesn't timeout
                    self._write_zapping_aborted(capture_folder, current_filename, f'Silence too long ({silence_duration:.1f}s > {MAX_ZAPPING_SILENCE}s) - real incident')
                    return
                elif mean_volume <= -90:  # Constant silence but short (< 2s) - might be real zapping
                    logger.warning(f"[{capture_folder}] ⚠️  Constant silence detected (no audio throughout)")
                    logger.warning(f"[{capture_folder}]     mean_volume={mean_volume:.1f}dB, silence={silence_duration:.1f}s")
                    logger.warning(f"[{capture_folder}]     Proceeding with banner detection (short silence < {MAX_ZAPPING_SILENCE}s)")
                    # Continue to banner detection
                else:
                    # Actual continuous audio → ABORT (likely dark content, not zapping)
                    logger.info(f"[{capture_folder}] ⏭️  ABORT: Continuous audio detected - likely dark content, not zapping")
                    logger.info(f"[{capture_folder}]     Checked {len(segments_checked)} segments: {segments_checked}")
                    logger.info(f"[{capture_folder}]     mean_volume={mean_volume:.1f}dB, silence={silence_duration:.1f}s")
                    
                    # ✅ Write "aborted" status so zap_executor doesn't timeout
                    self._write_zapping_aborted(capture_folder, current_filename, 'Continuous audio detected')
                    return
            else:
                # Audio dropout detected → PROCEED with banner detection (likely zapping)
                # Example: 800ms audio + 200ms silence during channel switch
                logger.info(f"[{capture_folder}] ✅ Audio dropout detected - proceeding with banner detection (likely zapping)")
                logger.info(f"[{capture_folder}]     Checked {len(segments_checked)} segments: {segments_checked}")
                logger.info(f"[{capture_folder}]     mean_volume={audio_info.get('mean_volume_db', 0):.1f}dB, silence={audio_info.get('silence_duration', 0):.1f}s")
            
            # Get device_state to access transition images (same way as _add_event_duration_metadata)
            device_state = self.incident_manager.get_device_state(device_id)
            
            # ✅ READ transition image paths from device_state (already copied to cold during event tracking)
            # Support both blackscreen and freeze event types
            if event_type == 'blackscreen':
                before_frame = device_state.get('blackscreen_before_filename')
                first_frame = device_state.get('blackscreen_start_filename')
                last_frame = device_state.get('blackscreen_last_filename')
                after_frame = device_state.get('blackscreen_closure_filename', current_filename)
                
                # Read cold storage paths (already copied during blackscreen tracking)
                before_original = device_state.get('blackscreen_before_original_cold')
                before_thumbnail = device_state.get('blackscreen_before_thumbnail_cold')
                first_original = device_state.get('blackscreen_start_original_cold')
                first_thumbnail = device_state.get('blackscreen_start_thumbnail_cold')
                last_original = device_state.get('blackscreen_last_original_cold')
                last_thumbnail = device_state.get('blackscreen_last_thumbnail_cold')
            elif event_type == 'freeze':
                before_frame = device_state.get('freeze_before_filename')
                first_frame = device_state.get('freeze_start_filename')
                last_frame = device_state.get('freeze_last_filename')
                after_frame = device_state.get('freeze_closure_filename', current_filename)
                
                # Read cold storage paths (already copied during freeze tracking)
                before_original = device_state.get('freeze_before_original_cold')
                before_thumbnail = device_state.get('freeze_before_thumbnail_cold')
                first_original = device_state.get('freeze_start_original_cold')
                first_thumbnail = device_state.get('freeze_start_thumbnail_cold')
                last_original = device_state.get('freeze_last_original_cold')
                last_thumbnail = device_state.get('freeze_last_thumbnail_cold')
            
            # AFTER frame is copied by zapping_detector (it's the analyzed frame) - no need to read from device_state
            
            # ✅ FALLBACK: If thumbnails are None but we have filenames, construct paths from hot storage
            from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, get_captures_path, copy_to_cold_storage
            thumbnails_dir = get_thumbnails_path(capture_folder)
            captures_dir = get_captures_path(capture_folder)
            
            if not before_thumbnail and before_frame:
                before_thumbnail_hot = os.path.join(thumbnails_dir, before_frame.replace('.jpg', '_thumbnail.jpg'))
                if os.path.exists(before_thumbnail_hot):
                    before_thumbnail = copy_to_cold_storage(before_thumbnail_hot)
                    if before_thumbnail:
                        logger.info(f"[{capture_folder}] 📸 Recovered BEFORE thumbnail from hot storage")
            
            if not first_thumbnail and first_frame:
                first_thumbnail_hot = os.path.join(thumbnails_dir, first_frame.replace('.jpg', '_thumbnail.jpg'))
                if os.path.exists(first_thumbnail_hot):
                    first_thumbnail = copy_to_cold_storage(first_thumbnail_hot)
                    if first_thumbnail:
                        logger.info(f"[{capture_folder}] 📸 Recovered FIRST thumbnail from hot storage")
            
            if not last_thumbnail and last_frame:
                last_thumbnail_hot = os.path.join(thumbnails_dir, last_frame.replace('.jpg', '_thumbnail.jpg'))
                if os.path.exists(last_thumbnail_hot):
                    last_thumbnail = copy_to_cold_storage(last_thumbnail_hot)
                    if last_thumbnail:
                        logger.info(f"[{capture_folder}] 📸 Recovered LAST thumbnail from hot storage")
            
            # Same for originals
            if not before_original and before_frame:
                before_original_hot = os.path.join(captures_dir, before_frame)
                if os.path.exists(before_original_hot):
                    before_original = copy_to_cold_storage(before_original_hot)
            
            if not first_original and first_frame:
                first_original_hot = os.path.join(captures_dir, first_frame)
                if os.path.exists(first_original_hot):
                    first_original = copy_to_cold_storage(first_original_hot)
            
            if not last_original and last_frame:
                last_original_hot = os.path.join(captures_dir, last_frame)
                if os.path.exists(last_original_hot):
                    last_original = copy_to_cold_storage(last_original_hot)
            
            # DEBUG: Log what we got from device_state
            event_name = event_type.upper()
            logger.info(f"[{capture_folder}] 📋 {event_name} transition images from device_state:")
            logger.info(f"  BEFORE: frame={before_frame}, thumbnail={before_thumbnail}")
            logger.info(f"  FIRST:  frame={first_frame}, thumbnail={first_thumbnail}")
            logger.info(f"  LAST:   frame={last_frame}, thumbnail={last_thumbnail}")
            logger.info(f"  AFTER:  frame={after_frame}, thumbnail=(will be copied during banner analysis)")
            
            # Build transition images dict (AFTER will be added by zapping_detector)
            transition_images = {
                'before_frame': before_frame,
                'before_original_path': before_original,
                'before_thumbnail_path': before_thumbnail,
                'first_blackscreen_frame': first_frame,
                'first_blackscreen_original_path': first_original,
                'first_blackscreen_thumbnail_path': first_thumbnail,
                'last_blackscreen_frame': last_frame,
                'last_blackscreen_original_path': last_original,
                'last_blackscreen_thumbnail_path': last_thumbnail,
                # AFTER will be filled by zapping_detector with the analyzed frame
                'after_frame': after_frame
            }
            
            # Log which thumbnails are available (for R2 upload)
            thumbnails = [before_thumbnail, first_thumbnail, last_thumbnail]
            images_found = sum(1 for path in thumbnails if path)
            missing = []
            if not before_thumbnail: missing.append('before')
            if not first_thumbnail: missing.append('first')
            if not last_thumbnail: missing.append('last')
            
            logger.info(f"[{capture_folder}] 📸 Transition thumbnails ready: {images_found}/3" + (f", missing: {missing}" if missing else "") + " (AFTER added during banner analysis)")
            
            # 🔍 DEBUG: Show action_info being passed to zapping detector
            logger.info(f"[{capture_folder}] 📝 Action info being passed to zapping detector:")
            logger.info(f"[{capture_folder}]    last_action_executed: {action_info.get('last_action_executed')}")
            logger.info(f"[{capture_folder}]    last_action_timestamp: {action_info.get('last_action_timestamp')}")
            logger.info(f"[{capture_folder}]    time_since_action_ms: {action_info.get('time_since_action_ms')}ms")
            
            # Call shared zapping detection function (reuses existing video controller)
            # This is the expensive operation (~5s for AI analysis)
            result = detect_and_record_zapping(
                device_id=device_id,
                device_model=device_model,
                capture_folder=capture_folder,
                frame_filename=current_filename,
                blackscreen_duration_ms=blackscreen_duration_ms,
                action_info=action_info,
                audio_info=audio_info,  # Pass audio dropout analysis to zapping record
                transition_images=transition_images  # ✅ NEW: Pass transition images
            )
            
            # Log result regardless of success/failure for debugging
            if result.get('zapping_detected'):
                channel_name = result.get('channel_name', 'Unknown')
                channel_number = result.get('channel_number', '')
                detection_type = result.get('detection_type', 'unknown')
                logger.info(f"[{capture_folder}] 📺 {detection_type.upper()} ZAPPING: {channel_name} {channel_number}")
                
                # Log R2 upload status for transition images with full URLs
                r2_images = result.get('r2_images', {})
                if r2_images:
                    uploaded = [k for k, v in r2_images.items() if v and k.endswith('_url')]
                    logger.info(f"[{capture_folder}] 📤 R2 upload: {len(uploaded)}/4 transition images uploaded to R2")
                    
                    # Log each URL (or None if missing)
                    logger.info(f"[{capture_folder}] R2 URLs:")
                    logger.info(f"  - before: {r2_images.get('before_url', 'MISSING')}")
                    logger.info(f"  - first_blackscreen: {r2_images.get('first_blackscreen_url', 'MISSING')}")
                    logger.info(f"  - last_blackscreen: {r2_images.get('last_blackscreen_url', 'MISSING')}")
                    logger.info(f"  - after: {r2_images.get('after_url', 'MISSING')}")
                    
                    if len(uploaded) < 4:
                        missing = [k.replace('_url', '') for k in ['before_url', 'first_blackscreen_url', 'last_blackscreen_url', 'after_url'] if not r2_images.get(k)]
                        logger.warning(f"[{capture_folder}] ⚠️  Missing R2 images: {missing}")
                else:
                    logger.warning(f"[{capture_folder}] ⚠️  No R2 images in result")
                
                # ✅ Cache: zapping_detector fills gap (existing frames), capture_monitor adds next 5 frames
                try:
                    original_sequence = int(current_filename.split('_')[1].split('.')[0])
                    # Use same ID format as zapping_detector (based on original frame for deduplication)
                    zap_id = result.get('id', f"zap_cache_{current_filename}")
                    self.zapping_cache[capture_folder] = {
                        'zap_data': {
                            'detected': True,
                            'id': zap_id,  # Same ID for all cache frames (deduplication)
                            'channel_name': channel_name,
                            'channel_number': channel_number,
                            'program_name': result.get('program_name', ''),
                            'program_start_time': result.get('program_start_time', ''),  # ✅ Now returned from detector
                            'program_end_time': result.get('program_end_time', ''),      # ✅ Now returned from detector
                            'blackscreen_duration_ms': blackscreen_duration_ms,
                            'detection_type': detection_type,
                            'confidence': result.get('confidence', 0.0),
                            'audio_silence_duration': result.get('audio_silence_duration', 0.0),  # ✅ Now in result
                            'time_since_action_ms': result.get('time_since_action_ms'),           # ✅ Now in result
                            'total_zap_duration_ms': result.get('total_zap_duration_ms'),         # ✅ Backend calculated total
                            'original_frame': current_filename
                        },
                        'frames_remaining': 5  # Add cache to next 5 frames
                    }
                    logger.info(f"[{capture_folder}] 📋 Cache: will add to next 5 frames (safety margin)")
                except Exception as e:
                    logger.error(f"[{capture_folder}] Failed to setup cache: {e}")
                
                # ✅ LEARN: Store which event type triggers zapping (first confirmed zapping only)
                if not device_state.get('zapping_event_type'):
                    device_state['zapping_event_type'] = event_type
                    logger.info(f"[{capture_folder}] 🎓 LEARNED: Zapping is {event_type}-based (will only check {event_type} from now on)")
                
            elif result.get('error'):
                logger.warning(f"[{capture_folder}] ⚠️  Zapping detection failed: {result.get('error')}")
            else:
                logger.info(f"[{capture_folder}] ℹ️  No zapping detected (no banner found)")
            
        except Exception as e:
            logger.error(f"[{capture_folder}] Error checking for zapping: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # ✅ ALWAYS RELEASE LOCK (even if exception occurred)
            lock.release()
            event_name = event_type.upper() if 'event_type' in locals() else 'UNKNOWN'
            logger.info(f"[{capture_folder}] 🔓 LOCK RELEASED - Zapping worker finished for {current_filename} ({event_name} event)")
    
    def _check_segment_audio(self, capture_folder, blackscreen_start_filename=None, blackscreen_end_filename=None):
        """
        Check for audio DROPOUTS across ALL segments spanning event duration + 1 extra segment after.
        
        This merges multiple TS segments (from event start to end + 1 more) and checks audio continuity
        across the entire period. This catches audio dropouts that span segment boundaries.
        
        Works for both BLACKSCREEN and FREEZE events (parameter names use "blackscreen" for backward compat).
        
        Example:
        - Event: frame 2495-2498 (800ms at 5fps)
        - Segments: 499 (frames 2495-2499), 500 (frames 2500-2504)
        - We check: segment 499 + 500 + 501 (start + end + 1 extra after)
        - This detects if audio cuts during zapping and comes back after
        
        This is called BEFORE expensive AI banner detection to avoid false positives:
        - If continuous audio → ABORT (likely dark content with audio, not zapping)
        - If audio dropout → PROCEED with banner detection (likely zapping - audio cuts during channel switch)
        
        Args:
            capture_folder: Device folder (e.g., 'capture1')
            blackscreen_start_filename: Frame where event started (e.g., 'capture_000002495.jpg')
            blackscreen_end_filename: Frame where event ended (e.g., 'capture_000002498.jpg')
        
        Returns:
            dict: Audio analysis result with keys:
                - has_continuous_audio (bool): True if audio is continuous, False if dropout detected
                - silence_duration (float): Total silence duration in seconds
                - mean_volume_db (float): Mean volume in dB
                - segment_duration (float): Total segment duration analyzed
                - segments_checked (list): List of segment numbers checked
        """
        try:
            # 🔍 DEBUG: Log what we received
            logger.info(f"[{capture_folder}] 🔊 _check_segment_audio called:")
            logger.info(f"[{capture_folder}]     start_filename: {blackscreen_start_filename}")
            logger.info(f"[{capture_folder}]     end_filename: {blackscreen_end_filename}")
            
            if not blackscreen_start_filename or not blackscreen_end_filename:
                logger.warning(f"[{capture_folder}] Missing blackscreen start/end filenames")
                return {
                    'has_continuous_audio': False,
                    'silence_duration': 0.0,
                    'mean_volume_db': -100.0,
                    'segment_duration': 0.0,
                    'segments_checked': []
                }
            
            # Extract frame numbers from filenames
            start_frame = int(blackscreen_start_filename.split('_')[1].split('.')[0])
            end_frame = int(blackscreen_end_filename.split('_')[1].split('.')[0])
            
            # 🔍 DEBUG: Log extracted frame numbers
            logger.info(f"[{capture_folder}]     start_frame_number: {start_frame}")
            logger.info(f"[{capture_folder}]     end_frame_number: {end_frame}")
            
            # 🔒 VALIDATION: Check if chronological
            if start_frame > end_frame:
                logger.error(f"[{capture_folder}] ❌ CRITICAL: Non-chronological frame numbers in audio check!")
                logger.error(f"[{capture_folder}]     start_frame ({start_frame}) > end_frame ({end_frame})")
                logger.error(f"[{capture_folder}]     Difference: {start_frame - end_frame} frames")
                logger.error(f"[{capture_folder}]     ROOT CAUSES:")
                logger.error(f"[{capture_folder}]       1. LIFO queue processing + backlog (MOST LIKELY)")
                logger.error(f"[{capture_folder}]       2. Hot storage rotated between event start and end")
                logger.error(f"[{capture_folder}]       3. Stale data in device_state from previous event")
                logger.error(f"[{capture_folder}]       4. Frame counter wrapped around (unlikely)")
                logger.error(f"[{capture_folder}]     IMPACT: Cannot determine audio segments, results would be invalid")
                logger.error(f"[{capture_folder}]     ABORTING audio check")
                return {
                    'has_continuous_audio': False,
                    'silence_duration': 0.0,
                    'mean_volume_db': -100.0,
                    'segment_duration': 0.0,
                    'segments_checked': []  # Empty = validation failed
                }
            
            # Get segment numbers from frames
            from shared.src.lib.utils.storage_path_utils import get_device_fps, get_segment_number_from_capture
            device_fps = get_device_fps(capture_folder)
            
            logger.info(f"[{capture_folder}]     device_fps: {device_fps}")
            
            start_segment = get_segment_number_from_capture(start_frame, device_fps)
            end_segment = get_segment_number_from_capture(end_frame, device_fps)
            
            logger.info(f"[{capture_folder}]     start_segment: {start_segment} (frame {start_frame})")
            logger.info(f"[{capture_folder}]     end_segment: {end_segment} (frame {end_frame})")
            
            # ✅ CAP TO 2 SEGMENTS MAX: Audio dropout happens at START of zapping (channel change)
            # Even if event lasts 10s (slow STB), we only need to check first 2 segments
            # This prevents analyzing 9+ segments when queue backlog causes stale device_state
            segments_to_check = [start_segment, start_segment + 1]  # Always max 2 segments
            
            logger.info(f"[{capture_folder}] Event: frames {start_frame}-{end_frame} → segments {start_segment}-{end_segment}")
            logger.info(f"[{capture_folder}] Will analyze {len(segments_to_check)} segment(s) [CAPPED TO 2]: {segments_to_check}")
            
            # Find all segment files
            segments_dir = get_segments_path(capture_folder)
            if not os.path.exists(segments_dir):
                logger.warning(f"[{capture_folder}] Segments directory not found: {segments_dir}")
                return {
                    'has_continuous_audio': False,
                    'silence_duration': 0.0,
                    'mean_volume_db': -100.0,
                    'segment_duration': 0.0,
                    'segments_checked': []
                }
            
            # Build segment file list (segments are .ts files in segments directory)
            segment_files = [os.path.join(segments_dir, f"segment_{seg_num:09d}.ts") for seg_num in segments_to_check]
            
            logger.info(f"[{capture_folder}] Will check {len(segment_files)} segments: {segments_to_check}")
            
            # ✅ DIAGNOSTIC: Check which segments exist and their sizes
            logger.info(f"[{capture_folder}] 📋 Segment files diagnostic:")
            available_segments = []
            missing_segments = []
            
            for seg_num in segments_to_check:
                seg_file = os.path.join(segments_dir, f"segment_{seg_num:09d}.ts")
                if os.path.exists(seg_file):
                    size_kb = os.path.getsize(seg_file) / 1024
                    logger.info(f"[{capture_folder}]   ✓ {seg_file} ({size_kb:.1f} KB)")
                    available_segments.append((seg_num, seg_file))
                else:
                    logger.warning(f"[{capture_folder}]   ✗ MISSING: {seg_file}")
                    missing_segments.append(seg_file)
            
            # ✅ RESILIENT: Use whatever segments we have (even just 1)
            if len(available_segments) == 0:
                logger.error(f"[{capture_folder}] ❌ No segments available: 0/{len(segment_files)} found")
                for missing in missing_segments:
                    logger.error(f"[{capture_folder}]   - {missing}")
                
                # ✅ SIMPLE FALLBACK: Race condition - try previous segment (start_segment - 1)
                logger.warning(f"[{capture_folder}] 🔄 RACE CONDITION: Expected segments not written yet")
                
                if start_segment > 0:
                    fallback_segment = start_segment - 1
                    fallback_path = os.path.join(segments_dir, f"segment_{fallback_segment:09d}.ts")
                    
                    if os.path.exists(fallback_path):
                        logger.warning(f"[{capture_folder}]     Using previous segment: {fallback_segment}")
                        
                        # Use the single fallback segment
                        available_segments = [(fallback_segment, fallback_path)]
                        segment_files_to_use = [fallback_path]
                        segments_used = [fallback_segment]
                        
                        logger.info(f"[{capture_folder}] 🔊 Analyzing fallback segment: {fallback_segment}")
                    else:
                        logger.error(f"[{capture_folder}] ❌ Fallback segment {fallback_segment} also missing")
                        return {
                            'has_continuous_audio': False,
                            'silence_duration': 0.0,
                            'mean_volume_db': -100.0,
                            'segment_duration': 0.0,
                            'segments_checked': []
                        }
                else:
                    logger.error(f"[{capture_folder}] ❌ Cannot fallback - start_segment is 0")
                    return {
                        'has_continuous_audio': False,
                        'silence_duration': 0.0,
                        'mean_volume_db': -100.0,
                        'segment_duration': 0.0,
                        'segments_checked': []
                    }
            else:
                # Some expected segments found - use them
                segment_files_to_use = [seg_file for _, seg_file in available_segments]
                segments_used = [seg_num for seg_num, _ in available_segments]
            
            # ✅ PARTIAL ANALYSIS: Use whatever segments we have
            if missing_segments and len(available_segments) < len(segment_files):
                logger.warning(f"[{capture_folder}] ⚠️  Partial analysis: {len(available_segments)}/{len(segment_files)} segments available")
                logger.warning(f"[{capture_folder}]     Missing: {[os.path.basename(m) for m in missing_segments]}")
                logger.info(f"[{capture_folder}]     Proceeding with available segments (better than aborting)")
            
            logger.info(f"[{capture_folder}] 🔊 Analyzing {len(segment_files_to_use)} segment(s): {segments_used}")
            
            # ✅ OPTIMIZATION: Single segment = check directly (no merge needed)
            if len(segment_files_to_use) == 1:
                single_segment = segment_files_to_use[0]
                segment_size = os.path.getsize(single_segment) / 1024
                logger.info(f"[{capture_folder}] 📁 Single segment analysis (no merge needed): {os.path.basename(single_segment)} ({segment_size:.1f} KB)")
                
                # Calculate duration for this single segment
                segment_duration = get_device_segment_duration(capture_folder)
                logger.info(f"[{capture_folder}] Analyzing single segment audio: {segment_duration:.1f}s")
                
                has_continuous_audio, silence_duration, mean_volume = check_audio_continuous(
                    file_path=single_segment,
                    sample_duration=segment_duration,
                    min_silence_duration=0.1,
                    timeout=10,
                    context=capture_folder
                )
                
                # ✅ LOG: Immediately log the raw result
                logger.info(f"[{capture_folder}] 🔊 Audio check returned: continuous={has_continuous_audio}, silence={silence_duration:.2f}s, volume={mean_volume:.1f}dB")
                
                # ✅ DISTINGUISH: Constant silence vs dropout
                # If silence_duration ≈ segment_duration → constant silence (no audio at all)
                # If silence_duration < segment_duration → true dropout (audio cut out temporarily)
                if abs(silence_duration - segment_duration) < 0.05:  # Within 50ms tolerance
                    logger.info(f"[{capture_folder}] 🔇 CONSTANT SILENCE: {silence_duration:.2f}s silence in {segment_duration:.1f}s total (mean: {mean_volume:.1f}dB)")
                    logger.info(f"[{capture_folder}]     This is NOT a dropout - no audio present at all")
                    # Treat constant silence as "continuous" (i.e., no dropout occurred)
                    has_continuous_audio = True
                elif has_continuous_audio:
                    logger.info(f"[{capture_folder}] 🔊 Audio CONTINUOUS: {mean_volume:.1f}dB (single segment)")
                else:
                    logger.info(f"[{capture_folder}] 🔇 Audio DROPOUT: {silence_duration:.2f}s silence in {segment_duration:.1f}s (mean: {mean_volume:.1f}dB)")
                
                return {
                    'has_continuous_audio': has_continuous_audio,
                    'silence_duration': silence_duration,
                    'mean_volume_db': mean_volume,
                    'segment_duration': segment_duration,
                    'segments_checked': segments_used
                }
            
            # ✅ Multiple segments: Merge and check
            logger.info(f"[{capture_folder}] 🔗 Merging {len(segment_files_to_use)} segments for audio analysis")
            
            # ✅ Use FIXED filenames (overwrite each time - no space accumulation!)
            concat_list_path = f'/tmp/{capture_folder}_concat_list.txt'
            merged_path = f'/tmp/{capture_folder}_audio_check.ts'
            
            try:
                # Write concat list (overwrites previous file)
                with open(concat_list_path, 'w') as f:
                    for seg_file in segment_files_to_use:
                        f.write(f"file '{seg_file}'\n")
                
                logger.info(f"[{capture_folder}] 📝 Concat list written to: {concat_list_path}")
                
                # Merge segments with ffmpeg (overwrites previous merged file)
                merge_cmd = [
                    'ffmpeg',
                    '-hide_banner',
                    '-loglevel', 'warning',  # Changed from 'error' to 'warning' for more details
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_list_path,
                    '-c', 'copy',
                    '-y',  # Overwrite without asking
                    merged_path
                ]
                
                logger.info(f"[{capture_folder}] 🔧 FFmpeg command: {' '.join(merge_cmd)}")
                
                result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=10)
                
                # Clean up concat list (tiny file, but good practice)
                if os.path.exists(concat_list_path):
                    os.unlink(concat_list_path)
                
                if result.returncode != 0:
                    logger.error(f"[{capture_folder}] ❌ FFmpeg merge FAILED (exit code {result.returncode})")
                    logger.error(f"[{capture_folder}] 📋 Attempted segments: {segments_to_check}")
                    logger.error(f"[{capture_folder}] 📂 Segments directory: {segments_dir}")
                    logger.error(f"[{capture_folder}] 📝 Concat list: {concat_list_path}")
                    logger.error(f"[{capture_folder}] 📤 Output path: {merged_path}")
                    if result.stderr:
                        logger.error(f"[{capture_folder}] 🔴 FFmpeg STDERR:")
                        for line in result.stderr.strip().split('\n'):
                            logger.error(f"[{capture_folder}]     {line}")
                    if result.stdout:
                        logger.error(f"[{capture_folder}] 🔵 FFmpeg STDOUT:")
                        for line in result.stdout.strip().split('\n'):
                            logger.error(f"[{capture_folder}]     {line}")
                    
                    # ✅ Return EMPTY segments_checked so caller knows merge FAILED
                    return {
                        'has_continuous_audio': False,
                        'silence_duration': 0.0,
                        'mean_volume_db': -100.0,
                        'segment_duration': 0.0,
                        'segments_checked': []  # ✅ EMPTY = merge failed (caller will abort)
                    }
                
                # Get total duration of merged file
                merged_size = os.path.getsize(merged_path)
                logger.info(f"[{capture_folder}] Merged {len(segment_files_to_use)} segments → {merged_path} ({merged_size/1024:.1f} KB)")
                
                # Analyze merged file for audio continuity
                segment_duration = get_device_segment_duration(capture_folder) * len(segment_files_to_use)
                logger.info(f"[{capture_folder}] Analyzing merged audio: {segment_duration:.1f}s total")
                
                has_continuous_audio, silence_duration, mean_volume = check_audio_continuous(
                    file_path=merged_path,
                    sample_duration=segment_duration,  # Full duration of merged segments
                    min_silence_duration=0.1,  # Detect silence >= 100ms
                    timeout=15,  # Higher timeout for merged file
                    context=capture_folder
                )
                
                # ✅ DISTINGUISH: Constant silence vs dropout
                # If silence_duration ≈ segment_duration → constant silence (no audio at all)
                # If silence_duration < segment_duration → true dropout (audio cut out temporarily)
                if abs(silence_duration - segment_duration) < 0.05:  # Within 50ms tolerance
                    logger.info(f"[{capture_folder}] 🔇 CONSTANT SILENCE: {silence_duration:.2f}s silence in {segment_duration:.1f}s total (mean: {mean_volume:.1f}dB)")
                    logger.info(f"[{capture_folder}]     This is NOT a dropout - no audio present at all")
                    # Treat constant silence as "continuous" (i.e., no dropout occurred)
                    has_continuous_audio = True
                elif has_continuous_audio:
                    logger.info(f"[{capture_folder}] 🔊 Audio CONTINUOUS: {mean_volume:.1f}dB (no dropouts across {len(segment_files_to_use)} segments)")
                else:
                    logger.info(f"[{capture_folder}] 🔇 Audio DROPOUT detected: {silence_duration:.2f}s silence in {segment_duration:.1f}s total (mean: {mean_volume:.1f}dB)")
                
                return {
                    'has_continuous_audio': has_continuous_audio,
                    'silence_duration': silence_duration,
                    'mean_volume_db': mean_volume,
                    'segment_duration': segment_duration,
                    'segments_checked': segments_used
                }
                
            finally:
                # Clean up merged file (frees space immediately instead of waiting for next overwrite)
                if os.path.exists(merged_path):
                    try:
                        os.unlink(merged_path)
                        logger.debug(f"[{capture_folder}] Cleaned up merged audio file: {merged_path}")
                    except Exception as e:
                        logger.warning(f"[{capture_folder}] Failed to delete merged audio file: {e}")
                
                # Also clean up concat list if it still exists
                if os.path.exists(concat_list_path):
                    try:
                        os.unlink(concat_list_path)
                    except:
                        pass
            
        except Exception as e:
            logger.warning(f"[{capture_folder}] Audio check failed: {e}")
            import traceback
            traceback.print_exc()
            # On error, assume dropout detected (safer to proceed with banner detection)
            return {
                'has_continuous_audio': False,
                'silence_duration': 0.0,
                'mean_volume_db': -100.0,
                'segment_duration': 0.0,
                'segments_checked': []
            }
    
    def _write_zapping_in_progress(self, capture_folder: str, frame_filename: str, blackscreen_duration_ms: int):
        """
        Write "in_progress" marker to last_zapping.json IMMEDIATELY when detection starts.
        This allows zap_executor to poll and wait instead of reading stale data.
        
        Written before expensive AI processing (~40 seconds), updated when complete.
        
        ✅ TIMEOUT PROTECTION: Includes timestamp to detect stale markers (> 5 minutes = stale)
        """
        try:
            from shared.src.lib.utils.storage_path_utils import get_metadata_path
            from datetime import datetime
            
            metadata_path = get_metadata_path(capture_folder)
            last_zapping_path = os.path.join(metadata_path, 'last_zapping.json')
            
            in_progress_data = {
                'status': 'in_progress',
                'started_at': datetime.now().isoformat(),
                'started_at_unix': time.time(),  # ✅ ADD: Unix timestamp for timeout check
                'frame_filename': frame_filename,
                'blackscreen_duration_ms': blackscreen_duration_ms,
                'message': 'AI banner detection in progress (may take up to 40 seconds)',
                'timeout_seconds': 300  # ✅ ADD: Max time before marker is considered stale (5 minutes)
            }
            
            # Atomic write
            with open(last_zapping_path + '.tmp', 'w') as f:
                json.dump(in_progress_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.rename(last_zapping_path + '.tmp', last_zapping_path)
            
            logger.info(f"[{capture_folder}] 📝 Written 'in_progress' marker to last_zapping.json")
            
        except Exception as e:
            logger.error(f"[{capture_folder}] Failed to write in_progress marker: {e}")
    
    def _write_zapping_aborted(self, capture_folder: str, frame_filename: str, reason: str):
        """
        Write "aborted" status when zapping detection is skipped/aborted.
        This prevents zap_executor from timing out waiting for a result.
        """
        try:
            from shared.src.lib.utils.storage_path_utils import get_metadata_path
            from datetime import datetime
            
            metadata_path = get_metadata_path(capture_folder)
            last_zapping_path = os.path.join(metadata_path, 'last_zapping.json')
            
            aborted_data = {
                'status': 'aborted',
                'zapping_detected': False,
                'aborted_at': datetime.now().isoformat(),
                'frame_filename': frame_filename,
                'reason': reason
            }
            
            # Atomic write
            with open(last_zapping_path + '.tmp', 'w') as f:
                json.dump(aborted_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.rename(last_zapping_path + '.tmp', last_zapping_path)
            
            logger.info(f"[{capture_folder}] 📝 Written 'aborted' status to last_zapping.json: {reason}")
            
        except Exception as e:
            logger.error(f"[{capture_folder}] Failed to write aborted status: {e}")
    
    def _get_action_from_device_state(self, capture_folder):
        """Read last_action.json from hot storage (simple IPC between processes)"""
        logger.info(f"[{capture_folder}] Reading last_action.json...")
        try:
            import time
            
            # Build path using centralized utility (same as last_zapping.json)
            metadata_path = get_metadata_path(capture_folder)
            last_action_path = os.path.join(metadata_path, 'last_action.json')
            
            logger.info(f"[{capture_folder}] Path: {last_action_path}")
            
            # Check if file exists
            if not os.path.exists(last_action_path):
                logger.info(f"[{capture_folder}] ❌ File not found")
                return None
            
            # Read JSON
            with open(last_action_path, 'r') as f:
                action_data = json.load(f)
            
            # 🔍 DEBUG: Show full file content
            logger.info(f"[{capture_folder}] 📄 last_action.json content:")
            logger.info(f"[{capture_folder}]    {json.dumps(action_data, indent=2)}")
            
            action_timestamp = action_data.get('timestamp')
            if not action_timestamp:
                logger.info(f"[{capture_folder}] ❌ No timestamp in file")
                return None
            
            # Check 10s timeout
            current_time = time.time()
            time_since_action = current_time - action_timestamp
            
            if time_since_action > 10.0:
                logger.info(f"[{capture_folder}] ❌ Action too old ({time_since_action:.1f}s)")
                return None
            
            # Success
            logger.info(f"[{capture_folder}] ✅ AUTOMATIC - action: {action_data.get('command')} ({time_since_action:.1f}s ago)")
            return {
                'last_action_executed': action_data.get('command'),
                'last_action_timestamp': action_timestamp,
                'action_params': action_data.get('params', {}),
                'time_since_action_ms': int(time_since_action * 1000)
            }
                
        except Exception as e:
            logger.error(f"[{capture_folder}] Error reading last_action.json: {e}")
            return None
    
    def process_frame(self, captures_path, filename, queue_size=0):
        """Process a single frame - called by both inotify and startup scan"""
        
        # Log memory usage periodically (every hour)
        log_memory_usage()
        
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
        
        # Check if we need to run detection (expensive) or just add audio (cheap)
        needs_detection = True
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    check_json = json.load(f)
                # If already analyzed, skip detection (but continue to add audio if needed)
                if check_json.get('analyzed'):
                    needs_detection = False
                    # If already has audio, skip entirely BUT update cache first!
                    if 'audio' in check_json:
                        # CRITICAL: Update cache before returning to propagate fresh audio data
                        self.audio_cache[capture_folder] = {
                            'audio': check_json['audio'],
                            'mean_volume_db': check_json.get('mean_volume_db', -100),
                            'audio_check_timestamp': check_json.get('audio_check_timestamp'),
                            'audio_segment_file': check_json.get('audio_segment_file')
                        }
                        return
            except:
                pass  # If can't read, run detection
        
        try:
            sequence = int(filename.split('_')[1].split('.')[0])
            
            # ✅ OPTIMIZATION: Get device state early to check if freeze is ongoing
            device_info = get_device_info_from_capture_folder(capture_folder)
            device_id = device_info.get('device_id', capture_folder)
            device_state = self.incident_manager.get_device_state(device_id)
            
            # ✅ INCIDENT AUDIO HANDLING: During freeze/blackscreen, always set audio=false
            # Reasons:
            # 1. We skip audio checking during incidents (performance optimization)
            # 2. Video incidents make audio state unreliable
            # 3. Showing stale "audio=true" during freeze is confusing
            has_freeze_incident = bool(device_state.get('freeze_event_start'))
            has_blackscreen_incident = bool(device_state.get('blackscreen_event_start'))
            
            # Check last 1 frame for audio data (refreshes cache from transcript_accumulator writes)
            # This runs for EVERY frame to catch audio updates written to recent frames
            # OPTIMIZATION: Reduced from 3 frames to 1 frame to save I/O (66% reduction)
            for i in range(1, 2):  # Check only previous 1 frame (200ms window)
                    prev_json = os.path.join(metadata_path, f'capture_{sequence-i:09d}.json')
                    if os.path.exists(prev_json):
                        try:
                            with open(prev_json, 'r') as f:
                                prev_data = json.load(f)
                            if 'audio' in prev_data:
                                # Found audio data - check if it's different from cache
                                new_audio = prev_data['audio']
                                new_volume = prev_data.get('mean_volume_db', -100)
                                
                                # Only update and log if changed (or cache empty)
                                if capture_folder not in self.audio_cache:
                                    self.audio_cache[capture_folder] = {'audio': new_audio, 'mean_volume_db': new_volume}
                                    audio_val = "✅ YES" if new_audio else "❌ NO"
                                    logger.info(f"[{capture_folder}] 🔍 Cached audio from frame-{i}: audio={audio_val}, volume={new_volume:.1f}dB")
                                    break
                                elif self.audio_cache[capture_folder].get('audio') != new_audio:
                                    # Audio changed - update cache and log
                                    self.audio_cache[capture_folder] = {'audio': new_audio, 'mean_volume_db': new_volume}
                                    audio_val = "✅ YES" if new_audio else "❌ NO"
                                    logger.info(f"[{capture_folder}] 🔄 Audio changed from frame-{i}: audio={audio_val}, volume={new_volume:.1f}dB")
                                    break
                                else:
                                    # Same as cache - just ensure it's fresh (silent update)
                                    self.audio_cache[capture_folder] = {'audio': new_audio, 'mean_volume_db': new_volume}
                                    break
                        except:
                            continue  # Skip corrupted JSON
            
            # Check if JSON already exists and extract audio data early (needed for event tracking)
            existing_audio_data = {}
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r') as f:
                        existing_json = json.load(f)
                    if 'audio' in existing_json:
                        existing_audio_data = {
                            'audio': existing_json['audio'],
                            'mean_volume_db': existing_json.get('mean_volume_db', -100),
                            'audio_check_timestamp': existing_json.get('audio_check_timestamp'),
                            'audio_segment_file': existing_json.get('audio_segment_file')
                        }
                        # CRITICAL FIX: Immediately update cache when reading JSON with audio data
                        # This ensures transcript_accumulator's fresh audio data propagates to subsequent frames
                        self.audio_cache[capture_folder] = existing_audio_data
                        audio_val = "✅ YES" if existing_audio_data['audio'] else "❌ NO"
                        volume = existing_audio_data.get('mean_volume_db', -100)
                        logger.debug(f"[{capture_folder}] 🔄 Cache updated from existing JSON: audio={audio_val}, volume={volume:.1f}dB")
                except:
                    pass
            
            # Use cached audio if JSON doesn't have it yet
            if not existing_audio_data and capture_folder in self.audio_cache:
                existing_audio_data = self.audio_cache[capture_folder]
            
            # ✅ INCIDENT PRIORITY OPTIMIZATION: Skip expensive checks if another incident is ongoing
            # Check device_state to see what's currently active (already loaded above at line 1621)
            
            skip_freeze = False
            skip_blackscreen = False
            skip_macroblocks = False
            
            if needs_detection:
                # Check if blackscreen is ongoing → skip freeze and macroblocks detection
                if device_state.get('blackscreen_event_start'):
                    skip_freeze = True
                    skip_macroblocks = True
                    logger.debug(f"[{capture_folder}] ⏩ Skipping freeze/macroblocks detection (blackscreen ongoing)")
                
                # Check if freeze is ongoing → skip blackscreen and macroblocks detection
                elif device_state.get('freeze_event_start'):
                    skip_blackscreen = True
                    skip_macroblocks = True
                    logger.debug(f"[{capture_folder}] ⏩ Skipping blackscreen/macroblocks detection (freeze ongoing)")
                
                # Calculate freeze duration for optimization (long freezes need less frequent checking)
                freeze_duration_ms = 0
                if device_state.get('freeze_event_start'):
                    from datetime import datetime
                    freeze_start = datetime.fromisoformat(device_state['freeze_event_start'])
                    freeze_duration_ms = int((datetime.now() - freeze_start).total_seconds() * 1000)
                
                # Run detection with skip flags (avoids wasting CPU on lower-priority checks)
                detection_result = detect_issues(
                    frame_path, 
                    queue_size=queue_size, 
                    skip_freeze=skip_freeze, 
                    skip_blackscreen=skip_blackscreen,
                    skip_macroblocks=skip_macroblocks,
                    freeze_duration_ms=freeze_duration_ms  # Pass freeze duration for long-freeze optimization
                )
            else:
                # JSON exists without audio - just add audio from cache (no detection needed)
                detection_result = {}  # Empty dict to merge with existing data
            
            # Merge audio data into detection_result BEFORE event tracking
            if existing_audio_data:
                detection_result.update(existing_audio_data)
            
            # ✅ PRIORITY SUPPRESSION: Apply BEFORE event tracking to avoid unnecessary processing
            # Priority: Blackscreen > Freeze > Macroblocks
            if detection_result is not None:
                has_blackscreen = detection_result.get('blackscreen', False)
                has_freeze = detection_result.get('freeze', False)
                has_macroblocks = detection_result.get('macroblocks', False)
                
                # Suppress lower-priority events BEFORE tracking starts
                if has_blackscreen:
                    # Blackscreen has priority - suppress freeze and macroblocks
                    if has_freeze:
                        detection_result['freeze'] = False
                        logger.debug(f"[{capture_folder}] Suppressing freeze (blackscreen has priority)")
                    if has_macroblocks:
                        detection_result['macroblocks'] = False
                        logger.debug(f"[{capture_folder}] Suppressing macroblocks (blackscreen has priority)")
                elif has_freeze:
                    # Freeze has priority over macroblocks
                    if has_macroblocks:
                        detection_result['macroblocks'] = False
                        logger.debug(f"[{capture_folder}] Suppressing macroblocks (freeze has priority)")
            
            # ALWAYS add event duration tracking (needed for audio_loss even when skipping detection)
            # NOTE: Suppressed events won't trigger tracking since they're now False
            if detection_result is not None:
                detection_result = self._add_event_duration_metadata(capture_folder, detection_result, filename, queue_size)
            
            # Build issues list for logging
            issues = []
            has_blackscreen = detection_result and detection_result.get('blackscreen', False)
            has_freeze = detection_result and detection_result.get('freeze', False)
            has_macroblocks = detection_result and detection_result.get('macroblocks', False)
            
            if has_blackscreen:
                issues.append('blackscreen')
            elif has_freeze:
                issues.append('freeze')
            elif has_macroblocks:
                issues.append('macroblocks')
            
            if issues:
                logger.info(f"[{capture_folder}] Issues: {issues}")
            
            # NOTE: Comparison images (last_3_filenames, last_3_thumbnails) are ALWAYS in JSON
            # even when there's no freeze - this allows displaying them on demand later
            
            # R2 upload is now handled ONLY by incident_manager when creating/resolving DB incidents
            # This simplifies the flow and ensures timing is correct
            
            # Process incident logic (5-minute debounce, DB operations)
            # Thumbnails are uploaded inside process_detection after 5min confirmation
            transitions = self.incident_manager.process_detection(capture_folder, detection_result, self.host_name)
            
            try:
                # Reuse existing_json if we read it earlier, otherwise read now
                existing_data = {}
                if 'existing_json' in locals() and existing_json:
                    existing_data = existing_json
                elif os.path.exists(json_file):
                    try:
                        with open(json_file, 'r') as f:
                            existing_data = json.load(f)
                    except Exception as e:
                        logger.warning(f"[{capture_folder}] Failed to read existing JSON: {e}")
                
                # Audio handling: Update cache if JSON has fresh audio data
                if existing_audio_data and 'audio' in existing_audio_data:
                    # Already extracted audio earlier - update cache
                    self.audio_cache[capture_folder] = existing_audio_data
                    audio_val = "✅ YES" if existing_audio_data['audio'] else "❌ NO"
                    volume = existing_audio_data.get('mean_volume_db', -100)
                    logger.info(f"[{capture_folder}] 🔄 Updated audio cache from {json_file}: audio={audio_val}, volume={volume:.1f}dB")
                    # Make sure existing_data has audio
                    existing_data.update(existing_audio_data)
                elif capture_folder in self.audio_cache:
                    # No audio in JSON but we have cached value - use it
                    existing_data.update(self.audio_cache[capture_folder])
                    audio_val = "✅ YES" if self.audio_cache[capture_folder]['audio'] else "❌ NO"
                    volume = self.audio_cache[capture_folder].get('mean_volume_db', -100)
                    logger.debug(f"[{capture_folder}] 📋 Using cached audio for {json_file}: audio={audio_val}, volume={volume:.1f}dB")
                
                # ✅ CHECK FOR ZAPPING CACHE: Add to next N frames after detection
                zap_cache_data = None
                if capture_folder in self.zapping_cache:
                    cache_entry = self.zapping_cache[capture_folder]
                    if cache_entry['frames_remaining'] > 0:
                        # Add cache to this frame
                        zap_data = cache_entry['zap_data']
                        sequence = int(filename.split('_')[1].split('.')[0])
                        zap_cache_data = {
                            'detected': True,
                            'id': zap_data['id'],  # Same ID for all cache frames (deduplication)
                            'channel_name': zap_data['channel_name'],
                            'channel_number': zap_data['channel_number'],
                            'program_name': zap_data['program_name'],
                            'program_start_time': zap_data['program_start_time'],  # ✅ Now populated
                            'program_end_time': zap_data['program_end_time'],      # ✅ Now populated
                            'blackscreen_duration_ms': zap_data['blackscreen_duration_ms'],
                            'detection_type': zap_data['detection_type'],
                            'confidence': zap_data['confidence'],
                            'detected_at': datetime.now().isoformat(),
                            'audio_silence_duration': zap_data['audio_silence_duration'],
                            'time_since_action_ms': zap_data.get('time_since_action_ms'),      # ✅ ADD: For calculation
                            'total_zap_duration_ms': zap_data.get('total_zap_duration_ms'),    # ✅ ADD: Backend calculated
                            'original_frame': zap_data['original_frame']
                        }
                        
                        # Track frames for logging
                        if 'frames_list' not in cache_entry:
                            cache_entry['frames_list'] = []
                        cache_entry['frames_list'].append(json_file)
                        cache_entry['frames_remaining'] -= 1
                        logger.debug(f"[{capture_folder}] 📋 Added zap_cache to {json_file} ({5 - cache_entry['frames_remaining']}/5)")
                        
                        # Clean up if done
                        if cache_entry['frames_remaining'] <= 0:
                            frames_list = ', '.join(cache_entry['frames_list'])
                            logger.info(f"[{capture_folder}] ✅ Cache safety margin complete (5 frames): {frames_list}")
                            del self.zapping_cache[capture_folder]
                
                if detection_result:
                    # Determine if transcription is worthwhile (skip if incidents present or no audio)
                    freeze = detection_result.get('freeze', False)
                    blackscreen = detection_result.get('blackscreen', False)
                    has_audio = existing_data.get('audio', True)  # Default to True if not yet checked
                    
                    # Skip transcription if freeze, blackscreen, or no audio
                    transcription_needed = not (freeze or blackscreen or not has_audio)
                    
                    # Determine skip reason for logging
                    skip_reason = None
                    if freeze:
                        skip_reason = "freeze"
                    elif blackscreen:
                        skip_reason = "blackscreen"
                    elif not has_audio:
                        skip_reason = "no_audio"
                    
                    analysis_data = {
                        "analyzed": True,
                        "subtitle_ocr_pending": True,
                        "transcription_needed": transcription_needed,
                        "skip_reason": skip_reason,
                        **existing_data,  # Includes audio from cache or JSON
                        **detection_result  # Merge detection results (overwrites if keys conflict)
                    }
                else:
                    analysis_data = {
                        "analyzed": True,
                        "subtitle_ocr_pending": True,
                        **existing_data,  # Includes audio from cache or JSON
                        "error": "detection_result_was_none"
                    }
                
                # ✅ ADD CACHE TO ANALYSIS DATA (if available)
                if zap_cache_data:
                    analysis_data['zap_cache'] = zap_cache_data
                
                with open(json_file, 'w') as f:
                    json.dump(analysis_data, f, indent=2)
                
                # Log successful individual JSON creation
                sequence = int(filename.split('_')[1].split('.')[0])
                has_r2_images = 'r2_images' in analysis_data and analysis_data['r2_images']
                if has_r2_images:
                    r2_count = len(analysis_data.get('r2_images', {}).get('thumbnail_urls', []))
                    logger.info(f"[{capture_folder}] ✓ Created JSON → {json_file} (seq={sequence}, r2_urls={r2_count})")
                else:
                    logger.debug(f"[{capture_folder}] ✓ Created JSON → {json_file} (seq={sequence})")
                
                # Append to chunk: 1 frame per second only (HLS displays at 1-second granularity)
                # OPTIMIZATION: Skip chunk append during backlog to reduce I/O and lock contention
                if sequence % 5 == 0 and queue_size <= 30:
                    try:
                        self._append_to_chunk(capture_folder, filename, analysis_data)
                    except Exception as e:
                        logger.warning(f"[{capture_folder}] Chunk append failed: {e}")
                    
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
                        
                        # 🔍 TRACE: Extract sequence from filename for logging
                        try:
                            sequence = int(filename.split('_')[1].split('.')[0])
                            logger.info(f"[{capture_folder}] 📥 INOTIFY ARRIVED: {filename} (seq={sequence})")
                        except:
                            sequence = None
                            logger.debug(f"[{capture_folder}] inotify event: {filename}")
                        
                        work_queue = self.device_queues[capture_folder]
                        queue_size = work_queue.qsize()
                        
                        # Don't fill queue if >150 (images may be deleted from hot storage before processing)
                        if queue_size > 150:
                            if sequence:
                                logger.warning(f"[{capture_folder}] ⏭️  Queue over 150 ({queue_size}), SKIPPING {filename} (seq={sequence}) - images may expire")
                            else:
                                logger.warning(f"[{capture_folder}] ⏭️  Queue over 150 ({queue_size}), skipping {filename} (images may expire)")
                        else:
                            try:
                                # 🔍 TRACE: Log queue insertion
                                if sequence:
                                    logger.info(f"[{capture_folder}] 📤 QUEUED: {filename} (seq={sequence}, queue_size={queue_size} → {queue_size+1})")
                                
                                work_queue.put_nowait((path, filename))
                                
                                if queue_size > 100:
                                    logger.warning(f"[{capture_folder}] 🔴 Queue backlog: {queue_size}/1000 frames")
                                elif queue_size > 50 and queue_size % 25 == 0:
                                    logger.warning(f"[{capture_folder}] 🟡 Queue backlog: {queue_size}/1000 frames")
                                    
                            except queue.Full:
                                logger.error(f"[{capture_folder}] 🚨 Queue FULL, dropping: {filename}")
                        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            for path in self.dir_to_info.keys():
                try:
                    self.inotify.remove_watch(path)
                except:
                    pass

def cleanup_stale_zapping_markers():
    """
    Clean up any stale zapping detection markers left by crashed/stuck processes.
    
    Stale markers (in_progress > 5 minutes old) can cause high CPU and block detection.
    This runs once at startup to ensure clean state.
    """
    try:
        logger.info("🧹 [STARTUP] Checking for stale zapping markers...")
        
        base_dirs = get_capture_base_directories()
        cleaned_count = 0
        checked_count = 0
        
        for base_dir in base_dirs:
            capture_folder = get_capture_folder(base_dir)
            checked_count += 1
            
            try:
                metadata_path = get_metadata_path(capture_folder)
                last_zapping_path = os.path.join(metadata_path, 'last_zapping.json')
                
                if os.path.exists(last_zapping_path):
                    with open(last_zapping_path, 'r') as f:
                        zapping_data = json.load(f)
                    
                    status = zapping_data.get('status')
                    if status == 'in_progress':
                        # Check if stale (> 5 minutes old)
                        started_at_unix = zapping_data.get('started_at_unix')
                        timeout_seconds = zapping_data.get('timeout_seconds', 300)
                        
                        if started_at_unix:
                            age_seconds = time.time() - started_at_unix
                            if age_seconds > timeout_seconds:
                                # STALE - remove it
                                os.remove(last_zapping_path)
                                cleaned_count += 1
                                logger.warning(f"🗑️  [{capture_folder}] Removed STALE marker (age: {age_seconds:.0f}s > {timeout_seconds}s)")
                            else:
                                logger.info(f"⏳ [{capture_folder}] Found recent in_progress marker (age: {age_seconds:.0f}s) - keeping")
                        else:
                            # No timestamp - assume stale (old format)
                            os.remove(last_zapping_path)
                            cleaned_count += 1
                            logger.warning(f"🗑️  [{capture_folder}] Removed STALE marker (no timestamp)")
            
            except Exception as e:
                logger.warning(f"⚠️  [{capture_folder}] Error checking marker: {e}")
                continue
        
        if cleaned_count > 0:
            logger.info(f"✅ [STARTUP] Cleaned {cleaned_count}/{checked_count} stale zapping markers")
        else:
            logger.info(f"✅ [STARTUP] No stale markers found ({checked_count} devices checked)")
    
    except Exception as e:
        logger.error(f"❌ [STARTUP] Error during stale marker cleanup: {e}")

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
    
    # ✅ STARTUP CLEANUP: Clear any stale zapping markers from previous crashed instances
    cleanup_stale_zapping_markers()
    
    host_name = os.getenv('HOST_NAME', 'unknown')
    
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
