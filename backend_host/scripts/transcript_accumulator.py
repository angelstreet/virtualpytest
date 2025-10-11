#!/usr/bin/env python3
"""
inotify-based Transcript Accumulator - MP3 Transcription Only
Event-driven processing: Zero CPU when idle, immediate response to new files

COLD STORAGE ARCHITECTURE:
  - Watches COLD /audio/temp/ for 1min MP3 files (instant transcription)
  - Scans COLD /audio/{hour}/ for 10min MP3 chunks (backfill/recovery)
  - MP3s created by hot_cold_archiver.py (extracted from MP4 segments)

Instant transcription: 1min MP3 → immediate Whisper transcription → merge to JSON
Progressive save: Transcripts saved by minute to chunk_10min_X.json
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

# Pre-translation target languages
TRANSLATION_LANGUAGES = {
    'fr': 'French',
    'en': 'English',
    'es': 'Spanish',
    'de': 'German',
    'it': 'Italian'
}

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
        
        # Calculate Real-Time Factor (RTF): how fast Whisper processes vs real-time
        # RTF < 1.0 = faster than real-time (good!)
        # RTF = 1.0 = real-time speed
        # RTF > 1.0 = slower than real-time (problematic)
        rtf = elapsed / audio_duration if audio_duration > 0 else 0.0
        rtf_note = f" (RTF={rtf:.2f}x)"
        
        logger.info(f"{GREEN}[WHISPER:{capture_folder}] ✅ TRANSCRIPTION COMPLETE:{RESET}")
        logger.info(f"{GREEN}  • Whisper processing time: {elapsed:.1f}s for {audio_duration:.1f}s audio{rtf_note}{duration_note}{RESET}")
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
            
            # ROLLING 24H: Check if existing chunk is from previous day - if so, clear it
            should_clear_old_data = False
            if chunk_data['minute_statuses']:
                # Check if any existing minute is from a different day
                existing_days = {status.get('processed_day') for status in chunk_data['minute_statuses'].values() if status.get('processed_day')}
                if existing_days and processed_day not in existing_days:
                    logger.info(f"[{capture_folder}] 🔄 New day detected for {hour}h/chunk_{chunk_index} (old: {existing_days}, new: {processed_day}) - clearing old segments")
                    should_clear_old_data = True
            
            if should_clear_old_data:
                # Clear old day's data completely
                chunk_data['segments'] = []
                chunk_data['minute_statuses'] = {}
                chunk_data['transcript'] = ''
                chunk_data['confidence'] = 0.0
                chunk_data['timestamp'] = datetime.now().isoformat()
            
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
                
                # Build full MP3 path for logging
                mp3_filename = chunk_data.get('mp3_file')
                if mp3_filename:
                    from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
                    audio_cold = get_cold_storage_path(capture_folder, 'audio')
                    mp3_full_path = os.path.join(audio_cold, str(hour), mp3_filename)
                else:
                    mp3_full_path = "None"
                
                logger.info(f"{GREEN}[{capture_folder}] 💾 Merged transcript to→ {hour}h/chunk_{chunk_index}: {len(chunk_data['segments'])} total segments, {len(chunk_data['transcript'])} chars{RESET}")
                logger.info(f"{GREEN}[{capture_folder}] 📄 language={chunk_data.get('language')}, confidence={chunk_data.get('confidence', 0):.2f}, audio_duration={chunk_data.get('chunk_duration_seconds', 0):.1f}s{RESET}")
                logger.info(f"{GREEN}[{capture_folder}] 🎵 mp3_file={mp3_full_path}{RESET}")
                
                # Show newly added minute's transcript (full text for this minute)
                minute_transcript = ' '.join([s.get('text', '').strip() for s in new_segments])
                if len(minute_transcript) > 500:
                    logger.info(f"{GREEN}[{capture_folder}] 📋 (minute {minute_offset}) Transcript: \"{minute_transcript[:500]}...\" (truncated, {len(minute_transcript)} chars total){RESET}")
                else:
                    logger.info(f"{GREEN}[{capture_folder}] 📋 (minute {minute_offset}) Transcript: \"{minute_transcript}\"{RESET}")
                
                # Show segment statistics
                sample_seg = new_segments[0]
                seg_duration = sample_seg.get('duration', sample_seg.get('end', 0) - sample_seg.get('start', 0))
                logger.info(f"{GREEN}[{capture_folder}] 📊 Added {len(new_segments)} segments: first segment at {sample_seg.get('start', 0):.2f}s, duration={seg_duration:.2f}s, confidence={sample_seg.get('confidence', 0):.2f}{RESET}")
                
                # Show full chunk transcript if it's substantial (e.g., > 200 chars)
                full_transcript = chunk_data['transcript']
                if len(full_transcript) >= 200:
                    if len(full_transcript) > 1000:
                        logger.info(f"{GREEN}[{capture_folder}] 📝 FULL CHUNK TRANSCRIPT: \"{full_transcript[:1000]}...\" (truncated, {len(full_transcript)} chars total){RESET}")
                    else:
                        logger.info(f"{GREEN}[{capture_folder}] 📝 FULL CHUNK TRANSCRIPT: \"{full_transcript}\"{RESET}")
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
        
        # Pre-translate chunk if it has substantial content
        if new_segments and len(chunk_data.get('transcript', '')) > 20:
            translate_chunk_to_languages(capture_folder, hour, chunk_index, chunk_path, device_base_path)
    except Exception as e:
        logger.warning(f"Failed to update transcript manifest: {e}")

def translate_chunk_to_languages(capture_folder: str, hour: int, chunk_index: int, chunk_path: str, device_base_path: str):
    """
    Pre-translate transcript chunk to multiple languages in background.
    Creates language-specific JSON files (e.g., chunk_10min_0_fr.json).
    
    Args:
        capture_folder: Device folder (e.g., 'capture1')
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
        chunk_path: Path to original transcript JSON
        device_base_path: Base path for device
    """
    try:
        # Load original transcript
        with open(chunk_path, 'r') as f:
            original_data = json.load(f)
        
        full_transcript = original_data.get('transcript', '')
        if not full_transcript or len(full_transcript) < 20:
            # Skip translation for very short or empty transcripts
            return
        
        source_language = original_data.get('language', 'unknown')
        if source_language == 'unknown':
            logger.debug(f"[{capture_folder}] Skipping translation - unknown source language")
            return
        
        # Map detected language to code
        lang_code_map = {
            'english': 'en', 'french': 'fr', 'spanish': 'es', 
            'german': 'de', 'italian': 'it', 'portuguese': 'pt',
            'russian': 'ru', 'japanese': 'ja', 'korean': 'ko',
            'chinese': 'zh', 'arabic': 'ar', 'hindi': 'hi'
        }
        source_code = lang_code_map.get(source_language.lower(), 'en')
        
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        RESET = '\033[0m'
        
        logger.info(f"{CYAN}[TRANSLATE:{capture_folder}] 🌐 Pre-translating {hour}h/chunk_{chunk_index} from {source_language} to {len(TRANSLATION_LANGUAGES)} languages...{RESET}")
        
        translation_start = time.time()
        translated_count = 0
        
        # Import translation utils
        from backend_host.src.lib.utils.translation_utils import translate_text
        
        transcript_dir = os.path.dirname(chunk_path)
        
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            # Skip if same as source
            if lang_code == source_code:
                logger.debug(f"[TRANSLATE:{capture_folder}] Skipping {lang_code} (same as source)")
                continue
            
            lang_file_path = os.path.join(transcript_dir, f'chunk_10min_{chunk_index}_{lang_code}.json')
            
            try:
                # Translate full transcript (single API call)
                lang_start = time.time()
                result = translate_text(full_transcript, source_code, lang_code, 'google')
                lang_elapsed = time.time() - lang_start
                
                if not result.get('success'):
                    logger.warning(f"[TRANSLATE:{capture_folder}] ⚠️  Failed to translate to {lang_code}")
                    continue
                
                translated_text = result.get('translated_text', '')
                
                # Create translated version of the chunk
                translated_data = original_data.copy()
                translated_data['transcript'] = translated_text
                translated_data['source_language'] = source_language
                translated_data['translated_to'] = lang_code
                translated_data['translation_timestamp'] = datetime.now().isoformat()
                
                # Translate segments (map translated text to segments by proportional splitting)
                if original_data.get('segments'):
                    original_segments = original_data['segments']
                    translated_segments = []
                    
                    # Simple proportional split (better than nothing)
                    words_original = full_transcript.split()
                    words_translated = translated_text.split()
                    ratio = len(words_translated) / len(words_original) if len(words_original) > 0 else 1.0
                    
                    for seg in original_segments:
                        seg_copy = seg.copy()
                        seg_text = seg.get('text', '').strip()
                        
                        # Find segment text in original transcript
                        if seg_text in full_transcript:
                            idx = full_transcript.find(seg_text)
                            # Approximate position in translated text
                            char_ratio = len(translated_text) / len(full_transcript) if len(full_transcript) > 0 else 1.0
                            approx_idx = int(idx * char_ratio)
                            approx_len = int(len(seg_text) * char_ratio)
                            
                            translated_seg_text = translated_text[approx_idx:approx_idx + approx_len].strip()
                            if not translated_seg_text:
                                # Fallback: use proportional chunk
                                seg_word_count = len(seg_text.split())
                                translated_seg_text = ' '.join(translated_text.split()[:seg_word_count])
                            
                            seg_copy['text'] = translated_seg_text
                        else:
                            # Fallback
                            seg_copy['text'] = translated_text[:50]
                        
                        translated_segments.append(seg_copy)
                    
                    translated_data['segments'] = translated_segments
                
                # Save translated version atomically
                with open(lang_file_path + '.tmp', 'w') as f:
                    json.dump(translated_data, f, indent=2)
                os.rename(lang_file_path + '.tmp', lang_file_path)
                
                file_size = os.path.getsize(lang_file_path)
                translated_count += 1
                
                # Detailed subtitle creation log
                logger.info(f"{GREEN}[SUBTITLE:{capture_folder}] ✅ Created {TRANSLATION_LANGUAGES[lang_code]} subtitle:{RESET}")
                logger.info(f"{GREEN}  • File: {lang_file_path}{RESET}")
                logger.info(f"{GREEN}  • Size: {file_size/1024:.1f}KB, Characters: {len(translated_text)}, Time: {lang_elapsed:.2f}s{RESET}")
                logger.info(f"{GREEN}  • Translated from: {source_language} → {TRANSLATION_LANGUAGES[lang_code]}{RESET}")
                
                # Show preview of translated text
                preview_text = translated_text[:100] + '...' if len(translated_text) > 100 else translated_text
                logger.info(f"{GREEN}  • Preview: \"{preview_text}\"{RESET}")
                
            except Exception as e:
                logger.error(f"[TRANSLATE:{capture_folder}] ❌ Error translating to {lang_code}: {e}")
                continue
        
        total_elapsed = time.time() - translation_start
        logger.info(f"{GREEN}[SUBTITLE-BATCH:{capture_folder}] 🎉 Completed {translated_count}/{len(TRANSLATION_LANGUAGES)} subtitle files in {total_elapsed:.2f}s{RESET}")
        
        if translated_count > 0:
            avg_time = total_elapsed / translated_count
            logger.info(f"{GREEN}[SUBTITLE-BATCH:{capture_folder}] 📊 Average time per subtitle: {avg_time:.2f}s{RESET}")
        
        # Generate dubbed audio for translated languages (reuse restart Edge-TTS!)
        if translated_count > 0:
            generate_dubbed_audio_for_chunk(capture_folder, hour, chunk_index, transcript_dir, device_base_path)
        
        # Update manifest with available languages
        try:
            from backend_host.scripts.hot_cold_archiver import update_transcript_manifest
            update_transcript_manifest(device_base_path, hour, chunk_index, chunk_path, has_mp3=original_data.get('mp3_file') is not None)
        except Exception as e:
            logger.warning(f"[TRANSLATE:{capture_folder}] Failed to update manifest after translation: {e}")
        
    except Exception as e:
        logger.error(f"[TRANSLATE:{capture_folder}] ❌ Translation error: {e}")
        import traceback
        logger.error(f"[TRANSLATE:{capture_folder}] Traceback: {traceback.format_exc()}")

def generate_1min_dubbed_audio(device_folder: str, mp3_path: str, transcript_text: str, slot: int, hour: int, chunk_index: int):
    """
    Generate 1-minute dubbed audio immediately after transcription (fast user access!)
    Uses rotating slots like 1min MP3s: 1min_0_fr.mp3, 1min_1_en.mp3, etc.
    
    Args:
        device_folder: Device folder (e.g., 'capture1')
        mp3_path: Original 1min MP3 path (for timing reference)
        transcript_text: Transcribed text to dub
        slot: Minute slot (0-9)
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
    """
    try:
        from backend_host.src.lib.utils.audio_utils import generate_edge_tts_audio
        from shared.src.lib.utils.translation_utils import translate_text
        from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
        
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        RESET = '\033[0m'
        
        # Get audio temp directory (COLD storage, same as 1min MP3s)
        audio_cold = get_cold_storage_path(device_folder, 'audio')
        audio_temp_dir = os.path.join(audio_cold, 'temp')
        os.makedirs(audio_temp_dir, exist_ok=True)
        
        # Voice mapping (same as 10min dubbing)
        voice_map = {
            'fr': 'fr-FR-DeniseNeural',
            'en': 'en-US-JennyNeural',
            'es': 'es-ES-ElviraNeural',
            'de': 'de-DE-KatjaNeural',
            'it': 'it-IT-ElsaNeural'
        }
        
        logger.info(f"{CYAN}[1MIN-DUB:{device_folder}] 🎤 Starting 1min dubbed audio for slot {slot} ({len(transcript_text)} chars)...{RESET}")
        dub_start = time.time()
        dubbed_count = 0
        
        for lang_code, voice_name in voice_map.items():
            try:
                lang_start = time.time()
                
                # Translate transcript
                translated_text = translate_text(transcript_text, lang_code)
                if not translated_text or len(translated_text) < 10:
                    logger.debug(f"[1MIN-DUB:{device_folder}] Skipping {lang_code} (translation too short)")
                    continue
                
                # Generate dubbed audio with rotating slot naming: 1min_0_fr.mp3
                output_mp3 = os.path.join(audio_temp_dir, f'1min_{slot}_{lang_code}.mp3')
                
                # Delete old file in this slot (if exists) - rotating behavior
                if os.path.exists(output_mp3):
                    try:
                        os.remove(output_mp3)
                    except:
                        pass
                
                success = generate_edge_tts_audio(
                    text=translated_text,
                    language_code=lang_code,
                    output_path=output_mp3,
                    voice_name=voice_name
                )
                
                if success and os.path.exists(output_mp3):
                    audio_size = os.path.getsize(output_mp3)
                    dubbed_count += 1
                    lang_elapsed = time.time() - lang_start
                    
                    # Detailed 1min dubbed audio log
                    logger.info(f"{GREEN}[1MIN-DUB:{device_folder}] ✅ Created 1-minute dubbed audio:{RESET}")
                    logger.info(f"{GREEN}  • Language: {TRANSLATION_LANGUAGES[lang_code]} ({lang_code}){RESET}")
                    logger.info(f"{GREEN}  • File: {output_mp3}{RESET}")
                    logger.info(f"{GREEN}  • Size: {audio_size/1024:.1f}KB, Duration: ~1min, Time: {lang_elapsed:.2f}s{RESET}")
                    logger.info(f"{GREEN}  • Slot: {slot}, Hour: {hour}, Chunk: {chunk_index}{RESET}")
                    logger.info(f"{GREEN}  • Text: \"{translated_text[:80]}...\"{RESET}")
                else:
                    logger.warning(f"[1MIN-DUB:{device_folder}] ⚠️  Failed to generate {lang_code} audio")
                
            except Exception as e:
                logger.error(f"[1MIN-DUB:{device_folder}] ❌ Error dubbing {lang_code}: {e}")
                continue
        
        total_elapsed = time.time() - dub_start
        logger.info(f"{GREEN}[1MIN-DUB-BATCH:{device_folder}] 🎉 Completed {dubbed_count}/{len(voice_map)} 1-minute dubbed audio files in {total_elapsed:.2f}s{RESET}")
        
        if dubbed_count > 0:
            avg_time = total_elapsed / dubbed_count
            logger.info(f"{GREEN}[1MIN-DUB-BATCH:{device_folder}] 📊 Average time per dubbed audio: {avg_time:.2f}s{RESET}")
        
    except Exception as e:
        logger.error(f"[1MIN-DUB:{device_folder}] ❌ Dubbing error: {e}")
        import traceback
        logger.error(f"[1MIN-DUB:{device_folder}] Traceback: {traceback.format_exc()}")


def generate_dubbed_audio_for_chunk(capture_folder: str, hour: int, chunk_index: int, transcript_dir: str, device_base_path: str):
    """
    Generate dubbed audio for all translated languages (reuses restart Edge-TTS pipeline!)
    Creates language-specific MP3 files for instant playback.
    
    Args:
        capture_folder: Device folder (e.g., 'capture1')
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
        transcript_dir: Directory containing transcript JSONs
        device_base_path: Base path for device
    """
    try:
        from backend_host.src.lib.utils.audio_utils import generate_edge_tts_audio
        from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
        
        MAGENTA = '\033[95m'
        GREEN = '\033[92m'
        RESET = '\033[0m'
        
        logger.info(f"{MAGENTA}[DUBBING:{capture_folder}] 🎤 Starting dubbed audio generation for {hour}h/chunk_{chunk_index}...{RESET}")
        dubbing_start = time.time()
        dubbed_count = 0
        
        # Get audio output directory (COLD storage)
        audio_cold = get_cold_storage_path(capture_folder, 'audio')
        audio_hour_dir = os.path.join(audio_cold, str(hour))
        os.makedirs(audio_hour_dir, exist_ok=True)
        
        # Voice mapping (reuse restart configuration)
        voice_map = {
            'fr': 'fr-FR-DeniseNeural',
            'en': 'en-US-JennyNeural',
            'es': 'es-ES-ElviraNeural',
            'de': 'de-DE-KatjaNeural',
            'it': 'it-IT-ElsaNeural'
        }
        
        for lang_code, voice_name in voice_map.items():
            lang_transcript_file = os.path.join(transcript_dir, f'chunk_10min_{chunk_index}_{lang_code}.json')
            
            # Skip if translation doesn't exist
            if not os.path.exists(lang_transcript_file):
                logger.debug(f"[DUBBING:{capture_folder}] Skipping {lang_code} (no translation file)")
                continue
            
            try:
                # Load translated transcript
                with open(lang_transcript_file, 'r') as f:
                    translated_data = json.load(f)
                
                translated_text = translated_data.get('transcript', '')
                if not translated_text or len(translated_text) < 20:
                    logger.debug(f"[DUBBING:{capture_folder}] Skipping {lang_code} (transcript too short)")
                    continue
                
                # Generate dubbed audio using Edge-TTS (SAME as restart!)
                output_mp3 = os.path.join(audio_hour_dir, f'chunk_10min_{chunk_index}_{lang_code}.mp3')
                
                lang_start = time.time()
                success = generate_edge_tts_audio(
                    text=translated_text,
                    language_code=lang_code,
                    output_path=output_mp3,
                    voice_name=voice_name
                )
                lang_elapsed = time.time() - lang_start
                
                if success and os.path.exists(output_mp3):
                    audio_size = os.path.getsize(output_mp3)
                    dubbed_count += 1
                    
                    # Detailed 10min dubbed audio log
                    logger.info(f"{GREEN}[10MIN-DUB:{capture_folder}] ✅ Created 10-minute dubbed audio:{RESET}")
                    logger.info(f"{GREEN}  • Language: {TRANSLATION_LANGUAGES[lang_code]} ({lang_code}){RESET}")
                    logger.info(f"{GREEN}  • File: {output_mp3}{RESET}")
                    logger.info(f"{GREEN}  • Size: {audio_size/1024:.1f}KB, Duration: ~10min, Time: {lang_elapsed:.2f}s{RESET}")
                    logger.info(f"{GREEN}  • Hour: {hour}, Chunk: {chunk_index}{RESET}")
                    
                    # Show preview of dubbed text
                    preview = translated_text[:100] + '...' if len(translated_text) > 100 else translated_text
                    logger.info(f"{GREEN}  • Text: \"{preview}\"{RESET}")
                else:
                    logger.warning(f"[10MIN-DUB:{capture_folder}] ⚠️  Failed to generate {lang_code} audio")
                
            except Exception as e:
                logger.error(f"[DUBBING:{capture_folder}] ❌ Error generating {lang_code} audio: {e}")
                continue
        
        total_elapsed = time.time() - dubbing_start
        logger.info(f"{GREEN}[10MIN-DUB-BATCH:{capture_folder}] 🎉 Completed {dubbed_count}/{len(voice_map)} 10-minute dubbed audio files in {total_elapsed:.2f}s{RESET}")
        
        if dubbed_count > 0:
            avg_time = total_elapsed / dubbed_count
            logger.info(f"{GREEN}[10MIN-DUB-BATCH:{capture_folder}] 📊 Average time per dubbed audio: {avg_time:.2f}s{RESET}")
        
    except Exception as e:
        logger.error(f"[DUBBING:{capture_folder}] ❌ Dubbing error: {e}")
        import traceback
        logger.error(f"[DUBBING:{capture_folder}] Traceback: {traceback.format_exc()}")

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
        # Two separate queues: inotify (real-time) and scan (backlog)
        self.inotify_queue = LifoQueue(maxsize=500)  # Real-time events (priority)
        self.scan_queue = queue.Queue(maxsize=10)    # Backlog/history (max 10)
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
            
            # Watch COLD temp directory for 1min MP3 files (same location as segments/temp)
            from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
            audio_cold = get_cold_storage_path(device_folder, 'audio')
            audio_temp_dir = os.path.join(audio_cold, 'temp')
            os.makedirs(audio_temp_dir, exist_ok=True)
            self.inotify.add_watch(audio_temp_dir)
            self.audio_path_to_device[audio_temp_dir] = device_folder
            
            logger.info(f"[{device_folder}] ✓ Watching {audio_temp_dir}")
        
        logger.info(f"Total: {len(self.audio_path_to_device)} temp dir watches")
        
        # Validate inotify is working
        self._validate_inotify_setup()
    
    def _validate_inotify_setup(self):
        """Test that inotify watches are working correctly"""
        logger.info("Validating inotify setup...")
        
        test_results = []
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            
            # Use COLD temp directory (same as setup)
            from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
            audio_cold = get_cold_storage_path(device_folder, 'audio')
            audio_temp_dir = os.path.join(audio_cold, 'temp')
            
            # Create test file to verify inotify
            test_file = os.path.join(audio_temp_dir, '_inotify_test.mp3')
            try:
                # Write test file with atomic rename (same as production)
                logger.info(f"[{device_folder}] Testing inotify on: {audio_temp_dir}")
                with open(test_file + '.tmp', 'w') as f:
                    f.write('test')
                os.rename(test_file + '.tmp', test_file)
                
                # Clean up
                time.sleep(0.1)
                if os.path.exists(test_file):
                    os.remove(test_file)
                
                test_results.append(f"✓ {device_folder}")
                logger.info(f"[{device_folder}] ✓ inotify watch validated: {audio_temp_dir}")
            except Exception as e:
                test_results.append(f"✗ {device_folder}: {e}")
                logger.error(f"[{device_folder}] ✗ inotify validation failed on {audio_temp_dir}: {e}")
        
        logger.info(f"inotify validation: {', '.join(test_results)}")
    
    def _scan_existing_mp3s(self):
        """Scan existing MP3s and queue missing transcripts (max 10 total)"""
        CYAN = '\033[96m'
        RESET = '\033[0m'
        
        logger.info(f"{CYAN}{'=' * 80}{RESET}")
        logger.info(f"{CYAN}[SCAN] 📋 Scanning for backlog MP3s (history files)...{RESET}")
        logger.info(f"{CYAN}{'=' * 80}{RESET}")
        
        all_pending = []  # Collect all pending items across devices
        
        for device_info in self.monitored_devices:
            device_folder = device_info['device_folder']
            
            from shared.src.lib.utils.storage_path_utils import get_cold_storage_path, calculate_chunk_location
            audio_cold = get_cold_storage_path(device_folder, 'audio')
            transcript_base = get_transcript_path(device_folder)
            
            device_1min_count = 0
            device_10min_count = 0
            device_pending = []
            
            # Scan 1min MP3s in temp/
            # NOTE: 1min MP3s now use rotating slots (1min_0.mp3 - 1min_9.mp3) without timestamps
            # Skip scanning 1min files - they're ephemeral and handled via inotify in real-time
            # Backlog recovery uses 10min chunks instead
            
            # Scan 10min MP3s in hour folders
            for hour in range(24):
                audio_dir = os.path.join(audio_cold, str(hour))
                if not os.path.exists(audio_dir):
                    continue
                
                for mp3_file in os.listdir(audio_dir):
                    if mp3_file.startswith('chunk_10min_') and mp3_file.endswith('.mp3'):
                        chunk_index = int(mp3_file.replace('chunk_10min_', '').replace('.mp3', ''))
                        transcript_path = os.path.join(transcript_base, str(hour), f'chunk_10min_{chunk_index}.json')
                        
                        if not os.path.exists(transcript_path):
                            mp3_path = os.path.join(audio_dir, mp3_file)
                            mtime = os.path.getmtime(mp3_path)
                            device_pending.append((mtime, '10min', device_folder, mp3_path, hour, chunk_index, mp3_file))
                            device_10min_count += 1
            
            # Log scan results per device
            if device_pending:
                logger.info(f"{CYAN}[SCAN] 📁 [{device_folder}] Found {device_1min_count} x 1min + {device_10min_count} x 10min = {len(device_pending)} backlog items{RESET}")
            else:
                logger.info(f"{CYAN}[SCAN] ✓ [{device_folder}] No backlog - all transcripts up to date{RESET}")
            
            all_pending.extend(device_pending)
        
        # Sort by modification time (oldest first) and limit to 10
        all_pending.sort(key=lambda x: x[0])
        limited_pending = all_pending[:10]
        
        if limited_pending:
            logger.info(f"{CYAN}[SCAN] {'─' * 80}{RESET}")
            logger.info(f"{CYAN}[SCAN] 📦 Total {len(all_pending)} backlog items found, queuing oldest 10:{RESET}")
            for idx, (mtime, type_label, device_folder, mp3_path, hour, chunk_index, mp3_file) in enumerate(limited_pending, 1):
                age_minutes = int((time.time() - mtime) / 60)
                logger.info(f"{CYAN}[SCAN]   {idx:2d}. [{device_folder}] {type_label:5s} {mp3_file} (age: {age_minutes}min){RESET}")
                
                # Add to scan queue
                if type_label == '1min':
                    self.scan_queue.put((device_folder, mp3_path, hour, chunk_index))
                else:  # 10min
                    self.scan_queue.put((device_folder, hour, chunk_index))
            
            logger.info(f"{CYAN}[SCAN] ✓ Queued {len(limited_pending)} items to scan_queue (FIFO order){RESET}")
        else:
            logger.info(f"{CYAN}[SCAN] ✓ No backlog across all devices - system fully up to date{RESET}")
        
        logger.info(f"{CYAN}{'=' * 80}{RESET}")
    
    def _start_transcription_worker(self):
        """Start single transcription worker"""
        worker = threading.Thread(target=self._transcription_worker, daemon=True)
        worker.start()
        logger.info("Transcription worker started")
    
    def _transcription_worker(self):
        """Process MP3 transcription with dual-queue priority (inotify > scan)"""
        last_heartbeat = time.time()
        heartbeat_interval = 60
        
        while True:
            try:
                item = None
                source_queue = None
                
                # Priority 1: Check inotify queue (real-time events)
                try:
                    item = self.inotify_queue.get_nowait()
                    source_queue = 'inotify'
                except queue.Empty:
                    # Priority 2: If inotify empty, check scan queue (backlog)
                    try:
                        item = self.scan_queue.get(timeout=5)
                        source_queue = 'scan'
                    except queue.Empty:
                        # Both queues empty - heartbeat check
                        if time.time() - last_heartbeat > heartbeat_interval:
                            inotify_size = self.inotify_queue.qsize()
                            scan_size = self.scan_queue.qsize()
                            logger.info(f"[TRANSCRIPTION] ❤️  Heartbeat: queues[inotify={inotify_size}, scan={scan_size}] - Idle, waiting for MP3s...")
                            last_heartbeat = time.time()
                        continue
                
                if item is None:
                    continue
                
                last_heartbeat = time.time()
                
                # Get current queue sizes for logging
                inotify_size = self.inotify_queue.qsize()
                scan_size = self.scan_queue.qsize()
                queue_status = f"queues[inotify={inotify_size}, scan={scan_size}]"
                
                # Debug: log what item we picked up
                logger.debug(f"[TRANSCRIPTION] Picked up item (len={len(item)}) from {source_queue}: {item}")
                
                if len(item) == 3:
                    # 10min MP3 chunk
                    device_folder, hour, chunk_index = item
                    
                    from shared.src.lib.utils.storage_path_utils import get_cold_storage_path
                    audio_cold = get_cold_storage_path(device_folder, 'audio')
                    mp3_path = os.path.join(audio_cold, str(hour), f'chunk_10min_{chunk_index}.mp3')
                    
                    if os.path.exists(mp3_path):
                        # Early silence check BEFORE loading Whisper (avoid wasting CPU on silent MP3s)
                        logger.info(f"[{device_folder}] 🎵 Checking 10min: {hour}h/chunk_{chunk_index} (source={source_queue}, {queue_status})")
                        has_audio, mean_volume_db = check_mp3_has_audio(mp3_path, device_folder, sample_duration=5.0)
                        
                        if not has_audio:
                            logger.info(f"[{device_folder}] ⏭️  SKIPPED 10min chunk (silent: {mean_volume_db:.1f}dB) - no Whisper needed")
                        else:
                            logger.info(f"[{device_folder}] ✅ Audio detected ({mean_volume_db:.1f}dB), starting Whisper transcription...")
                            minute_results = transcribe_mp3_chunk_progressive(mp3_path, device_folder, hour, chunk_index)
                            for minute_data in minute_results:
                                merge_minute_to_chunk(device_folder, hour, chunk_index, minute_data, has_mp3=True)
                    else:
                        logger.warning(f"[{device_folder}] ⚠️  10min MP3 not found: {mp3_path}")
                
                elif len(item) == 4:
                    # 1min MP3 segment (only created when audio detected, so no silence check needed)
                    device_folder, mp3_path, hour, chunk_index = item
                    
                    logger.info(f"[{device_folder}] 📋 Processing 1min MP3: {mp3_path}")
                    
                    if os.path.exists(mp3_path):
                        # Extract slot number from filename (1min_0.mp3 → slot 0)
                        slot = int(Path(mp3_path).stem.replace('1min_', ''))
                        minute_offset = slot  # Slot number IS the minute offset within the 10min chunk
                        logger.info(f"[{device_folder}] 🎵 Transcribing 1min: {hour}h/chunk_{chunk_index}/minute_{minute_offset} (source={source_queue}, {queue_status})")
                        
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
                            
                            # Generate 1-minute dubbed audio immediately (fast accessibility!)
                            if len(transcript) > 20:  # Only dub if substantial content
                                generate_1min_dubbed_audio(device_folder, mp3_path, transcript, slot, hour, chunk_index)
                        else:
                            logger.info(f"[{device_folder}] ⏭️  1min MP3 returned no segments (Whisper detected silence)")
                    else:
                        logger.warning(f"[{device_folder}] ⚠️  1min MP3 not found (may have been archived): {mp3_path}")
                
                # Mark task done on appropriate queue
                if source_queue == 'inotify':
                    self.inotify_queue.task_done()
                elif source_queue == 'scan':
                    self.scan_queue.task_done()
                
            except Exception as e:
                import traceback
                logger.error(f"Transcription error: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                if source_queue == 'inotify':
                    self.inotify_queue.task_done()
                elif source_queue == 'scan':
                    self.scan_queue.task_done()
    
    
    
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
                    # Get device_id (not device_folder) for state consistency
                    device_info = get_device_info_from_capture_folder(device_folder)
                    device_id = device_info.get('device_id', device_folder)
                    
                    device_state = self.incident_manager.get_device_state(device_id)
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
                        logger.info(f"{BLUE}[AUDIO:{device_folder}] 📌 Added {len(cached_audio_r2_urls)} cached R2 URLs to detection_result (for 5min DB report){RESET}")
                
                # Clear audio_loss R2 cache when audio returns
                if has_audio and self.incident_manager:
                    # Get device_id (not device_folder) for state consistency
                    device_info = get_device_info_from_capture_folder(device_folder)
                    device_id = device_info.get('device_id', device_folder)
                    
                    device_state = self.incident_manager.get_device_state(device_id)
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
        logger.info("=" * 80)
        logger.info("Starting 1min MP3 inotify event loop...")
        logger.info(f"Watching {len(self.audio_path_to_device)} directories for IN_MOVED_TO events")
        logger.info("Ready to process 1min MP3 files (real-time priority)")
        logger.info("=" * 80)
        
        event_count = 0
        mp3_count = 0
        last_heartbeat = time.time()
        heartbeat_interval = 60  # Log every 60s
        
        try:
            for event in self.inotify.event_gen(yield_nones=True):
                if time.time() - last_heartbeat > heartbeat_interval:
                    inotify_size = self.inotify_queue.qsize()
                    scan_size = self.scan_queue.qsize()
                    logger.info(f"[INOTIFY] ❤️  Heartbeat: events={event_count}, MP3s={mp3_count}, queues[inotify={inotify_size}, scan={scan_size}]")
                    last_heartbeat = time.time()
                
                if event is None:
                    continue
                
                event_count += 1
                (_, type_names, path, filename) = event
                
                if 'IN_MOVED_TO' in type_names and filename.endswith('.mp3') and filename.startswith('1min_'):
                    device_folder = self.audio_path_to_device.get(path)
                    if device_folder:
                        mp3_path = os.path.join(path, filename)
                        
                        # Slot-based naming (1min_0.mp3 through 1min_9.mp3) - use current time for chunk location
                        # File is created in real-time, so current time is accurate (within 1 minute)
                        from shared.src.lib.utils.storage_path_utils import calculate_chunk_location
                        now = datetime.now()
                        hour, chunk_index = calculate_chunk_location(now)
                        
                        mp3_count += 1
                        self.inotify_queue.put((device_folder, mp3_path, hour, chunk_index))
                        inotify_size = self.inotify_queue.qsize()
                        scan_size = self.scan_queue.qsize()
                        logger.info(f"[INOTIFY] 🆕 1min MP3 detected: {device_folder}/{filename} (slot {filename.replace('1min_', '').replace('.mp3', '')}) → queues[inotify={inotify_size}, scan={scan_size}]")
        
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
    logger.info("Watches: 1min MP3 files in COLD /audio/temp/ (instant transcription)")
    logger.info("Scans: 1min /audio/temp/ + 10min /audio/{hour}/ (backfill/recovery)")
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
            
            logger.info(f"  ✓ Monitoring: {device_folder}")
            
            monitored_devices.append({
                'device_folder': device_folder
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
