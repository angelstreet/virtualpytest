"""
Campaign API Routes

This module contains the campaign management endpoints for:
- Creating campaigns
- Retrieving campaigns
- Updating campaigns
- Deleting campaigns
"""

from flask import Blueprint, request, jsonify, current_app

# Import utility functions
from shared.src.lib.utils.app_utils import get_team_id

# Import database functions from src/lib/supabase (uses absolute import)
from shared.src.lib.config.supabase.campaign_executions_db import (
    get_campaign_results
)

from shared.src.lib.utils.app_utils import check_supabase

# Create blueprint with abstract server campaign prefix
server_campaign_bp = Blueprint('server_campaign', __name__, url_prefix='/server/campaigns')

# Helper functions (these should be imported from a shared module)
def get_user_id():
    '''Get user_id from request headers - FAIL FAST if not provided'''
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise ValueError('X-User-ID header is required but not provided')
    return user_id

# =====================================================
# CAMPAIGN ENDPOINTS WITH CONSISTENT NAMING
# =====================================================

@server_campaign_bp.route('/getAllCampaigns', methods=['GET'])
def get_all_campaigns_route():
    """Get all campaigns for a team"""
    # Log caller information to identify source
    user_agent = request.headers.get('User-Agent', 'Unknown')
    referer = request.headers.get('Referer', 'Unknown')
    x_requested_with = request.headers.get('X-Requested-With', 'Unknown')
    print(f"[@server_campaign_routes:getAllCampaigns] 🔍 CALLER INFO:")
    print(f"  - User-Agent: {user_agent}")
    print(f"  - Referer: {referer}")
    print(f"  - X-Requested-With: {x_requested_with}")
    print(f"  - Remote Address: {request.remote_addr}")
    
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        # Campaign templates are not stored in database - they are just configurations
        # Return empty list for now, or implement campaign template storage if needed
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_campaign_bp.route('/getCampaign/<campaign_id>', methods=['GET'])
def get_campaign_route(campaign_id):
    """Get a specific campaign by ID"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        # Campaign templates are not stored in database - they are just configurations
        # Return empty object for now, or implement campaign template storage if needed
        return jsonify({})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_campaign_bp.route('/createCampaign', methods=['POST'])
def create_campaign_route():
    """Create a new campaign"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    user_id = get_user_id()
    
    try:
        campaign = request.json
        # Campaign templates are not stored in database - they are just configurations
        # Return success for now, or implement campaign template storage if needed
        return jsonify({'status': 'success', 'campaign_id': campaign.get('campaign_id', 'template-campaign')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_campaign_bp.route('/updateCampaign/<campaign_id>', methods=['PUT'])
def update_campaign_route(campaign_id):
    """Update an existing campaign"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    user_id = get_user_id()
    
    try:
        campaign = request.json
        # Campaign templates are not stored in database - they are just configurations
        # Return success for now, or implement campaign template storage if needed
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_campaign_bp.route('/deleteCampaign/<campaign_id>', methods=['DELETE'])
def delete_campaign_route(campaign_id):
    """Delete a campaign"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        # Campaign templates are not stored in database - they are just configurations
        # Return success for now, or implement campaign template storage if needed
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500 