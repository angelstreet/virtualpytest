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

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args

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

def execute_ai_test_case(test_case_id: str, team_id: str) -> bool:
    """Execute AI test case - ai_testcase-specific logic"""
    context = get_context()
    
    # Load test case from database
    try:
        from shared.src.lib.supabase.testcase_db import get_test_case
        
        test_case = get_test_case(test_case_id, team_id)
        if not test_case:
            context.error_message = f"Test case not found: {test_case_id}"
            print(f"[@ai_testcase_executor] ERROR: {context.error_message}")
            return False
        
        script_display_name = test_case.get('name', f"AI Test Case {test_case_id}")
        print(f"[@ai_testcase_executor] Test Case: {script_display_name}")
        print(f"[@ai_testcase_executor] Original prompt: {test_case.get('original_prompt', 'N/A')}")
        
        # Store AI display name for report generator
        if not hasattr(context, 'custom_data') or context.custom_data is None:
            context.custom_data = {}
        context.custom_data['ai_testcase_name'] = script_display_name
        
    except Exception as e:
        context.error_message = f"Error loading test case: {str(e)}"
        print(f"[@ai_testcase_executor] ERROR: {context.error_message}")
        return False
    
    # Execute stored test case using AI executor
    try:
        device = context.selected_device
        if not device or not hasattr(device, 'ai_executor'):
            context.error_message = "Device or AI executor not found"
            print(f"[@ai_testcase_executor] ERROR: {context.error_message}")
            return False
        
        print(f"[@ai_testcase_executor] Executing stored test case {test_case_id}")
        ai_result = device.ai_executor.execute_testcase(test_case_id, team_id)
        
        success = ai_result.get('success', False)
        print(f"[@ai_testcase_executor] AIAgentController execution result: {'SUCCESS' if success else 'FAILED'}")
        
        if not success:
            # Extract detailed error message
            error_msg = ai_result.get('error')
            if not error_msg:
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
        else:
            print(f"🎉 [@ai_testcase_executor] Successfully executed AI test case: {script_display_name}")
        
        return success
        
    except Exception as e:
        context.error_message = f"AI execution error: {str(e)}"
        print(f"[@ai_testcase_executor] ERROR: {context.error_message}")
        return False

@script("ai_testcase", "Execute AI-generated test case")
def main():
    """Main execution function"""
    # Extract test case ID from script name (passed via environment)
    script_name_env = os.environ.get('AI_SCRIPT_NAME', '')
    if not script_name_env.startswith('ai_testcase_'):
        print(f"[@ai_testcase_executor] ERROR: Invalid AI script name: {script_name_env}")
        return False
        
    test_case_id = script_name_env.replace('ai_testcase_', '')
    
    # Get team_id from environment variable (set by host when executing)
    team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
    
    args = get_args()
    context = get_context()
    
    print(f"[@ai_testcase_executor] Starting AI test case executor")
    print(f"[@ai_testcase_executor] User Interface: {args.userinterface_name}")
    print(f"[@ai_testcase_executor] Host: {args.host}")
    print(f"[@ai_testcase_executor] Device: {args.device}")
    
    print(f"[@ai_testcase_executor] Loaded navigation tree for {args.userinterface_name}")
    
    # Execute AI test case using script-specific function
    success = execute_ai_test_case(test_case_id, team_id)
    
    if success:
        # Capture summary for report (need to reload test case for summary)
        try:
            from shared.src.lib.supabase.testcase_db import get_test_case
            test_case = get_test_case(test_case_id, team_id)
            stored_plan = test_case.get('ai_plan', {}) if test_case else {}
            summary_text = capture_ai_execution_summary(context, args.userinterface_name, test_case or {}, stored_plan.get('steps', []))
            context.execution_summary = summary_text
        except Exception:
            pass  # Summary is optional
    
    return success


if __name__ == "__main__":
    main()
