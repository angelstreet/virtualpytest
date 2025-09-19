#!/usr/bin/env python3
"""
AI Test Case Executor Script

This script executes AI-generated test cases by loading them from the database
and running them through the ScriptExecutor framework.

Usage: python ai_testcase_executor.py [userinterface_name] [--host host] [--device device]
"""

import sys
import os
from typing import Dict, List

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor, handle_keyboard_interrupt, handle_unexpected_error

def capture_ai_execution_summary(context, userinterface_name: str, test_case: dict, ai_steps: list) -> str:
    """Capture AI execution summary as text for report"""
    lines = []
    lines.append(f"🤖 [AI_TESTCASE] EXECUTION SUMMARY")
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"🧠 Test Case: {test_case.get('name', 'Unknown')}")
    lines.append(f"💭 Original Prompt: {test_case.get('original_prompt', 'N/A')}")
    lines.append(f"📍 AI Steps: {len(ai_steps)} executed")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    lines.append(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"❌ Error: {context.error_message}")
    
    return "\n".join(lines)

def main():
    """Main execution function"""
    # Extract test case ID from script name (passed via environment)
    script_name_env = os.environ.get('AI_SCRIPT_NAME', '')
    if not script_name_env.startswith('ai_testcase_'):
        print(f"[@ai_testcase_executor] ERROR: Invalid AI script name: {script_name_env}")
        sys.exit(1)
        
    test_case_id = script_name_env.replace('ai_testcase_', '')
    script_name = f"ai_testcase_{test_case_id}"
    
    # Load test case from database early to get display name
    try:
        from shared.lib.utils.app_utils import DEFAULT_TEAM_ID
        from shared.lib.supabase.testcase_db import get_test_case
        
        test_case = get_test_case(test_case_id, DEFAULT_TEAM_ID)
        if not test_case:
            print(f"[@ai_testcase_executor] ERROR: Test case not found: {test_case_id}")
            sys.exit(1)
            
        script_display_name = test_case.get('name', f"AI Test Case {test_case_id}")
        
    except Exception as e:
        print(f"[@ai_testcase_executor] ERROR loading test case: {str(e)}")
        sys.exit(1)
    
    # Initialize ScriptExecutor following the standard pattern
    executor = ScriptExecutor(script_name, script_display_name)
    
    # Create argument parser using ScriptExecutor framework
    parser = executor.create_argument_parser()
    args = parser.parse_args()
    
    print(f"[@ai_testcase_executor] Starting AI test case executor")
    print(f"[@ai_testcase_executor] Test Case: {script_display_name}")
    print(f"[@ai_testcase_executor] User Interface: {args.userinterface_name}")
    print(f"[@ai_testcase_executor] Host: {args.host}")
    print(f"[@ai_testcase_executor] Device: {args.device}")
    
    # Setup execution context with database tracking enabled
    context = executor.setup_execution_context(args, enable_db_tracking=True)
    if context.error_message:
        executor.cleanup_and_exit(context, args.userinterface_name)
        return
    # Ensure AI display name is available to report generator
    try:
        if not hasattr(context, 'custom_data') or context.custom_data is None:
            context.custom_data = {}
        context.custom_data['ai_testcase_name'] = script_display_name
    except Exception:
        pass
    
    try:
        # Load navigation tree
        if not executor.load_navigation_tree(context, args.userinterface_name):
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        print(f"[@ai_testcase_executor] Loaded navigation tree for {args.userinterface_name}")
        print(f"[@ai_testcase_executor] Original prompt: {test_case.get('original_prompt', 'N/A')}")
        
        # Get AI steps from test case
        ai_steps = test_case.get('steps', [])
        print(f"[@ai_testcase_executor] Processing {len(ai_steps)} AI steps")
        
        # Use AI Central for clean execution
        from shared.lib.utils.ai_central import AICentral, AIPlan, AIStep, AIStepType, ExecutionOptions, ExecutionMode
        
        print(f"[@ai_testcase_executor] Using AI Central with stored test case")
        
        # Convert stored steps to AI Central format
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
            userinterface_name=args.userinterface_name
        )
        
        # Execute using AI Central
        ai_central = AICentral(
            team_id=context.team_id,
            host={'host_name': context.host.host_name},
            device_id=context.selected_device.device_id
        )
        
        options = ExecutionOptions(
            mode=ExecutionMode.SCRIPT,
            context={'tree_id': test_case.get('tree_id')},
            enable_db_tracking=True
        )
        
        execution_id = ai_central.execute_plan(plan, options)
        
        # Wait for completion
        import time
        while True:
            status = ai_central.get_execution_status(execution_id)
            if not status.get('is_executing', False):
                ai_result = {'success': status.get('success', False)}
                break
            time.sleep(0.5)
        
        success = ai_result.get('success', False)
        context.overall_success = success
        
        print(f"[@ai_testcase_executor] AIAgentController execution result: {'SUCCESS' if success else 'FAILED'}")
        
        if not success:
            # Prefer detailed AI error surfaced by controller execution
            error_msg = ai_result.get('error')
            if not error_msg:
                # Try to extract a specific message from action/verification results
                ar = ai_result.get('action_result', {})
                vr = ai_result.get('verification_result', {})
                error_msg = ar.get('error') or vr.get('error')
                if not error_msg:
                    for s in (ar.get('step_results') or []):
                        if not s.get('success') and s.get('error'):
                            error_msg = s.get('error')
                            break
                if not error_msg:
                    for v in (vr.get('verification_results') or []):
                        if not v.get('success') and v.get('error'):
                            error_msg = v.get('error')
                            break
            if not error_msg:
                error_msg = 'AI plan execution failed'
            context.error_message = error_msg
            print(f"[@ai_testcase_executor] AI execution error: {error_msg}")
        
        # Capture summary for report
        summary_text = capture_ai_execution_summary(context, args.userinterface_name, test_case, ai_steps)
        context.execution_summary = summary_text
        
        if success:
            print(f"🎉 [@ai_testcase_executor] Successfully executed AI test case: {script_display_name}")
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)


if __name__ == "__main__":
    main()
