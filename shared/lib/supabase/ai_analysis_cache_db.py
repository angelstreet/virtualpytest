"""
AI Analysis Cache Database Operations

This module provides functions for managing AI analysis cache in the database.
Used for storing temporary analysis results during the two-step test case generation process.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from shared.lib.utils.supabase_utils import get_supabase_client

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()

def save_analysis_cache(analysis_id: str, prompt: str, analysis_result: Dict, 
                       compatibility_matrix: Dict, team_id: str) -> Dict:
    """Save AI analysis result to cache for later retrieval."""
    supabase = get_supabase()
    
    cache_data = {
        'id': analysis_id,
        'team_id': team_id,
        'prompt': prompt,
        'analysis_result': json.dumps(analysis_result),
        'compatibility_matrix': json.dumps(compatibility_matrix),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }
    
    try:
        result = supabase.table('ai_analysis_cache').insert(cache_data).execute()
        if result.data:
            cached_analysis = dict(result.data[0])
            # Parse JSON fields back
            cached_analysis['analysis_result'] = json.loads(cached_analysis['analysis_result'])
            cached_analysis['compatibility_matrix'] = json.loads(cached_analysis['compatibility_matrix'])
            return cached_analysis
    except Exception as e:
        print(f"Error saving analysis cache: {e}")
        
    return cache_data

def get_analysis_cache(analysis_id: str, team_id: str) -> Optional[Dict]:
    """Retrieve cached analysis result by analysis_id."""
    supabase = get_supabase()
    
    try:
        result = supabase.table('ai_analysis_cache').select(
            'id', 'prompt', 'analysis_result', 'compatibility_matrix', 
            'created_at', 'expires_at'
        ).eq('id', analysis_id).eq('team_id', team_id).execute()
        
        if result.data:
            cache_entry = dict(result.data[0])
            
            # Check if cache has expired
            expires_at = datetime.fromisoformat(cache_entry['expires_at'].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at.replace(tzinfo=None):
                # Cache expired, delete it
                delete_analysis_cache(analysis_id, team_id)
                return None
            
            # Parse JSON fields
            cache_entry['analysis_result'] = json.loads(cache_entry['analysis_result'])
            cache_entry['compatibility_matrix'] = json.loads(cache_entry['compatibility_matrix'])
            return cache_entry
            
    except Exception as e:
        print(f"Error retrieving analysis cache: {e}")
        
    return None

def delete_analysis_cache(analysis_id: str, team_id: str) -> bool:
    """Delete specific cached analysis result."""
    supabase = get_supabase()
    
    try:
        result = supabase.table('ai_analysis_cache').delete().eq('id', analysis_id).eq('team_id', team_id).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"Error deleting analysis cache: {e}")
        return False

def cleanup_expired_cache(team_id: str = None) -> int:
    """Clean up expired cache entries. Returns number of deleted entries."""
    supabase = get_supabase()
    
    try:
        query = supabase.table('ai_analysis_cache').delete().lt('expires_at', datetime.now(timezone.utc).isoformat())
        
        if team_id:
            query = query.eq('team_id', team_id)
            
        result = query.execute()
        return len(result.data)
    except Exception as e:
        print(f"Error cleaning up expired cache: {e}")
        return 0

def get_cached_analyses_for_team(team_id: str, limit: int = 10) -> List[Dict]:
    """Get recent cached analyses for a team (for debugging/monitoring)."""
    supabase = get_supabase()
    
    try:
        result = supabase.table('ai_analysis_cache').select(
            'id', 'prompt', 'created_at', 'expires_at'
        ).eq('team_id', team_id).order('created_at', desc=True).limit(limit).execute()
        
        return [dict(cache_entry) for cache_entry in result.data]
    except Exception as e:
        print(f"Error retrieving cached analyses: {e}")
        return []

def get_cache_stats(team_id: str) -> Dict:
    """Get cache statistics for monitoring."""
    supabase = get_supabase()
    
    try:
        # Get total cache entries
        total_result = supabase.table('ai_analysis_cache').select('id', count='exact').eq('team_id', team_id).execute()
        total_entries = total_result.count or 0
        
        # Get expired entries
        expired_result = supabase.table('ai_analysis_cache').select('id', count='exact').eq('team_id', team_id).lt('expires_at', datetime.now(timezone.utc).isoformat()).execute()
        expired_entries = expired_result.count or 0
        
        # Get valid entries
        valid_entries = total_entries - expired_entries
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_hit_rate': 0.0 if total_entries == 0 else round((valid_entries / total_entries) * 100, 2)
        }
    except Exception as e:
        print(f"Error getting cache stats: {e}")
        return {
            'total_entries': 0,
            'valid_entries': 0,
            'expired_entries': 0,
            'cache_hit_rate': 0.0
        }
