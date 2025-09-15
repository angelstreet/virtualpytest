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
            'background': f"{original_video_dir}/restart_original_background.wav",  # ✅ Consistent naming
            'vocals': f"{original_video_dir}/restart_original_vocals.wav",  # ✅ Consistent naming  
            'dubbed_voice_gtts': f"{original_video_dir}/restart_{language}_dubbed_voice_gtts.wav",
            'dubbed_voice_edge': f"{original_video_dir}/restart_{language}_dubbed_voice_edge.wav",
            'dubbed_voice_gtts_mp3': f"{original_video_dir}/restart_{language}_dubbed_voice_gtts.mp3",
            'dubbed_voice_edge_mp3': f"{original_video_dir}/restart_{language}_dubbed_voice_edge.mp3",
            'mixed_audio': f"{original_video_dir}/restart_{language}_mixed_audio.wav",
            'final_video': f"{original_video_dir}/restart_{language}_dubbed_video.mp4",
            'demucs_output': f"/tmp/restart_demucs"  # ✅ Cached - no language suffix
        }
        
    def separate_audio_tracks(self, audio_file: str, language: str, original_video_dir: str) -> Dict[str, str]:
        """Separate audio into vocals and background using Demucs - cached after first run."""
        try:
            import subprocess
            import shutil
            
            paths = self.get_file_paths(language, original_video_dir)
            
            # Check if background already exists (cached from previous separation)
            if os.path.exists(paths['background']) and os.path.exists(paths['vocals']):
                print(f"Dubbing[{self.device_name}]: Using cached background/vocals separation")
                return {'vocals': paths['vocals'], 'background': paths['background']}
            
            print(f"Dubbing[{self.device_name}]: Loading Demucs model for first-time separation...")
            
            # Run Demucs separation to fixed output directory with faster mdx_extra model
            cmd = [
                'python', '-m', 'demucs.separate',
                '--two-stems', 'vocals',  # Separate into vocals and no_vocals
                '--model', 'mdx_extra',  # Use faster model (3x speed improvement)
                '--out', paths['demucs_output'],
                audio_file
            ]
            
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Demucs creates: demucs_output/mdx_extra/{filename}/vocals.wav and no_vocals.wav
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            demucs_vocals = os.path.join(paths['demucs_output'], 'mdx_extra', base_name, 'vocals.wav')
            demucs_background = os.path.join(paths['demucs_output'], 'mdx_extra', base_name, 'no_vocals.wav')
            
            # Copy to cached locations (will be reused for all languages)
            if os.path.exists(demucs_vocals) and os.path.exists(demucs_background):
                shutil.copy2(demucs_vocals, paths['vocals'])
                shutil.copy2(demucs_background, paths['background'])
                print(f"Dubbing[{self.device_name}]: Audio separated and cached for reuse")
                return {'vocals': paths['vocals'], 'background': paths['background']}
            else:
                print(f"Dubbing[{self.device_name}]: Output files not found")
                return {}
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Separation failed: {e}")
            return {}
    
    
    # =============================================================================
    # 4-Step Dubbing Process Methods
    # =============================================================================
    
    def prepare_dubbing_audio_step(self, video_file: str, original_video_dir: str) -> Dict[str, Any]:
        """Step 1: Extract and separate audio (heavy operation ~20-35s)"""
        import time
        start_time = time.time()
        
        try:
            # Extract audio from video
            paths = self.get_file_paths('temp', original_video_dir)  # Use temp language for paths
            audio_file = paths['original_audio']
            
            print(f"Dubbing[{self.device_name}]: Step 1 - Extracting audio from video...")
            subprocess.run(['ffmpeg', '-i', video_file, '-vn', '-acodec', 'pcm_s16le', 
                          '-ar', '44100', '-ac', '2', audio_file, '-y'], 
                          capture_output=True, check=True)
            
            # Separate audio tracks (the heavy operation)
            print(f"Dubbing[{self.device_name}]: Step 1 - Separating audio tracks...")
            separated = self.separate_audio_tracks(audio_file, 'temp', original_video_dir)
            
            if not separated:
                return {
                    'success': False,
                    'error': 'Audio separation failed',
                    'duration_seconds': time.time() - start_time
                }
            
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 1 completed in {duration:.1f}s")
            
            return {
                'success': True,
                'step': 'audio_prepared',
                'duration_seconds': round(duration, 1),
                'message': f'Audio prepared in {duration:.1f}s (vocals + background separated)',
                'vocals_path': separated.get('vocals'),
                'background_path': separated.get('background')
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 1 failed after {duration:.1f}s: {e}")
            return {
                'success': False,
                'error': f'Audio preparation failed: {str(e)}',
                'duration_seconds': round(duration, 1)
            }
    
    def generate_gtts_speech_step(self, text: str, language: str, original_video_dir: str) -> Dict[str, Any]:
        """Step 2: Generate gTTS speech (~3-5s)"""
        import time
        start_time = time.time()
        
        try:
            from gtts import gTTS
            
            paths = self.get_file_paths(language, original_video_dir)
            
            print(f"Dubbing[{self.device_name}]: Step 2 - Generating gTTS speech for {language}...")
            
            gtts_lang_map = {'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it', 'pt': 'pt'}
            gtts_lang = gtts_lang_map.get(language, 'en')
            
            tts = gTTS(text=text, lang=gtts_lang, slow=False)
            temp_mp3 = f"/tmp/{self.device_name}_{language}_gtts_temp.mp3"
            tts.save(temp_mp3)
            
            # Convert to WAV and MP3
            subprocess.run(['ffmpeg', '-i', temp_mp3, '-ar', '44100', '-ac', '2', paths['dubbed_voice_gtts'], '-y'], 
                          capture_output=True, check=True)
            subprocess.run(['ffmpeg', '-i', temp_mp3, paths['dubbed_voice_gtts_mp3'], '-y'], 
                          capture_output=True, check=True)
            os.remove(temp_mp3)
            
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 2 completed in {duration:.1f}s")
            
            # Build URLs for preview
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            try:
                host = get_host_instance()
                gtts_mp3_url = buildHostImageUrl(host.to_dict(), paths['dubbed_voice_gtts_mp3'])
            except:
                # Fallback URL construction
                gtts_mp3_url = f"/host/stream/{os.path.basename(paths['dubbed_voice_gtts_mp3'])}"
            
            return {
                'success': True,
                'step': 'gtts_generated',
                'duration_seconds': round(duration, 1),
                'message': f'gTTS voice ready in {duration:.1f}s',
                'gtts_audio_url': gtts_mp3_url,
                'gtts_wav_path': paths['dubbed_voice_gtts']
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 2 failed after {duration:.1f}s: {e}")
            return {
                'success': False,
                'error': f'gTTS generation failed: {str(e)}',
                'duration_seconds': round(duration, 1)
            }
    
    def generate_edge_speech_step(self, text: str, language: str, original_video_dir: str) -> Dict[str, Any]:
        """Step 3: Generate Edge-TTS speech (~3-5s)"""
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
                'step': 'edge_generated',
                'duration_seconds': round(duration, 1),
                'message': f'Edge-TTS voice ready in {duration:.1f}s',
                'edge_audio_url': edge_mp3_url,
                'edge_wav_path': paths['dubbed_voice_edge']
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 3 failed after {duration:.1f}s: {e}")
            return {
                'success': False,
                'error': f'Edge-TTS generation failed: {str(e)}',
                'duration_seconds': round(duration, 1)
            }
    
    def create_dubbed_video_step(self, video_file: str, language: str, voice_choice: str = 'edge') -> Dict[str, Any]:
        """Step 4: Create final dubbed video (~5-8s)"""
        import time
        start_time = time.time()
        
        try:
            original_video_dir = os.path.dirname(video_file)
            paths = self.get_file_paths(language, original_video_dir)
            
            print(f"Dubbing[{self.device_name}]: Step 4 - Creating dubbed video with {voice_choice} voice...")
            
            # Get video duration
            result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 
                                   'format=duration', '-of', 'csv=p=0', video_file], 
                                   capture_output=True, text=True)
            duration_seconds = float(result.stdout.strip()) if result.stdout.strip() else 10.0
            
            # Mix audio with chosen voice
            use_gtts = voice_choice.lower() == 'gtts'
            final_audio = self.mix_dubbed_audio(language, duration_seconds, original_video_dir, use_gtts)
            if not final_audio:
                return {
                    'success': False,
                    'error': 'Audio mixing failed',
                    'duration_seconds': time.time() - start_time
                }
            
            # Create dubbed video
            dubbed_video = self.create_dubbed_video(video_file, language)
            if not dubbed_video:
                return {
                    'success': False,
                    'error': 'Video creation failed',
                    'duration_seconds': time.time() - start_time
                }
            
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 4 completed in {duration:.1f}s")
            
            # Build URLs for final video and both MP3 files
            from shared.lib.utils.build_url_utils import buildHostImageUrl
            from shared.lib.utils.host_utils import get_host_instance
            
            try:
                host = get_host_instance()
                host_dict = host.to_dict()
                dubbed_video_url = buildHostImageUrl(host_dict, dubbed_video)
                gtts_audio_url = buildHostImageUrl(host_dict, paths['dubbed_voice_gtts_mp3'])
                edge_audio_url = buildHostImageUrl(host_dict, paths['dubbed_voice_edge_mp3'])
            except:
                # Fallback URL construction
                dubbed_video_url = f"/host/stream/{os.path.basename(dubbed_video)}"
                gtts_audio_url = f"/host/stream/{os.path.basename(paths['dubbed_voice_gtts_mp3'])}"
                edge_audio_url = f"/host/stream/{os.path.basename(paths['dubbed_voice_edge_mp3'])}"
            
            return {
                'success': True,
                'step': 'video_created',
                'duration_seconds': round(duration, 1),
                'message': f'Dubbed video ready in {duration:.1f}s',
                'dubbed_video_url': dubbed_video_url,
                'gtts_audio_url': gtts_audio_url,
                'edge_audio_url': edge_audio_url,
                'voice_used': voice_choice
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"Dubbing[{self.device_name}]: Step 4 failed after {duration:.1f}s: {e}")
            return {
                'success': False,
                'error': f'Video creation failed: {str(e)}',
                'duration_seconds': round(duration, 1)
            }
    
    def mix_dubbed_audio(self, language: str, original_duration: float, original_video_dir: str, use_gtts: bool = False) -> Optional[str]:
        """Mix background audio with dubbed voice using fixed filenames."""
        try:
            from pydub import AudioSegment
            
            paths = self.get_file_paths(language, original_video_dir)
            
            background = AudioSegment.from_file(paths['background'])
            # Use Edge-TTS for video (default behavior)
            dubbed_voice_file = paths['dubbed_voice_gtts'] if use_gtts else paths['dubbed_voice_edge']
            dubbed_voice = AudioSegment.from_file(dubbed_voice_file)
            
            # Adjust durations
            target_ms = int(original_duration * 1000)
            if len(background) > target_ms:
                background = background[:target_ms]
            if len(dubbed_voice) > target_ms:
                dubbed_voice = dubbed_voice[:target_ms]
            elif len(dubbed_voice) < target_ms:
                silence = AudioSegment.silent(duration=target_ms - len(dubbed_voice))
                dubbed_voice = dubbed_voice + silence
            
            # Mix with volume adjustment - keep background at 100%
            # background = background  # Keep original volume (100%)
            mixed = background.overlay(dubbed_voice)
            
            # Export to fixed filename (auto-overwrite)
            mixed.export(paths['mixed_audio'], format="wav")
            
            print(f"Dubbing[{self.device_name}]: Audio mixed successfully using {'gTTS' if use_gtts else 'Edge-TTS'}")
            return paths['mixed_audio']
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Audio mixing failed: {e}")
            return None
    
    def create_dubbed_video(self, original_video: str, language: str) -> Optional[str]:
        """Combine original video with dubbed audio track directly in web directory."""
        try:
            original_dir = os.path.dirname(original_video)
            paths = self.get_file_paths(language, original_dir)
            
            subprocess.run([
                'ffmpeg', '-i', original_video, '-i', paths['mixed_audio'],
                '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
                '-shortest', paths['final_video'], '-y'
            ], capture_output=True, check=True)
            
            print(f"Dubbing[{self.device_name}]: Dubbed video created in web directory")
            return paths['final_video']
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Video creation failed: {e}")
            return None
    