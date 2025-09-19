"""
Server AI Agent Routes - Proxy to Host
Handles AI agent execution requests by proxying to selected host
"""

import uuid
from flask import Blueprint, request, jsonify
from shared.lib.utils.route_utils import proxy_to_host

server_aiagent_bp = Blueprint('server_aiagent', __name__, url_prefix='/server/aiagent')

@server_aiagent_bp.route('/executeTask', methods=['POST'])
def execute_task():
    """Proxy AI task execution request to selected host with async support"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        # Generate task_id for async execution tracking
        task_id = str(uuid.uuid4())
        request_data['task_id'] = task_id
        
        print(f"[@server_aiagent] Executing AI task with ID: {task_id}")
        print(f"[@server_aiagent] Task description: {request_data.get('task_description', 'N/A')}")
        print(f"[@server_aiagent] Device ID: {request_data.get('device_id', 'N/A')}")
        print(f"[@server_aiagent] Host: {request_data.get('host', 'N/A')}")
        
        # Proxy to host - CRITICAL: This preserves navigation context
        response_data, status_code = proxy_to_host('/host/aiagent/executeTask', 'POST', request_data)
        
        print(f"[@server_aiagent] Host response status: {status_code}")
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_aiagent] Error executing AI task: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500

@server_aiagent_bp.route('/getStatus', methods=['POST'])
def get_status():
    """Proxy AI agent status request to selected host"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        print(f"[@server_aiagent] Getting AI status for device: {request_data.get('device_id', 'N/A')}")
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/aiagent/getStatus', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_aiagent] Error getting AI status: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500

@server_aiagent_bp.route('/stopExecution', methods=['POST'])
def stop_execution():
    """Proxy AI agent stop execution request to selected host"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        print(f"[@server_aiagent] Stopping AI execution for device: {request_data.get('device_id', 'N/A')}")
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/aiagent/stopExecution', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_aiagent] Error stopping AI execution: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500

@server_aiagent_bp.route('/generatePlan', methods=['POST'])
def generate_plan():
    """Proxy AI plan generation request to selected host"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        print(f"[@server_aiagent] Generating AI plan for device: {request_data.get('device_id', 'N/A')}")
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/aiagent/generatePlan', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_aiagent] Error generating AI plan: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500

@server_aiagent_bp.route('/analyzeCompatibility', methods=['POST'])
def analyze_compatibility():
    """Proxy AI compatibility analysis request to selected host"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        print(f"[@server_aiagent] Analyzing AI compatibility for prompt: {request_data.get('prompt', 'N/A')}")
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/aiagent/analyzeCompatibility', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_aiagent] Error analyzing AI compatibility: {e}")
        return jsonify({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }), 500
