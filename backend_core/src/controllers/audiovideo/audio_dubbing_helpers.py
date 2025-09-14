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
        self.device_name = device_name
        self._spleeter_separator = None
        
    def separate_audio_tracks(self, audio_file: str) -> Dict[str, str]:
        """Separate audio into vocals and background using Spleeter."""
        try:
            from spleeter.separator import Separator
            
            if not self._spleeter_separator:
                print(f"Dubbing[{self.device_name}]: Loading Spleeter model...")
                self._spleeter_separator = Separator("spleeter:2stems")
            
            output_dir = tempfile.mkdtemp()
            self._spleeter_separator.separate_to_file(audio_file, output_dir)
            
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            vocals_path = os.path.join(output_dir, base_name, 'vocals.wav')
            background_path = os.path.join(output_dir, base_name, 'accompaniment.wav')
            
            print(f"Dubbing[{self.device_name}]: Audio separated successfully")
            return {'vocals': vocals_path, 'background': background_path}
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Separation failed: {e}")
            return {}
    
    def generate_dubbed_speech(self, text: str, language: str) -> Optional[str]:
        """Generate speech from text using gTTS."""
        try:
            from gtts import gTTS
            
            gtts_lang_map = {'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it', 'pt': 'pt'}
            gtts_lang = gtts_lang_map.get(language, 'en')
            
            tts = gTTS(text=text, lang=gtts_lang, slow=False)
            output_file = tempfile.mktemp(suffix='.mp3')
            tts.save(output_file)
            
            # Convert to WAV
            wav_file = output_file.replace('.mp3', '.wav')
            subprocess.run(['ffmpeg', '-i', output_file, '-ar', '44100', '-ac', '2', wav_file, '-y'], 
                          capture_output=True, check=True)
            os.remove(output_file)
            
            print(f"Dubbing[{self.device_name}]: Speech generated for {language}")
            return wav_file
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Speech generation failed: {e}")
            return None
    
    def mix_dubbed_audio(self, background_file: str, dubbed_voice_file: str, original_duration: float) -> Optional[str]:
        """Mix background audio with dubbed voice."""
        try:
            from pydub import AudioSegment
            
            background = AudioSegment.from_file(background_file)
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
            
            # Mix with volume adjustment
            background = background - 10  # Lower background
            dubbed_voice = dubbed_voice + 5   # Boost voice
            mixed = background.overlay(dubbed_voice)
            
            output_file = tempfile.mktemp(suffix='.wav')
            mixed.export(output_file, format="wav")
            
            print(f"Dubbing[{self.device_name}]: Audio mixed successfully")
            return output_file
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Audio mixing failed: {e}")
            return None
    
    def create_dubbed_video(self, video_file: str, dubbed_audio_file: str) -> Optional[str]:
        """Combine original video with dubbed audio track."""
        try:
            output_file = video_file.replace('.mp4', '_dubbed.mp4')
            
            subprocess.run([
                'ffmpeg', '-i', video_file, '-i', dubbed_audio_file,
                '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
                '-shortest', output_file, '-y'
            ], capture_output=True, check=True)
            
            print(f"Dubbing[{self.device_name}]: Dubbed video created")
            return output_file
            
        except Exception as e:
            print(f"Dubbing[{self.device_name}]: Video creation failed: {e}")
            return None
