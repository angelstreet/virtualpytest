"""
AI Plan Cache

Clean cache implementation for AI plan generation with no fallbacks.
"""

from typing import Dict, List, Optional, Any
from .ai_cache_utils import (
    normalize_prompt, 
    generate_fingerprint, 
    create_context_signature,
    should_reuse_plan
)
from shared.src.lib.supabase.ai_plan_generation_db import (
    store_plan,
    get_plan_by_fingerprint,
    find_compatible_plans,
    update_plan_metrics,
    invalidate_plan
)
from .ai_types import ExecutionResult


class AIExecutorCache:
    """
    Clean AI plan cache with explicit control and no fallbacks.
    """
    
    def __init__(self):
        """Initialize cache"""
        print("[@ai_plan_cache] Initialized AI plan cache")
    
    def find_cached_plan(self, prompt: str, context: Dict, team_id: str) -> Optional[Dict]:
        """
        Find a cached plan for the given prompt and context.
        
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
            exact_match = get_plan_by_fingerprint(fingerprint, team_id)
            if exact_match and should_reuse_plan(exact_match, context):
                print(f"[@ai_plan_cache] Found exact match for fingerprint: {fingerprint}")
                return exact_match
            
            # Try compatible plans
            normalized_prompt = normalize_prompt(prompt)
            compatible_plans = find_compatible_plans(
                normalized_prompt=normalized_prompt,
                device_model=context.get('device_model'),
                userinterface_name=context.get('userinterface_name'),
                available_nodes=context.get('available_nodes', []),
                team_id=team_id
            )
            
            # Return best compatible plan
            for plan in compatible_plans:
                if should_reuse_plan(plan, context):
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
