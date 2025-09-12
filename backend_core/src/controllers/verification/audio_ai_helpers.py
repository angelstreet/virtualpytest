"""
Audio AI Analysis Helpers

AI-powered audio analysis functionality for speech-to-text transcription:
1. Audio segment retrieval and processing
2. Speech-to-text transcription using local Whisper (optimized for speed)
3. Language detection from transcribed text
4. Audio analysis logging similar to subtitle detection
5. Integration with ZapController for comprehensive analysis

This helper handles all AI-powered audio analysis operations using
local Whisper models for fast, offline speech recognition and language detection.
Performance optimized with tiny model (~39MB) for real-time zap testing.
"""

import os
import base64
import requests
import tempfile
import json
import time
import wave
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List

# Optional imports for fallback language detection
try:
    from langdetect import detect, LangDetectException
    LANG_DETECT_AVAILABLE = True
except ImportError:
    LANG_DETECT_AVAILABLE = False


class AudioAIHelpers:
    """AI-powered audio analysis operations using local Whisper for fast speech recognition."""
    
    def __init__(self, av_controller, device_name: str = "AudioAI"):
        """
        Initialize audio AI helpers.
        
        Args:
            av_controller: AV controller for capturing audio/video and device context
            device_name: Name for logging purposes
        """
        self.av_controller = av_controller
        self.device_name = device_name
    
    # =============================================================================
    # Audio Segment Retrieval
    # =============================================================================
    
    def get_recent_audio_segments(self, segment_count: int = 3, segment_duration: int = None) -> List[str]:
        """
        Retrieve the last N audio segments from video capture.
        
        Args:
            segment_count: Number of recent segments to retrieve (default: 3)
            segment_duration: Duration of each segment in seconds (default: uses HLS_SEGMENT_DURATION from AVControllerInterface)
            
        Returns:
            List of audio file paths (WAV format) ready for AI analysis
        """
        try:
            # Use global HLS segment duration if not specified
            if segment_duration is None:
                from backend_core.src.controllers.base_controller import AVControllerInterface
                segment_duration = AVControllerInterface.HLS_SEGMENT_DURATION
            
            print(f"AudioAI[{self.device_name}]: Retrieving last {segment_count} audio segments ({segment_duration}s each)...")
            
            # Get video capture path from AV controller
            if not hasattr(self.av_controller, 'video_capture_path'):
                print(f"AudioAI[{self.device_name}]: No video capture path available")
                return []
            
            capture_folder = self.av_controller.video_capture_path
            if not os.path.exists(capture_folder):
                print(f"AudioAI[{self.device_name}]: Capture folder does not exist: {capture_folder}")
                return []
            
            # Find recent HLS segment files (last 30 seconds since segments rotate quickly)
            cutoff_time = time.time() - 30  # 30 seconds ago
            ts_files = []
            
            for filename in os.listdir(capture_folder):
                if filename.startswith('segment_') and filename.endswith('.ts'):
                    filepath = os.path.join(capture_folder, filename)
                    if os.path.getmtime(filepath) >= cutoff_time:
                        ts_files.append({
                            'path': filepath,
                            'filename': filename,
                            'mtime': os.path.getmtime(filepath)
                        })
            
            # Sort by modification time (newest first)
            ts_files.sort(key=lambda x: x['mtime'], reverse=True)
            
            # Take the most recent files (up to segment_count)
            recent_files = ts_files[:segment_count]
            
            if not recent_files:
                # Check if we have image captures but no TS files (device compatibility check)
                jpg_files = []
                for filename in os.listdir(capture_folder):
                    if filename.startswith('capture_') and filename.endswith('.jpg'):
                        jpg_files.append(filename)
                
                if jpg_files:
                    print(f"AudioAI[{self.device_name}]: Device uses image-only capture, audio analysis not available")
                    print(f"AudioAI[{self.device_name}]: Found {len(jpg_files)} image captures but no HLS segments")
                    return []
                else:
                    print(f"AudioAI[{self.device_name}]: No recent HLS segments found for audio extraction")
                    print(f"AudioAI[{self.device_name}]: Checked folder: {capture_folder}")
                    return []
            
            # NEW: Merge TS files first if more than one
            merged_ts = None  # Track for cleanup
            if len(recent_files) > 1:
                print(f"AudioAI[{self.device_name}]: Merging {len(recent_files)} TS segments into one file...")
                merged_ts = self._merge_ts_files([f['path'] for f in recent_files])
                if merged_ts:
                    # Replace recent_files with single merged file
                    recent_files = [{'path': merged_ts, 'filename': 'merged.ts', 'mtime': time.time()}]
                    print(f"AudioAI[{self.device_name}]: Merged successfully into: {os.path.basename(merged_ts)}")
                else:
                    print(f"AudioAI[{self.device_name}]: Failed to merge TS segments, proceeding with individual files")
            
            # Extract audio from (merged) TS file(s)
            audio_files = []
            temp_dir = tempfile.gettempdir()
            
            print(f"AudioAI[{self.device_name}]: Found {len(recent_files)} recent HLS segments for audio extraction")
            
            for i, ts_file in enumerate(recent_files):
                try:
                    # Create temporary audio file
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                    audio_filename = f"audio_segment_{i}_{timestamp}.wav"
                    audio_path = os.path.join(temp_dir, audio_filename)
                    
                    # Extract audio using ffmpeg from HLS segment
                    # TS files are already 2-second segments, so no duration needed
                    cmd = [
                        'ffmpeg', '-y',  # -y to overwrite existing files
                        '-i', ts_file['path'],
                        '-vn',  # No video
                        '-acodec', 'pcm_s16le',  # WAV format
                        '-ar', '16000',  # 16kHz sample rate (good for speech)
                        '-ac', '1',  # Mono
                        audio_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0 and os.path.exists(audio_path):
                        # Verify the audio file has content
                        if os.path.getsize(audio_path) > 1024:  # At least 1KB
                            audio_files.append(audio_path)
                            print(f"AudioAI[{self.device_name}]: Extracted audio segment {i+1}: {os.path.basename(audio_path)}")
                        else:
                            print(f"AudioAI[{self.device_name}]: Audio segment {i+1} is too small, skipping")
                            if os.path.exists(audio_path):
                                os.unlink(audio_path)
                    else:
                        print(f"AudioAI[{self.device_name}]: Failed to extract audio from segment {i+1}: {result.stderr}")
                        
                except Exception as e:
                    print(f"AudioAI[{self.device_name}]: Error processing segment {i+1}: {e}")
                    continue
            
            # NEW: Cleanup temporary merged TS if it was created
            if merged_ts and os.path.exists(merged_ts):
                try:
                    os.unlink(merged_ts)
                    print(f"AudioAI[{self.device_name}]: Cleaned up temporary merged TS: {os.path.basename(merged_ts)}")
                except Exception as e:
                    print(f"AudioAI[{self.device_name}]: Failed to clean up merged TS: {e}")
            
            if not audio_files:
                print(f"AudioAI[{self.device_name}]: No audio files extracted from HLS segments")
                return []
            
            print(f"AudioAI[{self.device_name}]: Successfully extracted {len(audio_files)} audio segments")
            return audio_files
            
        except Exception as e:
            print(f"AudioAI[{self.device_name}]: Error retrieving audio segments: {e}")
            # Cleanup on error too
            if merged_ts and os.path.exists(merged_ts):
                os.unlink(merged_ts)
            return []
    
    def extract_audio_from_segments(self, segment_files: List[Tuple[str, str]], segment_count: int = 3) -> List[str]:
        """Extract audio from specific HLS segments (optimized for restart video with merging)."""
        try:
            selected_segments = segment_files[-segment_count:] if len(segment_files) > segment_count else segment_files
            
            if not selected_segments:
                return []
            
            # For restart video with many segments, merge them first like zap controller
            if len(selected_segments) > 1:
                print(f"AudioAI[{self.device_name}]: Merging {len(selected_segments)} TS segments into one file...")
                
                # Extract paths for merging
                ts_paths = [segment_path for _, segment_path in selected_segments]
                merged_ts = self._merge_ts_files(ts_paths)
                
                if merged_ts:
                    print(f"AudioAI[{self.device_name}]: Merge successful (size: {os.path.getsize(merged_ts)} bytes)")
            
                    # Extract audio from merged file
                    temp_dir = tempfile.mkdtemp(prefix="restart_audio_")
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                    audio_filename = f"restart_merged_audio_{timestamp}.wav"
                    audio_path = os.path.join(temp_dir, audio_filename)
                    
                    cmd = ['ffmpeg', '-y', '-i', merged_ts, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    # Cleanup merged TS file
                    try:
                        os.remove(merged_ts)
                        print(f"AudioAI[{self.device_name}]: Cleaned up temporary merged TS: {os.path.basename(merged_ts)}")
                    except:
                        pass
                    
                    if result.returncode == 0 and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1024:
                        print(f"AudioAI[{self.device_name}]: Successfully extracted merged audio: {os.path.basename(audio_path)}")
                        return [audio_path]
                    else:
                        print(f"AudioAI[{self.device_name}]: Failed to extract audio from merged file")
                        return []
                else:
                    print(f"AudioAI[{self.device_name}]: Failed to merge TS segments, falling back to individual processing")
            
            # Fallback: process individual segments (original behavior)
            audio_files = []
            temp_dir = tempfile.mkdtemp(prefix="restart_audio_")
            
            for i, (filename, segment_path) in enumerate(selected_segments):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                audio_filename = f"restart_audio_{i}_{timestamp}.wav"
                audio_path = os.path.join(temp_dir, audio_filename)
                
                cmd = ['ffmpeg', '-y', '-i', segment_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1024:
                    audio_files.append(audio_path)
            
            return audio_files
            
        except Exception as e:
            print(f"AudioAI[{self.device_name}]: Audio extraction error: {e}")
            return []
    
    # NEW: Helper method to merge multiple TS files
    def _merge_ts_files(self, ts_files: List[str]) -> Optional[str]:
        """Merge multiple TS files into a single TS file using ffmpeg."""
        if not ts_files:
            return None
        
        try:
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            merged_filename = f"merged_ts_{timestamp}.ts"
            merged_path = os.path.join(temp_dir, merged_filename)
            
            # Build ffmpeg command for TS concatenation with safe flags
            cmd = ['ffmpeg', '-y'] 
            
            # Add all input files
            for ts in ts_files:
                cmd.extend(['-i', ts])
            
            # Build filter_complex for concat
            inputs = ''.join(f'[{i}:v][{i}:a]' for i in range(len(ts_files)))
            cmd.extend([
                '-filter_complex', f'{inputs}concat=n={len(ts_files)}:v=1:a=1[v][a]',
                '-map', '[v]',
                '-map', '[a]',
                merged_path
            ])
            
            # Run ffmpeg with debug output
            print(f"AudioAI[{self.device_name}]: Running merge command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                if os.path.exists(merged_path) and os.path.getsize(merged_path) > 1024:
                    print(f"AudioAI[{self.device_name}]: Merge successful (size: {os.path.getsize(merged_path)} bytes)")
                    return merged_path
                else:
                    print(f"AudioAI[{self.device_name}]: Merged file is empty or too small")
            else:
                print(f"AudioAI[{self.device_name}]: ffmpeg error: {result.stderr}")
                print(f"AudioAI[{self.device_name}]: ffmpeg stdout: {result.stdout}")
            
            return None
                
        except Exception as e:
            print(f"AudioAI[{self.device_name}]: Error merging TS files: {e}")
            return None
    
    # =============================================================================
    # AI-Powered Speech-to-Text Analysis
    # =============================================================================
    
    def analyze_audio_segments_ai(self, audio_files: List[str], upload_to_r2: bool = True, early_stop: bool = True) -> Dict[str, Any]:
        """
        AI-powered speech-to-text analysis for multiple audio segments.
        
        Args:
            audio_files: List of audio file paths to analyze
            upload_to_r2: Whether to upload audio files to R2 for traceability (default: True)
            early_stop: Whether to stop processing after first successful speech detection (default: True)
            
        Returns:
            Dictionary with detailed AI audio analysis results including R2 URLs
        """
        try:
            print(f"AudioAI[{self.device_name}]: Starting AI analysis of {len(audio_files)} audio segments...")
            
            if not audio_files:
                return {
                    'success': True,
                    'segments_analyzed': 0,
                    'combined_transcript': '',
                    'detected_language': 'unknown',
                    'confidence': 0.0,
                    'segments': [],
                    'analysis_type': 'ai_audio_transcription'
                }
            
            # Check Whisper availability (no API key needed for local processing)
            try:
                import whisper
            except ImportError:
                print(f"AudioAI[{self.device_name}]: Whisper not installed - run 'pip install openai-whisper'")
                return {
                    'success': False,
                    'error': 'Local Whisper not available - please install openai-whisper',
                    'analysis_type': 'local_whisper_transcription'
                }
            
            segment_results = []
            all_transcripts = []
            early_stopped = False
            
            for i, audio_file in enumerate(audio_files):
                try:
                    print(f"AudioAI[{self.device_name}]: Analyzing audio segment {i+1}/{len(audio_files)}...")
                    
                    # Transcribe audio segment
                    transcript, language, confidence = self.transcribe_audio_with_ai(audio_file)
                    
                    # Upload audio file to R2 for traceability (before cleanup)
                    r2_url = None
                    if upload_to_r2 and os.path.exists(audio_file):
                        r2_url = self._upload_audio_to_r2(audio_file, i + 1)
                    
                    segment_result = {
                        'segment_number': i + 1,
                        'audio_file': os.path.basename(audio_file),
                        'audio_url': r2_url,  # NEW: R2 URL for traceability
                        'transcript': transcript,
                        'detected_language': language,
                        'confidence': confidence,
                        'has_speech': bool(transcript and len(transcript.strip()) > 0),
                        'file_size': os.path.getsize(audio_file) if os.path.exists(audio_file) else 0
                    }
                    
                    segment_results.append(segment_result)
                    
                    if transcript:
                        all_transcripts.append(transcript)
                        print(f"AudioAI[{self.device_name}]: Segment {i+1} transcript: '{transcript[:50]}{'...' if len(transcript) > 50 else ''}' (lang: {language}, conf: {confidence:.2f})")
                        
                        # Early stop optimization: if we found speech and language, no need to process more segments
                        if early_stop and language != 'unknown' and confidence > 0.5:
                            remaining_segments = len(audio_files) - (i + 1)
                            if remaining_segments > 0:
                                print(f"AudioAI[{self.device_name}]: ⚡ Early stop: Speech detected with language '{language}' (confidence: {confidence:.2f}), skipping {remaining_segments} remaining segment(s)")
                                early_stopped = True
                                break
                    else:
                        print(f"AudioAI[{self.device_name}]: Segment {i+1}: No speech detected")
                        
                except Exception as e:
                    print(f"AudioAI[{self.device_name}]: Error analyzing segment {i+1}: {e}")
                    segment_results.append({
                        'segment_number': i + 1,
                        'audio_file': os.path.basename(audio_file) if audio_file else 'unknown',
                        'transcript': '',
                        'detected_language': 'unknown',
                        'confidence': 0.0,
                        'has_speech': False,
                        'error': str(e)
                    })
            
            # Combine results
            combined_transcript = ' '.join(all_transcripts).strip()
            
            # Determine overall language (most confident detection)
            detected_language = 'unknown'
            max_confidence = 0.0
            
            for result in segment_results:
                if result.get('confidence', 0) > max_confidence and result.get('detected_language') != 'unknown':
                    detected_language = result.get('detected_language')
                    max_confidence = result.get('confidence', 0)
            
            # Calculate overall confidence
            confidences = [r.get('confidence', 0) for r in segment_results if r.get('has_speech')]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Count successful segments
            successful_segments = len([r for r in segment_results if r.get('has_speech')])
            
            # Create detection message
            if combined_transcript:
                early_stop_info = " (early stopped)" if early_stopped else ""
                detection_message = f"Speech detected in {successful_segments}/{len(segment_results)} segments{early_stop_info}: '{combined_transcript[:100]}{'...' if len(combined_transcript) > 100 else ''}'"
            else:
                detection_message = f"No speech detected in any of the {len(segment_results)} audio segments"
            
            # Collect R2 URLs for traceability
            audio_urls = [result.get('audio_url') for result in segment_results if result.get('audio_url')]
            uploaded_count = len(audio_urls)
            
            overall_result = {
                'success': True,
                'segments_analyzed': len(segment_results),  # Use actual processed segments, not total files
                'total_segments_available': len(audio_files),  # Track total segments available
                'successful_segments': successful_segments,
                'combined_transcript': combined_transcript,
                'detected_language': detected_language,
                'confidence': overall_confidence,
                'detection_message': detection_message,
                'segments': segment_results,
                'audio_urls': audio_urls,  # NEW: List of R2 URLs for traceability
                'uploaded_segments': uploaded_count,  # NEW: Count of uploaded segments
                'early_stopped': early_stopped,  # NEW: Track if processing was stopped early
                'analysis_type': 'local_whisper_transcription',
                'timestamp': datetime.now().isoformat()
            }
            
            # Log R2 upload summary
            if upload_to_r2:
                processed_info = f"{len(segment_results)}/{len(audio_files)}" if early_stopped else f"{len(audio_files)}"
                print(f"AudioAI[{self.device_name}]: R2 Upload Summary: {uploaded_count} audio segments uploaded (processed {processed_info} segments)")
                if audio_urls:
                    print(f"AudioAI[{self.device_name}]: Audio files available at: audio-analysis/{self.device_name.replace(' ', '_').lower()}/")
            
            # Clean up temporary audio files
            self._cleanup_audio_files(audio_files)
            
            return overall_result
            
        except Exception as e:
            print(f"AudioAI[{self.device_name}]: AI audio analysis error: {e}")
            # Clean up on error too
            self._cleanup_audio_files(audio_files)
            return {
                'success': False,
                'error': f'Local Whisper analysis failed: {str(e)}',
                'analysis_type': 'local_whisper_transcription'
            }
    
    def transcribe_audio_with_ai(self, audio_file: str) -> Tuple[str, str, float]:
        """
        Transcribe a single audio file using local Whisper (optimized for speed).
        
        Args:
            audio_file: Path to audio file (WAV format)
            
        Returns:
            Tuple of (transcript, detected_language, confidence)
        """
        try:
            if not os.path.exists(audio_file):
                print(f"AudioAI[{self.device_name}]: Audio file not found: {audio_file}")
                return '', 'unknown', 0.0
            
            # Use local Whisper for fast transcription
            try:
                import whisper
            except ImportError:
                print(f"AudioAI[{self.device_name}]: Whisper not installed - run 'pip install openai-whisper'")
                return '', 'unknown', 0.0
            
            # Load optimized Whisper model (use tiny/base for speed)
            # Global model cache to avoid reloading
            if not hasattr(self, '_whisper_model'):
                print(f"AudioAI[{self.device_name}]: Loading Whisper model (tiny - optimized for speed)...")
                self._whisper_model = whisper.load_model("tiny")  # ~39MB, fastest
                print(f"AudioAI[{self.device_name}]: Whisper model loaded successfully")
            
            # Transcribe with Whisper
            result = self._whisper_model.transcribe(
                audio_file,
                language='en',  # Assume English for speed (can be removed for auto-detect)
                fp16=False,     # Better compatibility
                verbose=False   # Reduce output noise
            )
            
            # Extract results
            transcript = result.get('text', '').strip()
            detected_language = result.get('language', 'en')
            
            # Convert language code to full name
            language_map = {
                'en': 'English', 'fr': 'French', 'de': 'German',
                'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese',
                'nl': 'Dutch', 'da': 'Danish', 'sv': 'Swedish'
            }
            detected_language_name = language_map.get(detected_language, detected_language)
            
            # Calculate confidence based on transcript length and content
            if transcript and len(transcript.strip()) > 0:
                # Simple confidence heuristic: longer transcripts = higher confidence
                confidence = min(0.95, 0.5 + (len(transcript) / 100))
                print(f"AudioAI[{self.device_name}]: Whisper detected speech: '{transcript[:50]}...' (Language: {detected_language_name})")
                return transcript, detected_language_name, confidence
            else:
                print(f"AudioAI[{self.device_name}]: Whisper found no speech in audio")
                return '', 'unknown', 0.0
                
        except Exception as e:
            print(f"AudioAI[{self.device_name}]: Audio transcription error: {e}")
            return '', 'unknown', 0.0
    
    # =============================================================================
    # Utility Methods
    # =============================================================================
    
    def _upload_audio_to_r2(self, audio_file: str, segment_number: int) -> Optional[str]:
        """
        Upload audio file to R2 storage for traceability.
        
        Args:
            audio_file: Local path to audio file
            segment_number: Segment number for naming
            
        Returns:
            R2 URL if successful, None if failed
        """
        try:
            if not os.path.exists(audio_file):
                print(f"AudioAI[{self.device_name}]: Audio file not found for upload: {audio_file}")
                return None
            
            # Import CloudflareUtils
            from shared.lib.utils.cloudflare_utils import get_cloudflare_utils
            uploader = get_cloudflare_utils()
            
            # Generate R2 path with timestamp and device context
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            device_context = self.device_name.replace(' ', '_').lower()
            filename = f"audio_segment_{segment_number}_{timestamp}.wav"
            
            # Use audio-analysis folder structure
            remote_path = f"audio-analysis/{device_context}/{filename}"
            
            # Prepare file mapping with correct content type for WAV files
            file_mappings = [{
                'local_path': audio_file,
                'remote_path': remote_path,
                'content_type': 'audio/wav'  # Explicit content type for audio files
            }]
            
            print(f"AudioAI[{self.device_name}]: Uploading audio segment {segment_number} to R2...")
            
            # Upload to R2
            upload_result = uploader.upload_files(file_mappings)
            
            if upload_result['uploaded_files']:
                r2_url = upload_result['uploaded_files'][0]['url']
                file_size = upload_result['uploaded_files'][0]['size']
                print(f"AudioAI[{self.device_name}]: Audio segment {segment_number} uploaded successfully ({file_size} bytes)")
                print(f"AudioAI[{self.device_name}]: R2 URL: {r2_url}")
                return r2_url
            else:
                error_msg = upload_result['failed_uploads'][0]['error'] if upload_result['failed_uploads'] else 'Unknown upload error'
                print(f"AudioAI[{self.device_name}]: Failed to upload audio segment {segment_number}: {error_msg}")
                return None
                
        except Exception as e:
            print(f"AudioAI[{self.device_name}]: Error uploading audio segment {segment_number} to R2: {e}")
            return None
    
    def _cleanup_audio_files(self, audio_files: List[str]):
        """Clean up temporary audio files."""
        for audio_file in audio_files:
            try:
                if os.path.exists(audio_file):
                    os.unlink(audio_file)
                    print(f"AudioAI[{self.device_name}]: Cleaned up temporary audio file: {os.path.basename(audio_file)}")
            except Exception as e:
                print(f"AudioAI[{self.device_name}]: Error cleaning up {audio_file}: {e}")
    
    def get_audio_analysis_summary(self, audio_result: Dict[str, Any]) -> str:
        """
        Generate a summary string for audio analysis results.
        
        Args:
            audio_result: Audio analysis result dictionary
            
        Returns:
            Formatted summary string for logging
        """
        if not audio_result.get('success'):
            return f"Audio analysis failed: {audio_result.get('error', 'Unknown error')}"
        
        segments_analyzed = audio_result.get('segments_analyzed', 0)
        successful_segments = audio_result.get('successful_segments', 0)
        combined_transcript = audio_result.get('combined_transcript', '')
        detected_language = audio_result.get('detected_language', 'unknown')
        confidence = audio_result.get('confidence', 0.0)
        
        if combined_transcript:
            transcript_preview = combined_transcript[:100] + "..." if len(combined_transcript) > 100 else combined_transcript
            return f"Speech detected in {successful_segments}/{segments_analyzed} segments: '{transcript_preview}' (Language: {detected_language}, Confidence: {confidence:.2f})"
        else:
            return f"No speech detected in {segments_analyzed} audio segments"
