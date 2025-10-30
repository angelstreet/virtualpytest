"""
Host Action Routes - Device Action Execution (Async)

All action execution is async - returns execution_id immediately and polls for results.
"""

import time
import threading
import uuid
from flask import Blueprint, request, jsonify, current_app
from backend_host.src.orchestrator import ExecutionOrchestrator

# Create blueprint
host_actions_bp = Blueprint('host_actions', __name__, url_prefix='/host/action')


def _execute_actions_thread(device, execution_id, actions, retry_actions, failure_actions, team_id, context_data):
    """Background thread for async action execution"""
    try:
        print(f"[@route:host_actions:_execute_actions_thread] Starting execution: {execution_id}")
        
        # Update status to running
        with device.action_executor._lock:
            device.action_executor._executions[execution_id]['status'] = 'running'
            device.action_executor._executions[execution_id]['message'] = 'Executing actions...'
        
        # Execute actions through orchestrator (logs + screenshots)
        result = ExecutionOrchestrator.execute_actions(
            device=device,
            actions=actions,
            retry_actions=retry_actions,
            failure_actions=failure_actions,
            team_id=team_id,
            context=None
        )
        
        # Update execution state with result
        with device.action_executor._lock:
            device.action_executor._executions[execution_id]['status'] = 'completed'
            device.action_executor._executions[execution_id]['result'] = result
            device.action_executor._executions[execution_id]['progress'] = 100
            device.action_executor._executions[execution_id]['message'] = result.get('message', 'Completed')
        
        print(f"[@route:host_actions:_execute_actions_thread] Execution completed: {execution_id}")
        
    except Exception as e:
        print(f"[@route:host_actions:_execute_actions_thread] Execution failed: {execution_id}, error: {e}")
        import traceback
        traceback.print_exc()
        
        # Update execution state with error
        with device.action_executor._lock:
            device.action_executor._executions[execution_id]['status'] = 'error'
            device.action_executor._executions[execution_id]['error'] = str(e)
            device.action_executor._executions[execution_id]['message'] = f'Execution failed: {str(e)}'


@host_actions_bp.route('/executeBatch', methods=['POST'])
def action_execute_batch():
    """Execute batch of actions asynchronously - returns execution_id immediately"""
    try:
        print("[@route:host_actions:action_execute_batch] Starting async action execution")
        
        # Get request data
        data = request.get_json() or {}
        actions = data.get('actions', [])
        retry_actions = data.get('retry_actions', [])
        failure_actions = data.get('failure_actions', [])
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        
        print(f"[@route:host_actions:action_execute_batch] Processing {len(actions)} actions for device: {device_id}, team: {team_id}")
        
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
            return jsonify({'success': False, 'error': f'Device {device_id} not found in host'}), 404
        
        device = host_devices[device_id]
        
        # Check if device has action_executor
        if not hasattr(device, 'action_executor') or not device.action_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have ActionExecutor initialized'
            }), 500
        
        # Always execute asynchronously to prevent HTTP timeouts
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        # Store execution state
        if not hasattr(device.action_executor, '_executions'):
            device.action_executor._executions = {}
            device.action_executor._lock = threading.Lock()
        
        with device.action_executor._lock:
            device.action_executor._executions[execution_id] = {
                'execution_id': execution_id,
                'status': 'running',
                'result': None,
                'error': None,
                'start_time': time.time(),
                'progress': 0,
                'message': 'Action execution starting...'
            }
        
        # Start execution in background thread
        context_data = {
            'tree_id': data.get('tree_id'),
            'edge_id': data.get('edge_id'),
            'action_set_id': data.get('action_set_id'),
            'target_node_id': data.get('target_node_id'),
            'skip_db_recording': data.get('skip_db_recording', False)
        }
        
        thread = threading.Thread(
            target=_execute_actions_thread,
            args=(device, execution_id, actions, retry_actions, failure_actions, team_id, context_data),
            daemon=True
        )
        thread.start()
        
        print(f"[@route:host_actions:action_execute_batch] Async execution started: {execution_id}")
        
        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'message': 'Action execution started'
        })
        
    except Exception as e:
        print(f"[@route:host_actions:action_execute_batch] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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
        if not hasattr(device.action_executor, '_executions'):
            return jsonify({
                'success': False,
                'error': f'Execution {execution_id} not found'
            }), 404
        
        with device.action_executor._lock:
            if execution_id not in device.action_executor._executions:
                return jsonify({
                    'success': False,
                    'error': f'Execution {execution_id} not found'
                }), 404
            
            execution = device.action_executor._executions[execution_id].copy()
        
        # Calculate elapsed time
        elapsed_time_ms = int((time.time() - execution['start_time']) * 1000)
        
        return jsonify({
            'success': True,
            'execution_id': execution['execution_id'],
            'status': execution['status'],
            'result': execution.get('result'),
            'error': execution.get('error'),
            'progress': execution.get('progress', 0),
            'message': execution.get('message', ''),
            'elapsed_time_ms': elapsed_time_ms
        })
        
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
