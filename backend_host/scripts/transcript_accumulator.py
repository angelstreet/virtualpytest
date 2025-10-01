#!/usr/bin/env python3
"""
Circular 24h Transcript Accumulator
Samples audio every 10s, generates timestamped transcripts, local circular buffer
Uses audio_transcription_utils for clean, dependency-free transcription
"""
import os
import sys
import json
import time
import glob
import logging
from datetime import datetime
from archive_utils import get_capture_directories, get_capture_folder, get_device_info_from_capture_folder

# Add paths for imports (script is in backend_host/scripts/)
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_host_dir = os.path.dirname(script_dir)  # backend_host/
project_root = os.path.dirname(backend_host_dir)  # virtualpytest/
sys.path.insert(0, project_root)

from shared.src.lib.utils.audio_transcription_utils import transcribe_ts_segments
from shared.src.lib.utils.ai_utils import call_text_ai

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
SAMPLE_INTERVAL = 10  # Sample every 10 seconds
MAX_DURATION_HOURS = 24
MAX_SAMPLES = (MAX_DURATION_HOURS * 3600) // SAMPLE_INTERVAL  # 8,640 samples
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
        
        # Build context for AI enhancement
        transcripts_text = []
        for seg in segments:
            seg_num = seg.get('segment_num', 0)
            transcript = seg.get('transcript', '').strip()
            language = seg.get('language', 'unknown')
            
            if transcript:
                transcripts_text.append(f"[Segment {seg_num}] ({language}): {transcript}")
        
        if not transcripts_text:
            logger.info(f"[{capture_folder}] No transcripts to enhance (all silent)")
            return {}
        
        combined = "\n".join(transcripts_text)
        
        # AI enhancement prompt - focused on accuracy improvement
        prompt = f"""You are enhancing speech-to-text transcripts from Whisper AI for better accuracy.

Original transcripts (may contain errors, mishearings, or unclear words):
{combined}

TASK: Fix errors, improve accuracy, and provide context while preserving the original meaning.

RULES:
1. Fix obvious speech-to-text errors and mishearings
2. Correct grammar and punctuation
3. Preserve the original language (don't translate)
4. Keep technical terms and proper nouns as-is if clearly correct
5. If a segment is unclear, keep the original but mark with [?]
6. Maintain the same segment structure

Respond with JSON only:
{{
  "enhanced": [
    {{"segment_num": 123, "enhanced_text": "corrected transcript text"}},
    {{"segment_num": 124, "enhanced_text": "corrected transcript text"}}
  ]
}}

CRITICAL: Respond with valid JSON only, no markdown, no extra text."""
        
        logger.info(f"[{capture_folder}] 🤖 Enhancing {len(segments)} transcripts with AI...")
        
        # Call AI
        result = call_text_ai(prompt, max_tokens=800, temperature=0.1)
        
        if not result['success']:
            logger.warning(f"[{capture_folder}] AI enhancement failed: {result.get('error', 'Unknown error')}")
            return {}
        
        # Parse AI response
        content = result['content'].strip()
        
        # Remove markdown code blocks if present
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        
        try:
            ai_result = json.loads(content)
            enhanced_map = {}
            
            for item in ai_result.get('enhanced', []):
                seg_num = item.get('segment_num')
                enhanced_text = item.get('enhanced_text', '').strip()
                
                if seg_num is not None and enhanced_text:
                    enhanced_map[seg_num] = enhanced_text
            
            logger.info(f"[{capture_folder}] ✅ AI enhanced {len(enhanced_map)}/{len(segments)} transcripts")
            return enhanced_map
            
        except json.JSONDecodeError as e:
            logger.warning(f"[{capture_folder}] AI response parsing failed: {e}")
            logger.debug(f"[{capture_folder}] AI raw response: {content[:200]}")
            return {}
    
    except Exception as e:
        logger.error(f"[{capture_folder}] AI enhancement error: {e}")
        return {}

def update_transcript_buffer(capture_dir, max_samples_per_run=1):
    """Update transcript buffer with new samples (circular 24h) - uses transcription utils
    
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
        transcript_path = os.path.join(stream_dir, 'transcript_segments.json')
        
        # Load existing transcript data
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r') as f:
                transcript_data = json.load(f)
        else:
            transcript_data = {
                'capture_folder': capture_folder,
                'sample_interval_seconds': SAMPLE_INTERVAL,
                'segments': [],
                'last_processed_segment': 0,
                'samples_since_ai_enhancement': 0
            }
        
        existing_segments = {s['segment_num']: s for s in transcript_data.get('segments', [])}
        last_processed = transcript_data.get('last_processed_segment', 0)
        
        # First run: Start 10 segments back to get immediate feedback
        if last_processed == 0:
            segment_files = glob.glob(os.path.join(stream_dir, 'segment_*.ts'))
            if segment_files:
                latest_seg = max(int(os.path.basename(f).split('_')[1].split('.')[0]) for f in segment_files)
                # Start 10 segments back for immediate processing (1 sample = 10 segments)
                start_offset = 10
                last_processed = max(0, latest_seg - start_offset)
                logger.info(f"[{capture_folder}] 🆕 First run - starting from segment #{last_processed} (10 segments back from #{latest_seg})")
                transcript_data['last_processed_segment'] = last_processed
        
        # Find available segments
        segment_files = glob.glob(os.path.join(stream_dir, 'segment_*.ts'))
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
        
        # Find segments to sample (every 10th segment interval, but merge 10 segments per sample)
        segments_to_process = []
        for seg_num in all_segment_nums:
            if seg_num > last_processed and seg_num % SAMPLE_INTERVAL == 0:
                # Collect 10 consecutive segments ending at this segment
                batch = []
                for i in range(SAMPLE_INTERVAL):
                    batch_seg_num = seg_num - SAMPLE_INTERVAL + 1 + i
                    if batch_seg_num in segment_map:
                        batch.append((batch_seg_num, segment_map[batch_seg_num]))
                
                if batch:  # Only process if we have segments in the batch
                    segments_to_process.append((seg_num, batch))  # (target_seg_num, list_of_10_segments)
        
        if not segments_to_process:
            # No new segments to process
            logger.debug(f"[{capture_folder}] No new samples (waiting for seg after #{last_processed})")
            return False
        
        # Limit processing to max_samples_per_run (for alternating between devices)
        total_pending = len(segments_to_process)
        segments_to_process = segments_to_process[:max_samples_per_run]
        
        if total_pending > max_samples_per_run:
            logger.info(f"[{capture_folder}] 🔄 Processing {len(segments_to_process)}/{total_pending} samples (alternating with other devices)...")
        else:
            logger.info(f"[{capture_folder}] 🔄 Processing {len(segments_to_process)} new samples (10 segments per sample)...")
        
        # Process new samples using transcription utils (clean, no dependencies)
        for segment_num, segment_batch in segments_to_process:
            # Extract TS file paths from batch
            ts_file_paths = [seg_path for _, seg_path in segment_batch]
            
            # Start timing
            seg_start_time = time.time()
            
            # Calculate total size of files being merged
            total_size = sum(os.path.getsize(f) for f in ts_file_paths if os.path.exists(f))
            
            # Transcribe merged segments (utility handles merging + transcription + cleanup)
            # Pre-checks audio level to skip Whisper on silent segments (saves CPU on RPi)
            logger.info(f"[{capture_folder}] 🎬 seg#{segment_num}: Merged {len(segment_batch)} TS files ({total_size} bytes)")
            result = transcribe_ts_segments(ts_file_paths, merge=True, model_name='tiny', device_id=capture_folder)
            
            transcript = result.get('transcript', '').strip()
            language = result.get('language', 'unknown')
            confidence = result.get('confidence', 0.0)
            skipped = result.get('skipped', False)
            seg_elapsed = time.time() - seg_start_time
            
            relative_seconds = segment_num
            manifest_window = (relative_seconds // 3600) + 1
            
            existing_segments[segment_num] = {
                'segment_num': segment_num,
                'relative_seconds': relative_seconds,
                'language': language,
                'transcript': transcript,
                'confidence': confidence,
                'manifest_window': manifest_window,
                'segments_merged': len(segment_batch)  # Track how many segments were merged
            }
            
            # Compact logging: all info in 2-3 lines
            if transcript:
                logger.info(f"[{capture_folder}] 📝 Language: {language} | Confidence: {confidence:.2f} | Duration: {seg_elapsed:.1f}s")
                logger.info(f"[{capture_folder}] 💬 '{transcript}'")
            elif skipped:
                logger.info(f"[{capture_folder}] 🔇 Silent (Whisper skipped) | Duration: {seg_elapsed:.1f}s")
            else:
                logger.info(f"[{capture_folder}] 🔇 No speech detected | Duration: {seg_elapsed:.1f}s")
        
        # Circular buffer: Keep only last MAX_SAMPLES
        all_segments = sorted(existing_segments.values(), key=lambda x: x['segment_num'])
        if len(all_segments) > MAX_SAMPLES:
            all_segments = all_segments[-MAX_SAMPLES:]
            logger.info(f"[{capture_folder}] Circular buffer: pruned to {MAX_SAMPLES} samples")
        
        # AI Enhancement: Every 10 new samples, enhance the last batch
        samples_since_enhancement = transcript_data.get('samples_since_ai_enhancement', 0)
        samples_since_enhancement += len(segments_to_process)
        
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
                            logger.info(f"[{capture_folder}] Enhanced seg#{seg_num}: '{enhanced_map[seg_num][:60]}{'...' if len(enhanced_map[seg_num]) > 60 else ''}'")
            
            # Reset counter
            samples_since_enhancement = 0
        
        # Update transcript data
        transcript_data['capture_folder'] = capture_folder
        transcript_data['sample_interval_seconds'] = SAMPLE_INTERVAL
        transcript_data['total_duration_seconds'] = MAX_DURATION_HOURS * 3600
        transcript_data['segments'] = all_segments
        transcript_data['last_update'] = datetime.now().isoformat()
        transcript_data['total_samples'] = len(all_segments)
        transcript_data['last_processed_segment'] = segments_to_process[-1][0] if segments_to_process else last_processed
        transcript_data['samples_since_ai_enhancement'] = samples_since_enhancement
        
        # Save immediately after processing this device (atomic write)
        with open(transcript_path + '.tmp', 'w') as f:
            json.dump(transcript_data, f, indent=2)
        os.rename(transcript_path + '.tmp', transcript_path)
        
        elapsed = time.time() - start_time
        logger.info(f"[{capture_folder}] ✅ Saved transcript_segments.json: {len(all_segments)} total samples (processed {len(segments_to_process)} new) [{elapsed:.2f}s]")
        return True
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[{capture_folder}] ❌ Error updating transcript buffer: {e} [{elapsed:.2f}s]")
        return False

def main():
    cleanup_logs_on_startup()  # Clean log on startup
    
    logger.info("Starting Transcript Accumulator (10s sampling, 24h circular buffer)...")
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

