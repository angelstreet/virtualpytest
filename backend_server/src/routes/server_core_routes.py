"""
Core API Routes

This module contains the core API endpoints for:
- Health check
- Feature status
- Screenshot
"""

from flask import Blueprint, request, jsonify, current_app, redirect
import requests

# Import utility functions
from shared.src.lib.utils.app_utils import get_team_id
from shared.src.lib.utils.build_url_utils import buildHostUrl
from backend_server.src.lib.utils.server_utils import get_host_manager

# Create blueprint
server_core_bp = Blueprint('server_core', __name__, url_prefix='/server')

# =====================================================
# HEALTH CHECK ENDPOINT
# =====================================================

@server_core_bp.route('/health')
def health():
    """Health check endpoint with lazy-loaded feature status"""
    # Try to get Supabase (will load if not already loaded)
    try:
        from shared.src.lib.utils.supabase_utils import get_supabase_client
        supabase_client = get_supabase_client()
        supabase_status = "connected" if supabase_client else "disconnected"
    except Exception:
        supabase_status = "unavailable"
    
    return jsonify({
        'status': 'ok',
        'supabase': supabase_status,
        'team_id': request.args.get('team_id')
    })


# =====================================================
# SCREENSHOT ENDPOINT
# =====================================================

@server_core_bp.route('/screenshot', methods=['GET'])
def take_screenshot_and_redirect():
    """
    Take screenshot and redirect to image URL.
    
    Query params:
        - host_name: Required - which host to capture from
        - device_id: Optional - device ID (default: device1)
    
    Returns: Redirect to the screenshot image URL
    """
    try:
        host_name = request.args.get('host_name')
        device_id = request.args.get('device_id', 'device1')
        
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name query parameter is required'
            }), 400
        
        print(f"📸 [SCREENSHOT] Taking screenshot for {host_name}/{device_id}")
        
        # Get host info
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({
                'success': False,
                'error': f'Host {host_name} not found'
            }), 404
        
        # Call host's takeScreenshot endpoint
        host_url = buildHostUrl(host_data, '/host/av/takeScreenshot')
        
        response = requests.post(
            host_url,
            json={'device_id': device_id},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('screenshot_url'):
                screenshot_url = result['screenshot_url']
                print(f"📸 [SCREENSHOT] Success! Redirecting to: {screenshot_url}")
                # Redirect to the screenshot image URL
                return redirect(screenshot_url, code=302)
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ [SCREENSHOT] Failed: {error}")
                return jsonify({
                    'success': False,
                    'error': f'Screenshot failed: {error}'
                }), 500
        else:
            error_msg = f'Host returned status {response.status_code}'
            print(f"❌ [SCREENSHOT] {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'raw_response': response.text[:500]  # First 500 chars for debugging
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"❌ [SCREENSHOT] Network error: {e}")
        return jsonify({
            'success': False,
            'error': f'Network error: {str(e)}'
        }), 500
    except Exception as e:
        print(f"❌ [SCREENSHOT] Unexpected error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to take screenshot: {str(e)}'
        }), 500
