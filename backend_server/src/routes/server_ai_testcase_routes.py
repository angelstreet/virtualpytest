"""
Server AI Test Case Routes

AI test case generation, analysis, and execution with modern host_name pattern.
Clean implementation with consistent endpoint naming.
"""

from flask import Blueprint, request, jsonify
import json
import uuid
from datetime import datetime

from shared.src.lib.supabase.testcase_db import save_test_case, get_test_case
from shared.src.lib.supabase.navigation_trees_db import get_full_tree, get_root_tree_for_interface
from shared.src.lib.supabase.userinterface_db import get_all_userinterfaces, get_userinterface_by_name
from shared.src.lib.supabase.ai_analysis_cache_db import save_analysis_cache, get_analysis_cache

from  backend_server.src.lib.utils.route_utils import proxy_to_host

# Create blueprint
server_ai_testcase_bp = Blueprint('server_ai_testcase', __name__, url_prefix='/server/ai-testcase')

@server_ai_testcase_bp.route('/analyze', methods=['POST'])
def analyze_test_case():
    """
    Analyze test case compatibility against ALL userinterfaces
    
    Input: { "prompt": "Go to live and check audio" }
    
    Output: { 
        "analysis_id": "uuid",
        "understanding": "Navigate to live TV and verify audio functionality",
        "compatibility_matrix": {
            "compatible_userinterfaces": ["horizon_android_mobile", "horizon_android_tv"],
            "incompatible": ["web_interface"],
            "reasons": {"horizon_android_mobile": "Has required navigation and audio verification"}
        },
        "requires_multiple_testcases": false,
        "estimated_complexity": "medium"
    }
    """
    try:
        team_id = request.args.get('team_id') or (request.get_json() or {}).get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
            
        request_data = request.get_json() or {}
        prompt = request_data.get('prompt')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        print(f"[@server_ai_testcase] Analyzing prompt: {prompt}")
        
        # Get all available userinterfaces for this team
        userinterfaces = get_all_userinterfaces(team_id)
        
        if not userinterfaces:
            return jsonify({
                'success': False, 
                'error': 'No userinterfaces found for analysis'
            }), 404
        
        # Analyze compatibility using AI Planner
        compatible = []
        incompatible = []
        
        for interface in userinterfaces:
            try:
                # Create minimal context for analysis
                context = {
                    'device_model': 'unknown',
                    'userinterface_name': interface['name'],
                    'available_nodes': [],
                    'available_actions': [],
                    'available_verifications': []
                }
                
                # Proxy AI plan generation to host
                plan_response, _ = proxy_to_host_with_params(
                    '/host/ai/generatePlan', 
                    'POST', 
                    {
                        'prompt': prompt,
                        'context': context,
                        'team_id': team_id
                    },
                    {}
                )
                plan_dict = plan_response.get('plan', {}) if plan_response.get('success') else {}
                
                if plan_dict.get('feasible', True):
                    compatible.append({
                        'userinterface_name': interface['name'],
                        'reasoning': plan_dict.get('analysis', '')
                    })
                else:
                    incompatible.append({
                        'userinterface_name': interface['name'],
                        'reasoning': plan_dict.get('analysis', '')
                    })
            except Exception as e:
                incompatible.append({
                    'userinterface_name': interface['name'],
                    'reasoning': f'Analysis failed: {str(e)}'
                })
        
        # Create analysis result
        compatible_interfaces = [r['userinterface_name'] for r in compatible]
        analysis_result = {
            'analysis_id': str(uuid.uuid4()),
            'understanding': f"AI analysis of: {prompt}",
            'compatibility_matrix': {
                'compatible_userinterfaces': compatible_interfaces,
                'incompatible': [r['userinterface_name'] for r in incompatible],
                'reasons': {r['userinterface_name']: r.get('reasoning', '') for r in compatible + incompatible}
            },
            'requires_multiple_testcases': False,
            'estimated_complexity': 'medium',
            'compatible_count': len(compatible_interfaces),
            'total_analyzed': len(userinterfaces)
        }
        
        # Cache analysis result
        save_analysis_cache(
            analysis_result['analysis_id'], 
            prompt, 
            analysis_result, 
            analysis_result['compatibility_matrix'], 
            team_id
        )
        
        print(f"[@server_ai_testcase] Analysis complete. Compatible: {analysis_result['compatible_count']}/{analysis_result['total_analyzed']}")
        
        return jsonify(analysis_result)
        
    except Exception as e:
        print(f"[@server_ai_testcase] Analysis error: {e}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

@server_ai_testcase_bp.route('/generate', methods=['POST'])
def generate_test_cases():
    """
    Generate actual test cases for confirmed userinterfaces
    
    Input: { 
        "analysis_id": "uuid",
        "confirmed_userinterfaces": ["horizon_android_mobile", "horizon_android_tv"]
    }
    
    Output: {
        "success": true,
        "generated_testcases": [
            {
                "id": "uuid",
                "name": "Go to live and check audio - Android Mobile",
                "creator": "ai",
                "original_prompt": "Go to live and check audio",
                "steps": [...],
                "compatible_userinterfaces": ["horizon_android_mobile"]
            }
        ]
    }
    """
    try:
        team_id = request.args.get('team_id') or (request.get_json() or {}).get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
            
        request_data = request.get_json() or {}
        analysis_id = request_data.get('analysis_id')
        confirmed_interfaces = request_data.get('confirmed_userinterfaces', [])
        
        if not analysis_id or not confirmed_interfaces:
            return jsonify({
                'success': False,
                'error': 'analysis_id and confirmed_userinterfaces are required'
            }), 400
        
        print(f"[@server_ai_testcase] Generating for interfaces: {confirmed_interfaces}")
        
        # Retrieve cached analysis
        cached_analysis = get_analysis_cache(analysis_id, team_id)
        
        if not cached_analysis:
            return jsonify({
                'success': False,
                'error': 'Analysis not found or expired. Please run analysis again.'
            }), 404
        
        original_prompt = cached_analysis['prompt']
        generated_testcases = []
        
        # Generate ONE test case with ALL confirmed interfaces
        if confirmed_interfaces:
            try:
                print(f"[@server_ai_testcase] Generating single test case for interfaces: {confirmed_interfaces}")
                
                # Use AI Planner to generate test case
                primary_interface = confirmed_interfaces[0]
                
                # Create context for generation
                context = {
                    'device_model': 'unknown',
                    'userinterface_name': primary_interface,
                    'available_nodes': [],
                    'available_actions': [],
                    'available_verifications': []
                }
                
                # Proxy AI plan generation to host
                plan_response, _ = proxy_to_host_with_params(
                    '/host/ai/generatePlan', 
                    'POST', 
                    {
                        'prompt': original_prompt,
                        'context': context,
                        'team_id': team_id
                    },
                    {}
                )
                plan_dict = plan_response.get('plan', {}) if plan_response.get('success') else {}
                
                if plan_dict.get('feasible', True):
                    steps = plan_dict.get('plan', [])
                else:
                    steps = []
                
                # Create unified test case for all interfaces
                test_case = {
                    'test_id': str(uuid.uuid4()),
                    'name': f"AI: {original_prompt[:50]}{'...' if len(original_prompt) > 50 else ''}",
                    'test_type': 'functional',
                    'start_node': 'home',
                    'steps': steps,
                    'creator': 'ai',
                    'original_prompt': original_prompt,
                    'compatible_userinterfaces': confirmed_interfaces,
                    'tags': ['ai-generated'] + confirmed_interfaces,
                    'priority': 2,
                    'estimated_duration': max(30, len(steps) * 10)
                }
                
                # Save to database
                saved_test_case = save_test_case(test_case, team_id)
                generated_testcases.append(saved_test_case)
                
                print(f"[@server_ai_testcase] Generated unified test case: {saved_test_case.get('test_id')} for {len(confirmed_interfaces)} interfaces")
                    
            except Exception as e:
                print(f"[@server_ai_testcase] Error generating test case: {e}")
        
        return jsonify({
            'success': True,
            'generated_testcases': generated_testcases,
            'total_generated': len(generated_testcases)
        })
        
    except Exception as e:
        print(f"[@server_ai_testcase] Generation error: {e}")
        return jsonify({
            'success': False,
            'error': f'Generation failed: {str(e)}'
        }), 500

@server_ai_testcase_bp.route('/execute', methods=['POST'])
def execute_test_case():
    """Execute test case using modern host_name pattern"""
    try:
        print("[@server_ai_testcase] Proxying test case execution to host")
        
        team_id = request.args.get('team_id') or (request.get_json() or {}).get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
            
        request_data = request.get_json() or {}
        
        test_case_id = request_data.get('test_case_id')
        device_id = request_data.get('device_id')
        interface_name = request_data.get('interface_name')
        
        if not all([test_case_id, device_id]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: test_case_id, device_id'
            }), 400
        
        # Get test case from database
        test_case = get_test_case(test_case_id, team_id)
        
        if not test_case:
            return jsonify({
                'success': False,
                'error': 'Test case not found'
            }), 404
        
        # Proxy to host for execution using modern pattern
        host_request = {
            'test_case': test_case,
            'device_id': device_id,
            'interface_name': interface_name or test_case.get('interface_name'),
            'team_id': team_id
        }
        
        query_params = {'team_id': team_id}
        response_data, status_code = proxy_to_host_with_params(
            '/host/ai/executeTestCase',
            'POST',
            host_request,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@server_ai_testcase] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test case execution error: {str(e)}'
        }), 500

@server_ai_testcase_bp.route('/validate', methods=['POST'])
def validate_compatibility():
    """Validate test case compatibility with specific userinterface"""
    try:
        team_id = request.args.get('team_id') or (request.get_json() or {}).get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
            
        request_data = request.get_json() or {}
        
        test_case_id = request_data.get('test_case_id')
        interface_name = request_data.get('interface_name')
        
        if not all([test_case_id, interface_name]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        # Get test case
        test_case = get_test_case(test_case_id, team_id)
        
        if not test_case:
            return jsonify({
                'success': False,
                'error': 'Test case not found'
            }), 404
        
        # Check if already compatible
        compatible_interfaces = test_case.get('compatible_userinterfaces', [])
        if 'all' in compatible_interfaces or interface_name in compatible_interfaces:
            return jsonify({
                'success': True,
                'compatible': True,
                'reasoning': 'Already marked as compatible'
            })
        
        # Analyze compatibility for this interface
        compatibility_result = _analyze_single_interface_compatibility(
            test_case, interface_name, team_id
        )
        
        return jsonify({
            'success': True,
            **compatibility_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Compatibility validation error: {str(e)}'
        }), 500

@server_ai_testcase_bp.route('/feasibilityCheck', methods=['POST'])
def quick_feasibility_check():
    """Quick feasibility check using modern host_name pattern"""
    try:
        request_data = request.get_json() or {}
        prompt = request_data.get('prompt')
        interface_name = request_data.get('interface_name')
        team_id = request_data.get('team_id')
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: prompt'
            }), 400
        
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        
        # Create minimal context for feasibility check
        context = {
            'device_model': 'unknown',
            'userinterface_name': interface_name or 'unknown',
            'available_nodes': [],
            'available_actions': [],
            'available_verifications': []
        }
        
        # Proxy AI plan generation to host
        plan_response, _ = proxy_to_host_with_params(
            '/host/ai/generatePlan', 
            'POST', 
            {
                'prompt': prompt,
                'context': context,
                'team_id': team_id
            },
            {}
        )
        plan_dict = plan_response.get('plan', {}) if plan_response.get('success') else {}
        
        return jsonify({
            'success': True,
            'feasible': plan_dict.get('feasible', True),
            'reason': plan_dict.get('analysis', '')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'feasible': False,
            'reason': f'Feasibility check error: {str(e)}'
        }), 500

def _analyze_single_interface_compatibility(test_case, interface_name, team_id):
    """Analyze compatibility for a single interface"""
    try:
        # Get userinterface info
        userinterface_info = get_userinterface_by_name(interface_name, team_id)
        if not userinterface_info:
            return {
                'compatible': False,
                'reasoning': 'Userinterface not found'
            }
        
        # Get navigation graph
        root_tree = get_root_tree_for_interface(userinterface_info.get('id'), team_id)
        unified_graph = get_full_tree(root_tree.get('tree_id'), team_id) if root_tree else None
        
        if not unified_graph:
            return {
                'compatible': False,
                'reasoning': 'No navigation graph available'
            }
        
        # Extract required nodes from test case steps
        required_nodes = set()
        for step in test_case.get('steps', []):
            if isinstance(step, dict) and step.get('type') == 'navigation':
                required_nodes.add(step.get('target_node'))
        
        # Check availability
        available_nodes = set(unified_graph.get('nodes', {}).keys())
        missing_nodes = required_nodes - available_nodes
        
        if missing_nodes:
            return {
                'compatible': False,
                'reasoning': f'Missing required nodes: {", ".join(missing_nodes)}'
            }
        
        return {
            'compatible': True,
            'reasoning': 'All required nodes available'
        }
        
    except Exception as e:
        return {
            'compatible': False,
            'reasoning': f'Analysis error: {str(e)}'
        }
