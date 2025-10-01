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

def update_transcript_buffer(capture_dir):
    """Update transcript buffer with new samples (circular 24h) - uses transcription utils"""
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
                   'last_processed_segment': 0
               }
           
           existing_segments = {s['segment_num']: s for s in transcript_data.get('segments', [])}
           last_processed = transcript_data.get('last_processed_segment', 0)
           
           # First run: Start from NOW, not from backlog (don't try to catch up)
           if last_processed == 0:
               segment_files = glob.glob(os.path.join(stream_dir, 'segment_*.ts'))
               if segment_files:
                   latest_seg = max(int(os.path.basename(f).split('_')[1].split('.')[0]) for f in segment_files)
                   last_processed = latest_seg
                   logger.info(f"[{capture_folder}] 🆕 First run - starting from current segment #{latest_seg} (skipping backlog)")
                   transcript_data['last_processed_segment'] = last_processed
        
        # Find available segments
        segment_files = glob.glob(os.path.join(stream_dir, 'segment_*.ts'))
        if not segment_files:
            return
        
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
            return
        
        logger.info(f"[{capture_folder}] Processing {len(segments_to_process)} new samples (10 segments per sample)...")
        
        # Process new samples using transcription utils (clean, no dependencies)
        for segment_num, segment_batch in segments_to_process:
            # Extract TS file paths from batch
            ts_file_paths = [seg_path for _, seg_path in segment_batch]
            
            # Transcribe merged segments (utility handles merging + transcription + cleanup)
            # Pre-checks audio level to skip Whisper on silent segments (saves CPU on RPi)
            result = transcribe_ts_segments(ts_file_paths, merge=True, model_name='tiny', device_id=capture_folder)
            
            transcript = result.get('transcript', '').strip()
            language = result.get('language', 'unknown')
            confidence = result.get('confidence', 0.0)
            skipped = result.get('skipped', False)
            
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
            
            if transcript:
                logger.info(f"[{capture_folder}] 📝 seg#{segment_num} ({len(segment_batch)} merged) - {language}: '{transcript}'")
            elif skipped:
                logger.info(f"[{capture_folder}] 🔇 seg#{segment_num} ({len(segment_batch)} merged) - Silent (Whisper skipped)")
            else:
                logger.info(f"[{capture_folder}] 🔇 seg#{segment_num} ({len(segment_batch)} merged) - No speech detected")
        
        # Circular buffer: Keep only last MAX_SAMPLES
        all_segments = sorted(existing_segments.values(), key=lambda x: x['segment_num'])
        if len(all_segments) > MAX_SAMPLES:
            all_segments = all_segments[-MAX_SAMPLES:]
            logger.info(f"[{capture_folder}] Circular buffer: pruned to {MAX_SAMPLES} samples")
        
        # Save updated transcript (atomic write)
        transcript_data = {
            'capture_folder': capture_folder,
            'sample_interval_seconds': SAMPLE_INTERVAL,
            'total_duration_seconds': MAX_DURATION_HOURS * 3600,
            'segments': all_segments,
            'last_update': datetime.now().isoformat(),
            'total_samples': len(all_segments),
            'last_processed_segment': segments_to_process[-1][0] if segments_to_process else last_processed
        }
        
        with open(transcript_path + '.tmp', 'w') as f:
            json.dump(transcript_data, f, indent=2)
        os.rename(transcript_path + '.tmp', transcript_path)
        
        logger.info(f"[{capture_folder}] ✓ Transcript buffer updated: {len(all_segments)} samples")
        
    except Exception as e:
        logger.error(f"Error updating transcript buffer for {capture_dir}: {e}")

def main():
    cleanup_logs_on_startup()  # Clean log on startup
    
    logger.info("Starting Transcript Accumulator (10s sampling, 24h circular buffer)...")
    logger.info("Using audio_transcription_utils (clean, no dependencies)...")
    
    try:
        capture_dirs = get_capture_directories()
        logger.info(f"Monitoring {len(capture_dirs)} capture directories")
        
        # Log each capture directory being monitored
        for capture_dir in capture_dirs:
            capture_folder = get_capture_folder(capture_dir)
            logger.info(f"  → Monitoring: {capture_dir} -> {capture_folder}")
        
        # Whisper model will be loaded on first use and cached globally
        logger.info("✓ Whisper model will be loaded on first transcription (global singleton cache)")
        
        # Filter out host device from monitored directories (no audio capture)
        # Uses lightweight device mapping without loading incidents from DB
        monitored_devices = []
        for capture_dir in capture_dirs:
            capture_folder = get_capture_folder(capture_dir)
            device_info = get_device_info_from_capture_folder(capture_folder)
            device_id = device_info.get('device_id', capture_folder)
            is_host = (device_id == 'host')
            
            if is_host:
                logger.info(f"  ⊗ Skipping: {capture_dir} -> {capture_folder} (host has no audio)")
            else:
                monitored_devices.append(capture_dir)
        
        logger.info(f"Monitoring {len(monitored_devices)} devices for transcripts (excluding host)")
        
        while True:
            for i, capture_dir in enumerate(monitored_devices, 1):
                capture_folder = get_capture_folder(capture_dir)
                logger.info(f"[{capture_folder}] Checking for new transcript samples... ({i}/{len(monitored_devices)})")
                update_transcript_buffer(capture_dir)
                logger.info(f"[{capture_folder}] ✓ Transcript processing complete")
            
            logger.info(f"Completed full cycle for {len(monitored_devices)} devices, sleeping 60s...")
            time.sleep(60)  # Check every 60s
            
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise

if __name__ == '__main__':
    main()

