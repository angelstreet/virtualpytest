"""
Host Heatmap Routes

Minimalist host-side heatmap endpoint that returns raw file data with analysis.
"""

from flask import Blueprint, request, jsonify
import os
import time
import json
from utils.host_utils import get_controller
from utils.analysis_utils import load_recent_analysis_data

# Create blueprint
host_heatmap_bp = Blueprint('host_heatmap', __name__, url_prefix='/host/heatmap')

@host_heatmap_bp.route('/listRecentAnalysis', methods=['POST'])
def list_recent_analysis():
    """List recent capture files with analysis data"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        timeframe_minutes = data.get('timeframe_minutes', 1)
        
        # Use shared utility function
        result = load_recent_analysis_data(device_id, timeframe_minutes)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 