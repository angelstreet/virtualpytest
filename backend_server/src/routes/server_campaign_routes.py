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
from shared.src.lib.supabase.campaign_executions_db import (
    get_campaign_results
)

from shared.src.lib.utils.app_utils import check_supabase

# Create blueprint with abstract server campaign prefix
server_campaign_bp = Blueprint('server_campaign', __name__, url_prefix='/server/campaigns')

# Legacy helper functions moved to services/campaign_service.py
# All business logic has been extracted to the service layer

# =====================================================
# CAMPAIGN ENDPOINTS WITH CONSISTENT NAMING
# =====================================================

@server_campaign_bp.route('/getAllCampaigns', methods=['GET'])
def get_all_campaigns_route():
    """Get all campaigns for a team"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        user_agent = request.headers.get('User-Agent', 'Unknown')
        referer = request.headers.get('Referer', 'Unknown')
        
        # Delegate to service layer
        from services.campaign_service import campaign_service
        result = campaign_service.get_all_campaigns(team_id, user_agent, referer)
        
        # Return HTTP response
        if result['success']:
            return jsonify(result['campaigns'])
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_campaign_bp.route('/getCampaign/<campaign_id>', methods=['GET'])
def get_campaign_route(campaign_id):
    """Get a specific campaign by ID"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        
        # Delegate to service layer
        from services.campaign_service import campaign_service
        result = campaign_service.get_campaign(campaign_id, team_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify(result['campaign'])
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_campaign_bp.route('/createCampaign', methods=['POST'])
def create_campaign_route():
    """Create a new campaign"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        user_id = request.headers.get('X-User-ID')
        campaign_data = request.json
        
        # Delegate to service layer
        from services.campaign_service import campaign_service
        result = campaign_service.create_campaign(campaign_data, team_id, user_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify({'status': 'success', 'campaign': result['campaign']})
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_campaign_bp.route('/updateCampaign/<campaign_id>', methods=['PUT'])
def update_campaign_route(campaign_id):
    """Update an existing campaign"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        user_id = request.headers.get('X-User-ID')
        campaign_data = request.json
        
        # Delegate to service layer
        from services.campaign_service import campaign_service
        result = campaign_service.update_campaign(campaign_id, campaign_data, team_id, user_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify({'status': 'success', 'campaign': result['campaign']})
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_campaign_bp.route('/deleteCampaign/<campaign_id>', methods=['DELETE'])
def delete_campaign_route(campaign_id):
    """Delete a campaign"""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        user_id = request.headers.get('X-User-ID')
        
        # Delegate to service layer
        from services.campaign_service import campaign_service
        result = campaign_service.delete_campaign(campaign_id, team_id, user_id)
        
        # Return HTTP response
        if result['success']:
            return jsonify({'status': 'success'})
        else:
            status_code = result.get('status_code', 500)
            return jsonify({'error': result['error']}), status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500 