"""
Server Audio/Video Routes

This module contains the server-side audio/video API endpoints that proxy requests
to the selected host's AV controller endpoints.

These endpoints run on the server and forward requests to the appropriate host.
"""

from flask import Blueprint, request, jsonify, Response
import requests
from shared.lib.utils.route_utils import proxy_to_host, proxy_to_host_with_params, get_host_from_request

# Create blueprint
server_av_bp = Blueprint('server_av', __name__, url_prefix='/server/av')

@server_av_bp.route('/restartStream', methods=['POST'])
def restart_stream():
    """Proxy restart stream request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/restartStream',
            'POST',
            request_data,
            query_params
        )

        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/getStreamUrl', methods=['GET', 'POST'])
def get_stream_url():
    """Proxy get stream URL request to selected host with device_id"""
    try:
        if request.method == 'POST':
            request_data = request.get_json() or {}
            device_id = request_data.get('device_id', 'device1')
        else:
            device_id = request.args.get('device_id', 'device1')
            request_data = {}

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/getStreamUrl',
            'GET',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/proxyImage', methods=['GET'])
def proxy_image():
    """Proxy HTTP image URLs through HTTPS to solve mixed content issues"""
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({
                'success': False,
                'error': 'Missing url parameter'
            }), 400
        
        if image_url.startswith('data:'):
            return Response(
                image_url,
                content_type='text/plain',
                headers={'Access-Control-Allow-Origin': '*'}
            )
        
        if image_url.startswith('https:'):
            return Response(
                '',
                status=302,
                headers={
                    'Location': image_url,
                    'Access-Control-Allow-Origin': '*'
                }
            )
        
        if image_url.startswith('http:'):
            try:
                response = requests.get(image_url, stream=True, timeout=30, verify=False)
                response.raise_for_status()
                
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
                    'error': f'Failed to fetch image: {str(e)}'
                }), 502
        
        return jsonify({
            'success': False,
            'error': f'Unsupported URL format: {image_url}'
        }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Image proxy error: {str(e)}'
        }), 500

@server_av_bp.route('/proxyImage', methods=['OPTIONS'])
def proxy_image_options():
    """Handle CORS preflight requests for image proxy"""
    return Response(
        '',
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '86400'
        }
    )

@server_av_bp.route('/proxyMonitoringImage/<filename>', methods=['GET'])
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

@server_av_bp.route('/getStatus', methods=['GET', 'POST'])
def get_status():
    """Proxy get status request to selected host with device_id"""
    try:
        if request.method == 'POST':
            request_data = request.get_json() or {}
            device_id = request_data.get('device_id', 'device1')
            host = request_data.get('host')
        else:
            device_id = request.args.get('device_id', 'device1')
            request_data = {}
            host = None

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/status',
            'GET',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/takeScreenshot', methods=['POST'])
def take_screenshot():
    """Proxy take screenshot request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/takeScreenshot',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/saveScreenshot', methods=['POST'])
def save_screenshot():
    """Proxy save screenshot request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/saveScreenshot',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/startCapture', methods=['POST'])
def start_video_capture():
    """Proxy start video capture request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/startCapture',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/stopCapture', methods=['POST'])
def stop_video_capture():
    """Proxy stop video capture request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/stopCapture',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/takeControl', methods=['POST'])
def take_control():
    """Proxy take control request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/takeControl',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/connect', methods=['POST'])
def connect():
    """Proxy connect request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/connect',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/monitoring/latest-json', methods=['POST'])
def get_latest_monitoring_json():
    """Get the latest available JSON analysis file from selected host"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/monitoring/latest-json',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_av_bp.route('/disconnect', methods=['POST'])
def disconnect():
    """Proxy disconnect request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/av/disconnect',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500