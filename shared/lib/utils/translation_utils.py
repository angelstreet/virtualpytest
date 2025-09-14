"""
Translation Utilities - AI-powered text translation using existing AI infrastructure
"""

from typing import Dict, Any, Optional
from .ai_utils import call_text_ai

def translate_text(text: str, source_language: str, target_language: str) -> Dict[str, Any]:
    """
    Translate text using AI with language detection and context preservation.
    
    Args:
        text: Text to translate
        source_language: Source language code (e.g., 'en', 'es', 'fr')
        target_language: Target language code
        
    Returns:
        Dict with success status, translated text, and metadata
    """
    try:
        if not text or not text.strip():
            return {
                'success': False,
                'error': 'Empty text provided',
                'translated_text': '',
                'source_language': source_language,
                'target_language': target_language
            }
        
        # Skip translation if source and target are the same
        if source_language == target_language:
            return {
                'success': True,
                'translated_text': text,
                'source_language': source_language,
                'target_language': target_language,
                'skipped': True
            }
        
        # Language name mapping for better AI understanding
        language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi'
        }
        
        source_name = language_names.get(source_language, source_language)
        target_name = language_names.get(target_language, target_language)
        
        # Create translation prompt
        prompt = f"""Translate the following text from {source_name} to {target_name}.

IMPORTANT INSTRUCTIONS:
1. Provide ONLY the translated text - no explanations, no quotes, no additional text
2. Preserve the original meaning and context
3. Keep the same tone and style (formal/informal)
4. For subtitle text, keep it concise and readable
5. If the text is already in {target_name}, return it unchanged
6. Do not add any formatting or markdown
7. Do not include language detection metadata, confidence percentages, or technical annotations
8. Remove any text like "(ENGLISH, 95% confidence):" or similar metadata from your response

Text to translate:
{text}

Translation:"""

        # Call AI for translation
        result = call_text_ai(prompt, max_tokens=300, temperature=0.1)
        
        if result['success']:
            translated_text = result['content'].strip()
            
            # Clean up any unwanted formatting or quotes
            if translated_text.startswith('"') and translated_text.endswith('"'):
                translated_text = translated_text[1:-1]
            if translated_text.startswith("'") and translated_text.endswith("'"):
                translated_text = translated_text[1:-1]
            
            # Remove any confidence metadata that might have been included
            import re
            # Remove patterns like "Translated to Spanish(ENGLISH, 95% confidence):"
            translated_text = re.sub(r'^Translated to \w+\([^)]+\):\s*', '', translated_text)
            # Remove patterns like "(ENGLISH, 95% confidence):"
            translated_text = re.sub(r'\([A-Z]+,\s*\d+%\s*confidence\):\s*', '', translated_text)
            # Remove any remaining confidence metadata patterns
            translated_text = re.sub(r'\(\w+,\s*\d+%\s*confidence\):\s*', '', translated_text)
            
            translated_text = translated_text.strip()
            
            return {
                'success': True,
                'translated_text': translated_text,
                'source_language': source_language,
                'target_language': target_language,
                'original_text': text
            }
        else:
            return {
                'success': False,
                'error': f'Translation failed: {result.get("error", "Unknown error")}',
                'translated_text': '',
                'source_language': source_language,
                'target_language': target_language
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Translation error: {str(e)}',
            'translated_text': '',
            'source_language': source_language,
            'target_language': target_language
        }

def batch_translate_segments(segments: list, source_language: str, target_language: str) -> Dict[str, Any]:
    """
    Translate multiple text segments efficiently.
    
    Args:
        segments: List of text segments to translate
        source_language: Source language code
        target_language: Target language code
        
    Returns:
        Dict with success status and list of translated segments
    """
    try:
        if not segments:
            return {
                'success': True,
                'translated_segments': [],
                'source_language': source_language,
                'target_language': target_language
            }
        
        # Skip if same language
        if source_language == target_language:
            return {
                'success': True,
                'translated_segments': segments,
                'source_language': source_language,
                'target_language': target_language,
                'skipped': True
            }
        
        # Combine segments for batch translation
        combined_text = "\n---SEGMENT---\n".join(segments)
        
        # Translate combined text
        translation_result = translate_text(combined_text, source_language, target_language)
        
        if translation_result['success']:
            # Split back into segments
            translated_combined = translation_result['translated_text']
            translated_segments = translated_combined.split("\n---SEGMENT---\n")
            
            # Ensure we have the same number of segments
            if len(translated_segments) != len(segments):
                # Fallback to individual translation
                translated_segments = []
                for segment in segments:
                    individual_result = translate_text(segment, source_language, target_language)
                    if individual_result['success']:
                        translated_segments.append(individual_result['translated_text'])
                    else:
                        translated_segments.append(segment)  # Keep original if translation fails
            
            return {
                'success': True,
                'translated_segments': translated_segments,
                'source_language': source_language,
                'target_language': target_language,
                'original_segments': segments
            }
        else:
            return {
                'success': False,
                'error': translation_result['error'],
                'translated_segments': segments,  # Return originals on failure
                'source_language': source_language,
                'target_language': target_language
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Batch translation error: {str(e)}',
            'translated_segments': segments,  # Return originals on failure
            'source_language': source_language,
            'target_language': target_language
        }

def detect_language_from_text(text: str) -> Dict[str, Any]:
    """
    Detect language of text using AI.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dict with detected language code and confidence
    """
    try:
        if not text or not text.strip():
            return {
                'success': False,
                'error': 'Empty text provided',
                'language': 'unknown',
                'confidence': 0.0
            }
        
        prompt = f"""Detect the language of the following text and respond with ONLY the two-letter language code (e.g., en, es, fr, de, it, pt, ru, ja, ko, zh, ar, hi).

Text: {text}

Language code:"""

        result = call_text_ai(prompt, max_tokens=10, temperature=0.0)
        
        if result['success']:
            detected_code = result['content'].strip().lower()
            
            # Validate the code
            valid_codes = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar', 'hi']
            if detected_code in valid_codes:
                return {
                    'success': True,
                    'language': detected_code,
                    'confidence': 0.9  # High confidence for AI detection
                }
            else:
                return {
                    'success': False,
                    'error': f'Invalid language code detected: {detected_code}',
                    'language': 'unknown',
                    'confidence': 0.0
                }
        else:
            return {
                'success': False,
                'error': f'Language detection failed: {result.get("error", "Unknown error")}',
                'language': 'unknown',
                'confidence': 0.0
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Language detection error: {str(e)}',
            'language': 'unknown',
            'confidence': 0.0
        }
