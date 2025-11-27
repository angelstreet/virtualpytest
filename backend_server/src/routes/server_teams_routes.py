"""
Teams Management Routes
Handles CRUD operations for teams
"""
from flask import Blueprint, request, jsonify
from typing import Optional
import logging

from shared.src.lib.database import teams_db
from backend_server.src.lib.error_handler import handle_error

logger = logging.getLogger(__name__)

server_teams_bp = Blueprint('server_teams', __name__, url_prefix='/server/teams')


@server_teams_bp.route('', methods=['GET'])
def get_teams():
    """
    Get all teams
    Admin: sees all teams
    Regular user: sees only their teams
    """
    try:
        teams = teams_db.get_all_teams()
        return jsonify(teams), 200
        
    except Exception as e:
        logger.error(f"Error fetching teams: {str(e)}")
        return handle_error(e, "Failed to fetch teams")


@server_teams_bp.route('/<team_id>', methods=['GET'])
def get_team(team_id: str):
    """Get a specific team by ID"""
    try:
        team = teams_db.get_team(team_id)
        
        if not team:
            return jsonify({"error": "Team not found"}), 404
        
        return jsonify(team), 200
        
    except Exception as e:
        logger.error(f"Error fetching team {team_id}: {str(e)}")
        return handle_error(e, f"Failed to fetch team {team_id}")


@server_teams_bp.route('', methods=['POST'])
def create_team():
    """Create a new team (admin only)"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({"error": "Team name is required"}), 400
        
        team = teams_db.create_team(data)
        
        if not team:
            return jsonify({"error": "Failed to create team"}), 500
        
        logger.info(f"Team created: {team['id']} by user {user_id}")
        return jsonify(team), 201
        
    except Exception as e:
        logger.error(f"Error creating team: {str(e)}")
        return handle_error(e, "Failed to create team")


@server_teams_bp.route('/<team_id>', methods=['PUT'])
def update_team(team_id: str):
    """Update a team (admin only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        team = teams_db.update_team(team_id, data)
        
        if not team:
            return jsonify({"error": "Team not found"}), 404
        
        logger.info(f"Team updated: {team_id}")
        return jsonify(team), 200
        
    except Exception as e:
        logger.error(f"Error updating team {team_id}: {str(e)}")
        return handle_error(e, f"Failed to update team {team_id}")


@server_teams_bp.route('/<team_id>', methods=['DELETE'])
def delete_team(team_id: str):
    """Delete a team (admin only)"""
    try:
        success = teams_db.delete_team(team_id)
        
        if not success:
            return jsonify({"error": "Team not found"}), 404
        
        logger.info(f"Team deleted: {team_id}")
        return jsonify({"message": "Team deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error deleting team {team_id}: {str(e)}")
        return handle_error(e, f"Failed to delete team {team_id}")


@server_teams_bp.route('/<team_id>/members', methods=['GET'])
def get_team_members(team_id: str):
    """Get all members of a team"""
    try:
        members = teams_db.get_team_members(team_id)
        return jsonify(members), 200
        
    except Exception as e:
        logger.error(f"Error fetching team members for {team_id}: {str(e)}")
        return handle_error(e, f"Failed to fetch team members")


@server_teams_bp.route('/<team_id>/members', methods=['POST'])
def add_team_member(team_id: str):
    """Add a user to a team (admin only)"""
    try:
        data = request.get_json()
        
        if not data or not data.get('user_id'):
            return jsonify({"error": "user_id is required"}), 400
        
        member = teams_db.add_team_member(team_id, data['user_id'], data.get('role', 'member'))
        
        if not member:
            return jsonify({"error": "Failed to add team member"}), 500
        
        logger.info(f"User {data['user_id']} added to team {team_id}")
        return jsonify(member), 201
        
    except Exception as e:
        logger.error(f"Error adding team member: {str(e)}")
        return handle_error(e, "Failed to add team member")


@server_teams_bp.route('/<team_id>/members/<user_id>', methods=['DELETE'])
def remove_team_member(team_id: str, user_id: str):
    """Remove a user from a team (admin only)"""
    try:
        success = teams_db.remove_team_member(team_id, user_id)
        
        if not success:
            return jsonify({"error": "Failed to remove team member"}), 500
        
        logger.info(f"User {user_id} removed from team {team_id}")
        return jsonify({"message": "Team member removed successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error removing team member: {str(e)}")
        return handle_error(e, "Failed to remove team member")

