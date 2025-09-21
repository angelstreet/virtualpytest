"""
AI Cache Utilities

Clean utility functions for AI plan caching with no fallbacks.
"""

import re
import hashlib
import json
from typing import Dict, List, Optional


def normalize_prompt(prompt: str) -> str:
    """
    Normalize prompt to standard form for cache matching.
    
    Args:
        prompt: Original user prompt
        
    Returns:
        Normalized prompt string
    """
    # Basic cleanup
    normalized = prompt.lower().strip()
    
    # Remove politeness words
    politeness_words = ['please', 'can you', 'could you', 'would you', 'i want to', 'i need to']
    for word in politeness_words:
        normalized = normalized.replace(word, '').strip()
    
    # Classify intent and extract target
    intent = classify_intent(normalized)
    target = extract_target(normalized)
    
    # Create standardized format: intent_target
    if intent and target:
        return f"{intent}_{target}"
    
    # Fallback to basic normalization
    return _basic_normalize(normalized)


def classify_intent(prompt: str) -> str:
    """
    Classify the main intent of the prompt.
    
    Args:
        prompt: Prompt to classify
        
    Returns:
        Intent classification ('navigation', 'action', 'search', etc.)
    """
    navigation_keywords = ['go', 'navigate', 'take me', 'show', 'open', 'goto']
    action_keywords = ['click', 'tap', 'press', 'select', 'touch']
    search_keywords = ['find', 'search', 'look for', 'locate']
    media_keywords = ['play', 'start', 'stop', 'pause', 'resume']
    system_keywords = ['back', 'home', 'exit', 'quit']
    
    if any(keyword in prompt for keyword in navigation_keywords):
        return 'navigation'
    elif any(keyword in prompt for keyword in action_keywords):
        return 'action'
    elif any(keyword in prompt for keyword in search_keywords):
        return 'search'
    elif any(keyword in prompt for keyword in media_keywords):
        return 'media'
    elif any(keyword in prompt for keyword in system_keywords):
        return 'system'
    
    return 'unknown'


def extract_target(prompt: str) -> str:
    """
    Extract the main target/object from the prompt.
    
    Args:
        prompt: Prompt to extract target from
        
    Returns:
        Extracted target string
    """
    # Remove common prefixes
    cleaned = re.sub(r'^(go to|navigate to|click on|find|show me|take me to)\s+', '', prompt)
    
    # Remove common suffixes
    cleaned = re.sub(r'\s+(section|area|page|screen|button)$', '', cleaned)
    
    # Remove articles and filler words
    filler_words = ['the', 'a', 'an']
    words = cleaned.split()
    words = [w for w in words if w not in filler_words]
    
    # Handle compound targets (space to underscore for navigation nodes)
    target = '_'.join(words) if words else cleaned
    
    return target.strip()


def _basic_normalize(prompt: str) -> str:
    """
    Basic prompt normalization fallback.
    
    Args:
        prompt: Prompt to normalize
        
    Returns:
        Normalized prompt
    """
    # Standardize navigation verbs
    navigation_patterns = {
        r'\b(go to|navigate to|take me to|show me|open|goto)\b': 'navigate_to',
        r'\b(click on|tap on|press|select)\b': 'click',
        r'\b(find|search for|look for)\b': 'find',
        r'\b(play|start|launch)\b': 'play',
        r'\b(stop|pause|halt)\b': 'stop'
    }
    
    normalized = prompt
    for pattern, replacement in navigation_patterns.items():
        normalized = re.sub(pattern, replacement, normalized)
    
    # Remove articles and filler words
    filler_words = ['the', 'a', 'an', 'section', 'area', 'page', 'screen']
    words = normalized.split()
    words = [w for w in words if w not in filler_words]
    
    # Clean up whitespace
    return re.sub(r'\s+', ' ', ' '.join(words)).strip()


def generate_fingerprint(prompt: str, context: Dict) -> str:
    """
    Generate unique fingerprint for task matching.
    
    Args:
        prompt: User prompt
        context: Execution context
        
    Returns:
        MD5 fingerprint string
    """
    # Normalize prompt
    normalized_prompt = normalize_prompt(prompt)
    
    # Create context signature
    context_signature = {
        'available_nodes': sorted(context.get('available_nodes', [])),
        'device_model': context.get('device_model'),
        'userinterface_name': context.get('userinterface_name')
    }
    
    # Generate fingerprint
    fingerprint_data = f"{normalized_prompt}:{json.dumps(context_signature, sort_keys=True)}"
    return hashlib.md5(fingerprint_data.encode()).hexdigest()


def create_context_signature(context: Dict) -> Dict:
    """
    Create a standardized context signature for compatibility checking.
    
    Args:
        context: Full execution context
        
    Returns:
        Standardized context signature
    """
    return {
        'available_nodes': sorted(context.get('available_nodes', [])),
        'device_model': context.get('device_model'),
        'userinterface_name': context.get('userinterface_name')
    }


def is_context_compatible(cached_context: Dict, current_context: Dict, 
                         compatibility_threshold: float = 0.8) -> bool:
    """
    Check if cached plan context is compatible with current context.
    
    Args:
        cached_context: Context from cached plan
        current_context: Current execution context
        compatibility_threshold: Minimum compatibility score (0.0-1.0)
        
    Returns:
        True if contexts are compatible, False otherwise
    """
    # Device model must match exactly
    if cached_context.get('device_model') != current_context.get('device_model'):
        return False
    
    # Interface must match exactly
    if cached_context.get('userinterface_name') != current_context.get('userinterface_name'):
        return False
    
    # Check node compatibility
    cached_nodes = set(cached_context.get('available_nodes', []))
    current_nodes = set(current_context.get('available_nodes', []))
    
    if not cached_nodes or not current_nodes:
        return False
    
    # Calculate overlap percentage
    overlap = len(cached_nodes.intersection(current_nodes))
    total_unique = len(cached_nodes.union(current_nodes))
    compatibility = overlap / total_unique if total_unique > 0 else 0
    
    return compatibility >= compatibility_threshold


def should_reuse_plan(plan_data: Dict, context: Dict, 
                     min_success_rate: float = 0.6,
                     min_executions: int = 1) -> bool:
    """
    Decide if a cached plan should be reused.
    
    Args:
        plan_data: Cached plan data from database
        context: Current execution context
        min_success_rate: Minimum success rate threshold
        min_executions: Minimum number of executions required
        
    Returns:
        True if plan should be reused, False otherwise
    """
    # Check success rate
    if plan_data.get('success_rate', 0) < min_success_rate:
        return False
    
    # Check execution count
    if plan_data.get('execution_count', 0) < min_executions:
        return False
    
    # Check context compatibility
    cached_context = {
        'device_model': plan_data.get('device_model'),
        'userinterface_name': plan_data.get('userinterface_name'),
        'available_nodes': plan_data.get('available_nodes', [])
    }
    
    if not is_context_compatible(cached_context, context):
        return False
    
    return True
