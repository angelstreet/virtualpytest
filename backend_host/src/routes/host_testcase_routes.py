"""
Host TestCase Routes - TestCase Builder execution on host

This module handles direct test case execution on the host device.
Test cases are visual no-code scripts created in TestCase Builder.
"""

from flask import Blueprint, request, jsonify, current_app

# Create blueprint
host_testcase_bp = Blueprint('host_testcase', __name__, url_prefix='/host/testcase')


@host_testcase_bp.route('/save', methods=['POST'])
def testcase_save():
    """Save or update test case definition"""
    try:
        from shared.src.lib.database.testcase_db import create_testcase, update_testcase, get_testcase_by_name
        
        print("[@host_testcase] Saving test case definition")
        
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        
        testcase_name = data.get('testcase_name')
        graph_json = data.get('graph_json')
        description = data.get('description')
        userinterface_name = data.get('userinterface_name')
        created_by = data.get('created_by')
        
        # Validate
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        if not testcase_name:
            return jsonify({'success': False, 'error': 'testcase_name is required'}), 400
        if not graph_json:
            return jsonify({'success': False, 'error': 'graph_json is required'}), 400
        
        # Check if test case already exists (update vs create)
        existing = get_testcase_by_name(testcase_name, team_id)
        
        if existing:
            # Update existing
            success = update_testcase(
                testcase_id=existing['testcase_id'],
                graph_json=graph_json,
                description=description,
                userinterface_name=userinterface_name,
                team_id=team_id
            )
            
            if success:
                print(f"[@host_testcase] Updated test case: {testcase_name}")
                return jsonify({
                    'success': True,
                    'testcase_id': existing['testcase_id'],
                    'action': 'updated'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to update test case'}), 500
        else:
            # Create new
            testcase_id = create_testcase(
                team_id=team_id,
                testcase_name=testcase_name,
                graph_json=graph_json,
                description=description,
                userinterface_name=userinterface_name,
                created_by=created_by
            )
            
            if testcase_id:
                print(f"[@host_testcase] Created test case: {testcase_name} (ID: {testcase_id})")
                return jsonify({
                    'success': True,
                    'testcase_id': testcase_id,
                    'action': 'created'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to create test case'}), 500
        
    except Exception as e:
        print(f"[@host_testcase] Error saving test case: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Save failed: {str(e)}'}), 500


@host_testcase_bp.route('/list', methods=['GET'])
def testcase_list():
    """List all test cases for a team"""
    try:
        from shared.src.lib.database.testcase_db import list_testcases
        
        team_id = request.args.get('team_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        testcases = list_testcases(team_id)
        
        return jsonify({
            'success': True,
            'testcases': testcases
        })
        
    except Exception as e:
        print(f"[@host_testcase] Error listing test cases: {e}")
        return jsonify({'success': False, 'error': f'List failed: {str(e)}'}), 500


@host_testcase_bp.route('/<testcase_id>', methods=['GET'])
def testcase_get(testcase_id):
    """Get test case definition by ID"""
    try:
        from shared.src.lib.database.testcase_db import get_testcase
        
        team_id = request.args.get('team_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        testcase = get_testcase(testcase_id, team_id)
        
        if testcase:
            return jsonify({
                'success': True,
                'testcase': testcase
            })
        else:
            return jsonify({'success': False, 'error': 'Test case not found'}), 404
        
    except Exception as e:
        print(f"[@host_testcase] Error getting test case: {e}")
        return jsonify({'success': False, 'error': f'Get failed: {str(e)}'}), 500


@host_testcase_bp.route('/<testcase_id>', methods=['DELETE'])
def testcase_delete(testcase_id):
    """Delete test case"""
    try:
        from shared.src.lib.database.testcase_db import delete_testcase
        
        team_id = request.args.get('team_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        success = delete_testcase(testcase_id, team_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Test case not found or delete failed'}), 404
        
    except Exception as e:
        print(f"[@host_testcase] Error deleting test case: {e}")
        return jsonify({'success': False, 'error': f'Delete failed: {str(e)}'}), 500


@host_testcase_bp.route('/<testcase_id>/execute', methods=['POST'])
def testcase_execute(testcase_id):
    """Execute test case by ID"""
    try:
        from backend_host.src.services.testcase.testcase_executor import TestCaseExecutor
        from shared.src.lib.database.testcase_db import get_testcase
        
        print(f"[@host_testcase] Executing test case: {testcase_id}")
        
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        device_id = data.get('device_id', 'device1')
        
        # Validate
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get test case to extract name
        testcase = get_testcase(testcase_id, team_id)
        if not testcase:
            return jsonify({'success': False, 'error': 'Test case not found'}), 404
        
        testcase_name = testcase['testcase_name']
        
        # Get device info from registry
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        host_name = getattr(device, 'host_name', 'unknown-host')
        device_name = device.device_name
        device_model = device.device_model
        
        # Execute test case
        executor = TestCaseExecutor()
        result = executor.execute_testcase(
            testcase_name=testcase_name,
            team_id=team_id,
            host_name=host_name,
            device_id=device_id,
            device_name=device_name,
            device_model=device_model
        )
        
        print(f"[@host_testcase] Execution result: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@host_testcase] Error executing test case: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Execution failed: {str(e)}'}), 500


@host_testcase_bp.route('/<testcase_id>/history', methods=['GET'])
def testcase_history(testcase_id):
    """Get execution history for a test case"""
    try:
        from shared.src.lib.database.testcase_db import get_testcase, get_testcase_execution_history
        
        team_id = request.args.get('team_id')
        limit = int(request.args.get('limit', 50))
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get test case to extract name
        testcase = get_testcase(testcase_id, team_id)
        if not testcase:
            return jsonify({'success': False, 'error': 'Test case not found'}), 404
        
        testcase_name = testcase['testcase_name']
        
        # Get execution history from script_results
        history = get_testcase_execution_history(testcase_name, team_id, limit)
        
        return jsonify({
            'success': True,
            'testcase_name': testcase_name,
            'history': history
        })
        
    except Exception as e:
        print(f"[@host_testcase] Error getting history: {e}")
        return jsonify({'success': False, 'error': f'Get history failed: {str(e)}'}), 500


@host_testcase_bp.route('/execute-from-prompt', methods=['POST'])
def execute_from_prompt():
    """
    Unified AI execution endpoint - executes prompt with optional save
    
    This replaces the old separate /server/ai/executePrompt route.
    Works for both:
    - Live AI Modal: save=false (ephemeral execution)
    - TestCase Builder AI Mode: save=true (save after generation)
    """
    try:
        from shared.src.lib.database.testcase_db import create_testcase
        from shared.src.lib.executors.ai_prompt_validation import preprocess_prompt
        
        print("[@host_testcase] Unified execute-from-prompt")
        
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        
        # Required params
        prompt = data.get('prompt')
        userinterface_name = data.get('userinterface_name')
        device_id = data.get('device_id')
        host_name = data.get('host_name')
        
        # Optional params
        save_testcase = data.get('save', False)  # ← KEY: Optional save flag
        testcase_name = data.get('testcase_name')  # Required if save=true
        description = data.get('description')
        created_by = data.get('created_by')
        use_cache = data.get('use_cache', True)
        async_execution = data.get('async_execution', False)
        skip_validation = data.get('skip_validation', False)  # Skip if already validated
        
        # Validate required
        if not all([prompt, userinterface_name, device_id, team_id]):
            return jsonify({
                'success': False, 
                'error': 'Missing required fields: prompt, userinterface_name, device_id, team_id'
            }), 400
        
        # If save=true, testcase_name is required
        if save_testcase and not testcase_name:
            return jsonify({
                'success': False,
                'error': 'testcase_name is required when save=true'
            }), 400
        
        # Get device from app registry (same as other routes)
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found in host registry'
            }), 404
        
        device = current_app.host_devices[device_id]
        
        # Use device's existing AI executor (don't create new instance)
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AIExecutor initialized'
            }), 500
        
        # STEP 1: Validate prompt for disambiguation (unless skipped)
        if not skip_validation:
            print(f"[@host_testcase] Validating prompt for disambiguation...")
            
            # Load context to get available nodes
            context = device.ai_executor._load_context(userinterface_name, None, team_id)
            available_nodes = context.get('available_nodes', [])
            
            # Validate prompt
            validation_result = preprocess_prompt(
                prompt=prompt,
                available_nodes=available_nodes,
                team_id=team_id,
                userinterface_name=userinterface_name
            )
            
            # Check if disambiguation needed
            if validation_result.get('status') == 'needs_disambiguation':
                print(f"[@host_testcase] ⚠️ Disambiguation needed")
                return jsonify({
                    'success': False,
                    'needs_disambiguation': True,
                    'analysis': validation_result,
                    'available_nodes': available_nodes
                }), 200  # Not an error, just needs user input
            
            # If auto-corrected, use corrected prompt
            if validation_result.get('status') == 'auto_corrected':
                corrected_prompt = validation_result.get('corrected_prompt')
                if corrected_prompt:
                    print(f"[@host_testcase] ✅ Auto-corrected prompt")
                    prompt = corrected_prompt
        
        # STEP 2: Execute prompt using AI executor
        print(f"[@host_testcase] Executing prompt: {prompt[:50]}...")
        print(f"[@host_testcase] Save mode: {save_testcase}")
        
        if async_execution:
            # Async execution with polling (for Live Modal)
            execution_result = device.ai_executor.execute_prompt(
                prompt=prompt,
                userinterface_name=userinterface_name,
                team_id=team_id,
                use_cache=use_cache,
                async_execution=True
            )
            
            # Get the generated plan/graph for display
            plan_dict = execution_result.get('plan_dict', {})
            graph = plan_dict.get('graph') if plan_dict else None
            analysis = plan_dict.get('analysis', '')
            
            # Convert graph to steps for frontend display (AIStepDisplay)
            steps = []
            if graph and graph.get('nodes'):
                step_num = 1
                for node in graph['nodes']:
                    if node['type'] in ['navigation', 'action', 'verification']:
                        step_data = node.get('data', {})
                        steps.append({
                            'step': step_num,
                            'command': step_data.get('command', node['type']),
                            'params': step_data.get('params', {}),
                            'description': step_data.get('label', ''),
                            'type': node['type']
                        })
                        step_num += 1
            
            return jsonify({
                'success': True,
                'execution_id': execution_result.get('execution_id'),
                'graph': graph,  # For TestCase Builder
                'steps': steps,  # For Live Modal display (AIStepDisplay)
                'analysis': analysis,
                'message': 'Execution started asynchronously'
            })
        else:
            # Synchronous execution
            execution_result = device.ai_executor.execute_prompt(
                prompt=prompt,
                userinterface_name=userinterface_name,
                team_id=team_id,
                use_cache=use_cache,
                async_execution=False  # ✅ Correct parameter name
            )
            
            if not execution_result.get('success'):
                return jsonify(execution_result), 400
            
            # If save=true, save the generated graph to database
            testcase_id = None
            if save_testcase:
                graph = execution_result.get('graph')
                analysis = execution_result.get('analysis')
                
                if graph:
                    print(f"[@host_testcase] Saving generated test case: {testcase_name}")
                    
                    testcase_id = create_testcase(
                        team_id=team_id,
                        testcase_name=testcase_name,
                        graph_json=graph,
                        description=description or analysis,
                        userinterface_name=userinterface_name,
                        created_by=created_by,
                        creation_method='ai',
                        ai_prompt=prompt,
                        ai_analysis=analysis
                    )
                    
                    if testcase_id:
                        print(f"[@host_testcase] Saved test case: {testcase_name} (ID: {testcase_id})")
                    else:
                        print(f"[@host_testcase] Warning: Failed to save test case")
            
            # Return execution result
            response = {
                'success': True,
                'result': execution_result,
                'saved': save_testcase,
            }
            
            if testcase_id:
                response['testcase_id'] = testcase_id
            
            return jsonify(response)
        
    except Exception as e:
        print(f"[@host_testcase] Error in execute-from-prompt: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Execution failed: {str(e)}'}), 500
