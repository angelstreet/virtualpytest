"""
Host Action Routes - Device Action Execution

This module receives action execution requests from the server and routes them
to the appropriate device's ActionExecutor.
"""

from flask import Blueprint, request, jsonify, current_app
from src.lib.utils.app_utils import get_team_id

# Create blueprint
host_actions_bp = Blueprint('host_actions', __name__, url_prefix='/host/action')

@host_actions_bp.route('/executeBatch', methods=['POST'])
def action_execute_batch():
    """Execute batch of actions using device's ActionExecutor"""
    try:
        print("[@route:host_actions:action_execute_batch] Starting batch action execution")
        
        # Get request data
        data = request.get_json() or {}
        actions = data.get('actions', [])
        retry_actions = data.get('retry_actions', [])
        device_id = data.get('device_id', 'device1')
        tree_id = data.get('tree_id')
        edge_id = data.get('edge_id')
        action_set_id = data.get('action_set_id')
        
        print(f"[@route:host_actions:action_execute_batch] Processing {len(actions)} actions for device: {device_id}")
        
        # Validate
        if not actions:
            return jsonify({'success': False, 'error': 'actions are required'}), 400
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False, 
                'error': f'Device {device_id} not found in host'
            }), 404
        
        device = host_devices[device_id]
        
        # Check if device has action_executor
        if not hasattr(device, 'action_executor') or not device.action_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have ActionExecutor initialized'
            }), 500
        
        # Execute actions using device's ActionExecutor
        from src.lib.utils.app_utils import get_team_id
        result = device.action_executor.execute_actions(
            actions=actions,
            retry_actions=retry_actions,
            team_id=get_team_id()
        )
        
        print(f"[@route:host_actions:action_execute_batch] Execution completed: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_actions:action_execute_batch] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host action execution failed: {str(e)}'
        }), 500

@host_actions_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for host action service"""
    return jsonify({
        'success': True,
        'message': 'Host action service is running'
    })
