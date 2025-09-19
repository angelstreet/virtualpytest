"""
Clean AI Routes - Uses New AI Architecture
"""

from flask import Blueprint, request, jsonify
from shared.lib.utils.ai_central import AISession, AIPlanner, AITracker, AIContextService, ExecutionMode
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
                
                planner = AIPlanner.get_instance(get_team_id())
                plan_dict = planner.generate_plan(prompt, context)
                
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
    data = request.get_json()
    prompt = data.get('prompt')
    userinterface_name = data.get('userinterface_name')
    host = data.get('host')
    device_id = data.get('device_id')
    
    if not prompt or not userinterface_name:
        return jsonify({'success': False, 'error': 'Prompt and userinterface_name required'}), 400
    
    try:
        # Load context if host and device provided, otherwise use minimal context
        if host and device_id:
            # Extract device_model from host for efficiency
            from shared.lib.utils.build_url_utils import get_device_by_id
            device_dict = get_device_by_id(host, device_id)
            device_model = device_dict.get('device_model') if device_dict else 'unknown'
            context = AIContextService.load_context(host, device_id, get_team_id(), userinterface_name, device_model)
        else:
            context = {
                'device_model': 'unknown',
                'userinterface_name': userinterface_name,
                'available_nodes': [],
                'available_actions': [],
                'available_verifications': []
            }
        
        planner = AIPlanner.get_instance(get_team_id())
        plan = planner.generate_plan(prompt, context)
        
        # Return plan dict directly - no conversion needed
        return jsonify({
            'success': True,
            'ai_plan': plan  # plan is already a dict from generate_plan
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@server_ai_bp.route('/executeTask', methods=['POST'])
def execute_task():
    data = request.get_json()
    prompt = data.get('prompt')
    userinterface_name = data.get('userinterface_name')
    host = data.get('host')
    device_id = data.get('device_id')
    
    if not all([prompt, userinterface_name, host, device_id]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    try:
        # Create session for this request
        session = AISession(
            host=host,
            device_id=device_id,
            team_id=get_team_id()
        )
        
        # Execute task
        execution_id = session.execute_task(prompt, userinterface_name, ExecutionMode.REAL_TIME)
        
        return jsonify({
            'success': True,
            'execution_id': execution_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@server_ai_bp.route('/status/<execution_id>', methods=['GET'])
def get_status(execution_id):
    try:
        status = AITracker.get_status(execution_id)
        return jsonify(status)
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
        
        # Route should NOT reconstruct plans - AI central handles stored plans directly
        session = AISession(
            host=host,
            device_id=device_id,
            team_id=get_team_id()
        )
        
        # Execute stored test case directly - AI central handles everything
        execution_id = session.execute_stored_testcase(test_case_id)
        
        # Return execution status
        status = AITracker.get_status(execution_id)
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
