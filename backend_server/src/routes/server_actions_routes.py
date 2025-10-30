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

from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params
import requests

# Create blueprint
server_actions_bp = Blueprint('server_actions', __name__, url_prefix='/server/action')

# =====================================================
# ACTION INFORMATION (for frontend compatibility)
# =====================================================

@server_actions_bp.route('/getActions', methods=['GET'])
def get_actions():
    """Get available actions for a device model (for frontend compatibility)."""
    try:
        device_model = request.args.get('device_model', 'android_mobile')
        team_id = request.args.get('team_id')
        
        # Return basic action types available for the device model
        # This is mainly for frontend compatibility - actions are now embedded in edges
        actions = [
            {
                'id': 'click_element',
                'name': 'click_element',
                'command': 'click_element',
                'device_model': device_model,
                'params': {
                    'element_id': '',
                    'wait_time': 0
                }
            },
            {
                'id': 'tap_coordinates',
                'name': 'tap_coordinates', 
                'command': 'tap_coordinates',
                'device_model': device_model,
                'params': {
                    'x': 0,
                    'y': 0,
                    'wait_time': 0
                }
            },
            {
                'id': 'press_key',
                'name': 'press_key',
                'command': 'press_key', 
                'device_model': device_model,
                'params': {
                    'key': '',
                    'wait_time': 0
                }
            }
        ]
        
        return jsonify({
            'success': True,
            'actions': actions
        })
        
    except Exception as e:
        print(f'[@route:server_actions:get_actions] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# =====================================================
# ACTION EXECUTION
# =====================================================

@server_actions_bp.route('/executeBatch', methods=['POST'])
def action_execute_batch():
    """Execute batch of actions using ActionExecutor directly (same as navigation execution)"""
    try:
        print("[@route:server_actions:action_execute_batch] Starting batch action execution")
        
        # Get request data
        data = request.get_json() or {}
        actions = data.get('actions', [])  # Array of embedded action objects
        host_name = data.get('host_name')
        device_id = data.get('device_id', 'device1')
        retry_actions = data.get('retry_actions', [])
        team_id = request.args.get('team_id')
        
        # NEW: Navigation context for proper metrics recording
        tree_id = data.get('tree_id')
        edge_id = data.get('edge_id')
        action_set_id = data.get('action_set_id')
        skip_db_recording = data.get('skip_db_recording', False)
        
        print(f"[@route:server_actions:action_execute_batch] Processing {len(actions)} main actions, {len(retry_actions)} retry actions")
        print(f"[@route:server_actions:action_execute_batch] Host: {host_name}, Device ID: {device_id}")
        print(f"[@route:server_actions:action_execute_batch] Navigation context: tree_id={tree_id}, edge_id={edge_id}, action_set_id={action_set_id}, skip_db_recording={skip_db_recording}")
        
        # Validate
        if not actions:
            return jsonify({'success': False, 'error': 'actions are required'}), 400
        
        if not host_name:
            return jsonify({'success': False, 'error': 'host_name is required'}), 400
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Proxy to host action execution endpoint
        try:
            from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params
            
            # Prepare execution payload
            execution_payload = {
                'actions': actions,
                'retry_actions': retry_actions,
                'device_id': device_id,
                'tree_id': tree_id,
                'edge_id': edge_id,
                'action_set_id': action_set_id,
                'skip_db_recording': skip_db_recording,
                'team_id': team_id
            }
            
            # Extract parameters for query string
            query_params = {}
            if device_id:
                query_params['device_id'] = device_id
            if team_id:
                query_params['team_id'] = team_id
            
            # Use short timeout - only for initial async response (execution_id)
            timeout = 10
            
            # Proxy to host action execution endpoint with parameters
            response_data, status_code = proxy_to_host_with_params(
                '/host/action/executeBatch', 
                'POST', 
                execution_payload, 
                query_params, 
                timeout=timeout
            )
            
            print(f"[@route:server_actions:action_execute_batch] Execution completed: success={response_data.get('success')}")
            
            return jsonify(response_data), status_code
            
        except Exception as e:
            print(f"[@route:server_actions:action_execute_batch] Proxy error: {e}")
            return jsonify({
                'success': False,
                'error': f'Action execution failed: {str(e)}',
                'passed_count': 0,
                'total_count': len(actions)
            }), 500
            
    except Exception as e:
        print(f"[@route:server_actions:action_execute_batch] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error during batch action execution: {str(e)}'
        }), 500


@server_actions_bp.route('/execution/<execution_id>/status', methods=['GET'])
def get_action_execution_status(execution_id):
    """
    Get status of async action execution
    
    Query parameters:
    - device_id: Device ID
    - host_name: Host name (required)
    """
    try:
        print(f"[@route:server_actions:get_status] Getting status for execution {execution_id}")
        
        device_id = request.args.get('device_id')
        host_name = request.args.get('host_name')
        
        # Validate required parameters
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name query parameter is required'
            }), 400
        
        # Proxy to host status endpoint
        query_params = {}
        if device_id:
            query_params['device_id'] = device_id
        
        from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params
        response_data, status_code = proxy_to_host_with_params(
            f'/host/action/execution/{execution_id}/status',
            'GET',
            None,
            query_params,
            timeout=5
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_actions:get_status] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get execution status: {str(e)}'
        }), 500

@server_actions_bp.route('/execute', methods=['POST'])
def action_execute_single():
    """Execute a single action with embedded action object"""
    try:
        print("[@route:server_actions:action_execute_single] Starting single action execution")
        
        # Get request data
        data = request.get_json() or {}
        action = data.get('action', {})  # Single embedded action object
        host_name = data.get('host_name')
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        
        print(f"[@route:server_actions:action_execute_single] Executing action: {action.get('command', 'unknown_command')}")
        print(f"[@route:server_actions:action_execute_single] Host: {host_name}, Device ID: {device_id}")
        
        # Validate
        if not action:
            return jsonify({'success': False, 'error': 'action is required'}), 400
        
        if not host_name:
            return jsonify({'success': False, 'error': 'host_name is required'}), 400
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Convert single action to batch format
        actions = [action]
        
        # Prepare execution payload - always async (no HTTP timeout risk)
        execution_payload = {
            'actions': actions,
            'device_id': device_id,
            'retry_actions': [],
            'team_id': team_id
        }
        
        # Extract parameters for query string
        query_params = {}
        if device_id:
            query_params['device_id'] = device_id
        if team_id:
            query_params['team_id'] = team_id
        
        print(f"[@route:server_actions:action_execute_single] Proxying to host: {host_name}")
        
        # Proxy to host with parameters (short timeout for async start)
        response_data, status_code = proxy_to_host_with_params(
            '/host/action/executeBatch',
            'POST',
            execution_payload,
            query_params,
            timeout=10
        )
        
        if response_data.get('success'):
            print(f"[@route:server_actions:action_execute_single] Single action execution completed successfully")
            return jsonify(response_data), status_code
        else:
            print(f"[@route:server_actions:action_execute_single] Single action execution failed: {response_data.get('error', 'Unknown error')}")
            return jsonify(response_data), status_code
            
    except Exception as e:
        print(f"[@route:server_actions:action_execute_single] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error during single action execution: {str(e)}'
        }), 500

# =====================================================
# HEALTH CHECK
# =====================================================

@server_actions_bp.route('/checkDependenciesBatch', methods=['POST'])
def check_dependencies_batch():
    """Check if actions are used in other edges (dependency check) - DEPRECATED: Legacy action_ids removed"""
    try:
        data = request.get_json()
        # Legacy action_ids support removed - action_sets are now embedded in edges
        
        # Return no dependencies since action_ids are no longer used
        return jsonify({
            'success': True,
            'has_shared_actions': False,
            'edges': [],
            'count': 0,
            'message': 'Dependency check completed - no shared actions found'
        })
        
    except Exception as e:
        print(f"[@route:server_actions:check_dependencies_batch] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error during dependency check: {str(e)}'
        }), 500

@server_actions_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for action execution service"""
    return jsonify({
        'success': True,
        'message': 'Action execution service is running',
        'note': 'Actions are now embedded in navigation edges'
    })


 