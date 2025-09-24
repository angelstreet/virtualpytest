"""
Host Verification Routes

This module contains the host-side verification API endpoints that:
- List available verification references
- Provide status information for verification system
"""

import os
import json
from flask import Blueprint, request, jsonify, current_app
from backend_host.src.lib.utils.host_utils import get_controller, get_device_by_id

# Create blueprint
host_verification_bp = Blueprint('host_verification', __name__, url_prefix='/host/verification')

# =====================================================
# HOST-SIDE VERIFICATION ENDPOINTS
# =====================================================

@host_verification_bp.route('/getStatus', methods=['GET'])
def verification_status():
    """Get verification system status."""
    try:
        # Get device_id from query params (defaults to device1)
        device_id = request.args.get('device_id', 'device1')
        
        print(f"[@route:verification_status] Getting verification system status for device: {device_id}")
        
        # Get device info
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        # Check available controllers for this device
        available_controllers = []
        
        # Check AV controller
        av_controller = get_controller(device_id, 'av')
        if av_controller:
            available_controllers.append('av')
        
        # Check remote controller
        remote_controller = get_controller(device_id, 'remote')
        if remote_controller:
            available_controllers.append('remote')
        
        # Check verification controllers
        for verification_type in ['verification_image', 'verification_text', 'verification_adb']:
            controller = get_controller(device_id, verification_type)
            if controller:
                available_controllers.append(verification_type)
        
        print(f"[@route:verification_status] Available controllers for device {device_id}: {available_controllers}")
        
        return jsonify({
            'success': True,
            'status': 'ready',
            'controllers_available': available_controllers,
            'message': 'Verification system is ready',
            'host_connected': True,
            'device_id': device_id,
            'device_model': device.device_model,
            'device_name': device.device_name
        })
        
    except Exception as e:
        print(f"[@route:verification_status] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Verification status error: {str(e)}'
        }), 500

@host_verification_bp.route('/executeBatch', methods=['POST'])
def verification_execute_batch():
    """Execute batch of verifications using device's VerificationExecutor"""
    try:
        print("[@route:host_verification:verification_execute_batch] Starting batch verification execution")
        
        # Get request data
        data = request.get_json() or {}
        verifications = data.get('verifications', [])
        device_id = data.get('device_id', 'device1')
        team_id = data.get('team_id')
        image_source_url = data.get('image_source_url')
        tree_id = data.get('tree_id')
        node_id = data.get('node_id')
        
        print(f"[@route:host_verification:verification_execute_batch] Processing {len(verifications)} verifications for device: {device_id}, team: {team_id}")
        
        # Validate
        if not verifications:
            return jsonify({'success': False, 'error': 'verifications are required'}), 400
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
            
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False, 
                'error': f'Device {device_id} not found in host'
            }), 404
        
        device = host_devices[device_id]
        
        # Check if device has verification_executor
        if not hasattr(device, 'verification_executor') or not device.verification_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have VerificationExecutor initialized'
            }), 500
        
        # Execute verifications using device's VerificationExecutor
        result = device.verification_executor.execute_verifications(
            verifications=verifications,
            image_source_url=image_source_url,
            team_id=team_id
        )
        
        print(f"[@route:host_verification:verification_execute_batch] Execution completed: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_verification:verification_execute_batch] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host verification execution failed: {str(e)}'
        }), 500
