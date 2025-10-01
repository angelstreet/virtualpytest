#!/usr/bin/env python3
"""
Circular 24h Transcript Accumulator
Samples audio every 10s, generates timestamped transcripts, local circular buffer
"""
import os
import json
import time
import glob
import logging
import subprocess
import tempfile
from datetime import datetime
from archive_utils import get_capture_directories, get_capture_folder

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

def transcribe_segment(segment_path, segment_num):
    """Extract audio and transcribe single segment using Whisper"""
    try:
        # Extract audio from TS segment
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        cmd = ['ffmpeg', '-y', '-i', segment_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', temp_audio.name]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        
        if result.returncode != 0 or not os.path.exists(temp_audio.name) or os.path.getsize(temp_audio.name) < 1024:
            os.unlink(temp_audio.name)
            return '', 'unknown', 0.0
        
        # Transcribe with Whisper
        import whisper
        if not hasattr(transcribe_segment, 'model'):
            transcribe_segment.model = whisper.load_model("tiny")
        
        result = transcribe_segment.model.transcribe(
            temp_audio.name,
            fp16=False, verbose=False, beam_size=1, best_of=1, 
            temperature=0, no_speech_threshold=0.6
        )
        
        # Cleanup
        os.unlink(temp_audio.name)
        
        transcript = result.get('text', '').strip()
        language = result.get('language', 'en')
        
        # Convert language code to name
        lang_map = {'en': 'English', 'fr': 'French', 'de': 'German', 'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese'}
        language_name = lang_map.get(language, language)
        confidence = min(0.95, 0.5 + (len(transcript) / 100)) if transcript else 0.0
        
        return transcript, language_name, confidence
        
    except Exception as e:
        logger.error(f"Error transcribing segment {segment_num}: {e}")
        return '', 'unknown', 0.0

def update_transcript_buffer(capture_dir):
    """Update transcript buffer with new samples (circular 24h)"""
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
        
        # Find available segments
        segment_files = glob.glob(os.path.join(stream_dir, 'segment_*.ts'))
        if not segment_files:
            return
        
        # Filter segments to sample (every 10th segment)
        segments_to_process = []
        for seg_file in segment_files:
            seg_num = int(os.path.basename(seg_file).split('_')[1].split('.')[0])
            if seg_num > last_processed and seg_num % SAMPLE_INTERVAL == 0:
                segments_to_process.append((seg_num, seg_file))
        
        segments_to_process.sort()
        
        if not segments_to_process:
            return
        
        logger.info(f"[{capture_folder}] Processing {len(segments_to_process)} new samples...")
        
        # Process new samples
        for segment_num, segment_path in segments_to_process:
            transcript, language, confidence = transcribe_segment(segment_path, segment_num)
            
            relative_seconds = segment_num
            manifest_window = (relative_seconds // 3600) + 1
            
            existing_segments[segment_num] = {
                'segment_num': segment_num,
                'relative_seconds': relative_seconds,
                'language': language,
                'transcript': transcript,
                'confidence': confidence,
                'manifest_window': manifest_window
            }
            
            if transcript:
                logger.info(f"[{capture_folder}] seg#{segment_num}: '{transcript[:50]}...' ({language})")
        
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
    logger.info("Starting Transcript Accumulator (10s sampling, 24h circular buffer)...")
    capture_dirs = get_capture_directories()
    logger.info(f"Monitoring {len(capture_dirs)} capture directories")
    
    while True:
        for capture_dir in capture_dirs:
            update_transcript_buffer(capture_dir)
        time.sleep(60)  # Check every 60s

if __name__ == '__main__':
    main()

