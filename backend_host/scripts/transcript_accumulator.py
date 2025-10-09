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

# CRITICAL: Limit CPU threads BEFORE importing PyTorch/Whisper
# PyTorch/NumPy/OpenBLAS create 40+ threads by default, killing performance
import os
os.environ['OMP_NUM_THREADS'] = '2'          # OpenMP
os.environ['MKL_NUM_THREADS'] = '2'          # Intel MKL
os.environ['OPENBLAS_NUM_THREADS'] = '2'     # OpenBLAS
os.environ['NUMEXPR_NUM_THREADS'] = '2'      # NumExpr
os.environ['VECLIB_MAXIMUM_THREADS'] = '2'   # macOS Accelerate
os.environ['TORCH_NUM_THREADS'] = '2'        # PyTorch (was 2, now 4 for better Whisper performance)

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

def extract_audio_from_mp4(mp4_path: str, mp3_path: str, capture_folder: str, hour: int, chunk_index: int):
    """
    Extract audio from MP4 chunk using FFmpeg
    
    Args:
        mp4_path: Path to MP4 file (chunk_10min_X.mp4)
        mp3_path: Output path for MP3 file (chunk_10min_X.mp3)
        capture_folder: Device identifier
        hour: Hour (0-23)
        chunk_index: Chunk within hour (0-5)
    
    Returns:
        True if extraction succeeded
        False if extraction failed (error)
        None if no audio stream (skip)
    """
    mp3_tmp_path = None
    try:
        # Pre-check: Does MP4 have audio stream?
        if not has_audio_stream(mp4_path):
            logger.info(f"[{capture_folder}] ⏭️  Skipped: {hour}/chunk_10min_{chunk_index}.mp4 (no audio stream)")
            return None
        
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
            '-ar', '16000',      # 16kHz (Whisper's native sample rate - no resampling needed)
            '-ac', '1',          # Mono (Whisper only uses 1 channel, saves 50% space)
            '-b:a', '24k',       # Low bitrate for speech (still clear, 6-8x smaller files)
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

def check_mp3_has_audio(mp3_path: str, capture_folder: str, sample_duration: float = 5.0) -> tuple[bool, float]:
    """
    Check if MP3 has actual audio content (not silence) using ffmpeg volumedetect
    
    Uses 5s sample (vs 0.1s in capture_monitor) for better silence detection.
    Reuses same logic as detector.py analyze_audio() but for MP3 files.
    
    Args:
        mp3_path: Path to MP3 file
        capture_folder: Device identifier (for logging)
        sample_duration: Duration to sample in seconds (default 5.0s)
    
    Returns:
        (has_audio: bool, mean_volume_db: float)
    """
    try:
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
            '-i', mp3_path,
            '-t', str(sample_duration),  # Sample 5 seconds
            '-af', 'volumedetect',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stderr
        mean_volume = -100.0
        
        for line in output.split('\n'):
            if 'mean_volume:' in line:
                try:
                    mean_volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                    break
                except:
                    pass
        
        # Consider silent if volume < -50dB (same threshold as detector.py)
        has_audio = mean_volume > -50.0
        
        return has_audio, mean_volume
        
    except Exception as e:
        logger.warning(f"[{capture_folder}] Failed to check MP3 audio level: {e}")
        # On error, assume has audio (safer to transcribe than skip)
        return True, 0.0

def transcribe_mp3_chunk(mp3_path: str, capture_folder: str, hour: int, chunk_index: int) -> dict:
    """
    Transcribe 10-minute MP3 in full (restored from per-minute processing)
    """
    try:
        has_audio, mean_volume_db = check_mp3_has_audio(mp3_path, capture_folder, sample_duration=5.0)
        
        if not has_audio:
            logger.info(f"[{capture_folder}] ⏭️  SKIPPED: chunk_10min_{chunk_index}.mp3 (silent, {mean_volume_db:.1f}dB)")
            return {
                'capture_folder': capture_folder,
                'hour': hour,
                'chunk_index': chunk_index,
                'chunk_duration_minutes': CHUNK_DURATION_MINUTES,
                'language': 'unknown',
                'transcript': '',
                'confidence': 0.0,
                'transcription_time_seconds': 0.0,
                'timestamp': datetime.now().isoformat(),
                'mp3_file': os.path.basename(mp3_path),
                'segments': [],
                'skipped_reason': 'silent',
                'mean_volume_db': mean_volume_db
            }
        
        import psutil
        from shared.src.lib.utils.audio_transcription_utils import transcribe_audio
        
        process = psutil.Process()
        process.cpu_percent(interval=None)

        logger.info(f"[{capture_folder}] 🎬 START: chunk_10min_{chunk_index}.mp3 (full 10min)")

        # Step 1: Extract 5s sample for language detection
        sample_tmp = f'/tmp/sample_{capture_folder}.mp3'
        extract_start = time.time()
        cmd = ['ffmpeg', '-i', mp3_path, '-ss', '0', '-t', '5', '-y', sample_tmp]
        subprocess.run(cmd, capture_output=True, timeout=5)
        extract_time = time.time() - extract_start
        logger.info(f"[{capture_folder}] ✓ Extracted 5s sample in {extract_time:.1f}s")

        # Step 2: Detect language on sample
        sample_start = time.time()
        sample_result = transcribe_audio(sample_tmp, model_name='tiny', skip_silence_check=True, device_id=capture_folder)
        sample_time = time.time() - sample_start
        detected_language = sample_result.get('language_code', None)  # Use code for Whisper param
        logger.info(f"[{capture_folder}] ✓ Language detection: {detected_language or 'auto'} in {sample_time:.1f}s")

        # Cleanup sample
        try:
            os.remove(sample_tmp)
        except:
            pass

        # Step 3: Full transcription with detected language
        total_start = time.time()
        if detected_language:
            result = transcribe_audio(mp3_path, model_name='tiny', skip_silence_check=False, device_id=capture_folder, language=detected_language)
        else:
            result = transcribe_audio(mp3_path, model_name='tiny', skip_silence_check=False, device_id=capture_folder)
        elapsed = time.time() - total_start
        cpu_final = process.cpu_percent(interval=None)

        transcript = result.get('transcript', '').strip()
        segments = result.get('segments', [])
        language = result.get('language', 'unknown')
        confidence = result.get('confidence', 0.0)

        logger.info(f"[{capture_folder}] ✅ COMPLETED in {elapsed:.1f}s | Lang: {language} | {len(transcript)} chars, {len(segments)} segments | CPU: {cpu_final:.1f}%")
        
        return {
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
            'segments': segments
        }
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Error: {e}")
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
    """Single Whisper worker with round-robin device processing"""
    
    def __init__(self, monitored_devices):
        self.monitored_devices = monitored_devices
        self.inotify = inotify.adapters.Inotify()
        
        self.segments_path_to_device = {}
        self.audio_path_to_device = {}
        
        self.mp4_queues = {}
        self.mp4_workers = {}
        self.mp4_backlog = {}
        
        self.active_queues = {}
        self.history_queues = {}
        
        self.whisper_worker = None
        self.worker_running = False
        
        self._setup_watches()
        self._start_mp4_workers()
        
        all_pending = self._scan_last_24h()
        self._initialize_queues(all_pending)
        
        self._start_whisper_worker()
    
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
    
    def _start_mp4_workers(self):
        """Start MP4→MP3 extraction workers"""
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            self.mp4_queues[device_folder] = LifoQueue(maxsize=100)
            
            mp4_worker = threading.Thread(
                target=self._mp4_worker,
                args=(device_folder,),
                daemon=True,
                name=f"mp4-{device_folder}"
            )
            mp4_worker.start()
            self.mp4_workers[device_folder] = mp4_worker
    
    def _scan_last_24h(self):
        """Scan last 24h for MP3s without transcripts"""
        from pathlib import Path
        
        logger.info("Scanning last 24h for unprocessed MP3s")
        now = time.time()
        cutoff = now - (24 * 3600)
        
        all_pending = {}
        
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            audio_base = device_info['audio_base']
            transcript_base = get_transcript_path(device_folder)
            
            pending = []
            
            for hour in range(24):
                audio_dir = os.path.join(audio_base, str(hour))
                transcript_dir = os.path.join(transcript_base, str(hour))
                
                if not os.path.exists(audio_dir):
                    continue
                
                for mp3_file in Path(audio_dir).glob('chunk_10min_*.mp3'):
                    mtime = mp3_file.stat().st_mtime
                    
                    if mtime < cutoff:
                        continue
                    
                    chunk_index = int(mp3_file.stem.split('_')[-1])
                    transcript_file = Path(transcript_dir) / f'chunk_10min_{chunk_index}.json'
                    
                    if not transcript_file.exists() or transcript_file.stat().st_mtime < cutoff:
                        pending.append((mtime, hour, mp3_file.name))
            
            pending.sort(reverse=True)
            all_pending[device_folder] = pending
            
            if pending:
                logger.info(f"[{device_folder}] {len(pending)} MP3s need transcription")
        
        return all_pending
    
    def _initialize_queues(self, all_pending):
        """Put 3 newest in active queue, rest in history"""
        for device_folder, pending in all_pending.items():
            self.active_queues[device_folder] = queue.Queue(maxsize=3)
            self.history_queues[device_folder] = []
            
            for item in pending[:3]:
                try:
                    self.active_queues[device_folder].put_nowait(item)
                except queue.Full:
                    break
            
            self.history_queues[device_folder] = pending[3:]
            logger.info(f"[{device_folder}] Active: {self.active_queues[device_folder].qsize()}, History: {len(self.history_queues[device_folder])}")
    
    def _start_whisper_worker(self):
        """Start single shared Whisper worker"""
        self.worker_running = True
        self.whisper_worker = threading.Thread(
            target=self._round_robin_worker,
            daemon=True,
            name="whisper-worker"
        )
        self.whisper_worker.start()
        logger.info("Single Whisper worker started (round-robin, 30s delay, low priority)")
    
    def _round_robin_worker(self):
        """Process MP3s round-robin across devices"""
        device_index = 0
        
        while self.worker_running:
            if not self.monitored_devices:
                time.sleep(1)
                continue
            
            device_info = self.monitored_devices[device_index]
            device_folder = device_info['device_folder']
            audio_base = device_info['audio_base']
            work_queue = self.active_queues[device_folder]
            
            try:
                mtime, hour, filename = work_queue.get_nowait()
                
                logger.info(f"[{device_folder}] Processing: {filename}")
                
                mp3_path = os.path.join(audio_base, str(hour), filename)
                chunk_index = int(filename.split('_')[-1].replace('.mp3', ''))
                
                start = time.time()
                transcript_data = transcribe_mp3_chunk(mp3_path, device_folder, hour, chunk_index)
                
                if transcript_data:
                    save_transcript_chunk(device_folder, hour, chunk_index, transcript_data, has_mp3=True)
                    elapsed = time.time() - start
                    
                    # Summary already logged in transcribe_mp3_chunk, just log save confirmation
                    if transcript_data.get('skipped_reason') == 'silent':
                        logger.info(f"[{device_folder}] 💾 Saved silent chunk metadata (total: {elapsed:.1f}s)")
                    else:
                        logger.info(f"[{device_folder}] 💾 Saved transcript JSON (total: {elapsed:.1f}s)")
                
                work_queue.task_done()
                
                if work_queue.empty():
                    self._refill_from_history(device_folder)
                
                # Show queue status for all devices
                self._log_queue_status()
                
                time.sleep(30)
                
            except queue.Empty:
                pass
            
            device_index = (device_index + 1) % len(self.monitored_devices)
            time.sleep(0.5)
    
    def _refill_from_history(self, device_folder):
        """Refill active queue from history"""
        history = self.history_queues[device_folder]
        
        if not history:
            logger.info(f"[{device_folder}] All caught up")
            return
        
        refill = history[:3]
        self.history_queues[device_folder] = history[3:]
        
        work_queue = self.active_queues[device_folder]
        for item in refill:
            try:
                work_queue.put_nowait(item)
            except queue.Full:
                self.history_queues[device_folder].insert(0, item)
                break
        
        logger.info(f"[{device_folder}] Refilled ({len(self.history_queues[device_folder])} remaining)")
    
    def _log_queue_status(self):
        """Log queue status for all devices"""
        logger.info("=" * 80)
        logger.info("📊 QUEUE STATUS")
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            work_queue = self.active_queues[device_folder]
            history = self.history_queues[device_folder]
            
            # Get active queue items (peek without removing)
            active_items = []
            try:
                temp_list = []
                while not work_queue.empty():
                    item = work_queue.get_nowait()
                    temp_list.append(item)
                
                # Put items back
                for item in temp_list:
                    work_queue.put_nowait(item)
                    mtime, hour, filename = item
                    chunk_index = int(filename.split('_')[-1].replace('.mp3', ''))
                    minute = chunk_index * 10
                    active_items.append(f"{hour:02d}h{minute:02d}")
            except:
                pass
            
            # Format queue display
            active_str = ', '.join(active_items) if active_items else 'empty'
            history_count = len(history)
            
            if active_items or history_count > 0:
                logger.info(f"  [{device_folder}] Active: [{active_str}] | History: {history_count}")
            else:
                logger.info(f"  [{device_folder}] ✓ All caught up")
        
        logger.info("=" * 80)
    
    def _process_mp4_backlog_batch(self, device_folder):
        """Process MP4 backlog batch"""
        backlog = self.mp4_backlog.get(device_folder, [])
        if not backlog:
            return 0
        
        batch = backlog[:3]
        self.mp4_backlog[device_folder] = backlog[3:]
        
        added = 0
        for mtime, hour_dir, filename in batch:
            try:
                self.mp4_queues[device_folder].put_nowait((hour_dir, filename))
                added += 1
            except queue.Full:
                self.mp4_backlog[device_folder].insert(0, (mtime, hour_dir, filename))
                break
        
        if added > 0:
            logger.info(f"[{device_folder}] Refilled {added} MP4s ({len(self.mp4_backlog[device_folder])} remaining)")
        
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
                result = extract_audio_from_mp4(mp4_path, mp3_path, device_folder, hour, chunk_index)
                if result is True:
                    logger.info(f"[{device_folder}] ✅ Audio extraction complete for hour {hour}, chunk {chunk_index}")
                elif result is False:
                    logger.warning(f"[{device_folder}] ⚠️ Audio extraction failed for {hour}/chunk_10min_{chunk_index}.mp4")
                # elif result is None: already logged "Skipped" in extract_audio_from_mp4
                logger.info("=" * 80)
                
            except Exception as e:
                logger.error(f"[{device_folder}] MP4 worker error: {e}")
            finally:
                work_queue.task_done()
    
    def run(self):
        """Main event loop - enqueue files for worker threads (dual pipeline)"""
        logger.info("=" * 80)
        logger.info("Starting inotify event loop (dual pipeline)")
        logger.info("Zero CPU when idle - event-driven processing")
        logger.info("Pipeline 1: MP4 → MP3 (audio extraction)")
        logger.info("Pipeline 2: MP3 → JSON (transcription, ~2min per chunk)")
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
                        logger.info(f"[{device_folder}] New MP3: {filename}")
                        hour = int(os.path.basename(path))
                        mtime = os.path.getmtime(os.path.join(path, filename))
                        try:
                            self.active_queues[device_folder].put_nowait((mtime, hour, filename))
                        except queue.Full:
                            self.history_queues[device_folder].insert(0, (mtime, hour, filename))
                            logger.info(f"[{device_folder}] Queue full, added to history")
        
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
    logger.info("Priority: Normal (no nice) - faster transcription")
    logger.info("Threads: 4 per library (was 2) - better Whisper performance")
    logger.info("Pipeline 1: MP4 → MP3 (audio extraction, ~3s)")
    logger.info("Pipeline 2: MP3 → JSON (10× 60s segments, 5s rest between segments, 10s delay between chunks)")
    logger.info("CPU: 10× small bursts with 5s rest - gives CPU to other processes")
    logger.info("=" * 80)
    
    try:
        # Get base directories and resolve paths
        base_dirs = get_capture_base_directories()
        logger.info(f"Found {len(base_dirs)} capture base directories from active_captures.conf")
        
        # Build monitored devices list (exclude host - host has no audio)
        monitored_devices = []
        skipped_count = 0
        
        for base_dir in base_dirs:
            device_folder = os.path.basename(base_dir)
            
            # Map capture folder to device_id via .env
            device_info = get_device_info_from_capture_folder(device_folder)
            device_id = device_info.get('device_id', device_folder)
            is_host = (device_id == 'host')
            
            # Log device mapping
            logger.info(f"  [{device_folder}] device_id={device_id}, is_host={is_host}")
            
            if is_host:
                logger.info(f"  ⊗ Skipping: {device_folder} (host has no audio)")
                skipped_count += 1
                continue
            
            # Get segments path (where MP4 chunks are stored)
            segments_base = get_cold_segments_path(device_folder)
            
            # Get audio path (ALWAYS cold storage)
            audio_base = get_audio_path(device_folder)
            
            logger.info(f"  ✓ Monitoring: {device_folder}")
            logger.info(f"    Segments: {segments_base}")
            logger.info(f"    Audio: {audio_base}")
            
            monitored_devices.append({
                'device_folder': device_folder,
                'segments_base': segments_base,
                'audio_base': audio_base
            })
        
        if not monitored_devices:
            logger.error("No devices to monitor!")
            return
        
        logger.info(f"Monitoring {len(monitored_devices)} devices ({skipped_count} skipped)")
        logger.info("Whisper model will be loaded on first transcription (global singleton)")
        
        # Start monitoring (blocks forever, zero CPU when idle!)
        monitor = InotifyTranscriptMonitor(monitored_devices)
        monitor.run()
        
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise

if __name__ == '__main__':
    main()
