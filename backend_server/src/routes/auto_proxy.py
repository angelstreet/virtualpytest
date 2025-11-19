"""
Auto Proxy - Simple Passthrough System

Replaces 12 pure proxy route files with a single handler.
No legacy code, no backward compatibility - just clean elimination of duplication.
"""

import time
import threading
from flask import Blueprint, request, jsonify
from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params
from shared.src.lib.config.constants import CACHE_CONFIG, HTTP_CONFIG

auto_proxy_bp = Blueprint('auto_proxy', __name__)

# ============================================================================
# IN-MEMORY CACHE FOR STREAM URLs
# ============================================================================
_stream_url_cache = {}  # {cache_key: {'data': {...}, 'timestamp': time.time()}}
_cache_lock = threading.Lock()

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
    
    EXCLUDED from auto-proxy (handled by dedicated blueprints):
    - /server/executable/* (handled by server_executable_bp - no host_name needed for listing)
    - /server/mcp/* (handled by mcp_bp - registered BEFORE auto_proxy, takes precedence)
    """
    try:
        # Explicit exclusions for endpoints that don't need host proxying
        # Note: mcp/ is handled by blueprint precedence, not explicit exclusion
        if endpoint.startswith('executable/') or endpoint.startswith('settings/'):
            return jsonify({
                'success': False,
                'error': f'Endpoint /server/{endpoint} is handled by a dedicated blueprint, not auto-proxy'
            }), 404
        
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
                        if age < CACHE_CONFIG['LONG_TTL']:
                            print(f"[@cache] HIT: Stream URL for {host_name}/{device_id} (age: {age/3600:.1f}h)")
                            return jsonify(cached['data'])
                        else:
                            del _stream_url_cache[cache_key]
        
        # Determine timeout based on endpoint type
        if '/navigation/execute' in endpoint or '/navigation/batch-execute' in endpoint or 'action/executeBatch' in endpoint or 'verification/executeBatch' in endpoint:
            timeout = HTTP_CONFIG['NAVIGATION_TIMEOUT']
            print(f"[@auto_proxy] 🕐 TIMEOUT SET: {timeout}s for endpoint: {endpoint} (reason: navigation/action/verification execution)")
        elif '/av/getStreamUrl' in endpoint:
            timeout = HTTP_CONFIG['VERY_SHORT_TIMEOUT']
            print(f"[@auto_proxy] 🕐 TIMEOUT SET: {timeout}s for endpoint: {endpoint} (reason: very short timeout)")
        else:
            timeout = HTTP_CONFIG['DEFAULT_TIMEOUT']
            print(f"[@auto_proxy] 🕐 TIMEOUT SET: {timeout}s for endpoint: {endpoint} (reason: default timeout)")
        
        print(f"[@auto_proxy] 📡 Proxying {target_method} /server/{endpoint} -> {host_endpoint} with timeout={timeout}s")
        
        # DEBUG: Check API key before proxying
        import os
        api_key_check = os.getenv('API_KEY')
        print(f"[@auto_proxy] 🔑 DEBUG: API_KEY available: {('YES (len=' + str(len(api_key_check)) + ')') if api_key_check else 'NO - WILL FAIL!'}")
        
        # Proxy to host
        response_data, status_code = proxy_to_host_with_params(
            host_endpoint, target_method, data, query_params, timeout=timeout
        )
        
        # Invalidate navigation tree cache for AI exploration operations
        if status_code == 200 and response_data.get('success'):
            # These AI exploration operations modify the navigation tree
            cache_invalidation_endpoints = [
                'ai-generation/continue-exploration',
                'ai-generation/finalize-structure',
                'ai-generation/cleanup-temp'
            ]
            
            if any(endpoint.endswith(ep) for ep in cache_invalidation_endpoints):
                tree_id = data.get('tree_id') if data else None
                if tree_id:
                    from backend_server.src.routes.server_navigation_trees_routes import invalidate_cached_tree
                    invalidate_cached_tree(tree_id, team_id)
                    print(f"[@auto_proxy] 🔄 Cache invalidated for tree {tree_id} after {endpoint}")
        
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