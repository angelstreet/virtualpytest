"""
Server Restart Routes

Server-side restart video proxy endpoints that forward requests to host restart controllers.
"""

from flask import Blueprint, request, jsonify
from shared.lib.utils.route_utils import proxy_to_host_with_params

server_restart_bp = Blueprint('server_restart', __name__, url_prefix='/server/av')

@server_restart_bp.route('/generateRestartVideo', methods=['POST'])
def generate_restart_video():
    """Generate video only - fast response"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/generateVideo',
            'POST',
            request_data,
            {'device_id': device_id}
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_restart_bp.route('/analyzeRestartAudio', methods=['POST'])
def analyze_restart_audio():
    """Analyze audio transcript"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/analyzeAudio',
            'POST',
            request_data,
            {'device_id': device_id}
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_restart_bp.route('/generateRestartReport', methods=['POST'])
def generate_restart_report():
    """Generate restart report"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/generateReport',
            'POST',
            request_data,
            {'device_id': device_id}
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_restart_bp.route('/analyzeRestartComplete', methods=['POST'])
def analyze_restart_complete():
    """Combined restart analysis: subtitles + summary in single call"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/analyzeComplete',
            'POST',
            request_data,
            {'device_id': device_id},
            timeout=60
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_restart_bp.route('/analyzeRestartVideo', methods=['POST'])
def analyze_restart_video():
    """Proxy async AI analysis request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/analyzeVideo',
            'POST',
            request_data,
            {'device_id': device_id},
            timeout=120
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
