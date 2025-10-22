"""
Auto Proxy - Simple Passthrough System

Replaces 12 pure proxy route files with a single handler.
No legacy code, no backward compatibility - just clean elimination of duplication.
"""

import time
import threading
from flask import Blueprint, request, jsonify
from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params

auto_proxy_bp = Blueprint('auto_proxy', __name__)

# ============================================================================
# IN-MEMORY CACHE FOR STREAM URLs
# ============================================================================
_stream_url_cache = {}  # {cache_key: {'data': {...}, 'timestamp': time.time()}}
_cache_lock = threading.Lock()
_cache_ttl = 86400  # 24 hours TTL

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
    
    Note: Blueprints registered BEFORE auto_proxy in app.py take precedence.
    Example: server_ai_execution_routes handles /resetCache specifically, auto_proxy handles /executeTask
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
        
        # Cache for getStreamUrl endpoint (24h TTL)
        if endpoint == 'av/getStreamUrl':
            host_name = data.get('host_name') if data else query_params.get('host_name')
            device_id = query_params.get('device_id')
            
            if host_name and device_id:
                cache_key = f"{host_name}:{device_id}"
                
                # Check cache first
                with _cache_lock:
                    if cache_key in _stream_url_cache:
                        cached = _stream_url_cache[cache_key]
                        age = time.time() - cached['timestamp']
                        if age < _cache_ttl:
                            print(f"[@cache] HIT: Stream URL for {host_name}/{device_id} (age: {age/3600:.1f}h)")
                            return jsonify(cached['data'])
                        else:
                            del _stream_url_cache[cache_key]
        
        # Determine timeout based on endpoint type
        if '/navigation/execute' in endpoint or '/navigation/batch-execute' in endpoint:
            timeout = 180  # 3 minutes for navigation execution
        else:
            timeout = 60  # Default timeout for other operations
        
        # Proxy to host
        response_data, status_code = proxy_to_host_with_params(
            host_endpoint, target_method, data, query_params, timeout=timeout
        )
        
        # Store in cache if successful getStreamUrl
        if endpoint == 'av/getStreamUrl' and status_code == 200 and response_data.get('success'):
            host_name = data.get('host_name') if data else query_params.get('host_name')
            device_id = query_params.get('device_id')
            
            if host_name and device_id:
                cache_key = f"{host_name}:{device_id}"
                with _cache_lock:
                    _stream_url_cache[cache_key] = {
                        'data': response_data,
                        'timestamp': time.time()
                    }
                    print(f"[@cache] SET: Stream URL for {host_name}/{device_id} (24h TTL)")
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Auto proxy error: {str(e)}'
        }), 500