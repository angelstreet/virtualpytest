"""
Server TestCase Routes - TestCase Builder operations proxy

This module proxies TestCase Builder operations from the server to the appropriate host.
"""

from flask import Blueprint, request, jsonify
from backend_server.src.lib.utils.route_utils import proxy_to_host_with_params

server_testcase_bp = Blueprint('server_testcase', __name__, url_prefix='/server/testcase')


@server_testcase_bp.route('/save', methods=['POST'])
def testcase_save():
    """Save or update test case definition"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    query_params = {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/testcase/save', 'POST', data, query_params
    )
    return jsonify(response_data), status_code


@server_testcase_bp.route('/list', methods=['GET'])
def testcase_list():
    """List all test cases for a team"""
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    query_params = {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/testcase/list', 'GET', None, query_params
    )
    return jsonify(response_data), status_code


@server_testcase_bp.route('/<testcase_id>', methods=['GET'])
def testcase_get(testcase_id):
    """Get test case definition by ID"""
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    query_params = {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        f'/host/testcase/{testcase_id}', 'GET', None, query_params
    )
    return jsonify(response_data), status_code


@server_testcase_bp.route('/<testcase_id>', methods=['DELETE'])
def testcase_delete(testcase_id):
    """Delete test case"""
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    query_params = {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        f'/host/testcase/{testcase_id}', 'DELETE', None, query_params
    )
    return jsonify(response_data), status_code


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
