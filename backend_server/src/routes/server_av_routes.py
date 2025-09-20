"""
Server Audio/Video Routes

This module contains the server-side audio/video API endpoints that proxy requests
to the selected host's AV controller endpoints.

These endpoints run on the server and forward requests to the appropriate host.
"""

from flask import Blueprint, request, jsonify, Response
import requests
from shared.src.lib.utils.route_utils import proxy_to_host, proxy_to_host_with_params, get_host_from_request

# Create blueprint
server_av_bp = Blueprint('server_av', __name__, url_prefix='/server/av')


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



@server_av_bp.route('/getStatus', methods=['GET', 'POST'])
def get_status():
    """Proxy get status request to selected host with device_id"""
    try:
        if request.method == 'POST':
            request_data = request.get_json() or {}
            device_id = request_data.get('device_id', 'device1')
            host_name = request_data.get('host_name')
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
        host_name = request_data.get('host_name')
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
        host_name = request_data.get('host_name')
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
        host_name = request_data.get('host_name')
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
        host_name = request_data.get('host_name')
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
        host_name = request_data.get('host_name')
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
        host_name = request_data.get('host_name')
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

@server_av_bp.route('/disconnect', methods=['POST'])
def disconnect():
    """Proxy disconnect request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host_name = request_data.get('host_name')
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