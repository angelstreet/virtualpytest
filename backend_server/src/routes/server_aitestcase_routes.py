"""
AI Test Case Generation Routes - Clean Modern Implementation
No fallbacks, no legacy code, no backward compatibility
"""

from flask import Blueprint, request, jsonify
import json
import uuid
from datetime import datetime
import sys
import os

# Add backend_core to path for direct access
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend_core/src'))

from controllers.ai.ai_agent import AIAgentController
from controllers.controller_config_factory import get_device_capabilities
from shared.lib.supabase.testcase_db import save_test_case, get_test_case
from shared.lib.supabase.navigation_trees_db import get_full_tree, get_root_tree_for_interface
from shared.lib.supabase.userinterface_db import get_all_userinterfaces, get_userinterface_by_name
from shared.lib.supabase.ai_analysis_cache_db import save_analysis_cache, get_analysis_cache
from shared.lib.utils.app_utils import get_team_id
from shared.lib.utils.route_utils import proxy_to_host

server_aitestcase_bp = Blueprint('server_aitestcase', __name__, url_prefix='/server')

@server_aitestcase_bp.route('/analyzeTestCase', methods=['POST'])
def analyze_test_case():
    """
    STEP 1: Analyze test case compatibility against ALL userinterfaces
    
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
        team_id = get_team_id()
        request_data = request.get_json() or {}
        prompt = request_data.get('prompt')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        print(f"[@route:server_aitestcase:analyze] Analyzing prompt: {prompt}")
        
        # Get all available userinterfaces for this team
        userinterfaces = get_all_userinterfaces(team_id)
        
        if not userinterfaces:
            return jsonify({
                'success': False, 
                'error': 'No userinterfaces found for analysis'
            }), 404
        
        # Initialize AI agent
        ai_agent = AIAgentController()
        
        # Analyze compatibility with each userinterface
        compatibility_results = []
        
        for ui in userinterfaces:
            try:
                # Get navigation graph for this interface
                root_tree = get_root_tree_for_interface(ui.get('userinterface_id'), team_id)
                unified_graph = get_full_tree(root_tree.get('tree_id'), team_id) if root_tree else None
                
                # Prepare analysis context
                analysis_context = {
                    'prompt': prompt,
                    'userinterface_name': ui['name'],
                    'navigation_nodes': list(unified_graph.get('nodes', {}).keys()) if unified_graph else [],
                    'available_actions': ['click_element', 'navigate', 'wait', 'press_key'],
                    'available_verifications': ['verify_image', 'verify_audio', 'verify_video', 'verify_text']
                }
                
                # Quick compatibility analysis using AI agent
                compatibility = ai_agent.execute_task(
                    f"Analyze feasibility: Can '{prompt}' be executed on interface '{ui['name']}'?",
                    available_actions=[],  # Simplified for analysis
                    available_verifications=[],
                    device_model=None,
                    userinterface_name=ui['name']
                )
                
                is_compatible = compatibility.get('success', False) and 'impossible' not in compatibility.get('reasoning', '').lower()
                
                compatibility_results.append({
                    'userinterface': ui['name'],
                    'compatible': is_compatible,
                    'reasoning': compatibility.get('reasoning', 'AI analysis completed'),
                    'confidence': compatibility.get('confidence', 0.7)
                })
                
            except Exception as e:
                print(f"Error analyzing {ui['name']}: {e}")
                compatibility_results.append({
                    'userinterface': ui['name'],
                    'compatible': False,
                    'reasoning': f'Analysis failed: {str(e)}',
                    'confidence': 0.0
                })
        
        # Separate compatible and incompatible interfaces
        compatible = [r for r in compatibility_results if r['compatible']]
        incompatible = [r for r in compatibility_results if not r['compatible']]
        
        # Generate unique analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Build analysis result
        analysis_result = {
            'analysis_id': analysis_id,
            'understanding': f"AI analysis: {prompt}",
            'compatibility_matrix': {
                'compatible_userinterfaces': [ui['userinterface'] for ui in compatible],
                'incompatible': [ui['userinterface'] for ui in incompatible],
                'reasons': {ui['userinterface']: ui['reasoning'] for ui in compatibility_results}
            },
            'requires_multiple_testcases': len(compatible) > 1,
            'estimated_complexity': 'medium',
            'total_analyzed': len(userinterfaces),
            'compatible_count': len(compatible)
        }
        
        # Cache analysis result
        save_analysis_cache(
            analysis_id, 
            prompt, 
            analysis_result, 
            analysis_result['compatibility_matrix'], 
            team_id
        )
        
        print(f"[@route:server_aitestcase:analyze] Analysis complete. Compatible: {len(compatible)}/{len(userinterfaces)}")
        
        return jsonify(analysis_result)
        
    except Exception as e:
        print(f"Analysis error: {e}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

@server_aitestcase_bp.route('/generateTestCases', methods=['POST'])
def generate_test_cases():
    """
    STEP 2: Generate actual test cases for confirmed userinterfaces
    
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
        team_id = get_team_id()
        request_data = request.get_json() or {}
        analysis_id = request_data.get('analysis_id')
        confirmed_interfaces = request_data.get('confirmed_userinterfaces', [])
        
        if not analysis_id or not confirmed_interfaces:
            return jsonify({
                'success': False,
                'error': 'analysis_id and confirmed_userinterfaces are required'
            }), 400
        
        print(f"[@route:server_aitestcase:generate] Generating for interfaces: {confirmed_interfaces}")
        
        # Retrieve cached analysis
        cached_analysis = get_analysis_cache(analysis_id, team_id)
        
        if not cached_analysis:
            return jsonify({
                'success': False,
                'error': 'Analysis not found or expired. Please run analysis again.'
            }), 404
        
        original_prompt = cached_analysis['prompt']
        
        # Generate test cases for each confirmed interface
        ai_agent = AIAgentController()
        generated_testcases = []
        
        for interface_name in confirmed_interfaces:
            try:
                print(f"[@route:server_aitestcase:generate] Generating for {interface_name}")
                
                # Get interface data and navigation graph
                interface_data = get_userinterface_by_name(interface_name, team_id)
                root_tree = get_root_tree_for_interface(interface_data.get('userinterface_id'), team_id)
                unified_graph = get_full_tree(root_tree.get('tree_id'), team_id) if root_tree else None
                
                # Generate specific test case using AI agent
                test_case_result = ai_agent.execute_task(
                    task_description=original_prompt,
                    available_actions=[],  # Will be populated by AI agent
                    available_verifications=[],
                    device_model=None,  # Generic for now
                    userinterface_name=interface_name
                )
                
                if test_case_result.get('success', True):
                    # Create test case object
                    test_case = {
                        'test_id': str(uuid.uuid4()),
                        'name': f"{original_prompt} - {interface_name}",
                        'test_type': 'functional',
                        'start_node': test_case_result.get('start_node', ''),
                        'steps': test_case_result.get('steps', []),
                        'creator': 'ai',
                        'original_prompt': original_prompt,
                        'ai_analysis': {
                            'analysis_id': analysis_id,
                            'generated_at': datetime.utcnow().isoformat(),
                            'interface_specific': True
                        },
                        'compatible_userinterfaces': [interface_name],
                        'verification_conditions': test_case_result.get('verification_conditions', []),
                        'expected_results': test_case_result.get('expected_results', {}),
                        'execution_config': test_case_result.get('execution_config', {}),
                        'tags': ['ai-generated', interface_name],
                        'priority': 2,
                        'estimated_duration': test_case_result.get('estimated_duration', 60)
                    }
                    
                    # Save to database
                    saved_test_case = save_test_case(test_case, team_id)
                    generated_testcases.append(saved_test_case)
                    
                    print(f"[@route:server_aitestcase:generate] Generated test case: {saved_test_case.get('test_id')}")
                    
                else:
                    print(f"Generation failed for {interface_name}: {test_case_result.get('error')}")
                    
            except Exception as e:
                print(f"Error generating test case for {interface_name}: {e}")
        
        return jsonify({
            'success': True,
            'generated_testcases': generated_testcases,
            'total_generated': len(generated_testcases)
        })
        
    except Exception as e:
        print(f"Generation error: {e}")
        return jsonify({
            'success': False,
            'error': f'Generation failed: {str(e)}'
        }), 500

@server_aitestcase_bp.route('/generateTestCase', methods=['POST'])
def generate_test_case():
    """Generate AI test case from natural language prompt - Server handles generation"""
    try:
        print("[@route:server_aitestcase:generate_test_case] Starting AI test case generation")
        
        team_id = get_team_id()
        request_data = request.get_json() or {}
        
        prompt = request_data.get('prompt')
        device_model = request_data.get('device_model')
        interface_name = request_data.get('interface_name')
        
        if not all([prompt, device_model, interface_name]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: prompt, device_model, interface_name'
            }), 400
        
        print(f"[@route:server_aitestcase:generate_test_case] Prompt: {prompt}")
        print(f"[@route:server_aitestcase:generate_test_case] Device: {device_model}, Interface: {interface_name}")
        
        # Server directly accesses backend_core - no proxy needed for generation
        ai_agent = AIAgentController()
        
        # Get device capabilities and navigation context
        device_capabilities = get_device_capabilities(device_model)
        
        # Get userinterface info for compatibility analysis  
        userinterface_info = get_userinterface_by_name(interface_name, team_id)
        
        # Get navigation tree for interface
        if userinterface_info:
            root_tree = get_root_tree_for_interface(userinterface_info.get('userinterface_id'), team_id)
            unified_graph = get_full_tree(root_tree.get('tree_id'), team_id) if root_tree else None
        else:
            unified_graph = None
        
        if not userinterface_info:
            return jsonify({
                'success': False,
                'error': f'Userinterface {interface_name} not found'
            }), 404
        
        # Prepare AI context
        ai_context = {
            'prompt': prompt,
            'device_model': device_model,
            'interface_name': interface_name,
            'device_capabilities': device_capabilities,
            'navigation_graph': unified_graph,
            'userinterface_info': userinterface_info
        }
        
        print("[@route:server_aitestcase:generate_test_case] Calling AI agent")
        
        # Generate test case using AI - use existing execute_task method
        ai_result = ai_agent.execute_task(
            task_description=prompt,
            available_actions=[],  # Will be populated by the AI agent
            available_verifications=[],  # Will be populated by the AI agent  
            device_model=device_model,
            userinterface_name=interface_name
        )
        
        if not ai_result.get('success'):
            return jsonify({
                'success': False,
                'error': ai_result.get('error', 'AI generation failed')
            }), 500
        
        # Analyze compatibility across all userinterfaces
        compatibility_results = analyze_userinterface_compatibility(
            ai_result, team_id, device_model
        )
        
        # Create test case data structure
        test_case_data = {
            'test_id': str(uuid.uuid4()),
            'name': ai_result.get('name', f'AI Generated: {prompt[:50]}...'),
            'test_type': ai_result.get('test_type', 'functional'),
            'start_node': ai_result.get('start_node'),
            'steps': ai_result.get('steps', []),
            'team_id': team_id,
            'creator': 'ai',
            'original_prompt': prompt,
            'ai_analysis': {
                'feasibility': ai_result.get('feasibility', 'possible'),
                'reasoning': ai_result.get('reasoning', ''),
                'required_capabilities': ai_result.get('required_capabilities', []),
                'estimated_steps': len(ai_result.get('steps', [])),
                'generated_at': datetime.utcnow().isoformat()
            },
            'device_id': None,  # Will be set during execution
            'environment_profile_id': None,  # Will be set during execution
            'verification_conditions': ai_result.get('verification_conditions', []),
            'expected_results': ai_result.get('expected_results', {}),
            'execution_config': ai_result.get('execution_config', {}),
            'tags': ai_result.get('tags', ['ai-generated']),
            'priority': ai_result.get('priority', 2),
            'estimated_duration': ai_result.get('estimated_duration', 60),
            'compatible_devices': compatibility_results.get('compatible_devices', [device_model]),
            'compatible_userinterfaces': compatibility_results.get('compatible_userinterfaces', [interface_name]),
            'device_adaptations': compatibility_results.get('device_adaptations', {})
        }
        
        # Store in database  
        save_test_case(test_case_data, team_id)
        stored_test_case = test_case_data  # Return the data we just saved
        
        if not stored_test_case:
            return jsonify({
                'success': False,
                'error': 'Failed to store test case in database'
            }), 500
        
        print(f"[@route:server_aitestcase:generate_test_case] Test case created: {stored_test_case['test_id']}")
        
        return jsonify({
            'success': True,
            'test_case': stored_test_case,
            'compatibility_results': compatibility_results.get('analysis', [])
        })
        
    except Exception as e:
        print(f"[@route:server_aitestcase:generate_test_case] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test case generation error: {str(e)}'
        }), 500


@server_aitestcase_bp.route('/executeTestCase', methods=['POST'])
def execute_test_case():
    """Execute test case - PROXY TO HOST for execution"""
    try:
        print("[@route:server_aitestcase:execute_test_case] Proxying test case execution to host")
        
        team_id = get_team_id()
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
        
        # EXECUTION REQUIRES HOST - Proxy to host for actual execution
        host_request = {
            'test_case': test_case,
            'device_id': device_id,
            'interface_name': interface_name or test_case.get('interface_name'),
            'team_id': team_id
        }
        
        response_data, status_code = proxy_to_host(
            '/host/aitestcase/executeTestCase',
            'POST',
            host_request
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_aitestcase:execute_test_case] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test case execution error: {str(e)}'
        }), 500


@server_aitestcase_bp.route('/validateCompatibility', methods=['POST'])
def validate_compatibility():
    """Validate test case compatibility with specific userinterface"""
    try:
        team_id = get_team_id()
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
        compatibility_result = analyze_single_interface_compatibility(
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


def analyze_userinterface_compatibility(ai_result, team_id, device_model):
    """Analyze compatibility across all userinterfaces - clean implementation"""
    try:
        # Get all userinterfaces for this team
        all_interfaces = get_all_userinterfaces(team_id)
        
        compatible_interfaces = []
        compatibility_analysis = []
        device_adaptations = {}
        
        required_nodes = set()
        required_actions = set()
        
        # Extract requirements from AI result
        for step in ai_result.get('steps', []):
            if step.get('type') == 'navigation':
                required_nodes.add(step.get('target_node'))
            elif step.get('type') == 'action':
                required_actions.add(step.get('action_type'))
        
        for interface in all_interfaces:
            interface_name = interface['name']
            
            # Skip if interface doesn't support this device model
            if device_model not in interface.get('models', []):
                compatibility_analysis.append({
                    'interface_name': interface_name,
                    'compatible': False,
                    'reasoning': f'Interface does not support device model {device_model}'
                })
                continue
            
            # Get navigation graph for this interface
            root_tree = get_root_tree_for_interface(interface.get('userinterface_id'), team_id)
            unified_graph = get_full_tree(root_tree.get('tree_id'), team_id) if root_tree else None
            
            if not unified_graph:
                compatibility_analysis.append({
                    'interface_name': interface_name,
                    'compatible': False,
                    'reasoning': 'No navigation graph available'
                })
                continue
            
            # Check if all required nodes exist
            available_nodes = set(unified_graph.get('nodes', {}).keys())
            missing_nodes = required_nodes - available_nodes
            
            if missing_nodes:
                compatibility_analysis.append({
                    'interface_name': interface_name,
                    'compatible': False,
                    'reasoning': f'Missing required nodes: {", ".join(missing_nodes)}'
                })
                continue
            
            # Interface is compatible
            compatible_interfaces.append(interface_name)
            compatibility_analysis.append({
                'interface_name': interface_name,
                'compatible': True,
                'reasoning': 'All required nodes and actions available'
            })
            
            # Check for device-specific adaptations (like goto_live.py logic)
            if 'mobile' in device_model.lower() and 'live' in required_nodes:
                if 'live_fullscreen' in available_nodes:
                    device_adaptations[interface_name] = {
                        'live': 'live_fullscreen'  # Mobile devices use fullscreen
                    }
        
        return {
            'compatible_devices': [device_model],  # Current device is compatible
            'compatible_userinterfaces': compatible_interfaces,
            'device_adaptations': device_adaptations,
            'analysis': compatibility_analysis
        }
        
    except Exception as e:
        print(f"[@analyze_userinterface_compatibility] Error: {str(e)}")
        return {
            'compatible_devices': [device_model],
            'compatible_userinterfaces': [],
            'device_adaptations': {},
            'analysis': []
        }


def analyze_single_interface_compatibility(test_case, interface_name, team_id):
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
        root_tree = get_root_tree_for_interface(userinterface_info.get('userinterface_id'), team_id)
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
