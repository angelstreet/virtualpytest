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
        
        # CRITICAL: Create temp file in SAME directory as final MP3 (not /tmp)
        # This ensures os.rename() triggers IN_MOVED_TO inotify event (same filesystem)
        # Using /tmp would do copy+delete across filesystems = no inotify event!
        mp3_tmp_path = mp3_path + '.tmp'
        
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
        if mp3_tmp_path and os.path.exists(mp3_tmp_path):
            try:
                os.remove(mp3_tmp_path)
            except:
                pass
        return False

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
    """
    Check if minute was already processed today (persistent across restarts)
    
    Args:
        capture_folder: Device folder
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
        minute_offset: Minute within chunk (0-9)
    
    Returns:
        bool: True if processed today
    """
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
        
        # Check if processed today
        processed_day = minute_status.get('processed_day')
        today = datetime.now().strftime('%Y-%m-%d')
        
        return processed_day == today
        
    except Exception as e:
        return False

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
        
        self.segment_queues = {}
        self.segment_workers = {}
        self.backfill_queues = {}
        self.backfill_queued = {}
        self.backfill_scanned = {}
        
        self.active_queues = {}
        self.history_queues = {}
        
        self.backfill_scanner = None
        self.scan_position = {}
        self.last_cleanup_day = None
        
        self.whisper_worker = None
        self.worker_running = False
        
        self.audio_workers = {}
        self.incident_manager = None
        
        self._setup_watches()
        self._start_mp4_workers()
        self._start_segment_workers()
        self._start_audio_workers()
        
        all_pending = self._scan_last_24h()
        self._initialize_queues(all_pending)
        
        self._start_whisper_worker()
        self._start_backfill_scanner()
    
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
    
    def _start_segment_workers(self):
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            self.segment_queues[device_folder] = queue.Queue(maxsize=20)
            self.backfill_queues[device_folder] = queue.Queue(maxsize=100)
            self.backfill_queued[device_folder] = set()
            self.backfill_scanned[device_folder] = {}
            self.scan_position[device_folder] = 23
            
            segment_worker = threading.Thread(
                target=self._segment_worker,
                args=(device_folder,),
                daemon=True,
                name=f"segment-{device_folder}"
            )
            segment_worker.start()
            self.segment_workers[device_folder] = segment_worker
    
    def _segment_worker(self, device_folder):
        YELLOW = '\033[93m'
        MAGENTA = '\033[95m'
        RESET = '\033[0m'
        
        real_time_queue = self.segment_queues[device_folder]
        backfill_queue = self.backfill_queues[device_folder]
        last_status_log = time.time()
        idle_count = 0
        
        while True:
            item = None
            is_backfill = False
            
            try:
                item = real_time_queue.get_nowait()
                idle_count = 0  # Reset idle counter
            except queue.Empty:
                try:
                    item = backfill_queue.get(timeout=5)
                    is_backfill = True
                    idle_count = 0  # Reset idle counter
                except queue.Empty:
                    idle_count += 1
                    
                    # Log idle status every 60 seconds (12 cycles * 5s timeout)
                    if idle_count >= 12 and time.time() - last_status_log > 60:
                        logger.info(f"{YELLOW}[SEGMENT:{device_folder}] 😴 Idle - waiting for 1min segments{RESET}")
                        last_status_log = time.time()
                    continue
            
            tmp_audio = None
            hour = chunk_index = minute_offset = None
            try:
                start_time = time.time()
                tmp_audio = f'/tmp/segment_{device_folder}_{os.getpid()}.mp3'
                
                if is_backfill:
                    mp3_path, hour, chunk_index, minute_offset = item
                    color = MAGENTA
                    prefix = "BACKFILL"
                else:
                    segment_path, hour, chunk_index, minute_offset = item
                    color = YELLOW
                    prefix = "SEGMENT"
                
                # CRITICAL: Check if already processed today
                if check_minute_already_processed(device_folder, hour, chunk_index, minute_offset):
                    logger.debug(f"{color}[{prefix}:{device_folder}] ⏭️  Already processed today: {hour}h{minute_offset:02d}min{RESET}")
                    if is_backfill:
                        item_key = (hour, chunk_index, minute_offset)
                        self.backfill_queued[device_folder].discard(item_key)
                        backfill_queue.task_done()
                    else:
                        real_time_queue.task_done()
                    continue
                
                # CRITICAL: Check metadata to see if this minute should be skipped
                minute_in_hour = (chunk_index * 10) + minute_offset
                should_skip, skip_reason = should_skip_minute_by_metadata(device_folder, hour, minute_in_hour)
                
                if should_skip:
                    logger.info(f"{color}[{prefix}:{device_folder}] ⏭️  SKIP {hour}h{minute_offset:02d}min (reason: {skip_reason}){RESET}")
                    
                    # Mark as processed with skip reason
                    minute_data = {
                        'minute_offset': minute_offset,
                        'language': 'unknown',
                        'transcript': '',
                        'segments': [],
                        'skip_reason': skip_reason
                    }
                    merge_minute_to_chunk(device_folder, hour, chunk_index, minute_data, has_mp3=False)
                    
                    if is_backfill:
                        item_key = (hour, chunk_index, minute_offset)
                        self.backfill_queued[device_folder].discard(item_key)
                        backfill_queue.task_done()
                    else:
                        real_time_queue.task_done()
                    continue
                
                # Proceed with FFmpeg extraction
                if is_backfill:
                    start_sec = minute_offset * 60
                    cmd = [
                        'ffmpeg', '-ss', str(start_sec), '-t', '60',
                        '-i', mp3_path, '-vn',
                        '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1', '-b:a', '24k',
                        '-y', tmp_audio
                    ]
                else:
                    cmd = [
                        'ffmpeg', '-i', segment_path, '-vn',
                        '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1', '-b:a', '24k',
                        '-y', tmp_audio
                    ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"{color}[{prefix}:{device_folder}] FFmpeg extraction failed: {result.stderr[:200]}{RESET}")
                    if is_backfill:
                        item_key = (hour, chunk_index, minute_offset)
                        self.backfill_queued[device_folder].discard(item_key)
                        backfill_queue.task_done()
                    else:
                        real_time_queue.task_done()
                    continue
                
                # Verify extracted MP3 is valid (not empty/corrupt)
                if not os.path.exists(tmp_audio) or os.path.getsize(tmp_audio) < 1024:
                    file_size = os.path.getsize(tmp_audio) if os.path.exists(tmp_audio) else 0
                    logger.info(f"{color}[{prefix}:{device_folder}] ⏭️  SKIP - Invalid MP3 (size={file_size}B, likely silent source){RESET}")
                    
                    # Mark as processed so we don't retry infinitely
                    minute_data = {
                        'minute_offset': minute_offset,
                        'language': 'unknown',
                        'transcript': '',
                        'segments': [],
                        'skip_reason': 'invalid_extraction'
                    }
                    merge_minute_to_chunk(device_folder, hour, chunk_index, minute_data, has_mp3=False)
                    
                    if is_backfill:
                        item_key = (hour, chunk_index, minute_offset)
                        self.backfill_queued[device_folder].discard(item_key)
                        backfill_queue.task_done()
                    else:
                        real_time_queue.task_done()
                    continue
                
                lang = get_chunk_language(device_folder, hour, chunk_index)
                
                # Don't pass 'unknown' as language - Whisper will auto-detect instead
                whisper_lang = None if (not lang or lang == 'unknown') else lang
                result = transcribe_audio(tmp_audio, model_name='tiny', skip_silence_check=True, device_id=device_folder, language=whisper_lang)
                
                # Cache detected language for next segments in same chunk (skip if 'unknown' detected)
                detected_lang = result.get('language_code', 'unknown')
                if not lang and detected_lang != 'unknown':
                    set_chunk_language(device_folder, hour, chunk_index, detected_lang)
                
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
                    
                    elapsed = time.time() - start_time
                    logger.info(f"{color}[{prefix}:{device_folder}] ✅ {hour}h{minute_offset:02d}min in {elapsed:.1f}s ({len(segments)} segments){RESET}")
                
                if is_backfill:
                    item_key = (hour, chunk_index, minute_offset)
                    self.backfill_queued[device_folder].discard(item_key)
                    backfill_queue.task_done()
                else:
                    real_time_queue.task_done()
            except Exception as e:
                logger.error(f"{YELLOW}[SEGMENT:{device_folder}] Error: {e}{RESET}")
                if item:
                    if is_backfill:
                        if hour is not None:
                            item_key = (hour, chunk_index, minute_offset)
                            self.backfill_queued[device_folder].discard(item_key)
                        backfill_queue.task_done()
                    else:
                        real_time_queue.task_done()
            finally:
                if tmp_audio and os.path.exists(tmp_audio):
                    try:
                        os.remove(tmp_audio)
                    except:
                        pass
    
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
    
    def _start_backfill_scanner(self):
        scanner = threading.Thread(
            target=self._backfill_scanner_worker,
            daemon=True,
            name="backfill-scanner"
        )
        scanner.start()
        self.backfill_scanner = scanner
        logger.info("Backfill scanner started (progressive recovery when idle)")
    
    def _check_all_queues_idle(self):
        for device_folder in [d['device_folder'] for d in self.monitored_devices]:
            if not self.active_queues[device_folder].empty():
                return False
            if self.history_queues[device_folder]:
                return False
        return True
    
    def _has_transcript_for_minute(self, transcript_path: str, minute_offset: int) -> bool:
        if not os.path.exists(transcript_path):
            return False
        
        try:
            with open(transcript_path, 'r') as f:
                data = json.load(f)
            
            segments = data.get('segments', [])
            if not segments:
                return False
            
            start_time = minute_offset * 60
            end_time = (minute_offset + 1) * 60
            
            for seg in segments:
                seg_start = seg.get('start', 0)
                if start_time <= seg_start < end_time:
                    return True
            
            return False
        except:
            return False
    
    def _scan_hour_for_backfill(self, device_folder: str, hour: int) -> int:
        audio_base = None
        transcript_base = None
        
        for device_info in self.monitored_devices:
            if device_info['device_folder'] == device_folder:
                audio_base = device_info['audio_base']
                transcript_base = get_transcript_path(device_folder)
                break
        
        if not audio_base or not transcript_base:
            return 0
        
        added = 0
        now = time.time()
        scan_ttl = 3600
        
        for chunk_index in range(6):
            mp3_path = os.path.join(audio_base, str(hour), f'chunk_10min_{chunk_index}.mp3')
            if not os.path.exists(mp3_path):
                continue
            
            if not has_audio_stream(mp3_path):
                continue
            
            transcript_path = os.path.join(transcript_base, str(hour), f'chunk_10min_{chunk_index}.json')
            
            for minute_offset in range(10):
                item_key = (hour, chunk_index, minute_offset)
                
                last_scan = self.backfill_scanned[device_folder].get(item_key, 0)
                if now - last_scan < scan_ttl:
                    continue
                
                # Check if already processed today
                if check_minute_already_processed(device_folder, hour, chunk_index, minute_offset):
                    self.backfill_scanned[device_folder][item_key] = now
                    continue
                
                # Check metadata to see if should skip
                minute_in_hour = (chunk_index * 10) + minute_offset
                should_skip, skip_reason = should_skip_minute_by_metadata(device_folder, hour, minute_in_hour)
                
                if should_skip:
                    # Mark as processed with skip reason (don't queue)
                    minute_data = {
                        'minute_offset': minute_offset,
                        'language': 'unknown',
                        'transcript': '',
                        'segments': [],
                        'skip_reason': skip_reason
                    }
                    try:
                        merge_minute_to_chunk(device_folder, hour, chunk_index, minute_data, has_mp3=False)
                    except Exception as e:
                        logger.warning(f"[{device_folder}] Failed to mark minute as skipped: {e}")
                    self.backfill_scanned[device_folder][item_key] = now
                    continue
                
                # Queue if no transcript for this minute
                # No need to check timestamps - inotify catches all MP3 updates now
                if not self._has_transcript_for_minute(transcript_path, minute_offset):
                    if item_key in self.backfill_queued[device_folder]:
                        continue
                    
                    try:
                        self.backfill_queues[device_folder].put_nowait((mp3_path, hour, chunk_index, minute_offset))
                        self.backfill_queued[device_folder].add(item_key)
                        added += 1
                    except queue.Full:
                        return added
                
                self.backfill_scanned[device_folder][item_key] = now
        
        if len(self.backfill_scanned[device_folder]) > 500:
            self.backfill_scanned[device_folder] = {
                k: v for k, v in self.backfill_scanned[device_folder].items()
                if now - v < scan_ttl
            }
        
        return added
    
    def _backfill_scanner_worker(self):
        MAGENTA = '\033[95m'
        RESET = '\033[0m'
        
        time.sleep(60)
        
        while True:
            try:
                current_day = datetime.now().day
                if self.last_cleanup_day != current_day:
                    logger.info(f"{MAGENTA}[BACKFILL] Day changed - clearing scan history{RESET}")
                    for device_folder in [d['device_folder'] for d in self.monitored_devices]:
                        self.backfill_scanned[device_folder].clear()
                    self.last_cleanup_day = current_day
                
                if not self._check_all_queues_idle():
                    time.sleep(30)
                    continue
                
                for device_info in self.monitored_devices:
                    device_folder = device_info['device_folder']
                    hour = self.scan_position[device_folder]
                    
                    logger.info(f"{MAGENTA}[BACKFILL:{device_folder}] Scanning hour {hour}{RESET}")
                    
                    added = self._scan_hour_for_backfill(device_folder, hour)
                    
                    if added > 0:
                        logger.info(f"{MAGENTA}[BACKFILL:{device_folder}] Found {added} missing transcripts in hour {hour}{RESET}")
                    
                    self.scan_position[device_folder] = (hour - 1) % 24
                
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"{MAGENTA}[BACKFILL] Scanner error: {e}{RESET}")
                time.sleep(30)
    
    def _scan_last_24h(self):
        """Scan last 3h for MP3s without transcripts (accept data loss for older chunks)"""
        from pathlib import Path
        
        logger.info("Scanning last 3 hours for unprocessed MP3s (ignoring older backlog)")
        now = time.time()
        cutoff = now - (3 * 3600)  # Only last 3 hours
        
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
                    chunk_file = Path(transcript_dir) / f'chunk_10min_{chunk_index}.json'
                    
                    # Only queue if transcript doesn't exist or is stale
                    # No need to check MP3 vs transcript mtime - inotify catches all updates now
                    if not chunk_file.exists() or chunk_file.stat().st_mtime < cutoff:
                        pending.append((mtime, hour, mp3_file.name))
            
            pending.sort(reverse=True)
            
            # CRITICAL: Only keep 3 newest (accept data loss for older chunks)
            if len(pending) > 3:
                logger.warning(f"[{device_folder}] Found {len(pending)} pending MP3s, keeping only 3 newest (accepting data loss)")
                pending = pending[:3]
            
            all_pending[device_folder] = pending
            
            if pending:
                logger.info(f"[{device_folder}] {len(pending)} MP3s queued for transcription")
        
        return all_pending
    
    def _initialize_queues(self, all_pending):
        """Put up to 3 newest in active queue (scan already limited to 3 items max)"""
        for device_folder, pending in all_pending.items():
            self.active_queues[device_folder] = queue.Queue(maxsize=3)
            self.history_queues[device_folder] = []
            
            for item in pending[:3]:
                try:
                    self.active_queues[device_folder].put_nowait(item)
                except queue.Full:
                    break
            
            # Note: pending already limited to 3 items in _scan_last_24h, so history will be empty
            self.history_queues[device_folder] = pending[3:] if len(pending) > 3 else []
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
        GREEN = '\033[92m'
        RESET = '\033[0m'
        
        device_index = 0
        idle_cycles = 0
        last_status_log = time.time()
        
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
                
                mp3_path = os.path.join(audio_base, str(hour), filename)
                chunk_index = int(filename.split('_')[-1].replace('.mp3', ''))
                
                # Logging is done inside transcribe_mp3_chunk_progressive (shows full path)
                minute_results = transcribe_mp3_chunk_progressive(mp3_path, device_folder, hour, chunk_index)
                
                for minute_data in minute_results:
                    merge_start = time.time()
                    merge_minute_to_chunk(device_folder, hour, chunk_index, minute_data, has_mp3=True)
                    merge_time = time.time() - merge_start
                    logger.info(f"{GREEN}[WHISPER:{device_folder}] 💾 Saved minute {minute_data['minute_offset']}/10 in {merge_time:.3f}s{RESET}")
                
                work_queue.task_done()
                idle_cycles = 0  # Reset idle counter on work
                
                if work_queue.empty():
                    self._refill_from_history(device_folder)
                
                # Show queue status for all devices
                self._log_queue_status()
                
                time.sleep(10)
                
            except queue.Empty:
                idle_cycles += 1
                
                # Log idle status every 60 seconds (120 cycles * 0.5s)
                if time.time() - last_status_log > 60:
                    self._log_whisper_idle_status()
                    last_status_log = time.time()
            
            device_index = (device_index + 1) % len(self.monitored_devices)
            time.sleep(0.5)
    
    def _refill_from_history(self, device_folder):
        """Refill active queue from history - always prioritize 3 newest"""
        GREEN = '\033[92m'
        RESET = '\033[0m'
        
        history = self.history_queues[device_folder]
        
        if not history:
            logger.info(f"{GREEN}[WHISPER:{device_folder}] All caught up{RESET}")
            return
        
        # Always sort to get 3 newest from history (in case old items were pushed back)
        history.sort(reverse=True)  # Newest first by mtime
        
        refill = history[:3]
        self.history_queues[device_folder] = history[3:]
        
        work_queue = self.active_queues[device_folder]
        for item in refill:
            try:
                work_queue.put_nowait(item)
            except queue.Full:
                self.history_queues[device_folder].insert(0, item)
                break
        
        logger.info(f"{GREEN}[WHISPER:{device_folder}] Refilled with 3 newest ({len(self.history_queues[device_folder])} remaining){RESET}")
    
    def _log_whisper_idle_status(self):
        """Log idle status when no work to do"""
        GREEN = '\033[92m'
        RESET = '\033[0m'
        
        total_active = sum(self.active_queues[d['device_folder']].qsize() for d in self.monitored_devices)
        total_history = sum(len(self.history_queues[d['device_folder']]) for d in self.monitored_devices)
        
        if total_active == 0 and total_history == 0:
            logger.info(f"{GREEN}[WHISPER] 😴 Idle - all caught up (no MP3s to transcribe){RESET}")
        else:
            logger.info(f"{GREEN}[WHISPER] 🔄 Waiting for next chunk (active={total_active}, history={total_history}){RESET}")
    
    def _log_queue_status(self):
        """Log queue status for all devices"""
        GREEN = '\033[92m'
        RESET = '\033[0m'
        
        logger.info("=" * 80)
        logger.info(f"{GREEN}📊 WHISPER QUEUE STATUS{RESET}")
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
                logger.info(f"{GREEN}  [WHISPER:{device_folder}] Active: [{active_str}] | History: {history_count}{RESET}")
            else:
                logger.info(f"{GREEN}  [WHISPER:{device_folder}] ✓ All caught up{RESET}")
        
        logger.info("=" * 80)
    
    def _process_mp4_backlog_batch(self, device_folder):
        """Process MP4 backlog batch"""
        CYAN = '\033[96m'
        RESET = '\033[0m'
        
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
            logger.info(f"{CYAN}[MP4:{device_folder}] Refilled {added} MP4s ({len(self.mp4_backlog[device_folder])} remaining){RESET}")
        
        return added
    
    def _mp4_worker(self, device_folder):
        """Worker thread for MP4 → MP3 audio extraction (fast, ~3s per chunk)"""
        CYAN = '\033[96m'
        RESET = '\033[0m'
        
        work_queue = self.mp4_queues[device_folder]
        last_status_log = time.time()
        idle_count = 0
        
        logger.info(f"{CYAN}[MP4:{device_folder}] Worker ready (audio extraction pipeline){RESET}")
        
        while True:
            try:
                # Try to get work with timeout for idle detection
                path, filename = work_queue.get(timeout=5)
                idle_count = 0  # Reset idle counter
            except queue.Empty:
                idle_count += 1
                
                # Log idle status every 60 seconds (12 cycles * 5s timeout)
                if idle_count >= 12 and time.time() - last_status_log > 60:
                    logger.info(f"{CYAN}[MP4:{device_folder}] 😴 Idle - waiting for MP4 chunks{RESET}")
                    last_status_log = time.time()
                
                # Queue is empty - check backlog
                if self._process_mp4_backlog_batch(device_folder) == 0:
                    # No backlog either - truly idle
                    continue
                else:
                    # Added backlog items, get next item
                    idle_count = 0
                    continue
            
            try:
                # Log queue size occasionally
                queue_size = work_queue.qsize()
                if queue_size > 10:
                    logger.warning(f"{CYAN}[MP4:{device_folder}] Queue backlog: {queue_size} chunks{RESET}")
                
                # Parse hour and chunk_index from path and filename
                hour = int(os.path.basename(path))
                chunk_index = int(filename.replace('chunk_10min_', '').replace('.mp4', ''))
                
                mp4_path = os.path.join(path, filename)
                
                # Build MP3 output path (same structure under /audio/)
                device_base_path = get_device_base_path(device_folder)
                audio_base = get_audio_path(device_folder)
                mp3_path = os.path.join(audio_base, str(hour), f'chunk_10min_{chunk_index}.mp3')
                
                if os.path.exists(mp3_path):
                    logger.debug(f"{CYAN}[MP4:{device_folder}] Skipping {hour}/chunk_10min_{chunk_index}.mp4 (MP3 exists){RESET}")
                    continue
                
                # Extract audio
                logger.info(f"{CYAN}[MP4:{device_folder}] Extracting: {hour}/chunk_10min_{chunk_index}.mp4{RESET}")
                result = extract_audio_from_mp4(mp4_path, mp3_path, device_folder, hour, chunk_index)
                if result is True:
                    logger.info(f"{CYAN}[MP4:{device_folder}] ✅ Complete for hour {hour}, chunk {chunk_index}{RESET}")
                elif result is False:
                    logger.warning(f"{CYAN}[MP4:{device_folder}] ⚠️ Failed for {hour}/chunk_10min_{chunk_index}.mp4{RESET}")
                
            except Exception as e:
                logger.error(f"{CYAN}[MP4:{device_folder}] Error: {e}{RESET}")
            finally:
                work_queue.task_done()
    
    def run(self):
        """Main event loop - enqueue files for worker threads (dual pipeline)"""
        logger.info("=" * 80)
        logger.info("Starting inotify event loop (dual pipeline)")
        logger.info("Zero CPU when idle - event-driven processing")
        logger.info("Pipeline 1: MP4 → MP3 (audio extraction)")
        logger.info("Pipeline 2: MP3 → JSON (transcription, ~10s per chunk)")
        logger.info("=" * 80)
        
        try:
            for event in self.inotify.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                
                # Only process files moved into watched directories (atomic writes)
                if 'IN_MOVED_TO' not in type_names:
                    continue
                
                # Pipeline 1: MP4 chunk created → Extract audio (10min archival)
                if filename.endswith('.mp4') and 'chunk_10min_' in filename:
                    device_folder = self.segments_path_to_device.get(path)
                    if device_folder:
                        logger.info(f"[{device_folder}] 🎬 New MP4 detected: {filename}")
                        try:
                            work_queue = self.mp4_queues[device_folder]
                            work_queue.put_nowait((path, filename))
                        except queue.Full:
                            logger.error(f"[{device_folder}] 🚨 MP4 queue FULL, dropping: {filename}")
                
                # Pipeline 3: 1min segment → Transcribe immediately (low latency)
                elif filename.endswith('.mp4') and 'segment_1min_' in filename:
                    device_folder = self.segments_path_to_device.get(path)
                    if device_folder:
                        try:
                            segment_path = os.path.join(path, filename)
                            hour = int(os.path.basename(path))
                            parts = filename.replace('segment_1min_', '').replace('.mp4', '').split('_')
                            minute_in_hour = int(parts[0])
                            chunk_index = minute_in_hour // 10
                            minute_offset = minute_in_hour % 10
                            
                            work_queue = self.segment_queues[device_folder]
                            work_queue.put_nowait((segment_path, hour, chunk_index, minute_offset))
                        except queue.Full:
                            pass
                
                # Pipeline 2: MP3 chunk created → Transcribe
                elif filename.endswith('.mp3') and 'chunk_10min_' in filename:
                    device_folder = self.audio_path_to_device.get(path)
                    if device_folder:
                        logger.info(f"[{device_folder}] 🆕 New MP3: {filename}")
                        hour = int(os.path.basename(path))
                        mtime = os.path.getmtime(os.path.join(path, filename))
                        new_item = (mtime, hour, filename)
                        
                        work_queue = self.active_queues[device_folder]
                        try:
                            work_queue.put_nowait(new_item)
                            logger.info(f"[{device_folder}] ✓ Added to active queue")
                        except queue.Full:
                            # PRIORITY: New files replace oldest in active queue
                            # Extract all items, find oldest, push it to history, add new one
                            items = []
                            while not work_queue.empty():
                                items.append(work_queue.get_nowait())
                            
                            # Sort by mtime (oldest first), take oldest out
                            items.sort()  # Ascending by mtime
                            oldest = items.pop(0)  # Remove oldest
                            
                            # Put oldest back to history
                            self.history_queues[device_folder].insert(0, oldest)
                            
                            # Add new item and remaining items back to active queue
                            items.append(new_item)
                            items.sort(reverse=True)  # Newest first
                            for item in items:
                                work_queue.put_nowait(item)
                            
                            logger.info(f"[{device_folder}] ⚡ Replaced oldest in active queue with new MP3")
        
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
    
    # Disable noisy faster-whisper internal logs (they don't show capture folder)
    # Our own logs are more informative and show device context
    logging.getLogger('faster_whisper').setLevel(logging.WARNING)
    
    logger.info("=" * 80)
    logger.info("Starting inotify-based Transcript Accumulator (Dual Pipeline)")
    logger.info("=" * 80)
    logger.info("Architecture: Event-driven (zero CPU when idle)")
    logger.info("Priority: Normal (no nice) - faster transcription")
    logger.info("Threads: 4 per library (was 2) - better Whisper performance")
    logger.info("Pipeline 1: MP4 → MP3 (audio extraction, ~3s)")
    logger.info("Pipeline 2: MP3 → JSON (transcribe once, save by minute)")
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
        
        monitor = InotifyTranscriptMonitor(monitored_devices)
        monitor.run()
        
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise

if __name__ == '__main__':
    main()
