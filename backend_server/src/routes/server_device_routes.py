"""
Device Management Routes

This module contains the device management API endpoints for:
- Devices management
- Controllers management
- Environment profiles management
"""

from flask import Blueprint, request, jsonify

# Import database functions from src/lib/supabase (uses absolute import)
from shared.src.lib.database.devices_db import (
    get_all_devices, get_device, save_device as create_device, 
    delete_device
)

from shared.src.lib.utils.app_utils import check_supabase

# =====================================================
# HELPER FUNCTIONS
# =====================================================

# Legacy helper functions moved to services/device_service.py
# All business logic has been extracted to the service layer

# Create blueprint
server_device_bp = Blueprint('server_device', __name__, url_prefix='/server/devices')

# =====================================================
# DEVICE ENDPOINTS
# =====================================================

@server_device_bp.route('/getAllDevices', methods=['GET'])
def get_devices():
    """Get all devices for the team"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        
        # Delegate to service layer
        from services.device_service import device_service
        result = device_service.get_all_devices(team_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify(result['devices'])
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_device_bp.route('/createDevice', methods=['POST'])
def create_device_endpoint():
    """Create a new device"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        device_data = request.json
        
        # Delegate to service layer
        from services.device_service import device_service
        result = device_service.save_device(device_data, team_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify({'status': 'success', 'device': result['device']}), 201
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_device_bp.route('/getDevice/<device_id>', methods=['GET'])
def get_device_endpoint(device_id):
    """Get a specific device by ID"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        
        # Delegate to service layer
        from services.device_service import device_service
        result = device_service.get_device(device_id, team_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify(result['device'])
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_device_bp.route('/updateDevice/<device_id>', methods=['PUT'])
def update_device_endpoint(device_id):
    """Update a specific device"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        device_data = request.json
        
        # Add device_id to data for service
        if device_data:
            device_data['id'] = device_id
        
        # Delegate to service layer
        from services.device_service import device_service
        result = device_service.save_device(device_data, team_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify({'status': 'success', 'device': result['device']})
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_device_bp.route('/deleteDevice/<device_id>', methods=['DELETE'])
def delete_device_endpoint(device_id):
    """Delete a specific device"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        
        # Delegate to service layer
        from services.device_service import device_service
        result = device_service.delete_device(device_id, team_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify({'status': 'success'})
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500 