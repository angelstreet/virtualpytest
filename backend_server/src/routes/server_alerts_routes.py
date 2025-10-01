"""
Alerts Management Routes

This module contains the alerts management API endpoints for:
- Active alerts retrieval
- Closed alerts retrieval
- Alert filtering
"""

from flask import Blueprint, jsonify, request

# Import database functions from src/lib/supabase (uses absolute import)
from shared.src.lib.supabase.alerts_db import (
    get_all_alerts,
    get_active_alerts,
    get_closed_alerts,
    update_alert_checked_status,
    update_alert_discard_status,
    delete_all_alerts
)

from shared.src.lib.utils.app_utils import check_supabase

# Create blueprint
server_alerts_bp = Blueprint('server_alerts', __name__, url_prefix='/server/alerts')

# =====================================================
# ALERTS ENDPOINTS
# =====================================================

@server_alerts_bp.route('/getAllAlerts', methods=['GET'])
def get_all_alerts_endpoint():
    """Get all alerts (both active and resolved) - optimized single query.
    
    Optional query parameters:
    - host_name: Filter by specific host
    - device_id: Filter by specific device
    - incident_type: Filter by incident type
    - limit: Maximum number of alerts to return (default: 200)
    """
    try:
        # Get optional query parameters
        host_name = request.args.get('host_name')
        device_id = request.args.get('device_id') 
        incident_type = request.args.get('incident_type')
        limit = int(request.args.get('limit', 200))
        
        print("[@routes:server_alerts:getAllAlerts] Getting all alerts with optional filters:")
        print(f"  - host_name: {host_name}")
        print(f"  - device_id: {device_id}")
        print(f"  - incident_type: {incident_type}")
        print(f"  - limit: {limit}")
        
        result = get_all_alerts(
            host_name=host_name,
            device_id=device_id, 
            incident_type=incident_type,
            limit=limit
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'alerts': result['alerts'],
                'count': result['count']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'alerts': [],
                'count': 0
            }), 500
            
    except Exception as e:
        print(f"[@routes:server_alerts:getAllAlerts] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'alerts': [],
            'count': 0
        }), 500

@server_alerts_bp.route('/getActiveAlerts', methods=['GET'])
def get_all_active_alerts():
    """Get all active alerts."""
    try:
        print("[@routes:server_alerts:getActiveAlerts] Getting active alerts")
        
        result = get_active_alerts()
        
        if result['success']:
            return jsonify({
                'success': True,
                'alerts': result['alerts'],
                'count': result['count']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'alerts': [],
                'count': 0
            }), 500
            
    except Exception as e:
        print(f"[@routes:server_alerts:getActiveAlerts] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'alerts': [],
            'count': 0
        }), 500

@server_alerts_bp.route('/getClosedAlerts', methods=['GET'])
def get_all_closed_alerts():
    """Get all closed/resolved alerts."""
    try:
        print("[@routes:server_alerts:getClosedAlerts] Getting closed alerts")
        
        result = get_closed_alerts()
        
        if result['success']:
            return jsonify({
                'success': True,
                'alerts': result['alerts'],
                'count': result['count']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'alerts': [],
                'count': 0
            }), 500
            
    except Exception as e:
        print(f"[@routes:server_alerts:getClosedAlerts] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'alerts': [],
            'count': 0
        }), 500

@server_alerts_bp.route('/updateCheckedStatus/<alert_id>', methods=['PUT'])
def update_alert_checked_status_route(alert_id):
    """Update alert checked status"""
    error = check_supabase()
    if error:
        return error
    
    try:
        data = request.json
        checked = data.get('checked', False)
        check_type = data.get('check_type', 'manual')
        
        success = update_alert_checked_status(alert_id, checked, check_type)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Alert not found or failed to update'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_alerts_bp.route('/updateDiscardStatus/<alert_id>', methods=['PUT'])
def update_alert_discard_status_route(alert_id):
    """Update alert discard status"""
    error = check_supabase()
    if error:
        return error
    
    try:
        data = request.json
        discard = data.get('discard', False)
        discard_comment = data.get('discard_comment')
        check_type = data.get('check_type', 'manual')
        
        success = update_alert_discard_status(alert_id, discard, discard_comment, check_type)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Alert not found or failed to update'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@server_alerts_bp.route('/deleteAllAlerts', methods=['DELETE'])
def delete_all_alerts_route():
    """Delete all alerts from the database"""
    error = check_supabase()
    if error:
        return error
    
    try:
        print("[@routes:server_alerts:deleteAllAlerts] Deleting all alerts")
        
        result = delete_all_alerts()
        
        if result['success']:
            return jsonify({
                'success': True,
                'deleted_count': result['deleted_count'],
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'deleted_count': 0
            }), 500
            
    except Exception as e:
        print(f"[@routes:server_alerts:deleteAllAlerts] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'deleted_count': 0
        }), 500 