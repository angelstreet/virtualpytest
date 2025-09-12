"""
Server Translation Routes

Routes for AI-powered text translation using the shared translation utilities.
"""

from flask import Blueprint, request, jsonify
import sys
import os

# Add shared lib to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

from lib.utils.translation_utils import translate_text, batch_translate_segments, detect_language_from_text

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
