"""
Server Translation Routes

Routes for AI-powered text translation using the shared translation utilities.
"""

from flask import Blueprint, request, jsonify
import sys
import os

# Add shared lib to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

from lib.utils.translation_utils import translate_text, batch_translate_segments, detect_language_from_text, batch_translate_restart_content

# Create blueprint
server_translation_bp = Blueprint('server_translation', __name__, url_prefix='/server/translate')

@server_translation_bp.route('/text', methods=['POST'])
def translate_single_text():
    """Translate a single text string"""
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        source_language = data.get('source_language', 'en')
        target_language = data.get('target_language', 'en')
        
        if not text.strip():
            return jsonify({
                'success': False,
                'error': 'Empty text provided'
            }), 400
        
        result = translate_text(text, source_language, target_language)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Translation error: {str(e)}'
        }), 500

@server_translation_bp.route('/batch', methods=['POST'])
def translate_batch_segments():
    """Translate multiple text segments"""
    try:
        data = request.get_json() or {}
        segments = data.get('segments', [])
        source_language = data.get('source_language', 'en')
        target_language = data.get('target_language', 'en')
        
        if not segments:
            return jsonify({
                'success': False,
                'error': 'No segments provided'
            }), 400
        
        result = batch_translate_segments(segments, source_language, target_language)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Batch translation error: {str(e)}'
        }), 500

@server_translation_bp.route('/restart-batch', methods=['POST'])
def translate_restart_batch():
    """Translate all restart video content in a single AI request"""
    try:
        data = request.get_json() or {}
        content_blocks = data.get('content_blocks', {})
        target_language = data.get('target_language', 'en')
        
        print(f"[SERVER_TRANSLATION] Batch translation request for language: {target_language}")
        print(f"[SERVER_TRANSLATION] Content blocks keys: {list(content_blocks.keys())}")
        
        if not content_blocks:
            print("[SERVER_TRANSLATION] ERROR: No content blocks provided")
            return jsonify({
                'success': False,
                'error': 'No content blocks provided'
            }), 400
        
        result = batch_translate_restart_content(content_blocks, target_language)
        
        print(f"[SERVER_TRANSLATION] Translation result: success={result.get('success', False)}")
        if not result.get('success', False):
            print(f"[SERVER_TRANSLATION] Translation error: {result.get('error', 'Unknown error')}")
            if 'openrouter_response' in result:
                print(f"[SERVER_TRANSLATION] OpenRouter response: {result['openrouter_response']}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[SERVER_TRANSLATION] EXCEPTION: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Batch translation error: {str(e)}'
        }), 500

@server_translation_bp.route('/detect', methods=['POST'])
def detect_text_language():
    """Detect language of text"""
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        
        if not text.strip():
            return jsonify({
                'success': False,
                'error': 'Empty text provided'
            }), 400
        
        result = detect_language_from_text(text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Language detection error: {str(e)}'
        }), 500
