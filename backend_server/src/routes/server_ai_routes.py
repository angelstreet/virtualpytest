"""Server AI Routes - Unified AI operations"""

import uuid
from flask import Blueprint, request, jsonify
from backend_server.src.lib.utils.route_utils import proxy_to_host_with_params
from backend_server.src.lib.utils.server_utils import get_host_manager

server_ai_bp = Blueprint('server_ai', __name__, url_prefix='/server/ai')

@server_ai_bp.route('/analyzeCompatibility', methods=['POST'])
def analyze_compatibility():
    """Analyze AI task compatibility"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    query_params = {'device_id': data.get('device_id'), 'team_id': team_id} if data.get('device_id') else {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/ai/analyzeCompatibility', 'POST', data, query_params
    )
    return jsonify(response_data), status_code

@server_ai_bp.route('/generatePlan', methods=['POST'])
def generate_plan():
    """Generate AI execution plan"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    query_params = {'device_id': data.get('device_id'), 'team_id': team_id} if data.get('device_id') else {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/ai/generatePlan', 'POST', data, query_params
    )
    return jsonify(response_data), status_code

@server_ai_bp.route('/executePrompt', methods=['POST'])
def execute_prompt():
    """Execute AI prompt"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    query_params = {'device_id': data.get('device_id'), 'team_id': team_id} if data.get('device_id') else {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/ai/executePrompt', 'POST', data, query_params
    )
    return jsonify(response_data), status_code

@server_ai_bp.route('/getStatus', methods=['POST'])
def get_status():
    """Get AI execution status"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    query_params = {'device_id': data.get('device_id'), 'team_id': team_id} if data.get('device_id') else {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/ai/getStatus', 'POST', data, query_params
    )
    return jsonify(response_data), status_code

@server_ai_bp.route('/stopExecution', methods=['POST'])
def stop_execution():
    """Stop AI execution"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    query_params = {'device_id': data.get('device_id'), 'team_id': team_id} if data.get('device_id') else {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/ai/stopExecution', 'POST', data, query_params
    )
    return jsonify(response_data), status_code

@server_ai_bp.route('/resetCache', methods=['POST'])
def reset_cache():
    """Reset AI plan cache"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    host_name = data.get('host_name') or request.args.get('host_name')
    if not host_name:
        return jsonify({'success': False, 'error': 'host_name required'}), 400
    
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    from shared.src.lib.utils.supabase_utils import get_supabase_client
    supabase = get_supabase_client()
    
    count_result = supabase.table('ai_plan_generation').select('id', count='exact').eq('team_id', team_id).execute()
    deleted_count = count_result.count if count_result.count else 0
    
    supabase.table('ai_plan_generation').delete().eq('team_id', team_id).execute()
    
    return jsonify({
        'success': True,
        'message': f'Cache cleared: {deleted_count} plans deleted',
        'deleted_count': deleted_count
    }), 200

@server_ai_bp.route('/analyzePrompt', methods=['POST'])
def analyze_prompt():
    """Pre-analyze prompt for disambiguation"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    query_params = {'device_id': data.get('device_id'), 'team_id': team_id} if data.get('device_id') else {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/ai/analyzePrompt', 'POST', data, query_params
    )
    return jsonify(response_data), status_code

@server_ai_bp.route('/saveDisambiguation', methods=['POST'])
def save_disambiguation():
    """Save disambiguation preferences"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    query_params = {'team_id': team_id} if team_id else {}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/ai/saveDisambiguation', 'POST', data, query_params
    )
    return jsonify(response_data), status_code

