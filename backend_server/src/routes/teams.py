"""
Teams Management Routes
Handles CRUD operations for teams
"""
from flask import Blueprint, request, jsonify
from typing import Optional
import logging

from ..lib.supabase_client import get_supabase_client
from ..lib.error_handler import handle_error
from ..lib.auth_middleware import require_auth, require_admin

logger = logging.getLogger(__name__)

teams_bp = Blueprint('teams', __name__, url_prefix='/server/teams')


@teams_bp.route('', methods=['GET'])
@require_auth
def get_teams():
    """
    Get all teams
    Admin: sees all teams
    Regular user: sees only their teams
    """
    try:
        supabase = get_supabase_client()
        user_id = request.user_id
        user_role = request.user_role
        
        # Admins can see all teams
        if user_role == 'admin':
            response = supabase.table('teams').select('*').execute()
        else:
            # Regular users see only teams they belong to
            response = supabase.table('team_members')\
                .select('teams(*)')\
                .eq('user_id', user_id)\
                .execute()
            
            # Extract teams from nested response
            teams = [member['teams'] for member in response.data if member.get('teams')]
            return jsonify(teams), 200
        
        # Get member counts for each team
        teams_data = response.data
        for team in teams_data:
            count_response = supabase.rpc('get_team_member_count', {'team_uuid': team['id']}).execute()
            team['member_count'] = count_response.data if count_response.data else 0
        
        return jsonify(teams_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching teams: {str(e)}")
        return handle_error(e, "Failed to fetch teams")


@teams_bp.route('/<team_id>', methods=['GET'])
@require_auth
def get_team(team_id: str):
    """Get a specific team by ID"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('teams').select('*').eq('id', team_id).single().execute()
        
        if not response.data:
            return jsonify({"error": "Team not found"}), 404
        
        # Get member count
        count_response = supabase.rpc('get_team_member_count', {'team_uuid': team_id}).execute()
        response.data['member_count'] = count_response.data if count_response.data else 0
        
        return jsonify(response.data), 200
        
    except Exception as e:
        logger.error(f"Error fetching team {team_id}: {str(e)}")
        return handle_error(e, f"Failed to fetch team {team_id}")


@teams_bp.route('', methods=['POST'])
@require_admin
def create_team():
    """Create a new team (admin only)"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({"error": "Team name is required"}), 400
        
        supabase = get_supabase_client()
        user_id = request.user_id
        
        # Create team
        team_data = {
            'name': data['name'],
            'description': data.get('description', ''),
            'tenant_id': data.get('tenant_id', '00000000-0000-0000-0000-000000000000'),  # Default tenant
            'created_by': user_id,
            'is_default': data.get('is_default', False)
        }
        
        response = supabase.table('teams').insert(team_data).execute()
        
        if not response.data:
            return jsonify({"error": "Failed to create team"}), 500
        
        team = response.data[0]
        team['member_count'] = 0
        
        logger.info(f"Team created: {team['id']} by user {user_id}")
        return jsonify(team), 201
        
    except Exception as e:
        logger.error(f"Error creating team: {str(e)}")
        return handle_error(e, "Failed to create team")


@teams_bp.route('/<team_id>', methods=['PUT'])
@require_admin
def update_team(team_id: str):
    """Update a team (admin only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        supabase = get_supabase_client()
        
        # Build update data
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'is_default' in data:
            update_data['is_default'] = data['is_default']
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        response = supabase.table('teams').update(update_data).eq('id', team_id).execute()
        
        if not response.data:
            return jsonify({"error": "Team not found"}), 404
        
        team = response.data[0]
        
        # Get member count
        count_response = supabase.rpc('get_team_member_count', {'team_uuid': team_id}).execute()
        team['member_count'] = count_response.data if count_response.data else 0
        
        logger.info(f"Team updated: {team_id}")
        return jsonify(team), 200
        
    except Exception as e:
        logger.error(f"Error updating team {team_id}: {str(e)}")
        return handle_error(e, f"Failed to update team {team_id}")


@teams_bp.route('/<team_id>', methods=['DELETE'])
@require_admin
def delete_team(team_id: str):
    """Delete a team (admin only)"""
    try:
        supabase = get_supabase_client()
        
        # Check if team exists
        check_response = supabase.table('teams').select('id').eq('id', team_id).execute()
        
        if not check_response.data:
            return jsonify({"error": "Team not found"}), 404
        
        # Delete team (cascade will remove team_members entries)
        supabase.table('teams').delete().eq('id', team_id).execute()
        
        logger.info(f"Team deleted: {team_id}")
        return jsonify({"message": "Team deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error deleting team {team_id}: {str(e)}")
        return handle_error(e, f"Failed to delete team {team_id}")


@teams_bp.route('/<team_id>/members', methods=['GET'])
@require_auth
def get_team_members(team_id: str):
    """Get all members of a team"""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('team_members')\
            .select('*, profiles(*)')\
            .eq('team_id', team_id)\
            .execute()
        
        members = []
        for member in response.data:
            if member.get('profiles'):
                profile = member['profiles']
                members.append({
                    'id': member['id'],
                    'user_id': profile['id'],
                    'full_name': profile.get('full_name', ''),
                    'email': profile.get('email', ''),
                    'avatar_url': profile.get('avatar_url'),
                    'role': profile.get('role', 'viewer'),
                    'team_role': member.get('role', 'member'),
                    'created_at': member.get('created_at')
                })
        
        return jsonify(members), 200
        
    except Exception as e:
        logger.error(f"Error fetching team members for {team_id}: {str(e)}")
        return handle_error(e, f"Failed to fetch team members")


@teams_bp.route('/<team_id>/members', methods=['POST'])
@require_admin
def add_team_member(team_id: str):
    """Add a user to a team (admin only)"""
    try:
        data = request.get_json()
        
        if not data or not data.get('user_id'):
            return jsonify({"error": "user_id is required"}), 400
        
        supabase = get_supabase_client()
        
        member_data = {
            'team_id': team_id,
            'user_id': data['user_id'],
            'role': data.get('role', 'member')
        }
        
        response = supabase.table('team_members').insert(member_data).execute()
        
        if not response.data:
            return jsonify({"error": "Failed to add team member"}), 500
        
        logger.info(f"User {data['user_id']} added to team {team_id}")
        return jsonify(response.data[0]), 201
        
    except Exception as e:
        logger.error(f"Error adding team member: {str(e)}")
        return handle_error(e, "Failed to add team member")


@teams_bp.route('/<team_id>/members/<user_id>', methods=['DELETE'])
@require_admin
def remove_team_member(team_id: str, user_id: str):
    """Remove a user from a team (admin only)"""
    try:
        supabase = get_supabase_client()
        
        supabase.table('team_members')\
            .delete()\
            .eq('team_id', team_id)\
            .eq('user_id', user_id)\
            .execute()
        
        logger.info(f"User {user_id} removed from team {team_id}")
        return jsonify({"message": "Team member removed successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error removing team member: {str(e)}")
        return handle_error(e, "Failed to remove team member")

