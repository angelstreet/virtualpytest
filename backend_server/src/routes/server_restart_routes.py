"""
Server Restart Routes

Server-side restart video proxy endpoints that forward requests to host restart controllers.
"""

from flask import Blueprint, request, jsonify
from shared.lib.utils.route_utils import proxy_to_host_with_params

server_restart_bp = Blueprint('server_restart', __name__, url_prefix='/server/restart')

@server_restart_bp.route('/generateRestartVideo', methods=['POST'])
def generate_restart_video():
    """Generate video only - fast response"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')
        duration_seconds = request_data.get('duration_seconds', 10)

        print(f"[SERVER] 🎬 [@server_restart_routes:generateRestartVideo] Received request for host: {host}, device: {device_id}, duration: {duration_seconds}s")

        if not host:
            print(f"[SERVER] ❌ [@server_restart_routes:generateRestartVideo] Missing host parameter")
            return jsonify({'success': False, 'error': 'Host required'}), 400

        print(f"[SERVER] 🔄 [@server_restart_routes:generateRestartVideo] Proxying to host {host} endpoint: /host/restart/generateVideo")

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/generateVideo',
            'POST',
            request_data,
            {'device_id': device_id},
            timeout=300  # 5 minutes for video generation
        )
        
        print(f"[SERVER] 📊 [@server_restart_routes:generateRestartVideo] Host response: status={status_code}, success={response_data.get('success', 'unknown')}")
        
        if response_data.get('success'):
            print(f"[SERVER] ✅ [@server_restart_routes:generateRestartVideo] Video generation successful")
        else:
            print(f"[SERVER] ❌ [@server_restart_routes:generateRestartVideo] Video generation failed: {response_data.get('error', 'unknown error')}")
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[SERVER] 💥 [@server_restart_routes:generateRestartVideo] Exception: {str(e)}")
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
            {'device_id': device_id},
            timeout=90  # 90 seconds for audio analysis
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
            {'device_id': device_id},
            timeout=180  # 3 minutes for report generation
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
            timeout=180  # 3 minutes for combined analysis
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

@server_restart_bp.route('/restartStream', methods=['POST'])
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
            '/host/restart/restartStream',
            'POST',
            request_data,
            query_params,
            timeout=60  # 60 seconds for stream restart
        )

        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_restart_bp.route('/generateDubbedVideo', methods=['POST'])
def generate_dubbed_video():
    """Generate dubbed version of restart video"""
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')
        video_id = request_data.get('video_id')
        target_language = request_data.get('target_language', 'es')
        existing_transcript = request_data.get('existing_transcript', '')

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400
        if not existing_transcript:
            return jsonify({'success': False, 'error': 'Transcript required for dubbing'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/generateDubbedVideo',
            'POST',
            request_data,
            {'device_id': device_id, 'video_id': video_id, 'target_language': target_language, 'existing_transcript': existing_transcript},
            timeout=300  # 5 minutes for dubbing
        )
        return jsonify(response_data), status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Dubbing generation failed: {str(e)}'
        }), 500
