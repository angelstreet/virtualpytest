"""
Server stream proxy routes for forwarding requests to hosts
"""

from flask import Blueprint, request, jsonify, Response
import json

from shared.src.lib.utils.build_url_utils import call_host
from  backend_server.src.lib.utils.server_utils import get_host_manager

server_stream_proxy_bp = Blueprint('server_stream_proxy', __name__, url_prefix='/server/stream')

@server_stream_proxy_bp.route('/av/screenshot', methods=['POST'])
def proxy_screenshot():
    """Proxy screenshot request to appropriate host"""
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        
        print(f"📸 [PROXY] Screenshot request for host: {host_name}")
        
        # Get host from manager
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({'error': f'Host {host_name} not found'}), 404
        
        # Forward request to host
        print(f"📡 [PROXY] Forwarding screenshot request to host via call_host()")
        
        response_data, status_code = call_host(
            host_data,
            '/host/av/screenshot',
            method='POST',
            data=data,
            timeout=30
        )
        
        if status_code == 200:
            return jsonify(response_data)
        else:
            error_msg = f"Screenshot request failed: {status_code} {response_data.get('error', 'Unknown error')}"
            print(f"❌ [PROXY] {error_msg}")
            return jsonify({'error': error_msg}), status_code
        
    except Exception as e:
        print(f"❌ [PROXY] Error proxying screenshot: {e}")
        return jsonify({'error': str(e)}), 500

@server_stream_proxy_bp.route('/av/streamUrl', methods=['POST'])
def proxy_stream_url():
    """Proxy stream URL request to appropriate host"""
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        
        print(f"📺 [PROXY] Stream URL request for host: {host_name}")
        
        # Get host from manager
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({'error': f'Host {host_name} not found'}), 404
        
        # Forward request to host
        print(f"📡 [PROXY] Forwarding stream URL request to host via call_host()")
        
        response_data, status_code = call_host(
            host_data,
            '/host/av/streamUrl',
            method='POST',
            data=data,
            timeout=30
        )
        
        if status_code == 200:
            return jsonify(response_data)
        else:
            error_msg = f"Stream URL request failed: {status_code} {response_data.get('error', 'Unknown error')}"
            print(f"❌ [PROXY] {error_msg}")
            return jsonify({'error': error_msg}), status_code
        
    except Exception as e:
        print(f"❌ [PROXY] Error proxying stream URL: {e}")
        return jsonify({'error': str(e)}), 500

@server_stream_proxy_bp.route('/verification/execute', methods=['POST'])
def proxy_verification():
    """Proxy verification request to appropriate host"""
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        
        print(f"✅ [PROXY] Verification request for host: {host_name}")
        
        # Get host from manager
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({'error': f'Host {host_name} not found'}), 404
        
        # Forward request to host with async support
        print(f"📡 [PROXY] Forwarding verification request to host via call_host()")
        
        response_data, status_code = call_host(
            host_data,
            '/host/verification/execute',
            method='POST',
            data=data,
            timeout=60  # Longer timeout for verification
        )
        
        if status_code == 200:
            return jsonify(response_data)
        else:
            error_msg = f"Verification request failed: {status_code} {response_data.get('error', 'Unknown error')}"
            print(f"❌ [PROXY] {error_msg}")
            return jsonify({'error': error_msg}), status_code
        
    except Exception as e:
        print(f"❌ [PROXY] Error proxying verification: {e}")
        return jsonify({'error': str(e)}), 500 