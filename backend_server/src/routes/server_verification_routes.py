"""
Verification Routes - Server Logic Only

This module provides verification endpoints that require server-side logic.
Pure proxy routes have been moved to auto_proxy.py.
"""

from flask import Blueprint, request, jsonify

# Create blueprint
server_verification_bp = Blueprint('server_verification', __name__, url_prefix='/server/verification')

# =====================================================
# SERVER LOGIC ROUTES (keep these)
# =====================================================

@server_verification_bp.route('/getVerifications', methods=['GET'])
def get_verifications():
    """Get available verifications for a device model (for frontend compatibility)."""
    try:
        device_model = request.args.get('device_model', 'android_mobile')
        team_id = request.args.get('team_id')
        
        # Delegate to service layer (business logic moved out of route)
        from services.verification_service import verification_service
        result = verification_service.get_verification_types(device_model)
        
        if result['success']:
            return jsonify({
                'success': True,
                'verifications': result['verifications']
            })
        else:
            return jsonify({
                'success': False,
                'message': result['error']
            }), 500
        
    except Exception as e:
        print(f'[@route:server_verification:get_verifications] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_verification_bp.route('/getAllReferences', methods=['POST'])
def get_all_references():
    """Get all reference images/data."""
    try:
        team_id = request.args.get('team_id')
        userinterface_name = request.args.get('userinterface_name')  # OPTIMAL: Direct userinterface filter
        device_model = request.args.get('device_model')  # FALLBACK: Device model compatibility filter
        
        # Delegate to service layer
        from services.verification_service import verification_service
        result = verification_service.get_all_references(team_id, userinterface_name, device_model)
        
        if result['success']:
            return jsonify({
                'success': True,
                'references': result['references']
            })
        else:
            status_code = result.get('status_code', 500)
            return jsonify({
                'success': False,
                'message': result['error']
            }), status_code
        
    except Exception as e:
        print(f'[@route:server_verification:get_all_references] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# =====================================================
# HEALTH CHECK
# =====================================================

@server_verification_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for verification execution service"""
    return jsonify({
        'success': True,
        'message': 'Verification execution service is running',
        'note': 'Pure proxy routes moved to auto_proxy.py'
    })
