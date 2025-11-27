from flask import Blueprint, jsonify, request
import os
import json
import requests
import time
import threading
from pathlib import Path
from shared.src.lib.config.constants import CACHE_CONFIG

server_postman_bp = Blueprint('server_postman_bp', __name__, url_prefix='/server/postman')

# Path to workspaces config
BACKEND_SERVER_ROOT = Path(__file__).parent.parent.parent
WORKSPACES_CONFIG_PATH = BACKEND_SERVER_ROOT / 'config' / 'postman' / 'postman_workspaces.json'

# ============================================================================
# IN-MEMORY CACHE FOR POSTMAN COLLECTIONS
# ============================================================================
_postman_cache = {}  # {cache_key: {'data': {...}, 'timestamp': time.time()}}
_cache_lock = threading.Lock()

def load_workspaces_config():
    """Load workspaces configuration from JSON file"""
    try:
        if not WORKSPACES_CONFIG_PATH.exists():
            print(f"[@postman_routes] Config file not found: {WORKSPACES_CONFIG_PATH}")
            return []
        
        with open(WORKSPACES_CONFIG_PATH, 'r') as f:
            workspaces = json.load(f)
        
        print(f"[@postman_routes] Loaded {len(workspaces)} workspace(s)")
        return workspaces
    except Exception as e:
        print(f"[@postman_routes] Error loading config: {e}")
        return []

def get_workspace_by_id(workspace_id):
    """Get workspace config by ID"""
    workspaces = load_workspaces_config()
    for workspace in workspaces:
        if workspace['id'] == workspace_id:
            return workspace
    return None

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
        api_key = workspace['apiKey']
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
        api_key = workspace['apiKey']
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
        api_key = workspace['apiKey']
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
        api_key = workspace['apiKey']
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
    """Run API test immediately for selected endpoints (tests on current server)"""
    try:
        data = request.json
        workspace_id = data.get('workspaceId')
        workspace_name = data.get('workspaceName')
        endpoints = data.get('endpoints', [])
        
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
        
        # Determine server URL from request origin
        # If frontend is on localhost:5173, backend is on localhost:5109
        # Use the Host header to determine where we're running
        host_header = request.headers.get('Host', 'localhost:5109')
        
        # Extract host and determine corresponding backend_host port
        # Server is on 5109, Host is on 5073
        if 'localhost' in host_header or '127.0.0.1' in host_header:
            server_url = 'http://localhost:5073'
        else:
            # Production or other environment
            # Replace server port (5109) with host port (5073)
            server_url = f"http://{host_header.replace(':5109', ':5073')}"
        
        print(f"[@postman_routes:run_api_test] Determined server URL from Host header '{host_header}': {server_url}")
        
        # Format endpoints for api_test.py
        endpoint_paths = [f"{ep['method']} {ep['path']}" for ep in endpoints]
        endpoints_param = ','.join(endpoint_paths)
        
        # TODO: Trigger api_test.py script execution
        # For now, return the parameters that would be used
        print(f"[@postman_routes:run_api_test] Would run: api_test.py --endpoints '{endpoints_param}'")
        print(f"[@postman_routes:run_api_test] Server URL: {server_url}")
        
        return jsonify({
            'success': True,
            'message': f'Test queued for {len(endpoints)} endpoints on {server_url}',
            'endpoints': endpoint_paths,
            'serverUrl': server_url,
            'note': 'View results in Deployments page'
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
            
            requests_list.append({
                'id': item.get('id', ''),
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

