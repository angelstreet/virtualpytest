#!/usr/bin/env python3
"""
AI Test Case Executor Script

This script executes AI-generated test cases by loading them from the database
and running them through the ScriptExecutor framework.

Usage: python ai_testcase_executor.py <test_case_id> [userinterface_name] [--host host] [--device device]
"""

import sys
import os
import argparse
from typing import Dict, List

# Add project paths to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'shared', 'lib'))
sys.path.append(os.path.join(project_root, 'shared', 'lib', 'utils'))

def main():
    """Main execution function"""
    try:
        print(f"[@ai_testcase_executor] Starting AI test case executor")
        
        # Parse command line arguments - SAME FORMAT AS NORMAL SCRIPTS
        # Expected: python ai_testcase_executor.py horizon_android_mobile --host sunri-pi1 --device device2
        parser = argparse.ArgumentParser(description='Execute AI-generated test case')
        parser.add_argument('userinterface_name', help='User interface name')
        parser.add_argument('--host', required=True, help='Host name')
        parser.add_argument('--device', required=True, help='Device ID')
        
        args = parser.parse_args()
        
        print(f"[@ai_testcase_executor] User Interface: {args.userinterface_name}")
        print(f"[@ai_testcase_executor] Host: {args.host}")
        print(f"[@ai_testcase_executor] Device: {args.device}")
        
        # Extract test case ID from script name (passed via environment)
        script_name = os.environ.get('AI_SCRIPT_NAME', '')
        if not script_name.startswith('ai_testcase_'):
            print(f"[@ai_testcase_executor] ERROR: Invalid AI script name: {script_name}")
            sys.exit(1)
            
        test_case_id = script_name.replace('ai_testcase_', '')
        print(f"[@ai_testcase_executor] Test Case ID: {test_case_id}")
        
        # Load test case from database
        from shared.lib.utils.app_utils import DEFAULT_TEAM_ID
        from shared.lib.supabase.testcase_db import get_test_case
        
        print(f"[@ai_testcase_executor] Loading test case from database...")
        test_case = get_test_case(test_case_id, DEFAULT_TEAM_ID)
        
        if not test_case:
            print(f"[@ai_testcase_executor] ERROR: Test case not found: {test_case_id}")
            sys.exit(1)
            
        print(f"[@ai_testcase_executor] Loaded test case: {test_case.get('name', 'Unknown')}")
        print(f"[@ai_testcase_executor] Original prompt: {test_case.get('original_prompt', 'N/A')}")
        
        # Initialize ScriptExecutor
        from shared.lib.utils.script_framework import ScriptExecutor
        
        script_name = f"ai_testcase_{test_case_id}"
        script_display_name = test_case.get('name', f"AI Test Case {test_case_id}")
        executor = ScriptExecutor(script_name, script_display_name)
        
        print(f"[@ai_testcase_executor] Initialized ScriptExecutor: {script_display_name}")
        
        # Setup execution context
        context = executor.setup_execution_context(args, enable_db_tracking=True)
        
        if not context:
            print(f"[@ai_testcase_executor] ERROR: Failed to setup execution context")
            sys.exit(1)
            
        print(f"[@ai_testcase_executor] Setup execution context successfully")
        
        # Load navigation tree
        if not executor.load_navigation_tree(context, args.userinterface_name):
            print(f"[@ai_testcase_executor] ERROR: Failed to load navigation tree for {args.userinterface_name}")
            print(f"[@ai_testcase_executor] Error: {context.error_message}")
            sys.exit(1)
            
        print(f"[@ai_testcase_executor] Loaded navigation tree for {args.userinterface_name}")
        
        # Convert AI test case steps to navigation path
        navigation_path = convert_ai_steps_to_navigation_path(test_case.get('steps', []))
        print(f"[@ai_testcase_executor] Converted {len(test_case.get('steps', []))} AI steps to {len(navigation_path)} navigation steps")
        
        # Execute navigation sequence
        print(f"[@ai_testcase_executor] Starting navigation sequence execution...")
        success = executor.execute_navigation_sequence(context, navigation_path)
        context.overall_success = success
        
        # Set execution summary
        prompt = test_case.get('original_prompt', 'N/A')
        summary_text = f"AI Test Case: {script_display_name}\nOriginal Prompt: {prompt}\nSteps: {len(navigation_path)}\nResult: {'SUCCESS' if success else 'FAILED'}"
        context.execution_summary = summary_text
        
        print(f"[@ai_testcase_executor] Navigation sequence completed: {'SUCCESS' if success else 'FAILED'}")
        
        # Generate final report
        print(f"[@ai_testcase_executor] Generating execution report...")
        report_result = executor.generate_final_report(context, args.userinterface_name)
        
        if report_result.get('report_url'):
            print(f"[@ai_testcase_executor] Report generated: {report_result['report_url']}")
        
        # Clean up device control
        if context.device_key and context.session_id:
            from shared.lib.utils.device_control_utils import release_device_control
            release_device_control(context.device_key, context.session_id, script_name)
            print(f"[@ai_testcase_executor] Released device control")
        
        # Output final result (this is what the script execution pipeline expects)
        print(f"[@ai_testcase_executor] === EXECUTION COMPLETE ===")
        print(f"AI Test Case: {script_display_name}")
        print(f"Original Prompt: {prompt}")
        print(f"Steps Executed: {len(navigation_path)}")
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        if report_result.get('report_url'):
            print(f"Report: {report_result['report_url']}")
        
        # Use the standard script success marker
        print(f"SCRIPT_SUCCESS:{str(success).lower()}")
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"[@ai_testcase_executor] FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        print("SCRIPT_SUCCESS:false")
        sys.exit(1)


def convert_ai_steps_to_navigation_path(ai_steps: List[Dict]) -> List[Dict]:
    """Convert AI test case steps to navigation path format expected by ScriptExecutor"""
    navigation_path = []
    
    for i, step in enumerate(ai_steps):
        if step.get('type') == 'action':
            command = step.get('command')
            params = step.get('params', {})
            description = step.get('description', f'Execute {command}')
            
            if command == 'navigate':
                target_node = params.get('target_node')
                if target_node:
                    navigation_path.append({
                        'step_number': i + 1,
                        'from_node_label': 'current',
                        'to_node_label': target_node,
                        'actions': [step],
                        'verifications': []
                    })
            elif command in ['click_element', 'wait', 'press_key']:
                navigation_path.append({
                    'step_number': i + 1,
                    'from_node_label': 'current',
                    'to_node_label': 'current',
                    'actions': [step],
                    'verifications': []
                })
    
    # If no valid navigation steps, create a default one
    if not navigation_path:
        navigation_path.append({
            'step_number': 1,
            'from_node_label': 'home',
            'to_node_label': 'home',
            'actions': [{
                'type': 'action',
                'command': 'wait',
                'params': {'duration': 2000},
                'description': 'Execute AI test case'
            }],
            'verifications': []
        })
    
    return navigation_path


if __name__ == '__main__':
    main()
