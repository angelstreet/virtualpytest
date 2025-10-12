"""Host Transcript Routes - On-demand dubbed audio generation"""

from flask import Blueprint, request, jsonify
import os
import json
from pathlib import Path

host_transcript_bp = Blueprint('host_transcript', __name__, url_prefix='/host/transcript')

@host_transcript_bp.route('/generate-dubbed-audio', methods=['POST'])
def generate_dubbed_audio():
    """Generate dubbed audio on-demand for a specific chunk"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id')
        hour = data.get('hour')
        chunk_index = data.get('chunk_index')
        language = data.get('language')
        
        if not all([device_id, hour is not None, chunk_index is not None, language]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        # Get device base path
        from shared.src.lib.utils.storage_path_utils import get_device_base_path, get_cold_storage_path
        device_base_path = get_device_base_path(device_id)
        
        # Check if audio already exists
        audio_cold = get_cold_storage_path(device_id, 'audio')
        audio_file = os.path.join(audio_cold, str(hour), f'chunk_10min_{chunk_index}_{language}.mp3')
        
        if os.path.exists(audio_file):
            return jsonify({
                'success': True,
                'url': f'/audio/{hour}/chunk_10min_{chunk_index}_{language}.mp3',
                'status': 'ready',
                'cached': True
            })
        
        # Load transcript
        transcript_dir = os.path.join(device_base_path, 'transcript', str(hour))
        transcript_file = os.path.join(transcript_dir, f'chunk_10min_{chunk_index}_{language}.json')
        
        if not os.path.exists(transcript_file):
            return jsonify({
                'success': False,
                'error': f'Translation not available for {language}'
            }), 404
        
        # Generate dubbed audio
        from backend_host.src.lib.utils.audio_utils import generate_edge_tts_audio, EDGE_TTS_VOICE_MAP
        
        with open(transcript_file, 'r') as f:
            data = json.load(f)
        
        translated_text = data.get('transcript', '')
        if not translated_text:
            return jsonify({
                'success': False,
                'error': 'No transcript text found'
            }), 404
        
        voice_name = EDGE_TTS_VOICE_MAP.get(language)
        if not voice_name:
            return jsonify({
                'success': False,
                'error': f'Voice not available for {language}'
            }), 400
        
        # Create audio directory
        audio_hour_dir = os.path.join(audio_cold, str(hour))
        os.makedirs(audio_hour_dir, exist_ok=True)
        
        # Generate audio
        success = generate_edge_tts_audio(
            text=translated_text,
            language_code=language,
            output_path=audio_file,
            voice_name=voice_name
        )
        
        if not success or not os.path.exists(audio_file):
            return jsonify({
                'success': False,
                'error': 'Failed to generate dubbed audio'
            }), 500
        
        return jsonify({
            'success': True,
            'url': f'/audio/{hour}/chunk_10min_{chunk_index}_{language}.mp3',
            'status': 'ready',
            'cached': False,
            'size': os.path.getsize(audio_file)
        })
        
    except Exception as e:
        import traceback
        print(f"[@host_transcript] Error generating dubbed audio: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

