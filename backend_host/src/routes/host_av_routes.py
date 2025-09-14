"""
Host Audio/Video Routes

This module contains the host-specific audio/video API endpoints for:
- AV controller connection management
- Video capture control
- Screenshot capture

These endpoints run on the host and use the host's own stored device object.
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from utils.host_utils import get_controller, get_device_by_id
import os
import threading
import time
from typing import Dict, Set

# Create blueprint
host_av_bp = Blueprint('host_av', __name__, url_prefix='/host/av')

# Request deduplication tracking (prevents duplicate AI analysis calls)
_active_requests: Dict[str, float] = {}  # request_key -> start_time
_request_lock = threading.Lock()

def _get_request_key(endpoint: str, device_id: str, video_id: str) -> str:
    """Generate unique key for request deduplication"""
    return f"{endpoint}:{device_id}:{video_id}"

def _is_request_active(request_key: str) -> bool:
    """Check if request is already being processed"""
    with _request_lock:
        if request_key in _active_requests:
            # Check if request is stale (older than 60 seconds)
            if time.time() - _active_requests[request_key] > 60:
                del _active_requests[request_key]
                return False
            return True
        return False

def _mark_request_active(request_key: str):
    """Mark request as active"""
    with _request_lock:
        _active_requests[request_key] = time.time()

def _mark_request_complete(request_key: str):
    """Mark request as complete"""
    with _request_lock:
        _active_requests.pop(request_key, None)

@host_av_bp.route('/connect', methods=['POST'])
def connect():
    """Connect to AV controller using new architecture"""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_av:connect] Connecting to AV controller for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:connect] Using AV controller: {type(av_controller).__name__}")
        
        # Connect to controller
        connect_result = av_controller.connect()
        
        if connect_result:
            # Get status after connection
            status = av_controller.get_status()
            return jsonify({
                'success': True,
                'connected': True,
                'device_id': device_id,
                'status': status
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to connect to AV controller'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from AV controller using new architecture"""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_av:disconnect] Disconnecting AV controller for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:disconnect] Using AV controller: {type(av_controller).__name__}")
        
        # Disconnect from controller
        disconnect_result = av_controller.disconnect()
        
        return jsonify({
            'success': disconnect_result,
            'connected': False,
            'streaming': False,
            'device_id': device_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/status', methods=['GET'])
def get_status():
    """Get AV controller status using new architecture"""
    try:
        # Get device_id from query params (defaults to device1)
        device_id = request.args.get('device_id', 'device1')
        
        print(f"[@route:host_av:status] Getting AV controller status for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:status] Using AV controller: {type(av_controller).__name__}")
        
        # Get controller status
        status = av_controller.get_status()
        
        return jsonify({
            'success': True,
            'status': status,
            'device_id': device_id,
            'timestamp': __import__('time').time()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/restartStream', methods=['POST'])
def restart_stream():
    """Restart stream service using new architecture"""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_av:restart_stream] Restarting stream for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:restart_stream] Using AV controller: {type(av_controller).__name__}")
        
        # Restart stream service
        restart_result = av_controller.restart_stream()
        
        if restart_result:
            # Get updated status after restart
            status = av_controller.get_status()
            return jsonify({
                'success': True,
                'restarted': True,
                'status': status,
                'device_id': device_id,
                'message': 'Stream service restarted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to restart stream service'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/takeControl', methods=['POST'])
def take_control():
    """Take control of AV system using new architecture"""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_av:take_control] Taking control of AV system for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:take_control] Using AV controller: {type(av_controller).__name__}")
        
        # Take control of AV system
        control_result = av_controller.take_control()
        
        # Add device_id to result if it's a dict
        if isinstance(control_result, dict):
            control_result['device_id'] = device_id
            return jsonify(control_result)
        else:
            return jsonify({
                'success': control_result,
                'device_id': device_id
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/getStreamUrl', methods=['GET'])
def get_stream_url():
    """Get stream URL from AV controller using host URL building"""
    try:
        # Get device_id from query params (defaults to device1)
        device_id = request.args.get('device_id', 'device1')
        
        print(f"[@route:host_av:stream_url] Getting stream URL for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:stream_url] Using AV controller: {type(av_controller).__name__}")
        
        # Use URL building utilities
        from utils.build_url_utils import buildStreamUrlForDevice
        from utils.host_utils import get_host_instance as get_host
        
        host = get_host()
        stream_url = buildStreamUrlForDevice(host.to_dict(), device_id)
        
        print(f"[@route:host_av:stream_url] Built stream URL: {stream_url}")
        
        return jsonify({
            'success': True,
            'stream_url': stream_url,
            'device_id': device_id
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/takeScreenshot', methods=['POST'])
def take_screenshot():
    """Take temporary screenshot to nginx folder using new architecture"""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_av:take_screenshot] Taking screenshot for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:take_screenshot] Using AV controller: {type(av_controller).__name__}")
        print(f"[@route:host_av:take_screenshot] Controller details - Source: {getattr(av_controller, 'capture_source', 'unknown')}, Path: {getattr(av_controller, 'video_capture_path', 'unknown')}")
        
        # Take screenshot using controller - returns local file path
        screenshot_path = av_controller.take_screenshot()
        
        if not screenshot_path:
            print(f"[@route:host_av:take_screenshot] FAILURE - Controller returned None for screenshot")
            return jsonify({
                'success': False,
                'error': 'Failed to take temporary screenshot - controller returned None'
            }), 500
        
        print(f"[@route:host_av:take_screenshot] Screenshot path from controller: {screenshot_path}")
        
        # Wait 500ms to ensure file is fully written to disk
        import time
        time.sleep(0.5)
        print(f"[@route:host_av:take_screenshot] Waited 500ms for file to be fully written")
        
        # Use URL building utilities
        from utils.build_url_utils import buildCaptureUrlFromPath, buildClientImageUrl
        from utils.host_utils import get_host_instance as get_host
        
        try:
            host = get_host()
            screenshot_url = buildCaptureUrlFromPath(host.to_dict(), screenshot_path, device_id)
            
            # Process URL for client consumption
            client_screenshot_url = buildClientImageUrl(screenshot_url)
            
            print(f"[@route:host_av:take_screenshot] Built screenshot URL: {screenshot_url}")
            print(f"[@route:host_av:take_screenshot] Client screenshot URL: {client_screenshot_url}")
            
            return jsonify({
                'success': True,
                'screenshot_url': client_screenshot_url,
                'device_id': device_id
            })
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    except Exception as e:
        print(f"[@route:host_av:take_screenshot] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/saveScreenshot', methods=['POST'])
def save_screenshot():
    """Take screenshot and upload to R2 for navigation documentation"""
    try:
        # Get request data for device_id and other parameters
        request_data = request.get_json() or {}
        device_id = request_data.get('device_id', 'device1')
        
        print(f"[@route:host_av:save_screenshot] Saving screenshot for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:save_screenshot] Using AV controller: {type(av_controller).__name__}")
        
        # Get other parameters from request data
        filename = request_data.get('filename')
        device_model = request_data.get('device_model', 'android_mobile')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'Filename is required for saving screenshot'
            }), 400
        
        print(f"[@route:host_av:save_screenshot] Saving screenshot with filename: {filename}")
        print(f"[@route:host_av:save_screenshot] Using device model: {device_model}")
        
        # Save screenshot using controller (returns local path)
        local_screenshot_path = av_controller.save_screenshot(filename)
        
        if not local_screenshot_path:
            return jsonify({
                'success': False,
                'error': 'Failed to take screenshot'
            }), 500
        
        print(f"[@route:host_av:save_screenshot] Screenshot saved locally at: {local_screenshot_path}")
        
        # Check if local screenshot file exists
        if not os.path.exists(local_screenshot_path):
            return jsonify({
                'success': False,
                'error': f'Screenshot file not found: {local_screenshot_path}'
            }), 500
        
        # Upload to R2 using navigation upload function
        try:
            from utils.cloudflare_utils import upload_navigation_screenshot
            
            # Create the target filename for R2 (use filename with .jpg extension)
            r2_filename = f"{filename}.jpg"
            
            print(f"[@route:host_av:save_screenshot] Uploading screenshot to R2: {r2_filename}")
            print(f"[@route:host_av:save_screenshot] Source file: {local_screenshot_path}")
            print(f"[@route:host_av:save_screenshot] Target path: navigation/{device_model}/{r2_filename}")
            
            # Upload to R2 using the navigation upload function (uploads to navigation/ folder)
            upload_result = upload_navigation_screenshot(local_screenshot_path, device_model, r2_filename)
            
            if not upload_result.get('success'):
                print(f"[@route:host_av:save_screenshot] R2 upload failed: {upload_result.get('error')}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to upload to R2: {upload_result.get("error")}'
                }), 500
            
            r2_url = upload_result.get('url')
            print(f"[@route:host_av:save_screenshot] Successfully uploaded screenshot to R2: {r2_url}")
            
            # Screenshots are stored in the tree nodes, no database save needed
            print(f"[@route:host_av:save_screenshot] Screenshot uploaded to R2 successfully")
            
            # Process URLs for client consumption
            from utils.build_url_utils import buildClientImageUrl
            client_r2_url = buildClientImageUrl(r2_url)
            client_local_path = buildClientImageUrl(local_screenshot_path)
            
            return jsonify({
                'success': True,
                'screenshot_url': client_r2_url,  # R2 URL for permanent storage
                'screenshot_path': client_local_path, 
                'device_id': device_id
            })
            
        except Exception as upload_error:
            print(f"[@route:host_av:save_screenshot] Upload error: {str(upload_error)}")
            return jsonify({
                'success': False,
                'error': f'Upload to R2 failed: {str(upload_error)}'
            }), 500
            
    except Exception as e:
        print(f"[@route:host_av:save_screenshot] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/generateRestartVideo', methods=['POST'])
def generate_restart_video():
    """Generate video only - fast response (new 4-call architecture)"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        duration_seconds = data.get('duration_seconds', 10)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        # Use the original working method but extract only what we need for 4-call architecture
        result = av_controller.generateRestartVideoFast(
            duration_seconds=duration_seconds,
            processing_time=0.0
        )
        
        if result and result.get('success'):
            # Extract only the video generation parts for the 4-call architecture
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

@host_av_bp.route('/generateRestartVideoOnly', methods=['POST'])
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

@host_av_bp.route('/analyzeRestartAudio', methods=['POST'])
def analyze_restart_audio():
    """Analyze audio transcript"""
    import signal
    from contextlib import contextmanager
    
    @contextmanager
    def timeout(duration):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Audio analysis timed out after {duration} seconds")
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(duration)
        try:
            yield
        finally:
            signal.alarm(0)
    
    try:
        print(f"[@route:analyzeRestartAudio] Starting audio analysis")
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        
        # Deduplication check
        request_key = _get_request_key('analyzeRestartAudio', device_id, video_id)
        if _is_request_active(request_key):
            print(f"[@route:analyzeRestartAudio] Duplicate request detected, returning 409")
            return jsonify({
                'success': False, 
                'error': 'Audio analysis already in progress for this video',
                'code': 'DUPLICATE_REQUEST'
            }), 409
        
        _mark_request_active(request_key)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        with timeout(25):  # 25s max (under Flask 30s limit)
            result = av_controller.analyzeRestartAudio(video_id)
            
        if result and result.get('success'):
            print(f"[@route:analyzeRestartAudio] Audio analysis completed successfully")
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Audio analysis failed') if result else 'Audio analysis failed'
            print(f"[@route:analyzeRestartAudio] Audio analysis failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except TimeoutError as e:
        print(f"[@route:analyzeRestartAudio] Timeout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 408
    except Exception as e:
        print(f"[@route:analyzeRestartAudio] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Always clean up request tracking
        if 'request_key' in locals():
            _mark_request_complete(request_key)

@host_av_bp.route('/analyzeRestartSubtitles', methods=['POST'])
def analyze_restart_subtitles():
    """Analyze subtitles"""
    import signal
    from contextlib import contextmanager
    
    @contextmanager
    def timeout(duration):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Subtitle analysis timed out after {duration} seconds")
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(duration)
        try:
            yield
        finally:
            signal.alarm(0)
    
    try:
        print(f"[@route:analyzeRestartSubtitles] Starting subtitle analysis")
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        screenshot_urls = data.get('screenshot_urls', [])
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        if not screenshot_urls:
            return jsonify({'success': False, 'error': 'screenshot_urls are required'}), 400
        
        # Deduplication check
        request_key = _get_request_key('analyzeRestartSubtitles', device_id, video_id)
        if _is_request_active(request_key):
            print(f"[@route:analyzeRestartSubtitles] Duplicate request detected, returning 409")
            return jsonify({
                'success': False, 
                'error': 'Subtitle analysis already in progress for this video',
                'code': 'DUPLICATE_REQUEST'
            }), 409
        
        _mark_request_active(request_key)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        with timeout(25):  # 25s max (under Flask 30s limit)
            result = av_controller.analyzeRestartSubtitles(video_id, screenshot_urls)
            
        if result and result.get('success'):
            print(f"[@route:analyzeRestartSubtitles] Subtitle analysis completed successfully")
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Subtitle analysis failed') if result else 'Subtitle analysis failed'
            print(f"[@route:analyzeRestartSubtitles] Subtitle analysis failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except TimeoutError as e:
        print(f"[@route:analyzeRestartSubtitles] Timeout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 408
    except Exception as e:
        print(f"[@route:analyzeRestartSubtitles] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Always clean up request tracking
        if 'request_key' in locals():
            _mark_request_complete(request_key)

@host_av_bp.route('/analyzeRestartSummary', methods=['POST'])
def analyze_restart_summary():
    """Analyze video summary"""
    import signal
    from contextlib import contextmanager
    
    @contextmanager
    def timeout(duration):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Summary analysis timed out after {duration} seconds")
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(duration)
        try:
            yield
        finally:
            signal.alarm(0)
    
    try:
        print(f"[@route:analyzeRestartSummary] Starting summary analysis")
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        screenshot_urls = data.get('screenshot_urls', [])
        video_url = data.get('video_url')  # For report generation
        previous_analysis_data = data.get('analysis_data', {})  # Previous analysis results
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        if not screenshot_urls:
            return jsonify({'success': False, 'error': 'screenshot_urls are required'}), 400
        
        # Deduplication check
        request_key = _get_request_key('analyzeRestartSummary', device_id, video_id)
        if _is_request_active(request_key):
            print(f"[@route:analyzeRestartSummary] Duplicate request detected, returning 409")
            return jsonify({
                'success': False, 
                'error': 'Summary analysis already in progress for this video',
                'code': 'DUPLICATE_REQUEST'
            }), 409
        
        _mark_request_active(request_key)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        with timeout(25):  # 25s max (under Flask 30s limit)
            result = av_controller.analyzeRestartSummary(video_id, screenshot_urls)
            
        if result and result.get('success'):
            print(f"[@route:analyzeRestartSummary] Summary analysis completed successfully")
            
            # Generate report after summary analysis is complete
            try:
                from shared.lib.utils.report_generation import generate_and_upload_restart_report
                from utils.host_utils import get_host_instance
                import os
                import time
                
                # Get host and device info
                host = get_host_instance()
                host_info = {'host_name': host.host_name}
                device_info = {
                    'device_name': av_controller.device_name,
                    'device_model': getattr(av_controller, 'device_model', 'Unknown'),
                    'device_id': device_id
                }
                
                # Use video URL from request if provided, otherwise reconstruct
                if not video_url:
                    video_url = f"{av_controller.video_stream_path}/restart_video.mp4"
                
                # Get local video path for R2 upload
                local_video_path = os.path.join(av_controller.video_capture_path, "restart_video.mp4")
                
                # Prepare complete analysis data including previous results and current summary
                analysis_data = {
                    'audio_analysis': previous_analysis_data.get('audio_analysis', {}),
                    'subtitle_analysis': previous_analysis_data.get('subtitle_analysis', {}),
                    'video_analysis': result.get('video_analysis', {}),
                }
                
                # Generate complete report
                report_result = generate_and_upload_restart_report(
                    host_info=host_info,
                    device_info=device_info,
                    video_url=video_url,
                    analysis_data=analysis_data,
                    processing_time=0.0,  # Will be calculated by the report function
                    local_video_path=local_video_path if os.path.exists(local_video_path) else None
                )
                
                if report_result.get('success'):
                    result['report_url'] = report_result['report_url']
                    result['report_path'] = report_result['report_path']
                    print(f"[@route:analyzeRestartSummary] Report generation completed: {report_result['report_url']}")
                else:
                    print(f"[@route:analyzeRestartSummary] Report generation failed: {report_result.get('error')}")
                    # Continue without report if generation fails
                    
            except Exception as e:
                print(f"[@route:analyzeRestartSummary] Report generation error: {e}")
                # Continue without report if generation fails
            
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Summary analysis failed') if result else 'Summary analysis failed'
            print(f"[@route:analyzeRestartSummary] Summary analysis failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except TimeoutError as e:
        print(f"[@route:analyzeRestartSummary] Timeout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 408
    except Exception as e:
        print(f"[@route:analyzeRestartSummary] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Always clean up request tracking
        if 'request_key' in locals():
            _mark_request_complete(request_key)

@host_av_bp.route('/analyzeRestartComplete', methods=['POST'])
def analyze_restart_complete():
    """Combined restart analysis: subtitles + summary in single call"""
    import signal
    from contextlib import contextmanager
    
    @contextmanager
    def timeout(duration):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Combined analysis timed out after {duration} seconds")
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(duration)
        try:
            yield
        finally:
            signal.alarm(0)
    
    try:
        print(f"[@route:analyzeRestartComplete] Starting combined analysis")
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        screenshot_urls = data.get('screenshot_urls', [])
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id is required'}), 400
        if not screenshot_urls:
            return jsonify({'success': False, 'error': 'screenshot_urls are required'}), 400
        
        # Deduplication check
        request_key = _get_request_key('analyzeRestartComplete', device_id, video_id)
        if _is_request_active(request_key):
            print(f"[@route:analyzeRestartComplete] Duplicate request detected, returning 409")
            return jsonify({
                'success': False, 
                'error': 'Combined analysis already in progress for this video',
                'code': 'DUPLICATE_REQUEST'
            }), 409
        
        _mark_request_active(request_key)
        
        av_controller = get_controller(device_id, 'av')
        if not av_controller:
            return jsonify({'success': False, 'error': f'No AV controller for {device_id}'}), 404
        
        with timeout(45):  # 45s max for combined analysis (longer than individual calls)
            result = av_controller.analyzeRestartComplete(video_id, screenshot_urls)
            
        if result and result.get('success'):
            print(f"[@route:analyzeRestartComplete] Combined analysis completed successfully")
            return jsonify(result), 200
        else:
            error_msg = result.get('error', 'Combined analysis failed') if result else 'Combined analysis failed'
            print(f"[@route:analyzeRestartComplete] Combined analysis failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except TimeoutError as e:
        print(f"[@route:analyzeRestartComplete] Timeout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 408
    except Exception as e:
        print(f"[@route:analyzeRestartComplete] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'request_key' in locals():
            _mark_request_complete(request_key)

@host_av_bp.route('/generateRestartReport', methods=['POST'])
def generate_restart_report():
    """Generate report with all analysis data collected from frontend"""
    try:
        print(f"[@route:generateRestartReport] Starting report generation")
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
        
        # Import report generation utilities
        from shared.lib.utils.report_generation import generate_and_upload_restart_report
        from utils.host_utils import get_host_instance
        import os
        
        # Get host and device info
        host = get_host_instance()
        host_info = {'host_name': host.host_name}
        device_info = {
            'device_name': av_controller.device_name,
            'device_model': getattr(av_controller, 'device_model', 'Unknown'),
            'device_id': device_id
        }
        
        # Get local video path for R2 upload
        local_video_path = os.path.join(av_controller.video_capture_path, "restart_video.mp4")
        
        # Generate report with complete analysis data from frontend
        report_result = generate_and_upload_restart_report(
            host_info=host_info,
            device_info=device_info,
            video_url=video_url,
            analysis_data=analysis_data,
            processing_time=0.0,
            local_video_path=local_video_path if os.path.exists(local_video_path) else None
        )
        
        if report_result.get('success'):
            print(f"[@route:generateRestartReport] Report generated successfully: {report_result['report_url']}")
            return jsonify({
                'success': True,
                'report_url': report_result['report_url'],
                'report_path': report_result['report_path']
            })
        else:
            error_msg = report_result.get('error', 'Report generation failed')
            print(f"[@route:generateRestartReport] Report generation failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except Exception as e:
        print(f"[@route:generateRestartReport] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@host_av_bp.route('/analyzeRestartVideo', methods=['POST'])
def analyze_restart_video():
    """Async AI analysis for restart video - subtitle detection + video descriptions"""
    try:
        print("[@route:host_av:analyze_restart_video] Processing async AI analysis request")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        video_id = data.get('video_id')
        screenshot_urls = data.get('screenshot_urls', [])
        duration_seconds = data.get('duration_seconds', 10)  # Default to 10 seconds for restart videos
        segment_count = data.get('segment_count')  # Get segment count from request for proper synchronization
        
        if not video_id:
            return jsonify({
                'success': False,
                'error': 'video_id is required'
            }), 400
        
        if not screenshot_urls:
            return jsonify({
                'success': False,
                'error': 'screenshot_urls are required'
            }), 400
        
        print(f"[@route:host_av:analyze_restart_video] Video ID: {video_id}")
        print(f"[@route:host_av:analyze_restart_video] Duration: {duration_seconds}s")
        print(f"[@route:host_av:analyze_restart_video] Screenshots: {len(screenshot_urls)} frames")
        print(f"[@route:host_av:analyze_restart_video] Segment count: {segment_count}")
        
        # Get AV controller
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:analyze_restart_video] Using AV controller: {type(av_controller).__name__}")
        
        # Perform async AI analysis
        import time
        start_time = time.time()
        result = av_controller.analyzeRestartVideoAsync(
            video_id=video_id, 
            screenshot_urls=screenshot_urls, 
            duration_seconds=duration_seconds,
            segment_count=segment_count  # Pass segment count for proper synchronization
        )
        
        processing_time = time.time() - start_time
        
        if result:
            # Add processing metadata
            result.update({
                'processing_time_seconds': round(processing_time, 2),
                'device_id': device_id,
                'message': f'Successfully completed async AI analysis for video {video_id}'
            })
            
            # Phase 2: Generate report now that ALL AI analysis is complete
            try:
                from shared.lib.utils.report_utils import generate_and_upload_restart_report
                from shared.lib.utils.host_utils import get_host_instance
                
                # Get host and device info
                host = get_host_instance()
                host_info = {'host_name': host.host_name}
                device_info = {
                    'device_name': av_controller.device_name,
                    'device_model': getattr(av_controller, 'device_model', 'Unknown'),
                    'device_id': device_id
                }
                
                # Get video URL from the analysis result or reconstruct it
                video_url = result.get('video_url', '')
                if not video_url:
                    # Reconstruct video URL if not provided
                    video_url = f"{av_controller.video_stream_path}/restart_video.mp4"
                
                # Get local video path for R2 upload
                import os
                local_video_path = os.path.join(av_controller.video_capture_path, "restart_video.mp4")
                
                # Generate complete report with all analysis data
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
                    print(f"[@cloudflare_utils:upload_restart_report] INFO: Uploaded restart report: {report_result['report_path']}")
                else:
                    print(f"[@route:host_av:analyze_restart_video] Report generation failed: {report_result.get('error')}")
                    
            except Exception as e:
                print(f"[@route:host_av:analyze_restart_video] Report generation error: {e}")
                # Continue without report if generation fails
            
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to perform async AI analysis'
            }), 500
            
    except Exception as e:
        print(f"[@route:host_av:analyze_restart_video] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/startCapture', methods=['POST'])
def start_video_capture():
    """Start video capture using new architecture"""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_av:start_capture] Starting capture for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:start_capture] Using AV controller: {type(av_controller).__name__}")
        
        # Get request data for capture options
        duration = data.get('duration', 60.0)  # Default 60 seconds
        filename = data.get('filename')
        resolution = data.get('resolution')
        fps = data.get('fps')
        
        print(f"[@route:host_av:start_capture] Starting capture with duration: {duration}s")
        
        # Start video capture using controller
        capture_result = av_controller.start_video_capture(
            duration=duration,
            filename=filename,
            resolution=resolution,
            fps=fps
        )
        
        if capture_result:
            # Get session ID if available
            session_id = getattr(av_controller, 'capture_session_id', None)
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'duration': duration,
                'device_id': device_id,
                'message': 'Video capture started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start video capture'
            }), 500
            
    except Exception as e:
        print(f"[@route:host_av:start_capture] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/stopCapture', methods=['POST'])
def stop_video_capture():
    """Stop video capture using new architecture"""
    try:
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_av:stop_capture] Stopping capture for device: {device_id}")
        
        # Get AV controller for the specified device
        av_controller = get_controller(device_id, 'av')
        
        if not av_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No AV controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        print(f"[@route:host_av:stop_capture] Using AV controller: {type(av_controller).__name__}")
        
        # Stop video capture using controller
        stop_result = av_controller.stop_video_capture()
        
        if stop_result:
            return jsonify({
                'success': True,
                'device_id': device_id,
                'message': 'Video capture stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to stop video capture or no active capture session'
            }), 500
            
    except Exception as e:
        print(f"[@route:host_av:stop_capture] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/images/screenshot/<filename>', methods=['GET', 'OPTIONS'])
def serve_screenshot(filename):
    """Serve a screenshot image by filename from host"""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = current_app.response_class()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    try:
        print(f"[@route:host_av:serve_screenshot] Screenshot request for: {filename}")
        
        # Use URL building utilities to resolve screenshot path
        from utils.build_url_utils import resolveCaptureFilePath
        
        try:
            capture_path = resolveCaptureFilePath(filename)
        except ValueError as e:
            print(f"[@route:host_av:serve_screenshot] Invalid filename: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Check if the file exists
        if not os.path.exists(capture_path):
            print(f"[@route:host_av:serve_screenshot] Capture not found: {capture_path}")
            return jsonify({'success': False, 'error': 'Capture not found'}), 404
        
        # Check file size - ensure it's not empty
        file_size = os.path.getsize(capture_path)
        if file_size == 0:
            print(f"[@route:host_av:serve_screenshot] Capture file is empty: {capture_path}")
            return jsonify({'success': False, 'error': 'Capture file is empty'}), 500
        
        print(f"[@route:host_av:serve_screenshot] Serving capture: {capture_path} ({file_size} bytes)")
        
        # Serve the file with CORS headers and cache control
        response = send_file(capture_path, mimetype='image/jpeg')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
        return response
        
    except Exception as e:
        print(f"[@route:host_av:serve_screenshot] Error serving screenshot: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@host_av_bp.route('/images', methods=['GET', 'OPTIONS'])
def serve_image_by_path():
    """Serve an image or JSON file from a specified path on host"""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = current_app.response_class()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    try:
        file_path = request.args.get('path')
        
        # Check if this is a JSON file
        is_json = file_path and file_path.lower().endswith('.json')
        
        # Use URL building utilities to resolve and validate file path
        from utils.build_url_utils import resolveImageFilePath
        
        try:
            if is_json:
                # For JSON files, temporarily replace .json with .jpg to validate path
                temp_image_path = file_path.replace('.json', '.jpg')
                validated_image_path = resolveImageFilePath(temp_image_path)
                validated_path = validated_image_path.replace('.jpg', '.json')
            else:
                validated_path = resolveImageFilePath(file_path)
        except ValueError as e:
            print(f"[@route:host_av:serve_image_by_path] Invalid file path: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 400
        
        if not os.path.exists(validated_path):
            print(f"[@route:host_av:serve_image_by_path] File not found: {validated_path}")
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        # Check file size
        file_size = os.path.getsize(validated_path)
        if file_size == 0:
            print(f"[@route:host_av:serve_image_by_path] File is empty: {validated_path}")
            return jsonify({'success': False, 'error': 'File is empty'}), 500
        
        print(f"[@route:host_av:serve_image_by_path] Serving file: {validated_path} ({file_size} bytes)")
        
        # Set mimetype based on extension
        if is_json:
            mimetype = 'application/json'
        elif validated_path.lower().endswith('.png'):
            mimetype = 'image/png'
        else:
            mimetype = 'image/jpeg'  # Default
        
        # Serve the file with CORS headers
        response = send_file(validated_path, mimetype=mimetype)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
        return response
        
    except Exception as e:
        print(f"[@route:host_av:serve_image_by_path] Error serving file: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@host_av_bp.route('/listCaptures', methods=['POST'])
def list_captures():
    """List captured frames for monitoring with URLs built like screenshots"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        limit = data.get('limit', 180)
        
        print(f"[@route:host_av:list_captures] Listing captures for device: {device_id}, limit: {limit}")
        
        # Get image controller for the specified device (it handles captures)
        image_controller = get_controller(device_id, 'verification_image')
        
        if not image_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No image controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        # Get capture folder from image controller (it already has captures_path)
        capture_folder = image_controller.captures_path
        
        if not os.path.exists(capture_folder):
            return jsonify({
                'success': False,
                'error': f'Capture folder not found: {capture_folder}'
            }), 404
        
        # List all capture files (not test_capture files or thumbnails)
        capture_files = []
        for filename in os.listdir(capture_folder):
            if (filename.startswith('capture_') and 
                filename.endswith('.jpg') and 
                '_thumbnail' not in filename):  # Exclude thumbnail files
                filepath = os.path.join(capture_folder, filename)
                if os.path.isfile(filepath):
                    # Get file modification time as timestamp
                    timestamp = int(os.path.getmtime(filepath) * 1000)
                    capture_files.append({
                        'filename': filename,
                        'timestamp': timestamp,
                        'filepath': filepath
                    })
        
        # Sort by timestamp (newest first) and limit
        capture_files.sort(key=lambda x: x['timestamp'], reverse=True)
        capture_files = capture_files[:limit]
        
        # Build URLs using the same mechanism as takeScreenshot
        from utils.build_url_utils import buildCaptureUrlFromPath, buildClientImageUrl
        from utils.host_utils import get_host_instance as get_host
        
        try:
            host = get_host()
            host_dict = host.to_dict()
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to get host info: {str(e)}'
            }), 500
        
        # Build response with URLs for each capture
        captures = []
        for capture in capture_files:
            try:
                # Build URL from file path using same mechanism as screenshots
                capture_url = buildCaptureUrlFromPath(host_dict, capture['filepath'], device_id)
                
                # Process URL for client consumption
                client_capture_url = buildClientImageUrl(capture_url)
                
                captures.append({
                    'filename': capture['filename'],
                    'timestamp': capture['timestamp'],
                    'url': client_capture_url
                })
            except Exception as url_error:
                print(f"[@route:host_av:list_captures] Failed to build URL for {capture['filename']}: {url_error}")
                # Skip captures that can't have URLs built
                continue
        
        print(f"[@route:host_av:list_captures] Found {len(captures)} capture files with URLs")
        
        return jsonify({
            'success': True,
            'captures': captures,
            'total': len(captures),
            'device_id': device_id
        })
        
    except Exception as e:
        print(f"[@route:host_av:list_captures] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'List captures error: {str(e)}'
        }), 500

@host_av_bp.route('/monitoring/latest-json', methods=['POST'])
def get_latest_monitoring_json():
    """Get the latest available JSON analysis file for monitoring"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:host_av:latest_json] Getting latest JSON for device: {device_id}")
        
        # Get image controller for the specified device (it handles captures)
        image_controller = get_controller(device_id, 'verification_image')
        
        if not image_controller:
            device = get_device_by_id(device_id)
            if not device:
                return jsonify({
                    'success': False,
                    'error': f'Device {device_id} not found'
                }), 404
            
            return jsonify({
                'success': False,
                'error': f'No image controller found for device {device_id}',
                'available_capabilities': device.get_capabilities()
            }), 404
        
        # Get capture folder from image controller
        capture_folder = image_controller.captures_path
        
        if not os.path.exists(capture_folder):
            return jsonify({
                'success': False,
                'error': f'Capture folder not found: {capture_folder}'
            }), 404
        
        # Find the latest JSON file
        json_files = []
        for filename in os.listdir(capture_folder):
            if (filename.startswith('capture_') and 
                filename.endswith('.json')):
                filepath = os.path.join(capture_folder, filename)
                if os.path.isfile(filepath):
                    # Extract sequence number from filename for consistent sorting
                    import re
                    sequence_match = re.search(r'capture_(\d+)\.json', filename)
                    if sequence_match:
                        sequence_number = sequence_match.group(1)
                        json_files.append({
                            'filename': filename,
                            'timestamp': int(sequence_number),  # Use sequence number for sorting
                            'filepath': filepath
                        })
        
        if not json_files:
            return jsonify({
                'success': False,
                'error': 'No JSON analysis files found'
            }), 404
        
        # Sort by sequence number (newest first) and get the latest
        json_files.sort(key=lambda x: x['timestamp'], reverse=True)
        latest_json = json_files[0]
        
        # Simple: use same URL pattern as images but with .json extension
        from utils.build_url_utils import buildCaptureUrlFromPath, buildClientImageUrl
        from utils.host_utils import get_host_instance as get_host
        
        try:
            host = get_host()
            host_dict = host.to_dict()
            
            # Build URL using existing pattern, then fix extension
            json_url = buildCaptureUrlFromPath(host_dict, latest_json['filepath'], device_id)
            json_url = json_url.replace('.jpg', '.json')  # Fix the extension
            
            # Process URL for client consumption  
            client_json_url = buildClientImageUrl(json_url)
            
            print(f"[@route:host_av:latest_json] Latest JSON: {latest_json['filename']}")
            print(f"[@route:host_av:latest_json] JSON URL: {client_json_url}")
            
            return jsonify({
                'success': True,
                'latest_json_url': client_json_url,
                'filename': latest_json['filename'],
                'timestamp': latest_json['timestamp'],
                'device_id': device_id
            })
            
        except Exception as url_error:
            return jsonify({
                'success': False,
                'error': f'Failed to build JSON URL: {str(url_error)}'
            }), 500
        
    except Exception as e:
        print(f"[@route:host_av:latest_json] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Latest JSON error: {str(e)}'
        }), 500 