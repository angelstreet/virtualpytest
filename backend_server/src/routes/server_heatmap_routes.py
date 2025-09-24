"""
Server Heatmap Routes

Provides heatmap-related API endpoints for the server.
These are server-side endpoints that interact directly with the database.
"""

from flask import Blueprint, request, jsonify
from shared.src.lib.supabase.heatmap_db import get_recent_heatmaps
from shared.src.lib.utils.app_utils import check_supabase

# Create blueprint
server_heatmap_bp = Blueprint('server_heatmap', __name__, url_prefix='/server/heatmap')

@server_heatmap_bp.route('/history', methods=['GET'])
def get_heatmap_history():
    """Get recent heatmap reports for a team."""
    # Check Supabase connection
    error = check_supabase()
    if error:
        return error
    
    try:
        # Get parameters from query string
        team_id = request.args.get('team_id')
        limit = request.args.get('limit', 10, type=int)
        
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id parameter is required'
            }), 400
        
        print(f"[@route:server_heatmap:get_heatmap_history] Getting {limit} recent heatmaps for team: {team_id}")
        
        # Get recent heatmaps from database
        heatmaps = get_recent_heatmaps(team_id, limit)
        
        return jsonify({
            'success': True,
            'reports': heatmaps,
            'count': len(heatmaps)
        }), 200
        
    except Exception as e:
        print(f"[@route:server_heatmap:get_heatmap_history] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500
