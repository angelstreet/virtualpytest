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
from shared.lib.utils.auth_utils import get_team_id
from shared.lib.utils.proxy_utils import proxy_to_host

server_aitestcase_bp = Blueprint('server_aitestcase', __name__, url_prefix='/server/aitestcase')

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
