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
from shared.src.lib.utils.zapping_detector_utils import detect_and_record_zapping
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
        # ✅ Use global singleton to share device_state with action execution
        from backend_host.scripts.incident_manager import get_global_incident_manager
        self.incident_manager = get_global_incident_manager()
        self.inotify = inotify.adapters.Inotify()
        
        self.dir_to_info = {}
        self.device_queues = {}
        self.device_workers = {}
        
        # Audio cache: last known audio status per device (updated every 5s by transcript_accumulator)
        self.audio_cache = {}  # {capture_folder: {'audio': bool, 'mean_volume_db': float, 'timestamp': str}}
        
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
    
    def _add_event_duration_metadata(self, capture_folder, detection_result, current_filename):
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
                    
                    # Copy START frame to COLD immediately for visual incidents (hot storage frames expire)
                    if event_type in ['blackscreen', 'macroblocks', 'audio']:
                        current_thumbnail_filename = current_filename.replace('.jpg', '_thumbnail.jpg')
                        from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, copy_to_cold_storage
                        thumbnails_dir = get_thumbnails_path(capture_folder)
                        start_thumbnail_path = os.path.join(thumbnails_dir, current_thumbnail_filename)
                        
                        if os.path.exists(start_thumbnail_path):
                            # Copy to cold storage NOW (safe for 1+ hour, will upload to R2 later if incident persists)
                            cold_path = copy_to_cold_storage(start_thumbnail_path)
                            if cold_path:
                                # For audio, store as audio_loss (not audio) for consistency with incident_type
                                storage_key = 'audio_loss' if event_type == 'audio' else event_type
                                device_state[f'{storage_key}_start_thumbnail_cold'] = cold_path
                                device_state[f'{storage_key}_start_filename'] = current_filename
                                logger.debug(f"[{capture_folder}] Copied {storage_key} START to cold storage")
                            else:
                                logger.warning(f"[{capture_folder}] ⚠️  Failed to copy {event_type} START to cold")
                        else:
                            logger.warning(f"[{capture_folder}] ⚠️  {event_type} START thumbnail not found: {start_thumbnail_path}")
                    
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
                
                # Store closure frame for later upload by incident_manager (when resolving DB)
                # For all visual incidents: blackscreen, freeze, macroblocks, audio_loss
                if event_type in ['blackscreen', 'freeze', 'macroblocks', 'audio']:
                    # Get current frame thumbnail path for closure
                    current_thumbnail_filename = current_filename.replace('.jpg', '_thumbnail.jpg')
                    from shared.src.lib.utils.storage_path_utils import get_thumbnails_path, copy_to_cold_storage
                    thumbnails_dir = get_thumbnails_path(capture_folder)
                    current_thumbnail_path = os.path.join(thumbnails_dir, current_thumbnail_filename)
                    
                    if os.path.exists(current_thumbnail_path):
                        # Copy closure frame to cold storage immediately
                        cold_path = copy_to_cold_storage(current_thumbnail_path)
                        if cold_path:
                            # For audio, store as audio_loss (not audio) for consistency with incident_type
                            storage_key = 'audio_loss' if event_type == 'audio' else event_type
                            device_state[f'{storage_key}_closure_frame'] = cold_path
                            device_state[f'{storage_key}_closure_filename'] = current_filename
                            logger.debug(f"[{capture_folder}] Copied {storage_key} closure frame to cold storage")
                
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
                    
                    # ✅ NON-BLOCKING: Submit to thread pool (AI analysis takes ~5s, don't block frame queue!)
                    self.zapping_executor.submit(
                        self._check_for_zapping_async,
                        capture_folder=capture_folder,
                        device_id=device_id,
                        device_model=device_model,
                        current_filename=current_filename,
                        blackscreen_duration_ms=total_duration_ms
                    )
        
        return detection_result
    
    def _check_for_zapping_async(self, capture_folder, device_id, device_model, current_filename, blackscreen_duration_ms):
        """
        Check if blackscreen was caused by zapping (channel change).
        This happens AFTER blackscreen ends, analyzing the first normal frame.
        
        ✅ ASYNC: Runs in background thread pool to avoid blocking frame processing queue
        (AI banner analysis takes ~5 seconds - would cause major queue backlog if synchronous)
        
        Uses shared zapping detection utility (reuses existing banner detection AI).
        """
        try:
            logger.info(f"[{capture_folder}] 🔍 Zapping worker started for {current_filename}")
            
            # ✅ CLEAN: Read action from device_state (in-memory, instant lookup)
            action_info = self._get_action_from_device_state(device_id)
            
            # Log action info for debugging
            if action_info:
                logger.info(f"[{capture_folder}] 📋 Last action found:")
                logger.info(f"[{capture_folder}]    ⚡ Command: {action_info.get('last_action_executed', 'unknown')}")
                logger.info(f"[{capture_folder}]    ⏰ Timestamp: {action_info.get('last_action_timestamp', 0)}")
                logger.info(f"[{capture_folder}]    ⏱️  Time since action: {action_info.get('time_since_action_ms', 0)}ms")
                logger.info(f"[{capture_folder}]    🎯 Detection type: AUTOMATIC")
            else:
                logger.info(f"[{capture_folder}] 📋 No action found in device_state")
                logger.info(f"[{capture_folder}]    🎯 Detection type: MANUAL")
            
            # Call shared zapping detection function (reuses existing video controller)
            # This is the expensive operation (~5s for AI analysis)
            result = detect_and_record_zapping(
                device_id=device_id,
                device_model=device_model,
                capture_folder=capture_folder,
                frame_filename=current_filename,
                blackscreen_duration_ms=blackscreen_duration_ms,
                action_info=action_info
            )
            
            # Log result regardless of success/failure for debugging
            if result.get('zapping_detected'):
                channel_name = result.get('channel_name', 'Unknown')
                channel_number = result.get('channel_number', '')
                detection_type = result.get('detection_type', 'unknown')
                logger.info(f"[{capture_folder}] 📺 {detection_type.upper()} ZAPPING: {channel_name} {channel_number}")
            elif result.get('error'):
                logger.warning(f"[{capture_folder}] ⚠️  Zapping detection failed: {result.get('error')}")
            else:
                logger.info(f"[{capture_folder}] ℹ️  No zapping detected (no banner found)")
            
        except Exception as e:
            logger.error(f"[{capture_folder}] Error checking for zapping: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_action_from_device_state(self, device_id):
        """
        Get last action from device_state (in-memory, instant lookup).
        
        ✅ CLEAN ARCHITECTURE:
        - Single source of truth (device_state)
        - No file I/O (instant lookup)
        - No race conditions (atomic memory operations)
        - 10s timeout check
        
        Returns action_info if found within 10s, None otherwise.
        """
        import time
        
        device_state = self.incident_manager.get_device_state(device_id)
        last_action = device_state.get('last_action')
        
        if not last_action:
            logger.debug(f"[{device_id}] No action found in device_state - manual zapping")
            return None
        
        # Check 10s timeout
        current_time = time.time()
        action_timestamp = last_action.get('timestamp', 0)
        time_since_action = current_time - action_timestamp
        
        if time_since_action > 10.0:
            logger.debug(f"[{device_id}] Action too old ({time_since_action:.1f}s) - manual zapping")
            return None
        
        # ✅ Action within 10s - associate with this blackscreen
        action_info = {
            'last_action_executed': last_action.get('command'),
            'last_action_timestamp': action_timestamp,
            'action_params': last_action.get('params', {}),
            'time_since_action_ms': int(time_since_action * 1000)
        }
        logger.debug(f"[{device_id}] ✅ Found action in device_state: {action_info['last_action_executed']} ({time_since_action:.1f}s ago)")
        return action_info
    
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
        
        # Check if we need to run detection (expensive) or just add audio (cheap)
        needs_detection = True
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    check_json = json.load(f)
                # If already analyzed, skip detection (but continue to add audio if needed)
                if check_json.get('analyzed'):
                    needs_detection = False
                    # If already has audio, skip entirely
                    if 'audio' in check_json:
                        return
            except:
                pass  # If can't read, run detection
        
        try:
            # Populate audio cache from last 3 frames if empty (handles race condition)
            if capture_folder not in self.audio_cache:
                sequence = int(filename.split('_')[1].split('.')[0])
                for i in range(1, 4):  # Check previous 3 frames
                    prev_json = os.path.join(metadata_path, f'capture_{sequence-i:09d}.json')
                    if os.path.exists(prev_json):
                        with open(prev_json, 'r') as f:
                            prev_data = json.load(f)
                        if 'audio' in prev_data:
                            self.audio_cache[capture_folder] = {'audio': prev_data['audio'], 'mean_volume_db': prev_data.get('mean_volume_db', -100)}
                            logger.info(f"[{capture_folder}] 🔍 Cached audio from frame-{i}: audio={'✅' if prev_data['audio'] else '❌'}, volume={prev_data.get('mean_volume_db', -100):.1f}dB")
                            break
            
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
                except:
                    pass
            
            # Use cached audio if JSON doesn't have it yet
            if not existing_audio_data and capture_folder in self.audio_cache:
                existing_audio_data = self.audio_cache[capture_folder]
            
            # Run expensive detection only if needed
            if needs_detection:
                detection_result = detect_issues(frame_path, queue_size=queue_size)
            else:
                # JSON exists without audio - just add audio from cache (no detection needed)
                detection_result = {}  # Empty dict to merge with existing data
            
            # Merge audio data into detection_result BEFORE event tracking
            if existing_audio_data:
                detection_result.update(existing_audio_data)
            
            # ALWAYS add event duration tracking (needed for audio_loss even when skipping detection)
            if detection_result is not None:
                detection_result = self._add_event_duration_metadata(capture_folder, detection_result, filename)
            
            issues = []
            has_blackscreen = detection_result and detection_result.get('blackscreen', False)
            has_freeze = detection_result and detection_result.get('freeze', False)
            has_macroblocks = detection_result and detection_result.get('macroblocks', False)
            
            # Priority: Blackscreen > Freeze > Macroblocks
            # NOTE: Macroblocks is disabled by default (ENABLE_MACROBLOCKS=False in detector.py)
            if has_blackscreen:
                issues.append('blackscreen')
                # Blackscreen has priority - suppress freeze and macroblocks detection
                if has_freeze:
                    detection_result['freeze'] = False
                    logger.debug(f"[{capture_folder}] Suppressing freeze (blackscreen has priority)")
                if has_macroblocks:
                    detection_result['macroblocks'] = False
                    logger.debug(f"[{capture_folder}] Suppressing macroblocks (blackscreen has priority)")
            elif has_freeze:
                # Freeze has priority over macroblocks
                issues.append('freeze')
                if has_macroblocks:
                    detection_result['macroblocks'] = False
                    logger.debug(f"[{capture_folder}] Suppressing macroblocks (freeze has priority)")
            elif has_macroblocks:
                # Only report macroblocks if no blackscreen or freeze
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
                if sequence % 5 == 0:
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
                        logger.debug(f"[{capture_folder}] inotify event: {filename}")
                        
                        work_queue = self.device_queues[capture_folder]
                        queue_size = work_queue.qsize()
                        
                        # Don't fill queue if >150 (images may be deleted from hot storage before processing)
                        if queue_size > 150:
                            logger.warning(f"[{capture_folder}] ⏭️  Queue over 150 ({queue_size}), skipping {filename} (images may expire)")
                        else:
                            try:
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
