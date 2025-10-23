"""
Server Heatmap Routes

Provides heatmap-related API endpoints for the server.
These are server-side endpoints that interact directly with the database.
"""

from flask import Blueprint, request, jsonify
from shared.src.lib.database.heatmap_db import get_recent_heatmaps, save_heatmap_to_db
from shared.src.lib.utils.app_utils import check_supabase, get_team_id
from shared.src.lib.utils.cloudflare_utils import upload_heatmap_html
from backend_server.src.lib.utils.heatmap_report_utils import generate_comprehensive_heatmap_html
from datetime import datetime, timedelta
from uuid import uuid4
import os

# Create blueprint
server_heatmap_bp = Blueprint('server_heatmap', __name__, url_prefix='/server/heatmap')

def generate_previous_time_keys(selected_time_key: str, count: int = 9) -> list:
    """Generate the previous N time keys before the selected one"""
    try:
        # Parse the time key (format: "HHMM")
        hour = int(selected_time_key[:2])
        minute = int(selected_time_key[2:])
        
        # Create datetime for the selected time (using today as base)
        base_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        time_keys = []
        for i in range(count):
            # Go back i+1 minutes from the selected time
            prev_time = base_time - timedelta(minutes=i+1)
            time_key = f"{prev_time.hour:02d}{prev_time.minute:02d}"
            time_keys.append(time_key)
        
        return time_keys
    except Exception as e:
        print(f"[@generate_previous_time_keys] Error: {e}")
        return []

def generate_timeline_heatmap_data(selected_time_key: str, selected_mosaic_url: str, selected_devices: list, selected_incidents_count: int) -> list:
    """Generate heatmap data for selected mosaic + 9 previous mosaics with actual analysis data"""
    import requests
    
    try:
        # Get R2 base URL from environment
        R2_BASE_URL = os.getenv('CLOUDFLARE_R2_PUBLIC_URL', '')
        
        heatmap_data = []
        
        # Get previous 9 time keys first (these will be on the left)
        previous_time_keys = generate_previous_time_keys(selected_time_key, 9)
        
        for time_key in previous_time_keys:
            # Generate URLs for previous mosaics (they may or may not exist)
            mosaic_url = f"{R2_BASE_URL}/heatmaps/{time_key}.jpg"
            analysis_url = f"{R2_BASE_URL}/heatmaps/{time_key}.json"
            
            # Try to fetch actual analysis data from R2
            analysis_data = []
            incidents_count = 0
            
            try:
                print(f"[@generate_timeline_heatmap_data] Fetching analysis data for {time_key} from {analysis_url}")
                response = requests.get(analysis_url, timeout=5)
                if response.status_code == 200:
                    json_data = response.json()
                    analysis_data = json_data.get('devices', [])
                    incidents_count = json_data.get('incidents_count', 0)
                    print(f"[@generate_timeline_heatmap_data] Successfully loaded {len(analysis_data)} devices for {time_key}")
                else:
                    print(f"[@generate_timeline_heatmap_data] No analysis data found for {time_key} (HTTP {response.status_code})")
            except Exception as fetch_error:
                print(f"[@generate_timeline_heatmap_data] Failed to fetch analysis for {time_key}: {fetch_error}")
            
            heatmap_data.append({
                'timestamp': f"{time_key[:2]}:{time_key[2:]}",
                'mosaic_url': mosaic_url,
                'analysis_data': analysis_data,  # Now populated with actual data if available
                'incidents': [],
                'incidents_count': incidents_count,  # Now populated with actual count
                'is_selected': False,
                'analysis_url': analysis_url
            })
        
        # Add the selected mosaic last (this will be on the far right)
        heatmap_data.append({
            'timestamp': f"{selected_time_key[:2]}:{selected_time_key[2:]}",
            'mosaic_url': selected_mosaic_url,
            'analysis_data': selected_devices,
            'incidents': [],
            'incidents_count': selected_incidents_count,
            'is_selected': True  # Mark as the selected frame
        })
        
        print(f"[@generate_timeline_heatmap_data] Generated timeline with {len(heatmap_data)} frames")
        return heatmap_data
        
    except Exception as e:
        print(f"[@generate_timeline_heatmap_data] Error: {e}")
        # Fallback to single frame
        return [{
            'timestamp': f"{selected_time_key[:2]}:{selected_time_key[2:]}",
            'mosaic_url': selected_mosaic_url,
            'analysis_data': selected_devices,
            'incidents': [],
            'incidents_count': selected_incidents_count
        }]

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
        include_timeline = data.get('include_timeline', True)  # Default to timeline report
        
        if not all([time_key, mosaic_url, analysis_data]):
            return jsonify({
                'success': False,
                'error': 'time_key, mosaic_url, and analysis_data are required'
            }), 400
        
        print(f"[@route:server_heatmap:generate_html_report] Generating HTML report for {time_key} (timeline: {include_timeline})")
        
        # Use the incidents_count from the analysis_data that was already calculated
        incidents_count = analysis_data.get('incidents_count', 0)
        devices = analysis_data.get('devices', [])
        
        print(f"[@route:server_heatmap:generate_html_report] Using incidents_count from analysis_data: {incidents_count}")
        
        # Generate timeline data if requested
        if include_timeline:
            heatmap_data = generate_timeline_heatmap_data(time_key, mosaic_url, devices, incidents_count)
        else:
            # Single frame report (original behavior)
            heatmap_data = [{
                'timestamp': f"{time_key[:2]}:{time_key[2:]}",
                'mosaic_url': mosaic_url,
                'analysis_data': devices,
                'incidents': [],  # Keep empty as incidents are already counted in analysis_data
                'incidents_count': incidents_count
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
        
        # Extract R2 paths from the mosaic_url (includes server path)
        # mosaic_url format: https://r2.dev/heatmaps/server-path/1800.jpg
        # We need to extract "heatmaps/server-path/1800.jpg"
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(mosaic_url)
            mosaic_r2_path = parsed_url.path.lstrip('/')  # Remove leading slash
            # Extract server path from mosaic_r2_path (e.g., "heatmaps/server-path" from "heatmaps/server-path/1800.jpg")
            path_parts = mosaic_r2_path.split('/')
            if len(path_parts) >= 3:
                server_path = path_parts[1]  # Extract "server-path"
                metadata_r2_path = f"heatmaps/{server_path}/{time_key}.json"
            else:
                # Fallback if path structure is unexpected
                metadata_r2_path = f"heatmaps/{time_key}.json"
        except Exception as e:
            print(f"[@route:server_heatmap:generate_html_report] Warning: Could not parse mosaic URL: {e}")
            mosaic_r2_path = f"heatmaps/{time_key}.jpg"
            metadata_r2_path = f"heatmaps/{time_key}.json"
        
        # Save to database
        team_id = get_team_id()
        timestamp = datetime.now().isoformat()
        job_id = str(uuid4())  # Generate proper UUID for job_id
        
        print(f"[@route:server_heatmap:generate_html_report] Saving to DB with job_id: {job_id}")
        
        heatmap_id = save_heatmap_to_db(
            team_id=team_id,
            timestamp=timestamp,
            job_id=job_id,
            mosaic_r2_path=mosaic_r2_path,
            mosaic_r2_url=mosaic_url,
            metadata_r2_path=metadata_r2_path,
            metadata_r2_url=data.get('analysis_url', ''),
            html_r2_path=html_result['html_path'],
            html_r2_url=html_result['html_url'],
            hosts_included=len(analysis_data.get('devices', [])),
            hosts_total=len(analysis_data.get('devices', [])),
            incidents_count=incidents_count
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
