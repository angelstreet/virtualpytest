"""
Users Database Operations

This module provides functions for managing user profiles in the database.
Users represent authenticated accounts with roles and permissions.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from shared.src.lib.utils.supabase_utils import get_supabase_client

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()

def get_all_users() -> List[Dict]:
    """Retrieve all users from Supabase."""
    supabase = get_supabase()
    try:
        result = supabase.table('profiles').select('*').execute()
        
        users = []
        for profile in result.data:
            # Get user's teams
            teams_result = supabase.table('team_members')\
                .select('team_id, teams(name)')\
                .eq('user_id', profile['id'])\
                .execute()
            
            # Get primary team name if exists
            primary_team_name = None
            if profile.get('team_id'):
                team_result = supabase.table('teams')\
                    .select('name')\
                    .eq('id', profile['team_id'])\
                    .single()\
                    .execute()
                if team_result.data:
                    primary_team_name = team_result.data.get('name')
            
            users.append({
                'id': profile['id'],
                'full_name': profile.get('full_name', ''),
                'email': profile.get('email', ''),
                'avatar_url': profile.get('avatar_url'),
                'role': profile.get('role', 'viewer'),
                'team_id': profile.get('team_id'),
                'team': primary_team_name,
                'teams': [t['teams']['name'] for t in teams_result.data if t.get('teams')],
                'permissions': profile.get('permissions', []),
                'created_at': profile.get('created_at'),
                'updated_at': profile.get('updated_at')
            })
        
        return users
    except Exception as e:
        print(f"[@db:users_db:get_all_users] Error: {e}")
        return []

def get_user(user_id: str) -> Optional[Dict]:
    """Retrieve a user by ID from Supabase."""
    supabase = get_supabase()
    try:
        result = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
        
        if result.data:
            profile = result.data
            
            # Get user's teams
            teams_result = supabase.table('team_members')\
                .select('team_id, teams(name)')\
                .eq('user_id', user_id)\
                .execute()
            
            # Get primary team name if exists
            primary_team_name = None
            if profile.get('team_id'):
                team_result = supabase.table('teams')\
                    .select('name')\
                    .eq('id', profile['team_id'])\
                    .single()\
                    .execute()
                if team_result.data:
                    primary_team_name = team_result.data.get('name')
            
            return {
                'id': profile['id'],
                'full_name': profile.get('full_name', ''),
                'email': profile.get('email', ''),
                'avatar_url': profile.get('avatar_url'),
                'role': profile.get('role', 'viewer'),
                'team_id': profile.get('team_id'),
                'team': primary_team_name,
                'teams': [t['teams']['name'] for t in teams_result.data if t.get('teams')],
                'permissions': profile.get('permissions', []),
                'created_at': profile.get('created_at'),
                'updated_at': profile.get('updated_at')
            }
        return None
    except Exception as e:
        print(f"[@db:users_db:get_user] Error: {e}")
        return None

def update_user(user_id: str, user_data: Dict) -> Optional[Dict]:
    """Update an existing user profile."""
    supabase = get_supabase()
    try:
        update_data = {}
        
        if 'full_name' in user_data:
            update_data['full_name'] = user_data['full_name']
        if 'avatar_url' in user_data:
            update_data['avatar_url'] = user_data['avatar_url']
        if 'role' in user_data:
            update_data['role'] = user_data['role']
        if 'team_id' in user_data:
            update_data['team_id'] = user_data['team_id']
        if 'permissions' in user_data:
            update_data['permissions'] = user_data['permissions']
        
        if not update_data:
            return None
        
        result = supabase.table('profiles').update(update_data).eq('id', user_id).execute()
        
        if result.data and len(result.data) > 0:
            return get_user(user_id)
        return None
    except Exception as e:
        print(f"[@db:users_db:update_user] Error: {e}")
        return None

def delete_user(user_id: str) -> bool:
    """Delete a user (admin only). Deletes from auth.users which cascades to profiles."""
    supabase = get_supabase()
    try:
        # Check if user exists
        user = get_user(user_id)
        if not user:
            print(f"[@db:users_db:delete_user] User not found: {user_id}")
            return False
        
        # Delete user from auth.users (requires service_role key)
        supabase.auth.admin.delete_user(user_id)
        return True
    except Exception as e:
        print(f"[@db:users_db:delete_user] Error: {e}")
        return False

def assign_user_to_team(user_id: str, team_id: str, team_role: str = 'member') -> bool:
    """Assign a user to a team."""
    supabase = get_supabase()
    try:
        # Update user's primary team
        supabase.table('profiles').update({'team_id': team_id}).eq('id', user_id).execute()
        
        # Add to team_members if not already there
        try:
            insert_data = {
                'team_id': team_id,
                'user_id': user_id,
                'role': team_role,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            supabase.table('team_members').insert(insert_data).execute()
        except Exception:
            # Ignore if already exists (UNIQUE constraint)
            pass
        
        return True
    except Exception as e:
        print(f"[@db:users_db:assign_user_to_team] Error: {e}")
        return False

def remove_user_from_team(user_id: str, team_id: str) -> bool:
    """Remove a user from a team."""
    supabase = get_supabase()
    try:
        # Remove from team_members
        supabase.table('team_members')\
            .delete()\
            .eq('team_id', team_id)\
            .eq('user_id', user_id)\
            .execute()
        
        # Clear primary team if it matches
        profile = supabase.table('profiles').select('team_id').eq('id', user_id).single().execute()
        if profile.data and profile.data.get('team_id') == team_id:
            supabase.table('profiles').update({'team_id': None}).eq('id', user_id).execute()
        
        return True
    except Exception as e:
        print(f"[@db:users_db:remove_user_from_team] Error: {e}")
        return False

