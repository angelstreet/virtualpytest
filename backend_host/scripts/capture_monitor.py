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
        self.incident_manager = IncidentManager()
        self.inotify = inotify.adapters.Inotify()
        
        self.dir_to_info = {}
        self.device_queues = {}
        self.device_workers = {}
        
        # Audio cache: last known audio status per device (updated every 5s by transcript_accumulator)
        self.audio_cache = {}  # {capture_folder: {'audio': bool, 'mean_volume_db': float, 'timestamp': str}}
        
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
                        
                        # Log success
                        logger.info(f"[{capture_folder}] ✓ Merged JSON → {chunk_path} (seq={sequence}, frames={chunk_data['frames_count']})")
                
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
                    
                    # Log event start
                    if event_type == 'audio':
                        volume = detection_result.get('mean_volume_db', -100)
                        logger.info(f"[{capture_folder}] 🔇 AUDIO LOSS started (volume={volume:.1f}dB)")
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
                
                # Log event end
                if event_type == 'audio':
                    volume = detection_result.get('mean_volume_db', -100)
                    logger.info(f"[{capture_folder}] 🔊 AUDIO RESTORED after {total_duration_ms/1000:.1f}s (volume={volume:.1f}dB)")
                else:
                    logger.info(f"[{capture_folder}] ✅ {event_type.upper()} ended after {total_duration_ms/1000:.1f}s")
                
                # ✅ Automatic zapping detection when blackscreen ends
                if event_type == 'blackscreen' and total_duration_ms < 10000:
                    # Trigger for blackscreens up to 10s (zapping can take time depending on signal/TV)
                    # Blackscreens > 10s are likely real incidents, not channel changes
                    logger.info(f"[{capture_folder}] Blackscreen ended ({total_duration_ms}ms) - checking for zapping...")
                    self._check_for_zapping(
                        capture_folder=capture_folder,
                        device_id=device_id,
                        device_model=device_model,
                        current_filename=current_filename,
                        blackscreen_duration_ms=total_duration_ms
                    )
        
        return detection_result
    
    def _check_for_zapping(self, capture_folder, device_id, device_model, current_filename, blackscreen_duration_ms):
        """
        Check if blackscreen was caused by zapping (channel change).
        This happens AFTER blackscreen ends, analyzing the first normal frame.
        
        Uses shared zapping detection utility (reuses existing banner detection AI).
        """
        try:
            # Get action info from current frame JSON (with 10s timeout check)
            action_info = self._read_action_from_frame_json(capture_folder, current_filename)
            
            # Call shared zapping detection function (reuses existing video controller)
            result = detect_and_record_zapping(
                device_id=device_id,
                device_model=device_model,
                capture_folder=capture_folder,
                frame_filename=current_filename,
                blackscreen_duration_ms=blackscreen_duration_ms,
                action_info=action_info
            )
            
            if result.get('zapping_detected'):
                channel_name = result.get('channel_name', 'Unknown')
                channel_number = result.get('channel_number', '')
                detection_type = result.get('detection_type', 'unknown')
                logger.info(f"[{capture_folder}] 📺 {detection_type.upper()} ZAPPING: {channel_name} {channel_number}")
            
        except Exception as e:
            logger.error(f"[{capture_folder}] Error checking for zapping: {e}")
    
    def _read_action_from_frame_json(self, capture_folder, frame_filename):
        """
        Read last_action info from frame JSON with 10s timeout check.
        Returns None if no action found or action is too old (> 10s).
        """
        from datetime import datetime
        
        metadata_path = get_metadata_path(capture_folder)
        json_file = os.path.join(metadata_path, frame_filename.replace('.jpg', '.json'))
        
        if not os.path.exists(json_file):
            return None
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Check if action exists
            last_action_timestamp = data.get('last_action_timestamp')
            if not last_action_timestamp:
                return None  # No action found
            
            # ✅ 10-SECOND TIMEOUT CHECK
            frame_timestamp_str = data.get('timestamp')
            if not frame_timestamp_str:
                return None
            
            frame_timestamp = datetime.fromisoformat(frame_timestamp_str.replace('Z', '+00:00')).timestamp()
            time_since_action = frame_timestamp - last_action_timestamp
            
            if time_since_action > 10.0:
                logger.debug(f"[{capture_folder}] Action too old ({time_since_action:.1f}s) - manual zapping")
                return None  # Action too old → manual zapping
            
            # ✅ Action within 10s - associate with this blackscreen
            return {
                'last_action_executed': data.get('last_action_executed'),
                'last_action_timestamp': last_action_timestamp,
                'action_params': data.get('action_params', {}),
                'time_since_action_ms': int(time_since_action * 1000)
            }
            
        except Exception as e:
            logger.error(f"[{capture_folder}] Error reading action from JSON: {e}")
            return None
    
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
            
            # Run expensive detection only if needed
            if needs_detection:
                detection_result = detect_issues(frame_path, queue_size=queue_size)
                # Add event duration tracking metadata
                detection_result = self._add_event_duration_metadata(capture_folder, detection_result, filename)
            else:
                # JSON exists without audio - just add audio from cache (no detection needed)
                detection_result = {}  # Empty dict to merge with existing data
            
            issues = []
            if detection_result and detection_result.get('blackscreen', False):
                issues.append('blackscreen')
            if detection_result and detection_result.get('freeze', False):
                issues.append('freeze')
            
            if issues:
                logger.info(f"[{capture_folder}] Issues: {issues}")
            
            # Upload freeze frames to R2 ONCE per freeze event (not every frame)
            # Freeze is confirmed when detector returns 3 matching images
            freeze_urls_newly_uploaded = False  # Track if URLs are new or cached
            if detection_result and detection_result.get('freeze', False):
                last_3_captures = detection_result.get('last_3_filenames', [])
                if last_3_captures:
                    # Get device_id (same key used by incident_manager.process_detection)
                    device_info = get_device_info_from_capture_folder(capture_folder)
                    device_id = device_info.get('device_id', capture_folder)
                    
                    # Get device state from incident manager (creates if doesn't exist)
                    device_state = self.incident_manager.get_device_state(device_id)
                    
                    # Check if we already uploaded for this freeze event
                    cached_r2_urls = device_state.get('freeze_r2_urls')
                    
                    if not cached_r2_urls:
                        # First freeze frame - upload to R2 with HHMM-based naming
                        now = datetime.now()
                        time_key = f"{now.hour:02d}{now.minute:02d}"  # "1300"
                        
                        # Use last_3_thumbnails from detector (already validated to exist)
                        last_3_thumbnails = detection_result.get('last_3_thumbnails', [])
                        
                        if last_3_thumbnails:
                            logger.info(f"[{capture_folder}] 🆕 NEW freeze detected - uploading {len(last_3_thumbnails)} thumbnails to R2 (time_key={time_key})")
                        else:
                            logger.warning(f"[{capture_folder}] 🆕 NEW freeze detected but no thumbnails available (detector returned {len(last_3_captures)} captures)")
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
                            logger.info(f"[{capture_folder}] 📤 Uploaded {len(r2_urls['thumbnail_urls'])} FREEZE thumbnails to R2:")
                            for i, url in enumerate(r2_urls['thumbnail_urls']):
                                logger.info(f"[{capture_folder}]   🖼️  R2 URL {i+1}: {url}")
                        else:
                            logger.warning(f"[{capture_folder}] R2 upload failed, keeping local paths in JSON")
                    
                    else:
                        # Freeze ongoing - reuse cached R2 URLs from first upload
                        detection_result['last_3_thumbnails'] = cached_r2_urls
                        detection_result['r2_images'] = device_state.get('freeze_r2_images', {
                            'thumbnail_urls': cached_r2_urls
                        })
                        logger.debug(f"[{capture_folder}] Freeze ongoing")
            
            # Process incident logic (5-minute debounce, DB operations)
            # Thumbnails are uploaded inside process_detection after 5min confirmation
            transitions = self.incident_manager.process_detection(capture_folder, detection_result, self.host_name)
            
            try:
                # Check if JSON already exists (transcript_accumulator might have written audio data)
                existing_data = {}
                if os.path.exists(json_file):
                    try:
                        with open(json_file, 'r') as f:
                            existing_data = json.load(f)
                    except Exception as e:
                        logger.warning(f"[{capture_folder}] Failed to read existing JSON: {e}")
                
                # Audio handling: Update cache if JSON has fresh audio data, otherwise use cached value
                if 'audio' in existing_data:
                    # JSON has audio data from transcript_accumulator - update cache
                    self.audio_cache[capture_folder] = {
                        'audio': existing_data['audio'],
                        'mean_volume_db': existing_data.get('mean_volume_db', -100),
                        'audio_check_timestamp': existing_data.get('audio_check_timestamp'),
                        'audio_segment_file': existing_data.get('audio_segment_file')
                    }
                    audio_val = "✅ YES" if existing_data['audio'] else "❌ NO"
                    volume = existing_data.get('mean_volume_db', -100)
                    logger.info(f"[{capture_folder}] 🔄 Updated audio cache from {os.path.basename(json_file)}: audio={audio_val}, volume={volume:.1f}dB")
                elif capture_folder in self.audio_cache:
                    # No audio in JSON but we have cached value - use it
                    existing_data.update(self.audio_cache[capture_folder])
                    audio_val = "✅ YES" if self.audio_cache[capture_folder]['audio'] else "❌ NO"
                    volume = self.audio_cache[capture_folder].get('mean_volume_db', -100)
                    logger.debug(f"[{capture_folder}] 📋 Using cached audio for {os.path.basename(json_file)}: audio={audio_val}, volume={volume:.1f}dB")
                
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
                    logger.info(f"[{capture_folder}] ✓ Created JSON → {os.path.basename(json_file)} (seq={sequence}, r2_urls={r2_count})")
                else:
                    logger.debug(f"[{capture_folder}] ✓ Created JSON → {os.path.basename(json_file)} (seq={sequence})")
                
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
