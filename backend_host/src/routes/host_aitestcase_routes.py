"""
AI Test Case Execution Routes - Host handles actual execution
Clean modern implementation for test case execution on host
"""

from flask import Blueprint, request, jsonify
import sys
import os

# Add backend_core to path for access to controllers
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend_core/src'))

from shared.lib.utils.script_execution_utils import execute_script
from shared.lib.utils.script_framework import ScriptExecutor

host_aitestcase_bp = Blueprint('host_aitestcase', __name__)

@host_aitestcase_bp.route('/executeTestCase', methods=['POST'])
def execute_test_case():
    """Execute AI-generated test case on host device"""
    try:
        print("[@route:host_aitestcase:execute_test_case] Starting test case execution")
        
        request_data = request.get_json() or {}
        
        test_case = request_data.get('test_case')
        device_id = request_data.get('device_id')
        interface_name = request_data.get('interface_name')
        team_id = request_data.get('team_id')
        
        if not all([test_case, device_id, team_id]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        print(f"[@route:host_aitestcase:execute_test_case] Executing test case: {test_case.get('test_id')}")
        print(f"[@route:host_aitestcase:execute_test_case] Device: {device_id}, Interface: {interface_name}")
        
        # Convert AI test case to script execution format
        script_config = convert_ai_test_case_to_script(test_case, device_id, interface_name)
        
        if not script_config:
            return jsonify({
                'success': False,
                'error': 'Failed to convert test case to executable script'
            }), 500
        
        # Execute using existing script framework
        script_executor = ScriptExecutor(
            script_name=f"ai_test_{test_case.get('test_id', 'unknown')}",
            description=f"AI generated test: {test_case.get('original_prompt', 'Unknown')}"
        )
        
        execution_result = execute_script(script_executor, script_config, device_id, team_id)
        
        if not execution_result:
            return jsonify({
                'success': False,
                'error': 'Script execution failed'
            }), 500
        
        print(f"[@route:host_aitestcase:execute_test_case] Execution completed: {execution_result.get('success')}")
        
        return jsonify({
            'success': True,
            'execution_result': execution_result,
            'test_case_id': test_case.get('test_id')
        })
        
    except Exception as e:
        print(f"[@route:host_aitestcase:execute_test_case] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test case execution error: {str(e)}'
        }), 500


def convert_ai_test_case_to_script(test_case, device_id, interface_name):
    """Convert AI test case to script execution format - clean implementation"""
    try:
        script_config = {
            'script_name': f"ai_test_{test_case.get('test_id', 'unknown')}",
            'script_type': 'ai_generated',
            'device_id': device_id,
            'userinterface_name': interface_name,
            'start_node': test_case.get('start_node'),
            'steps': [],
            'verifications': test_case.get('verification_conditions', []),
            'expected_results': test_case.get('expected_results', {}),
            'execution_config': test_case.get('execution_config', {}),
            'metadata': {
                'original_prompt': test_case.get('original_prompt'),
                'ai_analysis': test_case.get('ai_analysis', {}),
                'creator': 'ai',
                'test_case_id': test_case.get('test_id')
            }
        }
        
        # Convert AI steps to script framework format
        for step in test_case.get('steps', []):
            script_step = convert_ai_step_to_script_step(step, test_case, device_id)
            if script_step:
                script_config['steps'].append(script_step)
        
        # Apply device adaptations if needed
        device_adaptations = test_case.get('device_adaptations', {})
        if interface_name in device_adaptations:
            apply_device_adaptations(script_config, device_adaptations[interface_name])
        
        return script_config
        
    except Exception as e:
        print(f"[@convert_ai_test_case_to_script] Error: {str(e)}")
        return None


def convert_ai_step_to_script_step(ai_step, test_case, device_id):
    """Convert individual AI step to script framework step"""
    try:
        step_type = ai_step.get('type')
        
        if step_type == 'navigation':
            return {
                'type': 'navigation',
                'action': 'navigate_to_node',
                'target_node': ai_step.get('target_node'),
                'parameters': ai_step.get('parameters', {}),
                'timeout_ms': ai_step.get('timeout_ms', 30000),
                'description': ai_step.get('description', ''),
                'verifications': ai_step.get('verifications', [])
            }
            
        elif step_type == 'action':
            return {
                'type': 'action',
                'action': ai_step.get('action_type'),
                'target': ai_step.get('target', ''),
                'parameters': ai_step.get('parameters', {}),
                'timeout_ms': ai_step.get('timeout_ms', 10000),
                'description': ai_step.get('description', ''),
                'verifications': ai_step.get('verifications', [])
            }
            
        elif step_type == 'verification':
            return {
                'type': 'verification',
                'action': ai_step.get('verification_type'),
                'condition': ai_step.get('condition'),
                'parameters': ai_step.get('parameters', {}),
                'timeout_ms': ai_step.get('timeout_ms', 5000),
                'critical': ai_step.get('critical', True),
                'description': ai_step.get('description', '')
            }
            
        elif step_type == 'wait':
            return {
                'type': 'wait',
                'action': 'wait',
                'duration_ms': ai_step.get('duration_ms', 1000),
                'description': ai_step.get('description', 'Wait')
            }
        
        else:
            print(f"[@convert_ai_step_to_script_step] Unknown step type: {step_type}")
            return None
            
    except Exception as e:
        print(f"[@convert_ai_step_to_script_step] Error: {str(e)}")
        return None


def apply_device_adaptations(script_config, adaptations):
    """Apply device-specific adaptations like mobile->live_fullscreen"""
    try:
        for step in script_config['steps']:
            if step.get('type') == 'navigation':
                target_node = step.get('target_node')
                if target_node in adaptations:
                    print(f"[@apply_device_adaptations] Adapting {target_node} -> {adaptations[target_node]}")
                    step['target_node'] = adaptations[target_node]
                    step['description'] += f" (adapted for device: {target_node} -> {adaptations[target_node]})"
        
        # Update start_node if needed
        start_node = script_config.get('start_node')
        if start_node in adaptations:
            script_config['start_node'] = adaptations[start_node]
            
    except Exception as e:
        print(f"[@apply_device_adaptations] Error: {str(e)}")
