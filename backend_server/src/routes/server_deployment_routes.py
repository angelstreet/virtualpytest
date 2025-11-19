"""Server Deployment Routes - Proxy to hosts and manage deployments"""
from flask import Blueprint, request, jsonify
from backend_server.src.lib.utils.server_utils import get_host_manager
from backend_server.src.lib.utils.route_utils import api_post, api_delete
from shared.src.lib.utils.build_url_utils import buildHostUrl
from shared.src.lib.utils.supabase_utils import get_supabase_client

server_deployment_bp = Blueprint('server_deployment', __name__, url_prefix='/server/deployment')

@server_deployment_bp.route('/create', methods=['POST'])
def create_deployment():
    try:
        data = request.get_json()
        team_id = request.args.get('team_id')
        supabase = get_supabase_client()
        
        # Build deployment data
        deployment_data = {
            'team_id': team_id,
            'name': data['name'],
            'host_name': data['host_name'],
            'device_id': data['device_id'],
            'script_name': data['script_name'],
            'userinterface_name': data['userinterface_name'],
            'parameters': data.get('parameters'),
            'cron_expression': data['cron_expression'],
            'status': 'active'
        }
        
        # Optional constraints
        if 'start_date' in data and data['start_date']:
            deployment_data['start_date'] = data['start_date']
        if 'end_date' in data and data['end_date']:
            deployment_data['end_date'] = data['end_date']
        if 'max_executions' in data and data['max_executions']:
            deployment_data['max_executions'] = data['max_executions']
        
        # Insert into Supabase
        result = supabase.table('deployments').insert(deployment_data).execute()
        
        deployment = result.data[0]
        
        # Call host to add to scheduler
        host_manager = get_host_manager()
        host_info = host_manager.get_host(data['host_name'])
        if host_info:
            host_url = buildHostUrl(host_info, '/host/deployment/add')
            api_post(host_url, json=deployment, timeout=10)
        
        return jsonify({'success': True, 'deployment': deployment})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_deployment_bp.route('/update/<deployment_id>', methods=['PUT'])
def update_deployment(deployment_id):
    try:
        data = request.get_json()
        supabase = get_supabase_client()
        
        # Get existing deployment
        dep = supabase.table('deployments').select('*').eq('id', deployment_id).single().execute().data
        
        # Build update data
        update_data = {}
        if 'cron_expression' in data:
            update_data['cron_expression'] = data['cron_expression']
        if 'start_date' in data:
            update_data['start_date'] = data['start_date']
        if 'end_date' in data:
            update_data['end_date'] = data['end_date']
        if 'max_executions' in data:
            update_data['max_executions'] = data['max_executions']
        
        # Update in database
        result = supabase.table('deployments').update(update_data).eq('id', deployment_id).execute()
        updated_deployment = result.data[0]
        
        # Notify host to update scheduler
        host_manager = get_host_manager()
        host_info = host_manager.get_host(dep['host_name'])
        if host_info:
            # Remove old job and add updated one
            host_url = buildHostUrl(host_info, f'/host/deployment/remove/{deployment_id}')
            api_delete(host_url, timeout=10)
            
            host_url = buildHostUrl(host_info, '/host/deployment/add')
            api_post(host_url, json=updated_deployment, timeout=10)
        
        return jsonify({'success': True, 'deployment': updated_deployment})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_deployment_bp.route('/list', methods=['GET'])
def list_deployments():
    try:
        team_id = request.args.get('team_id')
        supabase = get_supabase_client()
        result = supabase.table('deployments').select('*').eq('team_id', team_id).order('created_at', desc=True).execute()
        return jsonify({'success': True, 'deployments': result.data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_deployment_bp.route('/pause/<deployment_id>', methods=['POST'])
def pause_deployment(deployment_id):
    try:
        supabase = get_supabase_client()
        dep = supabase.table('deployments').select('*').eq('id', deployment_id).single().execute().data
        supabase.table('deployments').update({'status': 'paused'}).eq('id', deployment_id).execute()
        
        host_manager = get_host_manager()
        host_info = host_manager.get_host(dep['host_name'])
        if host_info:
            host_url = buildHostUrl(host_info, f'/host/deployment/pause/{deployment_id}')
            api_post(host_url, timeout=10)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_deployment_bp.route('/resume/<deployment_id>', methods=['POST'])
def resume_deployment(deployment_id):
    try:
        supabase = get_supabase_client()
        dep = supabase.table('deployments').select('*').eq('id', deployment_id).single().execute().data
        supabase.table('deployments').update({'status': 'active'}).eq('id', deployment_id).execute()
        
        host_manager = get_host_manager()
        host_info = host_manager.get_host(dep['host_name'])
        if host_info:
            host_url = buildHostUrl(host_info, f'/host/deployment/resume/{deployment_id}')
            api_post(host_url, timeout=10)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_deployment_bp.route('/delete/<deployment_id>', methods=['DELETE'])
def delete_deployment(deployment_id):
    try:
        supabase = get_supabase_client()
        dep = supabase.table('deployments').select('*').eq('id', deployment_id).single().execute().data
        supabase.table('deployments').delete().eq('id', deployment_id).execute()
        
        host_manager = get_host_manager()
        host_info = host_manager.get_host(dep['host_name'])
        if host_info:
            host_url = buildHostUrl(host_info, f'/host/deployment/remove/{deployment_id}')
            api_delete(host_url, timeout=10)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_deployment_bp.route('/history/<deployment_id>', methods=['GET'])
def deployment_history(deployment_id):
    try:
        supabase = get_supabase_client()
        result = supabase.table('deployment_executions').select('*').eq('deployment_id', deployment_id).order('started_at', desc=True).limit(100).execute()
        return jsonify({'success': True, 'executions': result.data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@server_deployment_bp.route('/executions/recent', methods=['GET'])
def recent_executions():
    try:
        team_id = request.args.get('team_id')
        supabase = get_supabase_client()
        # Join with deployments (inner) and script_results (left) to get report URLs
        # Use explicit foreign key relationship: script_results!script_result_id
        result = supabase.table('deployment_executions').select(
            '*, deployments!inner(team_id, name, script_name, host_name, device_id), script_results!script_result_id(html_report_r2_url)'
        ).eq('deployments.team_id', team_id).order('started_at', desc=True).limit(100).execute()
        
        # Flatten script_results data into execution objects for easier frontend access
        executions = []
        for exec in result.data:
            execution_data = {**exec}
            # Extract report_url from nested script_results object (using correct column name)
            script_results = exec.get('script_results')
            if script_results:
                if isinstance(script_results, dict):
                    execution_data['report_url'] = script_results.get('html_report_r2_url')
                elif isinstance(script_results, list) and len(script_results) > 0:
                    execution_data['report_url'] = script_results[0].get('html_report_r2_url')
            executions.append(execution_data)
        
        return jsonify({'success': True, 'executions': executions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

