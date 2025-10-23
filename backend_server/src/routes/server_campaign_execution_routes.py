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
import requests
from typing import Dict, Any

# Import utility functions

from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params, get_host_from_request
from  backend_server.src.lib.utils.task_manager import task_manager
from shared.src.lib.utils.build_url_utils import buildHostUrl, buildServerUrl

# Import database functions
from shared.src.lib.database.campaign_executions_db import (
    get_campaign_execution_with_scripts,
    get_campaign_results
)

from shared.src.lib.utils.app_utils import check_supabase

# Create blueprint
server_campaign_execution_bp = Blueprint('server_campaign_execution', __name__, url_prefix='/server/campaigns')

# Helper functions
def get_user_id():
    '''Get user_id from request headers - FAIL FAST if not provided'''
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise ValueError('X-User-ID header is required but not provided')
    return user_id

# Global dictionary to track running campaigns (now used for proxy tracking)
running_campaigns = {}

def execute_campaign_async_proxy(campaign_config: Dict[str, Any], execution_id: str, host_info: Dict[str, Any]):
    """Execute campaign asynchronously via proxy to host"""
    try:
        print(f"[@server_campaign] Starting async proxy execution for campaign: {execution_id}")
        
        # Build callback URL for host to notify server when complete
        callback_url = buildServerUrl('/server/campaigns/callback')
        
        # Add callback URL and task info to campaign config
        proxy_config = campaign_config.copy()
        proxy_config['callback_url'] = callback_url
        proxy_config['task_id'] = execution_id
        proxy_config['async'] = True
        
        # Build host URL for campaign execution
        host_url = buildHostUrl(host_info, '/host/campaigns/execute')
        
        print(f"[@server_campaign] Proxying to host: {host_url}")
        print(f"[@server_campaign] Callback URL: {callback_url}")
        
        # Make request to host
        response = requests.post(
            host_url,
            json=proxy_config,
            timeout=120  # 2 minutes timeout for initial response
        )
        
        if response.status_code in [200, 202]:
            result = response.json()
            print(f"[@server_campaign] Host accepted campaign execution: {result}")
            
            # Update running campaigns with host response
            if execution_id in running_campaigns:
                running_campaigns[execution_id].update({
                    'status': 'running',
                    'host_execution_id': result.get('execution_id'),
                    'host_response': result
                })
        else:
            error_msg = f"Host rejected campaign execution: {response.status_code} {response.text}"
            print(f"[@server_campaign] {error_msg}")
            
            # Update running campaigns with error
            if execution_id in running_campaigns:
                running_campaigns[execution_id].update({
                    'status': 'failed',
                    'error': error_msg,
                    'completed_at': time.time()
                })
        
    except Exception as e:
        error_msg = f"Error proxying campaign to host: {str(e)}"
        print(f"[@server_campaign] {error_msg}")
        
        # Update running campaigns with error
        if execution_id in running_campaigns:
            running_campaigns[execution_id].update({
                'status': 'failed',
                'error': error_msg,
                'completed_at': time.time()
            })

# =====================================================
# CAMPAIGN EXECUTION ENDPOINTS
# =====================================================

@server_campaign_execution_bp.route('/execute', methods=['POST'])
def execute_campaign():
    """Execute a campaign with multiple scripts - proxy to host"""
    try:
        print(f"[@server_campaign:execute_campaign] Received campaign execution request")
        
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
        
        # Get host information from request
        host_info, error = get_host_from_request()
        if not host_info:
            return jsonify({
                'success': False,
                'error': error or 'Host information required for campaign execution'
            }), 400
        
        print(f"[@server_campaign:execute_campaign] Target host: {host_info.get('host_name')}")
        
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
        
        # Generate execution ID
        campaign_id = data['campaign_id']
        execution_id = f"{campaign_id}_{int(time.time())}"
        
        print(f"[@server_campaign:execute_campaign] Campaign: {campaign_id}")
        print(f"[@server_campaign:execute_campaign] Execution ID: {execution_id}")
        print(f"[@server_campaign:execute_campaign] Scripts: {len(script_configs)}")
        
        # Add team_id to campaign config (not exposed in API but needed internally)
        campaign_config = data.copy()
        campaign_config['team_id'] = team_id
        
        # Remove host from campaign config before sending to host (host doesn't need its own info)
        campaign_config.pop('host', None)
        
        # Determine execution mode
        async_execution = data.get('async', True)
        
        if async_execution:
            # Execute asynchronously via proxy
            running_campaigns[execution_id] = {
                'campaign_id': campaign_id,
                'execution_id': execution_id,
                'status': 'starting',
                'started_at': time.time(),
                'campaign_config': campaign_config,
                'host_name': host_info.get('host_name')
            }
            
            # Start campaign execution proxy in background thread
            thread = threading.Thread(
                target=execute_campaign_async_proxy,
                args=(campaign_config, execution_id, host_info)
            )
            thread.daemon = True
            thread.start()
            
            print(f"[@server_campaign:execute_campaign] Started async proxy execution")
            
            return jsonify({
                'success': True,
                'message': 'Campaign execution started via proxy to host',
                'execution_id': execution_id,
                'campaign_id': campaign_id,
                'host_name': host_info.get('host_name'),
                'async': True,
                'status': 'starting'
            }), 202
        
        else:
            # Execute synchronously via proxy
            print(f"[@server_campaign:execute_campaign] Starting sync proxy execution")
            
            # Add callback URL and task info to campaign config
            callback_url = buildServerUrl('/server/campaigns/callback')
            proxy_config = campaign_config.copy()
            proxy_config['callback_url'] = callback_url
            proxy_config['task_id'] = execution_id
            proxy_config['async'] = False
            
            # Proxy to host
            response_data, status_code = proxy_to_host_with_params('/host/campaigns/execute', 'POST', proxy_config, {})
            
            print(f"[@server_campaign:execute_campaign] Sync proxy execution completed")
            
            return jsonify(response_data), status_code
            
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error executing campaign: {str(e)}")
        print(f"[@server_campaign:execute_campaign] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Campaign execution failed: {str(e)}'
        }), 500


@server_campaign_execution_bp.route('/status/<execution_id>', methods=['GET'])
def get_campaign_execution_status(execution_id: str):
    """Get status of a running campaign execution - proxy to host if needed"""
    try:
        print(f"[@server_campaign:get_status] Checking status for: {execution_id}")
        
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
            'runtime_seconds': runtime_seconds,
            'host_name': campaign_info.get('host_name')
        }
        
        # Add result if completed (from host callback)
        if campaign_info['status'] in ['completed', 'failed']:
            if 'host_result' in campaign_info:
                response_data['result'] = campaign_info['host_result']
            if 'host_error' in campaign_info:
                response_data['error'] = campaign_info['host_error']
            if 'error' in campaign_info:  # Server-side error
                response_data['server_error'] = campaign_info['error']
            if 'completed_at' in campaign_info:
                total_time = int(campaign_info['completed_at'] - start_time)
                response_data['total_time_seconds'] = total_time
        
        # If still running, try to get status from host
        elif campaign_info['status'] == 'running' and campaign_info.get('host_execution_id'):
            try:
                # Try to get status from host
                host_name = campaign_info.get('host_name')
                host_execution_id = campaign_info.get('host_execution_id')
                
                if host_name and host_execution_id:
                    print(f"[@server_campaign:get_status] Checking host status: {host_name}/{host_execution_id}")
                    
                    # Build host status URL
                    from  backend_server.src.lib.utils.server_utils import get_host_manager
                    host_manager = get_host_manager()
                    host_data = host_manager.get_host(host_name)
                    
                    if host_data:
                        host_url = buildHostUrl(host_data, f'/host/campaigns/status/{host_execution_id}')
                        
                        response = requests.get(host_url, timeout=10)
                        if response.status_code == 200:
                            host_status = response.json()
                            if host_status.get('success'):
                                # Update with host status
                                response_data['host_status'] = host_status.get('status')
                                response_data['host_runtime_seconds'] = host_status.get('runtime_seconds')
                                
                                # If host shows completed, update our tracking
                                if host_status.get('status') in ['completed', 'failed']:
                                    campaign_info['status'] = host_status.get('status')
                                    campaign_info['host_result'] = host_status.get('result')
                                    campaign_info['completed_at'] = time.time()
                                    response_data['status'] = host_status.get('status')
                                    response_data['result'] = host_status.get('result')
                        else:
                            print(f"[@server_campaign:get_status] Host status check failed: {response.status_code}")
                    else:
                        print(f"[@server_campaign:get_status] Host not found: {host_name}")
                        
            except Exception as host_error:
                print(f"[@server_campaign:get_status] Error checking host status: {host_error}")
                # Don't fail the whole request, just continue with server status
        
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


@server_campaign_execution_bp.route('/callback', methods=['POST'])
def campaign_execution_callback():
    """Callback endpoint for host to notify server when campaign execution completes"""
    try:
        print(f"[@server_campaign:callback] Received campaign completion callback")
        
        # Get callback data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Callback data is required'
            }), 400
        
        execution_id = data.get('execution_id')
        status = data.get('status')
        result = data.get('result')
        error = data.get('error')
        completed_at = data.get('completed_at')
        
        print(f"[@server_campaign:callback] Execution ID: {execution_id}")
        print(f"[@server_campaign:callback] Status: {status}")
        
        if not execution_id:
            return jsonify({
                'success': False,
                'error': 'execution_id is required in callback'
            }), 400
        
        # Update running campaigns with callback data
        if execution_id in running_campaigns:
            running_campaigns[execution_id].update({
                'status': status,
                'completed_at': completed_at or time.time(),
                'host_result': result,
                'host_error': error
            })
            
            print(f"[@server_campaign:callback] Updated campaign status: {execution_id} -> {status}")
        else:
            print(f"[@server_campaign:callback] WARNING: Execution ID not found in running campaigns: {execution_id}")
        
        return jsonify({
            'success': True,
            'message': 'Callback received and processed'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing campaign callback: {str(e)}")
        print(f"[@server_campaign:callback] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to process callback: {str(e)}'
        }), 500