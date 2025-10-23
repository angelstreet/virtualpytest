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
        
        # Return basic verification types available for the device model
        # This is mainly for frontend compatibility - verifications are now embedded in nodes
        verifications = [
            {
                'id': 'waitForElementToAppear',
                'name': 'waitForElementToAppear',
                'command': 'waitForElementToAppear',
                'device_model': device_model,
                'verification_type': 'adb',
                'params': {
                    'search_term': '',
                    'timeout': 10,
                    'check_interval': 1
                }
            },
            {
                'id': 'image_verification',
                'name': 'image_verification',
                'command': 'image_verification',
                'device_model': device_model,
                'verification_type': 'image',
                'params': {
                    'reference_image': '',
                    'confidence_threshold': 0.8
                }
            }
        ]
        
        return jsonify({
            'success': True,
            'verifications': verifications
        })
        
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
        from shared.src.lib.database.verifications_references_db import get_references
        
        # Get team_id from query params (standardized pattern like other endpoints)
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        
        print(f'[@route:server_verification:get_all_references] Getting all references for team: {team_id}')
        
        # Get all references for the team
        result = get_references(team_id=team_id)
        
        if result['success']:
            print(f'[@route:server_verification:get_all_references] Found {result["count"]} references')
            return jsonify({
                'success': True,
                'references': result['references']
            })
        else:
            print(f'[@route:server_verification:get_all_references] Error getting references: {result.get("error")}')
            return jsonify({
                'success': False,
                'message': result.get('error', 'Failed to get references')
            }), 500
        
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
