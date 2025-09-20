"""
Clean AI Routes - Proxy to Host AI Execution
"""

from flask import Blueprint, request, jsonify
from shared.lib.utils.route_utils import proxy_to_host, get_host_from_request
from shared.lib.utils.app_utils import get_team_id

server_ai_bp = Blueprint('server_ai', __name__, url_prefix='/server/ai')


@server_ai_bp.route('/analyzeCompatibility', methods=['POST'])
def analyze_compatibility():
    data = request.get_json()
    prompt = data.get('prompt')
    
    if not prompt:
        return jsonify({'success': False, 'error': 'Prompt required'}), 400
    
    try:
        from shared.lib.supabase.userinterface_db import get_all_userinterfaces
        
        interfaces = get_all_userinterfaces(get_team_id())
        compatible = []
        incompatible = []
        
        # Analyze compatibility across all interfaces
        for interface in interfaces:
            try:
                # Create temporary context for analysis
                context = {
                    'device_model': 'unknown',
                    'userinterface_name': interface['name'],
                    'available_nodes': [],
                    'available_actions': [],
                    'available_verifications': []
                }
                
                from backend_core.src.services.ai.ai_executor import AIExecutor
                
                # Create a mock device for server-side AI operations
                class MockDevice:
                    def __init__(self):
                        self.device_id = "server_ai_compatibility"
                        self.device_model = "server"
                
                ai_executor = AIExecutor(
                    host={'host_name': 'server_ai_compatibility'}, 
                    device=MockDevice(), 
                    team_id=get_team_id()
                )
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
        
        return jsonify({
            'success': True,
            'analysis_id': f"analysis_{hash(prompt)}",
            'compatible_interfaces': compatible,
            'incompatible_interfaces': incompatible,
            'compatible_count': len(compatible)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@server_ai_bp.route('/generatePlan', methods=['POST'])
def generate_plan():
    """Generate AI plan by proxying to host AI executor"""
    try:
        print("[@route:server_ai:generate_plan] Starting AI plan generation")
        
        data = request.get_json() or {}
        prompt = data.get('prompt')
        userinterface_name = data.get('userinterface_name', 'default')
        device_id = data.get('device_id', 'device1')
        current_node_id = data.get('current_node_id')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        print(f"[@route:server_ai:generate_plan] Proxying plan generation for device: {device_id}")
        
        # Proxy to host AI execution endpoint
        plan_payload = {
            'prompt': prompt,
            'device_id': device_id,
            'userinterface_name': userinterface_name,
            'current_node_id': current_node_id
        }
        
        response_data, status_code = proxy_to_host('/host/ai/generatePlan', 'POST', plan_payload, timeout=120)
        
        print(f"[@route:server_ai:generate_plan] Plan generation result: success={response_data.get('success')}")
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_ai:generate_plan] Error: {str(e)}")
        return jsonify({'success': False, 'error': f'AI plan generation failed: {str(e)}'}), 500


@server_ai_bp.route('/executeTask', methods=['POST'])
def execute_task():
    """Execute AI task by proxying to host AI executor"""
    try:
        print("[@route:server_ai:execute_task] Starting AI task execution")
        
        data = request.get_json() or {}
        prompt = data.get('prompt')
        userinterface_name = data.get('userinterface_name', 'default')
        device_id = data.get('device_id', 'device1')
        current_node_id = data.get('current_node_id')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        print(f"[@route:server_ai:execute_task] Proxying task execution for device: {device_id}")
        
        # Proxy to host AI execution endpoint (executePrompt combines generate + execute)
        task_payload = {
            'prompt': prompt,
            'device_id': device_id,
            'userinterface_name': userinterface_name,
            'current_node_id': current_node_id
        }
        
        response_data, status_code = proxy_to_host('/host/ai/executePrompt', 'POST', task_payload, timeout=300)
        
        print(f"[@route:server_ai:execute_task] Task execution result: success={response_data.get('success')}")
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_ai:execute_task] Error: {str(e)}")
        return jsonify({'success': False, 'error': f'AI task execution failed: {str(e)}'}), 500


@server_ai_bp.route('/status/<execution_id>', methods=['GET'])
def get_status(execution_id):
    try:
        # Proxy status request to host
        response_data, status_code = proxy_to_host(f'/host/ai/status/{execution_id}', 'GET', {})
        return jsonify(response_data), status_code
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@server_ai_bp.route('/executeTestCase', methods=['POST'])
def execute_test_case():
    data = request.get_json()
    test_case_id = data.get('test_case_id')
    device_id = data.get('device_id')
    host = data.get('host')
    
    if not all([test_case_id, device_id, host]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    try:
        # Load test case from database
        from shared.lib.supabase.testcase_db import get_test_case
        import uuid
        
        test_case = get_test_case(test_case_id, get_team_id())
        if not test_case:
            return jsonify({'success': False, 'error': 'Test case not found'}), 404
        
        # Proxy to host for test case execution
        from shared.lib.utils.route_utils import proxy_to_host
        
        execution_payload = {
            'test_case_id': test_case_id,
            'device_id': device_id
        }
        
        response_data, status_code = proxy_to_host('/host/ai/executeTestCase', 'POST', execution_payload, timeout=120)
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
