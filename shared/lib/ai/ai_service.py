"""
Minimalist AI Service - Centralized Inference with Multiple Providers

Simple service that centralizes all AI calls with support for:
- OpenRouter (primary)
- Hugging Face (fallback)
- Automatic provider fallback on errors
- Minimal code changes required
"""

import os
import requests
import json
import base64
import time
from typing import Dict, Any, Optional, Union

# Import config from project root
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from shared.config.ai_config import AI_CONFIG


class AIService:
    """Simple centralized AI service - no over-engineering"""
    
    def __init__(self):
        self.config = AI_CONFIG
        self.providers = {
            'openrouter': self._openrouter_call,
            'huggingface': self._huggingface_call
        }
        self.default_provider = self.config['defaults']['primary_provider']
        self.fallback_provider = self.config['defaults']['fallback_provider']
    
    def call_ai(self, prompt: str, task_type: str = 'text', image: Union[str, bytes] = None, 
                max_tokens: int = None, temperature: float = None, **kwargs) -> Dict[str, Any]:
        """
        Single method for all AI calls - defaults to OpenRouter, fallback to Hugging Face
        
        Args:
            prompt: The prompt text
            task_type: 'text', 'vision', or 'translation'
            image: Image path or bytes (for vision tasks)
            max_tokens: Override default max tokens
            temperature: Override default temperature
            
        Returns:
            {'success': bool, 'content': str, 'error': str, 'provider_used': str}
        """
        # Always try OpenRouter first (default provider)
        primary_provider = 'openrouter'
        
        # Get model for task type from OpenRouter
        model = self._get_model(primary_provider, task_type)
        if not model:
            return {'success': False, 'error': f'No OpenRouter model configured for {task_type}', 'content': ''}
        
        # Set defaults
        max_tokens = max_tokens or self.config['defaults']['max_tokens']
        temperature = temperature or self.config['defaults']['temperature']
        
        # Try OpenRouter first
        try:
            print(f"[AI_SERVICE] Using OpenRouter with model {model}")
            result = self.providers[primary_provider](prompt, model, image, max_tokens, temperature, **kwargs)
            if result['success']:
                result['provider_used'] = primary_provider
                return result
        except Exception as e:
            print(f"[AI_SERVICE] OpenRouter failed: {e}")
        
        # Try Hugging Face fallback only if OpenRouter fails
        fallback_provider = 'huggingface'
        fallback_model = self._get_model(fallback_provider, task_type)
        if fallback_model:
            try:
                print(f"[AI_SERVICE] Trying Hugging Face fallback with model {fallback_model}")
                result = self.providers[fallback_provider](prompt, fallback_model, image, max_tokens, temperature, **kwargs)
                if result['success']:
                    result['provider_used'] = fallback_provider
                    return result
            except Exception as e:
                print(f"[AI_SERVICE] Hugging Face fallback failed: {e}")
        
        return {'success': False, 'error': 'Both OpenRouter and Hugging Face failed', 'content': '', 'provider_used': 'none'}
    
    def _get_model(self, provider: str, task_type: str) -> Optional[str]:
        """Get model name for provider and task type"""
        try:
            return self.config['providers'][provider]['models'][task_type]
        except KeyError:
            return None
    
    def _openrouter_call(self, prompt: str, model: str, image: Union[str, bytes] = None, 
                        max_tokens: int = 1000, temperature: float = 0.0, **kwargs) -> Dict[str, Any]:
        """OpenRouter API implementation"""
        try:
            # Get API key
            api_key = os.getenv(self.config['providers']['openrouter']['api_key_env'])
            if not api_key:
                return {'success': False, 'error': 'OpenRouter API key not found', 'content': ''}
            
            # Prepare headers
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                **self.config['providers']['openrouter']['headers']
            }
            
            # Prepare message content
            if image:
                # Vision request
                image_b64 = self._process_image(image)
                if not image_b64:
                    return {'success': False, 'error': 'Failed to process image', 'content': ''}
                
                content = [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_b64}'}}
                ]
            else:
                # Text request
                content = prompt
            
            # Make API call
            response = requests.post(
                self.config['providers']['openrouter']['base_url'],
                headers=headers,
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': content}],
                    'max_tokens': max_tokens,
                    'temperature': temperature
                },
                timeout=self.config['defaults']['timeout']
            )
            
            print(f"[AI_SERVICE] OpenRouter response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return {'success': True, 'content': content}
            elif response.status_code == 429:
                return {'success': False, 'error': 'Rate limited', 'content': ''}
            else:
                error_text = response.text[:500] if response.text else f"HTTP {response.status_code}"
                return {'success': False, 'error': f'OpenRouter error: {error_text}', 'content': ''}
                
        except Exception as e:
            return {'success': False, 'error': f'OpenRouter exception: {str(e)}', 'content': ''}
    
    def _huggingface_call(self, prompt: str, model: str, image: Union[str, bytes] = None,
                         max_tokens: int = 1000, temperature: float = 0.0, **kwargs) -> Dict[str, Any]:
        """Hugging Face API implementation"""
        try:
            # Get API key
            api_key = os.getenv(self.config['providers']['huggingface']['api_key_env'])
            if not api_key:
                return {'success': False, 'error': 'Hugging Face API key not found', 'content': ''}
            
            # Prepare headers
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Build URL
            url = f"{self.config['providers']['huggingface']['base_url']}/{model}"
            
            # Prepare payload based on task type
            if image:
                # Vision task - send image data
                image_b64 = self._process_image(image)
                if not image_b64:
                    return {'success': False, 'error': 'Failed to process image', 'content': ''}
                
                payload = {
                    'inputs': image_b64,
                    'parameters': {
                        'max_new_tokens': max_tokens,
                        'temperature': temperature
                    }
                }
            else:
                # Text task
                payload = {
                    'inputs': prompt,
                    'parameters': {
                        'max_new_tokens': max_tokens,
                        'temperature': temperature,
                        'return_full_text': False
                    }
                }
            
            # Make API call
            response = requests.post(url, headers=headers, json=payload, timeout=self.config['defaults']['timeout'])
            
            print(f"[AI_SERVICE] Hugging Face response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    if 'generated_text' in result[0]:
                        content = result[0]['generated_text']
                    elif 'generated_text' in result[0]:
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
    
    def _process_image(self, image: Union[str, bytes]) -> Optional[str]:
        """Process image input to base64 string"""
        try:
            if isinstance(image, str):
                # File path
                if os.path.exists(image):
                    with open(image, 'rb') as f:
                        image_data = f.read()
                else:
                    return None
            else:
                # Bytes
                image_data = image
            
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            print(f"[AI_SERVICE] Image processing error: {e}")
            return None
    
    def get_available_providers(self) -> Dict[str, bool]:
        """Check which providers are available (have API keys)"""
        status = {}
        for provider_name, provider_config in self.config['providers'].items():
            api_key = os.getenv(provider_config['api_key_env'])
            status[provider_name] = bool(api_key)
        return status
    
    def get_models(self, provider: str = None) -> Dict[str, Any]:
        """Get available models for provider(s)"""
        if provider:
            return self.config['providers'].get(provider, {}).get('models', {})
        else:
            return {p: config['models'] for p, config in self.config['providers'].items()}


# Singleton instance
_ai_service_instance = None

def get_ai_service() -> AIService:
    """Get singleton AI service instance"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance
