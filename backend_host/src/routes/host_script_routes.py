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
        # Build callback URL directly (always points to server)
        from shared.lib.utils.build_url_utils import buildServerUrl
        callback_url = buildServerUrl('server/script/taskComplete')
        task_id = data.get('task_id')
        
        if not script_name or not device_id:
            return jsonify({
                'success': False,
                'error': 'script_name and device_id required'
            }), 400
        
        print(f"[@route:host_script:_execute_script] Executing {script_name} on {device_id} with parameters: {parameters}")
        
        if task_id:
            print(f"[@route:host_script:_execute_script] CALLBACK PREP: Async execution for task {task_id}")
            # Execute async with callback
            import threading
            def execute_async():
                try:
                    result = execute_script(script_name, device_id, parameters)
                    print(f"[@route:host_script:_execute_script] CALLBACK SEND: Script completed, sending callback")
                    
                    # Send callback to server
                    import requests
                    callback_payload = {
                        'task_id': task_id,
                        'result': result
                    }
                    
                    requests.post(callback_url, json=callback_payload, timeout=30)
                    print(f"[@route:host_script:_execute_script] Callback sent successfully")
                    
                except Exception as e:
                    print(f"[@route:host_script:_execute_script] Error in async execution: {e}")
                    # Send error callback
                    error_payload = {
                        'task_id': task_id,
                        'error': str(e)
                    }
                    try:
                        import requests
                        requests.post(callback_url, json=error_payload, timeout=30)
                    except:
                        pass
            
            # Start async execution
            threading.Thread(target=execute_async, daemon=True).start()
            
            return jsonify({
                'success': True,
                'message': 'Script execution started',
                'task_id': task_id
            }), 202
        else:
            # Synchronous execution (fallback)
            print(f"[@route:host_script:_execute_script] SYNC: Direct execution (no callback)")
            result = execute_script(script_name, device_id, parameters)
            
            print(f"[@route:host_script:_execute_script] Script completed - exit_code: {result.get('exit_code')}")
            print(f"[@route:host_script:_execute_script] Script has report_url: {bool(result.get('report_url'))}")
            print(f"[@route:host_script:_execute_script] Result keys: {list(result.keys()) if result else 'None'}")
            
            return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 