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
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host image verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/image/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_image_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/text/execute', methods=['POST'])
def verification_text_execute():
    """Proxy single text verification to host"""
    try:
        print("[@route:server_verification_common:verification_text_execute] Proxying text verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host text verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/text/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_text_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/adb/execute', methods=['POST'])
def verification_adb_execute():
    """Proxy single ADB verification to host"""
    try:
        print("[@route:server_verification_common:verification_adb_execute] Proxying ADB verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host ADB verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/adb/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_adb_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/appium/execute', methods=['POST'])
def verification_appium_execute():
    """Proxy single Appium verification to host"""
    try:
        print("[@route:server_verification_common:verification_appium_execute] Proxying Appium verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host Appium verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/appium/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_appium_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/audio/execute', methods=['POST'])
def verification_audio_execute():
    """Proxy single audio verification to host"""
    try:
        print("[@route:server_verification_common:verification_audio_execute] Proxying audio verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host audio verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/audio/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_audio_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/video/execute', methods=['POST'])
def verification_video_execute():
    """Proxy single video verification to host"""
    try:
        print("[@route:server_verification_common:verification_video_execute] Proxying video verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/video/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_video_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================================
# BATCH VERIFICATION EXECUTION
# =====================================================

@server_verification_common_bp.route('/executeBatch', methods=['POST'])
def verification_execute_batch():
    """Execute batch verification by dispatching individual requests to host endpoints"""
    try:
        print("[@route:server_verification_common:verification_execute_batch] Starting batch verification coordination")
        
        # Get request data
        data = request.get_json() or {}
        verifications = data.get('verifications', [])
        image_source_url = data.get('image_source_url')
        device_id = data.get('device_id', 'device1')  # Extract device_id from request
        
        print(f"[@route:server_verification_common:verification_execute_batch] Processing {len(verifications)} verifications")
        print(f"[@route:server_verification_common:verification_execute_batch] Source: {image_source_url}")
        
        # Validate required parameters
        if not verifications:
            return jsonify({
                'success': False,
                'error': 'verifications are required'
            }), 400
        
        results = []
        passed_count = 0
        
        for i, verification in enumerate(verifications):
            verification_type = verification.get('verification_type', 'text')
            
            print(f"[@route:server_verification_common:verification_execute_batch] Processing verification {i+1}/{len(verifications)}: {verification_type}")
            
            # Prepare individual request data (following original pattern)
            individual_request = {
                'verification': verification,
                'image_source_url': image_source_url,
                'device_id': device_id  # Include device_id in individual request
            }
            
            # Dispatch to appropriate host endpoint based on verification type (original proxy pattern)
            if verification_type == 'image':
                result, status = proxy_to_host('/host/verification/image/execute', 'POST', individual_request, timeout=60)
            elif verification_type == 'text':
                result, status = proxy_to_host('/host/verification/text/execute', 'POST', individual_request, timeout=60)
            elif verification_type == 'adb':
                result, status = proxy_to_host('/host/verification/adb/execute', 'POST', individual_request, timeout=60)
            elif verification_type == 'appium':
                result, status = proxy_to_host('/host/verification/appium/execute', 'POST', individual_request, timeout=60)
            elif verification_type == 'audio':
                result, status = proxy_to_host('/host/verification/audio/execute', 'POST', individual_request, timeout=60)
            elif verification_type == 'video':
                result, status = proxy_to_host('/host/verification/video/execute', 'POST', individual_request, timeout=60)
            else:
                result = {
                    'success': False,
                    'error': f'Unknown verification type: {verification_type}',
                    'verification_type': verification_type,
                    'resultType': 'FAIL'
                }
                status = 400
            
            # Handle proxy errors and flatten verification results (following original pattern)
            if status != 200 and isinstance(result, dict):
                result['verification_type'] = verification_type
                flattened_result = result
            elif status != 200:
                flattened_result = {
                    'success': False,
                    'error': f'Host request failed with status {status}',
                    'verification_type': verification_type,
                    'resultType': 'FAIL'
                }
            else:
                # Use the result directly from host (original pattern)
                verification_result = result
                
                flattened_result = {
                    'success': verification_result.get('success', False),
                    'message': verification_result.get('message'),
                    'error': verification_result.get('error'),
                    'resultType': 'PASS' if verification_result.get('success', False) else 'FAIL',
                    'verification_type': verification_result.get('verification_type', verification_type),
                    'execution_time_ms': verification_result.get('execution_time_ms'),
                    # Include all other fields from original result
                    **{k: v for k, v in verification_result.items() if k not in ['success', 'message', 'error', 'verification_type', 'execution_time_ms']}
                }
                
                print(f"[@route:server_verification_common:verification_execute_batch] Flattened result {i+1}: success={flattened_result['success']}, type={flattened_result['verification_type']}")
            
            results.append(flattened_result)
            
            # Count successful verifications
            if flattened_result.get('success'):
                passed_count += 1
        
        # Calculate overall batch success
        overall_success = passed_count == len(verifications)
        
        print(f"[@route:server_verification_common:verification_execute_batch] Batch completed: {passed_count}/{len(verifications)} passed")
        
        return jsonify({
            'success': overall_success,
            'total_count': len(verifications),
            'passed_count': passed_count,
            'failed_count': len(verifications) - passed_count,
            'results': results,
            'message': f'Batch verification completed: {passed_count}/{len(verifications)} passed'
        })
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_execute_batch] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Batch verification coordination error: {str(e)}'
        }), 500

# =====================================================
# VIDEO VERIFICATION SPECIFIC ENDPOINTS (PROXY TO HOST)
# =====================================================

@server_verification_common_bp.route('/video/detectSubtitles', methods=['POST'])
def video_detect_subtitles():
    """Proxy subtitle detection request to host"""
    try:
        print("[@route:server_verification_common:video_detect_subtitles] Proxying subtitle detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video subtitle detection endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/video/detectSubtitles', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:video_detect_subtitles] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/video/detectSubtitlesAI', methods=['POST'])
def video_detect_subtitles_ai():
    """Proxy AI subtitle detection request to host"""
    try:
        print("[@route:server_verification_common:video_detect_subtitles_ai] Proxying AI subtitle detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video AI subtitle detection endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/video/detectSubtitlesAI', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:video_detect_subtitles_ai] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_common_bp.route('/video/analyzeImageAI', methods=['POST'])
def video_analyze_image_ai():
    """Proxy AI image analysis request to host"""
    try:
        print("[@route:server_verification_common:video_analyze_image_ai] Proxying AI image analysis request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video AI image analysis endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/video/analyzeImageAI', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:video_analyze_image_ai] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
