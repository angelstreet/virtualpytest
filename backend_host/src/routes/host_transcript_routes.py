"""Host Transcript Routes - On-demand translation and dubbing"""

from flask import Blueprint, request, jsonify
import os
import json
import time
from pathlib import Path
from datetime import datetime

host_transcript_bp = Blueprint('host_transcript', __name__, url_prefix='/host/transcript')


@host_transcript_bp.route('/translate-chunk', methods=['POST'])
def translate_chunk():
    """Translate a transcript chunk on-demand using AI"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id')
        hour = data.get('hour')
        chunk_index = data.get('chunk_index')
        target_language = data.get('language')
        
        if not all([device_id, hour is not None, chunk_index is not None, target_language]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        # Get device paths
        from shared.src.lib.utils.storage_path_utils import get_device_base_path, get_transcript_path
        device_base_path = get_device_base_path(device_id)
        transcript_base = get_transcript_path(device_id)
        transcript_dir = os.path.join(transcript_base, str(hour))
        
        # Check if translation already exists
        translated_file = os.path.join(transcript_dir, f'chunk_10min_{chunk_index}_{target_language}.json')
        if os.path.exists(translated_file):
            with open(translated_file, 'r') as f:
                cached_data = json.load(f)
            return jsonify({
                'success': True,
                'transcript': cached_data.get('transcript', ''),
                'cached': True,
                'language': target_language
            })
        
        # Load original transcript
        original_file = os.path.join(transcript_dir, f'chunk_10min_{chunk_index}.json')
        if not os.path.exists(original_file):
            return jsonify({
                'success': False,
                'error': 'Original transcript not found'
            }), 404
        
        with open(original_file, 'r') as f:
            original_data = json.load(f)
        
        original_text = original_data.get('transcript', '')
        if not original_text or len(original_text) < 20:
            return jsonify({
                'success': False,
                'error': 'Transcript too short'
            }), 400
        
        # Translate using AI (single language only!)
        from backend_host.src.lib.utils.ai_transcript_utils import enhance_and_translate_transcript
        
        start_time = time.time()
        ai_result = enhance_and_translate_transcript(
            text=original_text,
            source_language=original_data.get('language', 'unknown'),
            target_languages=[target_language]  # Only one language!
        )
        
        if not ai_result['success']:
            return jsonify({
                'success': False,
                'error': f"AI translation failed: {ai_result.get('error')}"
            }), 500
        
        translated_text = ai_result.get('translations', {}).get(target_language)
        if not translated_text:
            return jsonify({
                'success': False,
                'error': f"No translation returned for {target_language}"
            }), 500
        
        # Cache the translation
        os.makedirs(transcript_dir, exist_ok=True)
        translated_data = original_data.copy()
        translated_data['transcript'] = translated_text
        translated_data['source_language'] = original_data.get('language')
        translated_data['translated_to'] = target_language
        translated_data['translation_timestamp'] = datetime.now().isoformat()
        translated_data['processing_time'] = ai_result['processing_time']
        
        with open(translated_file + '.tmp', 'w') as f:
            json.dump(translated_data, f, indent=2)
        os.rename(translated_file + '.tmp', translated_file)
        
        # Update manifest
        from backend_host.scripts.hot_cold_archiver import update_transcript_manifest
        update_transcript_manifest(
            device_base_path=device_base_path,
            hour=hour,
            chunk_index=chunk_index,
            chunk_path=original_file,
            has_mp3=original_data.get('mp3_file') is not None
        )
        
        print(f"[@host_transcript] ✅ Translated {device_id}/{hour}/{chunk_index} to {target_language} in {ai_result['processing_time']:.2f}s")
        
        return jsonify({
            'success': True,
            'transcript': translated_text,
            'cached': False,
            'language': target_language,
            'processing_time': ai_result['processing_time']
        })
        
    except Exception as e:
        import traceback
        print(f"[@host_transcript] ❌ Translation error: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

