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

# Add backend_host to path for direct access
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend_host/src'))

from backend_host.src.services.ai.ai_executor import AIExecutor
from controllers.controller_config_factory import get_device_capabilities
from src.lib.supabase.testcase_db import save_test_case, get_test_case
from src.lib.supabase.navigation_trees_db import get_full_tree, get_root_tree_for_interface
from src.lib.supabase.userinterface_db import get_all_userinterfaces, get_userinterface_by_name
from src.lib.supabase.ai_analysis_cache_db import save_analysis_cache, get_analysis_cache
from shared.src.lib.utils.app_utils import get_team_id
from src.lib.utils.route_utils import proxy_to_host

server_aitestcase_bp = Blueprint('server_aitestcase', __name__, url_prefix='/server/aitestcase')

def _create_server_ai_executor(team_id: str) -> AIExecutor:
    """Create AIExecutor for server-side AI operations"""
    class MockDevice:
        def __init__(self):
            self.device_id = "server_aitestcase"
            self.device_model = "server"
    
    return AIExecutor(
        host={'host_name': 'server_aitestcase'}, 
        device=MockDevice(), 
        team_id=team_id
    )

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
        
        # Load real commands for models used by the selected userinterfaces
        from backend_host.src.controllers.ai_descriptions import get_commands_for_device_model
        
        print(f"[@route:server_aitestcase:analyze] Loading commands for userinterface models")
        
        # Get unique models from all selected userinterfaces
        interface_models = set()
        for ui in userinterfaces:
            ui_models = ui.get('models', [])
            interface_models.update(ui_models)
            print(f"[@route:server_aitestcase:analyze] UserInterface {ui.get('name', 'unknown')} supports models: {ui_models}")
        
        interface_models = list(interface_models)
        print(f"[@route:server_aitestcase:analyze] Unique models across all interfaces: {interface_models}")
        
        model_commands = {}
        for model in interface_models:
            model_commands[model] = get_commands_for_device_model(model)
            if 'error' not in model_commands[model]:
                actions_count = len(model_commands[model].get('actions', []))
                verifications_count = len(model_commands[model].get('verifications', []))
                print(f"[@route:server_aitestcase:analyze] Model {model}: {actions_count} actions, {verifications_count} verifications")
            else:
                print(f"[@route:server_aitestcase:analyze] Error loading commands for model {model}: {model_commands[model]['error']}")
        
        # Add comprehensive capability analysis logging
        print(f"\n=== AI CAPABILITY ANALYSIS ===")
        print(f"Available Actions Across All Controllers:")
        
        all_actions = {}
        all_verifications = {}
        
        for model, commands in model_commands.items():
            if 'error' not in commands:
                actions = commands.get('actions', [])
                verifications = commands.get('verifications', [])
                
                for action in actions:
                    cmd = action.get('command')
                    if cmd not in all_actions:
                        all_actions[cmd] = []
                    all_actions[cmd].append(model)
                
                for verif in verifications:
                    cmd = verif.get('command')
                    if cmd not in all_verifications:
                        all_verifications[cmd] = []
                    all_verifications[cmd].append(model)
        
        for action, models in all_actions.items():
            print(f"  - {action}: {', '.join(models)}")
        
        print(f"Available Verifications Across All Controllers:")
        for verif, models in all_verifications.items():
            print(f"  - {verif}: {', '.join(models)}")
        
        print(f"Navigation Nodes Available:")
        for ui in userinterfaces:
            ui_name = ui.get('name')
            try:
                root_tree = get_root_tree_for_interface(ui.get('userinterface_id'), team_id)
                if root_tree:
                    tree_data = get_full_tree(root_tree.get('tree_id'), team_id)
                    if tree_data.get('success'):
                        nodes = tree_data.get('nodes', [])
                        node_names = [node.get('node_id') for node in nodes if node.get('node_id')]
                        print(f"  - {ui_name}: {', '.join(node_names[:10])}{'...' if len(node_names) > 10 else ''}")
                    else:
                        print(f"  - {ui_name}: No navigation tree available")
                else:
                    print(f"  - {ui_name}: No root tree found")
            except Exception as e:
                print(f"  - {ui_name}: Error loading navigation - {e}")
        
        print(f"=== END ANALYSIS ===\n")
        
        # Use AI Planner for compatibility analysis
        print(f"[@route:server_aitestcase:analyze] Using AI Planner for compatibility analysis")
        
        # Analyze compatibility using AI Planner
        from src.lib.supabase.userinterface_db import get_all_userinterfaces
        
        interfaces = get_all_userinterfaces(team_id)
        compatible = []
        incompatible = []
        
        for interface in interfaces:
            try:
                # Create minimal context for analysis
                context = {
                    'device_model': 'unknown',
                    'userinterface_name': interface['name'],
                    'available_nodes': [],
                    'available_actions': [],
                    'available_verifications': []
                }
                
                ai_executor = _create_server_ai_executor(team_id)
                plan_dict = ai_executor.generate_plan(prompt, context)
                
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
        
        analysis_result = {
            'compatible_interfaces': compatible,
            'incompatible_interfaces': incompatible,
            'compatible_count': len(compatible)
        }
        
        # Convert to expected format for backward compatibility
        compatible_interfaces = [r['userinterface_name'] for r in analysis_result['compatible_interfaces']]
        analysis_result = {
            'analysis_id': str(uuid.uuid4()),
            'understanding': f"AI analysis of: {prompt}",
            'compatibility_matrix': {
                'compatible_userinterfaces': compatible_interfaces,
                'incompatible': [r['userinterface_name'] for r in analysis_result['incompatible_interfaces']],
                'reasons': {r['userinterface_name']: r.get('reasoning', '') for r in analysis_result['compatible_interfaces'] + analysis_result['incompatible_interfaces']}
            },
            'requires_multiple_testcases': False,
            'estimated_complexity': 'medium',
            'compatible_count': len(compatible_interfaces),
            'total_analyzed': len(userinterfaces)
        }
        
        # Add model commands to analysis result for frontend debugging
        analysis_result['model_commands'] = model_commands
        analysis_result['total_models_analyzed'] = len(interface_models)
        analysis_result['interface_models'] = interface_models
        
        # Cache analysis result
        save_analysis_cache(
            analysis_result['analysis_id'], 
            prompt, 
            analysis_result, 
            analysis_result['compatibility_matrix'], 
            team_id
        )
        
        print(f"[@route:server_aitestcase:analyze] Analysis complete. Compatible: {analysis_result['compatible_count']}/{analysis_result['total_analyzed']}")
        
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
        
        # Use AI Planner for test case generation
        generated_testcases = []
        
        # Generate ONE test case with ALL confirmed interfaces
        if confirmed_interfaces:
            try:
                print(f"[@route:server_aitestcase:generate] Generating single test case for interfaces: {confirmed_interfaces}")
                
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
                
                ai_executor = _create_server_ai_executor(team_id)
                plan_dict = ai_executor.generate_plan(original_prompt, context)
                
                if plan_dict.get('feasible', True):
                    steps = plan_dict.get('plan', [])  # Direct dict access - no conversion
                else:
                    steps = []
                verification_conditions = []
                
                # Create unified tags from all interfaces
                all_tags = ['ai-generated'] + confirmed_interfaces
                
                # Create test case object with ALL compatible interfaces
                test_case = {
                    'test_id': str(uuid.uuid4()),
                    'name': f"AI: {original_prompt[:50]}{'...' if len(original_prompt) > 50 else ''}",
                    'test_type': 'functional',
                    'start_node': 'home',
                    'steps': steps,
                    'creator': 'ai',
                    'original_prompt': original_prompt,
                    'ai_analysis': {
                        'analysis_id': analysis_id,
                        'feasibility': 'possible',
                        'reasoning': f'AI generated test case compatible with {len(confirmed_interfaces)} interfaces: {", ".join(confirmed_interfaces)}',
                        'required_capabilities': ['navigate', 'click_element', 'wait'],
                        'estimated_steps': len(steps),
                        'generated_at': datetime.utcnow().isoformat(),
                        'interface_specific': False,  # Now supports multiple interfaces
                        'supported_interfaces': confirmed_interfaces
                    },
                    'compatible_userinterfaces': confirmed_interfaces,  # ALL compatible interfaces
                    'compatible_devices': ['all'],
                    'device_adaptations': {},
                    'verification_conditions': verification_conditions,
                    'expected_results': {
                        'success_criteria': f"Successfully execute: {original_prompt}",
                        'failure_conditions': ['Navigation failed', 'Verification failed', 'Timeout']
                    },
                    'execution_config': {
                        'timeout': 60,
                        'retry_count': 1,
                        'screenshot_on_failure': True
                    },
                    'tags': all_tags,  # Include all interface names as tags
                    'priority': 2,
                    'estimated_duration': max(30, len(steps) * 10)
                }
                
                # Save to database
                saved_test_case = save_test_case(test_case, team_id)
                generated_testcases.append(saved_test_case)
                
                print(f"[@route:server_aitestcase:generate] Generated unified test case: {saved_test_case.get('test_id')} for {len(confirmed_interfaces)} interfaces")
                    
            except Exception as e:
                print(f"Error generating unified test case: {e}")
        
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
    """Generate AI test case using unified AI Agent - Server handles generation"""
    try:
        print("[@route:server_aitestcase:generate_test_case] Starting unified AI test case generation")
        
        team_id = get_team_id()
        request_data = request.get_json() or {}
        
        prompt = request_data.get('prompt')
        device_model = request_data.get('device_model', 'generic')
        interface_name = request_data.get('interface_name')
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: prompt'
            }), 400
        
        print(f"[@route:server_aitestcase:generate_test_case] Prompt: {prompt}")
        print(f"[@route:server_aitestcase:generate_test_case] Interface: {interface_name}")
        
        # Use AI Planner for test case generation
        
        # Generate test case using AI Planner
        try:
            # Create context for generation
            context = {
                'device_model': device_model,
                'userinterface_name': interface_name,
                'available_nodes': [],
                'available_actions': [],
                'available_verifications': []
            }
            
            ai_executor = _create_server_ai_executor(team_id)
            plan_dict = ai_executor.generate_plan(prompt, context)
            
            generation_result = {
                'success': True,
                'test_case': {
                    'id': str(uuid.uuid4()),
                    'name': f"AI Generated: {prompt[:50]}...",
                    'original_prompt': prompt,
                    'steps': plan_dict.get('plan', []),  # Direct dict access - no conversion
                    'userinterface_name': interface_name,
                    'feasible': plan_dict.get('feasible', True)
                }
            }
        except Exception as e:
            generation_result = {
                'success': False,
                'error': str(e)
            }
        
        if not generation_result.get('success'):
            return jsonify({
                'success': False,
                'error': generation_result.get('error', 'AI test case generation failed')
            }), 500
        
        test_case = generation_result['test_case']
        
        # Analyze cross-device compatibility if multiple interfaces available
        all_interfaces = get_all_userinterfaces(team_id)
        interface_names = [ui['name'] for ui in all_interfaces]
        
        # Simple compatibility analysis - all interfaces are compatible for now
        # TODO: Implement proper cross-device compatibility analysis
        compatibility_results = [
            {
                'interface_name': name,
                'compatible': True,
                'reasoning': 'Basic AI-generated test case'
            }
            for name in interface_names
        ]
        
        # Store in database with team context
        test_case['team_id'] = team_id
        save_test_case(test_case, team_id)
        
        print(f"[@route:server_aitestcase:generate_test_case] Test case created: {test_case['id']}")
        
        return jsonify({
            'success': True,
            'test_case': test_case,
            'compatibility_results': compatibility_results,
            'ai_confidence': generation_result.get('ai_confidence', 0.8)
        })
        
    except Exception as e:
        print(f"[@route:server_aitestcase:generate_test_case] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test case generation error: {str(e)}'
        }), 500

@server_aitestcase_bp.route('/quickFeasibilityCheck', methods=['POST'])
def quick_feasibility_check():
    """Quick feasibility check using unified AI Agent"""
    try:
        request_data = request.get_json() or {}
        prompt = request_data.get('prompt')
        interface_name = request_data.get('interface_name')
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: prompt'
            }), 400
        
        # Use AI Planner for feasibility check
        try:
            from shared.src.lib.utils.app_utils import get_team_id
            team_id = get_team_id()
            
            # Create minimal context for feasibility check
            context = {
                'device_model': 'unknown',
                'userinterface_name': interface_name or 'unknown',
                'available_nodes': [],
                'available_actions': [],
                'available_verifications': []
            }
            
            ai_executor = _create_server_ai_executor(team_id)
            plan_dict = ai_executor.generate_plan(prompt, context)
            
            result = {
                'success': True,
                'feasible': plan_dict.get('feasible', True),
                'reason': plan_dict.get('analysis', '')
            }
        except Exception as e:
            result = {
                'success': False,
                'feasible': False,
                'reason': str(e)
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'feasible': False,
            'reason': f'Feasibility check error: {str(e)}'
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
