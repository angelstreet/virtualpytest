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

@server_restart_bp.route('/analysisStatus/<video_id>', methods=['POST'])
def get_analysis_status(video_id):
    """Get analysis status for polling"""
    try:
        data = request.get_json()
        device_id = data.get('device_id', 'device1')
        host = data.get('host')
        
        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400
        
        response_data, status_code = proxy_to_host_with_params(
            f'/host/restart/analysisStatus/{video_id}',
            'POST',
            {'device_id': device_id},
            {}
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
            {'device_id': device_id},
            timeout=300  # 5 minutes for audio analysis (AI processing can be slow)
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
            timeout=300  # 5 minutes for report generation
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
            timeout=600  # 10 minutes for combined analysis (AI processing can be slow)
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

# =============================================================================
# 4-Step Dubbing Process Routes
# =============================================================================

@server_restart_bp.route('/prepareDubbingAudio', methods=['POST'])
def prepare_dubbing_audio():
    """Step 1: Prepare audio for dubbing (extract + separate) ~20-35s"""
    import time
    step_start_time = time.time()
    
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')
        video_id = request_data.get('video_id')

        print(f"[SERVER] 🎵 [@server_restart_routes:prepareDubbingAudio] Step 1 starting for video_id: {video_id}")

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/prepareDubbingAudio',
            'POST',
            request_data,
            {'device_id': device_id, 'video_id': video_id},
            timeout=120  # 2 minutes for audio separation
        )
        
        step_duration = time.time() - step_start_time
        
        if response_data.get('success'):
            print(f"[SERVER] ✅ [@server_restart_routes:prepareDubbingAudio] Step 1 completed in {step_duration:.1f}s")
        else:
            print(f"[SERVER] ❌ [@server_restart_routes:prepareDubbingAudio] Step 1 failed after {step_duration:.1f}s: {response_data.get('error', 'unknown error')}")
        
        return jsonify(response_data), status_code

    except Exception as e:
        step_duration = time.time() - step_start_time
        print(f"[SERVER] ❌ [@server_restart_routes:prepareDubbingAudio] EXCEPTION after {step_duration:.1f}s: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Audio preparation failed: {str(e)}'
        }), 500


@server_restart_bp.route('/generateEdgeSpeech', methods=['POST'])
def generate_edge_speech():
    """Step 2: Generate Edge-TTS speech ~3-5s"""
    import time
    step_start_time = time.time()
    
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')
        video_id = request_data.get('video_id')
        target_language = request_data.get('target_language', 'es')
        existing_transcript = request_data.get('existing_transcript', '')

        print(f"[SERVER] 🤖 [@server_restart_routes:generateEdgeSpeech] Step 2 starting for {target_language}")

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400
        if not existing_transcript:
            return jsonify({'success': False, 'error': 'Transcript required for speech generation'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/generateEdgeSpeech',
            'POST',
            request_data,
            {'device_id': device_id, 'video_id': video_id, 'target_language': target_language, 'existing_transcript': existing_transcript},
            timeout=60  # 1 minute for Edge-TTS generation
        )
        
        step_duration = time.time() - step_start_time
        
        if response_data.get('success'):
            print(f"[SERVER] ✅ [@server_restart_routes:generateEdgeSpeech] Step 2 completed in {step_duration:.1f}s")
        else:
            print(f"[SERVER] ❌ [@server_restart_routes:generateEdgeSpeech] Step 2 failed after {step_duration:.1f}s: {response_data.get('error', 'unknown error')}")
        
        return jsonify(response_data), status_code

    except Exception as e:
        step_duration = time.time() - step_start_time
        print(f"[SERVER] ❌ [@server_restart_routes:generateEdgeSpeech] EXCEPTION after {step_duration:.1f}s: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Edge-TTS generation failed: {str(e)}'
        }), 500

@server_restart_bp.route('/createDubbedVideo', methods=['POST'])
def create_dubbed_video():
    """Step 3: Create final dubbed video ~5-8s"""
    import time
    step_start_time = time.time()
    
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')
        video_id = request_data.get('video_id')
        target_language = request_data.get('target_language', 'es')
        voice_choice = request_data.get('voice_choice', 'edge')

        print(f"[SERVER] 🎬 [@server_restart_routes:createDubbedVideo] Step 3 starting with {voice_choice} voice")

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/createDubbedVideo',
            'POST',
            request_data,
            {'device_id': device_id, 'video_id': video_id, 'target_language': target_language, 'voice_choice': voice_choice},
            timeout=60  # 1 minute for video creation
        )
        
        step_duration = time.time() - step_start_time
        
        if response_data.get('success'):
            print(f"[SERVER] ✅ [@server_restart_routes:createDubbedVideo] Step 3 completed in {step_duration:.1f}s")
        else:
            print(f"[SERVER] ❌ [@server_restart_routes:createDubbedVideo] Step 3 failed after {step_duration:.1f}s: {response_data.get('error', 'unknown error')}")
        
        return jsonify(response_data), status_code

    except Exception as e:
        step_duration = time.time() - step_start_time
        print(f"[SERVER] ❌ [@server_restart_routes:createDubbedVideo] EXCEPTION after {step_duration:.1f}s: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Video creation failed: {str(e)}'
        }), 500

@server_restart_bp.route('/createDubbedVideoFast', methods=['POST'])
def create_dubbed_video_fast():
    """NEW: Fast 2-step dubbed video creation without Demucs ~5-8s"""
    import time
    step_start_time = time.time()
    
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')
        video_id = request_data.get('video_id')
        target_language = request_data.get('target_language', 'es')
        existing_transcript = request_data.get('existing_transcript', '')

        print(f"[SERVER] ⚡ [@server_restart_routes:createDubbedVideoFast] Fast dubbing starting for {target_language}")

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400
        if not existing_transcript:
            return jsonify({'success': False, 'error': 'Transcript required for fast dubbing'}), 400

        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/createDubbedVideoFast',
            'POST',
            request_data,
            {'device_id': device_id, 'video_id': video_id, 'target_language': target_language, 'existing_transcript': existing_transcript},
            timeout=30  # 30 seconds for fast dubbing
        )
        
        step_duration = time.time() - step_start_time
        
        if response_data.get('success'):
            print(f"[SERVER] ✅ [@server_restart_routes:createDubbedVideoFast] Fast dubbing completed in {step_duration:.1f}s")
        else:
            print(f"[SERVER] ❌ [@server_restart_routes:createDubbedVideoFast] Fast dubbing failed after {step_duration:.1f}s: {response_data.get('error', 'unknown error')}")
        
        return jsonify(response_data), status_code

    except Exception as e:
        step_duration = time.time() - step_start_time
        print(f"[SERVER] ❌ [@server_restart_routes:createDubbedVideoFast] EXCEPTION after {step_duration:.1f}s: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Fast dubbing failed: {str(e)}'
        }), 500

@server_restart_bp.route('/adjustAudioTiming', methods=['POST'])
def adjust_audio_timing():
    """Adjust audio timing for existing restart video"""
    import time
    timing_start_time = time.time()
    
    try:
        request_data = request.get_json() or {}
        host = request_data.get('host')
        device_id = request_data.get('device_id', 'device1')
        video_url = request_data.get('video_url')
        timing_offset_ms = request_data.get('timing_offset_ms', 0)
        language = request_data.get('language', 'original')
        
        # Optional component paths from frontend
        silent_video_path = request_data.get('silent_video_path')
        background_audio_path = request_data.get('background_audio_path')
        vocals_path = request_data.get('vocals_path')

        print(f"[SERVER] 🎵 [@server_restart_routes:adjustAudioTiming] Starting timing adjustment: {timing_offset_ms:+d}ms for {language}")

        if not host:
            return jsonify({'success': False, 'error': 'Host required'}), 400
        if not video_url:
            return jsonify({'success': False, 'error': 'Video URL required'}), 400
        if timing_offset_ms == 0:
            return jsonify({'success': False, 'error': 'Timing offset cannot be 0'}), 400

        print(f"[SERVER] 🔄 [@server_restart_routes:adjustAudioTiming] Proxying to host {host.get('host_name', 'unknown')} endpoint: /host/restart/adjustAudioTiming")

        # Include component paths in proxy data
        proxy_params = {
            'device_id': device_id, 
            'video_url': video_url, 
            'timing_offset_ms': timing_offset_ms, 
            'language': language
        }
        
        # Add component paths if provided
        if silent_video_path:
            proxy_params['silent_video_path'] = silent_video_path
        if background_audio_path:
            proxy_params['background_audio_path'] = background_audio_path
        if vocals_path:
            proxy_params['vocals_path'] = vocals_path
        
        response_data, status_code = proxy_to_host_with_params(
            '/host/restart/adjustAudioTiming',
            'POST',
            request_data,
            proxy_params,
            timeout=60  # 1 minute for timing adjustment
        )
        
        timing_duration = time.time() - timing_start_time
        
        if response_data.get('success'):
            print(f"[SERVER] ✅ [@server_restart_routes:adjustAudioTiming] Audio timing adjustment ({timing_offset_ms:+d}ms) completed in {timing_duration:.1f}s")
        else:
            print(f"[SERVER] ❌ [@server_restart_routes:adjustAudioTiming] Timing adjustment failed after {timing_duration:.1f}s: {response_data.get('error', 'unknown error')}")
        
        return jsonify(response_data), status_code

    except Exception as e:
        timing_duration = time.time() - timing_start_time
        print(f"[SERVER] ❌ [@server_restart_routes:adjustAudioTiming] EXCEPTION after {timing_duration:.1f}s: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Audio timing adjustment failed: {str(e)}'
        }), 500
