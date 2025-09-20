"""
Verification Execution Routes

This module provides verification execution endpoints only.
Verifications are now embedded directly in navigation nodes, so no database CRUD operations are needed.
"""

from flask import Blueprint, request, jsonify
from src.lib.utils.route_utils import proxy_to_host, get_host_from_request

# Create blueprint
server_verification_bp = Blueprint('server_verification', __name__, url_prefix='/server/verification')

# =====================================================
# VERIFICATION INFORMATION (for frontend compatibility)
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
        from shared.src.lib.supabase.verifications_references_db import get_references
        from shared.src.lib.utils.app_utils import DEFAULT_TEAM_ID
        
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

@server_verification_bp.route('/image/execute', methods=['POST'])
def verification_image_execute():
    """Proxy single image verification to host"""
    try:
        print("[@route:server_verification:verification_image_execute] Proxying image verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host image verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/image/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_image_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/image/cropImage', methods=['POST'])
def verification_image_crop():
    """Proxy image cropping request to host"""
    try:
        print("[@route:server_verification:verification_image_crop] Proxying image crop request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host image verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/image/cropImage', 'POST', request_data, timeout=30)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_image_crop] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/image/processImage', methods=['POST'])
def verification_image_process():
    """Proxy image processing request to host"""
    try:
        print("[@route:server_verification:verification_image_process] Proxying image process request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host image verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/image/processImage', 'POST', request_data, timeout=30)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_image_process] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/image/saveImage', methods=['POST'])
def verification_image_save():
    """Proxy image saving request to host"""
    try:
        print("[@route:server_verification:verification_image_save] Proxying image save request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host image verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/image/saveImage', 'POST', request_data, timeout=30)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_image_save] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/text/execute', methods=['POST'])
def verification_text_execute():
    """Proxy single text verification to host"""
    try:
        print("[@route:server_verification:verification_text_execute] Proxying text verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host text verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/text/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_text_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/text/detectText', methods=['POST'])
def verification_text_detect():
    """Proxy text detection request to host"""
    try:
        print("[@route:server_verification:verification_text_detect] Proxying text detect request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host text verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/text/detectText', 'POST', request_data, timeout=30)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_text_detect] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/text/saveText', methods=['POST'])
def verification_text_save():
    """Proxy text saving request to host"""
    try:
        print("[@route:server_verification:verification_text_save] Proxying text save request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host text verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/text/saveText', 'POST', request_data, timeout=30)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_text_save] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/adb/execute', methods=['POST'])
def verification_adb_execute():
    """Proxy single ADB verification to host"""
    try:
        print("[@route:server_verification:verification_adb_execute] Proxying ADB verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host ADB verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/adb/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_adb_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/appium/execute', methods=['POST'])
def verification_appium_execute():
    """Proxy single Appium verification to host"""
    try:
        print("[@route:server_verification:verification_appium_execute] Proxying Appium verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host Appium verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/appium/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_appium_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/audio/execute', methods=['POST'])
def verification_audio_execute():
    """Proxy single audio verification to host"""
    try:
        print("[@route:server_verification:verification_audio_execute] Proxying audio verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host audio verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/audio/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_audio_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/video/execute', methods=['POST'])
def verification_video_execute():
    """Proxy single video verification to host"""
    try:
        print("[@route:server_verification:verification_video_execute] Proxying video verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video verification endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/video/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_video_execute] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================================
# BATCH VERIFICATION EXECUTION - REMOVE EXECUTOR INSTANTIATION
# =====================================================

@server_verification_bp.route('/executeBatch', methods=['POST'])
def verification_execute_batch():
    """Proxy batch verification execution to host"""
    try:
        print("[@route:server_verification:verification_execute_batch] Proxying batch verification to host")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host verification batch execution endpoint
        response_data, status_code = proxy_to_host('/host/verification/executeBatch', 'POST', request_data, timeout=120)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:verification_execute_batch] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================================
# VIDEO VERIFICATION SPECIFIC ENDPOINTS (PROXY TO HOST)
# =====================================================

@server_verification_bp.route('/video/detectSubtitles', methods=['POST'])
def video_detect_subtitles():
    """Proxy subtitle detection request to host"""
    try:
        print("[@route:server_verification:video_detect_subtitles] Proxying subtitle detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video subtitle detection endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/video/detectSubtitles', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:video_detect_subtitles] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/video/detectSubtitlesAI', methods=['POST'])
def video_detect_subtitles_ai():
    """Proxy AI subtitle detection request to host"""
    try:
        print("[@route:server_verification:video_detect_subtitles_ai] Proxying AI subtitle detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video AI subtitle detection endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/video/detectSubtitlesAI', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:video_detect_subtitles_ai] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/video/analyzeSubtitles', methods=['POST'])
def video_analyze_subtitles():
    """Proxy subtitle analysis request to host AI endpoint"""
    try:
        print("[@route:server_verification:video_analyze_subtitles] Proxying subtitle analysis request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video AI subtitle detection endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/detectSubtitlesAI', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:video_analyze_subtitles] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/video/analyzeImageAI', methods=['POST'])
def video_analyze_image_ai():
    """Proxy AI image analysis request to host"""
    try:
        print("[@route:server_verification:video_analyze_image_ai] Proxying AI image analysis request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video AI image analysis endpoint (original working pattern)
        response_data, status_code = proxy_to_host('/host/verification/video/analyzeImageAI', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:video_analyze_image_ai] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/video/analyzeImageComplete', methods=['POST'])
def video_analyze_image_complete():
    """Combined AI analysis: subtitles + description in single call"""
    try:
        print("[@route:server_verification:video_analyze_image_complete] Proxying combined AI analysis request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host combined analysis endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/analyzeImageComplete', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:video_analyze_image_complete] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_verification_bp.route('/video/analyzeLanguageMenu', methods=['POST'])
def video_analyze_language_menu():
    """Proxy AI language menu analysis request to host"""
    try:
        print("[@route:server_verification:video_analyze_language_menu] Proxying AI language menu analysis request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video AI language menu analysis endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/analyzeLanguageMenu', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification:video_analyze_language_menu] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================================
# HEALTH CHECK
# =====================================================

@server_verification_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for verification execution service"""
    return jsonify({
        'success': True,
        'message': 'Verification execution service is running',
        'note': 'Verifications are now embedded in navigation nodes'
    })
