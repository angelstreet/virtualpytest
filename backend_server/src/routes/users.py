"""
Users Management Routes
Handles user profile management and team assignments
"""
from flask import Blueprint, request, jsonify
from typing import Optional
import logging

from ..lib.supabase_client import get_supabase_client
from ..lib.error_handler import handle_error
from ..lib.auth_middleware import require_auth, require_admin

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__, url_prefix='/server/users')


@users_bp.route('', methods=['GET'])
@require_admin
def get_users():
    """
    Get all users (admin only)
    Returns user profiles with team information
    """
    try:
        supabase = get_supabase_client()
        
        # Get all profiles
        response = supabase.table('profiles').select('*').execute()
        
        users_data = []
        for profile in response.data:
            # Get user's teams
            teams_response = supabase.table('team_members')\
                .select('team_id, teams(name)')\
                .eq('user_id', profile['id'])\
                .execute()
            
            # Get primary team name if exists
            primary_team_name = None
            if profile.get('team_id'):
                team_response = supabase.table('teams')\
                    .select('name')\
                    .eq('id', profile['team_id'])\
                    .single()\
                    .execute()
                if team_response.data:
                    primary_team_name = team_response.data.get('name')
            
            # Build user object
            user = {
                'id': profile['id'],
                'full_name': profile.get('full_name', ''),
                'email': profile.get('email', ''),
                'avatar_url': profile.get('avatar_url'),
                'role': profile.get('role', 'viewer'),
                'team_id': profile.get('team_id'),
                'team': primary_team_name,
                'teams': [t['teams']['name'] for t in teams_response.data if t.get('teams')],
                'permissions': profile.get('permissions', []),
                'created_at': profile.get('created_at'),
                'updated_at': profile.get('updated_at')
            }
            users_data.append(user)
        
        return jsonify(users_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return handle_error(e, "Failed to fetch users")


@users_bp.route('/<user_id>', methods=['GET'])
@require_auth
def get_user(user_id: str):
    """
    Get a specific user by ID
    Users can view their own profile, admins can view any profile
    """
    try:
        supabase = get_supabase_client()
        current_user_id = request.user_id
        current_user_role = request.user_role
        
        # Check permission (self or admin)
        if user_id != current_user_id and current_user_role != 'admin':
            return jsonify({"error": "Unauthorized"}), 403
        
        response = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
        
        if not response.data:
            return jsonify({"error": "User not found"}), 404
        
        profile = response.data
        
        # Get user's teams
        teams_response = supabase.table('team_members')\
            .select('team_id, teams(name)')\
            .eq('user_id', user_id)\
            .execute()
        
        # Get primary team name if exists
        primary_team_name = None
        if profile.get('team_id'):
            team_response = supabase.table('teams')\
                .select('name')\
                .eq('id', profile['team_id'])\
                .single()\
                .execute()
            if team_response.data:
                primary_team_name = team_response.data.get('name')
        
        user = {
            'id': profile['id'],
            'full_name': profile.get('full_name', ''),
            'email': profile.get('email', ''),
            'avatar_url': profile.get('avatar_url'),
            'role': profile.get('role', 'viewer'),
            'team_id': profile.get('team_id'),
            'team': primary_team_name,
            'teams': [t['teams']['name'] for t in teams_response.data if t.get('teams')],
            'permissions': profile.get('permissions', []),
            'created_at': profile.get('created_at'),
            'updated_at': profile.get('updated_at')
        }
        
        return jsonify(user), 200
        
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return handle_error(e, f"Failed to fetch user {user_id}")


@users_bp.route('/<user_id>', methods=['PUT'])
@require_auth
def update_user(user_id: str):
    """
    Update a user profile
    Users can update their own profile (limited fields)
    Admins can update any profile (all fields)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        supabase = get_supabase_client()
        current_user_id = request.user_id
        current_user_role = request.user_role
        
        # Check permission
        is_self = user_id == current_user_id
        is_admin = current_user_role == 'admin'
        
        if not is_self and not is_admin:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Build update data based on permissions
        update_data = {}
        
        # Fields users can update for themselves
        if 'full_name' in data:
            update_data['full_name'] = data['full_name']
        if 'avatar_url' in data:
            update_data['avatar_url'] = data['avatar_url']
        
        # Admin-only fields
        if is_admin:
            if 'role' in data:
                update_data['role'] = data['role']
            if 'permissions' in data:
                update_data['permissions'] = data['permissions']
            if 'team_id' in data:
                update_data['team_id'] = data['team_id']
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        response = supabase.table('profiles').update(update_data).eq('id', user_id).execute()
        
        if not response.data:
            return jsonify({"error": "User not found"}), 404
        
        logger.info(f"User updated: {user_id}")
        return jsonify(response.data[0]), 200
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return handle_error(e, f"Failed to update user {user_id}")


@users_bp.route('/<user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id: str):
    """
    Delete a user (admin only)
    Note: This deletes from auth.users which cascades to profiles
    """
    try:
        supabase = get_supabase_client()
        
        # Check if user exists
        check_response = supabase.table('profiles').select('id').eq('id', user_id).execute()
        
        if not check_response.data:
            return jsonify({"error": "User not found"}), 404
        
        # Delete user from auth.users (cascades to profiles)
        # Note: This requires service_role key with admin privileges
        supabase.auth.admin.delete_user(user_id)
        
        logger.info(f"User deleted: {user_id}")
        return jsonify({"message": "User deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return handle_error(e, f"Failed to delete user {user_id}")


@users_bp.route('/<user_id>/assign-team', methods=['POST'])
@require_admin
def assign_user_to_team(user_id: str):
    """
    Assign a user to a team (admin only)
    Sets the primary team_id and optionally adds to team_members
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('team_id'):
            return jsonify({"error": "team_id is required"}), 400
        
        supabase = get_supabase_client()
        team_id = data['team_id']
        
        # Update user's primary team
        supabase.table('profiles').update({'team_id': team_id}).eq('id', user_id).execute()
        
        # Add to team_members if not already there
        try:
            member_data = {
                'team_id': team_id,
                'user_id': user_id,
                'role': data.get('team_role', 'member')
            }
            supabase.table('team_members').insert(member_data).execute()
        except Exception as e:
            # Ignore if already exists (UNIQUE constraint)
            if 'duplicate key' not in str(e).lower():
                raise
        
        logger.info(f"User {user_id} assigned to team {team_id}")
        return jsonify({"message": "User assigned to team successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error assigning user to team: {str(e)}")
        return handle_error(e, "Failed to assign user to team")


@users_bp.route('/<user_id>/remove-team', methods=['POST'])
@require_admin
def remove_user_from_team(user_id: str):
    """
    Remove a user from a team (admin only)
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('team_id'):
            return jsonify({"error": "team_id is required"}), 400
        
        supabase = get_supabase_client()
        team_id = data['team_id']
        
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
        
        logger.info(f"User {user_id} removed from team {team_id}")
        return jsonify({"message": "User removed from team successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error removing user from team: {str(e)}")
        return handle_error(e, "Failed to remove user from team")

