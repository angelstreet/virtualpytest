"""
Host System Control Routes

System control endpoints for host-level operations:
- Restart vpt_host service
- Reboot host machine
- Restart host streaming services
"""

from flask import Blueprint, request, jsonify
import time
import os

host_system_bp = Blueprint('host_system', __name__, url_prefix='/host/system')


# =====================================================
# HEALTH CHECK ENDPOINT
# =====================================================

@host_system_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint with system status"""
    # Try to get Supabase status
    try:
        from shared.src.lib.utils.supabase_utils import get_supabase_client
        supabase_client = get_supabase_client()
        supabase_status = "connected" if supabase_client else "disconnected"
    except Exception:
        supabase_status = "unavailable"
    
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'mode': 'host',
        'host_name': os.getenv('HOST_NAME', 'unknown'),
        'supabase': supabase_status
    }), 200


@host_system_bp.route('/restartHostService', methods=['POST'])
def restart_host_service():
    """Restart vpt_host systemd service"""
    try:
        from shared.src.lib.utils.system_utils import restart_systemd_service
        
        result = restart_systemd_service('vpt_host')
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to restart vpt_host service: {str(e)}'
        }), 500


@host_system_bp.route('/rebootHost', methods=['POST'])
def reboot_host():
    """Reboot the host machine"""
    try:
        from shared.src.lib.utils.system_utils import reboot_system
        
        result = reboot_system()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to reboot host: {str(e)}'
        }), 500


@host_system_bp.route('/restartHostStreamService', methods=['POST'])
def restart_host_stream_service():
    """Restart streaming service on host device with quality"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        quality = data.get('quality', 'sd')
        
        from backend_host.src.lib.utils.host_utils import get_controller, get_device_by_id
        
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
        
        restart_result = av_controller.restart_stream(quality=quality)
        
        if restart_result:
            return jsonify({
                'success': True,
                'restarted': True,
                'device_id': device_id,
                'quality': quality,
                'message': f'Stream restarted with {quality.upper()} quality'
            }), 200
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

