"""
Server Heatmap Routes

Provides heatmap-related API endpoints for the server.
These are server-side endpoints that interact directly with the database.
"""

from flask import Blueprint, request, jsonify
from shared.src.lib.supabase.heatmap_db import get_recent_heatmaps, save_heatmap_to_db
from shared.src.lib.utils.app_utils import check_supabase, get_team_id
from shared.src.lib.utils.cloudflare_utils import upload_heatmap_html
from backend_server.src.lib.utils.heatmap_report_utils import generate_comprehensive_heatmap_html
from datetime import datetime

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

@server_heatmap_bp.route('/generateReport', methods=['POST'])
def generate_html_report():
    """Generate HTML report for current heatmap frame."""
    # Check Supabase connection
    error = check_supabase()
    if error:
        return error
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        time_key = data.get('time_key')
        mosaic_url = data.get('mosaic_url')
        analysis_data = data.get('analysis_data')
        
        if not all([time_key, mosaic_url, analysis_data]):
            return jsonify({
                'success': False,
                'error': 'time_key, mosaic_url, and analysis_data are required'
            }), 400
        
        print(f"[@route:server_heatmap:generate_html_report] Generating HTML report for {time_key}")
        
        # Prepare heatmap data for HTML generation
        heatmap_data = [{
            'timestamp': f"{time_key[:2]}:{time_key[2:]}",
            'mosaic_url': mosaic_url,
            'analysis_data': analysis_data.get('devices', []),
            'incidents': []
        }]
        
        # Generate HTML content
        html_content = generate_comprehensive_heatmap_html(heatmap_data)
        
        # Upload HTML to R2
        html_result = upload_heatmap_html(html_content, time_key)
        
        if not html_result['success']:
            return jsonify({
                'success': False,
                'error': f'Failed to upload HTML: {html_result.get("error", "Unknown error")}'
            }), 500
        
        # Save to database
        team_id = get_team_id()
        timestamp = datetime.now().isoformat()
        
        heatmap_id = save_heatmap_to_db(
            team_id=team_id,
            timestamp=timestamp,
            job_id=f"report_{time_key}_{int(datetime.now().timestamp())}",
            mosaic_r2_path=f"heatmaps/{time_key}.jpg",
            mosaic_r2_url=mosaic_url,
            metadata_r2_path=f"heatmaps/{time_key}.json",
            metadata_r2_url=data.get('analysis_url', ''),
            html_r2_path=html_result['html_path'],
            html_r2_url=html_result['html_url'],
            hosts_included=len(analysis_data.get('devices', [])),
            hosts_total=len(analysis_data.get('devices', [])),
            incidents_count=analysis_data.get('incidents_count', 0)
        )
        
        if heatmap_id:
            print(f"[@route:server_heatmap:generate_html_report] Report saved to database with ID: {heatmap_id}")
        else:
            print(f"[@route:server_heatmap:generate_html_report] Warning: Failed to save to database")
        
        return jsonify({
            'success': True,
            'html_url': html_result['html_url'],
            'heatmap_id': heatmap_id
        }), 200
        
    except Exception as e:
        print(f"[@route:server_heatmap:generate_html_report] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500
