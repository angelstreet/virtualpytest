#!/usr/bin/env python3
"""
10-Minute Transcript Accumulator
Watches for 10min MP3 chunks created by hot_cold_archiver, transcribes them with Whisper
Perfect alignment: chunk_10min_X.mp4 + chunk_10min_X.mp3 + chunk_10min_X.json
Zero duplicate work - audio already extracted by archiver
"""
import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime


script_dir = os.path.dirname(os.path.abspath(__file__))
backend_host_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(backend_host_dir)
sys.path.insert(0, project_root)

from shared.src.lib.utils.storage_path_utils import get_capture_base_directories, get_capture_storage_path, get_capture_folder, get_device_info_from_capture_folder, is_ram_mode, get_device_base_path
from shared.src.lib.utils.ai_utils import call_text_ai
from backend_host.src.lib.utils.system_info_utils import get_files_by_pattern

# Logging will be configured in main() after cleanup_logs_on_startup()
logger = logging.getLogger(__name__)

# Configuration
CHUNK_DURATION_MINUTES = 10  # Process 10-minute audio chunks
CHECK_INTERVAL = 10  # Check for new MP3 chunks every 10 seconds
AI_ENHANCEMENT_ENABLED = False  # Disable AI enhancement to reduce CPU load

def cleanup_logs_on_startup():
    """Clean up log file on service restart for fresh debugging"""
    try:
        log_file = '/tmp/transcript_accumulator.log'
        
        print(f"[@transcript_accumulator] Cleaning log on service restart...")
        
        if os.path.exists(log_file):
            # Truncate the file instead of deleting to avoid permission issues
            with open(log_file, 'w') as f:
                f.write(f"=== LOG CLEANED ON SERVICE RESTART: {datetime.now().isoformat()} ===\n")
            print(f"[@transcript_accumulator] ✓ Cleaned: {log_file}")
        else:
            print(f"[@transcript_accumulator] ○ Not found (will be created): {log_file}")
                
        print(f"[@transcript_accumulator] Log cleanup complete - fresh logs for debugging")
                
    except Exception as e:
        print(f"[@transcript_accumulator] Warning: Could not clean log file: {e}")

def transcribe_mp3_chunk(mp3_path: str, capture_folder: str, hour: int, chunk_index: int) -> dict:
    """
    Transcribe a single 10-minute MP3 chunk using Whisper
    
    Args:
        mp3_path: Path to MP3 file (chunk_10min_X.mp3)
        capture_folder: Device identifier
        hour: Hour (0-23)
        chunk_index: Chunk within hour (0-5)
    
    Returns:
        dict: Transcript data with segments
    """
    try:
        logger.info(f"[{capture_folder}] 🎬 Transcribing chunk_10min_{chunk_index}.mp3 (hour {hour})")
        start_time = time.time()
        
        # Use audio_transcription_utils to transcribe MP3
        from shared.src.lib.utils.audio_transcription_utils import transcribe_audio_file
        
        result = transcribe_audio_file(mp3_path, model_name='tiny', device_id=capture_folder)
        
        transcript = result.get('transcript', '').strip()
        language = result.get('language', 'unknown')
        confidence = result.get('confidence', 0.0)
        elapsed = time.time() - start_time
        
        logger.info(f"[{capture_folder}] 📝 Language: {language} | Confidence: {confidence:.2f} | Duration: {elapsed:.1f}s")
        if transcript:
            # Show first 200 chars of transcript
            preview = transcript[:200] + ('...' if len(transcript) > 200 else '')
            logger.info(f"[{capture_folder}] 💬 '{preview}'")
        else:
            logger.info(f"[{capture_folder}] 🔇 No speech detected in chunk")
        
        # Build transcript data structure
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
            'mp3_file': os.path.basename(mp3_path)
        }
        
        return transcript_data
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Error transcribing MP3 chunk: {e}")
        return None

def enhance_transcripts_with_ai_old(segments: list, capture_folder: str) -> dict:
    """
    Enhance Whisper transcripts using AI for better accuracy.
    Takes a batch of segments and returns enhanced transcripts.
    
    Args:
        segments: List of segment dicts with 'transcript', 'language', etc.
        capture_folder: Device identifier for logging
    
    Returns:
        dict: Map of segment_num -> enhanced_transcript
    """
    try:
        if not segments:
            return {}
        
        # Build transcript list with language specified per line
        transcripts_text = []
        segment_info = []  # Keep track for JSON template
        
        for seg in segments:
            seg_num = seg.get('segment_num', 0)
            transcript = seg.get('transcript', '').strip()
            language = seg.get('language', 'unknown')
            
            if transcript:
                transcripts_text.append(f"- {language}: {transcript}")
                segment_info.append({'seg_num': seg_num, 'language': language})
        
        if not transcripts_text:
            logger.info(f"[{capture_folder}] No transcripts to enhance (all silent)")
            return {}
        
        combined = "\n".join(transcripts_text)
        
        # Build segment list for JSON template (show first 2 as examples)
        segment_examples = []
        for info in segment_info[:2]:
            segment_examples.append(f'{{"segment_num":{info["seg_num"]},"enhanced_text":"improved text here"}}')
        
        # AI enhancement prompt - focused on accuracy improvement with strict JSON format
        prompt = f"""CONTEXT: You are improving audio-to-text transcriptions from Whisper AI.

IMPORTANT: These are {len(segment_info)} consecutive 6-second audio segments (total ~{len(segment_info)*6} seconds of continuous audio).
They are part of the same conversation or program on TV. Read ALL segments first to understand the full context, then improve each one.

HOW TO PROCESS:
1. Read all {len(segment_info)} segments below to understand the complete context
2. Use context from previous and next segments to improve each transcript
3. Look for patterns across segments to fix errors more accurately
4. Maintain conversation flow and coherence across all segments

Transcripts to improve (consecutive 10s segments, language specified per line):
{combined}

ENHANCEMENT RULES:
1. Fix speech-to-text errors using context from ALL segments
2. Improve grammar and coherence while considering the full conversation
3. KEEP THE ORIGINAL LANGUAGE - DO NOT TRANSLATE (French stays French, English stays English)
4. Use surrounding segments to disambiguate unclear words
5. If text is repetitive or garbled, infer meaning from context
6. Keep responses concise and natural
7. Only improve when needed - if text is already good, keep it similar

Return ONLY valid JSON with ALL {len(segment_info)} segments (no markdown, no explanations):
{{"enhanced":[{segment_examples[0]},{segment_examples[1] if len(segment_examples) > 1 else '...'},...all {len(segment_info)} segments]}}

CRITICAL: Use full context. Return valid JSON only. Respect each segment's language. Escape special characters."""
        
        logger.info(f"[{capture_folder}] 🤖 Enhancing {len(segments)} transcripts with AI...")
        # logger.info(f"[{capture_folder}] 📋 AI Enhancement Prompt:")
        # logger.info("-" * 80)
        # logger.info(prompt)
        # logger.info("-" * 80)
        
        # Call AI with higher token limit to avoid truncation
        result = call_text_ai(prompt, max_tokens=1500, temperature=0.1)
        
        # logger.info(f"[{capture_folder}] 📨 AI Response (success={result.get('success')}):")
        # if result.get('success'):
        #     logger.info(f"[{capture_folder}] Response length: {len(result.get('content', ''))} chars")
        # else:
        #     logger.info(f"[{capture_folder}] Error: {result.get('error', 'Unknown')}")
        
        if not result['success']:
            logger.warning(f"[{capture_folder}] AI enhancement failed: {result.get('error', 'Unknown error')}")
            return {}
        
        # Parse AI response with robust error handling
        content = result['content'].strip()
        
        # Clean up content for logging (remove excessive empty lines)
        import re
        content_for_logging = re.sub(r'\n{3,}', '\n\n', content)  # Replace 3+ newlines with just 2
        
        # logger.info(f"[{capture_folder}] 📄 Full AI Response ({len(content)} chars, cleaned for display):")
        # logger.info("-" * 80)
        # logger.info(content_for_logging)
        # logger.info("-" * 80)
        
        # Remove markdown code blocks and extra text
        if '```json' in content:
            # Extract JSON from markdown block
            json_start = content.find('```json') + 7
            json_end = content.find('```', json_start)
            if json_end > json_start:
                content = content[json_start:json_end].strip()
        elif '```' in content:
            json_start = content.find('```') + 3
            json_end = content.find('```', json_start)
            if json_end > json_start:
                content = content[json_start:json_end].strip()
        
        # Find JSON object boundaries if there's extra text
        if not content.startswith('{'):
            json_start = content.find('{')
            if json_start >= 0:
                content = content[json_start:]
        
        if not content.endswith('}'):
            json_end = content.rfind('}')
            if json_end >= 0:
                content = content[:json_end + 1]
        
        # Sanitize content: replace invalid control characters
        # Common issues: unescaped newlines, tabs, and control chars in text
        import re
        # Replace literal newlines/tabs/control chars with spaces in text values
        # But keep the JSON structure intact
        def sanitize_text_value(match):
            text = match.group(0)
            # Replace control characters with spaces
            sanitized = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
            return sanitized
        
        # Apply sanitization only to text inside quotes (preserve JSON structure)
        try:
            # Simple approach: replace control chars everywhere except valid JSON escapes
            content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', ' ', content)
        except Exception as sanitize_error:
            logger.warning(f"[{capture_folder}] Sanitization error: {sanitize_error}")
        
        try:
            ai_result = json.loads(content)
            enhanced_map = {}
            
            for item in ai_result.get('enhanced', []):
                seg_num = item.get('segment_num')
                enhanced_text = item.get('enhanced_text', '').strip()
                
                if seg_num is not None and enhanced_text:
                    # Skip obviously truncated or repetitive text (likely AI token limit hit)
                    if len(enhanced_text) > 500 or enhanced_text.count(',') > 50:
                        logger.warning(f"[{capture_folder}] ⚠️ Skipping seg#{seg_num} - enhanced text appears truncated/repetitive")
                        continue
                    enhanced_map[seg_num] = enhanced_text
            
            if enhanced_map:
                logger.info(f"[{capture_folder}] ✅ AI enhanced {len(enhanced_map)}/{len(segments)} transcripts")
            else:
                logger.warning(f"[{capture_folder}] ⚠️ No valid enhancements (all skipped or empty)")
            return enhanced_map
            
        except json.JSONDecodeError as e:
            logger.error(f"[{capture_folder}] ❌ JSON parsing failed: {e}")
            # logger.error(f"[{capture_folder}] Error position: {e.lineno if hasattr(e, 'lineno') else 'unknown'}:{e.colno if hasattr(e, 'colno') else 'unknown'}")
            # logger.error(f"[{capture_folder}] Problematic content around error:")
            # # Show 200 chars before and after the error position
            # if hasattr(e, 'pos') and e.pos:
            #     start = max(0, e.pos - 200)
            #     end = min(len(content), e.pos + 200)
            #     logger.error(f"[{capture_folder}] ...{content[start:end]}...")
            # logger.warning(f"[{capture_folder}] 💡 Possible causes:")
            # logger.warning(f"[{capture_folder}]    1. AI token limit truncation (try reducing batch size)")
            # logger.warning(f"[{capture_folder}]    2. Unescaped special characters in response")
            # logger.warning(f"[{capture_folder}]    3. AI didn't follow JSON format")
            return {}
    
    except Exception as e:
        logger.error(f"[{capture_folder}] AI enhancement error: {e}")
        return {}

def save_transcript_chunk(device_base_path: str, hour: int, chunk_index: int, transcript_data: dict):
    """
    Save transcript JSON file aligned with MP4/MP3 chunks
    
    Args:
        device_base_path: Device base path (/var/www/html/stream/capture1)
        hour: Hour (0-23)
        chunk_index: Chunk index (0-5)
        transcript_data: Transcript data to save
    """
    # Save to cold storage (transcripts don't need hot RAM storage)
    transcript_dir = os.path.join(device_base_path, 'transcript', str(hour))
    os.makedirs(transcript_dir, exist_ok=True)
    
    transcript_path = os.path.join(transcript_dir, f'chunk_10min_{chunk_index}.json')
    
    # Atomic write
    with open(transcript_path + '.tmp', 'w') as f:
        json.dump(transcript_data, f, indent=2)
    os.rename(transcript_path + '.tmp', transcript_path)
    
    logger.info(f"✅ Saved: /transcript/{hour}/chunk_10min_{chunk_index}.json")

def process_mp3_chunks(capture_dir):
    """
    Watch for new 10-minute MP3 chunks and transcribe them
    
    Args:
        capture_dir: Path to captures directory
    
    Returns:
        bool: True if chunks were processed, False if nothing to process
    """
    try:
        # Use centralized path utilities
        capture_folder = get_capture_folder(capture_dir)
        device_base_path = get_device_base_path(capture_folder)
        
        # Determine where MP3 chunks are located (in hour folders)
        if is_ram_mode(device_base_path):
            audio_base_dir = os.path.join(device_base_path, 'hot', 'audio')
            state_path = os.path.join(device_base_path, 'hot', 'transcript_state.json')
        else:
            audio_base_dir = os.path.join(device_base_path, 'audio')
            state_path = os.path.join(device_base_path, 'transcript_state.json')
        
        if not os.path.exists(audio_base_dir):
            logger.debug(f"[{capture_folder}] Audio base directory does not exist: {audio_base_dir}")
            return False
        
        # Load state (track which chunks have been transcribed)
        if os.path.exists(state_path):
            with open(state_path, 'r') as f:
                state = json.load(f)
        else:
            state = {'processed_chunks': {}}
            logger.info(f"[{capture_folder}] 🆕 First run - watching for MP3 chunks in: {audio_base_dir}/{hour}/")
        
        processed_chunks = state.get('processed_chunks', {})
        
        # Find all MP3 chunks in all hour folders (0-23)
        mp3_files = []
        for hour in range(24):
            hour_dir = os.path.join(audio_base_dir, str(hour))
            if os.path.exists(hour_dir):
                hour_files = get_files_by_pattern(hour_dir, r'^chunk_10min_\d+\.mp3$')
                mp3_files.extend(hour_files)
        
        if not mp3_files:
            logger.debug(f"[{capture_folder}] No MP3 chunks found yet in hour folders")
            return False
        
        # Process new chunks
        new_chunks_processed = 0
        
        for mp3_path in mp3_files:
            mp3_filename = os.path.basename(mp3_path)
            
            # Extract hour from path (/audio/{hour}/chunk_10min_X.mp3)
            hour_folder = os.path.basename(os.path.dirname(mp3_path))
            try:
                hour = int(hour_folder)
            except ValueError:
                logger.warning(f"[{capture_folder}] Invalid hour folder: {hour_folder}")
                continue
            
            # Create unique key with hour for tracking (since chunk_index resets per hour)
            mp3_key = f"{hour}/{mp3_filename}"
            
            # Skip if already processed
            if mp3_key in processed_chunks:
                continue
            
            # Extract chunk index from filename (chunk_10min_0.mp3 → 0)
            try:
                chunk_index = int(mp3_filename.replace('chunk_10min_', '').replace('.mp3', ''))
            except ValueError:
                logger.warning(f"[{capture_folder}] Invalid MP3 filename: {mp3_filename}")
                continue
            
            logger.info("=" * 80)
            logger.info(f"[{capture_folder}] 🎵 New MP3 chunk detected: {mp3_filename}")
            
            # Transcribe MP3 chunk
            transcript_data = transcribe_mp3_chunk(mp3_path, capture_folder, hour, chunk_index)
            
            if transcript_data:
                # Save transcript JSON
                save_transcript_chunk(device_base_path, hour, chunk_index, transcript_data)
                
                # Mark as processed (using hour/filename key)
                processed_chunks[mp3_key] = {
                    'timestamp': datetime.now().isoformat(),
                    'hour': hour,
                    'chunk_index': chunk_index,
                    'mp3_path': mp3_path
                }
                new_chunks_processed += 1
                
                logger.info(f"[{capture_folder}] ✅ Transcription complete for hour {hour}, chunk {chunk_index}")
            else:
                logger.warning(f"[{capture_folder}] ⚠️ Transcription failed for {mp3_key}")
            
            logger.info("=" * 80)
        
        # Save state
        if new_chunks_processed > 0:
            state['processed_chunks'] = processed_chunks
            state['last_update'] = datetime.now().isoformat()
            
            with open(state_path + '.tmp', 'w') as f:
                json.dump(state, f, indent=2)
            os.rename(state_path + '.tmp', state_path)
            
            logger.info(f"[{capture_folder}] 💾 Processed {new_chunks_processed} new chunk(s)")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"[{capture_folder}] ❌ Error processing MP3 chunks: {e}")
        return False

def main():
    # Clean log file first
    cleanup_logs_on_startup()
    
    # Configure logging (systemd handles file output via StandardOutput directive)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()],
        force=True  # Override any existing configuration
    )
    
    logger.info("Starting 10-Minute Transcript Accumulator")
    logger.info("Logging to: /tmp/transcript_accumulator.log (via systemd) and journalctl")
    logger.info("Watches for MP3 chunks created by hot_cold_archiver (zero duplicate merging)")
    logger.info("Perfect alignment: chunk_10min_X.mp4 + chunk_10min_X.mp3 + chunk_10min_X.json")
    
    try:
        # Get base directories and resolve hot/cold paths automatically
        base_dirs = get_capture_base_directories()
        logger.info(f"Found {len(base_dirs)} capture base directories")
        
        # Filter out host device from monitored directories (no audio capture)
        # Uses lightweight device mapping without loading incidents from DB
        monitored_devices = []
        for base_dir in base_dirs:
            # Extract device folder name (e.g., 'capture1' from '/var/www/html/stream/capture1')
            device_folder = os.path.basename(base_dir)
            # Use centralized path resolution (handles hot/cold automatically)
            capture_dir = get_capture_storage_path(device_folder, 'captures')
            
            device_info = get_device_info_from_capture_folder(device_folder)
            device_id = device_info.get('device_id', device_folder)
            is_host = (device_id == 'host')
            
            storage_type = "HOT (RAM)" if '/hot/' in capture_dir else "COLD (SD)"
            logger.info(f"  [{device_folder}] device_id={device_id}, is_host={is_host}, storage={storage_type}")
            
            if is_host:
                logger.info(f"  ⊗ Skipping: {capture_dir} -> {device_folder} (host has no audio)")
            else:
                logger.info(f"  ✓ Monitoring [{storage_type}]: {capture_dir} -> {device_folder}")
                monitored_devices.append(capture_dir)
        
        # Whisper model will be loaded on first use and cached globally
        logger.info("✓ Whisper model will be loaded on first transcription (global singleton cache)")
        
        logger.info(f"Monitoring {len(monitored_devices)} devices for MP3 chunks (excluding host)")
        logger.info(f"Check interval: {CHECK_INTERVAL}s (waiting for hot_cold_archiver to create MP3 chunks)")
        
        while True:
            any_processed = False
            
            for i, capture_dir in enumerate(monitored_devices, 1):
                capture_folder = get_capture_folder(capture_dir)
                logger.debug(f"[{capture_folder}] Checking for new MP3 chunks... ({i}/{len(monitored_devices)})")
                
                # Process new MP3 chunks
                was_processed = process_mp3_chunks(capture_dir)
                if was_processed:
                    any_processed = True
            
            # If no device had new chunks, sleep until next check
            if not any_processed:
                logger.debug(f"⏸️  No new MP3 chunks, sleeping {CHECK_INTERVAL}s...")
            
            time.sleep(CHECK_INTERVAL)
            
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise

if __name__ == '__main__':
    main()

