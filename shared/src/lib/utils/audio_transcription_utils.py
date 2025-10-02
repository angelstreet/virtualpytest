"""
Audio Transcription Utilities
Shared utility for Whisper-based transcription - NO controller dependencies
Reused by: AudioAIHelpers, transcript_accumulator, and any script needing transcription
"""
import os
import subprocess
import tempfile
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime


# Global Whisper model cache (singleton pattern)
_whisper_model = None


def get_whisper_model(model_name: str = "tiny"):
    """Get cached Whisper model (singleton pattern for performance)"""
    global _whisper_model
    
    if _whisper_model is None:
        try:
            import whisper
            print(f"[AudioTranscriptionUtils] Loading Whisper model '{model_name}' (one-time load)...")
            _whisper_model = whisper.load_model(model_name)
            print(f"[AudioTranscriptionUtils] ✓ Whisper model '{model_name}' loaded and cached")
        except ImportError:
            print(f"[AudioTranscriptionUtils] ❌ Whisper not installed - run 'pip install openai-whisper'")
            return None
    
    return _whisper_model


def merge_ts_files(ts_file_paths: List[str], output_path: Optional[str] = None, device_id: str = "") -> Optional[str]:
    """
    Merge multiple TS files into a single TS file using ffmpeg
    
    Args:
        ts_file_paths: List of TS file paths to merge
        output_path: Optional output path (if None, uses fixed temp file - OVERWRITTEN)
        device_id: Device identifier for logging (e.g., "capture1")
    
    Returns:
        Path to merged TS file or None on failure
    """
    prefix = f"[{device_id}] " if device_id else ""
    if not ts_file_paths:
        return None
    
    if len(ts_file_paths) == 1:
        return ts_file_paths[0]  # No merge needed
    
    try:
        # Create output path if not provided - use FIXED name, overwrite each time
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            device_suffix = f"_{device_id}" if device_id else ""
            merged_filename = f"merged_ts{device_suffix}.ts"
            output_path = os.path.join(temp_dir, merged_filename)
        
        # Build ffmpeg command for TS concatenation
        cmd = ['ffmpeg', '-y']
        
        # Add all input files
        for ts in ts_file_paths:
            cmd.extend(['-i', ts])
        
        # Build filter_complex for concat
        inputs = ''.join(f'[{i}:v][{i}:a]' for i in range(len(ts_file_paths)))
        cmd.extend([
            '-filter_complex', f'{inputs}concat=n={len(ts_file_paths)}:v=1:a=1[v][a]',
            '-map', '[v]',
            '-map', '[a]',
            output_path
        ])
        
        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                # Success - return without logging (caller will log)
                return output_path
            else:
                print(f"{prefix}[AudioTranscriptionUtils] ❌ Merged file is empty or too small")
        else:
            print(f"{prefix}[AudioTranscriptionUtils] ❌ ffmpeg merge error: {result.stderr}")
        
        return None
            
    except Exception as e:
        print(f"{prefix}[AudioTranscriptionUtils] ❌ Error merging TS files: {e}")
        return None


def extract_audio_from_ts(ts_file_path: str, output_path: Optional[str] = None, device_id: str = "") -> Optional[str]:
    """
    Extract audio from TS file as WAV (16kHz mono for Whisper)
    
    Args:
        ts_file_path: Path to TS file
        output_path: Optional output path (if None, creates temp file in /tmp - REUSED)
        device_id: Device identifier for device-specific temp file (e.g., "capture1")
    
    Returns:
        Path to extracted WAV file or None on failure
    """
    try:
        # Create output path if not provided - use FIXED name per device, overwrite each time
        if output_path is None:
            temp_dir = tempfile.gettempdir()  # /tmp/
            # Use device-specific fixed filename (no timestamp) - will be overwritten on next extraction
            device_suffix = f"_{device_id}" if device_id else ""
            audio_filename = f"audio_temp_whisper{device_suffix}.wav"
            output_path = os.path.join(temp_dir, audio_filename)
        
        # Extract audio with Whisper-optimized settings (16kHz mono)
        cmd = [
            'ffmpeg', '-y', '-i', ts_file_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            return output_path
        else:
            print(f"[AudioTranscriptionUtils] ❌ Failed to extract audio from {os.path.basename(ts_file_path)}")
            return None
            
    except Exception as e:
        print(f"[AudioTranscriptionUtils] ❌ Error extracting audio: {e}")
        return None


def detect_audio_level(file_path: str, device_id: str = "") -> tuple:
    """
    Detect audio level using ffmpeg volumedetect - REUSES detector.py logic
    
    Args:
        file_path: Path to audio/video file (TS, WAV, MP4, etc.)
        device_id: Device identifier for logging (e.g., "capture1")
    
    Returns:
        Tuple of (has_audio: bool, volume_percentage: int, mean_volume_db: float)
    """
    import re
    
    prefix = f"[{device_id}] " if device_id else ""
    try:
        # Use ffmpeg volumedetect - same as detector.py
        cmd = [
            'ffmpeg', '-i', file_path,
            '-af', 'volumedetect',
            '-vn', '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        # Parse mean_volume from stderr - same as detector.py
        mean_volume = -100.0
        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                match = re.search(r'mean_volume:\s*([-\d.]+)\s*dB', line)
                if match:
                    mean_volume = float(match.group(1))
                    break
        
        # Convert dB to 0-100% scale: -60dB = 0%, 0dB = 100% - same as detector.py
        volume_percentage = max(0, min(100, (mean_volume + 60) * 100 / 60))
        has_audio = volume_percentage > 5  # 5% threshold - same as detector.py
        
        print(f"{prefix}[AudioTranscriptionUtils] Audio level: {mean_volume:.1f}dB ({volume_percentage}% - {'sound' if has_audio else 'silent'})")
        
        return has_audio, int(volume_percentage), mean_volume
        
    except Exception as e:
        print(f"{prefix}[AudioTranscriptionUtils] Audio check error: {e}, assuming sound present")
        return True, 0, -100.0


def transcribe_audio(audio_file_path: str, model_name: str = "tiny", skip_silence_check: bool = False, device_id: str = "") -> Dict[str, Any]:
    """
    Transcribe audio file using Whisper (with model caching)
    
    Args:
        audio_file_path: Path to audio file (WAV recommended)
        model_name: Whisper model name (tiny, base, small, medium, large)
        skip_silence_check: If True, skip audio level check (default False)
        device_id: Device identifier for logging (e.g., "capture1")
    
    Returns:
        Dict with 'transcript', 'language', 'confidence', 'success'
    """
    prefix = f"[{device_id}] " if device_id else ""
    try:
        # Quick pre-check: Skip Whisper if audio is silent (saves CPU)
        # Reuses same audio detection logic as detector.py
        if not skip_silence_check:
            has_audio, volume_percentage, mean_volume_db = detect_audio_level(audio_file_path, device_id=device_id)
            if not has_audio:
                print(f"{prefix}[AudioTranscriptionUtils] Skipping Whisper - audio is silent")
                return {
                    'success': True,
                    'transcript': '',
                    'language': 'unknown',
                    'confidence': 0.0,
                    'skipped': True,
                    'reason': 'silent_audio',
                    'volume_percentage': volume_percentage,
                    'mean_volume_db': mean_volume_db
                }
        
        model = get_whisper_model(model_name)
        
        if model is None:
            return {
                'success': False,
                'transcript': '',
                'language': 'unknown',
                'confidence': 0.0,
                'error': 'Whisper model not available'
            }
        
        # Transcribe with optimized settings for speed
        # Suppress all Whisper output (detected language, progress bar, etc.)
        import sys
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            result = model.transcribe(
                audio_file_path,
                fp16=False,
                verbose=False,
                beam_size=1,
                best_of=1,
                temperature=0,
                no_speech_threshold=0.6  # Strict threshold to avoid false positives on silence
            )
        finally:
            sys.stdout = old_stdout
        
        transcript = result.get('text', '').strip()
        language = result.get('language', 'en')
        
        # Get all segments for debugging
        segments = result.get('segments', [])
        segment_count = len(segments)
        
        # Convert language code to name
        lang_map = {
            'en': 'English', 'fr': 'French', 'de': 'German', 'es': 'Spanish',
            'it': 'Italian', 'pt': 'Portuguese', 'nl': 'Dutch', 'pl': 'Polish',
            'ru': 'Russian', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean'
        }
        language_name = lang_map.get(language, language)
        
        # Estimate confidence based on transcript length (simple heuristic)
        confidence = min(0.95, 0.5 + (len(transcript) / 100)) if transcript else 0.0
        
        return {
            'success': True,
            'transcript': transcript,
            'language': language_name,
            'confidence': confidence
        }
        
    except Exception as e:
        print(f"[AudioTranscriptionUtils] ❌ Transcription error: {e}")
        return {
            'success': False,
            'transcript': '',
            'language': 'unknown',
            'confidence': 0.0,
            'error': str(e)
        }


def transcribe_ts_segments(ts_file_paths: List[str], merge: bool = True, model_name: str = "tiny", device_id: str = "") -> Dict[str, Any]:
    """
    Transcribe multiple TS segments (with optional merging for better context)
    
    Args:
        ts_file_paths: List of TS file paths
        merge: If True, merge all segments before transcription (better quality)
        model_name: Whisper model name
        device_id: Device identifier for logging (e.g., "capture1")
    
    Returns:
        Dict with 'transcript', 'language', 'confidence', 'success', 'segments_processed'
    """
    prefix = f"[{device_id}] " if device_id else ""
    try:
        if not ts_file_paths:
            return {
                'success': False,
                'transcript': '',
                'language': 'unknown',
                'confidence': 0.0,
                'segments_processed': 0,
                'error': 'No TS files provided'
            }
        
        # Merge segments if requested and multiple files
        if merge and len(ts_file_paths) > 1:
            merged_ts = merge_ts_files(ts_file_paths, device_id=device_id)
            
            if merged_ts:
                # Extract audio from merged file
                audio_file = extract_audio_from_ts(merged_ts, device_id=device_id)
                
                if audio_file:
                    # Transcribe merged audio
                    result = transcribe_audio(audio_file, model_name, device_id=device_id)
                    result['segments_processed'] = len(ts_file_paths)
                    result['merged'] = True
                    # No cleanup needed - files are overwritten on next run
                    return result
        
        # Fallback: process first segment only (or single segment)
        ts_file = ts_file_paths[0]
        audio_file = extract_audio_from_ts(ts_file, device_id=device_id)
        
        if audio_file:
            result = transcribe_audio(audio_file, model_name, device_id=device_id)
            result['segments_processed'] = 1
            result['merged'] = False
            # No cleanup needed - file is overwritten on next run
            return result
        
        return {
            'success': False,
            'transcript': '',
            'language': 'unknown',
            'confidence': 0.0,
            'segments_processed': 0,
            'error': 'Failed to extract audio from TS files'
        }
        
    except Exception as e:
        print(f"[AudioTranscriptionUtils] ❌ Error in transcribe_ts_segments: {e}")
        return {
            'success': False,
            'transcript': '',
            'language': 'unknown',
            'confidence': 0.0,
            'segments_processed': 0,
            'error': str(e)
        }

