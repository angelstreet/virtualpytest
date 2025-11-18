"""
Host AI Routes - Device AI Execution

This module receives AI execution requests from the server and routes them
to the appropriate device's AIExecutor.
"""

from flask import Blueprint, request, jsonify, current_app

# Create blueprint
host_ai_bp = Blueprint('host_ai', __name__, url_prefix='/host/ai')

@host_ai_bp.route('/generatePlan', methods=['POST'])
def ai_generate_plan():
    """Generate AI graph using device's AIGraphBuilder"""
    try:
        print("[@host_ai] Starting AI graph generation")
        
        # Get request data
        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        device_id = data.get('device_id', 'device1')
        userinterface_name = data.get('userinterface_name', 'horizon_android_mobile')
        current_node_id = data.get('current_node_id')
        available_nodes = data.get('available_nodes')  # NEW: Accept from caller
        team_id = request.args.get('team_id')
        
        print(f"[@host_ai] Generating graph for device: {device_id}, team: {team_id}")
        print(f"[@host_ai] Prompt: {prompt[:100]}...")
        
        # Validate
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt is required'
            }), 400
        
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        # Get device from app registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        print(f"[@host_ai] Using AI service for device: {device_id}")
        
        # Check if device has ai_builder
        if not hasattr(device, 'ai_builder') or not device.ai_builder:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AIGraphBuilder initialized'
            }), 500
        
        # Generate graph using AIGraphBuilder
        result = device.ai_builder.generate_graph(
            prompt=prompt,
            userinterface_name=userinterface_name,
            team_id=team_id,
            current_node_id=current_node_id,
            available_nodes=available_nodes  # NEW: Pass to AI builder
        )
        
        print(f"[@host_ai] Graph generation result: success={result.get('success')}")
        print(f"[@host_ai] Result keys: {list(result.keys())}")
        print(f"[@host_ai] needs_disambiguation: {result.get('needs_disambiguation')}")
        
        if result.get('needs_disambiguation'):
            print(f"[@host_ai] ⚠️  DISAMBIGUATION - ambiguities count: {len(result.get('ambiguities', []))}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@host_ai] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'AI graph generation failed: {str(e)}'
        }), 500

@host_ai_bp.route('/executePlan', methods=['POST'])
def ai_execute_plan():
    """Execute AI plan using device's AIExecutor"""
    try:
        print("[@host_ai] Starting AI plan execution")
        
        # Get request data
        data = request.get_json() or {}
        plan_id = data.get('plan_id', '')
        plan = data.get('plan', {})
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        userinterface_name = data.get('userinterface_name', 'horizon_android_mobile')
        
        print(f"[@host_ai] Executing plan {plan_id} for device: {device_id}, team: {team_id}")
        
        # Validate
        if not plan_id or not plan:
            return jsonify({
                'success': False,
                'error': 'Plan ID and plan data are required'
            }), 400
            
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        # Get device from app registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        print(f"[@host_ai] Using AI service for device: {device_id}")
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AIExecutor initialized'
            }), 500
        
        result = device.ai_executor.execute_prompt(
            prompt=f"Execute plan: {plan.get('description', 'AI plan')}",
            userinterface_name=userinterface_name,
            async_execution=False,  # Synchronous for plan execution
            team_id=team_id
        )
        
        print(f"[@host_ai] Plan execution result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@host_ai] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI plan execution failed: {str(e)}'
        }), 500

@host_ai_bp.route('/getDevicePosition', methods=['GET'])
def ai_get_device_position():
    """Get device position using device's AIExecutor"""
    try:
        print("[@host_ai] Getting device position")
        
        # Get device_id from query params
        device_id = request.args.get('device_id', 'device1')
        
        print(f"[@host_ai] Getting position for device: {device_id}")
        
        # Get device from app registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AIExecutor initialized'
            }), 500
        
        result = device.ai_executor.get_device_position()
        
        print(f"[@host_ai] Position result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@host_ai] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get device position: {str(e)}'
        }), 500

@host_ai_bp.route('/updateDevicePosition', methods=['POST'])
def ai_update_device_position():
    """Update device position using device's AIExecutor"""
    try:
        print("[@host_ai] Updating device position")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        node_id = data.get('node_id', '')
        node_label = data.get('node_label')
        tree_id = data.get('tree_id')  # Optional tree_id
        
        print(f"[@host_ai] Updating position for device: {device_id} to node: {node_id}")
        
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
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AIExecutor initialized'
            }), 500
        
        result = device.ai_executor.update_device_position(node_id, tree_id, node_label)
        
        print(f"[@host_ai] Position update result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@host_ai] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to update device position: {str(e)}'
        }), 500

@host_ai_bp.route('/status/<execution_id>', methods=['GET'])
def ai_get_execution_status(execution_id):
    """Get execution status using AIPlanExecutor"""
    try:
        print(f"[@host_ai] Getting status for execution: {execution_id}")
        
        # Get device_id from query params (required for AIExecutor)
        device_id = request.args.get('device_id', 'device1')
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False, 
                'error': f'Device {device_id} not found in host'
            }), 404
        
        device = host_devices[device_id]
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AIExecutor initialized'
            }), 500
        
        result = device.ai_executor.get_execution_status(execution_id)
        
        print(f"[@host_ai] Status result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@host_ai] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get execution status: {str(e)}'
        }), 500

@host_ai_bp.route('/executeTestCase', methods=['POST'])
def ai_execute_test_case():
    """Execute test case using device's AIExecutor"""
    try:
        print("[@host_ai] Starting test case execution")
        
        # Get request data
        data = request.get_json() or {}
        test_case_id = data.get('test_case_id')
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        
        print(f"[@host_ai] Executing test case {test_case_id} for device: {device_id}, team: {team_id}")
        
        # Validate
        if not test_case_id:
            return jsonify({'success': False, 'error': 'test_case_id is required'}), 400
            
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
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AIExecutor initialized'
            }), 500
        
        result = device.ai_executor.execute_testcase(test_case_id, team_id=team_id)
        
        print(f"[@host_ai] Test case execution result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@host_ai] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Host AI test case execution failed: {str(e)}'
        }), 500

@host_ai_bp.route('/analyzeCompatibility', methods=['POST'])
def ai_analyze_compatibility():
    """Analyze AI compatibility"""
    try:
        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        device_id = data.get('device_id', 'device1')
        userinterface_name = data.get('userinterface_name', 'horizon_android_mobile')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({'success': False, 'error': f'Device {device_id} AIExecutor not initialized'}), 500
        
        result = device.ai_executor.analyze_compatibility(prompt, userinterface_name)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Compatibility analysis failed: {str(e)}'}), 500

@host_ai_bp.route('/analyzePrompt', methods=['POST'])
def ai_analyze_prompt_disambiguation():
    """Analyze prompt for disambiguation"""
    try:
        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        device_id = data.get('device_id', 'device1')
        userinterface_name = data.get('userinterface_name', 'horizon_android_mobile')
        team_id = request.args.get('team_id')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({'success': False, 'error': f'Device {device_id} AIExecutor not initialized'}), 500
        
        result = device.ai_executor.analyze_prompt_for_disambiguation(prompt, userinterface_name, team_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Prompt analysis failed: {str(e)}'}), 500

@host_ai_bp.route('/saveDisambiguation', methods=['POST'])
def ai_save_disambiguation():
    """Save disambiguation preferences"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({'success': False, 'error': f'Device {device_id} AIExecutor not initialized'}), 500
        
        result = device.ai_executor.save_disambiguation(data, team_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Save disambiguation failed: {str(e)}'}), 500

@host_ai_bp.route('/getStatus', methods=['POST'])
def ai_get_status():
    """Get AI execution status"""
    try:
        data = request.get_json() or {}
        execution_id = data.get('execution_id')
        device_id = data.get('device_id', 'device1')
        
        if not execution_id:
            return jsonify({'success': False, 'error': 'execution_id is required'}), 400
        
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({'success': False, 'error': f'Device {device_id} AIExecutor not initialized'}), 500
        
        result = device.ai_executor.get_execution_status(execution_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Get status failed: {str(e)}'}), 500

@host_ai_bp.route('/stopExecution', methods=['POST'])
def ai_stop_execution():
    """Stop AI execution"""
    try:
        data = request.get_json() or {}
        execution_id = data.get('execution_id')
        device_id = data.get('device_id', 'device1')
        
        if not execution_id:
            return jsonify({'success': False, 'error': 'execution_id is required'}), 400
        
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({'success': False, 'error': f'Device {device_id} AIExecutor not initialized'}), 500
        
        result = device.ai_executor.stop_execution(execution_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Stop execution failed: {str(e)}'}), 500
