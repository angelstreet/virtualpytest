"""
Server TestCase Routes - TestCase operations

This module handles test case CRUD operations using the database layer.
Execution is proxied to hosts.
"""

import uuid
from flask import Blueprint, request, jsonify
from backend_server.src.lib.utils.route_utils import proxy_to_host_with_params
from shared.src.lib.database.testcase_db import (
    create_testcase,
    update_testcase,
    get_testcase,
    delete_testcase,
    list_testcases,
    get_testcase_by_name
)

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
        
        # Check if updating existing testcase
        testcase_id = data.get('testcase_id')
        
        if testcase_id:
            # Update existing testcase
            success = update_testcase(
                testcase_id=testcase_id,
                graph_json=data.get('graph_json'),
                description=data.get('description'),
                userinterface_name=data.get('userinterface_name'),
                team_id=team_id
            )
            
            if success:
                # Fetch updated testcase
                testcase = get_testcase(testcase_id, team_id)
                if testcase:
                    return jsonify({'success': True, 'testcase': testcase})
                else:
                    return jsonify({'success': False, 'error': 'Test case not found after update'}), 404
            else:
                return jsonify({'success': False, 'error': 'Failed to update test case'}), 500
        else:
            # Create new testcase
            testcase_name = data.get('testcase_name')
            if not testcase_name:
                return jsonify({'success': False, 'error': 'testcase_name is required'}), 400
            
            graph_json = data.get('graph_json')
            if not graph_json:
                return jsonify({'success': False, 'error': 'graph_json is required'}), 400
            
            new_testcase_id = create_testcase(
                team_id=team_id,
                testcase_name=testcase_name,
                graph_json=graph_json,
                description=data.get('description'),
                userinterface_name=data.get('userinterface_name'),
                created_by=data.get('created_by'),
                creation_method=data.get('creation_method', 'visual'),
                ai_prompt=data.get('ai_prompt'),
                ai_analysis=data.get('ai_analysis')
            )
            
            if new_testcase_id:
                # Fetch created testcase
                testcase = get_testcase(new_testcase_id, team_id)
                if testcase:
                    return jsonify({'success': True, 'testcase': testcase})
                else:
                    return jsonify({'success': False, 'error': 'Test case not found after creation'}), 404
            else:
                return jsonify({'success': False, 'error': 'Failed to create test case'}), 500
            
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
        
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        testcases = list_testcases(team_id, include_inactive=include_inactive)
        
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
        
        testcase = get_testcase(testcase_id, team_id)
        
        if testcase:
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
        
        success = delete_testcase(testcase_id, team_id)
        
        if success:
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


@server_testcase_bp.route('/generate-with-ai', methods=['POST'])
def generate_with_ai():
    """
    Generate test case graph from natural language prompt
    
    This endpoint:
    1. Takes a natural language prompt
    2. Uses AI to analyze and generate a test case graph
    3. Returns React Flow compatible nodes/edges structure
    4. Does NOT save - frontend saves later with user input
    
    Request body:
        {
            "prompt": "Go to live TV and verify audio"
        }
    
    Response:
        {
            "success": true,
            "graph": {
                "nodes": [...],
                "edges": [...]
            },
            "testcase_name": "AI: Go to live TV",
            "description": "Generated from AI prompt",
            "ai_prompt": "Go to live TV and verify audio",
            "ai_analysis": "Step-by-step breakdown..."
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'success': False, 'error': 'prompt is required'}), 400
    
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    try:
        # Step 1: Analyze prompt using AI
        analyze_response, analyze_status = proxy_to_host_with_params(
            '/host/ai/analyzePrompt', 'POST', 
            {'prompt': prompt}, 
            {'team_id': team_id}
        )
        
        if not analyze_response.get('success'):
            return jsonify({
                'success': False,
                'error': analyze_response.get('error', 'Failed to analyze prompt')
            }), analyze_status
        
        analysis = analyze_response.get('analysis', {})
        steps = analysis.get('steps', [])
        
        # Step 2: Generate graph structure from analysis
        # Create nodes based on steps
        nodes = [
            {
                'id': 'start',
                'type': 'start',
                'position': {'x': 400, 'y': 50},
                'data': {}
            }
        ]
        
        edges = []
        last_node_id = 'start'
        y_position = 150
        
        # Generate nodes for each step
        for i, step in enumerate(steps):
            node_id = f'node_{uuid.uuid4().hex[:8]}'
            action_type = step.get('action_type', 'action')
            
            # Determine block type
            if 'verify' in action_type.lower() or 'check' in action_type.lower():
                block_type = 'verification'
            elif 'navigate' in action_type.lower() or 'goto' in action_type.lower():
                block_type = 'navigation'
            else:
                block_type = 'action'
            
            nodes.append({
                'id': node_id,
                'type': block_type,
                'position': {'x': 400, 'y': y_position},
                'data': {
                    'label': step.get('description', f'Step {i + 1}'),
                    'command': step.get('params', {}).get('command'),
                    'target': step.get('target'),
                    'params': step.get('params', {})
                }
            })
            
            # Connect to previous node
            edges.append({
                'id': f'edge_{uuid.uuid4().hex[:8]}',
                'source': last_node_id,
                'target': node_id,
                'sourceHandle': 'success',
                'type': 'success'
            })
            
            last_node_id = node_id
            y_position += 100
        
        # Add success and failure terminal nodes
        success_node_id = 'success'
        failure_node_id = 'failure'
        
        nodes.extend([
            {
                'id': success_node_id,
                'type': 'success',
                'position': {'x': 150, 'y': y_position + 100},
                'data': {}
            },
            {
                'id': failure_node_id,
                'type': 'failure',
                'position': {'x': 650, 'y': y_position + 100},
                'data': {}
            }
        ])
        
        # Connect last step to success
        if last_node_id != 'start':
            edges.append({
                'id': f'edge_{uuid.uuid4().hex[:8]}',
                'source': last_node_id,
                'target': success_node_id,
                'sourceHandle': 'success',
                'type': 'success'
            })
            edges.append({
                'id': f'edge_{uuid.uuid4().hex[:8]}',
                'source': last_node_id,
                'target': failure_node_id,
                'sourceHandle': 'failure',
                'type': 'failure'
            })
        
        # Generate suggested name and description
        testcase_name = f"AI: {prompt[:50]}" if len(prompt) > 50 else f"AI: {prompt}"
        description = f"Auto-generated test case from AI prompt: {prompt}"
        
        return jsonify({
            'success': True,
            'graph': {
                'nodes': nodes,
                'edges': edges
            },
            'testcase_name': testcase_name,
            'description': description,
            'ai_prompt': prompt,
            'ai_analysis': analysis.get('reasoning', 'AI-generated test case')
        }), 200
        
    except Exception as e:
        print(f"[@server_testcase] Error generating test case with AI: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to generate test case: {str(e)}'
        }), 500

