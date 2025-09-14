"""
Host Monitoring Routes

Monitoring system endpoints for capture frame listing and JSON analysis file retrieval.
"""

from flask import Blueprint, request, jsonify
from utils.host_utils import get_controller, get_device_by_id
import os
import re

host_monitoring_bp = Blueprint('host_monitoring', __name__, url_prefix='/host/monitoring')

@host_monitoring_bp.route('/listCaptures', methods=['POST'])
def list_captures():
    """List captured frames for monitoring with URLs built like screenshots"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        limit = data.get('limit', 180)
        
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
        
        capture_folder = image_controller.captures_path
        
        if not os.path.exists(capture_folder):
            return jsonify({
                'success': False,
                'error': f'Capture folder not found: {capture_folder}'
            }), 404
        
        capture_files = []
        for filename in os.listdir(capture_folder):
            if (filename.startswith('capture_') and 
                filename.endswith('.jpg') and 
                '_thumbnail' not in filename):
                filepath = os.path.join(capture_folder, filename)
                if os.path.isfile(filepath):
                    timestamp = int(os.path.getmtime(filepath) * 1000)
                    capture_files.append({
                        'filename': filename,
                        'timestamp': timestamp,
                        'filepath': filepath
                    })
        
        capture_files.sort(key=lambda x: x['timestamp'], reverse=True)
        capture_files = capture_files[:limit]
        
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
        
        captures = []
        for capture in capture_files:
            try:
                capture_url = buildCaptureUrlFromPath(host_dict, capture['filepath'], device_id)
                client_capture_url = buildClientImageUrl(capture_url)
                
                captures.append({
                    'filename': capture['filename'],
                    'timestamp': capture['timestamp'],
                    'url': client_capture_url
                })
            except Exception:
                continue
        
        return jsonify({
            'success': True,
            'captures': captures,
            'total': len(captures),
            'device_id': device_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'List captures error: {str(e)}'
        }), 500

@host_monitoring_bp.route('/latest-json', methods=['POST'])
def get_latest_monitoring_json():
    """Get the latest available JSON analysis file for monitoring"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
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
        
        capture_folder = image_controller.captures_path
        
        if not os.path.exists(capture_folder):
            return jsonify({
                'success': False,
                'error': f'Capture folder not found: {capture_folder}'
            }), 404
        
        json_files = []
        for filename in os.listdir(capture_folder):
            if (filename.startswith('capture_') and 
                filename.endswith('.json')):
                filepath = os.path.join(capture_folder, filename)
                if os.path.isfile(filepath):
                    sequence_match = re.search(r'capture_(\d+)\.json', filename)
                    if sequence_match:
                        sequence_number = sequence_match.group(1)
                        json_files.append({
                            'filename': filename,
                            'timestamp': int(sequence_number),
                            'filepath': filepath
                        })
        
        if not json_files:
            return jsonify({
                'success': False,
                'error': 'No JSON analysis files found'
            }), 404
        
        json_files.sort(key=lambda x: x['timestamp'], reverse=True)
        latest_json = json_files[0]
        
        from utils.build_url_utils import buildCaptureUrlFromPath, buildClientImageUrl
        from utils.host_utils import get_host_instance as get_host
        
        try:
            host = get_host()
            host_dict = host.to_dict()
            
            json_url = buildCaptureUrlFromPath(host_dict, latest_json['filepath'], device_id)
            json_url = json_url.replace('.jpg', '.json')
            
            client_json_url = buildClientImageUrl(json_url)
            
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
        return jsonify({
            'success': False,
            'error': f'Latest JSON error: {str(e)}'
        }), 500
