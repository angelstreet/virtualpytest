"""
Core API Routes

This module contains the core API endpoints for:
- Health check
- Feature status
"""

from flask import Blueprint, request, jsonify, current_app

# Import utility functions
from shared.src.lib.utils.app_utils import get_team_id

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
