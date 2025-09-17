"""
Simple AI Configuration - Centralized Models and Providers
"""

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
                'translation': 'microsoft/phi-3-mini-128k-instruct'
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
