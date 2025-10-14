"""AI-powered transcript enhancement and translation"""

import json
import time
from typing import Dict, Any, List
from shared.src.lib.utils.ai_utils import call_text_ai

def translate_segments(
    segments: List[Dict[str, Any]],
    source_language: str,
    target_language: str
) -> Dict[str, Any]:
    start_time = time.time()
    
    try:
        texts = [f"{i+1}. {seg['text']}" for i, seg in enumerate(segments)]
        prompt = f"""Translate from {source_language} to {target_language}:

{chr(10).join(texts)}

JSON only:
{{"translations": ["text1", "text2", ...]}}"""
        
        estimated_tokens = max(3000, len('\n'.join(texts)) * 2)
        result = call_text_ai(prompt, max_tokens=estimated_tokens, temperature=0.0)
        
        if not result['success']:
            return {'success': False, 'error': result.get('error', 'AI call failed'), 'processing_time': time.time() - start_time}
        
        content = result['content'].strip().replace('```json', '').replace('```', '').strip()
        data = json.loads(content)
        translations = data.get('translations', [])
        
        if len(translations) != len(segments):
            return {'success': False, 'error': f'Translation count mismatch: {len(translations)} != {len(segments)}', 'processing_time': time.time() - start_time}
        
        translated_segments = []
        for i, seg in enumerate(segments):
            new_seg = seg.copy()
            new_seg['text'] = translations[i]
            translated_segments.append(new_seg)
        
        return {
            'success': True,
            'segments': translated_segments,
            'processing_time': time.time() - start_time
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'processing_time': time.time() - start_time}

def enhance_and_translate_transcript(
    text: str,
    source_language: str,
    target_languages: List[str]
) -> Dict[str, Any]:
    """
    Single AI call to enhance transcript and translate to all languages.
    
    Args:
        text: Original transcript text
        source_language: Detected language (e.g., 'german', 'french')
        target_languages: List of language codes ['fr', 'en', 'es', 'de', 'it']
    
    Returns:
        {
            'success': bool,
            'enhanced_original': str,
            'translations': {'fr': '...', 'en': '...', ...},
            'processing_time': float
        }
    """
    try:
        start_time = time.time()
        
        lang_names = {
            'fr': 'French',
            'en': 'English',
            'es': 'Spanish',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese'
        }
        
        target_names = [lang_names.get(code, code) for code in target_languages]
        
        # Calculate needed tokens:
        # - Enhanced original: ~len(text) 
        # - 5 translations: 5 * len(text)
        # - JSON overhead + AI verbosity: 1.3x
        # Formula: (text_chars * 6.5) / 3.5 chars_per_token
        # Simplified: text_chars * 2, minimum 5000
        estimated_tokens = max(5000, len(text) * 2)
        
        prompt = f"""Translate this {source_language} text to EXACTLY these {len(target_languages)} languages: {', '.join(target_languages)}.

IMPORTANT: Only include these language codes in your response, no others.

Text:
{text}

Respond with JSON only (no markdown):
{{
    "enhanced_original": "corrected text",
    "translations": {{
        "fr": "French translation",
        "en": "English translation",
        "es": "Spanish translation",
        "de": "German translation",
        "it": "Italian translation"
    }}
}}"""

        result = call_text_ai(prompt, max_tokens=estimated_tokens, temperature=0.0)
        
        if not result['success']:
            return {
                'success': False,
                'error': result.get('error', 'AI call failed'),
                'enhanced_original': text,
                'translations': {},
                'processing_time': time.time() - start_time
            }
        
        content = result['content'].strip()
        content = content.replace('```json', '').replace('```', '').strip()
        
        # Try parsing, if it fails try cleaning control characters
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            import re
            # Remove control characters (except newlines in context)
            content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
            data = json.loads(content)
        
        return {
            'success': True,
            'enhanced_original': data.get('enhanced_original', text),
            'translations': data.get('translations', {}),
            'processing_time': time.time() - start_time
        }
        
    except json.JSONDecodeError as e:
        return {
            'success': False,
            'error': f'JSON parse error: {e}',
            'enhanced_original': text,
            'translations': {},
            'processing_time': time.time() - start_time
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'enhanced_original': text,
            'translations': {},
            'processing_time': time.time() - start_time
        }

