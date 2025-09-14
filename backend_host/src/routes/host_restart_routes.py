"""
Host Restart Video Routes

Restart video system endpoints for video generation and AI analysis.
"""

from flask import Blueprint, request, jsonify
from utils.host_utils import get_controller, get_device_by_id
import os
import threading
import time
import signal
from contextlib import contextmanager
from typing import Dict

host_restart_bp = Blueprint('host_restart', __name__, url_prefix='/host/restart')

# Request deduplication tracking
_active_requests: Dict[str, float] = {}
_request_lock = threading.Lock()

def _get_request_key(endpoint: str, device_id: str, video_id: str) -> str:
    return f"{endpoint}:{device_id}:{video_id}"

def _is_request_active(request_key: str) -> bool:
    with _request_lock:
        if request_key in _active_requests:
            if time.time() - _active_requests[request_key] > 60:
                del _active_requests[request_key]
                return False
            return True
        return False

def _mark_request_active(request_key: str):
    with _request_lock:
        _active_requests[request_key] = time.time()

def _mark_request_complete(request_key: str):
    with _request_lock:
        _active_requests.pop(request_key, None)

@contextmanager
def timeout(duration):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {duration} seconds")
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    try:
        yield
    finally:
        signal.alarm(0)

@host_restart_bp.route('/generateVideo', methods=['POST'])
def generate_restart_video():
    """Generate video only - fast response"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        duration_seconds = data.get('duration_seconds', 10)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        result = av_controller.generateRestartVideoFast(
            duration_seconds=duration_seconds,
            processing_time=0.0
        )
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'video_url': result.get('video_url'),
                'video_id': result.get('analysis_data', {}).get('video_id'),
                'screenshot_urls': result.get('analysis_data', {}).get('screenshot_urls', []),
                'segment_count': result.get('analysis_data', {}).get('segment_count', 0)
            })
        else:
            return jsonify({'success': False, 'error': 'Video generation failed'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_restart_bp.route('/generateVideoOnly', methods=['POST'])
def generate_restart_video_only():
    """Generate video only - fast response"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        duration_seconds = data.get('duration_seconds', 10)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        result = av_controller.generateRestartVideoOnly(duration_seconds)
        return jsonify(result) if result else jsonify({'success': False, 'error': 'Video generation failed'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_restart_bp.route('/analyzeAudio', methods=['POST'])
def analyze_restart_audio():
    """Analyze audio transcript"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        segment_files = data.get('segment_files')
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        
        request_key = _get_request_key('analyzeRestartAudio', device_id, video_id)
        if _is_request_active(request_key):
            return jsonify({
                'success': False, 
                'error': 'Audio analysis already in progress for this video',
                'code': 'DUPLICATE_REQUEST'
            }), 409
        
        _mark_request_active(request_key)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        with timeout(25):
            result = av_controller.analyzeRestartAudio(video_id, segment_files)
            
        if result and result.get('success'):
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Audio analysis failed') if result else 'Audio analysis failed'
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except TimeoutError as e:
        return jsonify({'success': False, 'error': str(e)}), 408
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'request_key' in locals():
            _mark_request_complete(request_key)

@host_restart_bp.route('/analyzeSubtitles', methods=['POST'])
def analyze_restart_subtitles():
    """Analyze subtitles"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        screenshot_urls = data.get('screenshot_urls', [])
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        if not screenshot_urls:
            return jsonify({'success': False, 'error': 'screenshot_urls are required'}), 400
        
        request_key = _get_request_key('analyzeRestartSubtitles', device_id, video_id)
        if _is_request_active(request_key):
            return jsonify({
                'success': False, 
                'error': 'Subtitle analysis already in progress for this video',
                'code': 'DUPLICATE_REQUEST'
            }), 409
        
        _mark_request_active(request_key)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        with timeout(25):
            result = av_controller.analyzeRestartSubtitles(video_id, screenshot_urls)
            
        if result and result.get('success'):
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Subtitle analysis failed') if result else 'Subtitle analysis failed'
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except TimeoutError as e:
        return jsonify({'success': False, 'error': str(e)}), 408
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'request_key' in locals():
            _mark_request_complete(request_key)

@host_restart_bp.route('/analyzeSummary', methods=['POST'])
def analyze_restart_summary():
    """Analyze video summary"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        screenshot_urls = data.get('screenshot_urls', [])
        video_url = data.get('video_url')
        previous_analysis_data = data.get('analysis_data', {})
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        if not screenshot_urls:
            return jsonify({'success': False, 'error': 'screenshot_urls are required'}), 400
        
        request_key = _get_request_key('analyzeRestartSummary', device_id, video_id)
        if _is_request_active(request_key):
            return jsonify({
                'success': False, 
                'error': 'Summary analysis already in progress for this video',
                'code': 'DUPLICATE_REQUEST'
            }), 409
        
        _mark_request_active(request_key)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        with timeout(25):
            result = av_controller.analyzeRestartSummary(video_id, screenshot_urls)
            
        if result and result.get('success'):
            try:
                from shared.lib.utils.report_generation import generate_and_upload_restart_report
                from utils.host_utils import get_host_instance
                
                host = get_host_instance()
                host_info = {'host_name': host.host_name}
                device_info = {
                    'device_name': av_controller.device_name,
                    'device_model': getattr(av_controller, 'device_model', 'Unknown'),
                    'device_id': device_id
                }
                
                if not video_url:
                    video_url = f"{av_controller.video_stream_path}/restart_video.mp4"
                
                local_video_path = os.path.join(av_controller.video_capture_path, "restart_video.mp4")
                
                analysis_data = {
                    'audio_analysis': previous_analysis_data.get('audio_analysis', {}),
                    'subtitle_analysis': previous_analysis_data.get('subtitle_analysis', {}),
                    'video_analysis': result.get('video_analysis', {}),
                }
                
                report_result = generate_and_upload_restart_report(
                    host_info=host_info,
                    device_info=device_info,
                    video_url=video_url,
                    analysis_data=analysis_data,
                    processing_time=0.0,
                    local_video_path=local_video_path if os.path.exists(local_video_path) else None
                )
                
                if report_result.get('success'):
                    result['report_url'] = report_result['report_url']
                    result['report_path'] = report_result['report_path']
                    
            except Exception:
                pass
            
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Summary analysis failed') if result else 'Summary analysis failed'
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except TimeoutError as e:
        return jsonify({'success': False, 'error': str(e)}), 408
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'request_key' in locals():
            _mark_request_complete(request_key)

@host_restart_bp.route('/analyzeComplete', methods=['POST'])
def analyze_restart_complete():
    """Combined restart analysis: subtitles + summary in single call"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        screenshot_urls = data.get('screenshot_urls', [])
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        if not screenshot_urls:
            return jsonify({'success': False, 'error': 'screenshot_urls are required'}), 400
        
        request_key = _get_request_key('analyzeRestartComplete', device_id, video_id)
        if _is_request_active(request_key):
            return jsonify({
                'success': False, 
                'error': 'Combined analysis already in progress for this video',
                'code': 'DUPLICATE_REQUEST'
            }), 409
        
        _mark_request_active(request_key)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        with timeout(45):
            result = av_controller.analyzeRestartComplete(video_id, screenshot_urls)
            
        if result and result.get('success'):
            return jsonify(result), 200
        else:
            error_msg = result.get('error', 'Combined analysis failed') if result else 'Combined analysis failed'
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except TimeoutError as e:
        return jsonify({'success': False, 'error': str(e)}), 408
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'request_key' in locals():
            _mark_request_complete(request_key)

@host_restart_bp.route('/generateReport', methods=['POST'])
def generate_restart_report():
    """Generate report with all analysis data collected from frontend"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_url = data.get('video_url')
        analysis_data = data.get('analysis_data', {})
        
        if not video_url:
            return jsonify({'success': False, 'error': 'video_url is required'}), 400
        if not analysis_data:
            return jsonify({'success': False, 'error': 'analysis_data is required'}), 400
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        from shared.lib.utils.report_generation import generate_and_upload_restart_report
        from utils.host_utils import get_host_instance
        
        host = get_host_instance()
        host_info = {'host_name': host.host_name}
        device_info = {
            'device_name': av_controller.device_name,
            'device_model': getattr(av_controller, 'device_model', 'Unknown'),
            'device_id': device_id
        }
        
        local_video_path = os.path.join(av_controller.video_capture_path, "restart_video.mp4")
        
        report_result = generate_and_upload_restart_report(
            host_info=host_info,
            device_info=device_info,
            video_url=video_url,
            analysis_data=analysis_data,
            processing_time=0.0,
            local_video_path=local_video_path if os.path.exists(local_video_path) else None
        )
        
        if report_result.get('success'):
            return jsonify({
                'success': True,
                'report_url': report_result['report_url'],
                'report_path': report_result['report_path']
            })
        else:
            error_msg = report_result.get('error', 'Report generation failed')
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_restart_bp.route('/analyzeVideo', methods=['POST'])
def analyze_restart_video():
    """Async AI analysis for restart video - subtitle detection + video descriptions"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        screenshot_urls = data.get('screenshot_urls', [])
        duration_seconds = data.get('duration_seconds', 10)
        segment_count = data.get('segment_count')
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        if not screenshot_urls:
            return jsonify({'success': False, 'error': 'screenshot_urls are required'}), 400
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        start_time = time.time()
        result = av_controller.analyzeRestartComplete(
            video_id=video_id, 
            screenshot_urls=screenshot_urls
        )
        
        processing_time = time.time() - start_time
        
        if result:
            result.update({
                'processing_time_seconds': round(processing_time, 2),
                'device_id': device_id,
                'message': f'Successfully completed async AI analysis for video {video_id}'
            })
            
            try:
                from shared.lib.utils.report_generation import generate_and_upload_restart_report
                from utils.host_utils import get_host_instance
                
                host = get_host_instance()
                host_info = {'host_name': host.host_name}
                device_info = {
                    'device_name': av_controller.device_name,
                    'device_model': getattr(av_controller, 'device_model', 'Unknown'),
                    'device_id': device_id
                }
                
                video_url = result.get('video_url', '')
                if not video_url:
                    video_url = f"{av_controller.video_stream_path}/restart_video.mp4"
                
                local_video_path = os.path.join(av_controller.video_capture_path, "restart_video.mp4")
                
                report_result = generate_and_upload_restart_report(
                    host_info=host_info,
                    device_info=device_info,
                    video_url=video_url,
                    analysis_data=result.get('analysis_data', {}),
                    processing_time=processing_time,
                    local_video_path=local_video_path if os.path.exists(local_video_path) else None
                )
                
                if report_result.get('success'):
                    result['report_url'] = report_result['report_url']
                    result['report_path'] = report_result['report_path']
                    
            except Exception:
                pass
            
            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': 'Failed to perform async AI analysis'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
