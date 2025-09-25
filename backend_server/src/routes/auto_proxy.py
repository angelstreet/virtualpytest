"""
Auto Proxy - Simple Passthrough System

Replaces 12 pure proxy route files with a single handler.
No legacy code, no backward compatibility - just clean elimination of duplication.
"""

from flask import Blueprint, request, jsonify
from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params

auto_proxy_bp = Blueprint('auto_proxy', __name__)

@auto_proxy_bp.route('/server/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def auto_proxy(endpoint):
    """
    Auto proxy handler - routes /server/* to /host/* for pure passthrough routes
    
    Examples:
    - /server/ai-execution/executeTask -> /host/ai-execution/executeTask
    - /server/actions/executeBatch -> /host/actions/executeBatch
    - /server/av/getStreamUrl -> /host/av/getStreamUrl (POST->GET conversion)
    - /server/verification/image/execute -> /host/verification/image/execute
    - /server/verification/text/execute -> /host/verification/text/execute
    """
    try:
        # Simple passthrough with method conversion for specific endpoints
        data = request.get_json() if request.method in ['POST', 'PUT'] else None
        host_endpoint = f'/host/{endpoint}'
        
        # Extract standard parameters
        query_params = {}
        team_id = request.args.get('team_id')
        if team_id:
            query_params['team_id'] = team_id
            # For POST requests, also include team_id in request body
            if request.method == 'POST' and data is not None:
                data['team_id'] = team_id
        
        # For GET requests, pass all query parameters
        if request.method == 'GET':
            query_params.update(request.args.to_dict())
        elif data and 'device_id' in data:
            query_params['device_id'] = data['device_id']
        
        # Handle method conversion for specific endpoints that need it
        target_method = request.method
        if endpoint in ['av/getStreamUrl', 'av/getStatus']:
            # These endpoints accept POST from frontend but host expects GET
            target_method = 'GET'
            # For POST requests, extract device_id from body to query params
            if request.method == 'POST' and data.get('device_id'):
                query_params['device_id'] = data.get('device_id')
        
        # Proxy to host
        response_data, status_code = proxy_to_host_with_params(
            host_endpoint, target_method, data, query_params, timeout=60
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Auto proxy error: {str(e)}'
        }), 500