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
from typing import Dict, Any, Optional, Union

# =============================================================================
# Models - Single Source of Truth  
# =============================================================================

AI_MODELS = {
    'text': 'moonshotai/kimi-k2:free',
    'vision': 'qwen/qwen-2.5-vl-7b-instruct',  # Updated version
}

API_BASE_URL = 'https://openrouter.ai/api/v1/chat/completions'

# =============================================================================
# Simple API Calls
# =============================================================================

def get_api_key() -> Optional[str]:
    """Get OpenRouter API key from environment."""
    return os.getenv('OPENROUTER_API_KEY')

def call_text_ai(prompt: str, max_tokens: int = 200, temperature: float = 0.1) -> Dict[str, Any]:
    """Simple text AI call."""
    try:
        api_key = get_api_key()
        if not api_key:
            return {'success': False, 'error': 'No API key', 'content': ''}
        
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
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return {'success': True, 'content': content}
        else:
            return {'success': False, 'error': f'API error: {response.status_code}', 'content': ''}
            
    except Exception as e:
        return {'success': False, 'error': str(e), 'content': ''}

def call_vision_ai(prompt: str, image_input: Union[str, bytes], max_tokens: int = 300, temperature: float = 0.0) -> Dict[str, Any]:
    """Simple vision AI call."""
    try:
        api_key = get_api_key()
        if not api_key:
            return {'success': False, 'error': 'No API key', 'content': ''}
        
        # Process image
        image_b64 = _process_image_input(image_input)
        if not image_b64:
            return {'success': False, 'error': 'Failed to process image', 'content': ''}
        
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
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            if content is None or content.strip() == '':
                return {'success': False, 'error': 'Empty content from AI', 'content': ''}
            
            return {'success': True, 'content': content.strip()}
        else:
            return {'success': False, 'error': f'API error: {response.status_code}', 'content': ''}
            
    except Exception as e:
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
