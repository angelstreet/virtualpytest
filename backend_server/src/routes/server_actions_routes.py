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
# ACTION INFORMATION (for frontend compatibility)
# =====================================================

@server_actions_bp.route('/getActions', methods=['GET'])
def get_actions():
    """Get available actions for a device model (for frontend compatibility)."""
    try:
        device_model = request.args.get('device_model', 'android_mobile')
        
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
        
        # Use ActionExecutor directly (same pattern as navigation execution)
        try:
            from backend_core.src.services.actions.action_executor import ActionExecutor
            from shared.lib.utils.app_utils import get_team_id
            
            action_executor = ActionExecutor(
                host=host,
                device_id=device_id,
                tree_id=None,  # Not needed for direct action execution
                edge_id=None,  # Not needed for direct action execution
                team_id=get_team_id()
            )
            
            result = action_executor.execute_actions(
                actions=actions,
                retry_actions=retry_actions
            )
            
            print(f"[@route:server_actions:action_execute_batch] Execution completed: success={result.get('success')}")
            
            return jsonify(result)
            
        except Exception as e:
            print(f"[@route:server_actions:action_execute_batch] ActionExecutor error: {e}")
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


 