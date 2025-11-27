"""
Users Management Routes
Handles user profile management and team assignments
"""
from flask import Blueprint, request, jsonify
from typing import Optional
import logging

from shared.src.lib.database import users_db
from backend_server.src.lib.error_handler import handle_error

logger = logging.getLogger(__name__)

server_users_bp = Blueprint('server_users', __name__, url_prefix='/server/users')


@server_users_bp.route('', methods=['GET'])
def get_users():
    """
    Get all users (admin only)
    Returns user profiles with team information
    """
    try:
        users = users_db.get_all_users()
        return jsonify(users), 200
        
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return handle_error(e, "Failed to fetch users")


@server_users_bp.route('/<user_id>', methods=['GET'])
def get_user(user_id: str):
    """
    Get a specific user by ID
    """
    try:
        user = users_db.get_user(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(user), 200
        
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return handle_error(e, f"Failed to fetch user {user_id}")


@server_users_bp.route('/<user_id>', methods=['PUT'])
def update_user(user_id: str):
    """
    Update a user profile
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user = users_db.update_user(user_id, data)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        logger.info(f"User updated: {user_id}")
        return jsonify(user), 200
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return handle_error(e, f"Failed to update user {user_id}")


@server_users_bp.route('/<user_id>', methods=['DELETE'])
def delete_user(user_id: str):
    """
    Delete a user (admin only)
    Note: This deletes from auth.users which cascades to profiles
    """
    try:
        success = users_db.delete_user(user_id)
        
        if not success:
            return jsonify({"error": "User not found"}), 404
        
        logger.info(f"User deleted: {user_id}")
        return jsonify({"message": "User deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return handle_error(e, f"Failed to delete user {user_id}")


@server_users_bp.route('/<user_id>/assign-team', methods=['POST'])
def assign_user_to_team(user_id: str):
    """
    Assign a user to a team (admin only)
    Sets the primary team_id and optionally adds to team_members
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('team_id'):
            return jsonify({"error": "team_id is required"}), 400
        
        team_id = data['team_id']
        success = users_db.assign_user_to_team(user_id, team_id, data.get('team_role', 'member'))
        
        if not success:
            return jsonify({"error": "Failed to assign user to team"}), 500
        
        logger.info(f"User {user_id} assigned to team {team_id}")
        return jsonify({"message": "User assigned to team successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error assigning user to team: {str(e)}")
        return handle_error(e, "Failed to assign user to team")


@server_users_bp.route('/<user_id>/remove-team', methods=['POST'])
def remove_user_from_team(user_id: str):
    """
    Remove a user from a team (admin only)
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('team_id'):
            return jsonify({"error": "team_id is required"}), 400
        
        team_id = data['team_id']
        success = users_db.remove_user_from_team(user_id, team_id)
        
        if not success:
            return jsonify({"error": "Failed to remove user from team"}), 500
        
        logger.info(f"User {user_id} removed from team {team_id}")
        return jsonify({"message": "User removed from team successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error removing user from team: {str(e)}")
        return handle_error(e, "Failed to remove user from team")

