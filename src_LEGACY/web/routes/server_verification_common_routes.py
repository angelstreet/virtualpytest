"""
Verification Common Routes

This module contains ALL server-side verification endpoints that:
- Handle single verification execution for all types (image, text, adb)
- Coordinate batch verification by dispatching to individual host endpoints
- Manage reference lists and database operations
- Provide shared verification utilities
"""

from flask import Blueprint, request, jsonify
from src.web.utils.routeUtils import proxy_to_host, get_host_from_request

# Import verification database functions
from src.lib.supabase.verifications_db import get_verifications, save_verification, delete_verification
from src.utils.app_utils import DEFAULT_TEAM_ID

# Create blueprint
server_verification_common_bp = Blueprint('server_verification_common', __name__, url_prefix='/server/verification')

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
        
        # Proxy to host image verification endpoint
        response_data, status_code = proxy_to_host('/host/verification/image/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/text/execute', methods=['POST'])
def verification_text_execute():
    """Proxy single text verification to host"""
    try:
        print("[@route:server_verification_common:verification_text_execute] Proxying text verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host text verification endpoint
        response_data, status_code = proxy_to_host('/host/verification/text/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/adb/execute', methods=['POST'])
def verification_adb_execute():
    """Proxy single ADB verification to host"""
    try:
        print("[@route:server_verification_common:verification_adb_execute] Proxying ADB verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host ADB verification endpoint
        response_data, status_code = proxy_to_host('/host/verification/adb/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/appium/execute', methods=['POST'])
def verification_appium_execute():
    """Proxy single Appium verification to host"""
    try:
        print("[@route:server_verification_common:verification_appium_execute] Proxying Appium verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host Appium verification endpoint
        response_data, status_code = proxy_to_host('/host/verification/appium/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/audio/execute', methods=['POST'])
def verification_audio_execute():
    """Proxy single audio verification to host"""
    try:
        print("[@route:server_verification_common:verification_audio_execute] Proxying audio verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host audio verification endpoint
        response_data, status_code = proxy_to_host('/host/verification/audio/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/video/execute', methods=['POST'])
def verification_video_execute():
    """Proxy single video verification to host"""
    try:
        print("[@route:server_verification_common:verification_video_execute] Proxying video verification request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video verification endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/execute', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/video/detectBlackscreen', methods=['POST'])
def verification_video_detect_blackscreen():
    """Proxy video blackscreen detection to host"""
    try:
        print("[@route:server_verification_common:verification_video_detect_blackscreen] Proxying blackscreen detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video blackscreen detection endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/detectBlackscreen', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/video/detectFreeze', methods=['POST'])
def verification_video_detect_freeze():
    """Proxy video freeze detection to host"""
    try:
        print("[@route:server_verification_common:verification_video_detect_freeze] Proxying freeze detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video freeze detection endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/detectFreeze', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/video/detectSubtitles', methods=['POST'])
def verification_video_detect_subtitles():
    """Proxy video subtitle detection to host"""
    try:
        print("[@route:server_verification_common:verification_video_detect_subtitles] Proxying subtitle detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video subtitle detection endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/detectSubtitles', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/video/detectSubtitlesAI', methods=['POST'])
def verification_video_detect_subtitles_ai():
    """Proxy video AI subtitle detection to host"""
    try:
        print("[@route:server_verification_common:verification_video_detect_subtitles_ai] Proxying AI subtitle detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video AI subtitle detection endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/detectSubtitlesAI', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/video/analyzeImageAI', methods=['POST'])
def verification_video_analyze_image_ai():
    """Proxy AI image analysis to host"""
    try:
        print("[@route:server_verification_common:verification_video_analyze_image_ai] Proxying AI image analysis request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host video AI image analysis endpoint
        response_data, status_code = proxy_to_host('/host/verification/video/analyzeImageAI', 'POST', request_data, timeout=60)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# BATCH VERIFICATION COORDINATION (SERVER-SIDE LOGIC)
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
        model = data.get('model')  # Get model from frontend request
        
        print(f"[@route:server_verification_common:verification_execute_batch] Processing {len(verifications)} verifications")
        print(f"[@route:server_verification_common:verification_execute_batch] Source: {image_source_url}")
        
        # Validate required parameters
        if not verifications:
            return jsonify({
                'success': False,
                'error': 'verifications are required'
            }), 400
        
        # Note: image_source_url is optional - controllers will take screenshots automatically when needed
        # ADB verifications don't need screenshots, image/text verifications will capture if no source provided
        
        results = []
        passed_count = 0
        
        for i, verification in enumerate(verifications):
            verification_type = verification.get('verification_type', 'text')
            
            print(f"[@route:server_verification_common:verification_execute_batch] Processing verification {i+1}/{len(verifications)}: {verification_type}")
            
            # Prepare individual request data with model from frontend
            individual_request = {
                'verification': verification,
                'image_source_url': image_source_url,
                'model': model  # Pass model to host for image verification
            }
            
            # Dispatch to appropriate host endpoint based on verification type
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
                    'error': f'Unknown verification type: {verification_type}. Supported types: image, text, adb, appium, audio, video',
                    'verification_type': verification_type
                }
                status = 400
            
            # Handle proxy errors and flatten verification results
            if status != 200 and isinstance(result, dict):
                result['verification_type'] = verification_type
                flattened_result = result
            elif status != 200:
                flattened_result = {
                    'success': False,
                    'error': f'Host request failed with status {status}',
                    'verification_type': verification_type
                }
            else:
                # All verification controllers return flat structures
                # Use the result directly without looking for a nested verification_result
                verification_result = result
                
                flattened_result = {
                    'success': verification_result.get('success', False),
                    'message': verification_result.get('message'),
                    'error': verification_result.get('error'),
                    'threshold': verification_result.get('threshold') or verification_result.get('confidence') or verification_result.get('userThreshold', 0.8),
                    'resultType': 'PASS' if verification_result.get('success', False) else 'FAIL',
                    'sourceImageUrl': verification_result.get('sourceUrl'),
                    'referenceImageUrl': verification_result.get('referenceUrl'),
                    'resultOverlayUrl': verification_result.get('overlayUrl'),
                    'extractedText': verification_result.get('extractedText', ''),
                    'searchedText': verification_result.get('searchedText', ''),
                    'imageFilter': verification_result.get('imageFilter', 'none'),
                    'detectedLanguage': verification_result.get('detected_language'),
                    'languageConfidence': verification_result.get('language_confidence'),
                    # ADB-specific fields
                    'search_term': verification_result.get('search_term'),
                    'wait_time': verification_result.get('wait_time'),
                    'total_matches': verification_result.get('total_matches'),
                    'matches': verification_result.get('matches'),
                    # Appium-specific fields
                    'platform': verification_result.get('platform'),
                    # Audio/Video-specific fields  
                    'motion_threshold': verification_result.get('motion_threshold'),
                    'duration': verification_result.get('duration'),
                    'frequency': verification_result.get('frequency'),
                    'audio_level': verification_result.get('audio_level'),
                    # General fields
                    'verification_type': verification_result.get('verification_type', verification_type),
                    'execution_time_ms': verification_result.get('execution_time_ms'),
                    'details': verification_result.get('details', {})
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
# IMAGE VERIFICATION SPECIFIC ENDPOINTS
# =====================================================

@server_verification_common_bp.route('/image/processImage', methods=['POST'])
def verification_image_process():
    """Proxy process image request to host for reference image processing"""
    try:
        print("[@route:server_verification_common:verification_image_process] Proxying process image request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host verification image process endpoint
        response_data, status_code = proxy_to_host('/host/verification/image/processImage', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/image/cropImage', methods=['POST'])
def verification_image_crop():
    """Proxy crop image request to host for reference image cropping"""
    try:
        print("[@route:server_verification_common:verification_image_crop] Proxying crop image request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host verification image crop endpoint
        response_data, status_code = proxy_to_host('/host/verification/image/cropImage', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/image/saveImage', methods=['POST'])
def verification_image_save():
    """Proxy save image request to host - host handles R2 upload and database save"""
    try:
        print("[@route:server_verification_common:verification_image_save] Proxying save image request to host")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host verification image save endpoint
        response_data, status_code = proxy_to_host('/host/verification/image/saveImage', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_image_save] ERROR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# TEXT VERIFICATION SPECIFIC ENDPOINTS
# =====================================================

@server_verification_common_bp.route('/text/detectText', methods=['POST'])
def verification_text_detect():
    """Proxy text auto-detection request to host"""
    try:
        print("[@route:server_verification_common:verification_text_detect] Proxying OCR detection request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/verification/text/detectText', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/text/saveText', methods=['POST'])
def verification_text_save():
    """Proxy save text request to host - host handles database save"""
    try:
        print("[@route:server_verification_common:verification_text_save] Proxying save text request to host")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host verification text save endpoint
        response_data, status_code = proxy_to_host('/host/verification/text/saveText', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_text_save] ERROR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# ADB VERIFICATION SPECIFIC ENDPOINTS
# =====================================================

@server_verification_common_bp.route('/adb/waitForElementToAppear', methods=['POST'])
def verification_adb_wait_for_element_to_appear():
    """Proxy ADB waitForElementToAppear request to host"""
    try:
        print("[@route:server_verification_common:verification_adb_wait_for_element_to_appear] Proxying ADB waitForElementToAppear request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/verification/adb/waitForElementToAppear', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/adb/waitForElementToDisappear', methods=['POST'])
def verification_adb_wait_for_element_to_disappear():
    """Proxy ADB waitForElementToDisappear request to host"""
    try:
        print("[@route:server_verification_common:verification_adb_wait_for_element_to_disappear] Proxying ADB waitForElementToDisappear request")
        
        # Get request data
        request_data = request.get_json() or {}
        
        # Proxy to host
        response_data, status_code = proxy_to_host('/host/verification/adb/waitForElementToDisappear', 'POST', request_data)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# DATABASE OPERATIONS (SERVER-SIDE ONLY)
# =====================================================

@server_verification_common_bp.route('/image/getReferences', methods=['POST'])
def verification_image_get_references():
    """Get image references from database - Uses verification controller"""
    try:
        print("[@route:server_verification_common:verification_image_get_references] Getting image references using verification controller")
        
        # Get host info for model filtering
        host_info, error = get_host_from_request()
        if not host_info:
            return jsonify({
                'success': False,
                'error': error or 'Host information required'
            }), 400
        
        # Get image references from database directly
        from src.lib.supabase.verifications_references_db import get_references
        
        result = get_references(
            team_id=DEFAULT_TEAM_ID,
            device_model=host_info.get('device_model'),
            reference_type='reference_image'
        )
        
        return jsonify(result)
            
    except Exception as e:
        print(f"[@route:server_verification_common:verification_image_get_references] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/text/getReferences', methods=['POST'])
def verification_text_get_references():
    """Get text references from database - Uses verification controller"""
    try:
        print("[@route:server_verification_common:verification_text_get_references] Getting text references using verification controller")
        
        # Get host info for model filtering
        host_info, error = get_host_from_request()
        if not host_info:
            return jsonify({
                'success': False,
                'error': error or 'Host information required'
            }), 400
        
        # Get text references from database directly
        from src.lib.supabase.verifications_references_db import get_references
        
        result = get_references(
            team_id=DEFAULT_TEAM_ID,
            device_model=host_info.get('device_model'),
            reference_type='reference_text'
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_text_get_references] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_verification_common_bp.route('/getAllReferences', methods=['GET', 'POST'])
def verification_get_all_references():
    """Get all references from database - Uses verification controller"""
    try:
        print("[@route:server_verification_common:verification_get_all_references] Getting references using verification controller")
        
        # Get host info for model filtering
        host_info, error = get_host_from_request()
        if not host_info:
            return jsonify({
                'success': False,
                'error': error or 'Host information required'
            }), 400
        
        # Get all references from database directly
        from src.lib.supabase.verifications_references_db import get_references
        
        result = get_references(
            team_id=DEFAULT_TEAM_ID,
            device_model=host_info.get('device_model')
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:server_verification_common:verification_get_all_references] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# VERIFICATION MANAGEMENT ENDPOINTS
# =====================================================

@server_verification_common_bp.route('/saveVerification', methods=['POST'])
def save_verification():
    """
    Save or update verification definition.
    
    Expected JSON payload:
    {
        "name": "verification_name",
        "device_model": "android_mobile",
        "verification_type": "image|text|adb",
        "command": "verification_command",
        "params": {...}
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'device_model', 'verification_type', 'command']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Use default team ID
        team_id = DEFAULT_TEAM_ID
        
        # Save verification to database
        result = save_verification(
            name=data['name'],
            device_model=data['device_model'],
            verification_type=data['verification_type'],
            command=data['command'],
            team_id=team_id,
            params=data.get('params', {})
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'verification_id': result['verification_id'],
                'reused': result.get('reused', False),
                'message': 'Verification saved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        print(f"[@server_verifications_routes:save_verification] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@server_verification_common_bp.route('/getVerifications', methods=['GET'])
def get_verifications_endpoint():
    """
    Get saved verifications from database with optional filtering.
    
    Query parameters:
    - verification_type: Filter by type
    - device_model: Filter by device model
    - name: Filter by name (partial match)
    """
    try:
        team_id = DEFAULT_TEAM_ID
        
        # Get optional filters from query parameters
        verification_type = request.args.get('verification_type')
        device_model = request.args.get('device_model')
        name = request.args.get('name')
        
        # Get verifications from database
        result = get_verifications(
            team_id=team_id,
            verification_type=verification_type,
            device_model=device_model,
            name=name
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'verifications': result['verifications'],
                'count': len(result['verifications'])
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        print(f"[@server_verifications_routes:get_verifications] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@server_verification_common_bp.route('/deleteVerification', methods=['POST'])
def delete_verification():
    """
    Delete verification by ID or by identifiers.
    
    Expected JSON payload (option 1 - by ID):
    {
        "verification_id": "uuid"
    }
    
    Expected JSON payload (option 2 - by identifiers):
    {
        "name": "verification_name",
        "device_model": "android_mobile", 
        "verification_type": "image"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        team_id = DEFAULT_TEAM_ID
        
        # Delete verification from database
        result = delete_verification(
            team_id=team_id,
            verification_id=data.get('verification_id'),
            name=data.get('name'),
            device_model=data.get('device_model'),
            verification_type=data.get('verification_type')
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Verification deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        print(f"[@server_verifications_routes:delete_verification] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@server_verification_common_bp.route('/getVerificationsByIds', methods=['POST'])
def get_verifications_by_ids():
    """
    Get multiple verifications by their IDs in a single batch request.
    
    Expected JSON payload:
    {
        "verification_ids": ["uuid1", "uuid2", "uuid3"]
    }
    """
    try:
        data = request.get_json()
        
        if 'verification_ids' not in data or not isinstance(data['verification_ids'], list):
            return jsonify({
                'success': False,
                'error': 'Missing required field: verification_ids (array)'
            }), 400
        
        if not data['verification_ids']:
            return jsonify({
                'success': True,
                'verifications': [],
                'count': 0
            })
        
        # Use default team ID
        team_id = DEFAULT_TEAM_ID
        verification_ids = data['verification_ids']
        
        # Get all verifications first
        all_verifications_result = get_verifications(team_id=team_id)
        
        if not all_verifications_result['success']:
            return jsonify({
                'success': False,
                'error': all_verifications_result.get('error', 'Failed to retrieve verifications')
            }), 500
        
        all_verifications = all_verifications_result['verifications']
        
        # Filter verifications by requested IDs
        requested_verifications = []
        found_ids = set()
        
        for verification in all_verifications:
            if verification.get('id') in verification_ids:
                requested_verifications.append(verification)
                found_ids.add(verification.get('id'))
        
        # Log any missing IDs
        missing_ids = set(verification_ids) - found_ids
        if missing_ids:
            print(f"[@server_verification_common_routes:get_verifications_by_ids] Warning: {len(missing_ids)} verification IDs not found: {missing_ids}")
        
        print(f"[@server_verification_common_routes:get_verifications_by_ids] Found {len(requested_verifications)}/{len(verification_ids)} requested verifications")
        
        return jsonify({
            'success': True,
            'verifications': requested_verifications,
            'count': len(requested_verifications),
            'requested_count': len(verification_ids),
            'missing_ids': list(missing_ids)
        })
        
    except Exception as e:
        print(f"[@server_verification_common_routes:get_verifications_by_ids] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500
