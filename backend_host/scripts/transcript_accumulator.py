#!/usr/bin/env python3
"""
inotify-based Transcript Accumulator - Dual Pipeline (MP4→MP3→JSON)
Event-driven processing: Zero CPU when idle, immediate response to new files

Pipeline 1: MP4 → MP3 (audio extraction)
  - Watches /video/{hour}/ directories for chunk_10min_X.mp4
  - Extracts audio → chunk_10min_X.mp3
  
Pipeline 2: MP3 → JSON (transcription)
  - Watches /audio/{hour}/ directories for chunk_10min_X.mp3
  - Transcribes → chunk_10min_X.json

Perfect alignment: chunk_10min_X.mp4 + chunk_10min_X.mp3 + chunk_10min_X.json
"""
import os
import sys
import json
import subprocess
import logging
import queue
from queue import LifoQueue
import threading
from datetime import datetime
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_host_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(backend_host_dir)
sys.path.insert(0, project_root)

import inotify.adapters

from shared.src.lib.utils.storage_path_utils import (
    get_capture_base_directories, 
    get_capture_folder, 
    get_device_info_from_capture_folder, 
    get_device_base_path,
    get_audio_path,
    get_transcript_path,
    get_cold_segments_path
)

logger = logging.getLogger(__name__)

# Configuration
CHUNK_DURATION_MINUTES = 10

def cleanup_logs_on_startup():
    """Clean up log file on service restart for fresh debugging"""
    try:
        log_file = '/tmp/transcript_accumulator.log'
        
        print(f"[@transcript_accumulator] Cleaning log on service restart...")
        
        if os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write(f"=== LOG CLEANED ON SERVICE RESTART: {datetime.now().isoformat()} ===\n")
            print(f"[@transcript_accumulator] ✓ Cleaned: {log_file}")
        else:
            print(f"[@transcript_accumulator] ○ Not found (will be created): {log_file}")
                
        print(f"[@transcript_accumulator] Log cleanup complete - fresh logs for debugging")
                
    except Exception as e:
        print(f"[@transcript_accumulator] Warning: Could not clean log file: {e}")

def has_audio_stream(mp4_path: str) -> bool:
    """
    Check if MP4 file has an audio stream using ffprobe
    
    Args:
        mp4_path: Path to MP4 file
    
    Returns:
        bool: True if audio stream exists
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a:0',
            '-show_entries', 'stream=codec_type',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            mp4_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        # If audio stream exists, output will be "audio"
        return result.stdout.strip() == 'audio'
        
    except Exception as e:
        logger.warning(f"Failed to probe audio stream: {e}")
        # On error, assume audio exists and let FFmpeg handle it
        return True

def extract_audio_from_mp4(mp4_path: str, mp3_path: str, capture_folder: str, hour: int, chunk_index: int) -> bool:
    """
    Extract audio from MP4 chunk using FFmpeg
    
    Args:
        mp4_path: Path to MP4 file (chunk_10min_X.mp4)
        mp3_path: Output path for MP3 file (chunk_10min_X.mp3)
        capture_folder: Device identifier
        hour: Hour (0-23)
        chunk_index: Chunk within hour (0-5)
    
    Returns:
        bool: True if extraction succeeded
    """
    mp3_tmp_path = None
    try:
        # Pre-check: Does MP4 have audio stream?
        if not has_audio_stream(mp4_path):
            logger.info(f"[{capture_folder}] 🔇 No audio stream: {hour}/chunk_10min_{chunk_index}.mp4 (video-only)")
            return False
        
        logger.info(f"[{capture_folder}] 🎵 Extracting audio: {hour}/chunk_10min_{chunk_index}.mp4 → .mp3")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(mp3_path), exist_ok=True)
        
        # Create temp file in /tmp with proper .mp3 extension (FFmpeg needs proper extension)
        # One temp file per device (overwritten each time, since worker processes one at a time)
        mp3_tmp_path = f'/tmp/audio_{capture_folder}.mp3'
        
        cmd = [
            'ffmpeg',
            '-i', mp4_path,
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-q:a', '2',  # Good quality
            '-y',  # Overwrite
            mp3_tmp_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"[{capture_folder}] ❌ FFmpeg failed: {result.stderr}")
            return False
        
        # Atomic move from /tmp to final destination
        os.rename(mp3_tmp_path, mp3_path)
        
        # Get file size for logging
        mp3_size_mb = os.path.getsize(mp3_path) / (1024 * 1024)
        logger.info(f"[{capture_folder}] ✅ Audio extracted: {mp3_size_mb:.1f}MB")
        
        return True
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Error extracting audio: {e}")
        # Clean up temp file if exists
        if mp3_tmp_path and os.path.exists(mp3_tmp_path):
            try:
                os.remove(mp3_tmp_path)
            except:
                pass
        return False

def transcribe_mp3_chunk(mp3_path: str, capture_folder: str, hour: int, chunk_index: int) -> dict:
    """
    Transcribe a single 10-minute MP3 chunk using Whisper
    
    Args:
        mp3_path: Path to MP3 file (chunk_10min_X.mp3)
        capture_folder: Device identifier
        hour: Hour (0-23)
        chunk_index: Chunk within hour (0-5)
    
    Returns:
        dict: Transcript data with timed segments
    """
    try:
        logger.info(f"[{capture_folder}] 🎬 Transcribing chunk_10min_{chunk_index}.mp3 (hour {hour})")
        
        from shared.src.lib.utils.audio_transcription_utils import transcribe_audio
        import time
        
        start_time = time.time()
        result = transcribe_audio(mp3_path, model_name='tiny', skip_silence_check=False, device_id=capture_folder)
        
        transcript = result.get('transcript', '').strip()
        language = result.get('language', 'unknown')
        confidence = result.get('confidence', 0.0)
        timed_segments = result.get('segments', [])
        elapsed = time.time() - start_time
        
        logger.info(f"[{capture_folder}] 📝 Language: {language} | Confidence: {confidence:.2f} | Duration: {elapsed:.1f}s")
        if transcript:
            preview = transcript[:200] + ('...' if len(transcript) > 200 else '')
            logger.info(f"[{capture_folder}] 💬 '{preview}'")
            logger.info(f"[{capture_folder}] ⏱️  Generated {len(timed_segments)} timed segments for subtitle display")
        else:
            logger.info(f"[{capture_folder}] 🔇 No speech detected in chunk")
        
        transcript_data = {
            'capture_folder': capture_folder,
            'hour': hour,
            'chunk_index': chunk_index,
            'chunk_duration_minutes': CHUNK_DURATION_MINUTES,
            'language': language,
            'transcript': transcript,
            'confidence': confidence,
            'transcription_time_seconds': elapsed,
            'timestamp': datetime.now().isoformat(),
            'mp3_file': os.path.basename(mp3_path),
            'segments': timed_segments
        }
        
        return transcript_data
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Error transcribing MP3 chunk: {e}")
        return None

def save_transcript_chunk(capture_folder: str, hour: int, chunk_index: int, transcript_data: dict, has_mp3: bool = True):
    """
    Save transcript JSON file aligned with MP4/MP3 chunks
    
    Args:
        capture_folder: Device folder name (e.g., 'capture1')
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
        transcript_data: Transcript data to save
        has_mp3: Whether corresponding MP3 exists
    """
    transcript_base = get_transcript_path(capture_folder)
    transcript_dir = os.path.join(transcript_base, str(hour))
    os.makedirs(transcript_dir, exist_ok=True)
    
    transcript_path = os.path.join(transcript_dir, f'chunk_10min_{chunk_index}.json')
    
    # Atomic write
    with open(transcript_path + '.tmp', 'w') as f:
        json.dump(transcript_data, f, indent=2)
    os.rename(transcript_path + '.tmp', transcript_path)
    
    logger.info(f"✅ Saved: /transcript/{hour}/chunk_10min_{chunk_index}.json")
    
    # Update transcript manifest
    try:
        device_base_path = get_device_base_path(capture_folder)
        from backend_host.scripts.hot_cold_archiver import update_transcript_manifest
        update_transcript_manifest(device_base_path, hour, chunk_index, transcript_path, has_mp3=has_mp3)
    except Exception as e:
        logger.warning(f"Failed to update transcript manifest: {e}")

class InotifyTranscriptMonitor:
    """
    Dual-pipeline inotify monitor with per-device queue processing
    
    Pipeline 1: MP4 → MP3 (audio extraction)
    Pipeline 2: MP3 → JSON (transcription)
    
    Intelligent backlog processing:
    - Prioritize inotify events (new files)
    - Process backlog in batches of 3 when idle
    - Track full backlog for visibility
    """
    
    def __init__(self, monitored_devices):
        """
        Initialize inotify monitor with dual pipelines
        
        Args:
            monitored_devices: List of dicts with device info
                [{'device_folder': 'capture1', 'segments_base': '/path/to/segments', 'audio_base': '/path/to/audio'}]
        """
        self.monitored_devices = monitored_devices
        self.inotify = inotify.adapters.Inotify()
        
        # Path mappings for event routing
        self.segments_path_to_device = {}  # segments path → device_folder
        self.audio_path_to_device = {}  # audio path → device_folder
        
        # Per-device queues (LIFO = newest first)
        self.mp4_queues = {}  # device_folder → LIFO queue for MP4→MP3
        self.mp3_queues = {}  # device_folder → LIFO queue for MP3→JSON
        
        # Backlog tracking (sorted by mtime, newest first)
        self.mp4_backlog = {}  # device_folder → list of (mtime, hour_dir, filename)
        self.mp3_backlog = {}  # device_folder → list of (mtime, hour_dir, filename)
        self.backlog_lock = threading.Lock()  # Protect backlog access
        
        # Worker threads
        self.mp4_workers = {}
        self.mp3_workers = {}
        
        self._setup_watches()
        self._start_workers()
        self._scan_existing_files()
    
    def _setup_watches(self):
        """Setup inotify watches for all segments and audio directories"""
        logger.info("=" * 80)
        logger.info("Setting up inotify watches (dual pipeline):")
        logger.info("=" * 80)
        
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            segments_base = device_info['segments_base']
            audio_base = device_info['audio_base']
            
            logger.info(f"[{device_folder}] Setting up watches...")
            
            # Watch all 24 hour directories for segments (MP4 chunks)
            segments_watch_count = 0
            for hour in range(24):
                segments_hour_dir = os.path.join(segments_base, str(hour))
                if os.path.exists(segments_hour_dir):
                    self.inotify.add_watch(segments_hour_dir)
                    self.segments_path_to_device[segments_hour_dir] = device_folder
                    segments_watch_count += 1
                else:
                    # Create directory so inotify can watch it
                    os.makedirs(segments_hour_dir, exist_ok=True)
                    self.inotify.add_watch(segments_hour_dir)
                    self.segments_path_to_device[segments_hour_dir] = device_folder
                    segments_watch_count += 1
            
            # Watch all 24 hour directories for audio (MP3 chunks)
            audio_watch_count = 0
            for hour in range(24):
                audio_hour_dir = os.path.join(audio_base, str(hour))
                if os.path.exists(audio_hour_dir):
                    self.inotify.add_watch(audio_hour_dir)
                    self.audio_path_to_device[audio_hour_dir] = device_folder
                    audio_watch_count += 1
                else:
                    # Create directory so inotify can watch it
                    os.makedirs(audio_hour_dir, exist_ok=True)
                    self.inotify.add_watch(audio_hour_dir)
                    self.audio_path_to_device[audio_hour_dir] = device_folder
                    audio_watch_count += 1
            
            logger.info(f"[{device_folder}] ✓ Segments watches: {segments_watch_count}/24 hour dirs")
            logger.info(f"[{device_folder}] ✓ Audio watches: {audio_watch_count}/24 hour dirs")
        
        logger.info("=" * 80)
        logger.info(f"Total: {len(self.segments_path_to_device)} segments + {len(self.audio_path_to_device)} audio watches")
        logger.info("=" * 80)
    
    def _start_workers(self):
        """Start worker threads for each device (2 workers per device)"""
        logger.info("Starting worker threads (2 per device):")
        
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            
            # Create LIFO queues (newest first)
            self.mp4_queues[device_folder] = LifoQueue(maxsize=100)
            self.mp3_queues[device_folder] = LifoQueue(maxsize=100)
            
            # Worker 1: MP4 → MP3 (audio extraction - fast)
            mp4_worker = threading.Thread(
                target=self._mp4_worker,
                args=(device_folder,),
                daemon=True,
                name=f"mp4-worker-{device_folder}"
            )
            mp4_worker.start()
            self.mp4_workers[device_folder] = mp4_worker
            
            # Worker 2: MP3 → JSON (transcription - slow)
            mp3_worker = threading.Thread(
                target=self._mp3_worker,
                args=(device_folder,),
                daemon=True,
                name=f"mp3-worker-{device_folder}"
            )
            mp3_worker.start()
            self.mp3_workers[device_folder] = mp3_worker
            
            logger.info(f"[{device_folder}] ✓ Started MP4→MP3 worker (audio extraction)")
            logger.info(f"[{device_folder}] ✓ Started MP3→JSON worker (transcription)")
    
    def _scan_existing_files(self):
        """
        Scan for ALL unprocessed MP4/MP3 files and build backlog
        Enqueue only 3 most recent for immediate processing
        """
        from pathlib import Path
        
        logger.info("=" * 80)
        logger.info("Scanning for existing files (building backlog):")
        logger.info("=" * 80)
        
        # Build per-device backlogs
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            segments_base = device_info['segments_base']
            audio_base = device_info['audio_base']
            
            device_mp4_backlog = []
            device_mp3_backlog = []
            
            # Scan MP4 chunks (segments) - find ALL unprocessed
            for hour in range(24):
                hour_dir = os.path.join(segments_base, str(hour))
                if not os.path.exists(hour_dir):
                    continue
                
                for mp4_file in Path(hour_dir).glob('chunk_10min_*.mp4'):
                    chunk_index = int(mp4_file.stem.replace('chunk_10min_', ''))
                    
                    # Check if MP3 already exists
                    mp3_path = os.path.join(audio_base, str(hour), f'chunk_10min_{chunk_index}.mp3')
                    if not os.path.exists(mp3_path):
                        mtime = mp4_file.stat().st_mtime
                        device_mp4_backlog.append((mtime, hour_dir, mp4_file.name))
            
            # Scan MP3 chunks (audio) - find ALL unprocessed
            for hour in range(24):
                hour_dir = os.path.join(audio_base, str(hour))
                if not os.path.exists(hour_dir):
                    continue
                
                for mp3_file in Path(hour_dir).glob('chunk_10min_*.mp3'):
                    chunk_index = int(mp3_file.stem.replace('chunk_10min_', ''))
                    
                    # Check if transcript already exists
                    transcript_base = get_transcript_path(device_folder)
                    transcript_path = os.path.join(transcript_base, str(hour), f'chunk_10min_{chunk_index}.json')
                    if not os.path.exists(transcript_path):
                        mtime = mp3_file.stat().st_mtime
                        device_mp3_backlog.append((mtime, hour_dir, mp3_file.name))
            
            # Sort by mtime (newest first)
            device_mp4_backlog.sort(reverse=True, key=lambda x: x[0])
            device_mp3_backlog.sort(reverse=True, key=lambda x: x[0])
            
            # Store backlog
            self.mp4_backlog[device_folder] = device_mp4_backlog
            self.mp3_backlog[device_folder] = device_mp3_backlog
            
            # Log backlog status
            if device_mp4_backlog:
                logger.info(f"[{device_folder}] 📦 MP4 backlog: {len(device_mp4_backlog)} chunks need audio extraction")
            if device_mp3_backlog:
                logger.info(f"[{device_folder}] 📦 MP3 backlog: {len(device_mp3_backlog)} chunks need transcription")
            
            # Enqueue 3 most recent MP4s for immediate processing
            if device_mp4_backlog:
                immediate_mp4s = device_mp4_backlog[:3]
                logger.info(f"[{device_folder}] ⚡ Enqueuing {len(immediate_mp4s)} most recent MP4s:")
                for mtime, hour_dir, filename in immediate_mp4s:
                    from datetime import datetime
                    mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"    {filename} (modified: {mtime_str})")
                    try:
                        self.mp4_queues[device_folder].put_nowait((hour_dir, filename))
                    except queue.Full:
                        logger.warning(f"    Queue full, skipping {filename}")
            
            # Enqueue 3 most recent MP3s for immediate processing
            if device_mp3_backlog:
                immediate_mp3s = device_mp3_backlog[:3]
                logger.info(f"[{device_folder}] ⚡ Enqueuing {len(immediate_mp3s)} most recent MP3s:")
                for mtime, hour_dir, filename in immediate_mp3s:
                    from datetime import datetime
                    mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"    {filename} (modified: {mtime_str})")
                    try:
                        self.mp3_queues[device_folder].put_nowait((hour_dir, filename))
                    except queue.Full:
                        logger.warning(f"    Queue full, skipping {filename}")
        
        # Summary
        total_mp4_backlog = sum(len(backlog) for backlog in self.mp4_backlog.values())
        total_mp3_backlog = sum(len(backlog) for backlog in self.mp3_backlog.values())
        logger.info("=" * 80)
        logger.info(f"📊 Total backlog: {total_mp4_backlog} MP4s + {total_mp3_backlog} MP3s")
        logger.info("🎯 Strategy: Process new files (inotify) first, then backlog when idle (3 at a time)")
        logger.info("=" * 80)
    
    def _process_mp4_backlog_batch(self, device_folder):
        """
        Process up to 3 items from MP4 backlog when idle
        Returns number of items added to queue
        """
        with self.backlog_lock:
            backlog = self.mp4_backlog.get(device_folder, [])
            if not backlog:
                return 0
            
            # Take up to 3 items from backlog
            batch = backlog[:3]
            self.mp4_backlog[device_folder] = backlog[3:]  # Remove processed items
            
            added = 0
            for mtime, hour_dir, filename in batch:
                try:
                    self.mp4_queues[device_folder].put_nowait((hour_dir, filename))
                    added += 1
                except queue.Full:
                    # Put back in backlog if queue is full
                    self.mp4_backlog[device_folder].insert(0, (mtime, hour_dir, filename))
                    break
            
            remaining = len(self.mp4_backlog[device_folder])
            if added > 0:
                logger.info(f"[{device_folder}] 🔄 Backlog: Added {added} MP4s to queue ({remaining} remaining)")
            
            return added
    
    def _mp4_worker(self, device_folder):
        """Worker thread for MP4 → MP3 audio extraction (fast, ~3s per chunk)"""
        work_queue = self.mp4_queues[device_folder]
        
        logger.info(f"[{device_folder}] MP4 worker ready (audio extraction pipeline)")
        
        while True:
            try:
                # Try to get work with timeout for idle detection
                path, filename = work_queue.get(timeout=5)
            except queue.Empty:
                # Queue is empty - check backlog
                if self._process_mp4_backlog_batch(device_folder) == 0:
                    # No backlog either - truly idle
                    continue
                else:
                    # Added backlog items, get next item
                    continue
            
            try:
                # Log queue size occasionally
                queue_size = work_queue.qsize()
                if queue_size > 10:
                    logger.warning(f"[{device_folder}] MP4 queue backlog: {queue_size} chunks")
                
                # Parse hour and chunk_index from path and filename
                hour = int(os.path.basename(path))
                chunk_index = int(filename.replace('chunk_10min_', '').replace('.mp4', ''))
                
                mp4_path = os.path.join(path, filename)
                
                # Build MP3 output path (same structure under /audio/)
                device_base_path = get_device_base_path(device_folder)
                audio_base = get_audio_path(device_folder)
                mp3_path = os.path.join(audio_base, str(hour), f'chunk_10min_{chunk_index}.mp3')
                
                # Skip if MP3 already exists
                if os.path.exists(mp3_path):
                    logger.debug(f"[{device_folder}] Skipping {hour}/chunk_10min_{chunk_index}.mp4 (MP3 exists)")
                    continue
                
                # Extract audio
                logger.info("=" * 80)
                success = extract_audio_from_mp4(mp4_path, mp3_path, device_folder, hour, chunk_index)
                if success:
                    logger.info(f"[{device_folder}] ✅ Audio extraction complete for hour {hour}, chunk {chunk_index}")
                else:
                    logger.warning(f"[{device_folder}] ⚠️ Audio extraction failed for {hour}/chunk_10min_{chunk_index}.mp4")
                logger.info("=" * 80)
                
            except Exception as e:
                logger.error(f"[{device_folder}] MP4 worker error: {e}")
            finally:
                work_queue.task_done()
    
    def _process_mp3_backlog_batch(self, device_folder):
        """
        Process up to 3 items from MP3 backlog when idle
        Returns number of items added to queue
        """
        with self.backlog_lock:
            backlog = self.mp3_backlog.get(device_folder, [])
            if not backlog:
                return 0
            
            # Take up to 3 items from backlog
            batch = backlog[:3]
            self.mp3_backlog[device_folder] = backlog[3:]  # Remove processed items
            
            added = 0
            for mtime, hour_dir, filename in batch:
                try:
                    self.mp3_queues[device_folder].put_nowait((hour_dir, filename))
                    added += 1
                except queue.Full:
                    # Put back in backlog if queue is full
                    self.mp3_backlog[device_folder].insert(0, (mtime, hour_dir, filename))
                    break
            
            remaining = len(self.mp3_backlog[device_folder])
            if added > 0:
                logger.info(f"[{device_folder}] 🔄 Backlog: Added {added} MP3s to queue ({remaining} remaining)")
            
            return added
    
    def _mp3_worker(self, device_folder):
        """Worker thread for MP3 → JSON transcription (slow, ~2min per chunk)"""
        work_queue = self.mp3_queues[device_folder]
        
        logger.info(f"[{device_folder}] MP3 worker ready (transcription pipeline)")
        
        while True:
            try:
                # Try to get work with timeout for idle detection
                path, filename = work_queue.get(timeout=5)
            except queue.Empty:
                # Queue is empty - check backlog
                if self._process_mp3_backlog_batch(device_folder) == 0:
                    # No backlog either - truly idle
                    continue
                else:
                    # Added backlog items, get next item
                    continue
            
            try:
                # Log queue size occasionally
                queue_size = work_queue.qsize()
                if queue_size > 5:
                    logger.warning(f"[{device_folder}] MP3 queue backlog: {queue_size} chunks (transcription is slow)")
                
                # Parse hour and chunk_index from path and filename
                hour = int(os.path.basename(path))
                chunk_index = int(filename.replace('chunk_10min_', '').replace('.mp3', ''))
                
                mp3_path = os.path.join(path, filename)
                
                # Build transcript output path
                transcript_base = get_transcript_path(device_folder)
                transcript_path = os.path.join(transcript_base, str(hour), f'chunk_10min_{chunk_index}.json')
                
                # Skip if transcript already exists
                if os.path.exists(transcript_path):
                    logger.debug(f"[{device_folder}] Skipping {hour}/chunk_10min_{chunk_index}.mp3 (transcript exists)")
                    continue
                
                # Transcribe
                logger.info("=" * 80)
                transcript_data = transcribe_mp3_chunk(mp3_path, device_folder, hour, chunk_index)
                
                if transcript_data:
                    save_transcript_chunk(device_folder, hour, chunk_index, transcript_data, has_mp3=True)
                    logger.info(f"[{device_folder}] ✅ Transcription complete for hour {hour}, chunk {chunk_index}")
                else:
                    logger.warning(f"[{device_folder}] ⚠️ Transcription failed for {hour}/chunk_10min_{chunk_index}.mp3")
                logger.info("=" * 80)
                
            except Exception as e:
                logger.error(f"[{device_folder}] MP3 worker error: {e}")
            finally:
                work_queue.task_done()
    
    def run(self):
        """Main event loop - enqueue files for worker threads (dual pipeline)"""
        logger.info("=" * 80)
        logger.info("Starting inotify event loop (dual pipeline)")
        logger.info("Zero CPU when idle - event-driven processing")
        logger.info("Pipeline 1: MP4 → MP3 (audio extraction)")
        logger.info("Pipeline 2: MP3 → JSON (transcription)")
        logger.info("=" * 80)
        
        try:
            for event in self.inotify.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                
                # Only process files moved into watched directories (atomic writes)
                if 'IN_MOVED_TO' not in type_names:
                    continue
                
                # Pipeline 1: MP4 chunk created → Extract audio
                if filename.endswith('.mp4') and 'chunk_10min_' in filename:
                    device_folder = self.segments_path_to_device.get(path)
                    if device_folder:
                        logger.info(f"[{device_folder}] 🎬 New MP4 detected: {filename}")
                        try:
                            work_queue = self.mp4_queues[device_folder]
                            work_queue.put_nowait((path, filename))
                        except queue.Full:
                            logger.error(f"[{device_folder}] 🚨 MP4 queue FULL, dropping: {filename}")
                
                # Pipeline 2: MP3 chunk created → Transcribe
                elif filename.endswith('.mp3') and 'chunk_10min_' in filename:
                    device_folder = self.audio_path_to_device.get(path)
                    if device_folder:
                        logger.info(f"[{device_folder}] 🎵 New MP3 detected: {filename}")
                        try:
                            work_queue = self.mp3_queues[device_folder]
                            work_queue.put_nowait((path, filename))
                        except queue.Full:
                            logger.error(f"[{device_folder}] 🚨 MP3 queue FULL, dropping: {filename}")
        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            # Clean up inotify watches
            for path in list(self.segments_path_to_device.keys()) + list(self.audio_path_to_device.keys()):
                try:
                    self.inotify.remove_watch(path)
                except:
                    pass

def main():
    # Clean log file first
    cleanup_logs_on_startup()
    
    # Kill any existing transcript_accumulator instances before starting
    from shared.src.lib.utils.system_utils import kill_existing_script_instances
    import time
    
    killed = kill_existing_script_instances('transcript_accumulator.py')
    if killed:
        print(f"[@transcript_accumulator] Killed existing instances: {killed}")
        time.sleep(1)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()],
        force=True
    )
    
    logger.info("=" * 80)
    logger.info("Starting inotify-based Transcript Accumulator (Dual Pipeline)")
    logger.info("=" * 80)
    logger.info("Architecture: Event-driven (zero CPU when idle)")
    logger.info("Pipeline 1: MP4 → MP3 (audio extraction, ~3s per chunk)")
    logger.info("Pipeline 2: MP3 → JSON (transcription, ~2min per chunk)")
    logger.info("Perfect alignment: chunk_10min_X.mp4 + chunk_10min_X.mp3 + chunk_10min_X.json")
    logger.info("=" * 80)
    
    try:
        # Get base directories and resolve paths
        base_dirs = get_capture_base_directories()
        logger.info(f"Found {len(base_dirs)} capture base directories")
        
        # Build monitored devices list (exclude host)
        monitored_devices = []
        for base_dir in base_dirs:
            device_folder = os.path.basename(base_dir)
            
            device_info = get_device_info_from_capture_folder(device_folder)
            device_id = device_info.get('device_id', device_folder)
            is_host = (device_id == 'host')
            
            if is_host:
                logger.info(f"[{device_folder}] ⊗ Skipping (host has no audio)")
                continue
            
            # Get segments path (where MP4 chunks are stored - ALWAYS COLD)
            segments_base = get_cold_segments_path(device_folder)
            
            # Get audio path (ALWAYS cold storage)
            audio_base = get_audio_path(device_folder)
            
            storage_type = "HOT (RAM)" if '/hot/' in segments_base else "COLD (SD)"
            logger.info(f"[{device_folder}] ✓ Monitoring [{storage_type}]")
            logger.info(f"  Segments: {segments_base}")
            logger.info(f"  Audio: {audio_base}")
            
            monitored_devices.append({
                'device_folder': device_folder,
                'segments_base': segments_base,
                'audio_base': audio_base
            })
        
        if not monitored_devices:
            logger.error("No devices to monitor!")
            return
        
        logger.info(f"Monitoring {len(monitored_devices)} devices (excluding host)")
        logger.info("Whisper model will be loaded on first transcription (global singleton)")
        
        # Start monitoring (blocks forever, zero CPU when idle!)
        monitor = InotifyTranscriptMonitor(monitored_devices)
        monitor.run()
        
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise

if __name__ == '__main__':
    main()
