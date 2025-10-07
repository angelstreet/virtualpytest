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
    """
    Get metadata JSON for specific video timestamp
    
    Strategy:
    - LIVE (recent): Look in HOT storage (individual files, 150s buffer)
    - ARCHIVE (old): Look in COLD storage (10-min chunks, 24h history)
    """
    import os
    import json
    from shared.src.lib.utils.storage_path_utils import get_capture_storage_path, is_ram_mode
    from  backend_host.src.lib.utils.host_utils import get_device_by_id
    
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        timestamp_seconds = data.get('timestamp_seconds')
        fps = data.get('fps', 5)
        
        if timestamp_seconds is None:
            return jsonify({'success': False, 'error': 'timestamp_seconds required'}), 400
        
        # Calculate sequence
        sequence = int(timestamp_seconds * fps)
        
        # Get device capture path
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        capture_dir = device.get_capture_dir('captures')
        if not capture_dir:
            return jsonify({'success': False, 'error': f'No capture directory configured for device {device_id}'}), 404
        
        # Extract device folder name (e.g., 'capture1' from '/var/www/html/stream/capture1/...')
        device_folder = os.path.basename(os.path.dirname(capture_dir)) if '/captures' in capture_dir else os.path.basename(capture_dir)
        base_path = f"/var/www/html/stream/{device_folder}"
        
        # STEP 1: Try HOT storage first (live monitoring, last 150s)
        ram_mode = is_ram_mode(base_path)
        hot_metadata_path = os.path.join(base_path, 'hot', 'metadata') if ram_mode else os.path.join(base_path, 'metadata')
        
        json_filename = f"capture_{sequence:06d}.json"
        hot_json_filepath = os.path.join(hot_metadata_path, json_filename)
        
        if os.path.exists(hot_json_filepath):
            with open(hot_json_filepath, 'r') as f:
                json_data = json.load(f)
            return jsonify({'success': True, 'json_data': json_data, 'sequence': sequence, 'found_exact': True, 'source': 'hot'})
        
        # STEP 2: Try COLD storage (archive, 10-min chunks)
        # Calculate chunk position
        hour = (sequence // (3600 * fps)) % 24
        chunk_index = ((sequence % (3600 * fps)) // (600 * fps))  # 0-5
        
        chunk_path = os.path.join(base_path, 'metadata', str(hour), f'chunk_10min_{chunk_index}.json')
        
        if os.path.exists(chunk_path):
            with open(chunk_path, 'r') as f:
                chunk_data = json.load(f)
            
            # Find frame in chunk by sequence
            frames = chunk_data.get('frames', [])
            
            # Find exact match
            for frame in frames:
                if frame.get('sequence') == sequence:
                    return jsonify({'success': True, 'json_data': frame, 'sequence': sequence, 'found_exact': True, 'source': 'cold'})
            
            # Find nearest frame (within ±5 frames = 1 second)
            closest_frame = None
            min_diff = float('inf')
            for frame in frames:
                diff = abs(frame.get('sequence', 0) - sequence)
                if diff < min_diff and diff <= 5:  # Within 1 second
                    min_diff = diff
                    closest_frame = frame
            
            if closest_frame:
                return jsonify({'success': True, 'json_data': closest_frame, 'sequence': sequence, 'found_exact': False, 'nearest_sequence': closest_frame.get('sequence'), 'source': 'cold'})
        
        return jsonify({'success': False, 'error': 'No metadata found in hot or cold storage', 'sequence': sequence, 'checked_chunk': f'{hour}/chunk_10min_{chunk_index}.json'}), 404
        
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
