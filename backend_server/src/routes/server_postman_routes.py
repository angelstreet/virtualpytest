from flask import Blueprint, jsonify, request
import os
import json
import requests
import time
import threading
from pathlib import Path
from shared.src.lib.config.constants import CACHE_CONFIG

server_postman_bp = Blueprint('server_postman_bp', __name__, url_prefix='/server/postman')

# Path to config file
BACKEND_SERVER_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = BACKEND_SERVER_ROOT / 'config' / 'postman' / 'postman_config.json'

# ============================================================================
# IN-MEMORY CACHE FOR POSTMAN COLLECTIONS
# ============================================================================
_postman_cache = {}  # {cache_key: {'data': {...}, 'timestamp': time.time()}}
_cache_lock = threading.Lock()

def load_config():
    """Load Postman configuration (workspaces + environments)"""
    try:
        if not CONFIG_PATH.exists():
            print(f"[@postman_routes] Config file not found: {CONFIG_PATH}")
            return {'workspaces': [], 'environments': []}
        
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        print(f"[@postman_routes] Loaded config: {len(config.get('workspaces', []))} workspace(s), {len(config.get('environments', []))} environment(s)")
        return config
    except Exception as e:
        print(f"[@postman_routes] Error loading config: {e}")
        return {'workspaces': [], 'environments': []}

def load_workspaces_config():
    """Get workspaces from config"""
    config = load_config()
    return config.get('workspaces', [])

def get_workspace_by_id(workspace_id):
    """Get workspace config by ID"""
    workspaces = load_workspaces_config()
    for workspace in workspaces:
        if workspace['id'] == workspace_id:
            return workspace
    return None

def get_environments_by_workspace(workspace_id):
    """Get all environments for a workspace"""
    config = load_config()
    environments = config.get('environments', [])
    return [env for env in environments if env.get('workspaceId') == workspace_id]

def normalize_environment_variables(variables):
    """Convert environment variables from array format to dict format
    
    Supports two formats:
    1. Array format (Postman standard): [{"key": "x", "value": "y", "type": "secret"}, ...]
    2. Object format (simple): {"x": "y", ...}
    
    Returns: dict format {"x": "y", ...}
    """
    if isinstance(variables, list):
        # Convert array to dict, extracting just key-value pairs
        return {var['key']: var['value'] for var in variables if 'key' in var}
    elif isinstance(variables, dict):
        # Already in dict format
        return variables
    return {}

def get_environment_by_id(environment_id):
    """Get environment by ID"""
    config = load_config()
    environments = config.get('environments', [])
    for env in environments:
        if env['id'] == environment_id:
            return env
    return None

def substitute_variables(text, variables):
    """Replace {{variable}} placeholders with values from environment variables"""
    if not text or not variables:
        return text
    
    import re
    def replacer(match):
        var_name = match.group(1)
        value = variables.get(var_name)
        return str(value) if value is not None else match.group(0)
    
    # Replace {{variable}} with value
    result = re.sub(r'\{\{(\w+)\}\}', replacer, str(text))
    return result

def call_postman_api(endpoint, api_key):
    """Call Postman API (security layer - API keys never exposed to frontend)"""
    try:
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        url = f"https://api.getpostman.com{endpoint}"
        
        print(f"[@postman_routes] Calling Postman API: {endpoint}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[@postman_routes] Postman API error: {e}")
        raise


@server_postman_bp.route('/workspaces', methods=['GET'])
def get_user_workspaces():
    """Get list of configured user workspaces"""
    try:
        workspaces = load_workspaces_config()
        
        # Return sanitized data (no API keys!)
        result = []
        for ws in workspaces:
            result.append({
                'id': ws['id'],
                'name': ws['name'],
                'description': ws.get('description', ''),
                'workspaceId': ws.get('workspaceId', ''),
            })
        
        return jsonify({
            'success': True,
            'workspaces': result
        })
    except Exception as e:
        print(f"[@postman_routes:get_user_workspaces] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_postman_bp.route('/environments', methods=['GET'])
def get_config_environments():
    """Get environments for a workspace from config file"""
    try:
        workspace_id = request.args.get('workspaceId')
        if not workspace_id:
            return jsonify({
                'success': False,
                'error': 'workspaceId parameter required'
            }), 400
        
        environments = get_environments_by_workspace(workspace_id)
        
        # Return sanitized data (variable values are safe to expose for testing)
        result = []
        for env in environments:
            result.append({
                'id': env['id'],
                'name': env['name'],
                'workspaceId': env.get('workspaceId'),
                'variables': env.get('variables', {})
            })
        
        return jsonify({
            'success': True,
            'environments': result
        })
    except Exception as e:
        print(f"[@postman_routes:get_workspace_environments] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_postman_bp.route('/workspaces/<workspace_id>/collections', methods=['GET'])
def get_workspace_collections(workspace_id):
    """Get collections for a workspace using Postman API (with 5-minute cache)"""
    try:
        # Check cache first
        cache_key = f"collections:{workspace_id}"
        with _cache_lock:
            if cache_key in _postman_cache:
                cached = _postman_cache[cache_key]
                age = time.time() - cached['timestamp']
                if age < CACHE_CONFIG['MEDIUM_TTL']:
                    print(f"[@cache] HIT: Postman collections for {workspace_id} (age: {age:.1f}s)")
                    return jsonify(cached['data'])
                else:
                    del _postman_cache[cache_key]
                    print(f"[@cache] EXPIRED: Postman collections for {workspace_id} (age: {age:.1f}s)")
        
        workspace = get_workspace_by_id(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Call Postman API (backend handles API key - secure!)
        api_key = workspace['postmanApiKey']
        postman_workspace_id = workspace['workspaceId']
        
        print(f"[@postman_routes] Fetching collections from Postman API for workspace {workspace_id}...")
        
        # Get collections in workspace
        data = call_postman_api(f"/collections?workspace={postman_workspace_id}", api_key)
        
        collections = data.get('collections', [])
        
        # Enhance with request counts (fetch each collection details)
        enhanced_collections = []
        for collection in collections:
            collection_id = collection['uid']
            
            # Get collection details to count requests
            try:
                collection_data = call_postman_api(f"/collections/{collection_id}", api_key)
                collection_detail = collection_data.get('collection', {})
                
                # Count requests recursively
                request_count = count_requests_in_items(collection_detail.get('item', []))
                
                enhanced_collections.append({
                    'id': collection['uid'],
                    'name': collection['name'],
                    'description': collection_detail.get('info', {}).get('description', ''),
                    'requestCount': request_count
                })
            except Exception as e:
                print(f"[@postman_routes] Error fetching collection {collection_id}: {e}")
                # Add basic info even if detailed fetch fails
                enhanced_collections.append({
                    'id': collection['uid'],
                    'name': collection['name'],
                    'description': '',
                    'requestCount': 0
                })
        
        response_data = {
            'success': True,
            'collections': enhanced_collections
        }
        
        # Store in cache
        with _cache_lock:
            _postman_cache[cache_key] = {
                'data': response_data,
                'timestamp': time.time()
            }
            print(f"[@cache] SET: Postman collections for {workspace_id} (TTL: {CACHE_CONFIG['MEDIUM_TTL']}s)")
        
        return jsonify(response_data)
    except Exception as e:
        print(f"[@postman_routes:get_workspace_collections] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_postman_bp.route('/workspaces/<workspace_id>/environments', methods=['GET'])
def get_workspace_environments(workspace_id):
    """Get environments for a workspace using Postman API (with 5-minute cache)"""
    try:
        # Check cache first
        cache_key = f"environments:{workspace_id}"
        with _cache_lock:
            if cache_key in _postman_cache:
                cached = _postman_cache[cache_key]
                age = time.time() - cached['timestamp']
                if age < CACHE_CONFIG['MEDIUM_TTL']:
                    print(f"[@cache] HIT: Postman environments for {workspace_id} (age: {age:.1f}s)")
                    return jsonify(cached['data'])
                else:
                    del _postman_cache[cache_key]
                    print(f"[@cache] EXPIRED: Postman environments for {workspace_id} (age: {age:.1f}s)")
        
        workspace = get_workspace_by_id(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        print(f"[@postman_routes] Fetching environments from Postman API for workspace {workspace_id}...")
        
        # Call Postman API
        api_key = workspace['postmanApiKey']
        postman_workspace_id = workspace['workspaceId']
        
        # Get environments in workspace
        data = call_postman_api(f"/environments?workspace={postman_workspace_id}", api_key)
        
        environments = data.get('environments', [])
        
        # Format environments
        formatted_environments = []
        for env in environments:
            formatted_environments.append({
                'id': env['uid'],
                'name': env['name'],
            })
        
        response_data = {
            'success': True,
            'environments': formatted_environments
        }
        
        # Store in cache
        with _cache_lock:
            _postman_cache[cache_key] = {
                'data': response_data,
                'timestamp': time.time()
            }
            print(f"[@cache] SET: Postman environments for {workspace_id} (TTL: {CACHE_CONFIG['MEDIUM_TTL']}s)")
        
        return jsonify(response_data)
    except Exception as e:
        print(f"[@postman_routes:get_workspace_environments] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_postman_bp.route('/environments/<environment_id>', methods=['GET'])
def get_environment_details(environment_id):
    """Get environment variables"""
    try:
        # Extract workspace_id from query params
        workspace_id = request.args.get('workspace_id')
        if not workspace_id:
            return jsonify({
                'success': False,
                'error': 'workspace_id query parameter required'
            }), 400
        
        workspace = get_workspace_by_id(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        # Call Postman API
        api_key = workspace['postmanApiKey']
        data = call_postman_api(f"/environments/{environment_id}", api_key)
        
        environment = data.get('environment', {})
        
        # Extract variables
        variables = {}
        for var in environment.get('values', []):
            if var.get('enabled', True):
                variables[var['key']] = var['value']
        
        return jsonify({
            'success': True,
            'environment': {
                'id': environment.get('id'),
                'name': environment.get('name'),
                'variables': variables
            }
        })
    except Exception as e:
        print(f"[@postman_routes:get_environment_details] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_postman_bp.route('/collections/<collection_id>/requests', methods=['GET'])
def get_collection_requests(collection_id):
    """Get all requests/endpoints from a collection (with 5-minute cache)"""
    try:
        # Extract workspace_id from query params
        workspace_id = request.args.get('workspace_id')
        if not workspace_id:
            return jsonify({
                'success': False,
                'error': 'workspace_id query parameter required'
            }), 400
        
        # Check cache first
        cache_key = f"requests:{collection_id}"
        with _cache_lock:
            if cache_key in _postman_cache:
                cached = _postman_cache[cache_key]
                age = time.time() - cached['timestamp']
                if age < CACHE_CONFIG['MEDIUM_TTL']:
                    print(f"[@cache] HIT: Postman requests for collection {collection_id} (age: {age:.1f}s)")
                    return jsonify(cached['data'])
                else:
                    del _postman_cache[cache_key]
                    print(f"[@cache] EXPIRED: Postman requests for collection {collection_id} (age: {age:.1f}s)")
        
        workspace = get_workspace_by_id(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        print(f"[@postman_routes] Fetching requests from Postman API for collection {collection_id}...")
        
        # Call Postman API
        api_key = workspace['postmanApiKey']
        data = call_postman_api(f"/collections/{collection_id}", api_key)
        
        collection = data.get('collection', {})
        
        # Extract all requests recursively
        requests_list = []
        extract_requests_from_items(collection.get('item', []), requests_list)
        
        response_data = {
            'success': True,
            'requests': requests_list
        }
        
        # Store in cache
        with _cache_lock:
            _postman_cache[cache_key] = {
                'data': response_data,
                'timestamp': time.time()
            }
            print(f"[@cache] SET: Postman requests for collection {collection_id} (TTL: {CACHE_CONFIG['MEDIUM_TTL']}s)")
        
        return jsonify(response_data)
    except Exception as e:
        print(f"[@postman_routes:get_collection_requests] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@server_postman_bp.route('/test', methods=['POST'])
def run_api_test():
    """Run API test immediately for selected endpoints with environment variable substitution"""
    try:
        from shared.src.lib.utils.build_url_utils import buildServerUrl
        
        data = request.json
        workspace_id = data.get('workspaceId')
        workspace_name = data.get('workspaceName')
        environment_id = data.get('environmentId')  # NEW: Environment ID for variable substitution
        endpoints = data.get('endpoints', [])
        
        # Load environment variables if specified
        env_variables = {}
        if environment_id:
            environment = get_environment_by_id(environment_id)
            if environment:
                raw_variables = environment.get('variables', {})
                # Normalize to dict format (supports both array and object formats)
                env_variables = normalize_environment_variables(raw_variables)
                print(f"[@postman_routes] Using environment '{environment.get('name')}' with {len(env_variables)} variables: {list(env_variables.keys())}")
            else:
                print(f"[@postman_routes] Warning: Environment '{environment_id}' not found")
        else:
            print(f"[@postman_routes] No environment selected, requests will use raw paths")
        
        if not endpoints:
            return jsonify({
                'success': False,
                'error': 'No endpoints provided'
            }), 400
        
        workspace = get_workspace_by_id(workspace_id)
        if not workspace:
            return jsonify({
                'success': False,
                'error': 'Workspace not found'
            }), 404
        
        print(f"[@postman_routes:run_api_test] Testing {len(endpoints)} endpoints")
        
        # Execute tests using requests
        results = []
        success_count = 0
        
        for ep in endpoints:
            method = ep.get('method', 'GET')
            path = ep.get('path', '')
            name = ep.get('name', path)
            body = ep.get('body', {})  # Get request body from endpoint definition
            
            # ==================================================================
            # STEP 1: Variable Substitution (like real Postman!)
            # ==================================================================
            # Substitute {{variables}} in path, params, and body
            path = substitute_variables(path, env_variables)
            
            # If path contains full URL (e.g., {{base_url}}/server/devices), extract it
            if path.startswith('http://') or path.startswith('https://'):
                url = path
                print(f"[@postman_routes] Using full URL from path: {url}")
            else:
                # Path is relative, need base_url from environment or fallback
                base_url = env_variables.get('base_url')
                if not base_url:
                    # Fallback to buildServerUrl
                    base_url = buildServerUrl('')
                    print(f"[@postman_routes] No {{base_url}} in environment, using buildServerUrl: {base_url}")
                
                # Ensure path starts with /
                if not path.startswith('/'):
                    path = '/' + path
                
                url = f"{base_url.rstrip('/')}{path}"
                print(f"[@postman_routes] Constructed URL: {url}")
            
            start_time = time.time()
            result_entry = {
                'name': name,
                'method': method,
                'path': path,
                'status': 'pending'
            }
            
            try:
                print(f"[@postman_routes] Executing {method} {url}")
                
                # ==================================================================
                # STEP 2: Build Request (params, body, headers) with variables
                # ==================================================================
                params = {}
                json_data = None
                headers = {}
                
                # Add API key from environment if available
                api_key = env_variables.get('api_key')
                if api_key:
                    headers['Authorization'] = f'Bearer {api_key}'
                    print(f"[@postman_routes] Using api_key from environment")
                
                # Add query parameters from environment variables
                # Common variables: team_id, host_name, device_id, userinterface, etc.
                if 'team_id' in env_variables:
                    params['team_id'] = env_variables['team_id']
                
                if 'host_name' in env_variables:
                    params['host_name'] = env_variables['host_name']
                
                if 'device_id' in env_variables:
                    params['device_id'] = env_variables['device_id']
                
                if 'userinterface' in env_variables:
                    # Map to userinterface_name for host routes
                    params['userinterface_name'] = env_variables['userinterface']
                
                # For /host/* endpoints, add context to request body (server will proxy)
                if path.startswith('/host/'):
                    json_data = {}
                    if 'host_name' in env_variables:
                        json_data['host_name'] = env_variables['host_name']
                    if 'device_id' in env_variables:
                        json_data['device_id'] = env_variables['device_id']
                    if 'userinterface' in env_variables:
                        json_data['userinterface'] = env_variables['userinterface']
                    print(f"[@postman_routes] Adding environment vars to request body: {json_data}")
                
                # Execute request
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                    timeout=10
                )
                
                duration = (time.time() - start_time) * 1000
                result_entry['statusCode'] = response.status_code
                result_entry['duration'] = round(duration, 2)
                result_entry['status'] = 'pass' if response.ok else 'fail'
                
                # Try to parse response body if JSON
                try:
                    result_entry['response'] = response.json()
                except:
                    result_entry['response'] = response.text[:500]  # Truncate text
                
                if response.ok:
                    success_count += 1
                    
            except Exception as e:
                print(f"[@postman_routes] Error executing {name}: {e}")
                result_entry['status'] = 'error'
                result_entry['error'] = str(e)
                result_entry['statusCode'] = 0
            
            results.append(result_entry)
        
        return jsonify({
            'success': True,
            'message': f'Completed {len(endpoints)} tests',
            'results': results,
            'passed': success_count,
            'total': len(endpoints)
        })
    except Exception as e:
        print(f"[@postman_routes:run_api_test] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Helper functions

def count_requests_in_items(items):
    """Recursively count requests in collection items"""
    count = 0
    for item in items:
        if 'request' in item:
            count += 1
        if 'item' in item:  # Folder with nested items
            count += count_requests_in_items(item['item'])
    return count


def extract_requests_from_items(items, requests_list, folder_path=""):
    """Recursively extract all requests from collection items"""
    for item in items:
        if 'request' in item:
            # It's a request
            req = item['request']
            
            # Extract URL
            url = req.get('url', {})
            if isinstance(url, str):
                path = url
            else:
                path = url.get('raw', '')
                # Try to extract just the path
                if 'path' in url:
                    path = '/' + '/'.join(url['path'])
            
            # Extract method
            method = req.get('method', 'GET')
            
            # Build full path with folder
            full_name = f"{folder_path}/{item['name']}" if folder_path else item['name']
            
            # Use uid as primary ID, fallback to id, then name (hashed) as last resort
            # This ensures we have a unique ID for the frontend
            item_id = item.get('uid') or item.get('id') or item.get('_postman_id')
            if not item_id:
                # Fallback for items without explicit ID
                import hashlib
                item_id = hashlib.md5(f"{full_name}:{method}:{path}".encode()).hexdigest()

            requests_list.append({
                'id': item_id,
                'name': item['name'],
                'fullName': full_name,
                'method': method,
                'path': path,
                'description': item.get('request', {}).get('description', '')
            })
        
        if 'item' in item:
            # It's a folder - recurse
            folder_name = item['name']
            new_path = f"{folder_path}/{folder_name}" if folder_path else folder_name
            extract_requests_from_items(item['item'], requests_list, new_path)

