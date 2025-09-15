"""
Audio Dubbing Helpers - Minimal implementation for voice dubbing with background preservation
"""

import os
import tempfile
import subprocess
from typing import Dict, Any, Optional


class AudioDubbingHelpers:
    """Helper class for audio dubbing functionality."""
    
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
            'dubbed_voice': f"{original_video_dir}/restart_{language}_dubbed_voice.wav",
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
            
            # Run Demucs separation to fixed output directory
            cmd = [
                'python', '-m', 'demucs.separate',
                '--two-stems', 'vocals',  # Separate into vocals and no_vocals
                '--out', paths['demucs_output'],
                audio_file
            ]
            
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Demucs creates: demucs_output/htdemucs/{filename}/vocals.wav and no_vocals.wav
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            demucs_vocals = os.path.join(paths['demucs_output'], 'htdemucs', base_name, 'vocals.wav')
            demucs_background = os.path.join(paths['demucs_output'], 'htdemucs', base_name, 'no_vocals.wav')
            
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
    
    def generate_dubbed_speech(self, text: str, language: str, original_video_dir: str) -> Optional[str]:
        """Generate speech from text using gTTS with fixed filename."""
        try:
            from gtts import gTTS
            
            paths = self.get_file_paths(language, original_video_dir)
            
            gtts_lang_map = {'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it', 'pt': 'pt'}
            gtts_lang = gtts_lang_map.get(language, 'en')
            
            tts = gTTS(text=text, lang=gtts_lang, slow=False)
            temp_mp3 = f"/tmp/{self.device_name}_{language}_temp.mp3"
            tts.save(temp_mp3)
            
            # Convert to WAV with fixed filename
            subprocess.run(['ffmpeg', '-i', temp_mp3, '-ar', '44100', '-ac', '2', paths['dubbed_voice'], '-y'], 
                          capture_output=True, check=True)
            os.remove(temp_mp3)
            
            print(f"Dubbing[{self.device_name}]: Speech generated for {language}")
            return paths['dubbed_voice']
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Speech generation failed: {e}")
            return None
    
    def mix_dubbed_audio(self, language: str, original_duration: float, original_video_dir: str) -> Optional[str]:
        """Mix background audio with dubbed voice using fixed filenames."""
        try:
            from pydub import AudioSegment
            
            paths = self.get_file_paths(language, original_video_dir)
            
            background = AudioSegment.from_file(paths['background'])
            dubbed_voice = AudioSegment.from_file(paths['dubbed_voice'])
            
            # Adjust durations
            target_ms = int(original_duration * 1000)
            if len(background) > target_ms:
                background = background[:target_ms]
            if len(dubbed_voice) > target_ms:
                dubbed_voice = dubbed_voice[:target_ms]
            elif len(dubbed_voice) < target_ms:
                silence = AudioSegment.silent(duration=target_ms - len(dubbed_voice))
                dubbed_voice = dubbed_voice + silence
            
            # Mix with volume adjustment
            background = background - 10  # Lower background
            dubbed_voice = dubbed_voice + 5   # Boost voice
            mixed = background.overlay(dubbed_voice)
            
            # Export to fixed filename (auto-overwrite)
            mixed.export(paths['mixed_audio'], format="wav")
            
            print(f"Dubbing[{self.device_name}]: Audio mixed successfully")
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
