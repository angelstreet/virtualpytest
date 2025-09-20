"""
Host AI Routes - Device AI Execution

This module receives AI execution requests from the server and routes them
to the appropriate device's AIExecutor.
"""

from flask import Blueprint, request, jsonify, current_app
from shared.lib.utils.app_utils import get_team_id

# Create blueprint
host_ai_bp = Blueprint('host_ai', __name__, url_prefix='/host/ai')

@host_ai_bp.route('/generatePlan', methods=['POST'])
def ai_generate_plan():
    """Generate AI plan using device's AIExecutor"""
    try:
        print("[@route:host_ai:ai_generate_plan] Starting AI plan generation")
        
        # Get request data
        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        device_id = data.get('device_id', 'device1')
        userinterface_name = data.get('userinterface_name', 'default')
        current_node_id = data.get('current_node_id')
        
        print(f"[@route:host_ai:ai_generate_plan] Generating plan for device: {device_id}")
        print(f"[@route:host_ai:ai_generate_plan] Prompt: {prompt[:100]}...")
        
        # Validate
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt is required'
            }), 400
        
        # Get device from app registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        # Create AI service for this device
        from backend_core.src.services.ai.ai_plan_executor import AIPlanExecutor
        from shared.lib.utils.app_utils import get_team_id
        
        print(f"[@route:host_ai:ai_generate_plan] Using AI service for device: {device_id}")
        
        # Get host dict for AI service
        from backend_core.src.controllers.controller_manager import get_host
        host = get_host()
        
        # Create AI service and generate plan
        ai_executor = AIPlanExecutor(host=host, device_id=device_id, team_id=get_team_id())
        result = ai_executor.execute_prompt(
            prompt=prompt,
            userinterface_name=userinterface_name,
            current_node_id=current_node_id,
            async_execution=False  # Synchronous for plan generation
        )
        
        print(f"[@route:host_ai:ai_generate_plan] Plan generation result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_ai:ai_generate_plan] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI plan generation failed: {str(e)}'
        }), 500

@host_ai_bp.route('/executePlan', methods=['POST'])
def ai_execute_plan():
    """Execute AI plan using device's AIExecutor"""
    try:
        print("[@route:host_ai:ai_execute_plan] Starting AI plan execution")
        
        # Get request data
        data = request.get_json() or {}
        plan_id = data.get('plan_id', '')
        plan = data.get('plan', {})
        device_id = data.get('device_id', 'device1')
        userinterface_name = data.get('userinterface_name', 'default')
        
        print(f"[@route:host_ai:ai_execute_plan] Executing plan {plan_id} for device: {device_id}")
        
        # Validate
        if not plan_id or not plan:
            return jsonify({
                'success': False,
                'error': 'Plan ID and plan data are required'
            }), 400
        
        # Get device from app registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        # Create AI service for this device
        from backend_core.src.services.ai.ai_plan_executor import AIPlanExecutor
        from shared.lib.utils.app_utils import get_team_id
        
        print(f"[@route:host_ai:ai_execute_plan] Using AI service for device: {device_id}")
        
        # Get host dict for AI service
        from backend_core.src.controllers.controller_manager import get_host
        host = get_host()
        
        # Create AI service and execute plan
        ai_executor = AIPlanExecutor(host=host, device_id=device_id, team_id=get_team_id())
        result = ai_executor.execute_prompt(
            prompt=f"Execute plan: {plan.get('description', 'AI plan')}",
            userinterface_name=userinterface_name,
            async_execution=False  # Synchronous for plan execution
        )
        
        print(f"[@route:host_ai:ai_execute_plan] Plan execution result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_ai:ai_execute_plan] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI plan execution failed: {str(e)}'
        }), 500

@host_ai_bp.route('/executePrompt', methods=['POST'])
def ai_execute_prompt():
    """Generate and execute AI plan in one call using device's AIExecutor"""
    try:
        print("[@route:host_ai:ai_execute_prompt] Starting AI prompt execution")
        
        # Get request data
        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        device_id = data.get('device_id', 'device1')
        userinterface_name = data.get('userinterface_name', 'default')
        current_node_id = data.get('current_node_id')
        
        print(f"[@route:host_ai:ai_execute_prompt] Executing prompt for device: {device_id}")
        print(f"[@route:host_ai:ai_execute_prompt] Prompt: {prompt[:100]}...")
        
        # Validate
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt is required'
            }), 400
        
        # Get device from app registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        # Create AI service for this device
        from backend_core.src.services.ai.ai_plan_executor import AIPlanExecutor
        from shared.lib.utils.app_utils import get_team_id
        
        print(f"[@route:host_ai:ai_execute_prompt] Using AI service for device: {device_id}")
        
        # Get host dict for AI service
        from backend_core.src.controllers.controller_manager import get_host
        host = get_host()
        
        # Create AI service and execute prompt
        ai_executor = AIPlanExecutor(host=host, device_id=device_id, team_id=get_team_id())
        result = ai_executor.execute_prompt(
            prompt=prompt,
            userinterface_name=userinterface_name,
            current_node_id=current_node_id,
            async_execution=True  # Async for prompt execution
        )
        
        print(f"[@route:host_ai:ai_execute_prompt] Prompt execution result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_ai:ai_execute_prompt] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI prompt execution failed: {str(e)}'
        }), 500

@host_ai_bp.route('/getDevicePosition', methods=['GET'])
def ai_get_device_position():
    """Get device position using device's AIExecutor"""
    try:
        print("[@route:host_ai:ai_get_device_position] Getting device position")
        
        # Get device_id from query params
        device_id = request.args.get('device_id', 'device1')
        
        print(f"[@route:host_ai:ai_get_device_position] Getting position for device: {device_id}")
        
        # Get device from app registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        # Create AI service for this device
        from backend_core.src.services.ai.ai_plan_executor import AIPlanExecutor
        from shared.lib.utils.app_utils import get_team_id
        
        # Get host dict for AI service
        from backend_core.src.controllers.controller_manager import get_host
        host = get_host()
        
        # Get position using AI service
        ai_executor = AIPlanExecutor(host=host, device_id=device_id, team_id=get_team_id())
        result = ai_executor.get_device_position()
        
        print(f"[@route:host_ai:ai_get_device_position] Position result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_ai:ai_get_device_position] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get device position: {str(e)}'
        }), 500

@host_ai_bp.route('/updateDevicePosition', methods=['POST'])
def ai_update_device_position():
    """Update device position using device's AIExecutor"""
    try:
        print("[@route:host_ai:ai_update_device_position] Updating device position")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        node_id = data.get('node_id', '')
        node_label = data.get('node_label')
        
        print(f"[@route:host_ai:ai_update_device_position] Updating position for device: {device_id} to node: {node_id}")
        
        # Validate
        if not node_id:
            return jsonify({
                'success': False,
                'error': 'Node ID is required'
            }), 400
        
        # Get device from app registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        # Create AI service for this device
        from backend_core.src.services.ai.ai_plan_executor import AIPlanExecutor
        from shared.lib.utils.app_utils import get_team_id
        
        # Get host dict for AI service
        from backend_core.src.controllers.controller_manager import get_host
        host = get_host()
        
        # Update position using AI service
        ai_executor = AIPlanExecutor(host=host, device_id=device_id, team_id=get_team_id())
        result = ai_executor.update_device_position(node_id, node_label)
        
        print(f"[@route:host_ai:ai_update_device_position] Position update result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_ai:ai_update_device_position] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to update device position: {str(e)}'
        }), 500

@host_ai_bp.route('/status/<execution_id>', methods=['GET'])
def ai_get_execution_status(execution_id):
    """Get execution status using AIPlanExecutor"""
    try:
        print(f"[@route:host_ai:ai_get_execution_status] Getting status for execution: {execution_id}")
        
        # Get device_id from query params (required for AIPlanExecutor)
        device_id = request.args.get('device_id', 'device1')
        
        # Create AI service for status check
        from backend_core.src.services.ai.ai_plan_executor import AIPlanExecutor
        from shared.lib.utils.app_utils import get_team_id
        from backend_core.src.controllers.controller_manager import get_host
        
        host = get_host()
        ai_executor = AIPlanExecutor(host=host, device_id=device_id, team_id=get_team_id())
        result = ai_executor.get_execution_status(execution_id)
        
        print(f"[@route:host_ai:ai_get_execution_status] Status result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_ai:ai_get_execution_status] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get execution status: {str(e)}'
        }), 500
