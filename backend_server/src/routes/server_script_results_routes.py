"""
Script Results Management Routes

This module contains the script results management API endpoints for:
- Script results retrieval
- Script results filtering
"""

from flask import Blueprint, jsonify, request

# Import database functions from src/lib/supabase (uses absolute import)
from src.lib.supabase.script_results_db import (
    get_script_results,
    update_script_checked_status,
    update_script_discard_status
)

from shared.src.lib.utils.app_utils import check_supabase, get_team_id

# Create blueprint
server_script_results_bp = Blueprint('server_script_results', __name__, url_prefix='/server/script-results')

# =====================================================
# SCRIPT RESULTS ENDPOINTS
# =====================================================

@server_script_results_bp.route('/getAllScriptResults', methods=['GET'])
def get_all_script_results():
    """Get all script results for the team"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        # Get script results from database (include all records for complete view)
        result = get_script_results(team_id, include_discarded=True, limit=100)
        
        if result['success']:
            return jsonify(result['script_results'])
        else:
            return jsonify({'error': result.get('error', 'Failed to fetch script results')}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_script_results_bp.route('/updateCheckedStatus/<script_result_id>', methods=['PUT'])
def update_script_checked_status_route(script_result_id):
    """Update script result checked status"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        data = request.json
        checked = data.get('checked', False)
        check_type = data.get('check_type', 'manual')
        
        success = update_script_checked_status(team_id, script_result_id, checked, check_type)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Script result not found or failed to update'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_script_results_bp.route('/updateDiscardStatus/<script_result_id>', methods=['PUT'])
def update_script_discard_status_route(script_result_id):
    """Update script result discard status"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        data = request.json
        discard = data.get('discard', False)
        discard_comment = data.get('discard_comment')
        check_type = data.get('check_type', 'manual')
        
        success = update_script_discard_status(team_id, script_result_id, discard, discard_comment, check_type)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Script result not found or failed to update'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500 