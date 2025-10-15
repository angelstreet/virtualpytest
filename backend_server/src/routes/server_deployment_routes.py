"""Server Deployment Routes - Proxy to hosts and manage deployments"""
from flask import Blueprint, request, jsonify
import requests
from backend_server.src.lib.utils.server_utils import get_host_manager
from shared.src.lib.utils.build_url_utils import buildHostUrl
from shared.src.lib.supabase.client import get_supabase_client

server_deployment_bp = Blueprint('server_deployment', __name__, url_prefix='/server/deployment')

@server_deployment_bp.route('/create', methods=['POST'])
def create_deployment():
    try:
        data = request.get_json()
        team_id = request.args.get('team_id')
        supabase = get_supabase_client()
        
        # Insert into Supabase
        result = supabase.table('deployments').insert({
            'team_id': team_id,
            'name': data['name'],
            'host_name': data['host_name'],
            'device_id': data['device_id'],
            'script_name': data['script_name'],
            'userinterface_name': data['userinterface_name'],
            'parameters': data.get('parameters'),
            'schedule_type': data['schedule_type'],
            'schedule_config': data['schedule_config'],
            'status': 'active'
        }).execute()
        
        deployment = result.data[0]
        
        # Call host to add to scheduler
        host_manager = get_host_manager()
        host_info = host_manager.get_host(data['host_name'])
        if host_info:
            host_url = buildHostUrl(host_info, '/host/deployment/add')
            requests.post(host_url, json=deployment, timeout=10)
        
        return jsonify({'success': True, 'deployment': deployment})
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
            requests.post(host_url, timeout=10)
        
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
            requests.post(host_url, timeout=10)
        
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
            requests.delete(host_url, timeout=10)
        
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
        result = supabase.table('deployment_executions').select('*, deployments!inner(team_id, name, script_name, host_name, device_id)').eq('deployments.team_id', team_id).order('started_at', desc=True).limit(100).execute()
        return jsonify({'success': True, 'executions': result.data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

