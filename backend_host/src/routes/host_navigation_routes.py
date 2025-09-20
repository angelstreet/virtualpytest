"""
Host Navigation Routes - Device Navigation Execution

This module receives navigation execution requests from the server and routes them
to the appropriate device's NavigationExecutor.
"""

from flask import Blueprint, request, jsonify, current_app
from lib.utils.app_utils import get_team_id

# Create blueprint
host_navigation_bp = Blueprint('host_navigation', __name__, url_prefix='/host/navigation')

@host_navigation_bp.route('/execute/<tree_id>/<target_node_id>', methods=['POST'])
def navigation_execute(tree_id, target_node_id):
    """Execute navigation using device's NavigationExecutor"""
    try:
        print(f"[@route:host_navigation:navigation_execute] Starting navigation to {target_node_id}")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        current_node_id = data.get('current_node_id')
        image_source_url = data.get('image_source_url')
        
        print(f"[@route:host_navigation:navigation_execute] Device: {device_id}, Tree: {tree_id}")
        
        # Validate
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
        
        # Check if device has navigation_executor
        if not hasattr(device, 'navigation_executor') or not device.navigation_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have NavigationExecutor initialized'
            }), 500
        
        # Execute navigation using device's NavigationExecutor
        from lib.utils.app_utils import get_team_id
        result = device.navigation_executor.execute_navigation(
            tree_id=tree_id,
            target_node_id=target_node_id,
            current_node_id=current_node_id,
            image_source_url=image_source_url,
            team_id=get_team_id()
        )
        
        print(f"[@route:host_navigation:navigation_execute] Execution completed: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_navigation:navigation_execute] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host navigation execution failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/preview/<tree_id>/<target_node_id>', methods=['GET'])
def navigation_preview(tree_id, target_node_id):
    """Get navigation preview using device's NavigationExecutor"""
    try:
        print(f"[@route:host_navigation:navigation_preview] Getting preview for {target_node_id}")
        
        # Get query parameters
        device_id = request.args.get('device_id', 'device1')
        current_node_id = request.args.get('current_node_id')
        
        print(f"[@route:host_navigation:navigation_preview] Device: {device_id}, Tree: {tree_id}")
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False, 
                'error': f'Device {device_id} not found in host'
            }), 404
        
        device = host_devices[device_id]
        
        # Check if device has navigation_executor
        if not hasattr(device, 'navigation_executor') or not device.navigation_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have NavigationExecutor initialized'
            }), 500
        
        # Get navigation preview using device's NavigationExecutor
        result = device.navigation_executor.get_navigation_preview(
            tree_id=tree_id,
            target_node_id=target_node_id,
            current_node_id=current_node_id
        )
        
        print(f"[@route:host_navigation:navigation_preview] Preview completed: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_navigation:navigation_preview] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host navigation preview failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for host navigation service"""
    return jsonify({
        'success': True,
        'message': 'Host navigation service is running'
    })
