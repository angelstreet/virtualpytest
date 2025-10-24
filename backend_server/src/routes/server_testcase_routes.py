"""
Server TestCase Routes - TestCase operations

This module handles test case CRUD operations using direct database access.
Execution is proxied to hosts.
"""

from flask import Blueprint, request, jsonify
from backend_server.src.lib.utils.route_utils import proxy_to_host_with_params
from shared.src.lib.utils.supabase_utils import get_supabase_client

server_testcase_bp = Blueprint('server_testcase', __name__, url_prefix='/server/testcase')


@server_testcase_bp.route('/save', methods=['POST'])
def testcase_save():
    """Save or update test case definition"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 503
        
        # Add team_id to data
        data['team_id'] = team_id
        
        # Check if updating existing testcase
        test_id = data.get('test_id')
        
        if test_id:
            # Update existing testcase
            result = supabase.table('test_cases').update(data).eq('test_id', test_id).eq('team_id', team_id).execute()
        else:
            # Create new testcase
            result = supabase.table('test_cases').insert(data).execute()
        
        if result.data and len(result.data) > 0:
            return jsonify({'success': True, 'testcase': result.data[0]})
        else:
            return jsonify({'success': False, 'error': 'Failed to save test case'}), 500
            
    except Exception as e:
        print(f"[@server_testcase:save] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_testcase_bp.route('/list', methods=['GET'])
def testcase_list():
    """List all test cases for a team"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 503
        
        # Query test_cases table
        result = supabase.table('test_cases')\
            .select('*')\
            .eq('team_id', team_id)\
            .order('created_at', desc=True)\
            .execute()
        
        testcases = result.data if result.data else []
        
        # Ensure IDs are strings
        for testcase in testcases:
            if 'test_id' in testcase:
                testcase['test_id'] = str(testcase['test_id'])
            if 'team_id' in testcase:
                testcase['team_id'] = str(testcase['team_id'])
        
        return jsonify(testcases)
        
    except Exception as e:
        print(f"[@server_testcase:list] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_testcase_bp.route('/<testcase_id>', methods=['GET'])
def testcase_get(testcase_id):
    """Get test case definition by ID"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 503
        
        result = supabase.table('test_cases')\
            .select('*')\
            .eq('test_id', testcase_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            testcase = result.data[0]
            testcase['test_id'] = str(testcase['test_id'])
            testcase['team_id'] = str(testcase['team_id'])
            return jsonify({'success': True, 'testcase': testcase})
        else:
            return jsonify({'success': False, 'error': 'Test case not found'}), 404
            
    except Exception as e:
        print(f"[@server_testcase:get] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_testcase_bp.route('/<testcase_id>', methods=['DELETE'])
def testcase_delete(testcase_id):
    """Delete test case"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 503
        
        result = supabase.table('test_cases')\
            .delete()\
            .eq('test_id', testcase_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return jsonify({'success': True, 'message': 'Test case deleted'})
        else:
            return jsonify({'success': False, 'error': 'Test case not found or already deleted'}), 404
            
    except Exception as e:
        print(f"[@server_testcase:delete] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server_testcase_bp.route('/<testcase_id>/execute', methods=['POST'])
def testcase_execute(testcase_id):
    """Execute test case by ID"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    query_params = {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        f'/host/testcase/{testcase_id}/execute', 'POST', data, query_params
    )
    return jsonify(response_data), status_code


@server_testcase_bp.route('/<testcase_id>/history', methods=['GET'])
def testcase_history(testcase_id):
    """Get execution history for a test case"""
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    limit = request.args.get('limit', '50')
    query_params = {'team_id': team_id, 'limit': limit}
    
    response_data, status_code = proxy_to_host_with_params(
        f'/host/testcase/{testcase_id}/history', 'GET', None, query_params
    )
    return jsonify(response_data), status_code


@server_testcase_bp.route('/execute-from-prompt', methods=['POST'])
def execute_from_prompt():
    """
    Unified AI execution endpoint - proxies to host
    
    This replaces the old /server/ai/executePrompt route.
    Supports optional save flag for both:
    - Live AI Modal: save=false (ephemeral)
    - TestCase Builder: save=true (persistent)
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    query_params = {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/testcase/execute-from-prompt', 'POST', data, query_params
    )
    return jsonify(response_data), status_code
