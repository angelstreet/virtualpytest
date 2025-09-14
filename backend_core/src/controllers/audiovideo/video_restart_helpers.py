"""
Video Restart Helpers

Dedicated helper functions for restart video generation and analysis.
Extracted from FFmpegCaptureController to maintain clean separation of concerns.
"""

import os
import time
import uuid
import glob
import re
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple


class VideoRestartHelpers:
    """Helper class for restart video functionality."""
    
    def __init__(self, av_controller, device_name: str = "RestartVideo"):
        """
        Initialize restart video helpers.
        
        Args:
            av_controller: AV controller instance
            device_name: Name for logging purposes
        """
        self.av_controller = av_controller
        self.device_name = device_name
        self.capture_source = getattr(av_controller, 'capture_source', 'AV')
        
        # Get paths from controller
        self.video_stream_path = getattr(av_controller, 'video_stream_path', '')
        self.video_capture_path = getattr(av_controller, 'video_capture_path', '')
        
        # HLS configuration
        self.HLS_SEGMENT_DURATION = getattr(av_controller, 'HLS_SEGMENT_DURATION', 1)
        
        # Dubbing helpers (lazy initialization)
        self._dubbing_helpers = None
        
        # Translation cache: {video_id: {language: {frame_data: {...}}}}
        self._translation_cache = {}
    
    def generate_restart_video_only(self, duration_seconds: float = 10.0) -> Optional[Dict[str, Any]]:
        """Generate video only - fast response"""
        try:
            print(f"RestartHelpers[{self.device_name}]: Generating restart video ({duration_seconds}s)")
            
            # Video generation logic
            m3u8_path = os.path.join(self.video_capture_path, "output.m3u8")
            if not os.path.exists(m3u8_path):
                return None
            
            # Get segments
            segment_pattern = os.path.join(self.video_capture_path, "segment_*.ts")
            all_segment_paths = sorted(glob.glob(segment_pattern), key=lambda path: os.path.getmtime(path))
            
            segments_needed = int(duration_seconds / self.HLS_SEGMENT_DURATION) + 2
            segment_files = [(os.path.basename(p), p) for p in all_segment_paths[-segments_needed:]]
            
            if not segment_files:
                return None
            
            # Compress to MP4
            from shared.lib.utils.video_compression_utils import VideoCompressionUtils
            compressor = VideoCompressionUtils()
            
            video_filename = "restart_video.mp4"
            local_video_path = os.path.join(self.video_capture_path, video_filename)
            
            compression_result = compressor.compress_hls_to_mp4(
                m3u8_path=m3u8_path,
                segment_files=segment_files,
                output_path=local_video_path,
                compression_level="medium"
            )
            
            if not compression_result['success']:
                return None
            
            # Build URL
            video_url = self._build_video_url(video_filename)
            
            # Get screenshots for later analysis
            screenshot_urls = self._get_aligned_screenshots(segment_files)
            
            video_id = f"restart_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            return {
                'success': True,
                'video_url': video_url,
                'video_id': video_id,
                'screenshot_urls': screenshot_urls,
                'segment_count': len(segment_files)
            }
            
        except Exception as e:
            print(f"RestartHelpers[{self.device_name}]: Video generation error: {e}")
            return None
    
    def analyze_restart_audio(self, video_id: str, segment_files: List[tuple] = None) -> Optional[Dict[str, Any]]:
        """Analyze audio transcript using provided segment files from video generation"""
        try:
            from backend_core.src.controllers.verification.audio_ai_helpers import AudioAIHelpers
            
            # Use provided segment files if available, otherwise fallback to globbing
            if segment_files is None:
                print(f"RestartHelpers[{self.device_name}]: No segment files provided, falling back to globbing")
                segment_pattern = os.path.join(self.video_capture_path, "segment_*.ts")
                all_segment_paths = sorted(glob.glob(segment_pattern), key=lambda path: os.path.getmtime(path))
                segments_needed = int(10.0 / self.HLS_SEGMENT_DURATION) + 2
                segment_files = [(os.path.basename(p), p) for p in all_segment_paths[-segments_needed:]]
            else:
                print(f"RestartHelpers[{self.device_name}]: Using provided segment files ({len(segment_files)} segments)")
            
            audio_ai = AudioAIHelpers(self.av_controller, f"RestartVideo-{self.device_name}")
            audio_files = audio_ai.extract_audio_from_segments(segment_files, segment_count=len(segment_files))
            
            if not audio_files:
                return {
                    'success': True,
                    'audio_analysis': {
                        'success': True,
                        'speech_detected': False,
                        'combined_transcript': '',
                        'detected_language': 'unknown',
                        'confidence': 0.0
                    }
                }
            
            audio_analysis = audio_ai.analyze_audio_segments_ai(audio_files, upload_to_r2=True, early_stop=True)
            
            return {
                'success': True,
                'audio_analysis': {
                    'success': audio_analysis.get('success', False),
                    'speech_detected': audio_analysis.get('speech_detected', False),
                    'combined_transcript': audio_analysis.get('combined_transcript', ''),
                    'detected_language': audio_analysis.get('detected_language', 'unknown'),
                    'confidence': audio_analysis.get('confidence', 0.0)
                }
            }
            
        except Exception as e:
            print(f"RestartHelpers[{self.device_name}]: Audio analysis error: {e}")
            return {'success': False, 'error': str(e)}
    
    def analyze_restart_complete(self, video_id: str, screenshot_urls: list) -> Optional[Dict[str, Any]]:
        """Combined restart analysis: subtitles + summary in single optimized call"""
        try:
            from shared.lib.utils.build_url_utils import convertHostUrlToLocalPath
            from backend_core.src.controllers.verification.video import VideoVerificationController
            
            local_paths = [convertHostUrlToLocalPath(url) if url.startswith(('http://', 'https://')) else url for url in screenshot_urls]
            
            video_controller = VideoVerificationController(self.device_name)
            
            # Use the optimized combined analysis for each frame
            frame_subtitles = []
            frame_descriptions = []
            detected_language = 'unknown'
            
            for i, local_path in enumerate(local_paths):
                # Single AI call for both subtitle + description analysis
                combined_result = video_controller.analyze_image_complete(local_path, extract_text=True, include_description=True)
                
                if combined_result and combined_result.get('success'):
                    # Extract subtitle data
                    subtitle_data = combined_result.get('subtitle_analysis', {})
                    text = subtitle_data.get('combined_extracted_text', '').strip()
                    frame_text = text if text and text != 'No subtitles detected' else 'No subtitles detected'
                    frame_subtitles.append(f"Frame {i+1}: {frame_text}")
                    
                    # Update detected language from first successful detection
                    if detected_language == 'unknown' and subtitle_data.get('detected_language'):
                        detected_language = subtitle_data.get('detected_language')
                    
                    # Extract description data
                    description_data = combined_result.get('description_analysis', {})
                    description = description_data.get('response', '').strip()
                    if description and description != 'No description available':
                        frame_descriptions.append(f"Frame {i+1}: {description}")
                    else:
                        frame_descriptions.append(f"Frame {i+1}: No description available")
                else:
                    frame_subtitles.append(f"Frame {i+1}: No subtitles detected")
                    frame_descriptions.append(f"Frame {i+1}: No description available")
            
            # Generate video summary from frame descriptions
            if frame_descriptions:
                summary_query = f"Based on the {len(frame_descriptions)} frame descriptions, provide a concise summary of what happened in this video sequence."
                video_summary = video_controller.analyze_image_with_ai(local_paths[0], summary_query) if local_paths else "No video description available"
                if not video_summary or not video_summary.strip():
                    video_summary = f"Video sequence showing {len(frame_descriptions)} frames of activity"
            else:
                video_summary = "No video description available"
            
            # Combine subtitle analysis results
            subtitle_analysis = {
                'success': True,
                'subtitles_detected': any('No subtitles detected' not in fs for fs in frame_subtitles),
                'extracted_text': ' '.join([fs.split(': ', 1)[1] for fs in frame_subtitles if 'No subtitles detected' not in fs]),
                'detected_language': detected_language,
                'frame_subtitles': frame_subtitles
            }
            
            # Combine video analysis results
            video_analysis = {
                'success': True,
                'frame_descriptions': frame_descriptions,
                'video_summary': video_summary.strip(),
                'frames_analyzed': len(local_paths)
            }
            
            return {
                'success': True,
                'subtitle_analysis': subtitle_analysis,
                'video_analysis': video_analysis
            }
            
        except Exception as e:
            print(f"RestartHelpers[{self.device_name}]: Combined restart analysis error: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_restart_video_fast(self, duration_seconds: float = None, test_start_time: float = None, processing_time: float = None) -> Optional[Dict[str, Any]]:
        """
        Fast restart video generation - returns video URL + audio analysis only.
        Shows player immediately while AI analysis runs in background.
        """
        try:
            if duration_seconds is None:
                duration_seconds = 10.0
                
            print(f"RestartHelpers[{self.device_name}]: Compressing {duration_seconds}s HLS video to MP4")
            
            # Find the M3U8 file
            m3u8_path = os.path.join(self.video_capture_path, "output.m3u8")
            
            if not os.path.exists(m3u8_path):
                print(f"RestartHelpers[{self.device_name}]: No M3U8 file found at {m3u8_path}")
                return None
            
            # Wait for encoder to finish
            if test_start_time:
                print(f"RestartHelpers[{self.device_name}]: Waiting 5s for final segments to complete...")
                time.sleep(5)
            
            # Get segment files
            segment_files = self._get_recent_segments(duration_seconds)
            if not segment_files:
                print(f"RestartHelpers[{self.device_name}]: No video segments found")
                return None
            
            # Compress HLS segments to MP4
            from shared.lib.utils.video_compression_utils import VideoCompressionUtils
            compressor = VideoCompressionUtils()
            
            video_filename = "restart_video.mp4"
            local_video_path = os.path.join(self.video_capture_path, video_filename)
            
            compression_result = compressor.compress_hls_to_mp4(
                m3u8_path=m3u8_path,
                segment_files=segment_files,
                output_path=local_video_path,
                compression_level="medium"
            )
            
            if not compression_result['success']:
                print(f"RestartHelpers[{self.device_name}]: Video compression failed: {compression_result['error']}")
                return None
            
            print(f"RestartHelpers[{self.device_name}]: Compression complete - {compression_result['compression_ratio']:.1f}% size reduction")
            
            # Build video URL
            video_url = self._build_video_url(video_filename)
            
            # Get audio transcript
            audio_result = self._get_audio_transcript_locally(segment_files, duration_seconds)
            
            # Get screenshot URLs aligned with video segments
            screenshot_urls = self._get_video_screenshots(segment_files)
            
            # Generate unique video ID
            video_id = f"restart_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            analysis_data = {
                'audio_analysis': {
                    'success': audio_result.get('success', False),
                    'speech_detected': audio_result.get('speech_detected', False),
                    'combined_transcript': audio_result.get('combined_transcript', ''),
                    'detected_language': audio_result.get('detected_language', 'unknown'),
                    'confidence': audio_result.get('confidence', 0.0),
                    'segments_analyzed': audio_result.get('segments_analyzed', 0),
                    'execution_time_ms': 0
                },
                'screenshot_urls': screenshot_urls,
                'video_analysis': {
                    'success': False,
                    'pending': True,
                    'message': 'Video analysis will be performed asynchronously'
                },
                'subtitle_analysis': {
                    'success': False,
                    'pending': True,
                    'message': 'Subtitle analysis will be performed asynchronously'
                },
                'video_id': video_id,
                'segment_count': len(segment_files),
                'segment_files': segment_files,
                'analysis_complete': False,
                'timestamp': time.time(),
                'created_at': datetime.now().isoformat()
            }
            
            print(f"RestartHelpers[{self.device_name}]: Fast generation complete - Video ID: {video_id}")
            
            return {
                'success': True,
                'video_url': video_url,
                'analysis_data': analysis_data
            }
                
        except Exception as e:
            print(f"RestartHelpers[{self.device_name}]: Error generating fast restart video: {e}")
            return None
    
    def _get_recent_segments(self, duration_seconds: float) -> List[Tuple[str, str]]:
        """Get recent HLS segments for the specified duration"""
        try:
            segment_pattern = os.path.join(self.video_capture_path, "segment_*.ts")
            all_segment_paths = glob.glob(segment_pattern)
            
            # Sort by file modification time
            all_segment_paths.sort(key=lambda path: os.path.getmtime(path))
            
            # Convert to (filename, filepath) tuples
            all_segments = []
            for segment_path in all_segment_paths:
                if os.path.exists(segment_path):
                    filename = os.path.basename(segment_path)
                    all_segments.append((filename, segment_path))
            
            # Calculate segments needed
            segments_needed = int(duration_seconds / self.HLS_SEGMENT_DURATION) + 2
            
            if len(all_segments) < segments_needed:
                segment_files = all_segments
                actual_duration = len(all_segments) * self.HLS_SEGMENT_DURATION
                print(f"RestartHelpers[{self.device_name}]: Only {len(all_segments)} segments available ({actual_duration}s), using all")
            else:
                segment_files = all_segments[-segments_needed:]
                print(f"RestartHelpers[{self.device_name}]: Taking last {segments_needed} segments ({duration_seconds}s)")
            
            return segment_files
            
        except Exception as e:
            print(f"RestartHelpers[{self.device_name}]: Error getting recent segments: {e}")
            return []
    
    def _build_video_url(self, video_filename: str) -> str:
        """Build proper video URL using host URL building utilities"""
        try:
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            local_video_path = os.path.join(self.video_capture_path, video_filename)
            host = get_host_instance()
            video_url = buildHostImageUrl(host.to_dict(), local_video_path)
            return video_url
        except Exception:
            # Fallback to stream path
            return self.video_stream_path + "/" + video_filename
    
    def _get_aligned_screenshots(self, segment_files: List[Tuple[str, str]]) -> List[str]:
        """Get screenshots aligned with video segments"""
        try:
            capture_folder = f"{self.video_capture_path}/captures"
            
            # Find screenshot closest to first segment timestamp
            if not segment_files:
                return []
            
            first_segment_path = segment_files[0][1]
            first_segment_mtime = os.path.getmtime(first_segment_path)
            
            # Find all available screenshots
            pattern = os.path.join(capture_folder, "capture_*.jpg")
            all_screenshots = glob.glob(pattern)
            
            if not all_screenshots:
                return []
            
            # Find screenshot closest to first segment timestamp
            closest_screenshot = None
            min_time_diff = float('inf')
            for screenshot_path in all_screenshots:
                screenshot_mtime = os.path.getmtime(screenshot_path)
                time_diff = abs(screenshot_mtime - first_segment_mtime)
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_screenshot = screenshot_path
            
            if not closest_screenshot:
                return []
            
            # Extract number from closest screenshot filename
            closest_filename = os.path.basename(closest_screenshot)
            match = re.search(r'capture_(\d+)', closest_filename)
            if not match:
                return []
            
            start_number = int(match.group(1))
            
            # Get FPS from controller
            fps = getattr(self.av_controller, 'screenshot_fps', 5)
            screenshots_per_segment = int(self.HLS_SEGMENT_DURATION * fps)
            
            # Apply offset to account for segment/screenshot timing differences
            segment_offset = 3  # Hardcoded offset - go back 3 screenshots
            adjusted_start = start_number - segment_offset
            
            print(f"RestartHelpers[{self.device_name}]: Screenshot alignment - FPS:{fps}, PerSegment:{screenshots_per_segment}, Start:{start_number}, Offset:{segment_offset}, Adjusted:{adjusted_start}")
            
            # Get sequential screenshots aligned with segments
            aligned_screenshots = []
            screenshots_needed = len(segment_files)
            
            for i in range(screenshots_needed):
                screenshot_number = adjusted_start + (i * screenshots_per_segment)
                screenshot_patterns = [
                    f"capture_{screenshot_number}.jpg",
                    f"capture_{screenshot_number}_thumbnail.jpg"
                ]
                
                found_screenshot = None
                for pattern_name in screenshot_patterns:
                    screenshot_path = os.path.join(capture_folder, pattern_name)
                    if os.path.exists(screenshot_path):
                        found_screenshot = screenshot_path
                        break
                
                if found_screenshot:
                    aligned_screenshots.append(found_screenshot)
            
            # Convert to proper host URLs
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            screenshot_urls = []
            try:
                host = get_host_instance()
                host_dict = host.to_dict()
                
                for screenshot_path in aligned_screenshots:
                    screenshot_url = buildHostImageUrl(host_dict, screenshot_path)
                    screenshot_urls.append(screenshot_url)
            except Exception:
                # Fallback to relative paths
                for screenshot_path in aligned_screenshots:
                    filename = os.path.basename(screenshot_path)
                    screenshot_url = f"{self.video_stream_path}/captures/{filename}"
                    screenshot_urls.append(screenshot_url)
            
            print(f"RestartHelpers[{self.device_name}]: Found {len(screenshot_urls)} aligned screenshots: {[os.path.basename(url.split('/')[-1]) for url in screenshot_urls]}")
            return screenshot_urls
            
        except Exception as e:
            print(f"RestartHelpers[{self.device_name}]: Screenshot collection error: {e}")
            return []
    
    def _get_audio_transcript_locally(self, segment_files: List[Tuple[str, str]], duration_seconds: float) -> Dict[str, Any]:
        """Get audio transcript locally using the same segments as video generation"""
        try:
            from backend_core.src.controllers.verification.audio_ai_helpers import AudioAIHelpers
            
            audio_ai = AudioAIHelpers(self.av_controller, f"RestartVideo-{self.device_name}")
            
            print(f"RestartHelpers[{self.device_name}]: Using SAME {len(segment_files)} segments for audio as video ({duration_seconds}s)")
            
            audio_files = audio_ai.extract_audio_from_segments(segment_files, segment_count=len(segment_files))
            
            if not audio_files:
                return {
                    'success': True,
                    'speech_detected': False,
                    'combined_transcript': '',
                    'detected_language': 'unknown',
                    'confidence': 0.0,
                    'segments_analyzed': 0
                }
            
            # Analyze with AI
            audio_analysis = audio_ai.analyze_audio_segments_ai(audio_files, upload_to_r2=True, early_stop=True)
            
            if not audio_analysis.get('success'):
                return {
                    'success': False,
                    'speech_detected': False,
                    'combined_transcript': '',
                    'detected_language': 'unknown',
                    'confidence': 0.0,
                    'segments_analyzed': 0
                }
            
            return {
                'success': True,
                'speech_detected': audio_analysis.get('successful_segments', 0) > 0,
                'combined_transcript': audio_analysis.get('combined_transcript', ''),
                'detected_language': audio_analysis.get('detected_language', 'unknown'),
                'confidence': audio_analysis.get('confidence', 0.0),
                'segments_analyzed': audio_analysis.get('segments_analyzed', 0)
            }
            
        except Exception as e:
            print(f"RestartHelpers[{self.device_name}]: Audio analysis error: {e}")
            return {
                'success': False,
                'speech_detected': False,
                'combined_transcript': '',
                'detected_language': 'unknown',
                'confidence': 0.0,
                'segments_analyzed': 0,
                'error': str(e)
            }
    
    def _get_video_screenshots(self, segment_files: List[Tuple[str, str]]) -> List[str]:
        """Get screenshot URLs aligned with video segments"""
        return self._get_aligned_screenshots(segment_files)
    
    @property
    def dubbing_helpers(self):
        """Lazy initialization of dubbing helpers"""
        if self._dubbing_helpers is None:
            from .audio_dubbing_helpers import AudioDubbingHelpers
            self._dubbing_helpers = AudioDubbingHelpers(self.av_controller, self.device_name)
        return self._dubbing_helpers
    
    def generate_dubbed_restart_video(self, video_id: str, target_language: str, existing_transcript: str) -> Optional[Dict[str, Any]]:
        """Generate dubbed version of restart video using existing transcript."""
        try:
            print(f"RestartHelpers[{self.device_name}]: Starting dubbing to {target_language}")
            
             # Check translation cache first
             cache_key = video_id
             if cache_key in self._translation_cache and target_language in self._translation_cache[cache_key]:
                 print(f"RestartHelpers[{self.device_name}]: Using cached translation for {target_language}")
                 translation_result = self._translation_cache[cache_key][target_language]
             else:
                 # Batch translate with frame structure preservation
                 from shared.lib.utils.translation_utils import translate_text
                 
                 # Create structured batch input for single API call
                 batch_input = f"FRAME_STRUCTURE_TRANSLATION:\n{existing_transcript}\n\nPlease translate this maintaining any frame markers or structure."
                 
                 translation_result = translate_text(batch_input, 'en', target_language)
                 if not translation_result['success']:
                     print(f"RestartHelpers[{self.device_name}]: Translation failed")
                     return None
                 
                 # Cache the translation
                 if cache_key not in self._translation_cache:
                     self._translation_cache[cache_key] = {}
                 self._translation_cache[cache_key][target_language] = translation_result
                 print(f"RestartHelpers[{self.device_name}]: Cached batch translation for {target_language}")
            
            # Get original video file
            video_filename = "restart_video.mp4"
            video_file = os.path.join(self.video_capture_path, video_filename)
            
            if not os.path.exists(video_file):
                print(f"RestartHelpers[{self.device_name}]: Video file not found")
                return None
            
            # Extract audio from video
            audio_file = video_file.replace('.mp4', '.wav')
            subprocess.run(['ffmpeg', '-i', video_file, '-vn', '-acodec', 'pcm_s16le', 
                          '-ar', '44100', '-ac', '2', audio_file, '-y'], 
                          capture_output=True, check=True)
            
            # Separate audio tracks
            separated = self.dubbing_helpers.separate_audio_tracks(audio_file)
            if not separated:
                return None
            
            # Generate dubbed speech
            dubbed_voice = self.dubbing_helpers.generate_dubbed_speech(
                translation_result['translated_text'], target_language)
            if not dubbed_voice:
                return None
            
            # Get video duration
            result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 
                                   'format=duration', '-of', 'csv=p=0', video_file], 
                                   capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.stdout.strip() else 10.0
            
            # Mix audio
            final_audio = self.dubbing_helpers.mix_dubbed_audio(
                separated['background'], dubbed_voice, duration)
            if not final_audio:
                return None
            
            # Create dubbed video
            dubbed_video = self.dubbing_helpers.create_dubbed_video(video_file, final_audio)
            if not dubbed_video:
                return None
            
            # Build URL
            dubbed_filename = os.path.basename(dubbed_video)
            dubbed_url = self._build_video_url(dubbed_filename)
            
            print(f"RestartHelpers[{self.device_name}]: Dubbing completed")
            return {
                'success': True,
                'dubbed_video_url': dubbed_url,
                'target_language': target_language,
                'video_id': f"{video_id}_dubbed_{target_language}"
            }
            
        except Exception as e:
            print(f"RestartHelpers[{self.device_name}]: Dubbing error: {e}")
            return None
