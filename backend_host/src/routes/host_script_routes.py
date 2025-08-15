"""
Host Script Routes - Execute scripts on host device
"""
from flask import Blueprint, request, jsonify
from shared.lib.utils.script_execution_utils import execute_script

host_script_bp = Blueprint('host_script', __name__, url_prefix='/host')

@host_script_bp.route('/script/execute', methods=['POST'])
def _execute_script():
    """Execute script on host device with async support"""
    try:
        data = request.get_json()
        
        script_name = data.get('script_name')
        device_id = data.get('device_id')
        parameters = data.get('parameters', '')
        callback_url = data.get('callback_url')
        task_id = data.get('task_id')
        
        if not script_name or not device_id:
            return jsonify({
                'success': False,
                'error': 'script_name and device_id required'
            }), 400
        
        # Handle async execution with callback
        if callback_url and task_id:
            import threading
            import requests
            
            def execute_async():
                try:
                    print(f"[@route:host_script:_execute_script] Starting async script execution for task {task_id}")
                    result = execute_script(script_name, device_id, parameters)
                    print(f"[@route:host_script:_execute_script] Script execution completed for task {task_id}, success: {result.get('success')}")
                    
                    # Determine if there was an error
                    script_success = result.get('success', False)
                    error_message = None if script_success else result.get('stderr', 'Script execution failed')
                    
                    # Send callback with result
                    callback_data = {
                        'task_id': task_id,
                        'result': result,
                        'error': error_message
                    }
                    
                    try:
                        print(f"[@route:host_script:_execute_script] Sending callback to: {callback_url}")
                        print(f"[@route:host_script:_execute_script] Callback data: task_id={task_id}, success={script_success}, error={error_message}")
                        
                        callback_response = requests.post(
                            callback_url, 
                            json=callback_data, 
                            timeout=30, 
                            verify=False
                        )
                        
                        print(f"[@route:host_script:_execute_script] Callback sent for task {task_id}, status: {callback_response.status_code}")
                        
                        # Log response for debugging
                        if callback_response.status_code != 200:
                            print(f"[@route:host_script:_execute_script] Callback response error: {callback_response.text}")
                        else:
                            print(f"[@route:host_script:_execute_script] Callback successful for task {task_id}")
                            
                    except Exception as callback_error:
                        print(f"[@route:host_script:_execute_script] Callback failed for task {task_id}: {callback_error}")
                        print(f"[@route:host_script:_execute_script] Callback URL was: {callback_url}")
                        import traceback
                        traceback.print_exc()
                        
                except Exception as e:
                    print(f"[@route:host_script:_execute_script] Async execution failed for task {task_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Send callback with error
                    callback_data = {
                        'task_id': task_id,
                        'result': {},
                        'error': str(e)
                    }
                    
                    try:
                        print(f"[@route:host_script:_execute_script] Sending error callback to: {callback_url}")
                        requests.post(callback_url, json=callback_data, timeout=30, verify=False)
                        print(f"[@route:host_script:_execute_script] Error callback sent for task {task_id}")
                    except Exception as callback_error:
                        print(f"[@route:host_script:_execute_script] Error callback also failed for task {task_id}: {callback_error}")
                
                print(f"[@route:host_script:_execute_script] Async execution thread completed for task {task_id}")
            
            # Start background execution
            threading.Thread(target=execute_async, daemon=True).start()
            
            return jsonify({
                'success': True,
                'message': f'Script {script_name} started in background',
                'task_id': task_id
            }), 202
        
        else:
            # Execute synchronously as before for backward compatibility
            result = execute_script(script_name, device_id, parameters)
            return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 