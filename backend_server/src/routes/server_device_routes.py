"""
Device Management Routes

API endpoints for device management.
Queries device_flags table which contains devices auto-registered from hosts.
"""

from flask import Blueprint, request, jsonify

# Create blueprint
server_device_bp = Blueprint('server_device', __name__, url_prefix='/server/devices')


@server_device_bp.route('/getAllDevices', methods=['GET'])
def get_devices():
    """Get all devices from device_flags table"""
    try:
        from services.device_service import device_service
        result = device_service.get_all_devices()
        
        if result['success']:
            return jsonify(result['devices'])
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_device_bp.route('/createDevice', methods=['POST'])
def create_device_endpoint():
    """Create a new device in device_flags table"""
    try:
        device_data = request.json
        
        from services.device_service import device_service
        result = device_service.save_device(device_data)
        
        if result['success']:
            return jsonify({'status': 'success', 'device': result['device']}), 201
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_device_bp.route('/getDevice/<device_id>', methods=['GET'])
def get_device_endpoint(device_id):
    """Get a specific device by device_id"""
    try:
        host_name = request.args.get('host_name')
        
        from services.device_service import device_service
        result = device_service.get_device(device_id, host_name)
        
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
        device_data = request.json or {}
        device_data['device_id'] = device_id
        
        from services.device_service import device_service
        result = device_service.save_device(device_data)
        
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
        host_name = request.args.get('host_name')
        
        from services.device_service import device_service
        result = device_service.delete_device(device_id, host_name)
        
        if result['success']:
            return jsonify({'status': 'success'})
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
