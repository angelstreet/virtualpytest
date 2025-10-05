"""
Host Monitoring Routes

Monitoring system endpoints for capture frame listing and JSON analysis file retrieval.
"""

from flask import Blueprint, request, jsonify
from  backend_host.src.lib.utils.host_utils import get_controller, get_device_by_id
from  backend_host.src.services.disk_usage_service import DiskUsageService

host_monitoring_bp = Blueprint('host_monitoring', __name__, url_prefix='/host/monitoring')

@host_monitoring_bp.route('/listCaptures', methods=['POST'])
def list_captures():
    """List captured frames for monitoring with URLs built like screenshots"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        limit = data.get('limit', 180)
        
        # Get AV controller to access monitoring helpers
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
        
        # Use monitoring helpers
        result = av_controller.monitoring_helpers.list_captures(limit)
        
        return jsonify(result)
        
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
        
        # Get AV controller to access monitoring helpers
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
        
        # Use monitoring helpers
        result = av_controller.monitoring_helpers.get_latest_monitoring_json()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Latest JSON error: {str(e)}'
        }), 500

@host_monitoring_bp.route('/json-by-time', methods=['POST'])
def get_json_by_time():
    """Get metadata JSON for specific video timestamp (archive mode)"""
    import os
    import json
    from shared.src.lib.utils.storage_path_utils import get_capture_storage_path, get_capture_folder
    
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        timestamp_seconds = data.get('timestamp_seconds')
        fps = data.get('fps', 5)
        
        if timestamp_seconds is None:
            return jsonify({'success': False, 'error': 'timestamp_seconds required'}), 400
        
        # Calculate sequence
        sequence = int(timestamp_seconds * fps)
        
        # Get metadata path
        capture_folder = get_capture_folder(None, device_id)
        metadata_path = get_capture_storage_path(capture_folder, 'metadata')
        
        # Look for exact match
        json_filename = f"capture_{sequence:06d}.json"
        json_filepath = os.path.join(metadata_path, json_filename)
        
        if os.path.exists(json_filepath):
            with open(json_filepath, 'r') as f:
                json_data = json.load(f)
            return jsonify({'success': True, 'json_data': json_data, 'sequence': sequence, 'found_exact': True})
        
        # Find nearest (±10 sequences)
        for offset in range(1, 11):
            for direction in [-1, 1]:
                nearby_seq = sequence + (offset * direction)
                if nearby_seq < 0:
                    continue
                nearby_filename = f"capture_{nearby_seq:06d}.json"
                nearby_filepath = os.path.join(metadata_path, nearby_filename)
                
                if os.path.exists(nearby_filepath):
                    with open(nearby_filepath, 'r') as f:
                        json_data = json.load(f)
                    return jsonify({'success': True, 'json_data': json_data, 'sequence': sequence, 'found_exact': False, 'nearest_sequence': nearby_seq})
        
        return jsonify({'success': False, 'error': 'No metadata found', 'sequence': sequence}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@host_monitoring_bp.route('/disk-usage', methods=['GET'])
def disk_usage_diagnostics():
    """
    Comprehensive disk space diagnostics for all capture directories.
    Returns detailed breakdown of segments, captures, thumbnails, and cleanup status.
    
    Query params:
        - capture_dir: Optional specific capture (e.g., 'capture1'), or 'all' for all captures (default)
    """
    try:
        capture_filter = request.args.get('capture_dir', 'all')
        result = DiskUsageService.get_complete_diagnostics(capture_filter)
        
        if not result.get('success'):
            return jsonify(result), 404
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Disk usage diagnostics error: {str(e)}'
        }), 500
