"""
Server AI Agent Routes

Server-side AI agent proxy endpoints that forward requests to host AI agent controllers.
"""

from flask import Blueprint, request, jsonify
from src.web.utils.routeUtils import proxy_to_host

# Create blueprint
server_aiagent_bp = Blueprint('server_aiagent', __name__, url_prefix='/server/aiagent')

@server_aiagent_bp.route('/executeTask', methods=['POST'])
def execute_task():
    """Proxy AI task execution request to selected host"""
    try:
        print("[@route:server_aiagent:execute_task] Proxying AI task execution request")
        
        # Get request data
        request_data = request.get_json() or {}
        
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