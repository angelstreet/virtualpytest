#!/usr/bin/env python3
"""
inotify-based Transcript Accumulator - Dual Pipeline (MP4→MP3→JSON)
Event-driven processing: Zero CPU when idle, immediate response to new files

Pipeline 1: MP4 → MP3 (audio extraction)
  - Watches /video/{hour}/ directories for chunk_10min_X.mp4
  - Extracts audio → chunk_10min_X.mp3
  
Pipeline 2: MP3 → JSON (transcription + progressive save)
  - Watches /audio/{hour}/ directories for chunk_10min_X.mp3
  - Transcribes 10-minute MP3 once (Whisper auto-segments)
  - Groups segments by minute, saves progressively to chunk_10min_X.json

Progressive processing: Load once, transcribe once, save by minute
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
from pathlib import Path

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
    get_cold_segments_path,
    get_metadata_path,
    get_segments_path,
    get_captures_path
)

from shared.src.lib.utils.audio_transcription_utils import (
    transcribe_audio,
    clean_transcript_text,
    correct_spelling,
    ENABLE_SPELLCHECK
)

logger = logging.getLogger(__name__)

# Configuration
CHUNK_DURATION_MINUTES = 10
SEGMENT_DURATION_MINUTES = 1

_chunk_languages = {}

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

def get_chunk_language(capture_folder: str, hour: int, chunk_index: int):
    global _chunk_languages
    chunk_key = f"{capture_folder}_{hour}_{chunk_index}"
    return _chunk_languages.get(chunk_key)

def set_chunk_language(capture_folder: str, hour: int, chunk_index: int, language: str):
    global _chunk_languages
    chunk_key = f"{capture_folder}_{hour}_{chunk_index}"
    _chunk_languages[chunk_key] = language

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

def transcribe_mp3_chunk_progressive(mp3_path: str, capture_folder: str, hour: int, chunk_index: int) -> list:
    """
    Transcribe 10-minute MP3 once, return results grouped by minute for progressive merging
    
    Returns:
        List of minute_data dicts (one per minute 0-9)
    """
    try:
        import psutil
        
        process = psutil.Process()
        cpu_before = process.cpu_percent(interval=None)  # Initialize CPU monitoring
        
        GREEN = '\033[92m'
        RESET = '\033[0m'
        logger.info(f"{GREEN}[WHISPER:{capture_folder}] 🎬 Processing: {mp3_path} (transcribe once, save progressively){RESET}")

        has_audio, mean_volume_db = check_mp3_has_audio(mp3_path, capture_folder, sample_duration=5.0)
        
        if not has_audio:
            logger.info(f"[{capture_folder}] ⏭️  SKIPPED: chunk silent ({mean_volume_db:.1f}dB)")
            return []
        
        # Log CPU before Whisper execution
        time.sleep(0.1)  # Small delay to get accurate baseline
        cpu_before = process.cpu_percent(interval=None)
        
        total_start = time.time()
        result = transcribe_audio(mp3_path, model_name='tiny', skip_silence_check=True, device_id=capture_folder)
        elapsed = time.time() - total_start
        cpu_after = process.cpu_percent(interval=None)
        
        segments = result.get('segments', [])
        language = result.get('language', 'unknown')
        language_code = result.get('language_code', 'unknown')
        confidence = result.get('confidence', 0.0)
        audio_duration = result.get('duration', 0.0)
        
        # Calculate real-time factor (RTF): processing_time / audio_duration
        # RTF < 1.0 means faster than real-time (good!)
        # RTF = 1.0 means processing at real-time speed
        # RTF > 1.0 means slower than real-time (problematic for live transcription)
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RESET = '\033[0m'
        
        # Get text preview from first segment (if any)
        text_preview = ""
        if segments:
            first_text = segments[0].get('text', '').strip()
            text_preview = f' | Text: "{first_text[:60]}..."' if first_text else ""
        
        # Duration 0.0s = Whisper detected silence/no speech (normal for silent sources)
        duration_note = " (silent audio)" if audio_duration == 0 else ""
        
        logger.info(f"{GREEN}[WHISPER:{capture_folder}] ✅ TRANSCRIPTION COMPLETE:{RESET}")
        logger.info(f"{GREEN}  • Processing time: {elapsed:.1f}s{RESET}")
        logger.info(f"{GREEN}  • Audio duration: {audio_duration:.1f}s{duration_note}{RESET}")
        logger.info(f"{GREEN}  • Language: {language} ({language_code}), Confidence: {confidence:.2f}{RESET}")
        logger.info(f"{GREEN}  • Segments: {len(segments)}, CPU: {cpu_before:.1f}%→{cpu_after:.1f}%{text_preview}{RESET}")
        
        minute_groups = {}
        for i in range(10):
            minute_groups[i] = []
        
        for segment in segments:
            start_time = segment.get('start', 0)
            minute_offset = int(start_time // 60)
            if minute_offset < 10:
                minute_groups[minute_offset].append(segment)
        
        minute_results = []
        for minute_offset in range(10):
            minute_segments = minute_groups[minute_offset]
            
            if not minute_segments:
                continue
            
            minute_transcript = ' '.join([s.get('text', '').strip() for s in minute_segments])
            minute_transcript = clean_transcript_text(minute_transcript)
            if ENABLE_SPELLCHECK:
                minute_transcript = correct_spelling(minute_transcript, result.get('language_code'))
            
            GREEN = '\033[92m'
            RESET = '\033[0m'
            logger.info(f"{GREEN}[{capture_folder}] 📝 Minute {minute_offset}: {len(minute_segments)} segments, {len(minute_transcript)} chars - \"{minute_transcript[:50]}...\"{RESET}")
            
            minute_results.append({
                'minute_offset': minute_offset,
                'language': language,
                'transcript': minute_transcript,
                'segments': minute_segments
            })
        
        return minute_results
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Error: {e}")
        return []

def merge_minute_to_chunk(capture_folder: str, hour: int, chunk_index: int, minute_data: dict, has_mp3: bool = True):
    """
    Progressively append segments to 10-minute chunk (same format as before)
    
    Args:
        capture_folder: Device folder name (e.g., 'capture1')
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
        minute_data: Minute transcription data with segments to append
        has_mp3: Whether corresponding MP3 exists
    """
    import fcntl
    
    transcript_base = get_transcript_path(capture_folder)
    transcript_dir = os.path.join(transcript_base, str(hour))
    os.makedirs(transcript_dir, exist_ok=True)
    
    chunk_path = os.path.join(transcript_dir, f'chunk_10min_{chunk_index}.json')
    
    lock_path = chunk_path + '.lock'
    with open(lock_path, 'w') as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        
        try:
            if os.path.exists(chunk_path):
                with open(chunk_path, 'r') as f:
                    chunk_data = json.load(f)
                if 'segments' not in chunk_data:
                    chunk_data['segments'] = []
                if 'minute_statuses' not in chunk_data:
                    chunk_data['minute_statuses'] = {}
            else:
                chunk_data = {
                    'capture_folder': capture_folder,
                    'hour': hour,
                    'chunk_index': chunk_index,
                    'chunk_duration_minutes': CHUNK_DURATION_MINUTES,
                    'language': None,  # Will be set when first segment is added
                    'transcript': '',
                    'confidence': 0.0,
                    'transcription_time_seconds': 0.0,
                    'timestamp': datetime.now().isoformat(),
                    'mp3_file': f'chunk_10min_{chunk_index}.mp3' if has_mp3 else None,
                    'segments': [],
                    'minute_statuses': {}  # Track processing status per minute
                }
            
            minute_segments = minute_data.get('segments', [])
            minute_offset = minute_data.get('minute_offset')
            
            # Mark minute as processed (even if no segments - could be silent or skipped)
            processed_day = datetime.now().strftime('%Y-%m-%d')
            has_audio = len(minute_segments) > 0
            skip_reason = minute_data.get('skip_reason')
            
            chunk_data['minute_statuses'][str(minute_offset)] = {
                'processed': True,
                'processed_day': processed_day,
                'has_audio': has_audio,
                'skip_reason': skip_reason
            }
            
            existing_starts = {s.get('start') for s in chunk_data['segments']}
            new_segments = [s for s in minute_segments if s.get('start') not in existing_starts]
            
            if new_segments:
                chunk_data['segments'].extend(new_segments)
                chunk_data['segments'].sort(key=lambda x: x.get('start', 0))
                
                full_transcript = ' '.join([s.get('text', '').strip() for s in chunk_data['segments']])
                chunk_data['transcript'] = full_transcript
                
                # Only update language if we have a valid detected language (not 'unknown')
                detected_lang = minute_data.get('language')
                if detected_lang and detected_lang != 'unknown':
                    chunk_data['language'] = detected_lang
                elif not chunk_data.get('language'):
                    chunk_data['language'] = None  # Keep as None if still unknown
                
                if chunk_data['segments']:
                    confidences = [s.get('confidence', 0) for s in chunk_data['segments'] if 'confidence' in s]
                    chunk_data['confidence'] = sum(confidences) / len(confidences) if confidences else 0.0
                
                chunk_data['timestamp'] = datetime.now().isoformat()
                
                # Calculate total audio duration from segments
                if chunk_data['segments']:
                    last_segment = max(chunk_data['segments'], key=lambda s: s.get('end', 0))
                    chunk_duration_seconds = last_segment.get('end', 0)
                    chunk_data['chunk_duration_seconds'] = chunk_duration_seconds
                else:
                    chunk_data['chunk_duration_seconds'] = 0.0
            
            with open(chunk_path + '.tmp', 'w') as f:
                json.dump(chunk_data, f, indent=2)
            os.rename(chunk_path + '.tmp', chunk_path)
            
            # Log ONLY if actual audio data was merged (not status updates)
            if new_segments:
                # Real audio data merged - show detailed log
                GREEN = '\033[92m'
                RESET = '\033[0m'
                logger.info(f"{GREEN}[{capture_folder}] 💾 Merged audio data → {hour}h/chunk_{chunk_index}: {len(chunk_data['segments'])} total segments, {len(chunk_data['transcript'])} chars{RESET}")
                logger.info(f"{GREEN}[{capture_folder}] 📄 Chunk structure: language={chunk_data.get('language')}, confidence={chunk_data.get('confidence', 0):.2f}, duration={chunk_data.get('chunk_duration_seconds', 0):.1f}s, mp3_file={chunk_data.get('mp3_file')}{RESET}")
                # Show sample from NEWLY ADDED segments
                sample_seg = new_segments[0]
                seg_duration = sample_seg.get('duration', sample_seg.get('end', 0) - sample_seg.get('start', 0))
                logger.info(f"{GREEN}[{capture_folder}] 📋 NEW segment sample (minute {minute_offset}): start={sample_seg.get('start', 0):.2f}s, duration={seg_duration:.2f}s, confidence={sample_seg.get('confidence', 0):.2f}, text=\"{sample_seg.get('text', '')[:80]}...\"{RESET}")
            else:
                # No audio merged - just status tracking (silent minute)
                logger.debug(f"[{capture_folder}] ✓ Updated chunk {hour}h/chunk_{chunk_index} status: minute {minute_offset} processed (skip_reason: {skip_reason or 'no_audio'})")
    
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    
    try:
        os.remove(lock_path)
    except:
        pass
    
    try:
        device_base_path = get_device_base_path(capture_folder)
        from backend_host.scripts.hot_cold_archiver import update_transcript_manifest
        update_transcript_manifest(device_base_path, hour, chunk_index, chunk_path, has_mp3=has_mp3)
    except Exception as e:
        logger.warning(f"Failed to update transcript manifest: {e}")

def should_skip_minute_by_metadata(capture_folder: str, hour: int, minute_in_hour: int) -> tuple[bool, str]:
    """
    Check metadata JSONs for a 1-minute period to determine if transcription should be skipped
    
    Args:
        capture_folder: Device folder (e.g., 'capture1')
        hour: Hour (0-23)
        minute_in_hour: Minute within hour (0-59)
    
    Returns:
        (should_skip: bool, reason: str)
    """
    try:
        metadata_path = get_metadata_path(capture_folder)
        
        # Calculate sequence range for this minute (5 fps = ~300 frames per minute)
        # But we only check sampled frames (every 5th frame = 1fps in metadata)
        # So ~60 frames per minute to check
        
        # Heuristic: Check 10 sample frames across the minute (every 6 seconds)
        has_good_frames = 0
        has_incidents = 0
        has_no_audio = 0
        checked = 0
        
        # We need to map hour+minute to sequence numbers
        # Sequences are continuous, but we don't know the start sequence for this device
        # Better approach: scan metadata dir for JSONs with matching timestamps
        
        # Get all JSONs from metadata directory
        if not os.path.exists(metadata_path):
            return False, None
        
        target_hour = hour
        target_minute = minute_in_hour
        
        # Sample up to 10 files from this minute
        sample_count = 0
        max_samples = 10
        
        try:
            # Get all capture JSONs sorted by name (sequence order)
            json_files = sorted([f for f in os.listdir(metadata_path) if f.startswith('capture_') and f.endswith('.json')])
            
            for json_file in json_files:
                if sample_count >= max_samples:
                    break
                
                json_path = os.path.join(metadata_path, json_file)
                
                try:
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                    
                    # Check timestamp
                    timestamp = data.get('timestamp')
                    if not timestamp:
                        continue
                    
                    # Parse timestamp to get hour and minute
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if dt.hour != target_hour or dt.minute != target_minute:
                        continue
                    
                    # This frame is in our target minute
                    checked += 1
                    sample_count += 1
                    
                    # Check for incidents
                    freeze = data.get('freeze', False)
                    blackscreen = data.get('blackscreen', False)
                    has_audio = data.get('audio', True)
                    
                    if freeze or blackscreen:
                        has_incidents += 1
                    
                    if not has_audio:
                        has_no_audio += 1
                    
                    if not freeze and not blackscreen and has_audio:
                        has_good_frames += 1
                
                except Exception as e:
                    continue
        
        except Exception as e:
            logger.debug(f"[{capture_folder}] Metadata check failed: {e}")
            return False, None
        
        if checked == 0:
            # No metadata found for this minute - don't skip (might be legitimate audio)
            return False, None
        
        # Decision logic:
        # - If ALL checked frames have incidents or no audio → skip
        # - If MAJORITY (>80%) have issues → skip
        # - Otherwise → process
        
        incident_ratio = (has_incidents + has_no_audio) / checked if checked > 0 else 0
        
        if incident_ratio >= 0.8:
            # Skip this minute
            if has_no_audio >= checked * 0.8:
                return True, "no_audio"
            elif has_incidents >= checked * 0.8:
                return True, "incidents"
            else:
                return True, "mixed_issues"
        
        return False, None
        
    except Exception as e:
        logger.warning(f"[{capture_folder}] Error checking metadata: {e}")
        return False, None


def check_minute_already_processed(capture_folder: str, hour: int, chunk_index: int, minute_offset: int) -> bool:
    """Check if minute was already processed today"""
    try:
        transcript_base = get_transcript_path(capture_folder)
        chunk_path = os.path.join(transcript_base, str(hour), f'chunk_10min_{chunk_index}.json')
        
        if not os.path.exists(chunk_path):
            return False
        
        with open(chunk_path, 'r') as f:
            chunk_data = json.load(f)
        
        minute_statuses = chunk_data.get('minute_statuses', {})
        minute_status = minute_statuses.get(str(minute_offset))
        
        if not minute_status:
            return False
        
        processed_day = minute_status.get('processed_day')
        today = datetime.now().strftime('%Y-%m-%d')
        
        return processed_day == today
        
    except Exception as e:
        return False

class InotifyTranscriptMonitor:
    """Simple MP3 transcription monitor"""
    
    def __init__(self, monitored_devices):
        self.monitored_devices = monitored_devices
        self.inotify = inotify.adapters.Inotify()
        self.audio_path_to_device = {}
        self.mp3_queue = queue.Queue()
        self.audio_workers = {}
        self.incident_manager = None
        
        self._setup_watches()
        self._start_audio_workers()
        self._scan_existing_mp3s()
        self._start_transcription_worker()
    
    def _setup_watches(self):
        """Setup inotify watches for 1min MP3 files in temp/"""
        logger.info("Setting up 1min MP3 inotify watches...")
        
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            audio_base = device_info['audio_base']
            
            # Watch temp directory for 1min MP3 files (instant transcription)
            audio_temp_dir = os.path.join(audio_base, 'temp')
            os.makedirs(audio_temp_dir, exist_ok=True)
            self.inotify.add_watch(audio_temp_dir)
            self.audio_path_to_device[audio_temp_dir] = device_folder
            
            logger.info(f"[{device_folder}] ✓ Watching {audio_temp_dir}")
        
        logger.info(f"Total: {len(self.audio_path_to_device)} temp dir watches")
    
    def _scan_existing_mp3s(self):
        """Scan existing 10min MP3s and queue missing transcripts"""
        logger.info("Scanning existing 10min MP3s...")
        
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            audio_base = device_info['audio_base']
            transcript_base = get_transcript_path(device_folder)
            
            found = 0
            for hour in range(24):
                audio_dir = os.path.join(audio_base, str(hour))
                if not os.path.exists(audio_dir):
                    continue
                
                for mp3_file in os.listdir(audio_dir):
                    if mp3_file.startswith('chunk_10min_') and mp3_file.endswith('.mp3'):
                        chunk_index = int(mp3_file.replace('chunk_10min_', '').replace('.mp3', ''))
                        transcript_path = os.path.join(transcript_base, str(hour), f'chunk_10min_{chunk_index}.json')
                        
                        if not os.path.exists(transcript_path):
                            self.mp3_queue.put((device_folder, hour, chunk_index))
                            found += 1
            
            if found > 0:
                logger.info(f"[{device_folder}] Queued {found} MP3s for transcription")
    
    def _start_transcription_worker(self):
        """Start single transcription worker"""
        worker = threading.Thread(target=self._transcription_worker, daemon=True)
        worker.start()
        logger.info("Transcription worker started")
    
    def _transcription_worker(self):
        """Process MP3 transcription queue (1min or 10min)"""
        while True:
            try:
                item = self.mp3_queue.get(timeout=30)
                
                # Handle both 1min (from inotify) and 10min (from scan)
                if len(item) == 3:
                    # 10min scan: (device_folder, hour, chunk_index)
                    device_folder, hour, chunk_index = item
                    mp3_path = None
                    for device_info in self.monitored_devices:
                        if device_info['device_folder'] == device_folder:
                            mp3_path = os.path.join(device_info['audio_base'], str(hour), f'chunk_10min_{chunk_index}.mp3')
                            break
                    
                    if mp3_path and os.path.exists(mp3_path):
                        logger.info(f"[{device_folder}] Transcribing 10min: {hour}/chunk_10min_{chunk_index}.mp3")
                        minute_results = transcribe_mp3_chunk_progressive(mp3_path, device_folder, hour, chunk_index)
                        for minute_data in minute_results:
                            merge_minute_to_chunk(device_folder, hour, chunk_index, minute_data, has_mp3=True)
                
                elif len(item) == 4:
                    # 1min inotify: (device_folder, mp3_path, hour, chunk_index)
                    device_folder, mp3_path, hour, chunk_index = item
                    
                    if os.path.exists(mp3_path):
                        minute_offset = (datetime.fromtimestamp(int(Path(mp3_path).stem.replace('1min_', ''))).minute % 60) % 10
                        logger.info(f"[{device_folder}] Transcribing 1min: {hour}h{minute_offset:02d}min")
                        
                        result = transcribe_audio(mp3_path, model_name='tiny', skip_silence_check=True, device_id=device_folder)
                        segments = result.get('segments', [])
                        
                        if segments:
                            transcript = ' '.join([s.get('text', '').strip() for s in segments])
                            transcript = clean_transcript_text(transcript)
                            if ENABLE_SPELLCHECK:
                                transcript = correct_spelling(transcript, result.get('language_code'))
                            
                            minute_data = {
                                'minute_offset': minute_offset,
                                'language': result.get('language', 'unknown'),
                                'transcript': transcript,
                                'segments': segments
                            }
                            merge_minute_to_chunk(device_folder, hour, chunk_index, minute_data, has_mp3=False)
                
                self.mp3_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                self.mp3_queue.task_done()
    
    
    
    def _start_audio_workers(self):
        """Start audio detection workers (5s interval per device)"""
        logger.info("Starting audio detection workers...")
        
        try:
            from backend_host.scripts.incident_manager import IncidentManager
            # Don't resolve stale incidents - that's capture_monitor's job
            # We only report audio detection results, not manage incident lifecycle
            self.incident_manager = IncidentManager(skip_startup_cleanup=True)
            logger.info("✓ IncidentManager initialized (audio reporting only)")
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize IncidentManager: {e} (audio detection will continue without incident tracking)")
            self.incident_manager = None
        
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            
            try:
                audio_worker = threading.Thread(
                    target=self._audio_detection_worker,
                    args=(device_folder,),
                    daemon=True,
                    name=f"audio-{device_folder}"
                )
                audio_worker.start()
                self.audio_workers[device_folder] = audio_worker
                logger.info(f"✓ [{device_folder}] Started audio detection worker (5s interval)")
            except Exception as e:
                logger.error(f"✗ [{device_folder}] Failed to start audio detection worker: {e}")
    
    def _audio_detection_worker(self, device_folder):
        """Worker thread: Check audio every 5s by scanning segments directory"""
        BLUE = '\033[94m'
        RESET = '\033[0m'
        
        logger.info(f"{BLUE}[AUDIO:{device_folder}] Worker thread started - checking every 5s{RESET}")
        
        # Resolve segments path once (hot/cold aware)
        segments_dir = get_segments_path(device_folder)
        logger.info(f"{BLUE}[AUDIO:{device_folder}] 📂 Watching: {segments_dir}{RESET}")
        
        check_count = 0
        while True:
            check_count += 1
            try:
                # Find latest segment file (same approach as old detector.py)
                if not os.path.exists(segments_dir):
                    if check_count % 12 == 0:
                        logger.info(f"{BLUE}[AUDIO:{device_folder}] ⏸️  Segments directory not found (check #{check_count}): {segments_dir}{RESET}")
                    time.sleep(5)
                    continue
                
                # Scan for latest segment_*.ts or segment_*.mp4 file
                latest_segment = None
                latest_mtime = 0
                
                try:
                    with os.scandir(segments_dir) as it:
                        for entry in it:
                            # Check TS or MP4 segments (not hour folders)
                            if entry.is_file() and entry.name.startswith('segment_') and (entry.name.endswith('.ts') or entry.name.endswith('.mp4')):
                                mtime = entry.stat().st_mtime
                                if mtime > latest_mtime:
                                    latest_segment = entry.path
                                    latest_mtime = mtime
                except Exception as e:
                    if check_count % 12 == 0:
                        logger.error(f"{BLUE}[AUDIO:{device_folder}] ⏸️  Segment scan failed (check #{check_count}): {e}{RESET}")
                    time.sleep(5)
                    continue
                
                if not latest_segment:
                    if check_count % 12 == 0:
                        logger.info(f"{BLUE}[AUDIO:{device_folder}] ⏸️  No segments found in {segments_dir} (check #{check_count}){RESET}")
                    time.sleep(5)
                    continue
                
                # Check if segment is recent (within last 5 minutes)
                age_seconds = time.time() - latest_mtime
                segment_filename = os.path.basename(latest_segment)
                
                # Only log segment found occasionally (every 60 checks = 5 minutes)
                if check_count % 60 == 0:
                    logger.info(f"{BLUE}[AUDIO:{device_folder}] 📁 Found segment: {segment_filename} (age: {age_seconds:.1f}s){RESET}")
                
                if age_seconds > 300:
                    if check_count % 60 == 0:
                        logger.warning(f"{BLUE}[AUDIO:{device_folder}] ⏸️  Segment too old (check #{check_count}): {age_seconds:.0f}s{RESET}")
                    time.sleep(5)
                    continue
                
                segment_path = latest_segment
                
                cmd = [
                    'ffmpeg',
                    '-hide_banner',
                    '-loglevel', 'info',  # Need info level to get volumedetect output
                    '-i', segment_path,
                    '-t', '0.5',
                    '-af', 'volumedetect',
                    '-f', 'null',
                    '-'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                
                mean_volume = -100.0
                for line in result.stderr.split('\n'):
                    if 'mean_volume:' in line:
                        try:
                            mean_volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                            break
                        except Exception as e:
                            logger.error(f"{BLUE}[AUDIO:{device_folder}] Failed to parse volume: {line} (error: {e}){RESET}")
                
                has_audio = mean_volume > -50.0
                status_icon = '🔊' if has_audio else '🔇'
                
                # Only log audio status occasionally or when audio is detected
                if has_audio or check_count % 60 == 0:
                    logger.info(f"{BLUE}[AUDIO:{device_folder}] {status_icon} {mean_volume:.1f}dB from {segment_filename} (check #{check_count}){RESET}")
                
                detection_result = {
                    'audio': has_audio,
                    'mean_volume_db': mean_volume,
                    'segment_path': segment_path,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Write audio detection to ONE recent capture JSON
                # capture_monitor will propagate this to all subsequent frames via its audio cache
                latest_json_filename = None
                try:
                    metadata_path = get_metadata_path(device_folder)
                    os.makedirs(metadata_path, mode=0o777, exist_ok=True)
                    
                    # Find most recent capture JSON
                    import fcntl
                    latest_json = None
                    latest_mtime = 0
                    current_time = time.time()
                    
                    try:
                        with os.scandir(metadata_path) as it:
                            for entry in it:
                                if entry.is_file() and entry.name.startswith('capture_') and entry.name.endswith('.json'):
                                    mtime = entry.stat().st_mtime
                                    # Only consider JSONs from last 2 seconds
                                    if current_time - mtime < 2.0 and mtime > latest_mtime:
                                        latest_json = entry.path
                                        latest_mtime = mtime
                    except Exception:
                        pass
                    
                    # If no recent JSON, wait 100ms and try again
                    if not latest_json:
                        time.sleep(0.1)
                        try:
                            with os.scandir(metadata_path) as it:
                                for entry in it:
                                    if entry.is_file() and entry.name.startswith('capture_') and entry.name.endswith('.json'):
                                        mtime = entry.stat().st_mtime
                                        if current_time - mtime < 2.0 and mtime > latest_mtime:
                                            latest_json = entry.path
                                            latest_mtime = mtime
                        except Exception:
                            pass
                    
                    if latest_json and os.path.exists(latest_json):
                        latest_json_filename = os.path.basename(latest_json).replace('.json', '.jpg')
                        
                        # Update ONE JSON with audio data (capture_monitor will propagate via cache)
                        with open(latest_json, 'r') as f:
                            existing_data = json.load(f)
                        
                        existing_data['audio'] = has_audio
                        existing_data['mean_volume_db'] = mean_volume
                        existing_data['audio_check_timestamp'] = detection_result['timestamp']
                        existing_data['audio_segment_file'] = segment_filename
                        
                        # Write atomically
                        lock_path = latest_json + '.lock'
                        with open(lock_path, 'w') as lock_file:
                            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                            try:
                                with open(latest_json + '.tmp', 'w') as f:
                                    json.dump(existing_data, f, indent=2)
                                os.rename(latest_json + '.tmp', latest_json)
                                
                                # Log audio write
                                audio_status = "✅ YES" if has_audio else "❌ NO"
                                logger.info(f"{BLUE}[AUDIO:{device_folder}] 💾 WROTE → {os.path.basename(latest_json)}: audio={audio_status}, volume={mean_volume:.1f}dB (will propagate via cache){RESET}")
                            finally:
                                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                        
                        try:
                            os.remove(lock_path)
                        except:
                            pass
                        
                except Exception as e:
                    logger.warning(f"{BLUE}[AUDIO:{device_folder}] Failed to write audio to JSON: {e}{RESET}")
                
                # Add frame filename to detection_result for R2 upload
                if latest_json_filename:
                    detection_result['filename'] = latest_json_filename
                
                # Upload R2 image for audio_loss incidents (once per incident)
                if not has_audio and self.incident_manager:
                    device_state = self.incident_manager.get_device_state(device_folder)
                    cached_audio_r2_urls = device_state.get('audio_loss_r2_urls')
                    
                    # Upload new image if we don't have cached URLs and have a frame
                    if not cached_audio_r2_urls and latest_json_filename:
                        # First audio loss - upload frame to R2
                        now = datetime.now()
                        time_key = f"{now.hour:02d}{now.minute:02d}"
                        thumbnail_filename = latest_json_filename.replace('.jpg', '_thumbnail.jpg')
                        
                        # Check if thumbnail exists
                        captures_path = get_captures_path(device_folder)
                        thumbnail_path = os.path.join(captures_path, thumbnail_filename)
                        
                        if os.path.exists(thumbnail_path):
                            logger.info(f"{BLUE}[AUDIO:{device_folder}] 🆕 NEW audio_loss - uploading frame to R2{RESET}")
                            r2_urls = self.incident_manager.upload_freeze_frames_to_r2(
                                [latest_json_filename], [thumbnail_filename], device_folder, time_key, thumbnails_only=True
                            )
                            if r2_urls and r2_urls.get('thumbnail_urls'):
                                device_state['audio_loss_r2_urls'] = r2_urls['thumbnail_urls']
                                device_state['audio_loss_r2_images'] = r2_urls
                                detection_result['r2_images'] = r2_urls
                                logger.info(f"{BLUE}[AUDIO:{device_folder}] 📤 Uploaded to R2: {r2_urls['thumbnail_urls'][0]}{RESET}")
                    
                    # ALWAYS add cached R2 images to detection_result (for DB insert after 5min)
                    if cached_audio_r2_urls:
                        detection_result['r2_images'] = device_state.get('audio_loss_r2_images', {'thumbnail_urls': cached_audio_r2_urls})
                
                # Clear audio_loss R2 cache when audio returns
                if has_audio and self.incident_manager:
                    device_state = self.incident_manager.get_device_state(device_folder)
                    if device_state.get('audio_loss_r2_urls'):
                        device_state['audio_loss_r2_urls'] = None
                        device_state['audio_loss_r2_images'] = None
                
                # Report to incident manager for tracking only (no lifecycle management)
                if self.incident_manager:
                    host_name = os.getenv('USER', 'unknown')
                    self.incident_manager.process_detection(device_folder, detection_result, host_name)
                
            except Exception as e:
                import traceback
                logger.error(f"{BLUE}[AUDIO:{device_folder}] Error: {e}{RESET}")
                logger.error(f"{BLUE}[AUDIO:{device_folder}] Traceback: {traceback.format_exc()}{RESET}")
            
            time.sleep(5)
    
    def run(self):
        """Main event loop - watch for 1min MP3 files in temp/"""
        logger.info("Starting 1min MP3 inotify event loop...")
        
        try:
            for event in self.inotify.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                
                # Watch for 1min MP3 files (IN_MOVED_TO = atomic rename after creation)
                if 'IN_MOVED_TO' in type_names and filename.endswith('.mp3') and filename.startswith('1min_'):
                    device_folder = self.audio_path_to_device.get(path)
                    if device_folder:
                        mp3_path = os.path.join(path, filename)
                        timestamp = int(filename.replace('1min_', '').replace('.mp3', ''))
                        from shared.src.lib.utils.storage_path_utils import calculate_chunk_location
                        hour, chunk_index = calculate_chunk_location(datetime.fromtimestamp(timestamp))
                        
                        logger.info(f"[{device_folder}] 🆕 1min MP3: {filename}")
                        self.mp3_queue.put((device_folder, mp3_path, hour, chunk_index))
        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            for path in self.audio_path_to_device.keys():
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
    
    # Disable noisy faster-whisper internal logs (they don't show capture folder)
    # Our own logs are more informative and show device context
    logging.getLogger('faster_whisper').setLevel(logging.WARNING)
    
    logger.info("=" * 80)
    logger.info("Transcript Accumulator - MP3 Transcription Service")
    logger.info("=" * 80)
    logger.info("Architecture: inotify event-driven (zero CPU when idle)")
    logger.info("Watches: 1min MP3 files in /audio/temp/ (instant transcription)")
    logger.info("Scans: 10min MP3 chunks in /audio/{hour}/ (backfill/recovery)")
    logger.info("Processing: MP3 → JSON transcript (Whisper tiny model)")
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
            
            # Get audio path (ALWAYS cold storage)
            audio_base = get_audio_path(device_folder)
            
            logger.info(f"  ✓ Monitoring: {device_folder}")
            logger.info(f"    Audio: {audio_base}")
            
            monitored_devices.append({
                'device_folder': device_folder,
                'audio_base': audio_base
            })
        
        if not monitored_devices:
            logger.error("No devices to monitor!")
            return
        
        logger.info(f"Monitoring {len(monitored_devices)} devices ({skipped_count} skipped)")
        logger.info("Whisper model will be loaded on first transcription (global singleton)")
        
        monitor = InotifyTranscriptMonitor(monitored_devices)
        monitor.run()
        
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise

if __name__ == '__main__':
    main()
