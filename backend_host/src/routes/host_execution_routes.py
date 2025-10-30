"""
Unified Execution Routes
All execution types go through ExecutionOrchestrator for consistent logging and cross-cutting concerns
"""

from flask import Blueprint, request, jsonify, current_app
from backend_host.src.orchestrator import ExecutionOrchestrator

# Create blueprint
host_execution_bp = Blueprint('host_execution', __name__, url_prefix='/execute')


@host_execution_bp.route('/navigation', methods=['POST'])
def execute_navigation():
    """Execute navigation through orchestrator"""
    try:
        print("[@route:execute_navigation] Starting navigation execution")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        tree_id = data.get('tree_id')
        userinterface_name = data.get('userinterface_name')
        target_node_id = data.get('target_node_id')
        target_node_label = data.get('target_node_label')
        navigation_path = data.get('navigation_path')
        current_node_id = data.get('current_node_id')
        frontend_sent_position = data.get('frontend_sent_position', False)
        image_source_url = data.get('image_source_url')
        team_id = request.args.get('team_id')
        
        print(f"[@route:execute_navigation] device: {device_id}, tree: {tree_id}, target: {target_node_label or target_node_id}")
        
        # Validate required fields
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
        if not tree_id:
            return jsonify({'success': False, 'error': 'tree_id is required'}), 400
        if not userinterface_name:
            return jsonify({'success': False, 'error': 'userinterface_name is required'}), 400
        if not target_node_id and not target_node_label:
            return jsonify({'success': False, 'error': 'target_node_id or target_node_label is required'}), 400
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get device from registry
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = host_devices[device_id]
        
        # Execute navigation through orchestrator
        result = ExecutionOrchestrator.execute_navigation(
            device=device,
            tree_id=tree_id,
            userinterface_name=userinterface_name,
            target_node_id=target_node_id,
            target_node_label=target_node_label,
            navigation_path=navigation_path,
            current_node_id=current_node_id,
            frontend_sent_position=frontend_sent_position,
            image_source_url=image_source_url,
            team_id=team_id
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[@route:execute_navigation] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_execution_bp.route('/actions', methods=['POST'])
def execute_actions():
    """Execute actions through orchestrator"""
    try:
        print("[@route:execute_actions] Starting action execution")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        actions = data.get('actions', [])
        retry_actions = data.get('retry_actions', [])
        failure_actions = data.get('failure_actions', [])
        team_id = request.args.get('team_id')
        
        print(f"[@route:execute_actions] device: {device_id}, actions: {len(actions)}")
        
        # Validate required fields
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
        if not actions:
            return jsonify({'success': False, 'error': 'actions are required'}), 400
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get device from registry
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = host_devices[device_id]
        
        # Execute actions through orchestrator
        result = ExecutionOrchestrator.execute_actions(
            device=device,
            actions=actions,
            retry_actions=retry_actions,
            failure_actions=failure_actions,
            team_id=team_id
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[@route:execute_actions] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_execution_bp.route('/verifications', methods=['POST'])
def execute_verifications():
    """Execute verifications through orchestrator"""
    try:
        print("[@route:execute_verifications] Starting verification execution")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        verifications = data.get('verifications', [])
        userinterface_name = data.get('userinterface_name')
        image_source_url = data.get('image_source_url')
        team_id = request.args.get('team_id')
        tree_id = data.get('tree_id')
        node_id = data.get('node_id')
        verification_pass_condition = data.get('verification_pass_condition', 'all')
        
        print(f"[@route:execute_verifications] device: {device_id}, verifications: {len(verifications)}")
        
        # Validate required fields
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
        if not verifications:
            return jsonify({'success': False, 'error': 'verifications are required'}), 400
        if not userinterface_name:
            return jsonify({'success': False, 'error': 'userinterface_name is required'}), 400
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get device from registry
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = host_devices[device_id]
        
        # Execute verifications through orchestrator
        result = ExecutionOrchestrator.execute_verifications(
            device=device,
            verifications=verifications,
            userinterface_name=userinterface_name,
            image_source_url=image_source_url,
            team_id=team_id,
            tree_id=tree_id,
            node_id=node_id,
            verification_pass_condition=verification_pass_condition
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[@route:execute_verifications] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_execution_bp.route('/blocks', methods=['POST'])
def execute_blocks():
    """Execute standard blocks through orchestrator"""
    try:
        print("[@route:execute_blocks] Starting block execution")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        blocks = data.get('blocks', [])
        
        print(f"[@route:execute_blocks] device: {device_id}, blocks: {len(blocks)}")
        
        # Validate required fields
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
        if not blocks:
            return jsonify({'success': False, 'error': 'blocks are required'}), 400
        
        # Get device from registry
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = host_devices[device_id]
        
        # Execute blocks through orchestrator
        result = ExecutionOrchestrator.execute_blocks(
            device=device,
            blocks=blocks
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[@route:execute_blocks] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

