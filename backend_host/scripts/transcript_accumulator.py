#!/usr/bin/env python3
"""
Circular 24h Transcript Accumulator
Samples audio every 6s, generates timestamped transcripts, local circular buffer
Uses audio_transcription_utils for clean, dependency-free transcription
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

from shared.src.lib.utils.storage_path_utils import get_capture_directories, get_capture_folder, get_device_info_from_capture_folder, is_ram_mode
from shared.src.lib.utils.audio_transcription_utils import transcribe_ts_segments
from shared.src.lib.utils.ai_utils import call_text_ai
from backend_host.src.lib.utils.system_info_utils import get_files_by_pattern

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/transcript_accumulator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
SAMPLE_INTERVAL = 6  # Sample every 6 seconds
MAX_DURATION_HOURS = 24
MAX_SAMPLES = (MAX_DURATION_HOURS * 3600) // SAMPLE_INTERVAL  # 14,400 samples
AI_ENHANCEMENT_BATCH = 10  # Enhance every 10 samples with AI

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

def enhance_transcripts_with_ai(segments: list, capture_folder: str) -> dict:
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

def load_hourly_transcript(stream_dir, hour_window, capture_folder):
    """Load transcript data for a specific hour window (aligned with archive manifests)"""
    # Use hot storage if RAM mode is active
    if is_ram_mode(stream_dir):
        transcript_path = os.path.join(stream_dir, 'hot', f'transcript_hour{hour_window}.json')
    else:
        transcript_path = os.path.join(stream_dir, f'transcript_hour{hour_window}.json')
    
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r') as f:
            return json.load(f)
    else:
        return {
            'capture_folder': capture_folder,
            'hour_window': hour_window,
            'sample_interval_seconds': SAMPLE_INTERVAL,
            'segments': [],
            'samples_since_ai_enhancement': 0
        }

def save_hourly_transcript(stream_dir, hour_window, transcript_data):
    """Save transcript data for a specific hour window (atomic write)"""
    # Use hot storage if RAM mode is active
    if is_ram_mode(stream_dir):
        # Ensure hot directory exists
        hot_dir = os.path.join(stream_dir, 'hot')
        os.makedirs(hot_dir, exist_ok=True)
        transcript_path = os.path.join(hot_dir, f'transcript_hour{hour_window}.json')
    else:
        transcript_path = os.path.join(stream_dir, f'transcript_hour{hour_window}.json')
    
    with open(transcript_path + '.tmp', 'w') as f:
        json.dump(transcript_data, f, indent=2)
    os.rename(transcript_path + '.tmp', transcript_path)

def cleanup_old_hourly_transcripts(stream_dir):
    """Remove hourly transcript files older than 24 hours (circular cleanup)"""
    try:
        # Use hot storage if RAM mode is active
        if is_ram_mode(stream_dir):
            search_dir = os.path.join(stream_dir, 'hot')
        else:
            search_dir = stream_dir
        
        # Use fast os.scandir (no subprocess overhead)
        transcript_files = get_files_by_pattern(search_dir, r'^transcript_hour.*\.json$')
        
        if len(transcript_files) > 24:
            # Sort by modification time and remove oldest
            transcript_files.sort(key=lambda x: os.path.getmtime(x))
            for old_file in transcript_files[:-24]:
                os.remove(old_file)
                logger.info(f"Cleaned up old transcript: {os.path.basename(old_file)}")
    except Exception as e:
        logger.warning(f"Failed to cleanup old transcripts: {e}")

def update_transcript_buffer(capture_dir, max_samples_per_run=1):
    """Update transcript buffer with new samples (hourly files aligned with archive manifests)
    
    Args:
        capture_dir: Path to capture directory
        max_samples_per_run: Maximum number of samples to process in one call (for alternating between devices)
    
    Returns:
        bool: True if samples were processed, False if nothing to process
    """
    start_time = time.time()
    try:
        capture_folder = get_capture_folder(capture_dir)
        stream_dir = capture_dir.replace('/captures', '')
        
        # Load global state (track last processed segment across all hours)
        # Use hot storage if RAM mode is active
        if is_ram_mode(stream_dir):
            hot_dir = os.path.join(stream_dir, 'hot')
            os.makedirs(hot_dir, exist_ok=True)
            state_path = os.path.join(hot_dir, 'transcript_state.json')
        else:
            state_path = os.path.join(stream_dir, 'transcript_state.json')
        
        if os.path.exists(state_path):
            with open(state_path, 'r') as f:
                state = json.load(f)
        else:
            state = {'last_processed_segment': 0}
        
        last_processed = state.get('last_processed_segment', 0)
        
        # First run: Start 6 segments back to get immediate feedback
        if last_processed == 0:
            # Use fast os.scandir (no subprocess overhead, no timeout risk)
            segment_files = get_files_by_pattern(stream_dir, r'^segment_.*\.ts$')
            
            if segment_files:
                latest_seg = max(int(os.path.basename(f).split('_')[1].split('.')[0]) for f in segment_files)
                # Start 6 segments back for immediate processing (1 sample = 6 segments)
                start_offset = 6
                last_processed = max(0, latest_seg - start_offset)
                logger.info(f"[{capture_folder}] 🆕 First run - starting from segment #{last_processed} (6 segments back from #{latest_seg})")
                state['last_processed_segment'] = last_processed
        
        # Find available segments using fast os.scandir (no subprocess overhead, no timeout risk)
        segment_files = get_files_by_pattern(stream_dir, r'^segment_.*\.ts$')
        if not segment_files:
            logger.debug(f"[{capture_folder}] No segment files found")
            return False
        
        # Get all segments and find new ones to process
        all_segment_nums = []
        segment_map = {}
        for seg_file in segment_files:
            seg_num = int(os.path.basename(seg_file).split('_')[1].split('.')[0])
            all_segment_nums.append(seg_num)
            segment_map[seg_num] = seg_file
        
        all_segment_nums.sort()
        
        # Find segments to sample (every 6th segment interval, but merge 6 segments per sample)
        segments_to_process = []
        for seg_num in all_segment_nums:
            if seg_num > last_processed and seg_num % SAMPLE_INTERVAL == 0:
                # Collect 6 consecutive segments ending at this segment
                batch = []
                for i in range(SAMPLE_INTERVAL):
                    batch_seg_num = seg_num - SAMPLE_INTERVAL + 1 + i
                    if batch_seg_num in segment_map:
                        batch.append((batch_seg_num, segment_map[batch_seg_num]))
                
                if batch:  # Only process if we have segments in the batch
                    segments_to_process.append((seg_num, batch))  # (target_seg_num, list_of_6_segments)
        
        if not segments_to_process:
            # No new segments to process
            logger.debug(f"[{capture_folder}] No new samples (waiting for seg after #{last_processed})")
            return False
        
        # Limit processing to max_samples_per_run (for alternating between devices)
        total_pending = len(segments_to_process)
        segments_to_process = segments_to_process[:max_samples_per_run]
        
        # Visual separator for readability
        logger.info("=" * 80)
        
        if total_pending > max_samples_per_run:
            logger.info(f"[{capture_folder}] 🔄 Processing {len(segments_to_process)}/{total_pending} samples (alternating with other devices)...")
        else:
            logger.info(f"[{capture_folder}] 🔄 Processing {len(segments_to_process)} new samples (6 segments per sample)...")
        
        # Group segments by hour window (aligned with archive manifests)
        segments_by_hour = {}
        for segment_num, segment_batch in segments_to_process:
            relative_seconds = segment_num
            hour_window = (relative_seconds // 3600) + 1  # 1-24
            
            if hour_window not in segments_by_hour:
                segments_by_hour[hour_window] = []
            segments_by_hour[hour_window].append((segment_num, segment_batch))
        
        # Process each hour separately
        for hour_window in sorted(segments_by_hour.keys()):
            hour_segments = segments_by_hour[hour_window]
            logger.info(f"[{capture_folder}] Processing {len(hour_segments)} samples for hour window {hour_window}")
            
            # Load hourly transcript file
            transcript_data = load_hourly_transcript(stream_dir, hour_window, capture_folder)
            existing_segments = {s['segment_num']: s for s in transcript_data.get('segments', [])}
            
            # Process new samples for this hour
            for segment_num, segment_batch in hour_segments:
                # Extract TS file paths from batch
                ts_file_paths = [seg_path for _, seg_path in segment_batch]
                
                # Start timing
                seg_start_time = time.time()
                
                # Calculate total size of files being merged
                total_size = sum(os.path.getsize(f) for f in ts_file_paths if os.path.exists(f))
                
                # Transcribe merged segments
                logger.info(f"[{capture_folder}] 🎬 seg#{segment_num} (hour{hour_window}): Merged {len(segment_batch)} TS files ({total_size} bytes)")
                result = transcribe_ts_segments(ts_file_paths, merge=True, model_name='tiny', device_id=capture_folder)
                
                transcript = result.get('transcript', '').strip()
                language = result.get('language', 'unknown')
                confidence = result.get('confidence', 0.0)
                skipped = result.get('skipped', False)
                seg_elapsed = time.time() - seg_start_time
                
                relative_seconds = segment_num
                
                existing_segments[segment_num] = {
                    'segment_num': segment_num,
                    'relative_seconds': relative_seconds,
                    'language': language,
                    'transcript': transcript,
                    'confidence': confidence,
                    'hour_window': hour_window,
                    'segments_merged': len(segment_batch)
                }
                
                # Compact logging
                if transcript:
                    # logger.info(f"[{capture_folder}] 📝 Language: {language} | Confidence: {confidence:.2f} | Duration: {seg_elapsed:.1f}s")
                    # logger.info(f"[{capture_folder}] 💬 '{transcript}'")
                elif skipped:
                    logger.info(f"[{capture_folder}] 🔇 Silent (Whisper skipped) | Duration: {seg_elapsed:.1f}s")
                else:
                    logger.info(f"[{capture_folder}] 🔇 No speech detected | Duration: {seg_elapsed:.1f}s")
            
            # Sort segments for this hour
            all_segments = sorted(existing_segments.values(), key=lambda x: x['segment_num'])
            
            # AI Enhancement: Every 10 new samples for this hour
            samples_since_enhancement = transcript_data.get('samples_since_ai_enhancement', 0)
            samples_since_enhancement += len(hour_segments)
            
            if samples_since_enhancement >= AI_ENHANCEMENT_BATCH:
                # Get the last 10 segments with transcripts for enhancement
                segments_to_enhance = [seg for seg in all_segments[-AI_ENHANCEMENT_BATCH:] if seg.get('transcript', '').strip()]
                
                if segments_to_enhance:
                    enhanced_map = enhance_transcripts_with_ai(segments_to_enhance, capture_folder)
                    
                    # Apply enhanced transcripts back to segments
                    if enhanced_map:
                        for seg in all_segments:
                            seg_num = seg['segment_num']
                            if seg_num in enhanced_map:
                                seg['enhanced_transcript'] = enhanced_map[seg_num]
                                original = seg.get('transcript', '')[:40]
                                enhanced = enhanced_map[seg_num][:40]
                                # logger.info(f"[{capture_folder}] 🔵 seg#{seg_num} Enhanced:")
                                # logger.info(f"[{capture_folder}]    Original: '{original}...'")
                                # logger.info(f"[{capture_folder}]    Enhanced: '{enhanced}...'")
                
                # Reset counter
                samples_since_enhancement = 0
            
            # Update and save hourly transcript data
            transcript_data['capture_folder'] = capture_folder
            transcript_data['hour_window'] = hour_window
            transcript_data['sample_interval_seconds'] = SAMPLE_INTERVAL
            transcript_data['segments'] = all_segments
            transcript_data['last_update'] = datetime.now().isoformat()
            transcript_data['total_samples'] = len(all_segments)
            transcript_data['samples_since_ai_enhancement'] = samples_since_enhancement
            
            # Save this hour's transcript file
            save_hourly_transcript(stream_dir, hour_window, transcript_data)
            
            # Count how many segments have enhanced transcripts
            enhanced_count = sum(1 for seg in all_segments if seg.get('enhanced_transcript'))
            logger.info(f"[{capture_folder}] ✅ Saved transcript_hour{hour_window}.json: {len(all_segments)} samples ({enhanced_count} enhanced)")
        
        # Update global state
        state['last_processed_segment'] = segments_to_process[-1][0] if segments_to_process else last_processed
        with open(state_path + '.tmp', 'w') as f:
            json.dump(state, f, indent=2)
        os.rename(state_path + '.tmp', state_path)
        
        # Cleanup old hourly transcripts (keep last 24 hours)
        cleanup_old_hourly_transcripts(stream_dir)
        
        elapsed = time.time() - start_time
        
        # Summary: count total enhanced transcripts across all processed hours
        total_enhanced = 0
        for hour_window in sorted(segments_by_hour.keys()):
            transcript_data = load_hourly_transcript(stream_dir, hour_window, capture_folder)
            total_enhanced += sum(1 for seg in transcript_data.get('segments', []) if seg.get('enhanced_transcript'))
        
        logger.info(f"[{capture_folder}] ✅ Processed {len(segments_to_process)} new samples across {len(segments_by_hour)} hour window(s) [{elapsed:.2f}s]")
        if total_enhanced > 0:
            logger.info(f"[{capture_folder}] 🔵 Total AI-enhanced transcripts in processed hours: {total_enhanced}")
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{capture_folder}] ❌ Error updating transcript buffer: {e} [{elapsed:.2f}s]")
        return False

def main():
    cleanup_logs_on_startup()  # Clean log on startup
    
    logger.info("Starting Transcript Accumulator (6s sampling, 24h circular buffer)...")
    logger.info("Using audio_transcription_utils (clean, no dependencies)...")
    
    try:
        capture_dirs = get_capture_directories()
        logger.info(f"Found {len(capture_dirs)} capture directories")
        
        # Filter out host device from monitored directories (no audio capture)
        # Uses lightweight device mapping without loading incidents from DB
        monitored_devices = []
        for capture_dir in capture_dirs:
            capture_folder = get_capture_folder(capture_dir)
            device_info = get_device_info_from_capture_folder(capture_folder)
            device_id = device_info.get('device_id', capture_folder)
            is_host = (device_id == 'host')
            
            logger.info(f"  [{capture_folder}] device_id={device_id}, is_host={is_host}")
            
            if is_host:
                logger.info(f"  ⊗ Skipping: {capture_dir} -> {capture_folder} (host has no audio)")
            else:
                logger.info(f"  ✓ Monitoring: {capture_dir} -> {capture_folder}")
                monitored_devices.append(capture_dir)
        
        # Whisper model will be loaded on first use and cached globally
        logger.info("✓ Whisper model will be loaded on first transcription (global singleton cache)")
        
        logger.info(f"Monitoring {len(monitored_devices)} devices for transcripts (excluding host)")
        logger.info("Processing strategy: Continuous loop, process when 10 new segments available")
        
        while True:
            any_processed = False
            
            for i, capture_dir in enumerate(monitored_devices, 1):
                capture_folder = get_capture_folder(capture_dir)
                logger.debug(f"[{capture_folder}] Checking for new transcript samples... ({i}/{len(monitored_devices)})")
                # Process 1 sample at a time to alternate between devices
                # Returns True if processed, False if nothing to process
                was_processed = update_transcript_buffer(capture_dir, max_samples_per_run=1)
                if was_processed:
                    any_processed = True
            
            # If no device had anything to process, sleep briefly to avoid CPU spin
            if not any_processed:
                logger.debug(f"⏸️  No devices ready, sleeping 1s...")
                time.sleep(1)
            
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise

if __name__ == '__main__':
    main()

