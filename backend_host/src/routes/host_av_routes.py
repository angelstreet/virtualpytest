"""
Host Audio/Video Routes

This module contains the host-specific audio/video API endpoints for:
- AV controller connection management
- Video capture control
- Screenshot capture

These endpoints run on the host and use the host's own stored device object.
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from  backend_host.src.lib.utils.host_utils import get_controller, get_device_by_id
import os
import shutil
import time

# Create blueprint
host_av_bp = Blueprint('host_av', __name__, url_prefix='/host/av')

@host_av_bp.route('/connect', methods=['POST'])
def connect():
    """Connect to AV controller using new architecture"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
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
        
        connect_result = av_controller.connect()
        
        if connect_result:
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
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
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
        device_id = request.args.get('device_id', 'device1')
        
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
        
        status = av_controller.get_status()
        
        return jsonify({
            'success': True,
            'status': status,
            'device_id': device_id,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@host_av_bp.route('/takeControl', methods=['POST'])
def take_control():
    """Take control of AV system using new architecture"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
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
        
        control_result = av_controller.take_control()
        
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
        device_id = request.args.get('device_id', 'device1')
        
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
        
        from shared.src.lib.utils.build_url_utils import buildStreamUrl
        from  backend_host.src.lib.utils.host_utils import get_host_instance as get_host
        
        host = get_host()
        stream_url = buildStreamUrl(host.to_dict(), device_id)
        
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

@host_av_bp.route('/getSegmentCapture', methods=['POST'])
def get_segment_capture():
    """Get capture image for a specific segment (with hot-to-cold copy)"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        segment_number = data.get('segment_number')
        fps = data.get('fps', 5)
        
        if segment_number is None:
            return jsonify({
                'success': False,
                'error': 'segment_number is required'
            }), 400
        
        # Get device to find capture path
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        # Get capture path from device
        av_controller = get_controller(device_id, 'av')
        if not av_controller or not hasattr(av_controller, 'video_capture_path'):
            return jsonify({
                'success': False,
                'error': f'No video capture path for device {device_id}'
            }), 404
        
        from shared.src.lib.utils.storage_path_utils import (
            get_capture_folder, 
            get_captures_path,
            get_cold_storage_path,
            get_capture_number_from_segment
        )
        
        # Calculate capture number from segment
        capture_number = get_capture_number_from_segment(segment_number, fps)
        filename = f'capture_{str(capture_number).zfill(9)}.jpg'
        
        # Get device folder
        device_folder = get_capture_folder(av_controller.video_capture_path)
        
        # Check hot storage first
        hot_captures_path = get_captures_path(device_folder)
        hot_path = os.path.join(hot_captures_path, filename)
        
        # Build cold path
        cold_captures_path = get_cold_storage_path(device_folder, 'captures')
        cold_path = os.path.join(cold_captures_path, filename)
        
        # Copy from hot to cold if exists in hot
        if os.path.exists(hot_path):
            # Directory MUST exist (pre-created by setup_ram_hot_storage.sh)
            if not os.path.exists(cold_captures_path):
                return jsonify({
                    'success': False,
                    'error': f'Cold storage directory not found: {cold_captures_path}. Run setup_ram_hot_storage.sh to create it.'
                }), 500
            shutil.copy2(hot_path, cold_path)
            print(f"[@route:host_av:getSegmentCapture] Copied from HOT to COLD: {filename}")
        elif not os.path.exists(cold_path):
            return jsonify({
                'success': False,
                'error': f'Capture {filename} not found in hot or cold storage',
                'debug': {
                    'segment_number': segment_number,
                    'fps': fps,
                    'capture_number': capture_number,
                    'filename': filename,
                    'hot_path': hot_path,
                    'cold_path': cold_path
                }
            }), 500
        
        # Build URL for cold path
        from shared.src.lib.utils.build_url_utils import buildCaptureUrlFromPath
        from  backend_host.src.lib.utils.host_utils import get_host_instance as get_host
        
        host = get_host()
        capture_url = buildCaptureUrlFromPath(host.to_dict(), cold_path, device_id)
        
        return jsonify({
            'success': True,
            'capture_url': capture_url,
            'capture_path': cold_path,
            'segment_number': segment_number,
            'capture_number': capture_number
        })
        
    except Exception as e:
        print(f"[@route:host_av:getSegmentCapture] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/takeScreenshot', methods=['POST'])
def take_screenshot():
    """Take temporary screenshot to nginx folder using new architecture"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
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
        
        screenshot_path = av_controller.take_screenshot()
        
        if not screenshot_path:
            return jsonify({
                'success': False,
                'error': 'Failed to take temporary screenshot - controller returned None'
            }), 500
        
        # ALWAYS copy to cold storage with FIXED filename (for verification persistence)
        from shared.src.lib.utils.storage_path_utils import get_capture_folder, get_cold_storage_path
        
        print(f"[@route:host_av:takeScreenshot] Original screenshot path: {screenshot_path}")
        
        device_folder = get_capture_folder(screenshot_path)
        print(f"[@route:host_av:takeScreenshot] Extracted device folder: {device_folder}")
        
        cold_captures_path = get_cold_storage_path(device_folder, 'captures')
        
        # Use FIXED filename that overwrites each time (ensures verification source is always available)
        cold_path = os.path.join(cold_captures_path, 'verification_source.jpg')
        
        print(f"[@route:host_av:takeScreenshot] Target cold path: {cold_path}")
        
        # Directory MUST exist (pre-created by setup_ram_hot_storage.sh with www-data ownership)
        # Flask app does NOT create directories - only writes to existing 777 folders
        if not os.path.exists(cold_captures_path):
            return jsonify({
                'success': False,
                'error': f'Cold storage directory not found: {cold_captures_path}. Run setup_ram_hot_storage.sh to create it.'
            }), 500
        
        if os.path.exists(screenshot_path):
            try:
                shutil.copy2(screenshot_path, cold_path)
                screenshot_path = cold_path
                print(f"[@route:host_av:takeScreenshot] ✅ Copied to COLD: {cold_path}")
            except PermissionError as e:
                return jsonify({
                    'success': False,
                    'error': f'Permission denied writing to {cold_path}. Check folder permissions (should be 777).'
                }), 500
        else:
            print(f"[@route:host_av:takeScreenshot] ⚠️ Source not found: {screenshot_path}")
        
        time.sleep(0.5)
        
        from shared.src.lib.utils.build_url_utils import buildCaptureUrlFromPath
        from  backend_host.src.lib.utils.host_utils import get_host_instance as get_host
        
        try:
            host = get_host()
            screenshot_url = buildCaptureUrlFromPath(host.to_dict(), screenshot_path, device_id)
            client_screenshot_url = screenshot_url
            
            print(f"[@route:host_av:takeScreenshot] Final URL: {client_screenshot_url}")
            
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/saveScreenshot', methods=['POST'])
def save_screenshot():
    """Take screenshot and upload to R2 for navigation documentation"""
    try:
        request_data = request.get_json() or {}
        device_id = request_data.get('device_id', 'device1')
        
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
        
        filename = request_data.get('filename')
        userinterface_name = request_data.get('userinterface_name')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': 'Filename is required for saving screenshot'
            }), 400
        
        if not userinterface_name:
            return jsonify({
                'success': False,
                'error': 'userinterface_name is required for saving screenshot'
            }), 400
        
        local_screenshot_path = av_controller.save_screenshot(filename)
        
        if not local_screenshot_path:
            return jsonify({
                'success': False,
                'error': 'Failed to take screenshot'
            }), 500
        
        if not os.path.exists(local_screenshot_path):
            return jsonify({
                'success': False,
                'error': f'Screenshot file not found: {local_screenshot_path}'
            }), 500
        
        try:
            from shared.src.lib.utils.cloudflare_utils import upload_navigation_screenshot
            
            r2_filename = f"{filename}.jpg"
            upload_result = upload_navigation_screenshot(local_screenshot_path, userinterface_name, r2_filename)
            
            if not upload_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': f'Failed to upload to R2: {upload_result.get("error")}'
                }), 500
            
            r2_url = upload_result.get('url')
            
            client_r2_url = r2_url
            client_local_path = local_screenshot_path
            
            return jsonify({
                'success': True,
                'screenshot_url': client_r2_url,
                'screenshot_path': client_local_path, 
                'device_id': device_id
            })
            
        except Exception as upload_error:
            return jsonify({
                'success': False,
                'error': f'Upload to R2 failed: {str(upload_error)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/startCapture', methods=['POST'])
def start_video_capture():
    """Start video capture using new architecture"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
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
        
        duration = data.get('duration', 60.0)
        filename = data.get('filename')
        resolution = data.get('resolution')
        fps = data.get('fps')
        
        capture_result = av_controller.start_video_capture(
            duration=duration,
            filename=filename,
            resolution=resolution,
            fps=fps
        )
        
        if capture_result:
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/stopCapture', methods=['POST'])
def stop_video_capture():
    """Stop video capture using new architecture"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_av_bp.route('/images/screenshot/<filename>', methods=['GET', 'OPTIONS'])
def serve_screenshot(filename):
    """Serve a screenshot image by filename from host"""
    if request.method == 'OPTIONS':
        response = current_app.response_class()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    try:
        from shared.src.lib.utils.build_url_utils import resolveCaptureFilePath
        
        try:
            capture_path = resolveCaptureFilePath(filename)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        if not os.path.exists(capture_path):
            return jsonify({'success': False, 'error': 'Capture not found'}), 404
        
        file_size = os.path.getsize(capture_path)
        if file_size == 0:
            return jsonify({'success': False, 'error': 'Capture file is empty'}), 500
        
        response = send_file(capture_path, mimetype='image/jpeg')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_av_bp.route('/images', methods=['GET', 'OPTIONS'])
def serve_image_by_path():
    """Serve an image or JSON file from a specified path on host"""
    if request.method == 'OPTIONS':
        response = current_app.response_class()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    try:
        file_path = request.args.get('path')
        
        is_json = file_path and file_path.lower().endswith('.json')
        
        from shared.src.lib.utils.build_url_utils import resolveImageFilePath
        
        try:
            if is_json:
                temp_image_path = file_path.replace('.json', '.jpg')
                validated_image_path = resolveImageFilePath(temp_image_path)
                validated_path = validated_image_path.replace('.jpg', '.json')
            else:
                validated_path = resolveImageFilePath(file_path)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        if not os.path.exists(validated_path):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_size = os.path.getsize(validated_path)
        if file_size == 0:
            return jsonify({'success': False, 'error': 'File is empty'}), 500
        
        if is_json:
            mimetype = 'application/json'
        elif validated_path.lower().endswith('.png'):
            mimetype = 'image/png'
        else:
            mimetype = 'image/jpeg'
        
        response = send_file(validated_path, mimetype=mimetype)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500