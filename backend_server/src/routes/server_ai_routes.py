"""
Clean AI Routes - Uses AI Central
"""

from flask import Blueprint, request, jsonify
from backend_core.src.controllers.ai.ai_central import AICentral, ExecutionOptions, ExecutionMode
from shared.lib.utils.app_utils import get_team_id

server_ai_bp = Blueprint('server_ai', __name__, url_prefix='/server/ai')


@server_ai_bp.route('/analyzeCompatibility', methods=['POST'])
def analyze_compatibility():
    data = request.get_json()
    prompt = data.get('prompt')
    
    if not prompt:
        return jsonify({'success': False, 'error': 'Prompt required'}), 400
    
    ai_central = AICentral(team_id=get_team_id())
    result = ai_central.analyze_compatibility(prompt)
    
    return jsonify({
        'success': True,
        'analysis_id': f"analysis_{hash(prompt)}",
        **result
    })


@server_ai_bp.route('/generatePlan', methods=['POST'])
def generate_plan():
    data = request.get_json()
    prompt = data.get('prompt')
    userinterface_name = data.get('userinterface_name')
    
    if not prompt or not userinterface_name:
        return jsonify({'success': False, 'error': 'Prompt and userinterface_name required'}), 400
    
    try:
        ai_central = AICentral(team_id=get_team_id())
        plan = ai_central.generate_plan(prompt, userinterface_name)
        
        return jsonify({
            'success': True,
            'plan': {
                'id': plan.id,
                'prompt': plan.prompt,
                'analysis': plan.analysis,
                'feasible': plan.feasible,
                'steps': [
                    {
                        'step': step.step_id,
                        'type': step.type.value,
                        'command': step.command,
                        'params': step.params,
                        'description': step.description
                    }
                    for step in plan.steps
                ]
            }
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
        ai_central = AICentral(
            team_id=get_team_id(),
            host=host,
            device_id=device_id
        )
        
        options = ExecutionOptions(
            mode=ExecutionMode.REAL_TIME,
            context={'tree_id': None, 'current_node_id': None}
        )
        
        execution_id = ai_central.execute_task(prompt, userinterface_name, options)
        
        return jsonify({
            'success': True,
            'execution_id': execution_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@server_ai_bp.route('/status/<execution_id>', methods=['GET'])
def get_status(execution_id):
    try:
        ai_central = AICentral(team_id=get_team_id())
        status = ai_central.get_execution_status(execution_id)
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
        from backend_core.src.controllers.ai.ai_central import AIPlan, AIStep, AIStepType
        
        test_case = get_test_case(test_case_id, get_team_id())
        if not test_case:
            return jsonify({'success': False, 'error': 'Test case not found'}), 404
        
        # Convert stored test case to AIPlan
        steps = []
        for i, step_data in enumerate(test_case.get('steps', [])):
            step_type = AIStepType.ACTION
            if step_data.get('command') == 'execute_navigation':
                step_type = AIStepType.NAVIGATION
            elif step_data.get('command', '').startswith('verify_'):
                step_type = AIStepType.VERIFICATION
            elif step_data.get('command') == 'wait':
                step_type = AIStepType.WAIT
                
            steps.append(AIStep(
                step_id=i + 1,
                type=step_type,
                command=step_data.get('command'),
                params=step_data.get('params', {}),
                description=step_data.get('description', '')
            ))
        
        plan = AIPlan(
            id=test_case_id,
            prompt=test_case.get('original_prompt', ''),
            analysis=f"Stored test case: {test_case.get('name', '')}",
            feasible=True,
            steps=steps,
            userinterface_name=test_case.get('userinterface_name', 'horizon_android_mobile')
        )
        
        ai_central = AICentral(
            team_id=get_team_id(),
            host=host,
            device_id=device_id
        )
        
        options = ExecutionOptions(
            mode=ExecutionMode.TEST_CASE,
            context={'tree_id': test_case.get('tree_id')},
            enable_db_tracking=True
        )
        
        execution_id = ai_central.execute_plan(plan, options)
        
        # Wait for completion (synchronous for test cases)
        import time
        while True:
            status = ai_central.get_execution_status(execution_id)
            if not status.get('is_executing', False):
                break
            time.sleep(0.5)
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
