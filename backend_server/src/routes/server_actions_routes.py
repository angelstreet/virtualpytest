"""
Server Actions Routes - Action Execution Only

This module provides action execution endpoints.
Actions are now embedded directly in navigation edges, so no database CRUD operations are needed.
"""

from flask import Blueprint, request, jsonify
import os
import sys
import time

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Actions are now embedded in navigation edges - no separate database operations needed

# Import default team ID from app utils
from shared.lib.utils.app_utils import DEFAULT_TEAM_ID
from shared.lib.utils.route_utils import proxy_to_host
import requests

# Create blueprint
server_actions_bp = Blueprint('server_actions', __name__, url_prefix='/server/action')

# =====================================================
# ACTION EXECUTION
# =====================================================

@server_actions_bp.route('/executeBatch', methods=['POST'])
def action_execute_batch():
    """Execute batch of actions with embedded action objects"""
    try:
        print("[@route:server_actions:action_execute_batch] Starting batch action execution")
        
        # Get request data
        data = request.get_json() or {}
        actions = data.get('actions', [])  # Array of embedded action objects
        host = data.get('host', {})
        device_id = data.get('device_id', 'device1')
        retry_actions = data.get('retry_actions', [])
        
        print(f"[@route:server_actions:action_execute_batch] Processing {len(actions)} main actions, {len(retry_actions)} retry actions")
        print(f"[@route:server_actions:action_execute_batch] Host: {host.get('host_name')}, Device ID: {device_id}")
        
        # Validate
        if not actions:
            return jsonify({'success': False, 'error': 'actions are required'}), 400
        
        if not host:
            return jsonify({'success': False, 'error': 'host is required'}), 400
        
        # Proxy execution to host
        host_url = host.get('host_url', f"http://{host.get('host_name')}:6109")
        
        # Prepare execution payload with embedded actions
        execution_payload = {
            'actions': actions,  # Actions are already embedded objects with all parameters
            'device_id': device_id,
            'retry_actions': retry_actions
        }
        
        print(f"[@route:server_actions:action_execute_batch] Proxying to host: {host_url}")
        
        # Proxy to host
        response = proxy_to_host(
            host_url=host_url,
            endpoint='/host/action/executeBatch',
            method='POST',
            data=execution_payload,
            timeout=300  # 5 minute timeout for action execution
        )
        
        if response.get('success'):
            print(f"[@route:server_actions:action_execute_batch] Batch execution completed successfully")
            return jsonify(response)
        else:
            print(f"[@route:server_actions:action_execute_batch] Batch execution failed: {response.get('error', 'Unknown error')}")
            return jsonify(response), 400
            
    except Exception as e:
        print(f"[@route:server_actions:action_execute_batch] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error during batch action execution: {str(e)}'
        }), 500

@server_actions_bp.route('/execute', methods=['POST'])
def action_execute_single():
    """Execute a single action with embedded action object"""
    try:
        print("[@route:server_actions:action_execute_single] Starting single action execution")
        
        # Get request data
        data = request.get_json() or {}
        action = data.get('action', {})  # Single embedded action object
        host = data.get('host', {})
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:server_actions:action_execute_single] Executing action: {action.get('name', 'unnamed')}")
        print(f"[@route:server_actions:action_execute_single] Host: {host.get('host_name')}, Device ID: {device_id}")
        
        # Validate
        if not action:
            return jsonify({'success': False, 'error': 'action is required'}), 400
        
        if not host:
            return jsonify({'success': False, 'error': 'host is required'}), 400
        
        # Convert single action to batch format
        actions = [action]
        
        # Proxy execution to host
        host_url = host.get('host_url', f"http://{host.get('host_name')}:6109")
        
        # Prepare execution payload
        execution_payload = {
            'actions': actions,
            'device_id': device_id,
            'retry_actions': []
        }
        
        print(f"[@route:server_actions:action_execute_single] Proxying to host: {host_url}")
        
        # Proxy to host
        response = proxy_to_host(
            host_url=host_url,
            endpoint='/host/action/executeBatch',
            method='POST',
            data=execution_payload,
            timeout=60  # 1 minute timeout for single action
        )
        
        if response.get('success'):
            print(f"[@route:server_actions:action_execute_single] Single action execution completed successfully")
            return jsonify(response)
        else:
            print(f"[@route:server_actions:action_execute_single] Single action execution failed: {response.get('error', 'Unknown error')}")
            return jsonify(response), 400
            
    except Exception as e:
        print(f"[@route:server_actions:action_execute_single] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error during single action execution: {str(e)}'
        }), 500

# =====================================================
# HEALTH CHECK
# =====================================================

@server_actions_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for action execution service"""
    return jsonify({
        'success': True,
        'message': 'Action execution service is running',
        'note': 'Actions are now embedded in navigation edges'
    })


 