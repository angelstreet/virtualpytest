"""
AI Plan Generation Database Operations

Clean database operations for AI plan caching with no fallbacks or legacy support.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime


def store_plan(fingerprint: str, original_prompt: str, normalized_prompt: str, 
               device_model: str, userinterface_name: str, available_nodes: List[str],
               plan: Dict, team_id: str) -> bool:
    """
    Store a successful AI plan in the database.
    
    Args:
        fingerprint: Unique plan fingerprint
        original_prompt: Original user prompt
        normalized_prompt: Normalized prompt for matching
        device_model: Device model (e.g., 'android_mobile')
        userinterface_name: Interface name (e.g., 'horizon_android_mobile')
        available_nodes: List of available navigation nodes
        plan: AI-generated plan dictionary
        team_id: Team ID for multi-tenancy
        
    Returns:
        True if stored successfully, False otherwise
    """
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        plan_data = {
            'fingerprint': fingerprint,
            'original_prompt': original_prompt,
            'normalized_prompt': normalized_prompt,
            'device_model': device_model,
            'userinterface_name': userinterface_name,
            'available_nodes': json.dumps(available_nodes),
            'plan': json.dumps(plan),
            'team_id': team_id,
            'success_rate': 1.0,  # First execution is successful
            'execution_count': 1,
            'success_count': 1,
            'created_at': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat()
        }
        
        result = supabase.table('ai_plan_generation').insert(plan_data).execute()
        
        if result.data:
            print(f"[@ai_plan_generation_db] Stored plan with fingerprint: {fingerprint}")
            return True
        else:
            print(f"[@ai_plan_generation_db] Failed to store plan: {result}")
            return False
            
    except Exception as e:
        print(f"[@ai_plan_generation_db] Error storing plan: {e}")
        return False


def get_plan_by_fingerprint(fingerprint: str, team_id: str) -> Optional[Dict]:
    """
    Get a cached plan by its fingerprint.
    
    Args:
        fingerprint: Plan fingerprint
        team_id: Team ID for security
        
    Returns:
        Plan dictionary or None if not found
    """
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        result = supabase.table('ai_plan_generation')\
            .select('*')\
            .eq('fingerprint', fingerprint)\
            .eq('team_id', team_id)\
            .single()\
            .execute()
        
        if result.data:
            plan_data = result.data
            # Parse JSON fields
            plan_data['available_nodes'] = json.loads(plan_data['available_nodes'])
            plan_data['plan'] = json.loads(plan_data['plan'])
            return plan_data
        else:
            return None
            
    except Exception as e:
        print(f"[@ai_plan_generation_db] Error getting plan by fingerprint: {e}")
        return None


def find_compatible_plans(normalized_prompt: str, device_model: str, 
                         userinterface_name: str, available_nodes: List[str],
                         team_id: str, min_success_rate: float = 0.6) -> List[Dict]:
    """
    Find compatible cached plans for the given context.
    
    Args:
        normalized_prompt: Normalized prompt to match
        device_model: Device model
        userinterface_name: Interface name
        available_nodes: Current available nodes
        team_id: Team ID for security
        min_success_rate: Minimum success rate threshold
        
    Returns:
        List of compatible plans ordered by success rate
    """
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Find plans with matching prompt and context
        result = supabase.table('ai_plan_generation')\
            .select('*')\
            .eq('normalized_prompt', normalized_prompt)\
            .eq('device_model', device_model)\
            .eq('userinterface_name', userinterface_name)\
            .eq('team_id', team_id)\
            .gte('success_rate', min_success_rate)\
            .gt('execution_count', 0)\
            .order('success_rate', desc=True)\
            .order('execution_count', desc=True)\
            .limit(5)\
            .execute()
        
        if not result.data:
            return []
        
        compatible_plans = []
        available_nodes_set = set(available_nodes)
        
        for plan_data in result.data:
            # Parse JSON fields
            plan_data['available_nodes'] = json.loads(plan_data['available_nodes'])
            plan_data['plan'] = json.loads(plan_data['plan'])
            
            # Check node compatibility (80% overlap required)
            cached_nodes_set = set(plan_data['available_nodes'])
            if not cached_nodes_set or not available_nodes_set:
                continue
                
            overlap = len(cached_nodes_set.intersection(available_nodes_set))
            total_unique = len(cached_nodes_set.union(available_nodes_set))
            compatibility = overlap / total_unique if total_unique > 0 else 0
            
            if compatibility >= 0.8:
                plan_data['compatibility_score'] = compatibility
                compatible_plans.append(plan_data)
        
        print(f"[@ai_plan_generation_db] Found {len(compatible_plans)} compatible plans for '{normalized_prompt}'")
        return compatible_plans
        
    except Exception as e:
        print(f"[@ai_plan_generation_db] Error finding compatible plans: {e}")
        return []


def update_plan_metrics(fingerprint: str, success: bool, execution_time_ms: int, team_id: str) -> bool:
    """
    Update plan performance metrics after execution.
    
    Args:
        fingerprint: Plan fingerprint
        success: Whether execution was successful
        execution_time_ms: Execution time in milliseconds
        team_id: Team ID for security
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Get current metrics
        current = supabase.table('ai_plan_generation')\
            .select('execution_count', 'success_count')\
            .eq('fingerprint', fingerprint)\
            .eq('team_id', team_id)\
            .single()\
            .execute()
        
        if not current.data:
            return False
        
        # Calculate new metrics
        new_execution_count = current.data['execution_count'] + 1
        new_success_count = current.data['success_count'] + (1 if success else 0)
        new_success_rate = new_success_count / new_execution_count
        
        # Update metrics
        update_data = {
            'execution_count': new_execution_count,
            'success_count': new_success_count,
            'success_rate': new_success_rate,
            'last_used': datetime.now().isoformat()
        }
        
        result = supabase.table('ai_plan_generation')\
            .update(update_data)\
            .eq('fingerprint', fingerprint)\
            .eq('team_id', team_id)\
            .execute()
        
        if result.data:
            print(f"[@ai_plan_generation_db] Updated metrics for {fingerprint}: {new_success_rate:.2f} success rate")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"[@ai_plan_generation_db] Error updating plan metrics: {e}")
        return False


def invalidate_plan(fingerprint: str, team_id: str) -> bool:
    """
    Manually invalidate a plan (delete it from cache).
    
    Args:
        fingerprint: Plan fingerprint to invalidate
        team_id: Team ID for security
        
    Returns:
        True if invalidated successfully, False otherwise
    """
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        result = supabase.table('ai_plan_generation')\
            .delete()\
            .eq('fingerprint', fingerprint)\
            .eq('team_id', team_id)\
            .execute()
        
        if result.data:
            print(f"[@ai_plan_generation_db] Invalidated plan: {fingerprint}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"[@ai_plan_generation_db] Error invalidating plan: {e}")
        return False


def cleanup_old_plans(team_id: str, days_old: int = 90, min_success_rate: float = 0.3) -> int:
    """
    Clean up old or poorly performing plans.
    
    Args:
        team_id: Team ID for security
        days_old: Remove plans older than this many days
        min_success_rate: Remove plans with success rate below this threshold
        
    Returns:
        Number of plans removed
    """
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Calculate cutoff date
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
        
        # Remove old plans with low success rates
        result = supabase.table('ai_plan_generation')\
            .delete()\
            .eq('team_id', team_id)\
            .lt('last_used', cutoff_date.isoformat())\
            .lt('success_rate', min_success_rate)\
            .execute()
        
        removed_count = len(result.data) if result.data else 0
        print(f"[@ai_plan_generation_db] Cleaned up {removed_count} old plans for team {team_id}")
        return removed_count
        
    except Exception as e:
        print(f"[@ai_plan_generation_db] Error cleaning up plans: {e}")
        return 0
