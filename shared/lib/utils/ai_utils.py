"""
AI Utilities - Simple Centralized AI Configuration

Just centralizes the models and basic API calls you already have.
"""

import os
import base64
import requests
import json
import tempfile
import cv2
from datetime import datetime
from typing import Dict, Any, Optional, Union

# =============================================================================
# Models - Single Source of Truth  
# =============================================================================

AI_MODELS = {
    'text': 'moonshotai/kimi-k2:free', # Kimi not working for now, using Qwen instead moonshotai/kimi-k2:free
    'vision': 'google/gemini-2.0-flash-exp',# google/gemini-2.0-flash-exp or qwen/qwen2.5-vl-3b-instruct
    'translation': 'google/gemma-2-2b', # or microsoft/phi-3-mini-4k-instruct
}

# AI Batch Processing Configuration
AI_BATCH_CONFIG = {
    'batch_size': 4,            # Number of images per batch (reduced from 10)
    'max_batch_size': 4,        # Maximum allowed batch size (reduced from 10)
    'timeout_seconds': 300,     # 5 minutes timeout per batch
    'max_tokens': 2000,          # Max tokens per AI response
    'temperature': 0.0          # AI temperature setting
}

API_BASE_URL = 'https://openrouter.ai/api/v1/chat/completions'

# =============================================================================
# Helper Functions
# =============================================================================

def _format_timestamp(timestamp: float) -> str:
    """Convert Unix timestamp to readable HH:mm:ss format."""
    return datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')

# =============================================================================
# Simple API Calls
# =============================================================================

def get_api_key() -> Optional[str]:
    """Get OpenRouter API key from environment."""
    return os.getenv('OPENROUTER_API_KEY')

def call_text_ai(prompt: str, max_tokens: int = 200, temperature: float = 0.1) -> Dict[str, Any]:
    """Simple text AI call with model fallback on 429."""
    try:
        api_key = get_api_key()
        if not api_key:
            print("[AI_UTILS] ERROR: No API key found")
            return {'success': False, 'error': 'No API key', 'content': ''}
        
        # Try Kimi first
        print(f"[AI_UTILS] Making OpenRouter API call - Model: {AI_MODELS['text']}, Max tokens: {max_tokens}")
        
        response = requests.post(
            API_BASE_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://virtualpytest.com',
                'X-Title': 'VirtualPyTest'
            },
            json={
                'model': AI_MODELS['text'],
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': max_tokens,
                'temperature': temperature
            },
            timeout=60
        )
        
        print(f"[AI_UTILS] OpenRouter Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"[AI_UTILS] SUCCESS: Received {len(content)} characters")
            return {'success': True, 'content': content}
        elif response.status_code == 429:
            # Try Qwen vision model on rate limit
            print(f"[AI_UTILS] Kimi rate limited, trying Qwen...")
            
            response = requests.post(
                API_BASE_URL,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://virtualpytest.com',
                    'X-Title': 'VirtualPyTest'
                },
                json={
                    'model': AI_MODELS['vision'],
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': max_tokens,
                    'temperature': temperature
                },
                timeout=60
            )
            
            print(f"[AI_UTILS] Qwen Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"[AI_UTILS] SUCCESS with Qwen: Received {len(content)} characters")
                return {'success': True, 'content': content}
        
        # Log error for any failure
        try:
            error_body = response.json()
            print(f"[AI_UTILS] ERROR BODY: {error_body}")
        except:
            error_body = response.text
            print(f"[AI_UTILS] ERROR TEXT: {error_body}")
        
        print(f"[AI_UTILS] FAILED: Status {response.status_code}")
        return {'success': False, 'error': f'API error: {response.status_code}', 'content': '', 'response_body': error_body}
            
    except Exception as e:
        print(f"[AI_UTILS] EXCEPTION: {str(e)}")
        return {'success': False, 'error': str(e), 'content': ''}

def call_vision_ai(prompt: str, image_input: Union[str, bytes], max_tokens: int = 300, temperature: float = 0.0) -> Dict[str, Any]:
    """Simple vision AI call."""
    import time
    start_time = time.time()
    
    try:
        api_key = get_api_key()
        if not api_key:
            return {'success': False, 'error': 'No API key', 'content': ''}
        
        # Process image
        image_b64 = _process_image_input(image_input)
        if not image_b64:
            return {'success': False, 'error': 'Failed to process image', 'content': ''}
        
        # Get image info for logging
        image_size_kb = len(image_b64) * 3 / 4 / 1024  # Approximate size in KB
        image_path = image_input if isinstance(image_input, str) else "bytes_input"
        
        # Log request details in one line for easy re-execution
        prompt_oneline = prompt.replace('\n', '\\n').replace('"', '\\"')
        readable_time = _format_timestamp(start_time)
        print(f"[AI_UTILS] 🚀 VISION_REQUEST_START: time={readable_time} image='{image_path}' size={image_size_kb:.1f}KB model='{AI_MODELS['vision']}' max_tokens={max_tokens} temp={temperature} prompt=\"{prompt_oneline}\"")
        
        response = requests.post(
            API_BASE_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://virtualpytest.com',
                'X-Title': 'VirtualPyTest'
            },
            json={
                'model': AI_MODELS['vision'],
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_b64}'}}
                    ]
                }],
                'max_tokens': max_tokens,
                'temperature': temperature
            },
            timeout=300
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            if content is None or content.strip() == '':
                print(f"[AI_UTILS] ❌ VISION_REQUEST_EMPTY: duration={duration:.2f}s status=200 image='{image_path}' error='Empty content from AI'")
                return {'success': False, 'error': 'Empty content from AI', 'content': ''}
            
            content_preview = content.strip()[:100].replace('\n', '\\n')
            print(f"[AI_UTILS] ✅ VISION_REQUEST_SUCCESS: duration={duration:.2f}s status=200 image='{image_path}' content_length={len(content)} preview=\"{content_preview}...\"")
            return {'success': True, 'content': content.strip()}
        else:
            print(f"[AI_UTILS] ❌ VISION_REQUEST_ERROR: duration={duration:.2f}s status={response.status_code} image='{image_path}' error='API error: {response.status_code}'")
            return {'success': False, 'error': f'API error: {response.status_code}', 'content': ''}
            
    except Exception as e:
        duration = time.time() - start_time
        image_path = image_input if isinstance(image_input, str) else "bytes_input"
        print(f"[AI_UTILS] 💥 VISION_REQUEST_EXCEPTION: duration={duration:.2f}s image='{image_path}' error='{str(e)}'")
        return {'success': False, 'error': str(e), 'content': ''}

def call_vision_ai_batch(prompt: str, image_paths: list, max_tokens: int = None, temperature: float = None) -> Dict[str, Any]:
    """Simple batch vision AI call using global AI_BATCH_CONFIG."""
    import time
    start_time = time.time()
    
    # Use global config values if not provided
    max_tokens = max_tokens or AI_BATCH_CONFIG['max_tokens']
    temperature = temperature if temperature is not None else AI_BATCH_CONFIG['temperature']
    timeout = AI_BATCH_CONFIG['timeout_seconds']
    max_batch_size = AI_BATCH_CONFIG['max_batch_size']
    
    try:
        api_key = get_api_key()
        if not api_key:
            return {'success': False, 'error': 'No API key', 'content': ''}
        
        if len(image_paths) > max_batch_size:
            return {'success': False, 'error': f'Maximum {max_batch_size} images per batch', 'content': ''}
        
        # Process all images
        image_contents = []
        total_size_kb = 0
        
        for image_path in image_paths:
            image_b64 = _process_image_input(image_path)
            if not image_b64:
                return {'success': False, 'error': f'Failed to process image: {image_path}', 'content': ''}
            
            image_contents.append({'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_b64}'}})
            total_size_kb += len(image_b64) * 3 / 4 / 1024
        
        # Build message content: prompt + all images
        message_content = [{'type': 'text', 'text': prompt}] + image_contents
        
        # Log batch request
        prompt_oneline = prompt.replace('\n', '\\n').replace('"', '\\"')
        readable_time = _format_timestamp(start_time)
        print(f"[AI_UTILS] 🚀 BATCH_VISION_REQUEST_START: time={readable_time} images={len(image_paths)} total_size={total_size_kb:.1f}KB model='{AI_MODELS['vision']}' max_tokens={max_tokens} temp={temperature}")
        print(f"[AI_UTILS] 📁 BATCH_IMAGES: {image_paths}")
        print(f"[AI_UTILS] 📝 BATCH_PROMPT: \"{prompt_oneline}\"")
        
        response = requests.post(
            API_BASE_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://virtualpytest.com',
                'X-Title': 'VirtualPyTest'
            },
            json={
                'model': AI_MODELS['vision'],
                'messages': [{
                    'role': 'user',
                    'content': message_content
                }],
                'max_tokens': max_tokens,
                'temperature': temperature
            },
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            if content is None or content.strip() == '':
                print(f"[AI_UTILS] ❌ BATCH_VISION_REQUEST_EMPTY: duration={duration:.2f}s status=200 images={len(image_paths)} error='Empty content from AI'")
                return {'success': False, 'error': 'Empty content from AI', 'content': ''}
            
            content_preview = content.strip()[:150].replace('\n', '\\n')
            print(f"[AI_UTILS] ✅ BATCH_VISION_REQUEST_SUCCESS: duration={duration:.2f}s status=200 images={len(image_paths)} content_length={len(content)} preview=\"{content_preview}...\"")
            return {'success': True, 'content': content.strip()}
        else:
            print(f"[AI_UTILS] ❌ BATCH_VISION_REQUEST_ERROR: duration={duration:.2f}s status={response.status_code} images={len(image_paths)} error='API error: {response.status_code}'")
            return {'success': False, 'error': f'API error: {response.status_code}', 'content': ''}
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"[AI_UTILS] 💥 BATCH_VISION_REQUEST_EXCEPTION: duration={duration:.2f}s images={len(image_paths)} error='{str(e)}'")
        return {'success': False, 'error': str(e), 'content': ''}

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
