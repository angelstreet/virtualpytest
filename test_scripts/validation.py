#!/usr/bin/env python3
"""
Validation Script for VirtualPyTest

This script validates all transitions in a navigation tree using the unified script framework.

Usage:
    python scripts/validation.py <userinterface_name> [--host <host>] [--device <device>]
    
Example:
    python scripts/validation.py horizon_android_mobile
    python scripts/validation.py horizon_android_mobile --device device2
"""

import sys
import os

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor, ScriptExecutionContext, handle_keyboard_interrupt, handle_unexpected_error
from backend_core.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
from shared.lib.utils.report_utils import generate_validation_report
from shared.lib.utils.cloudflare_utils import upload_script_report, upload_validation_screenshots
from shared.lib.supabase.script_results_db import update_script_execution_result
from shared.lib.utils.action_utils import execute_navigation_with_verifications
from datetime import datetime


def custom_validation_step_handler(context: ScriptExecutionContext, step, step_num):
    """Custom step handler for validation that includes script_result_id"""
    return execute_navigation_with_verifications(
        context.host, context.selected_device, step, context.team_id, 
        context.tree_id, context.script_result_id, 'validation'
    )


def generate_validation_report_custom(context: ScriptExecutionContext, userinterface_name: str) -> str:
    """Generate custom validation report with statistics"""
    try:
        # Calculate verification statistics
        total_verifications = sum(len(step.get('verification_results', [])) for step in context.step_results)
        passed_verifications = sum(
            sum(1 for v in step.get('verification_results', []) if v.get('success', False)) 
            for step in context.step_results
        )
        failed_verifications = total_verifications - passed_verifications
        
        # Generate timestamp
        execution_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Prepare report data
        report_data = {
            'script_name': 'validation.py',
            'device_info': {
                'device_name': context.selected_device.device_name,
                'device_model': context.selected_device.device_model,
                'device_id': context.selected_device.device_id
            },
            'host_info': {
                'host_name': context.host.host_name
            },
            'execution_time': context.get_execution_time_ms(),
            'success': context.overall_success,
            'step_results': context.step_results,
            'screenshots': {
                'initial': context.screenshot_paths[0] if context.screenshot_paths else None,
                'steps': [step.get('screenshot_path') for step in context.step_results if step.get('screenshot_path')],
                'final': context.screenshot_paths[-1] if len(context.screenshot_paths) > 1 else None
            },
            'error_msg': context.error_message,
            'timestamp': execution_timestamp,
            'userinterface_name': userinterface_name,
            'total_steps': len(context.step_results),
            'passed_steps': sum(1 for step in context.step_results if step.get('success', False)),
            'failed_steps': sum(1 for step in context.step_results if not step.get('success', True)),
            'total_verifications': total_verifications,
            'passed_verifications': passed_verifications,
            'failed_verifications': failed_verifications
        }
        
        # Generate HTML report
        print("📄 [validation] Generating HTML report...")
        html_content = generate_validation_report(report_data)
        print("✅ [validation] HTML report generated")
        
        # Upload HTML report
        print("☁️ [validation] Uploading report to R2 storage...")
        upload_result = upload_script_report(
            html_content=html_content,
            device_model=context.selected_device.device_model,
            script_name="validation",
            timestamp=execution_timestamp
        )
        
        report_url = ""
        if upload_result['success']:
            report_url = upload_result['report_url']
            print(f"✅ [validation] Report uploaded: {report_url}")
            
            # Upload screenshots
            if context.screenshot_paths:
                screenshot_result = upload_validation_screenshots(
                    screenshot_paths=context.screenshot_paths,
                    device_model=context.selected_device.device_model,
                    script_name="validation",
                    timestamp=execution_timestamp
                )
                
                if screenshot_result['success']:
                    print(f"✅ [validation] Screenshots uploaded: {screenshot_result['uploaded_count']} files")
                else:
                    print(f"⚠️ [validation] Screenshot upload failed: {screenshot_result.get('error', 'Unknown error')}")
        else:
            print(f"⚠️ [validation] Report upload failed: {upload_result.get('error', 'Unknown error')}")
        
        # Update database with final results
        if context.script_result_id:
            print("📝 [validation] Updating database with final results...")
            update_success = update_script_execution_result(
                script_result_id=context.script_result_id,
                success=context.overall_success,
                execution_time_ms=context.get_execution_time_ms(),
                html_report_r2_path=upload_result.get('report_path') if upload_result['success'] else None,
                html_report_r2_url=report_url if report_url else None,
                error_msg=context.error_message if context.error_message else None,
                metadata={
                    'validation_sequence_count': len(context.step_results),
                    'step_results_count': len(context.step_results),
                    'screenshots_captured': len(context.screenshot_paths),
                    'passed_steps': sum(1 for step in context.step_results if step.get('success', False)),
                    'failed_steps': sum(1 for step in context.step_results if not step.get('success', True)),
                    'total_verifications': total_verifications,
                    'passed_verifications': passed_verifications,
                    'failed_verifications': failed_verifications
                }
            )
            
            if update_success:
                print("✅ [validation] Database updated successfully")
            else:
                print("⚠️ [validation] Failed to update database")
        
        return report_url
        
    except Exception as e:
        print(f"⚠️ [validation] Error in validation report generation: {e}")
        return ""


def print_validation_summary(context: ScriptExecutionContext, userinterface_name: str):
    """Print validation-specific summary"""
    # Calculate verification statistics
    total_verifications = sum(len(step.get('verification_results', [])) for step in context.step_results)
    passed_verifications = sum(
        sum(1 for v in step.get('verification_results', []) if v.get('success', False)) 
        for step in context.step_results
    )
    
        print("\n" + "="*60)
    print(f"🎯 [VALIDATION] EXECUTION SUMMARY")
        print("="*60)
    print(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    print(f"🖥️  Host: {context.host.host_name}")
        print(f"📋 Interface: {userinterface_name}")
    print(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    print(f"📊 Steps: {len(context.step_results)} executed")
    print(f"✅ Passed: {sum(1 for step in context.step_results if step.get('success', False))}")
    print(f"❌ Failed: {sum(1 for step in context.step_results if not step.get('success', True))}")
        print(f"🔍 Verifications: {passed_verifications}/{total_verifications} passed")
    print(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    print(f"🎯 Overall Result: {'PASS' if context.overall_success else 'FAIL'}")
    if context.error_message:
        print(f"❌ Error: {context.error_message}")
        print("="*60)


def main():
    """Main validation function with report generation"""
    script_name = "validation"
    executor = ScriptExecutor(script_name, "Validate navigation tree transitions")
    
    # Create argument parser
    parser = executor.create_argument_parser()
    args = parser.parse_args()
    
    # Setup execution context with database tracking enabled
    context = executor.setup_execution_context(args, enable_db_tracking=True)
    if context.error_message:
        executor.cleanup_and_exit(context, args.userinterface_name)
        return
    
    try:
        # Load navigation tree
        if not executor.load_navigation_tree(context, args.userinterface_name):
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        # Get validation sequence
        print("📋 [validation] Getting validation sequence...")
        validation_sequence = find_optimal_edge_validation_sequence(context.tree_id, context.team_id)
        
        if not validation_sequence:
            context.error_message = "No validation sequence found"
            print(f"❌ [validation] {context.error_message}")
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        print(f"✅ [validation] Found {len(validation_sequence)} validation steps")
        
        # Execute validation sequence with custom step handler
        success = executor.execute_navigation_sequence(
            context, validation_sequence, custom_validation_step_handler
        )
        context.overall_success = success
        
        if success:
            print("🎉 [validation] All validation steps completed successfully!")
        
        # Generate custom validation report
        generate_validation_report_custom(context, args.userinterface_name)
        
        # Print custom validation summary
        print_validation_summary(context, args.userinterface_name)
        
        # Exit with proper code based on test result
        if context.overall_success:
            print("✅ [validation] Validation completed successfully - exiting with code 0")
            sys.exit(0)
        else:
            print("❌ [validation] Validation failed - exiting with code 1") 
            sys.exit(1)
            
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)


if __name__ == "__main__":
    main() 