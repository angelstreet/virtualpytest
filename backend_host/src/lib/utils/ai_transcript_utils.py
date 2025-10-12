"""AI-powered transcript enhancement and translation"""

import json
import time
from typing import Dict, Any, List
from shared.src.lib.utils.ai_utils import call_text_ai

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
        
        prompt = f"""Fix transcription errors and translate this {source_language} text.

Original text:
{text}

Instructions:
1. Fix spelling, grammar, and punctuation errors
2. Correct misheard words using context
3. Translate to: {', '.join(target_names)}

Respond with JSON only:
{{
    "enhanced_original": "corrected original text",
    "translations": {{
        "fr": "French translation",
        "en": "English translation",
        "es": "Spanish translation",
        "de": "German translation",
        "it": "Italian translation"
    }}
}}"""

        result = call_text_ai(prompt, max_tokens=1500, temperature=0.1)
        
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

