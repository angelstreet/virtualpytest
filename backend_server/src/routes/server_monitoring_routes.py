"""
Server Monitoring Routes

Server-side monitoring proxy endpoints that forward requests to host monitoring controllers.
"""

from flask import Blueprint, request, jsonify, Response
import requests
from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params

server_monitoring_bp = Blueprint('server_monitoring', __name__, url_prefix='/server/monitoring')

def _validate_host_ip(host_ip: str) -> bool:
    """
    Validate that host_ip is either localhost or in the registered hosts allowlist.
    Prevents SSRF attacks by restricting requests to known trusted hosts.
    
    Args:
        host_ip: IP address or hostname to validate
        
    Returns:
        True if host is allowed, False otherwise
    """
    if not host_ip:
        return False
    
    # Allow localhost
    localhost_variants = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
    if host_ip in localhost_variants:
        return True
    
    # Check against registered hosts
    try:
        from backend_server.src.lib.utils.server_utils import get_host_manager
        host_manager = get_host_manager()
        
        # Get all registered hosts
        registered_hosts = host_manager.list_hosts()
        
        for host in registered_hosts:
            # Check if host_ip matches any registered host URL
            host_url = host.get('host_url', '')
            host_ip_from_url = host.get('host_ip', '')
            
            # Match against host_ip or extract from host_url
            if host_ip in [host_ip_from_url, host_url]:
                return True
            
            # Also check if host_ip appears in the URL (e.g., "http://192.168.1.100:5000")
            if host_ip in host_url:
                return True
        
        print(f"[@server_monitoring] Host validation FAILED for {host_ip} - not in allowlist")
        return False
        
    except Exception as e:
        print(f"[@server_monitoring] Host validation ERROR: {e}")
        return False

@server_monitoring_bp.route('/listCaptures', methods=['POST'])
def list_captures():
    """Proxy list captures request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        device_id = request_data.get('device_id', 'device1')
        
        # Let proxy_to_host_with_params handle host lookup via get_host_from_request()

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
        import os
        api_key = os.getenv('API_KEY')
        
        request_data = request.get_json() or {}
        device_id = request_data.get('device_id', 'device1')
        
        # Let proxy_to_host_with_params handle host lookup via get_host_from_request()

        response_data, status_code = proxy_to_host_with_params(
            '/host/monitoring/latest-json',
            'POST',
            request_data,
            {'device_id': device_id}
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_monitoring_bp.route('/json-by-time', methods=['POST'])
def get_json_by_time():
    """Get metadata JSON for specific timestamp (archive mode)"""
    try:
        request_data = request.get_json() or {}
        device_id = request_data.get('device_id', 'device1')
        
        response_data, status_code = proxy_to_host_with_params(
            '/host/monitoring/json-by-time',
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
        
        # SECURITY: Validate host_ip against allowlist to prevent SSRF
        if not _validate_host_ip(host_ip):
            print(f"[@server_monitoring] BLOCKED proxy request to unauthorized host: {host_ip}")
            return jsonify({
                'success': False,
                'error': 'Host IP not authorized. Only registered hosts are allowed.'
            }), 403
        
        is_json = filename.endswith('.json')
        
        file_url = f"http://{host_ip}:{host_port}/host/av/images/screenshot/{filename}?device_id={device_id}"
        
        try:
            response = requests.get(file_url, stream=True, timeout=30)
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

@server_monitoring_bp.route('/live-events', methods=['POST'])
def get_live_events():
    """
    Get live monitoring events (zapping, etc.) for real-time display.
    Events auto-expire after 10 seconds.
    Proxies request to host to read live_events.json file.
    """
    try:
        request_data = request.get_json() or {}
        device_id = request_data.get('device_id', 'device1')
        
        response_data, status_code = proxy_to_host_with_params(
            '/host/monitoring/live-events',
            'POST',
            request_data,
            {'device_id': device_id}
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500