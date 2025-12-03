"""
Host Translation Routes - Handle Google Translate processing on Host machines
"""

from flask import Blueprint, request, jsonify
import sys
import os

from backend_host.src.lib.utils.translation_utils import batch_translate_restart_content, translate_text, detect_language_from_text
from shared.src.lib.utils.storage_path_utils import get_device_base_path, sanitize_folder_name

import json

# Create blueprint
host_translation_bp = Blueprint('host_translation', __name__)

@host_translation_bp.route('/host/translate/restart-batch', methods=['POST'])
def translate_restart_batch():
    """
    Handle batch translation of restart video content on Host.
    Processes all content types (video summary, audio transcript, frame descriptions, subtitles).
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        content_blocks = data.get('content_blocks')
        target_language = data.get('target_language')
        
        if not content_blocks or not target_language:
            return jsonify({
                'success': False,
                'error': 'Missing content_blocks or target_language'
            }), 400
        
        print(f"[HOST_TRANSLATION] 🌐 Processing batch translation to {target_language}")
        print(f"[HOST_TRANSLATION] Content sections: {list(content_blocks.keys())}")
        
        # Process translation on Host (uses async Google Translate)
        result = batch_translate_restart_content(content_blocks, target_language)
        
        if result['success']:
            print(f"[HOST_TRANSLATION] ✅ Batch translation completed successfully")
            return jsonify(result)
        else:
            print(f"[HOST_TRANSLATION] ❌ Batch translation failed: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        print(f"[HOST_TRANSLATION] 💥 Exception in batch translation: {e}")
        return jsonify({
            'success': False,
            'error': f'Host translation error: {str(e)}'
        }), 500

@host_translation_bp.route('/host/translate/text', methods=['POST'])
def translate_text_endpoint():
    """
    Handle individual text translation on Host.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        text = data.get('text')
        source_language = data.get('source_language', 'auto')
        target_language = data.get('target_language')
        method = data.get('method', 'google')
        
        if not text or not target_language:
            return jsonify({
                'success': False,
                'error': 'Missing text or target_language'
            }), 400
        
        print(f"[HOST_TRANSLATION] 🌐 Translating text: {source_language} → {target_language} (method: {method})")
        
        # Process translation on Host (uses async Google Translate)
        result = translate_text(text, source_language, target_language, method)
        
        if result['success']:
            print(f"[HOST_TRANSLATION] ✅ Text translation completed")
            return jsonify(result)
        else:
            print(f"[HOST_TRANSLATION] ❌ Text translation failed: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        print(f"[HOST_TRANSLATION] 💥 Exception in text translation: {e}")
        return jsonify({
            'success': False,
            'error': f'Host translation error: {str(e)}'
        }), 500

@host_translation_bp.route('/host/translate/detect', methods=['POST'])
def detect_text_language():
    """Detect language of text - Host side implementation"""
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

@host_translation_bp.route('/host/<capture_folder>/translate-segments', methods=['POST'])
def translate_segments(capture_folder):
    """
    Translate transcript using BATCH translation (full text as ONE block)
    Much faster than translating segment-by-segment!
    """
    try:
        # Security: sanitize capture_folder to prevent path traversal
        capture_folder = sanitize_folder_name(capture_folder)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    try:
        data = request.get_json()
        
        hour = data.get('hour')
        chunk_index = data.get('chunk_index')
        target_language = data.get('target_language')
        source_language = data.get('source_language', 'en')
        
        if hour is None or chunk_index is None or not target_language:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Use centralized path utility
        from shared.src.lib.utils.storage_path_utils import get_transcript_chunk_path
        transcript_file = get_transcript_chunk_path(capture_folder, hour, chunk_index)
        
        if not os.path.exists(transcript_file):
            return jsonify({'success': False, 'error': 'Transcript not found'}), 404
        
        # Load transcript JSON
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        # Check if already translated and cached
        if 'segments' in transcript_data and transcript_data['segments']:
            first_seg = transcript_data['segments'][0]
            if 'translations' in first_seg and target_language in first_seg['translations']:
                print(f"[HOST_TRANSLATION] ✨ Using cached translations for hour {hour}, chunk {chunk_index}")
                cached_translations = [
                    seg.get('translations', {}).get(target_language, seg.get('text', ''))
                    for seg in transcript_data['segments']
                ]
                return jsonify({
                    'success': True,
                    'translated_segments': cached_translations,
                    'cached': True
                })
        
        # NEW: Use FULL TRANSCRIPT for single batch translation (FAST!)
        full_transcript = transcript_data.get('transcript', '')
        
        if not full_transcript:
            # Fallback: reconstruct from segments
            full_transcript = ' '.join([seg.get('text', '') for seg in transcript_data.get('segments', [])])
        
        if not full_transcript.strip():
            return jsonify({'success': True, 'translated_segments': [], 'cached': False})
        
        print(f"[HOST_TRANSLATION] 🌐 Translating FULL transcript (hour {hour}, chunk {chunk_index}) to {target_language}")
        print(f"[HOST_TRANSLATION] 📝 Text length: {len(full_transcript)} chars")
        
        # Translate ENTIRE transcript as ONE block (single API call!)
        import time
        start = time.time()
        result = translate_text(full_transcript, source_language, target_language, 'google')
        elapsed = time.time() - start
        
        if not result.get('success'):
            return jsonify({'success': False, 'error': 'Translation failed'}), 500
        
        translated_full_text = result.get('translated_text', '')
        print(f"[HOST_TRANSLATION] ⚡ Translated in {elapsed:.2f}s")
        
        # Map translated text back to segments by matching sentence boundaries
        segments = transcript_data.get('segments', [])
        translated_segments = []
        
        if segments:
            # Use sentence splitting for better accuracy
            import re
            # Split on sentence boundaries
            original_sentences = [seg.get('text', '').strip() for seg in segments]
            translated_sentences = re.split(r'([.!?]+\s+)', translated_full_text)
            
            # Recombine punctuation with sentences
            combined = []
            for i in range(0, len(translated_sentences), 2):
                sentence = translated_sentences[i]
                if i + 1 < len(translated_sentences):
                    sentence += translated_sentences[i + 1]
                if sentence.strip():
                    combined.append(sentence.strip())
            
            # Match translated to original segments
            if len(combined) >= len(original_sentences):
                translated_segments = combined[:len(original_sentences)]
            else:
                # Fallback: pad with remaining text
                translated_segments = combined + [''] * (len(original_sentences) - len(combined))
        
        # Cache translations in JSON for all segments
        if 'segments' in transcript_data:
            for i, translation in enumerate(translated_segments):
                if i < len(transcript_data['segments']):
                    if 'translations' not in transcript_data['segments'][i]:
                        transcript_data['segments'][i]['translations'] = {}
                    transcript_data['segments'][i]['translations'][target_language] = translation
        
        # Also cache the full translated transcript
        if 'full_translations' not in transcript_data:
            transcript_data['full_translations'] = {}
        transcript_data['full_translations'][target_language] = translated_full_text
        
        # Save atomically
        temp_file = transcript_file + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2, ensure_ascii=False)
        os.replace(temp_file, transcript_file)
        
        print(f"[HOST_TRANSLATION] ✅ Translated and cached full transcript + {len(translated_segments)} segments")
        
        return jsonify({
            'success': True,
            'translated_segments': translated_segments,
            'translated_full_text': translated_full_text,
            'cached': False,
            'translation_time': elapsed
        })
        
    except Exception as e:
        print(f"[HOST_TRANSLATION] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@host_translation_bp.route('/host/<capture_folder>/translate-transcripts', methods=['POST'])
def translate_transcripts(capture_folder):
    """
    Translate transcript segments on-demand (caches in JSON)
    Minimal pattern from useRestart.ts - cached translations
    """
    try:
        # Security: sanitize capture_folder to prevent path traversal
        capture_folder = sanitize_folder_name(capture_folder)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        target_language = data.get('target_language')
        
        if not target_language:
            return jsonify({
                'success': False,
                'error': 'Missing target_language'
            }), 400
        
        device_path = get_device_base_path(capture_folder)
        transcript_path = os.path.join(device_path, 'transcript_segments.json')
        
        if not os.path.exists(transcript_path):
            return jsonify({
                'success': False,
                'error': f'Transcript file not found: {transcript_path}'
            }), 404
        
        with open(transcript_path, 'r') as f:
            transcript_data = json.load(f)
        
        print(f"[HOST_TRANSLATION] 🌐 Translating transcripts to {target_language} for {capture_folder}")
        
        # Translate segments that don't have translation yet
        translated_count = 0
        skipped_count = 0
        
        for segment in transcript_data['segments']:
            if not segment.get('transcript') or not segment.get('transcript').strip():
                continue
            
            # Initialize translations dict if not exists
            if 'translations' not in segment:
                segment['translations'] = {}
            
            # Check if translation already exists (cache hit)
            if target_language in segment['translations']:
                skipped_count += 1
                continue
            
            # Translate using existing helper (auto method uses Google Translate)
            result = translate_text(
                text=segment['transcript'],
                source_language=segment['language'],
                target_language=target_language,
                method='auto'  # Uses Google Translate (fast) with fallback
            )
            
            if result['success']:
                segment['translations'][target_language] = result['translated_text']
                translated_count += 1
        
        # Save updated JSON (atomic write)
        with open(transcript_path + '.tmp', 'w') as f:
            json.dump(transcript_data, f, indent=2)
        os.rename(transcript_path + '.tmp', transcript_path)
        
        print(f"[HOST_TRANSLATION] ✅ Translation complete: {translated_count} new, {skipped_count} cached")
        
        return jsonify({
            'success': True,
            'translated_count': translated_count,
            'skipped_count': skipped_count,
            'total_segments': len(transcript_data['segments']),
            'target_language': target_language
        })
        
    except Exception as e:
        print(f"[HOST_TRANSLATION] 💥 Exception in transcript translation: {e}")
        return jsonify({
            'success': False,
            'error': f'Transcript translation error: {str(e)}'
        }), 500

@host_translation_bp.route('/host/translate/health', methods=['GET'])
def translation_health():
    """
    Health check for translation services on Host.
    """
    try:
        # Test Google Translate availability
        from  backend_host.src.lib.utils.translation_utils import GOOGLE_TRANSLATE_AVAILABLE
        
        return jsonify({
            'success': True,
            'google_translate_available': GOOGLE_TRANSLATE_AVAILABLE,
            'status': 'healthy'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Translation health check failed: {str(e)}',
            'status': 'unhealthy'
        }), 500
