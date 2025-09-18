"""
Server AI Agent Routes

Server-side AI agent proxy endpoints that forward requests to host AI agent controllers.
"""

from flask import Blueprint, request, jsonify
from shared.lib.utils.route_utils import proxy_to_host
from shared.lib.utils.ai_utils import call_text_ai

# Create blueprint
server_aiagent_bp = Blueprint('server_aiagent', __name__, url_prefix='/server/aiagent')

@server_aiagent_bp.route('/executeTask', methods=['POST'])
def execute_task():
    """Proxy AI task execution request to selected host with async support"""
    try:
        print("[@route:server_aiagent:execute_task] Proxying AI task execution request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Generate task_id for async execution (same pattern as scripts)
        import uuid
        task_id = str(uuid.uuid4())
        request_data['task_id'] = task_id
        
        print(f"[@route:server_aiagent:execute_task] Generated task_id: {task_id}")
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/aiagent/executeTask', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_aiagent_bp.route('/getStatus', methods=['POST'])
def get_status():
    """Proxy AI agent status request to selected host"""
    try:
        print("[@route:server_aiagent:get_status] Proxying AI status request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/aiagent/getStatus', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_aiagent_bp.route('/stopExecution', methods=['POST'])
def stop_execution():
    """Proxy AI agent stop execution request to selected host"""
    try:
        print("[@route:server_aiagent:stop_execution] Proxying AI stop execution request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/aiagent/stopExecution', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_aiagent_bp.route('/debug', methods=['POST'])
def debug_openrouter():
    """Debug endpoint to test OpenRouter AI models directly"""
    try:
        print("[@route:server_aiagent:debug] OpenRouter debug request")
        
        # Get request data
        request_data = request.get_json() or {}
        model = request_data.get('model', 'qwen/qwen-2.5-vl-7b-instruct')
        prompt = request_data.get('prompt', '')
        max_tokens = request_data.get('max_tokens', 1000)
        temperature = request_data.get('temperature', 0.0)
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt is required'
            }), 400
        
        print(f"[@route:server_aiagent:debug] Testing model: {model}")
        print(f"[@route:server_aiagent:debug] Prompt length: {len(prompt)}")
        
        # Call AI directly using ai_utils with custom model
        result = call_text_ai(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model
        )
        
        print(f"[@route:server_aiagent:debug] AI call result: success={result.get('success')}")
        
        if result.get('success'):
            print(f"[@route:server_aiagent:debug] Response length: {len(result.get('content', ''))}")
            return jsonify({
                'success': True,
                'content': result.get('content', ''),
                'provider_used': result.get('provider_used', 'unknown'),
                'model': model
            })
        else:
            error_msg = result.get('error', 'Unknown AI error')
            print(f"[@route:server_aiagent:debug] AI call failed: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'provider_used': result.get('provider_used', 'unknown'),
                'model': model
            }), 400
        
    except Exception as e:
        print(f"[@route:server_aiagent:debug] Exception: {e}")
        return jsonify({
            'success': False,
            'error': f'Debug endpoint error: {str(e)}'
        }), 500