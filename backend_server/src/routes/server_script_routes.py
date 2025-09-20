"""
Server Script Routes - Script management and execution proxy
"""
import os
import re
from flask import Blueprint, request, jsonify
import requests
from src.lib.utils.host_utils import get_host_manager
from src.lib.utils.build_url_utils import buildHostUrl

server_script_bp = Blueprint('server_script', __name__, url_prefix='/server')

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
        
        # Look for argparse patterns
        parameters = []
        
        # Find argument parser creation and add_argument calls
        parser_patterns = [
            r"parser\.add_argument\(['\"]([^'\"]+)['\"][^)]*\)",
            r"parser\.add_argument\(['\"]--([^'\"]+)['\"][^)]*\)",
            r"parser\.add_argument\(['\"]([^'\"]+)['\"].*help=['\"]([^'\"]*)['\"]",
        ]
        
        # Extract positional arguments (required)
        positional_pattern = r"parser\.add_argument\(['\"]([^-][^'\"]*)['\"](?:[^)]*help=['\"]([^'\"]*)['\"])?[^)]*\)"
        positional_matches = re.findall(positional_pattern, script_content, re.MULTILINE)
        
        for match in positional_matches:
            param_name = match[0]
            help_text = match[1] if len(match) > 1 else ''
            parameters.append({
                'name': param_name,
                'type': 'positional',
                'required': True,
                'help': help_text or f'Required parameter: {param_name}',
                'default': None
            })
        
        # Extract optional arguments with better multi-line handling
        # Look for parser.add_argument('--param_name', ... ) patterns that can span multiple lines
        optional_pattern = r"parser\.add_argument\(['\"]--([^'\"]+)['\"]([^)]*?)\)"
        
        # Find all add_argument calls for optional parameters
        for match in re.finditer(optional_pattern, script_content, re.MULTILINE | re.DOTALL):
            param_name = match.group(1)
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
                'help': help_text or f'Optional parameter: --{param_name}',
                'default': default_value
            })
        
        # Add standard framework parameters that all scripts using ScriptExecutor have
        # Check if script uses ScriptExecutor framework
        if 'ScriptExecutor' in script_content or 'script_framework' in script_content:
            # Add userinterface_name as positional if not already present
            if not any(p['name'] == 'userinterface_name' for p in parameters):
                parameters.insert(0, {
                    'name': 'userinterface_name',
                    'type': 'positional',
                    'required': True,
                    'help': 'Name of the userinterface to use (default: horizon_android_mobile)',
                    'default': 'horizon_android_mobile'
                })
            
            # Add host parameter if not already present
            if not any(p['name'] == 'host' for p in parameters):
                parameters.append({
                    'name': 'host',
                    'type': 'optional',
                    'required': False,
                    'help': 'Specific host to use (will be auto-filled from selection)',
                    'default': None
                })
            
            # Add device parameter if not already present
            if not any(p['name'] == 'device' for p in parameters):
                parameters.append({
                    'name': 'device',
                    'type': 'optional',
                    'required': False,
                    'help': 'Specific device to use (will be auto-filled from selection)',
                    'default': None
                })
        
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
        from src.lib.utils.script_execution_utils import get_script_path
        
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

@server_script_bp.route('/script/list', methods=['GET'])
def list_scripts():
    """List all available Python scripts AND AI test cases"""
    try:
        # Get regular Python scripts
        from src.lib.utils.script_execution_utils import list_available_scripts, get_scripts_directory
        
        regular_scripts = list_available_scripts()
        scripts_dir = get_scripts_directory()
        
        # Get AI test cases from database
        ai_scripts = []
        ai_test_cases_info = []
        
        try:
            from shared.src.lib.utils.app_utils import get_team_id
            from shared.src.lib.utils.testcase_db import get_all_test_cases
            
            team_id = get_team_id()
            all_test_cases = get_all_test_cases(team_id)
            
            # Filter for AI-created test cases and format as script names
            for tc in all_test_cases:
                if tc.get('creator') == 'ai':
                    script_name = f"ai_testcase_{tc['test_id']}"
                    ai_scripts.append(script_name)
                    
                    # Store metadata for frontend display
                    ai_test_cases_info.append({
                        'script_name': script_name,
                        'test_case_id': tc['test_id'],
                        'name': tc.get('name', 'Unnamed AI Test Case'),
                        'original_prompt': tc.get('original_prompt', ''),
                        'compatible_userinterfaces': tc.get('compatible_userinterfaces', []),
                        'created_at': tc.get('created_at', '')
                    })
            
            print(f"[@server_script_routes:list_scripts] Found {len(ai_scripts)} AI test cases")
            
        except Exception as e:
            print(f"[@server_script_routes:list_scripts] Error loading AI test cases: {e}")
            # Continue without AI test cases if there's an error
        
        # Combine both types
        all_scripts = regular_scripts + ai_scripts
        
        if not all_scripts:
            return jsonify({
                'success': False,
                'error': f'No scripts found in directory: {scripts_dir} and no AI test cases'
            }), 404
        
        return jsonify({
            'success': True,
            'scripts': all_scripts,
            'count': len(all_scripts),
            'scripts_directory': scripts_dir,
            'regular_scripts': regular_scripts,
            'ai_scripts': ai_scripts,
            'ai_test_cases_info': ai_test_cases_info  # Metadata for frontend
        })
        
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
        
        # Create task for async execution
        from src.lib.utils.task_manager import task_manager
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
                print(f"[@route:server_script:execute_script] Starting background execution for task {task_id}")
                
                # Build host URL
                host_url = buildHostUrl(host_info, '/host/script/execute')
                print(f"[@route:server_script:execute_script] Making request to host URL: {host_url}")
                print(f"[@route:server_script:execute_script] Payload: {payload}")
                
                # Make request to host (immediate response expected)
                response = requests.post(
                    host_url,
                    json=payload,
                    timeout=120  # 2 minutes timeout for immediate response
                )
                
                result = response.json()
                
                if response.status_code not in [200, 202]:
                    # Host execution failed, complete task with error
                    print(f"[@route:server_script:execute_script] Host execution failed for task {task_id}")
                    task_manager.complete_task(task_id, {}, error=result.get('error', 'Host execution failed'))
                else:
                    print(f"[@route:server_script:execute_script] Host execution started for task {task_id}")
                    # Task will be completed by the host's callback
                        
            except Exception as e:
                print(f"[@route:server_script:execute_script] Background execution error for task {task_id}: {e}")
                print(f"[@route:server_script:execute_script] Exception type: {type(e).__name__}")
                import traceback
                print(f"[@route:server_script:execute_script] Traceback: {traceback.format_exc()}")
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
        from src.lib.utils.task_manager import task_manager
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
        from src.lib.utils.task_manager import task_manager
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