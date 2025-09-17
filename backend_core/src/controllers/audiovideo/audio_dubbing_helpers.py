"""
Audio Dubbing Helpers - Minimal implementation for voice dubbing with background preservation
"""

import os
import tempfile
import subprocess
from typing import Dict, Any, Optional


class AudioDubbingHelpers:
    """Audio dubbing helpers with 4-step process for timeout avoidance."""
    
    def __init__(self, av_controller, device_name: str = "DubbingHelper"):
        self.av_controller = av_controller
        self.device_name = device_name.replace(" ", "_")  # Clean device name for filenames
        self.temp_dir = "/tmp"
        
    def get_file_paths(self, language: str, original_video_dir: str = "/tmp") -> Dict[str, str]:
        """Fixed filenames - background cached, language-specific for others"""
        
        return {
            'original_audio': f"{original_video_dir}/restart_original_audio.wav",
            'background': f"{original_video_dir}/restart_original_background.wav",
            'vocals': f"{original_video_dir}/restart_original_vocals.wav",
            'dubbed_voice_edge': f"{original_video_dir}/restart_{language}_dubbed_voice_edge.wav",
            'dubbed_voice_edge_mp3': f"{original_video_dir}/restart_{language}_dubbed_voice_edge.mp3",
            'mixed_audio': f"{original_video_dir}/restart_{language}_mixed_audio.wav",
            'final_video': f"{original_video_dir}/restart_{language}_dubbed_video.mp4",
            'demucs_output': f"/tmp/restart_demucs"
        }
        
    def separate_audio_tracks(self, audio_file: str, language: str, original_video_dir: str) -> Dict[str, str]:
        """Separate audio into vocals and background - Demucs disabled, use cached files if available."""
        try:
            paths = self.get_file_paths(language, original_video_dir)
            
            # Check if background already exists (cached from previous separation)
            if os.path.exists(paths['background']) and os.path.exists(paths['vocals']):
                print(f"Dubbing[{self.device_name}]: Using cached background/vocals separation")
                return {'vocals': paths['vocals'], 'background': paths['background']}
            
            print(f"Dubbing[{self.device_name}]: Demucs disabled - skipping audio separation")
            print(f"Dubbing[{self.device_name}]: Use fast dubbing method instead for new content")
            return {}
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Separation check failed: {e}")
            return {}
    
    
    # =============================================================================
    # 4-Step Dubbing Process Methods
    # =============================================================================
    
    def prepare_dubbing_audio_step(self, video_file: str, original_video_dir: str) -> Dict[str, Any]:
        """Step 1: Audio extraction only - fast method without separation (~2-3s)"""
        import time
        start_time = time.time()
        
        try:
            # Extract audio from video (only step needed for fast dubbing)
            paths = self.get_file_paths('temp', original_video_dir)
            audio_file = paths['original_audio']
            
            print(f"Dubbing[{self.device_name}]: Step 1 - Extracting audio from video (fast method)...")
            subprocess.run(['ffmpeg', '-i', video_file, '-vn', '-acodec', 'pcm_s16le', 
                          '-ar', '44100', '-ac', '2', audio_file, '-y'], 
                          capture_output=True, check=True)
            
            print(f"Dubbing[{self.device_name}]: Audio separation skipped - using fast dubbing method")
            
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 1 completed in {duration:.1f}s (fast method)")
            
            return {
                'success': True,
                'step': 'audio_prepared_fast',
                'duration_seconds': round(duration, 1),
                'message': f'Audio extracted in {duration:.1f}s (fast method - no separation)',
                'method': 'fast'
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 1 failed after {duration:.1f}s: {e}")
            return {
                'success': False,
                'error': f'Audio extraction failed: {str(e)}',
                'duration_seconds': round(duration, 1)
            }
    
    
    def generate_edge_speech_step(self, text: str, language: str, original_video_dir: str) -> Dict[str, Any]:
        """Generate Edge-TTS speech (~3-5s)"""
        import time
        start_time = time.time()
        
        try:
            import edge_tts
            import asyncio
            
            paths = self.get_file_paths(language, original_video_dir)
            
            print(f"Dubbing[{self.device_name}]: Step 3 - Generating Edge-TTS speech for {language}...")
            
            edge_lang_map = {
                'es': 'es-ES-ElviraNeural', 'fr': 'fr-FR-DeniseNeural', 
                'de': 'de-DE-KatjaNeural', 'it': 'it-IT-ElsaNeural', 
                'pt': 'pt-BR-FranciscaNeural'
            }
            edge_voice = edge_lang_map.get(language, 'en-US-JennyNeural')
            
            async def generate_edge_audio():
                communicate = edge_tts.Communicate(text, edge_voice)
                temp_mp3 = f"/tmp/{self.device_name}_{language}_edge_temp.mp3"
                await communicate.save(temp_mp3)
                
                # Convert to WAV and copy MP3
                subprocess.run(['ffmpeg', '-i', temp_mp3, '-ar', '44100', '-ac', '2', paths['dubbed_voice_edge'], '-y'], 
                              capture_output=True, check=True)
                subprocess.run(['cp', temp_mp3, paths['dubbed_voice_edge_mp3']], check=True)
                os.remove(temp_mp3)
            
            asyncio.run(generate_edge_audio())
            
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 3 completed in {duration:.1f}s")
            
            # Build URLs for preview
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            try:
                host = get_host_instance()
                edge_mp3_url = buildHostImageUrl(host.to_dict(), paths['dubbed_voice_edge_mp3'])
            except:
                # Fallback URL construction
                edge_mp3_url = f"/host/stream/{os.path.basename(paths['dubbed_voice_edge_mp3'])}"
            
            return {
                'success': True,
                'duration_seconds': round(duration, 1),
                'edge_audio_url': edge_mp3_url,
                'edge_wav_path': paths['dubbed_voice_edge']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_dubbed_video_step(self, video_file: str, language: str, voice_choice: str = 'edge') -> Dict[str, Any]:
        """Step 4: Create final dubbed video using fast method (~3-5s)"""
        import time
        start_time = time.time()
        
        try:
            original_video_dir = os.path.dirname(video_file)
            
            print(f"Dubbing[{self.device_name}]: Step 4 - Creating dubbed video with fast method...")
            
            # Use the fast dubbing method directly (mute original + overlay Edge-TTS)
            paths = self.get_file_paths(language, original_video_dir)
            
            # Simple FFmpeg: mute video + add new audio (no background mixing)
            subprocess.run([
                'ffmpeg', '-i', video_file, '-i', paths['dubbed_voice_edge'],
                '-c:v', 'copy',      # Copy video unchanged
                '-c:a', 'aac',       # Encode new audio
                '-map', '0:v:0',     # Video from input 0 (original video)
                '-map', '1:a:0',     # Audio from input 1 (Edge-TTS audio)
                '-shortest',         # Match shortest stream duration
                paths['final_video'], '-y'
            ], capture_output=True, check=True)
            
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 4 completed in {duration:.1f}s (fast method)")
            
            # Build URLs for final video and audio preview
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            try:
                host = get_host_instance()
                host_dict = host.to_dict()
                dubbed_video_url = buildHostImageUrl(host_dict, paths['final_video'])
                edge_audio_url = buildHostImageUrl(host_dict, paths['dubbed_voice_edge_mp3'])
            except:
                # Fallback URL construction
                dubbed_video_url = f"/host/stream/{os.path.basename(paths['final_video'])}"
                edge_audio_url = f"/host/stream/{os.path.basename(paths['dubbed_voice_edge_mp3'])}"
            
            return {
                'success': True,
                'dubbed_video_url': dubbed_video_url,
                'edge_audio_url': edge_audio_url,
                'duration_seconds': round(duration, 1),
                'method': 'fast_mute_overlay'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    
    def create_dubbed_video_fast_step(self, text: str, language: str, video_file: str, original_video_dir: str) -> Dict[str, Any]:
        """NEW: Fast 2-step dubbing without Demucs separation (~5-8s total)"""
        import time
        start_time = time.time()
        
        try:
            print(f"Dubbing[{self.device_name}]: Fast dubbing - generating Edge-TTS + muting video for {language}...")
            
            # Step 1: Generate Edge-TTS audio (reuse existing method)
            edge_result = self.generate_edge_speech_step(text, language, original_video_dir)
            if not edge_result.get('success'):
                return edge_result
            
            # Step 2: Mute original video + overlay Edge-TTS audio
            paths = self.get_file_paths(language, original_video_dir)
            
            print(f"Dubbing[{self.device_name}]: Fast dubbing - muting video and overlaying Edge-TTS audio...")
            
            # Simple FFmpeg: mute video + add new audio (no background mixing)
            subprocess.run([
                'ffmpeg', '-i', video_file, '-i', paths['dubbed_voice_edge'],
                '-c:v', 'copy',      # Copy video unchanged
                '-c:a', 'aac',       # Encode new audio
                '-map', '0:v:0',     # Video from input 0 (original video)
                '-map', '1:a:0',     # Audio from input 1 (Edge-TTS audio)
                '-shortest',         # Match shortest stream duration
                paths['final_video'], '-y'
            ], capture_output=True, check=True)
            
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Fast dubbing completed in {duration:.1f}s")
            
            # Build URLs for final video and audio preview
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            try:
                host = get_host_instance()
                host_dict = host.to_dict()
                dubbed_video_url = buildHostImageUrl(host_dict, paths['final_video'])
                edge_audio_url = buildHostImageUrl(host_dict, paths['dubbed_voice_edge_mp3'])
            except:
                # Fallback URL construction
                dubbed_video_url = f"/host/stream/{os.path.basename(paths['final_video'])}"
                edge_audio_url = f"/host/stream/{os.path.basename(paths['dubbed_voice_edge_mp3'])}"
            
            return {
                'success': True,
                'dubbed_video_url': dubbed_video_url,
                'edge_audio_url': edge_audio_url,
                'duration_seconds': round(duration, 1),
                'method': 'fast_mute_overlay'
            }
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Fast dubbing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    
    # =============================================================================
    # Audio Sync Methods (Reuse Dubbing Logic)
    # =============================================================================
    
    def sync_dubbed_video(self, language: str, timing_offset_ms: int, original_video_dir: str) -> Dict[str, Any]:
        """
        Sync dubbed video by applying timing to cached audio and reusing dubbing combine logic.
        
        Args:
            language: Language code (e.g., 'fr', 'es') or 'original'
            timing_offset_ms: Timing offset in milliseconds (+delay, -advance)
            original_video_dir: Directory containing cached components
            
        Returns:
            Dictionary with sync result
        """
        import time
        start_time = time.time()
        
        try:
            print(f"Dubbing[{self.device_name}]: Syncing {language} video with {timing_offset_ms:+d}ms timing")
            
            paths = self.get_file_paths(language, original_video_dir)
            
            # Step 1: Get cached silent video (create if needed)
            silent_video_path = os.path.join(original_video_dir, "restart_video_no_audio.mp4")
            if not os.path.exists(silent_video_path):
                # Create silent video from any available video
                source_video = self._find_source_video(original_video_dir, language)
                if not source_video:
                    return {'success': False, 'error': 'No source video found for silent video creation'}
                
                print(f"Dubbing[{self.device_name}]: Creating cached silent video...")
                subprocess.run([
                    'ffmpeg', '-i', source_video,
                    '-c:v', 'copy', '-an',
                    silent_video_path, '-y'
                ], capture_output=True, check=True)
                print(f"Dubbing[{self.device_name}]: Silent video cached")
            
            # Step 2: Get audio to sync
            if language == 'original':
                # For original language, extract from original video if not cached
                audio_to_sync = paths['original_audio']
                if not os.path.exists(audio_to_sync):
                    original_video = os.path.join(original_video_dir, "restart_original_video.mp4")
                    if os.path.exists(original_video):
                        print(f"Dubbing[{self.device_name}]: Extracting original audio...")
                        subprocess.run([
                            'ffmpeg', '-i', original_video,
                            '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                            audio_to_sync, '-y'
                        ], capture_output=True, check=True)
                    else:
                        return {'success': False, 'error': 'Original video not found for audio extraction'}
            else:
                # For dubbed languages, use cached dubbed audio
                audio_to_sync = paths['dubbed_voice_edge']
                if not os.path.exists(audio_to_sync):
                    return {'success': False, 'error': f'Dubbed audio not found: {audio_to_sync}'}
            
            # Step 3: Apply timing to audio
            sync_suffix = f"_sync{timing_offset_ms:+d}" if timing_offset_ms != 0 else ""
            timed_audio_path = os.path.join(original_video_dir, f"restart_{language}_audio{sync_suffix}.wav")
            
            if timing_offset_ms == 0:
                # No timing needed, use original audio
                timed_audio_path = audio_to_sync
            else:
                print(f"Dubbing[{self.device_name}]: Applying {timing_offset_ms:+d}ms timing to audio...")
                
                if timing_offset_ms > 0:
                    # Positive offset: delay audio
                    audio_filter = f"adelay={timing_offset_ms}"
                else:
                    # Negative offset: advance audio (trim from start)
                    trim_seconds = abs(timing_offset_ms) / 1000.0
                    audio_filter = f"atrim=start={trim_seconds}"
                
                subprocess.run([
                    'ffmpeg', '-i', audio_to_sync,
                    '-af', audio_filter,
                    timed_audio_path, '-y'
                ], capture_output=True, check=True)
                print(f"Dubbing[{self.device_name}]: Audio timing applied")
            
            # Step 4: Combine silent video + timed audio (reuse dubbing logic)
            sync_video_path = os.path.join(original_video_dir, f"restart_{language}_video{sync_suffix}.mp4")
            
            print(f"Dubbing[{self.device_name}]: Combining silent video with timed audio...")
            subprocess.run([
                'ffmpeg', '-i', silent_video_path, '-i', timed_audio_path,
                '-c:v', 'copy',      # Copy video unchanged
                '-c:a', 'aac',       # Encode audio
                '-map', '0:v:0',     # Video from silent video
                '-map', '1:a:0',     # Audio from timed audio
                '-shortest',         # Match shortest stream duration
                sync_video_path, '-y'
            ], capture_output=True, check=True)
            
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Sync completed in {duration:.1f}s")
            
            # Build URLs for synced video
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            try:
                host = get_host_instance()
                host_dict = host.to_dict()
                synced_video_url = buildHostImageUrl(host_dict, sync_video_path)
            except:
                # Fallback URL construction
                synced_video_url = f"/host/stream/{os.path.basename(sync_video_path)}"
            
            return {
                'success': True,
                'synced_video_url': synced_video_url,
                'timing_offset_ms': timing_offset_ms,
                'language': language,
                'duration_seconds': round(duration, 1),
                'method': 'cache_based_sync'
            }
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _find_source_video(self, original_video_dir: str, language: str) -> Optional[str]:
        """Find best source video for creating silent video"""
        # Priority order: dubbed video for language > original video > any video
        candidates = [
            os.path.join(original_video_dir, f"restart_{language}_dubbed_video.mp4"),
            os.path.join(original_video_dir, "restart_original_video.mp4"),
        ]
        
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        
        # Look for any restart video as fallback
        import glob
        pattern = os.path.join(original_video_dir, "restart_*.mp4")
        videos = glob.glob(pattern)
        return videos[0] if videos else None
    