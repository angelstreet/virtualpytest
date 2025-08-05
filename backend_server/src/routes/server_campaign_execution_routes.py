"""
Campaign Execution API Routes

This module contains the campaign execution endpoints for:
- Executing campaigns
- Getting campaign execution results
- Managing campaign executions
"""

from flask import Blueprint, request, jsonify, current_app
import threading
import time
from typing import Dict, Any

# Import utility functions
from shared.lib.utils.app_utils import get_team_id
from shared.lib.utils.campaign_executor import CampaignExecutor

# Import database functions
from shared.lib.supabase.campaign_executions_db import (
    get_campaign_execution_with_scripts,
    get_campaign_results
)

from shared.lib.utils.app_utils import check_supabase

# Create blueprint
server_campaign_execution_bp = Blueprint('server_campaign_execution', __name__, url_prefix='/server/campaigns')

# Helper functions
def get_user_id():
    '''Get user_id from request headers - FAIL FAST if not provided'''
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise ValueError('X-User-ID header is required but not provided')
    return user_id

# Global dictionary to track running campaigns
running_campaigns = {}

def execute_campaign_async(campaign_config: Dict[str, Any], execution_id: str):
    """Execute campaign asynchronously"""
    try:
        executor = CampaignExecutor()
        result = executor.execute_campaign(campaign_config)
        
        # Update running campaigns status
        if execution_id in running_campaigns:
            running_campaigns[execution_id].update({
                'status': 'completed',
                'result': result,
                'completed_at': time.time()
            })
    except Exception as e:
        # Update running campaigns with error
        if execution_id in running_campaigns:
            running_campaigns[execution_id].update({
                'status': 'failed',
                'error': str(e),
                'completed_at': time.time()
            })

# =====================================================
# CAMPAIGN EXECUTION ENDPOINTS
# =====================================================

@server_campaign_execution_bp.route('/execute', methods=['POST'])
def execute_campaign():
    """Execute a campaign with multiple scripts"""
    try:
        # Check Supabase connection
        supabase_check = check_supabase()
        if not supabase_check['success']:
            return jsonify({
                'success': False,
                'error': f"Supabase connection failed: {supabase_check['error']}"
            }), 500
        
        # Get team_id
        user_id = get_user_id()
        team_id = get_team_id(user_id)
        
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'Could not determine team_id for user'
            }), 400
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Validate required fields
        required_fields = ['campaign_id', 'name', 'script_configurations']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate script configurations
        script_configs = data.get('script_configurations', [])
        if not script_configs:
            return jsonify({
                'success': False,
                'error': 'At least one script configuration is required'
            }), 400
        
        for i, script_config in enumerate(script_configs):
            if 'script_name' not in script_config:
                return jsonify({
                    'success': False,
                    'error': f'script_name is required for script configuration {i+1}'
                }), 400
        
        # Check if campaign is already running
        campaign_id = data['campaign_id']
        execution_id = f"{campaign_id}_{int(time.time())}"
        
        # Add team_id to campaign config (not exposed in API but needed internally)
        campaign_config = data.copy()
        campaign_config['team_id'] = team_id
        
        # Determine execution mode
        async_execution = data.get('async', True)
        
        if async_execution:
            # Execute asynchronously
            running_campaigns[execution_id] = {
                'campaign_id': campaign_id,
                'execution_id': execution_id,
                'status': 'running',
                'started_at': time.time(),
                'campaign_config': campaign_config
            }
            
            # Start campaign execution in background thread
            thread = threading.Thread(
                target=execute_campaign_async,
                args=(campaign_config, execution_id)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'success': True,
                'message': 'Campaign execution started',
                'execution_id': execution_id,
                'campaign_id': campaign_id,
                'async': True,
                'status': 'running'
            }), 202
        
        else:
            # Execute synchronously
            executor = CampaignExecutor()
            result = executor.execute_campaign(campaign_config)
            
            return jsonify({
                'success': True,
                'message': 'Campaign execution completed',
                'campaign_id': campaign_id,
                'async': False,
                'result': result
            }), 200
            
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error executing campaign: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Campaign execution failed: {str(e)}'
        }), 500


@server_campaign_execution_bp.route('/status/<execution_id>', methods=['GET'])
def get_campaign_execution_status(execution_id: str):
    """Get status of a running campaign execution"""
    try:
        if execution_id not in running_campaigns:
            return jsonify({
                'success': False,
                'error': 'Campaign execution not found'
            }), 404
        
        campaign_info = running_campaigns[execution_id]
        
        # Calculate runtime
        start_time = campaign_info.get('started_at', time.time())
        current_time = time.time()
        runtime_seconds = int(current_time - start_time)
        
        response_data = {
            'success': True,
            'execution_id': execution_id,
            'campaign_id': campaign_info['campaign_id'],
            'status': campaign_info['status'],
            'runtime_seconds': runtime_seconds
        }
        
        # Add result if completed
        if campaign_info['status'] in ['completed', 'failed']:
            if 'result' in campaign_info:
                response_data['result'] = campaign_info['result']
            if 'error' in campaign_info:
                response_data['error'] = campaign_info['error']
            if 'completed_at' in campaign_info:
                total_time = int(campaign_info['completed_at'] - start_time)
                response_data['total_time_seconds'] = total_time
        
        return jsonify(response_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting campaign status: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get campaign status: {str(e)}'
        }), 500


@server_campaign_execution_bp.route('/results', methods=['GET'])
def get_all_campaign_results():
    """Get all campaign results for a team"""
    try:
        # Check Supabase connection
        supabase_check = check_supabase()
        if not supabase_check['success']:
            return jsonify({
                'success': False,
                'error': f"Supabase connection failed: {supabase_check['error']}"
            }), 500
        
        # Get team_id
        user_id = get_user_id()
        team_id = get_team_id(user_id)
        
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'Could not determine team_id for user'
            }), 400
        
        # Get query parameters
        campaign_id = request.args.get('campaign_id')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        # Get campaign results from database
        results = get_campaign_results(
            team_id=team_id,
            campaign_id=campaign_id,
            status=status,
            limit=limit
        )
        
        if not results['success']:
            return jsonify({
                'success': False,
                'error': results.get('error', 'Failed to get campaign results')
            }), 500
        
        return jsonify({
            'success': True,
            'campaign_results': results['campaign_results'],
            'count': results['count']
        }), 200
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error getting campaign results: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get campaign results: {str(e)}'
        }), 500


@server_campaign_execution_bp.route('/results/<campaign_result_id>', methods=['GET'])
def get_campaign_result_details(campaign_result_id: str):
    """Get detailed campaign result including script executions"""
    try:
        # Check Supabase connection
        supabase_check = check_supabase()
        if not supabase_check['success']:
            return jsonify({
                'success': False,
                'error': f"Supabase connection failed: {supabase_check['error']}"
            }), 500
        
        # Get team_id
        user_id = get_user_id()
        team_id = get_team_id(user_id)
        
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'Could not determine team_id for user'
            }), 400
        
        # Get campaign execution summary
        summary = get_campaign_execution_summary(
            team_id=team_id,
            campaign_result_id=campaign_result_id
        )
        
        if not summary['success']:
            return jsonify({
                'success': False,
                'error': summary.get('error', 'Failed to get campaign summary')
            }), 500 if 'not found' not in summary.get('error', '').lower() else 404
        
        return jsonify({
            'success': True,
            'campaign_result': summary['campaign_result'],
            'script_executions': summary['script_executions']
        }), 200
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error getting campaign result details: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get campaign result details: {str(e)}'
        }), 500


@server_campaign_execution_bp.route('/running', methods=['GET'])
def get_running_campaigns():
    """Get list of currently running campaigns"""
    try:
        # Filter out completed campaigns older than 1 hour
        import time
        current_time = time.time()
        hour_ago = current_time - 3600
        
        active_campaigns = {}
        for execution_id, campaign_info in running_campaigns.items():
            # Keep running campaigns and recently completed ones
            if (campaign_info['status'] == 'running' or 
                (campaign_info.get('completed_at', current_time) > hour_ago)):
                
                # Calculate runtime
                start_time = campaign_info.get('started_at', current_time)
                runtime_seconds = int(current_time - start_time)
                
                active_campaigns[execution_id] = {
                    'execution_id': execution_id,
                    'campaign_id': campaign_info['campaign_id'],
                    'status': campaign_info['status'],
                    'started_at': campaign_info['started_at'],
                    'runtime_seconds': runtime_seconds
                }
                
                if campaign_info['status'] in ['completed', 'failed']:
                    if 'completed_at' in campaign_info:
                        total_time = int(campaign_info['completed_at'] - start_time)
                        active_campaigns[execution_id]['total_time_seconds'] = total_time
        
        return jsonify({
            'success': True,
            'running_campaigns': list(active_campaigns.values()),
            'count': len(active_campaigns)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting running campaigns: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get running campaigns: {str(e)}'
        }), 500