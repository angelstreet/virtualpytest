"""
Server AI Execution Routes

Core AI task execution, planning, and status monitoring.
Consolidates AI agent execution functionality with modern host_name pattern.
"""

import uuid
from flask import Blueprint, request, jsonify
from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params

# Create blueprint
server_ai_execution_bp = Blueprint('server_ai_execution', __name__, url_prefix='/server/ai-execution')

@server_ai_execution_bp.route('/executeTask', methods=['POST'])
def execute_task():
    """Execute AI task with async support using modern host_name pattern"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        # Generate task_id for async execution tracking
        task_id = str(uuid.uuid4())
        request_data['task_id'] = task_id
        
        print(f"[@server_ai_execution] Executing AI task with ID: {task_id}")
        print(f"[@server_ai_execution] Task description: {request_data.get('task_description', 'N/A')}")
        print(f"[@server_ai_execution] Device ID: {request_data.get('device_id', 'N/A')}")
        print(f"[@server_ai_execution] Host name: {request_data.get('host_name', 'N/A')}")
        # Get team_id from query params (standardized pattern)
        team_id = request.args.get('team_id')
        print(f"[@server_ai_execution] Team ID: {team_id or 'N/A'}")
        
        # Extract parameters for query string
        query_params = {}
        if 'device_id' in request_data:
            query_params['device_id'] = request_data['device_id']
        if team_id:
            query_params['team_id'] = team_id
        
        # Proxy to host with parameters
        response_data, status_code = proxy_to_host_with_params(
            '/host/ai-execution/executeTask',
            'POST',
            request_data,
            query_params
        )
        
        print(f"[@server_ai_execution] Host response status: {status_code}")
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_ai_execution] Error executing AI task: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500

# Plan generation moved to server_ai_generation_routes.py to match host structure

@server_ai_execution_bp.route('/getStatus', methods=['POST'])
def get_status():
    """Get AI execution status using modern host_name pattern"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        print(f"[@server_ai_execution] Getting AI status for device: {request_data.get('device_id', 'N/A')}")
        # Get team_id from query params (standardized pattern)
        team_id = request.args.get('team_id')
        print(f"[@server_ai_execution] Team ID: {team_id or 'N/A'}")
        
        # Extract parameters for query string
        query_params = {}
        if 'device_id' in request_data:
            query_params['device_id'] = request_data['device_id']
        if team_id:
            query_params['team_id'] = team_id
        
        # Proxy to host with parameters
        response_data, status_code = proxy_to_host_with_params(
            '/host/ai-execution/getStatus',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_ai_execution] Error getting AI status: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500

@server_ai_execution_bp.route('/stopExecution', methods=['POST'])
def stop_execution():
    """Stop AI execution using modern host_name pattern"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        print(f"[@server_ai_execution] Stopping AI execution for device: {request_data.get('device_id', 'N/A')}")
        # Get team_id from query params (standardized pattern)
        team_id = request.args.get('team_id')
        print(f"[@server_ai_execution] Team ID: {team_id or 'N/A'}")
        
        # Extract parameters for query string
        query_params = {}
        if 'device_id' in request_data:
            query_params['device_id'] = request_data['device_id']
        if team_id:
            query_params['team_id'] = team_id
        
        # Proxy to host with parameters
        response_data, status_code = proxy_to_host_with_params(
            '/host/ai-execution/stopExecution',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_ai_execution] Error stopping AI execution: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500

@server_ai_execution_bp.route('/resetCache', methods=['POST'])
def reset_cache():
    """Reset AI plan cache - delete all cached plans for a team"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        # Validate required parameters (following modern pattern)
        host_name = request_data.get('host_name') or request.args.get('host_name')
        if not host_name:
            return jsonify({'success': False, 'error': 'host_name required in request body or query parameters'}), 400
        
        # team_id is automatically added to query params by buildServerUrl in frontend
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        print(f"[@server_ai_execution] Resetting AI plan cache for team: {team_id}, host: {host_name}")
        
        # Delete all cached plans for this team
        from shared.src.lib.supabase.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Count before delete
        count_result = supabase.table('ai_plan_generation')\
            .select('id', count='exact')\
            .eq('team_id', team_id)\
            .execute()
        
        deleted_count = count_result.count if count_result.count else 0
        
        # Delete all plans
        delete_result = supabase.table('ai_plan_generation')\
            .delete()\
            .eq('team_id', team_id)\
            .execute()
        
        print(f"[@server_ai_execution] ✅ Cache reset complete: {deleted_count} plans deleted")
        
        return jsonify({
            'success': True,
            'message': f'Cache cleared: {deleted_count} plans deleted',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        print(f"[@server_ai_execution] ❌ Error resetting cache: {e}")
        return jsonify({
            'success': False,
            'error': f'Error resetting cache: {str(e)}'
        }), 500

# Compatibility analysis moved to server_ai_generation_routes.py to match host structure
