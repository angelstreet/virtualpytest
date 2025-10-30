"""
Server Builder Routes - Proxy for Standard Block Execution

Proxies standard block execution requests to host.
"""

from flask import Blueprint, request, jsonify
from backend_server.src.lib.utils.route_utils import proxy_to_host_with_params

# Create blueprint
server_builder_bp = Blueprint('server_builder', __name__, url_prefix='/server/builder')


@server_builder_bp.route('/execute', methods=['POST'])
def execute_standard_block():
    """
    Execute a standard block (sleep, loop, set_variable, etc.)
    
    Proxies to /host/builder/execute
    
    Request body:
        {
            "command": "sleep",
            "params": {"duration": 2.0},
            "host_name": "pi1",
            "device_id": "device1"
        }
    """
    try:
        print("[@route:server_builder:execute] Starting standard block execution")
        
        # Get request data
        data = request.get_json() or {}
        command = data.get('command')
        params = data.get('params', {})
        host_name = data.get('host_name')
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        
        print(f"[@route:server_builder:execute] Executing block: {command}")
        print(f"[@route:server_builder:execute] Host: {host_name}, Device: {device_id}")
        
        # Validate
        if not command:
            return jsonify({'success': False, 'error': 'command is required'}), 400
        
        if not host_name:
            return jsonify({'success': False, 'error': 'host_name is required'}), 400
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Prepare execution payload
        execution_payload = {
            'command': command,
            'params': params,
            'device_id': device_id
        }
        
        # Query params
        query_params = {'team_id': team_id}
        if device_id:
            query_params['device_id'] = device_id
        
        print(f"[@route:server_builder:execute] Proxying to host...")
        
        # Proxy to host with parameters
        response_data, status_code = proxy_to_host_with_params(
            '/host/builder/execute',
            'POST',
            execution_payload,
            query_params,
            timeout=60  # Standard blocks might take time (e.g., sleep)
        )
        
        if response_data.get('success'):
            print(f"[@route:server_builder:execute] Block execution completed successfully")
        else:
            print(f"[@route:server_builder:execute] Block execution failed: {response_data.get('error', 'Unknown error')}")
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_builder:execute] Error: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'Server error during block execution: {str(e)}'
        }), 500

