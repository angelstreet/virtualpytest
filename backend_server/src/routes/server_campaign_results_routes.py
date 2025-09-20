"""
Campaign Results Management Routes

This module contains the campaign results management API endpoints for:
- Campaign results retrieval
- Campaign results filtering
"""

from flask import Blueprint, jsonify

# Import database functions from src/lib/supabase (uses absolute import)
from shared.src.lib.utils.campaign_executions_db import (
    get_campaign_results
)

from shared.src.lib.utils.app_utils import check_supabase, get_team_id

# Create blueprint
server_campaign_results_bp = Blueprint('server_campaign_results', __name__, url_prefix='/server/campaign-results')

# =====================================================
# CAMPAIGN RESULTS ENDPOINTS
# =====================================================

@server_campaign_results_bp.route('/getAllCampaignResults', methods=['GET'])
def get_all_campaign_results():
    """Get all campaign results for the team"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        # Get campaign results from database
        result = get_campaign_results(team_id, limit=100)
        
        if result['success']:
            return jsonify(result['data'])
        else:
            return jsonify({'error': result.get('error', 'Failed to fetch campaign results')}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Note: getCampaignScripts endpoint removed - script results now included in main campaign results