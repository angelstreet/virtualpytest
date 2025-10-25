"""
Host Action Routes - Device Action Execution

This module receives action execution requests from the server and routes them
to the appropriate device's ActionExecutor.
"""

from flask import Blueprint, request, jsonify, current_app

# Create blueprint
host_actions_bp = Blueprint('host_actions', __name__, url_prefix='/host/action')

@host_actions_bp.route('/executeBatch', methods=['POST'])
def action_execute_batch():
    """Execute batch of actions using device's ActionExecutor - supports async execution"""
    try:
        print("[@route:host_actions:action_execute_batch] Starting batch action execution")
        
        # Get request data
        data = request.get_json() or {}
        actions = data.get('actions', [])
        retry_actions = data.get('retry_actions', [])
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        tree_id = data.get('tree_id')
        edge_id = data.get('edge_id')
        action_set_id = data.get('action_set_id')
        skip_db_recording = data.get('skip_db_recording', False)
        async_execution = data.get('async_execution', True)  # Default to async to prevent timeouts
        
        print(f"[@route:host_actions:action_execute_batch] Processing {len(actions)} actions for device: {device_id}, team: {team_id}")
        print(f"[@route:host_actions:action_execute_batch] Async Execution: {async_execution}")
        
        # Validate
        if not actions:
            return jsonify({'success': False, 'error': 'actions are required'}), 400
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
            
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
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
        
        # Set navigation context on ActionExecutor for proper metrics recording
        if tree_id:
            device.action_executor.tree_id = tree_id
        if edge_id:
            device.action_executor.edge_id = edge_id
        if action_set_id:
            device.action_executor.action_set_id = action_set_id
        
        # Set skip_db_recording flag in device's navigation_context (for frontend testing)
        if skip_db_recording:
            device.navigation_context['skip_db_recording'] = True
            print(f"[@route:host_actions:action_execute_batch] Frontend testing mode - DB recording disabled")
        else:
            # Clear the flag if it was previously set
            device.navigation_context.pop('skip_db_recording', None)
        
        print(f"[@route:host_actions:action_execute_batch] Set navigation context: tree_id={tree_id}, edge_id={edge_id}, action_set_id={action_set_id}, skip_db_recording={skip_db_recording}")
        
        # Execute actions: async or sync
        if async_execution:
            # Async execution - returns immediately with execution_id
            result = device.action_executor.execute_actions_async(
                actions=actions,
                retry_actions=retry_actions,
                team_id=team_id
            )
            print(f"[@route:host_actions:action_execute_batch] Async execution started: {result.get('execution_id')}")
        else:
            # Sync execution - waits for completion (may timeout)
            result = device.action_executor.execute_actions(
                actions=actions,
                retry_actions=retry_actions,
                team_id=team_id
            )
            print(f"[@route:host_actions:action_execute_batch] Sync execution completed: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_actions:action_execute_batch] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host action execution failed: {str(e)}'
        }), 500


@host_actions_bp.route('/execution/<execution_id>/status', methods=['GET'])
def action_execution_status(execution_id):
    """Get status of async action execution"""
    try:
        # Get query parameters
        device_id = request.args.get('device_id', 'device1')
        
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
        
        # Get execution status
        status = device.action_executor.get_execution_status(execution_id)
        return jsonify(status)
        
    except Exception as e:
        print(f"[@route:host_actions:execution_status] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get execution status: {str(e)}'
        }), 500

@host_actions_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for host action service"""
    return jsonify({
        'success': True,
        'message': 'Host action service is running'
    })
