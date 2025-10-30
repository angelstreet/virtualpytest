"""
Host Verification Web Routes

Host-side web verification endpoints (Playwright web element-based verifications).
"""

from flask import Blueprint, request, jsonify
from backend_host.src.lib.utils.host_utils import get_controller

# Create blueprint
host_verification_web_bp = Blueprint('host_verification_web', __name__, url_prefix='/host/verification/web')

def get_verification_controller(device_id: str, controller_type: str):
    """
    Helper function to get verification controller and handle common validation.
    
    Args:
        device_id: ID of the device
        controller_type: Type of controller ('web')
        
    Returns:
        Tuple of (controller, device, error_response) where error_response is None if successful
    """
    controller = get_controller(device_id, controller_type)
    
    if not controller:
        error_response = jsonify({
            'success': False,
            'error': f'No {controller_type} controller found for device {device_id}'
        }), 404
        return None, None, error_response
    
    return controller, None, None

@host_verification_web_bp.route('/execute', methods=['POST'])
def web_verification_execute():
    """Execute web verification (Playwright web elements based)"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        verification = data.get('verification', {})
        
        command = verification.get('command')
        params = verification.get('params', {})
        
        print(f"[@route:host_verification_web:execute] Web verification request: {command}, device: {device_id}")
        
        # Get web controller using helper
        web_controller, _, error_response = get_verification_controller(device_id, 'web')
        if error_response:
            return error_response
        
        # Check if controller has execute_verification method
        if not hasattr(web_controller, 'execute_verification'):
            return jsonify({
                'success': False,
                'error': 'Web controller does not support verification execution'
            }), 500
        
        # Build verification config
        verification_config = {
            'command': command,
            'params': params,
            'context': None  # Context will be added by executor if needed
        }
        
        # Execute verification
        result = web_controller.execute_verification(verification_config)
        
        print(f"[@route:host_verification_web:execute] Result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_verification_web:execute] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Web verification error: {str(e)}'
        }), 500

