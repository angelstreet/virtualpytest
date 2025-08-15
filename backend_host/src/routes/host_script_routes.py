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
        
        print(f"[@route:host_script:_execute_script] Executing {script_name} on {device_id} with parameters: {parameters}")
        
        # Execute script directly and wait for completion (no callback complexity)
        result = execute_script(script_name, device_id, parameters)
        
        print(f"[@route:host_script:_execute_script] Script completed - success: {result.get('success')}")
        print(f"[@route:host_script:_execute_script] Script has report_url: {bool(result.get('report_url'))}")
        print(f"[@route:host_script:_execute_script] Result keys: {list(result.keys()) if result else 'None'}")
        
        # ENSURE CONSISTENT OUTPUT: Every script must have SCRIPT_SUCCESS
        stdout = result.get('stdout', '')
        if not stdout or 'SCRIPT_SUCCESS:' not in stdout:
            print(f"⚠️ [@route:host_script:_execute_script] WARNING: Script {script_name} did not output SCRIPT_SUCCESS marker")
            print(f"⚠️ [@route:host_script:_execute_script] Stdout length: {len(stdout)} chars")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 