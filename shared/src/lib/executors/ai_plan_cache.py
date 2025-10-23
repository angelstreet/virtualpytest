"""
AI Plan Cache

Clean cache implementation for AI plan generation with no fallbacks.
Consolidated utilities and cache logic in one file.
"""

import re
import hashlib
import json
from typing import Dict, List, Optional, Any
from .ai_types import ExecutionResult


# ============================================================================
# CACHE UTILITIES (consolidated from ai_cache_utils.py)
# ============================================================================

def normalize_prompt(prompt: str) -> str:
    """Normalize prompt to standard form for cache matching."""
    # Basic cleanup
    normalized = prompt.lower().strip()
    
    # Remove politeness words
    politeness_words = ['please', 'can you', 'could you', 'would you', 'i want to', 'i need to']
    for word in politeness_words:
        normalized = normalized.replace(word, '').strip()
    
    # Classify intent and extract target
    intent = _classify_intent(normalized)
    target = _extract_target(normalized)
    
    # Create standardized format: intent_target
    if intent and target:
        return f"{intent}_{target}"
    
    # Fallback to basic normalization
    return _basic_normalize(normalized)


def _classify_intent(prompt: str) -> str:
    """Classify the main intent of the prompt."""
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


def _extract_target(prompt: str) -> str:
    """Extract the main target/object from the prompt."""
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
    """Basic prompt normalization fallback."""
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
    """Generate unique fingerprint for task matching."""
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


def _is_context_compatible(cached_context: Dict, current_context: Dict, 
                          compatibility_threshold: float = 0.8) -> bool:
    """Check if cached plan context is compatible with current context."""
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


def _should_reuse_plan(plan_data: Dict, context: Dict, 
                      min_success_rate: float = 0.6,
                      min_executions: int = 1) -> bool:
    """Decide if a cached plan should be reused."""
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
    
    if not _is_context_compatible(cached_context, context):
        return False
    
    return True


# ============================================================================
# CACHE IMPLEMENTATION
# ============================================================================


class AIExecutorCache:
    """
    Clean AI plan cache with explicit control and no fallbacks.
    """
    
    def __init__(self):
        """Initialize cache"""
        print("[@ai_plan_cache] Initialized AI plan cache")
    
    def _is_plan_format_valid(self, cached_plan: Dict) -> bool:
        """
        Validate cached plan format to ensure it matches current architecture.
        Auto-reject old format plans with verbose AI descriptions.
        
        Args:
            cached_plan: Cached plan dictionary
            
        Returns:
            True if format is valid, False if invalid (will trigger auto-delete)
        """
        try:
            plan = cached_plan.get('plan', {})
            steps = plan.get('steps', [])
            
            if not steps:
                return True  # Empty plan is valid (might be infeasible task)
            
            for step in steps:
                # Check required fields
                if 'command' not in step:
                    print(f"[@ai_plan_cache:validation] ❌ Invalid: Missing 'command' field")
                    return False
                
                # Navigation steps MUST have pre-fetched transitions in new format
                if step.get('command') == 'execute_navigation':
                    # Old format: no transitions field OR missing transitions
                    # New format: transitions field exists (even if empty list)
                    if 'transitions' not in step:
                        print(f"[@ai_plan_cache:validation] ❌ Invalid: Navigation step missing pre-fetched 'transitions'")
                        return False
                    
                    # Check for old AI verbose descriptions (reject verbose AI text)
                    description = step.get('description', '')
                    if description and any(phrase in description.lower() for phrase in [
                        'navigate directly',
                        'navigate to the',
                        'task is to',
                        'since the',
                        'closest node',
                        'the node exists',
                        'which could',
                        'proceed to',
                        'visually locate',
                        'could potentially'
                    ]):
                        print(f"[@ai_plan_cache:validation] ❌ Invalid: Old AI verbose description detected: '{description}'")
                        return False
            
            # All checks passed
            print(f"[@ai_plan_cache:validation] ✅ Plan format valid")
            return True
            
        except Exception as e:
            print(f"[@ai_plan_cache:validation] ❌ Validation error: {e}")
            return False  # Reject on any error
    
    def find_cached_plan(self, prompt: str, context: Dict, team_id: str) -> Optional[Dict]:
        """
        Find a cached plan for the given prompt and context.
        Auto-deletes invalid/old format cached plans.
        
        Args:
            prompt: User prompt
            context: Execution context
            team_id: Team ID for security
            
        Returns:
            Cached plan dictionary or None if not found
        """
        try:
            # Generate fingerprint for exact match
            fingerprint = generate_fingerprint(prompt, context)
            
            # Try exact match first
            from shared.src.lib.database.ai_plan_generation_db import get_plan_by_fingerprint, delete_plan_by_fingerprint
            exact_match = get_plan_by_fingerprint(fingerprint, team_id)
            if exact_match:
                # Validate plan format - delete if invalid
                if not self._is_plan_format_valid(exact_match):
                    print(f"[@ai_plan_cache] ⚠️ Exact match has INVALID format - auto-deleting: {fingerprint}")
                    delete_plan_by_fingerprint(fingerprint, team_id)
                    exact_match = None  # Force regeneration
                elif _should_reuse_plan(exact_match, context):
                    print(f"[@ai_plan_cache] Found exact match for fingerprint: {fingerprint}")
                    return exact_match
            
            # Try compatible plans
            normalized_prompt = normalize_prompt(prompt)
            from shared.src.lib.database.ai_plan_generation_db import find_compatible_plans
            compatible_plans = find_compatible_plans(
                normalized_prompt=normalized_prompt,
                device_model=context.get('device_model'),
                userinterface_name=context.get('userinterface_name'),
                available_nodes=context.get('available_nodes', []),
                team_id=team_id
            )
            
            # Return best compatible plan (validate format first)
            for plan in compatible_plans:
                # Validate plan format - delete if invalid
                if not self._is_plan_format_valid(plan):
                    print(f"[@ai_plan_cache] ⚠️ Compatible plan has INVALID format - auto-deleting: {plan['fingerprint']}")
                    delete_plan_by_fingerprint(plan['fingerprint'], team_id)
                    continue  # Skip this plan
                    
                if _should_reuse_plan(plan, context):
                    print(f"[@ai_plan_cache] Found compatible plan: {plan['fingerprint']} (success rate: {plan['success_rate']:.2f})")
                    return plan
            
            print(f"[@ai_plan_cache] No cached plan found for prompt: '{prompt}'")
            return None
            
        except Exception as e:
            print(f"[@ai_plan_cache] Error finding cached plan: {e}")
            return None
    
    def store_successful_plan(self, prompt: str, context: Dict, plan: Dict, 
                            result: ExecutionResult, team_id: str) -> bool:
        """
        Store a successful plan in the cache.
        
        Args:
            prompt: Original user prompt
            context: Execution context
            plan: AI-generated plan
            result: Execution result (must be successful)
            team_id: Team ID for security
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Validate that result is successful
            if not result.success:
                print(f"[@ai_plan_cache] Not storing failed plan")
                return False
            
            # Generate fingerprint and normalized prompt
            fingerprint = generate_fingerprint(prompt, context)
            normalized_prompt = normalize_prompt(prompt)
            
            # Store in database
            from shared.src.lib.database.ai_plan_generation_db import store_plan
            success = store_plan(
                fingerprint=fingerprint,
                original_prompt=prompt,
                normalized_prompt=normalized_prompt,
                device_model=context.get('device_model'),
                userinterface_name=context.get('userinterface_name'),
                available_nodes=context.get('available_nodes', []),
                plan=plan,
                team_id=team_id
            )
            
            if success:
                print(f"[@ai_plan_cache] Stored successful plan: {fingerprint}")
            else:
                print(f"[@ai_plan_cache] Failed to store plan: {fingerprint}")
            
            return success
            
        except Exception as e:
            print(f"[@ai_plan_cache] Error storing plan: {e}")
            return False
    
    def update_plan_metrics(self, fingerprint: str, success: bool, 
                          execution_time_ms: int, team_id: str) -> bool:
        """
        Update metrics for a cached plan after execution.
        
        Args:
            fingerprint: Plan fingerprint
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds
            team_id: Team ID for security
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            from shared.src.lib.database.ai_plan_generation_db import update_plan_metrics
            result = update_plan_metrics(fingerprint, success, execution_time_ms, team_id)
            
            if result:
                status = "successful" if success else "failed"
                print(f"[@ai_plan_cache] Updated metrics for {fingerprint}: {status} execution")
            
            return result
            
        except Exception as e:
            print(f"[@ai_plan_cache] Error updating metrics: {e}")
            return False
    
    def invalidate_plan(self, fingerprint: str, team_id: str) -> bool:
        """
        Manually invalidate a cached plan.
        
        Args:
            fingerprint: Plan fingerprint to invalidate
            team_id: Team ID for security
            
        Returns:
            True if invalidated successfully, False otherwise
        """
        try:
            from shared.src.lib.database.ai_plan_generation_db import invalidate_plan
            result = invalidate_plan(fingerprint, team_id)
            
            if result:
                print(f"[@ai_plan_cache] Invalidated plan: {fingerprint}")
            
            return result
            
        except Exception as e:
            print(f"[@ai_plan_cache] Error invalidating plan: {e}")
            return False
    
    def get_cache_stats(self, team_id: str) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Args:
            team_id: Team ID for security
            
        Returns:
            Dictionary with cache statistics
        """
        # This would require additional database queries
        # For now, return basic stats
        return {
            'cache_enabled': True,
            'message': 'Cache statistics not implemented yet'
        }
