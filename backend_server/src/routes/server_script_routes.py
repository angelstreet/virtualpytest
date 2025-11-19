"""
Server Script Routes - Script management and execution proxy
"""
import os
import re
import time
import threading
from flask import Blueprint, request, jsonify
import requests
from  backend_server.src.lib.utils.server_utils import get_host_manager
from shared.src.lib.utils.build_url_utils import buildHostUrl
from shared.src.lib.config.constants import CACHE_CONFIG

server_script_bp = Blueprint('server_script', __name__, url_prefix='/server')

# ============================================================================
# IN-MEMORY CACHE FOR SCRIPT LIST
# ============================================================================
_script_cache = {}  # {team_id: {'data': {...}, 'timestamp': time.time()}}
_cache_lock = threading.Lock()

def analyze_script_parameters(script_path):
    """
    Analyze a Python script to extract parameter information from argparse
    Returns dict with parameter details including required/optional status
    """
    try:
        if not os.path.exists(script_path):
            return {'success': False, 'error': f'Script not found: {script_path}'}
        
        with open(script_path, 'r', encoding='utf-8') as f:
            # Read first 300 lines to analyze parameters (some scripts have args later in file)
            lines = []
            for i, line in enumerate(f):
                if i >= 300:
                    break
                lines.append(line.strip())
        
        script_content = '\n'.join(lines)
        
        # Look for both argparse patterns AND _script_args decorator patterns
        parameters = []
        
        # FIRST: Check for _script_args pattern (used by @script decorator framework)
        # Format: main._script_args = ['--param:type:default', ...]
        script_args_pattern = r"_script_args\s*=\s*\[(.*?)\]"
        script_args_match = re.search(script_args_pattern, script_content, re.DOTALL)
        
        if script_args_match:
            args_content = script_args_match.group(1)
            # Parse each argument: '--param:type:default' or '--param:type'
            arg_items = re.findall(r"['\"]([^'\"]+)['\"]", args_content)
            print(f"[@analyze_script] Found _script_args: {arg_items}")
            
            for arg_item in arg_items:
                # Parse format: --param-name:type:default or --param-name:type
                parts = arg_item.split(':')
                if len(parts) >= 2:
                    # Keep dashes in parameter names - they're used for command-line arguments
                    param_name = parts[0].replace('--', '')
                    param_type = parts[1] if len(parts) > 1 else 'str'
                    default_value = parts[2] if len(parts) > 2 else None
                    
                    # Convert default values
                    if default_value == 'None':
                        default_value = None
                    elif default_value == 'true' or default_value == 'True':
                        default_value = 'true'
                    elif default_value == 'false' or default_value == 'False':
                        default_value = 'false'
                    
                    param = {
                        'name': param_name,
                        'type': 'optional',
                        'required': False,
                        'help': '',
                        'default': default_value
                    }
                    print(f"[@analyze_script] Parsed parameter from _script_args: {param}")
                    parameters.append(param)
        
        # SECOND: Look for argparse patterns (fallback for scripts not using @script decorator)
        parser_patterns = [
            r"parser\.add_argument\(['\"]([^'\"]+)['\"][^)]*\)",
            r"parser\.add_argument\(['\"]--([^'\"]+)['\"][^)]*\)",
            r"parser\.add_argument\(['\"]([^'\"]+)['\"].*help=['\"]([^'\"]*)['\"]",
        ]
        
        # Extract positional arguments (required) - only if not already found in _script_args
        positional_pattern = r"parser\.add_argument\(['\"]([^-][^'\"]*)['\"](?:[^)]*help=['\"]([^'\"]*)['\"])?[^)]*\)"
        positional_matches = re.findall(positional_pattern, script_content, re.MULTILINE)
        
        for match in positional_matches:
            param_name = match[0]
            help_text = match[1] if len(match) > 1 else ''
            
            # Skip if already added from _script_args
            if not any(p['name'] == param_name for p in parameters):
                parameters.append({
                    'name': param_name,
                    'type': 'positional',
                    'required': True,
                    'help': help_text,
                    'default': None
                })
        
        # Extract optional arguments with better multi-line handling
        # Look for parser.add_argument('--param_name', ... ) patterns that can span multiple lines
        optional_pattern = r"parser\.add_argument\(['\"]--([^'\"]+)['\"]([^)]*?)\)"
        
        # Find all add_argument calls for optional parameters - only if not already found in _script_args
        for match in re.finditer(optional_pattern, script_content, re.MULTILINE | re.DOTALL):
            param_name = match.group(1)
            
            # Skip if already added from _script_args
            if any(p['name'] == param_name for p in parameters):
                continue
            
            args_content = match.group(2)  # Everything between the parameter name and closing )
            
            # Extract help text
            help_match = re.search(r"help=['\"]([^'\"]*)['\"]", args_content)
            help_text = help_match.group(1) if help_match else ''
            
            # Extract default value
            default_match = re.search(r"default=([^,)]+)", args_content)
            default_value = None
            if default_match:
                default_raw = default_match.group(1).strip()
                # Handle different types of defaults
                if default_raw == 'True':
                    default_value = 'true'
                elif default_raw == 'False':
                    default_value = 'false'
                elif default_raw.startswith("'") and default_raw.endswith("'"):
                    default_value = default_raw[1:-1]
                elif default_raw.startswith('"') and default_raw.endswith('"'):
                    default_value = default_raw[1:-1]
                elif default_raw.isdigit():
                    default_value = default_raw
                else:
                    # For complex expressions like lambda, just take the value before comma/parenthesis
                    default_value = default_raw.split(',')[0].split(')')[0].strip()
            
            parameters.append({
                'name': param_name,
                'type': 'optional',
                'required': False,
                'help': help_text,
                'default': default_value
            })
        
        # NO MORE INJECTION - Scripts explicitly define all their parameters
        # Framework parameters (userinterface_name, host, device) should be
        # explicitly defined in script's _script_args if the script needs them
        
        # Special handling for common patterns
        if 'userinterface_name' in [p['name'] for p in parameters]:
            # Add suggestions for userinterface_name based on common patterns
            ui_param = next(p for p in parameters if p['name'] == 'userinterface_name')
            ui_param['suggestions'] = [
                'horizon_android_mobile',
                'horizon_android_tv'
            ]
        
        return {
            'success': True,
            'parameters': parameters,
            'script_name': os.path.basename(script_path),
            'has_parameters': len(parameters) > 0
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Error analyzing script: {str(e)}'}



@server_script_bp.route('/script/analyze', methods=['POST'])
def analyze_script():
    """Analyze script parameters"""
    try:
        data = request.get_json()
        script_name = data.get('script_name')
        device_model = data.get('device_model')
        device_id = data.get('device_id')
        
        if not script_name:
            return jsonify({
                'success': False,
                'error': 'script_name is required'
            }), 400
        
        # Use centralized script path logic
        from  backend_server.src.lib.utils.script_utils import get_script_path
        
        try:
            script_path = get_script_path(script_name)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
        
        print(f"[@analyze_script] Looking for script at: {script_path}")
        print(f"[@analyze_script] Script exists: {os.path.exists(script_path)}")
        
        # Analyze parameters
        analysis = analyze_script_parameters(script_path)
        
        if not analysis['success']:
            return jsonify(analysis), 404
        

        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"[@analyze_script] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_script_bp.route('/script/get_edge_options', methods=['POST'])
def get_edge_options():
    """Get available edge action_set labels for KPI measurement script"""
    try:
        data = request.get_json()
        userinterface_name = data.get('userinterface_name')
        team_id = data.get('team_id')
        host_name = data.get('host_name')
        
        if not all([userinterface_name, team_id, host_name]):
            return jsonify({
                'success': False,
                'error': 'userinterface_name, team_id, and host_name are required'
            }), 400
        
        print(f"[@get_edge_options] Loading edges for {userinterface_name} on {host_name}")
        
        # Get host info
        host_manager = get_host_manager()
        host_info = host_manager.get_host(host_name)
        
        if not host_info:
            return jsonify({
                'success': False,
                'error': f'Host not found: {host_name}'
            }), 404
        
        # Call host to get edges
        from shared.src.lib.utils.build_url_utils import call_host
        
        response_data, status_code = call_host(
            host_info,
            '/host/script/get_edge_options',
            method='POST',
            data={
                'userinterface_name': userinterface_name,
                'team_id': team_id
            },
            timeout=30
        )
        
        if status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Host request failed: {response_data.get("error", "Unknown error")}'
            }), status_code
        
        if not response_data.get('success'):
            return jsonify(response_data), 400
        
        print(f"[@get_edge_options] Found {len(response_data.get('edge_options', []))} edge options")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[@get_edge_options] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_script_bp.route('/script/list', methods=['GET'])
def list_scripts():
    """List all available Python scripts AND AI test cases"""
    try:
        # Get team_id from request args (GET request)
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        # Check cache first
        with _cache_lock:
            if team_id in _script_cache:
                cached = _script_cache[team_id]
                age = time.time() - cached['timestamp']
                if age < CACHE_CONFIG['SHORT_TTL']:
                    print(f"[@cache] HIT: Script list for team {team_id} (age: {age:.1f}s)")
                    return jsonify(cached['data'])
                else:
                    del _script_cache[team_id]
        
        # Get regular Python scripts
        from  backend_server.src.lib.utils.script_utils import list_available_scripts, get_scripts_directory
        
        regular_scripts = list_available_scripts()
        scripts_dir = get_scripts_directory()
        
        # NOTE: AI test cases are loaded separately via /server/testcase/list endpoint
        # No need to mix them with scripts here
        ai_scripts = []
        ai_test_cases_info = []
        
        # Combine both types
        all_scripts = regular_scripts + ai_scripts
        
        if not all_scripts:
            return jsonify({
                'success': False,
                'error': f'No scripts found in directory: {scripts_dir} and no AI test cases'
            }), 404
        
        response_data = {
            'success': True,
            'scripts': all_scripts,
            'count': len(all_scripts),
            'scripts_directory': scripts_dir,
            'regular_scripts': regular_scripts,
            'ai_scripts': ai_scripts,
            'ai_test_cases_info': ai_test_cases_info  # Metadata for frontend
        }
        
        # Store in cache
        with _cache_lock:
            _script_cache[team_id] = {
                'data': response_data,
                'timestamp': time.time()
            }
            print(f"[@cache] SET: Script list for team {team_id}")
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_script_bp.route('/script/execute', methods=['POST'])
def execute_script():
    """Execute script asynchronously to prevent timeouts"""
    try:
        data = request.get_json()
        
        # Get team_id from query params (standardized pattern)
        team_id = request.args.get('team_id')
        print(f"[@server_script:execute_script] Team ID: {team_id or 'N/A'}")
        
        host_name = data.get('host_name')
        device_id = data.get('device_id')
        script_name = data.get('script_name')
        parameters = data.get('parameters', '')
        
        if not all([host_name, device_id, script_name]):
            return jsonify({
                'success': False,
                'error': 'host_name, device_id, and script_name required'
            }), 400
        
        # Get host info from registry
        host_manager = get_host_manager()
        host_info = host_manager.get_host(host_name)
        
        if not host_info:
            return jsonify({
                'success': False,
                'error': f'Host not found: {host_name}'
            }), 404
        
        # Check if device is locked by another session
        from  backend_server.src.lib.utils.lock_utils import get_device_lock_info, lock_device, unlock_device, get_client_ip
        from flask import session
        import uuid
        
        # Generate session ID if not exists
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        client_ip = get_client_ip()
        
        # Check if device is already locked
        lock_info = get_device_lock_info(host_name)
        if lock_info and lock_info.get('lockedBy') != session_id:
            # Check if same IP can take over
            if not (client_ip and lock_info.get('lockedIp') == client_ip):
                return jsonify({
                    'success': False,
                    'error': f'Device {host_name} is locked by another session',
                    'errorType': 'device_locked',
                    'locked_by': lock_info.get('lockedBy'),
                    'locked_at': lock_info.get('lockedAt'),
                    'locked_ip': lock_info.get('lockedIp')
                }), 423  # HTTP 423 Locked
        
        # Lock device for script execution
        lock_success = lock_device(host_name, session_id, client_ip)
        if not lock_success:
            return jsonify({
                'success': False,
                'error': f'Failed to lock device {host_name} for script execution'
            }), 500
        
        # Create task for async execution
        from  backend_server.src.lib.utils.task_manager import task_manager
        task_id = task_manager.create_task('script_execute', {
            'script_name': script_name,
            'host_name': host_name,
            'device_id': device_id,
            'parameters': parameters
        })
        
        # Prepare request payload with callback
        payload = {
            'script_name': script_name,
            'device_id': device_id,
            'task_id': task_id
        }
        
        # Add parameters if provided
        if parameters and parameters.strip():
            payload['parameters'] = parameters.strip()
        
        # Host will build callback URL directly, no need to pass it
        
        # Execute in background thread (keep async for frontend polling)
        import threading
        def execute_async():
            try:
                from shared.src.lib.utils.build_url_utils import call_host
                
                print(f"[@route:server_script:execute_script] Starting background execution for task {task_id}")
                print(f"[@route:server_script:execute_script] Payload: {payload}")
                
                # Use centralized call_host() which automatically adds API key
                response_data, status_code = call_host(
                    host_info,
                    '/host/script/execute',
                    method='POST',
                    data=payload,
                    timeout=120  # 2 minutes timeout for immediate response
                )
                
                if status_code not in [200, 202]:
                    # Host execution failed, complete task with error and unlock device
                    print(f"[@route:server_script:execute_script] Host execution failed for task {task_id}")
                    unlock_device(host_name, session_id)
                    task_manager.complete_task(task_id, {}, error=response_data.get('error', 'Host execution failed'))
                else:
                    print(f"[@route:server_script:execute_script] Host execution started for task {task_id}")
                    # Task will be completed by the host's callback (which will unlock device)
                        
            except Exception as e:
                print(f"[@route:server_script:execute_script] Background execution error for task {task_id}: {e}")
                print(f"[@route:server_script:execute_script] Exception type: {type(e).__name__}")
                import traceback
                print(f"[@route:server_script:execute_script] Traceback: {traceback.format_exc()}")
                # Unlock device on error
                unlock_device(host_name, session_id)
                task_manager.complete_task(task_id, {}, error=str(e))
        
        threading.Thread(target=execute_async, daemon=True).start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': 'started',
            'message': f'Script "{script_name}" started in background'
        }), 202
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_script_bp.route('/script/taskComplete', methods=['POST'])
def task_complete():
    """Receive script execution completion callback from host"""
    try:
        print("[@route:server_script:task_complete] Received script completion callback")
        
        # Get callback data
        callback_data = request.get_json() or {}
        task_id = callback_data.get('task_id')
        result = callback_data.get('result', {})
        error = callback_data.get('error')
        
        if not task_id:
            return jsonify({
                'success': False,
                'error': 'task_id required'
            }), 400
        
        # Update task in manager
        from  backend_server.src.lib.utils.task_manager import task_manager
        
        # Get task info to unlock device
        task_info = task_manager.get_task(task_id)
        if task_info and task_info.get('data'):
            host_name = task_info['data'].get('host_name')
            if host_name:
                # Unlock device after script completion
                from  backend_server.src.lib.utils.lock_utils import unlock_device
                unlock_success = unlock_device(host_name)
                print(f"[@route:server_script:task_complete] Device unlock for {host_name}: {'success' if unlock_success else 'failed'}")
        
        task_manager.complete_task(task_id, result, error)
        
        print(f"[@route:server_script:task_complete] Task {task_id} marked as {'failed' if error else 'completed'}")
        
        return jsonify({
            'success': True,
            'message': 'Script completion processed'
        }), 200
        
    except Exception as e:
        print(f"[@route:server_script:task_complete] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_script_bp.route('/script/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of an async script execution task"""
    try:
        from  backend_server.src.lib.utils.task_manager import task_manager
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        return jsonify({
            'success': True,
            'task': task
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500