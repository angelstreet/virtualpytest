"""
Server Monitoring Routes

Server-side monitoring proxy endpoints that forward requests to host monitoring controllers.
"""

from flask import Blueprint, request, jsonify
from shared.lib.utils.route_utils import proxy_to_host_with_params

server_monitoring_bp = Blueprint('server_monitoring', __name__, url_prefix='/server/monitoring')

@server_monitoring_bp.route('/listCaptures', methods=['POST'])
def list_captures():
    """Proxy list captures request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/monitoring/listCaptures',
            'POST',
            request_data,
            {'device_id': device_id}
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_monitoring_bp.route('/latest-json', methods=['POST'])
def get_latest_monitoring_json():
    """Get the latest available JSON analysis file from selected host"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/monitoring/latest-json',
            'POST',
            request_data,
            {'device_id': device_id}
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
