"""
AI Utilities - Centralized AI Configuration and Interface

All AI calls with OpenRouter (primary) and Hugging Face (fallback).
No hardcoded models - everything configured here.
"""

import os
import base64
import json
import tempfile
import cv2
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Union

# =============================================================================
# AI Configuration - Centralized Models and Providers
# =============================================================================

AI_CONFIG = {
    'providers': {
        'openrouter': {
            'api_key_env': 'OPENROUTER_API_KEY',
            'base_url': 'https://openrouter.ai/api/v1/chat/completions',
            'headers': {
                'HTTP-Referer': 'https://virtualpytest.com',
                'X-Title': 'VirtualPyTest'
            },
            'models': {
                'text': 'microsoft/phi-3-mini-128k-instruct',
                'vision': 'qwen/qwen-2.5-vl-7b-instruct',
                'translation': 'microsoft/phi-3-mini-128k-instruct',
                'agent': 'google/gemini-2.0-flash-exp:free'  # meta-llama/llama-3.1-8b-instruct:free
            }
        },
        'huggingface': {
            'api_key_env': 'HUGGINGFACE_API_KEY',
            'base_url': 'https://api-inference.huggingface.co/models',
            'headers': {},
            'models': {
                'text': 'microsoft/DialoGPT-medium',
                'vision': 'Salesforce/blip-image-captioning-base', 
                'translation': 'Helsinki-NLP/opus-mt-en-de'
            }
        }
    },
    'defaults': {
        'primary_provider': 'openrouter',
        'fallback_provider': 'huggingface',
        'timeout': 60,
        'max_tokens': 1000,
        'temperature': 0.0
    }
}

AI_BATCH_CONFIG = {
    'batch_size': 4,
    'max_batch_size': 4,
    'timeout_seconds': 300,
    'max_tokens': 2000,
    'temperature': 0.0
}

# =============================================================================
# Helper Functions
# =============================================================================

def _format_timestamp(timestamp: float) -> str:
    """Convert Unix timestamp to readable HH:mm:ss format."""
    return datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')

# =============================================================================
# Clean AI Interface Functions
# =============================================================================

def call_text_ai(prompt: str, max_tokens: int = 200, temperature: float = 0.1, model: str = None) -> Dict[str, Any]:
    """Simple text AI call with OpenRouter only (no fallback)."""
    return _call_ai(prompt, task_type='text', max_tokens=max_tokens, temperature=temperature, model=model)

def call_vision_ai(prompt: str, image_input: Union[str, bytes], max_tokens: int = 300, temperature: float = 0.0) -> Dict[str, Any]:
    """Simple vision AI call with OpenRouter only (no fallback)."""
    return _call_ai(prompt, task_type='vision', image=image_input, max_tokens=max_tokens, temperature=temperature)

def _call_ai(prompt: str, task_type: str = 'text', image: Union[str, bytes] = None, 
             max_tokens: int = None, temperature: float = None, model: str = None) -> Dict[str, Any]:
    """
    Centralized AI call using OpenRouter only (no Hugging Face fallback).
    Fails fast if OpenRouter is not available.
    Enhanced with detailed error reporting and logging.
    """
    print(f"[AI_UTILS] Starting AI call - task_type: {task_type}, model: {model or 'default'}")
    
    # Set defaults
    max_tokens = max_tokens or AI_CONFIG['defaults']['max_tokens']
    temperature = temperature if temperature is not None else AI_CONFIG['defaults']['temperature']
    
    print(f"[AI_UTILS] Parameters - max_tokens: {max_tokens}, temperature: {temperature}")
    
    # Try OpenRouter only
    try:
        # Use custom model if provided, otherwise use configured model for task type
        ai_model = model or AI_CONFIG['providers']['openrouter']['models'].get(task_type)
        if not ai_model:
            error_msg = f'No OpenRouter model configured for task type: {task_type}'
            print(f"[AI_UTILS] ERROR: {error_msg}")
            print(f"[AI_UTILS] Available task types: {list(AI_CONFIG['providers']['openrouter']['models'].keys())}")
            return {'success': False, 'error': error_msg, 'content': '', 'provider_used': 'none'}
        
        print(f"[AI_UTILS] Using OpenRouter model: {ai_model}")
        result = _openrouter_call(prompt, ai_model, image, max_tokens, temperature)
        
        if result['success']:
            result['provider_used'] = 'openrouter'
            print(f"[AI_UTILS] ✅ OpenRouter call successful - content length: {len(result.get('content', ''))}")
            return result
        else:
            # OpenRouter failed, return detailed error
            error_msg = result.get('error', 'OpenRouter call failed')
            print(f"[AI_UTILS] ❌ OpenRouter call failed: {error_msg}")
            return {'success': False, 'error': f'AI call failed: {error_msg}', 'content': '', 'provider_used': 'openrouter'}
            
    except Exception as e:
        error_msg = f'AI call exception: {str(e)}'
        print(f"[AI_UTILS] ❌ {error_msg}")
        return {'success': False, 'error': error_msg, 'content': '', 'provider_used': 'openrouter'}

def _openrouter_call(prompt: str, model: str, image: Union[str, bytes] = None, 
                    max_tokens: int = 1000, temperature: float = 0.0) -> Dict[str, Any]:
    """OpenRouter API call with enhanced error handling and logging"""
    try:
        print(f"[AI_UTILS] OpenRouter call starting - model: {model}, max_tokens: {max_tokens}, temperature: {temperature}")
        
        # Get API key
        api_key = os.getenv(AI_CONFIG['providers']['openrouter']['api_key_env'])
        if not api_key:
            error_msg = 'OpenRouter API key not found in environment variables'
            print(f"[AI_UTILS] ERROR: {error_msg}")
            return {'success': False, 'error': error_msg, 'content': ''}
        
        print(f"[AI_UTILS] API key found, length: {len(api_key)} characters")
        
        # Prepare headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            **AI_CONFIG['providers']['openrouter']['headers']
        }
        
        print(f"[AI_UTILS] Headers prepared: {list(headers.keys())}")
        
        # Prepare message content
        if image:
            # Vision request
            image_b64 = _process_image_input(image)
            if not image_b64:
                return {'success': False, 'error': 'Failed to process image', 'content': ''}
            
            content = [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_b64}'}}
            ]
        else:
            # Text request
            content = prompt
        
        # Prepare request payload
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': content}],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        print(f"[AI_UTILS] Making API call to: {AI_CONFIG['providers']['openrouter']['base_url']}")
        print(f"[AI_UTILS] Payload keys: {list(payload.keys())}")
        print(f"[AI_UTILS] Prompt length: {len(prompt)} characters")
        
        # Make API call
        response = requests.post(
            AI_CONFIG['providers']['openrouter']['base_url'],
            headers=headers,
            json=payload,
            timeout=AI_CONFIG['defaults']['timeout']
        )
        
        print(f"[AI_UTILS] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[AI_UTILS] Full OpenRouter response: {json.dumps(result, indent=2)}")
            
            # Extract content safely
            try:
                content = result['choices'][0]['message']['content']
                print(f"[AI_UTILS] Extracted content: {repr(content)}")
                
                # Handle None or empty content
                if content is None or content == "":
                    return {'success': False, 'error': 'OpenRouter returned empty/null content', 'content': ''}
                
                return {'success': True, 'content': content}
            except (KeyError, IndexError, TypeError) as e:
                print(f"[AI_UTILS] Error extracting content: {e}")
                print(f"[AI_UTILS] Response structure: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                return {'success': False, 'error': f'Invalid OpenRouter response structure: {e}', 'content': ''}
        else:
            error_text = response.text[:500] if response.text else f"HTTP {response.status_code}"
            print(f"[AI_UTILS] OpenRouter API error - Status: {response.status_code}")
            print(f"[AI_UTILS] Error response: {error_text}")
            return {'success': False, 'error': f'OpenRouter API error (HTTP {response.status_code}): {error_text}', 'content': ''}
            
    except requests.exceptions.Timeout as e:
        error_msg = f'OpenRouter API timeout after {AI_CONFIG["defaults"]["timeout"]} seconds'
        print(f"[AI_UTILS] {error_msg}")
        return {'success': False, 'error': error_msg, 'content': ''}
    except requests.exceptions.ConnectionError as e:
        error_msg = f'OpenRouter API connection error: {str(e)}'
        print(f"[AI_UTILS] {error_msg}")
        return {'success': False, 'error': error_msg, 'content': ''}
    except requests.exceptions.RequestException as e:
        error_msg = f'OpenRouter API request error: {str(e)}'
        print(f"[AI_UTILS] {error_msg}")
        return {'success': False, 'error': error_msg, 'content': ''}
    except Exception as e:
        error_msg = f'OpenRouter unexpected error: {str(e)}'
        print(f"[AI_UTILS] {error_msg}")
        return {'success': False, 'error': error_msg, 'content': ''}

def _huggingface_call(prompt: str, model: str, image: Union[str, bytes] = None,
                     max_tokens: int = 1000, temperature: float = 0.0) -> Dict[str, Any]:
    """Hugging Face API call"""
    try:
        # Get API key
        api_key = os.getenv(AI_CONFIG['providers']['huggingface']['api_key_env'])
        if not api_key:
            return {'success': False, 'error': 'Hugging Face API key not found', 'content': ''}
        
        # Prepare headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Build URL
        url = f"{AI_CONFIG['providers']['huggingface']['base_url']}/{model}"
        
        # Prepare payload
        if image:
            # Vision task
            image_b64 = _process_image_input(image)
            if not image_b64:
                return {'success': False, 'error': 'Failed to process image', 'content': ''}
            
            payload = {'inputs': image_b64}
        else:
            # Text task
            payload = {'inputs': prompt}
        
        # Make API call
        response = requests.post(url, headers=headers, json=payload, timeout=AI_CONFIG['defaults']['timeout'])
        
        if response.status_code == 200:
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                if 'generated_text' in result[0]:
                    content = result[0]['generated_text']
                else:
                    content = str(result[0])
            else:
                content = str(result)
            
            return {'success': True, 'content': content}
        else:
            error_text = response.text[:500] if response.text else f"HTTP {response.status_code}"
            return {'success': False, 'error': f'Hugging Face error: {error_text}', 'content': ''}
            
    except Exception as e:
        return {'success': False, 'error': f'Hugging Face exception: {str(e)}', 'content': ''}

def call_vision_ai_batch(prompt: str, image_paths: list, max_tokens: int = None, temperature: float = None) -> Dict[str, Any]:
    """Simple batch vision AI call."""
    print(f"[AI_UTILS] Batch processing {len(image_paths)} images")
    
    # Process first image with batch context (can be enhanced for true batch processing later)
    if image_paths:
        batch_prompt = f"{prompt}\n\nNote: This is part of a batch analysis of {len(image_paths)} images."
        result = _call_ai(
            batch_prompt, 
            task_type='vision', 
            image=image_paths[0], 
            max_tokens=max_tokens or AI_BATCH_CONFIG['max_tokens'], 
            temperature=temperature if temperature is not None else AI_BATCH_CONFIG['temperature']
        )
        print(f"[AI_UTILS] Batch result: success={result['success']}, provider={result.get('provider_used', 'unknown')}")
        return result
    else:
        return {'success': False, 'error': 'No images provided', 'content': ''}

# =============================================================================
# Helper Functions
# =============================================================================

def _process_image_input(image_input: Union[str, bytes]) -> Optional[str]:
    """Convert image to base64."""
    try:
        if isinstance(image_input, str):
            if image_input.startswith('data:image'):
                return image_input.split(',')[1]
            elif os.path.exists(image_input):
                with open(image_input, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
            else:
                return image_input
        elif isinstance(image_input, bytes):
            return base64.b64encode(image_input).decode()
        elif hasattr(image_input, 'shape'):  # OpenCV image
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                cv2.imwrite(tmp_file.name, image_input)
                temp_path = tmp_file.name
            
            try:
                with open(temp_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        return None
        
    except Exception as e:
        print(f"AI: Error processing image: {e}")
        return None

# =============================================================================
# Specialized AI Functions
# =============================================================================

def analyze_language_menu_ai(image_path: str, context_name: str = "AI") -> Dict[str, Any]:
    """
    AI-powered language/subtitle menu analysis using centralized AI utilities.
    
    Args:
        image_path: Path to image file showing a language/subtitle menu
        context_name: Context name for logging
        
    Returns:
        Dictionary with language and subtitle options analysis
    """
    try:
        print(f"{context_name}: AI language menu analysis")
        
        # Check if image exists
        if not os.path.exists(image_path):
            print(f"{context_name}: Image file not found: {image_path}")
            return {'success': False, 'error': 'Image file not found'}
        
        # Enhanced prompt for language/subtitle menu detection with exact format extraction
        prompt = """Analyze this image for language/subtitle/audio menu options. This could be a TV settings menu, streaming app menu, or media player interface.

LOOK FOR THESE UI PATTERNS:
- Settings menus with AUDIO, SUBTITLES, or LANGUAGE sections
- Dropdown menus or lists showing language options
- Media player controls with language/subtitle buttons
- TV/STB interface menus for audio/subtitle settings
- Streaming app (Netflix, Prime, etc.) audio/subtitle menus
- Any interface showing language choices like "English", "French", "Spanish", etc.
- Audio tracks, subtitle tracks, or closed caption options

CRITICAL INSTRUCTIONS:
1. You MUST ALWAYS respond with valid JSON - never return empty content
2. If you find ANY language/audio/subtitle menu or options, extract them
3. If you find NO menu, you MUST still respond with the "menu_detected": false JSON format below
4. ALWAYS provide a response - never return empty or null content
5. Be liberal in detecting menus - if there are any language-related options, consider it a menu

Required JSON format when menu found:
{
  "menu_detected": true,
  "audio_languages": ["English - AD - Stereo", "English - Stereo", "French - Stereo"],
  "subtitle_languages": ["English", "French", "Spanish", "Off"],
  "selected_audio": 0,
  "selected_subtitle": 3
}

If no language/subtitle menu found:
{
  "menu_detected": false,
  "audio_languages": [],
  "subtitle_languages": [],
  "selected_audio": -1,
  "selected_subtitle": -1
}

LANGUAGE FORMAT EXTRACTION RULES:
- Extract the COMPLETE text as shown for each language option
- Include ALL descriptors like "AD" (Audio Description), "Stereo", "Dolby", etc.
- Preserve exact formatting with dashes, spaces, and separators as displayed
- Examples of complete formats to capture:
  * "English - AD - Stereo"
  * "English - Stereo"
  * "English - Dolby"
  * "French - Stereo"
  * "French - AD - Stereo"
- DO NOT simplify to just "English" - capture the full descriptive text
- If only "English" is shown without descriptors, then use just "English"

CATEGORIZATION RULES:
- AUDIO section: Main audio languages with their full descriptors
- SUBTITLE section: Subtitle options (usually simpler, like "English", "French", "Off")
- AUDIO DESCRIPTION: These belong in audio_languages, not subtitle_languages
- Look for section headers like "AUDIO", "SUBTITLES", "AUDIO DESCRIPTION", "LANGUAGE", "CC"
- List languages in the order they appear within each section (index 0, 1, 2, etc.)
- Use "Off" for disabled subtitles
- Set selected_audio/selected_subtitle to the index of the currently selected option (-1 if none)
- Check for visual indicators like checkmarks (✓), highlighting, arrows, or bold text

SPECIAL AUDIO HANDLING:
- "Audio description" or "Audio Description" should be treated as an audio language option
- If you see "Audio description" in an AUDIO section, include it as "Audio Description" in audio_languages
- Even standalone audio accessibility options count as audio language choices
- Look for any audio-related options like "Descriptive Audio", "AD", "Audio Description", etc.

IMPORTANT: Even if the image has no language/subtitle menu, you MUST respond with the "menu_detected": false JSON format above. Never return empty content.

RESPOND WITH JSON ONLY - NO MARKDOWN - NO OTHER TEXT"""
        
        # Call AI with image
        result = call_vision_ai(prompt, image_path, max_tokens=400, temperature=0.0)
        
        if not result['success']:
            return {
                'success': False,
                'error': f"AI call failed: {result.get('error', 'Unknown error')}",
                'analysis_type': 'ai_language_menu_analysis'
            }
        
        content = result['content']
        
        # Parse JSON response
        try:
            # Remove markdown code block markers
            json_content = content.replace('```json', '').replace('```', '').strip()
            
            ai_result = json.loads(json_content)
            
            # Validate and normalize the result
            menu_detected = ai_result.get('menu_detected', False)
            audio_languages = ai_result.get('audio_languages', [])
            subtitle_languages = ai_result.get('subtitle_languages', [])
            selected_audio = ai_result.get('selected_audio', -1)
            selected_subtitle = ai_result.get('selected_subtitle', -1)
            
            # Return standardized result
            return {
                'success': True,
                'menu_detected': menu_detected,
                'audio_languages': audio_languages,
                'subtitle_languages': subtitle_languages,
                'selected_audio': selected_audio,
                'selected_subtitle': selected_subtitle,
                'analysis_type': 'ai_language_menu_analysis'
            }
            
        except json.JSONDecodeError as e:
            print(f"{context_name}: JSON parsing error: {e}")
            print(f"{context_name}: Raw AI response: {repr(content)}")
            return {
                'success': False,
                'error': 'Invalid AI response format',
                'raw_response': content,
                'json_error': str(e)
            }
            
    except Exception as e:
        print(f"{context_name}: AI language menu analysis error: {e}")
        return {
            'success': False,
            'error': f'Analysis error: {str(e)}'
        }
