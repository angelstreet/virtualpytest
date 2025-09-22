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
    - /server/av/get-stream-url -> /host/av/get-stream-url
    """
    try:
        # Simple passthrough
        data = request.get_json() or {}
        host_endpoint = f'/host/{endpoint}'
        
        # Extract standard parameters
        query_params = {}
        team_id = request.args.get('team_id')
        if team_id:
            query_params['team_id'] = team_id
        if data and 'device_id' in data:
            query_params['device_id'] = data['device_id']
        
        # Proxy to host
        response_data, status_code = proxy_to_host_with_params(
            host_endpoint, request.method, data, query_params, timeout=60
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Auto proxy error: {str(e)}'
        }), 500