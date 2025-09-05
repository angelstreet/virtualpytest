"""
AI Command Description System

This module provides enhanced command descriptions for AI test case generation.
It supplements existing controller commands with detailed descriptions and examples
without modifying the original controller implementations.

Usage:
    from backend_core.src.controllers.ai_descriptions import get_enhanced_actions_for_device
    
    enhanced_actions = get_enhanced_actions_for_device('device1')
    # Returns all device commands with AI-friendly descriptions
"""

from .description_registry import (
    get_enhanced_description,
    enhance_controller_actions,
    get_all_enhanced_actions_for_device,
    get_enhanced_actions_for_ai,
    get_commands_for_device_model
)

__all__ = [
    'get_enhanced_description',
    'enhance_controller_actions', 
    'get_all_enhanced_actions_for_device',
    'get_enhanced_actions_for_ai',
    'get_commands_for_device_model'
]
