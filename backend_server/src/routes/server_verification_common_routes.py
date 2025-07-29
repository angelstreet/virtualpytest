"""
Verification Execution Routes

This module provides verification execution endpoints only.
Verifications are now embedded directly in navigation nodes, so no database CRUD operations are needed.
"""

from flask import Blueprint, request, jsonify
from shared.lib.utils.route_utils import proxy_to_host, get_host_from_request

# Create blueprint
server_verification_common_bp = Blueprint('server_verification_common', __name__, url_prefix='/server/verification')

# =====================================================
# VERIFICATION INFORMATION (for frontend compatibility)
# =====================================================

@server_verification_common_bp.route('/getVerifications', methods=['GET'])
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

@server_verification_common_bp.route('/getAllReferences', methods=['POST'])
def get_all_references():
    """Get all reference images/data."""
    try:
        from shared.lib.supabase.verifications_references_db import get_references
        from shared.lib.utils.app_utils import DEFAULT_TEAM_ID
        
        print(f'[@route:server_verification:get_all_references] Getting all references for team: {DEFAULT_TEAM_ID}')
        
        # Get all references for the team
        result = get_references(team_id=DEFAULT_TEAM_ID)
        
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
# SINGLE VERIFICATION EXECUTION ENDPOINTS (PROXY TO HOST)
# =====================================================

@server_verification_common_bp.route('/image/execute', methods=['POST'])
def verification_image_execute():
    """Proxy single image verification to host"""
    try:
        print("[@route:server_verification_common:verification_image_execute] Proxying image verification request")
        
        data = request.get_json()
        host_info = get_host_from_request(data)
        
        response = proxy_to_host(
            host_url=host_info['host_url'],
            endpoint='/host/verification/image/execute',
            method='POST',
            data=data
        )
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_image_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/text/execute', methods=['POST'])
def verification_text_execute():
    """Proxy single text verification to host"""
    try:
        print("[@route:server_verification_common:verification_text_execute] Proxying text verification request")
        
        data = request.get_json()
        host_info = get_host_from_request(data)
        
        response = proxy_to_host(
            host_url=host_info['host_url'],
            endpoint='/host/verification/text/execute',
            method='POST',
            data=data
        )
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_text_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/adb/execute', methods=['POST'])
def verification_adb_execute():
    """Proxy single adb verification to host"""
    try:
        print("[@route:server_verification_common:verification_adb_execute] Proxying adb verification request")
        
        data = request.get_json()
        host_info = get_host_from_request(data)
        
        response = proxy_to_host(
            host_url=host_info['host_url'],
            endpoint='/host/verification/adb/execute',
            method='POST',
            data=data
        )
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_adb_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/appium/execute', methods=['POST'])
def verification_appium_execute():
    """Proxy single appium verification to host"""
    try:
        print("[@route:server_verification_common:verification_appium_execute] Proxying appium verification request")
        
        data = request.get_json()
        host_info = get_host_from_request(data)
        
        response = proxy_to_host(
            host_url=host_info['host_url'],
            endpoint='/host/verification/appium/execute',
            method='POST',
            data=data
        )
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_appium_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/audio/execute', methods=['POST'])
def verification_audio_execute():
    """Proxy single audio verification to host"""
    try:
        print("[@route:server_verification_common:verification_audio_execute] Proxying audio verification request")
        
        data = request.get_json()
        host_info = get_host_from_request(data)
        
        response = proxy_to_host(
            host_url=host_info['host_url'],
            endpoint='/host/verification/audio/execute',
            method='POST',
            data=data
        )
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_audio_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/video/execute', methods=['POST'])
def verification_video_execute():
    """Proxy single video verification to host"""
    try:
        print("[@route:server_verification_common:verification_video_execute] Proxying video verification request")
        
        data = request.get_json()
        host_info = get_host_from_request(data)
        
        response = proxy_to_host(
            host_url=host_info['host_url'],
            endpoint='/host/verification/video/execute',
            method='POST',
            data=data
        )
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_video_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================================
# BATCH VERIFICATION EXECUTION
# =====================================================

@server_verification_common_bp.route('/executeBatch', methods=['POST'])
def verification_execute_batch():
    """Execute batch of verifications with embedded verification objects"""
    try:
        print("[@route:server_verification_common:verification_execute_batch] Starting batch verification execution")
        
        # Get request data
        data = request.get_json() or {}
        verifications = data.get('verifications', [])  # Array of embedded verification objects
        host = data.get('host', {})
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:server_verification_common:verification_execute_batch] Processing {len(verifications)} verifications")
        print(f"[@route:server_verification_common:verification_execute_batch] Host: {host.get('host_name')}, Device ID: {device_id}")
        
        # Validate
        if not verifications:
            return jsonify({'success': False, 'error': 'verifications are required'}), 400
        
        if not host:
            return jsonify({'success': False, 'error': 'host is required'}), 400
        
        # Proxy execution to host
        host_url = host.get('host_url', f"http://{host.get('host_name')}:6109")
        
        # Prepare execution payload with embedded verifications
        execution_payload = {
            'verifications': verifications,  # Verifications are already embedded objects
            'device_id': device_id
        }
        
        print(f"[@route:server_verification_common:verification_execute_batch] Proxying to host: {host_url}")
        
        # Proxy to host
        response = proxy_to_host(
            host_url=host_url,
            endpoint='/host/verification/executeBatch',
            method='POST',
            data=execution_payload,
            timeout=300  # 5 minute timeout for verification execution
        )
        
        if response.get('success'):
            print(f"[@route:server_verification_common:verification_execute_batch] Batch execution completed successfully")
            return jsonify(response)
        else:
            print(f"[@route:server_verification_common:verification_execute_batch] Batch execution failed: {response.get('error', 'Unknown error')}")
            return jsonify(response), 400
            
    except Exception as e:
        print(f"[@route:server_verification_common:verification_execute_batch] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error during batch verification execution: {str(e)}'
        }), 500

# =====================================================
# HEALTH CHECK
# =====================================================

@server_verification_common_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for verification execution service"""
    return jsonify({
        'success': True,
        'message': 'Verification execution service is running',
        'note': 'Verifications are now embedded in navigation nodes'
    })
