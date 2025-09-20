"""
Server Monitoring Routes

Server-side monitoring proxy endpoints that forward requests to host monitoring controllers.
"""

from flask import Blueprint, request, jsonify, Response
import requests
from shared.src.lib.utils.route_utils import proxy_to_host_with_params

server_monitoring_bp = Blueprint('server_monitoring', __name__, url_prefix='/server/monitoring')

@server_monitoring_bp.route('/listCaptures', methods=['POST'])
def list_captures():
    """Proxy list captures request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host_name = request_data.get('host_name')
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
        host_name = request_data.get('host_name')
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

@server_monitoring_bp.route('/proxyImage/<filename>', methods=['GET'])
def proxy_monitoring_image(filename):
    """Proxy monitoring image and JSON requests to the selected host"""
    try:
        host_ip = request.args.get('host_ip')
        host_port = request.args.get('host_port', '5000')
        device_id = request.args.get('device_id', 'device1')
        
        if not host_ip:
            return jsonify({
                'success': False,
                'error': 'host_ip parameter required'
            }), 400
        
        is_json = filename.endswith('.json')
        
        file_url = f"http://{host_ip}:{host_port}/host/av/images/screenshot/{filename}?device_id={device_id}"
        
        try:
            response = requests.get(file_url, stream=True, timeout=30, verify=False)
            response.raise_for_status()
            
            if is_json:
                content_type = 'application/json'
            else:
                content_type = response.headers.get('Content-Type', 'image/jpeg')
            
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            
            return Response(
                generate(),
                content_type=content_type,
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Content-Length': response.headers.get('Content-Length'),
                    'Cache-Control': 'no-cache, no-store, must-revalidate'
                }
            )
            
        except requests.exceptions.RequestException as e:
            return jsonify({
                'success': False,
                'error': f'Failed to fetch monitoring file: {str(e)}'
            }), 502
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Monitoring file proxy error: {str(e)}'
        }), 500