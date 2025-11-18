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
    get_testcase_by_name,
    get_next_version_number
)
from shared.src.lib.database.folder_tag_db import (
    list_all_folders,
    list_all_tags
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
                team_id=team_id,
                folder=data.get('folder'),  # NEW: Folder name
                tags=data.get('tags'),  # NEW: List of tag names
                testcase_name=data.get('testcase_name')  # NEW: Support renaming
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
            
            overwrite = data.get('overwrite', False)  # Allow overwriting existing test case
            
            new_testcase_result = create_testcase(
                team_id=team_id,
                testcase_name=testcase_name,
                graph_json=graph_json,
                description=data.get('description'),
                userinterface_name=data.get('userinterface_name'),
                created_by=data.get('created_by'),
                creation_method=data.get('creation_method', 'visual'),
                ai_prompt=data.get('ai_prompt'),
                ai_analysis=data.get('ai_analysis'),
                overwrite=overwrite,
                folder=data.get('folder'),  # NEW: Folder name (user-selected or typed)
                tags=data.get('tags')  # NEW: List of tag names
            )
            
            # Handle dict response (new format with auto-increment info)
            if isinstance(new_testcase_result, dict) and new_testcase_result.get('success'):
                testcase_id = new_testcase_result['testcase_id']
                final_name = new_testcase_result['testcase_name']
                
                # Fetch full testcase data
                testcase = get_testcase(testcase_id, team_id)
                if testcase:
                    return jsonify({
                        'success': True, 
                        'testcase': testcase,
                        'testcase_id': testcase_id,
                        'testcase_name': final_name,
                        'action': 'created'
                    })
                else:
                    return jsonify({'success': False, 'error': 'Test case not found after creation'}), 404
            elif new_testcase_result == 'DUPLICATE_NAME':
                return jsonify({'success': False, 'error': f'Test case name "{testcase_name}" already exists. Please choose a different name or enable overwrite.'}), 409
            elif new_testcase_result:
                # Old format (backward compatibility) - just testcase_id string
                testcase = get_testcase(new_testcase_result, team_id)
                if testcase:
                    return jsonify({'success': True, 'testcase': testcase, 'action': 'updated' if overwrite else 'created'})
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
        
        return jsonify({'success': True, 'testcases': testcases})
        
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


@server_testcase_bp.route('/execute', methods=['POST'])
def testcase_execute_direct():
    """Execute test case directly from graph (no save required) - supports async execution"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    # Validate required fields
    if 'graph_json' not in data:
        return jsonify({'success': False, 'error': 'graph_json is required'}), 400
    if 'device_id' not in data:
        return jsonify({'success': False, 'error': 'device_id is required'}), 400
    if 'host_name' not in data:
        return jsonify({'success': False, 'error': 'host_name is required'}), 400
    
    # async_execution defaults to True on the host side to prevent timeouts
    # Frontend can override by passing async_execution: false
    
    query_params = {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        '/host/testcase/execute', 'POST', data, query_params
    )
    return jsonify(response_data), status_code


@server_testcase_bp.route('/execution/<execution_id>/status', methods=['GET'])
def testcase_execution_status(execution_id):
    """Get status of async test case execution"""
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    query_params = {'team_id': team_id}
    
    response_data, status_code = proxy_to_host_with_params(
        f'/host/testcase/execution/{execution_id}/status', 'GET', None, query_params
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


@server_testcase_bp.route('/<testcase_id>/next-version', methods=['GET'])
def testcase_get_next_version(testcase_id):
    """Get next version number for a test case"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        next_version = get_next_version_number(testcase_id, team_id)
        
        return jsonify({'success': True, 'next_version': next_version})
            
    except Exception as e:
        print(f"[@server_testcase:get_next_version] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
    Generate test case graph from natural language prompt (for TestCase Builder)
    
    Uses the unified execute-from-prompt endpoint but with save=false
    Returns graph + analysis for frontend to save later with user input
    
    Request body:
        {
            "prompt": "Go to live TV and verify audio",
            "userinterface_name": "horizon_android_mobile",
            "device_id": "device1"  // Optional - uses default if not provided
        }
    
    Response:
        {
            "success": true,
            "graph": {nodes: [...], edges: [...]},
            "analysis": "Goal: ...\nThinking: ...",
            "testcase_name": "AI: Go to live TV",
            "ai_prompt": "Go to live TV and verify audio"
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    prompt = data.get('prompt')
    userinterface_name = data.get('userinterface_name')
    device_id = data.get('device_id', 'device1')  # Default to device1
    
    if not prompt:
        return jsonify({'success': False, 'error': 'prompt is required'}), 400
    
    if not userinterface_name:
        return jsonify({'success': False, 'error': 'userinterface_name is required'}), 400
    
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'error': 'team_id is required'}), 400
    
    try:
        # Use unified execute-from-prompt endpoint to generate plan
        # save=false means it only generates, doesn't execute or save
        generate_response, generate_status = proxy_to_host_with_params(
            '/host/testcase/execute-from-prompt', 'POST', 
            {
                'prompt': prompt,
                'userinterface_name': userinterface_name,
                'device_id': device_id,
                'host_name': 'default',  # Not used for generation-only
                'save': False,  # Don't save or execute
                'use_cache': False,  # Always generate fresh for testcase builder
                'async_execution': False  # Synchronous
            }, 
            {'team_id': team_id}
        )
        
        if not generate_response.get('success'):
            return jsonify({
                'success': False,
                'error': generate_response.get('error', 'Failed to generate plan')
            }), generate_status
        
        result = generate_response.get('result', {})
        graph = result.get('graph')
        analysis = result.get('analysis', '')
        
        if not graph:
            return jsonify({
                'success': False,
                'error': 'No graph generated by AI'
            }), 500
        
        # Generate suggested name from prompt
        testcase_name = f"AI: {prompt[:50]}" if len(prompt) > 50 else f"AI: {prompt}"
        
        # Return the graph directly from AI (already has nodes/edges in React Flow format)
        return jsonify({
            'success': True,
            'graph': graph,  # Use AI-generated graph directly
            'testcase_name': testcase_name,
            'description': analysis,  # Use AI analysis as description
            'ai_prompt': prompt,
            'ai_analysis': analysis
        }), 200
        
    except Exception as e:
        print(f"[@server_testcase] Error generating test case with AI: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to generate test case: {str(e)}'
        }), 500


@server_testcase_bp.route('/folders-tags', methods=['GET'])
def get_folders_and_tags():
    """
    Get all folders and tags for dropdown selection.
    Used by TestCaseBuilder save dialog and RunTests selector.
    
    Returns:
        {
            "success": true,
            "folders": [{folder_id, name}, ...],
            "tags": [{tag_id, name, color}, ...]
        }
    """
    try:
        folders = list_all_folders()
        tags = list_all_tags()
        
        return jsonify({
            'success': True,
            'folders': folders,
            'tags': tags
        })
        
    except Exception as e:
        print(f"[@server_testcase:folders_tags] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

