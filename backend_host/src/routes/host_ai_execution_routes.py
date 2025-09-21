"""
Host AI Execution Routes

Host-side AI execution endpoints that execute using device AI executors.
Matches the server AI execution route organization.
"""

from flask import Blueprint, request, jsonify
from src.lib.utils.host_utils import get_controller, get_device_by_id

# Create blueprint - matches server AI execution organization
host_ai_execution_bp = Blueprint('host_ai_execution', __name__, url_prefix='/host/ai-execution')

@host_ai_execution_bp.route('/executeTask', methods=['POST'])
def execute_task():
    """Execute AI task using device AI executor."""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        task_description = data.get('task_description', '')
        
        print(f"[@route:host_aiagent:execute_task] Executing AI task for device: {device_id}")
        print(f"[@route:host_aiagent:execute_task] Task: {task_description}")
        
        # Get device and check AI executor
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        print(f"[@route:host_aiagent:execute_task] Using AI executor for device: {device_id}")
        
        device_model = device.device_model
        print(f"[@route:host_aiagent:execute_task] Device model: {device_model}")
        
        # Get userinterface_name from request or use default
        userinterface_name = data.get('userinterface_name', 'horizon_android_mobile')
        team_id = data.get('team_id', 'default')
        
        print(f"[@route:host_aiagent:execute_task] Using AI executor for task execution")
        print(f"[@route:host_aiagent:execute_task] Interface: {userinterface_name}, Team: {team_id}")
        
        # Check if this is async execution (has task_id)
        task_id = data.get('task_id')
        
        if task_id:
            print(f"[@route:host_aiagent:execute_task] 2-PHASE: Starting AI task for {task_id}")
            
            # Use AI executor for both plan generation and execution
            result = device.ai_executor.execute_prompt(
                task_description,
                userinterface_name,
                team_id=team_id,
                async_execution=True
            )
            
            if not result.get('success'):
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to execute AI task'),
                    'execution_id': result.get('execution_id'),
                    'device_id': device_id
                }), 400
            
            # Return immediately with execution started
            return jsonify({
                'success': True,
                'message': result.get('message', 'AI execution started'),
                'task_id': task_id,
                'execution_id': result.get('execution_id'),
                'device_id': device_id,
                'plan_steps': result.get('plan_steps', 0)
            }), 202
        else:
            # Synchronous execution using AI executor
            print(f"[@route:host_aiagent:execute_task] SYNC: Direct AI execution (no task_id)")
            result = device.ai_executor.execute_prompt(
                task_description,
                userinterface_name,
                team_id=team_id,
                async_execution=False
            )
            
            # Determine appropriate status code based on execution result
            success = result.get('success', False)
            status_code = 200 if success else 400
            
            return jsonify({
                'success': success,
                'message': result.get('message', ''),
                'error': result.get('error'),
                'execution_id': result.get('execution_id'),
                'steps_executed': result.get('steps_executed', 0),
                'total_steps': result.get('total_steps', 0),
                'execution_time': result.get('execution_time', 0),
                'device_id': device_id
            }), status_code
        
    except Exception as e:
        print(f"[@route:host_aiagent:execute_task] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI task execution error: {str(e)}'
        }), 500

@host_ai_execution_bp.route('/getStatus', methods=['POST'])
def get_status():
    """Get AI execution status."""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_aiagent:get_status] Getting AI status for device: {device_id}")
        
        # Get device and check AI executor
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AI executor initialized'
            }), 404
        
        # Get status from AI executor (placeholder - AI executor doesn't have get_status method)
        status = {
            'success': True,
            'message': 'AI executor is available',
            'device_id': device_id
        }
        
        return jsonify(status)
        
    except Exception as e:
        print(f"[@route:host_aiagent:get_status] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI status error: {str(e)}'
        }), 500

@host_ai_execution_bp.route('/stopExecution', methods=['POST'])
def stop_execution():
    """Stop AI execution."""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_aiagent:stop_execution] Stopping AI execution for device: {device_id}")
        
        # Get device and check AI executor
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AI executor initialized'
            }), 404
        
        # Stop execution (placeholder - AI executor doesn't have stop_execution method)
        result = {
            'success': True,
            'message': 'AI execution stop requested',
            'device_id': device_id
        }
        
        # Determine appropriate status code based on stop result
        success = result.get('success', False)
        status_code = 200 if success else 400
        
        return jsonify({
            'success': success,
            'message': result.get('message', ''),
            'execution_log': result.get('execution_log', []),
            'device_id': device_id
        }), status_code
        
    except Exception as e:
        print(f"[@route:host_aiagent:stop_execution] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI stop execution error: {str(e)}'
        }), 500 