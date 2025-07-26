"""
Core API Routes

This module contains the core API endpoints for:
- Health check
- Feature status
"""

from flask import Blueprint, request, jsonify, current_app

# Import utility functions
from src.utils.app_utils import get_team_id

# Create blueprint
core_bp = Blueprint('core', __name__)

# =====================================================
# HEALTH CHECK ENDPOINT
# =====================================================

@core_bp.route('/server/health')
def health():
    """Health check endpoint with lazy-loaded feature status"""
    # Try to get Supabase (will load if not already loaded)
    try:
        from src.utils.supabase_utils import get_supabase_client
        supabase_client = get_supabase_client()
        supabase_status = "connected" if supabase_client else "disconnected"
    except Exception:
        supabase_status = "unavailable"
    
    return jsonify({
        'status': 'ok',
        'supabase': supabase_status,
        'team_id': get_team_id()
    })

@core_bp.route('/server/features')
def features():
    """Get status of all available features"""
    from src.utils.app_utils import (
        lazy_load_controllers, 
        lazy_load_adb_utils, 
        lazy_load_navigation, 
        lazy_load_device_models
    )
    from src.utils.supabase_utils import get_supabase_client
    
    features_status = {}
    
    # Check each feature
    try:
        features_status['supabase'] = get_supabase_client() is not None
    except Exception:
        features_status['supabase'] = False
        
    try:
        features_status['controllers'] = lazy_load_controllers() is not False
    except Exception:
        features_status['controllers'] = False
        
    try:
        features_status['adb_utils'] = lazy_load_adb_utils() is not None
    except Exception:
        features_status['adb_utils'] = False
        
    try:
        features_status['navigation'] = lazy_load_navigation() is not None
    except Exception:
        features_status['navigation'] = False
        
    try:
        features_status['device_models'] = lazy_load_device_models() is not None
    except Exception:
        features_status['device_models'] = False
    
    return jsonify({
        'features': features_status
    }) 