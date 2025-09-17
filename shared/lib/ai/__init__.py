"""
Centralized AI Service - Simple Exports

Usage:
    from shared.lib.ai import AIService, get_ai_service
    
    ai = AIService()  # or get_ai_service() for singleton
    result = ai.call_ai("prompt", task_type="text")
"""

from .ai_service import AIService, get_ai_service

__all__ = ['AIService', 'get_ai_service']
