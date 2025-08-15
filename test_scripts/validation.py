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
from shared.lib.utils.action_utils import execute_navigation_with_verifications


def custom_validation_step_handler(context: ScriptExecutionContext, step, step_num):
    """Enhanced validation step handler with failure tolerance and position tracking"""
    try:
        result = execute_navigation_with_verifications(
            context.host, context.selected_device, step, context.team_id, 
            context.tree_id, context.script_result_id, 'validation', 
            context.global_verification_counter
        )
        
        # Update global verification counter for next step
        counter_increment = result.get('global_verification_counter_increment', 0)
        context.global_verification_counter += counter_increment
        print(f"🔢 [validation] Updated global verification counter: +{counter_increment} = {context.global_verification_counter}")
        
        # Update current position tracking
        if result.get('success', False):
            # If step was successful, update current position to the target node
            context.current_node_id = step.get('to_node_id')
            print(f"📍 [validation] Updated current position to: {context.current_node_id} ({step.get('to_node_label', 'unknown')})")
        else:
            # If step failed, we might still be at the previous position or unknown
            print(f"⚠️ [validation] Step failed, current position uncertain. Staying at: {context.current_node_id}")
        
        # Note: Failed step recording is handled by the main execution sequence
        # to avoid duplicate entries
        
        return result
        
    except Exception as e:
        # Even if step handler fails, don't crash entire validation
        print(f"⚠️ [validation] Step handler error: {e}")
        return {
            'success': False,
            'error': f'Step handler exception: {str(e)}',
            'verification_results': [],
            'global_verification_counter_increment': 0
        }



def capture_validation_summary(context: ScriptExecutionContext, userinterface_name: str) -> str:
    """Capture validation summary as text for report"""
    # Calculate verification statistics
    total_verifications = sum(len(step.get('verification_results', [])) for step in context.step_results)
    passed_verifications = sum(
        sum(1 for v in step.get('verification_results', []) if v.get('success', False)) 
        for step in context.step_results
    )
    
    successful_steps = sum(1 for step in context.step_results if step.get('success', False))
    failed_steps = sum(1 for step in context.step_results if not step.get('success', False))
    recovered_steps = context.recovered_steps
    
    lines = []
    lines.append("🎯 [VALIDATION] EXECUTION SUMMARY")
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📊 Steps: {successful_steps}/{len(context.step_results)} steps successful")
    lines.append(f"✅ Successful: {successful_steps}")
    lines.append(f"❌ Failed: {failed_steps}")
    lines.append(f"🔄 Recovered: {recovered_steps}")
    lines.append(f"🔍 Verifications: {passed_verifications}/{total_verifications} passed")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    lines.append(f"🎯 Coverage: {((successful_steps + recovered_steps) / len(context.step_results) * 100):.1f}%")
    
    failed_step_details = [step for step in context.step_results if not step.get('success', False)]
    if failed_step_details:
        lines.append("\n❌ Failed Steps Details:")
        for failed_step in failed_step_details:
            step_num = failed_step.get('step_number')
            from_node = failed_step.get('from_node')
            to_node = failed_step.get('to_node')
            # Get the error from step-level error field first, then verification results
            error = failed_step.get('error')
            if not error:
                # Check verification results as fallback
                verification_results = failed_step.get('verification_results', [])
                if verification_results and verification_results[0].get('error'):
                    error = verification_results[0].get('error')
                else:
                    error = 'Unknown error'
            lines.append(f"   Step {step_num}: {from_node} → {to_node}")
            lines.append(f"     Error: {error}")
    
    # Add detailed step results for frontend parsing
    lines.append("")
    lines.append("📋 [VALIDATION] DETAILED STEP RESULTS")
    lines.append("="*60)
    for i, step in enumerate(context.step_results):
        step_success = step.get('success', False)
        from_node = step.get('from_node', 'unknown')
        to_node = step.get('to_node', 'unknown')
        
        # Get execution time using the same logic as the report generation
        execution_time_ms = step.get('execution_time_ms', 0)
        
        # Use the same formatting function as the report to ensure consistency
        from shared.lib.utils.report_utils import format_execution_time
        execution_time_formatted = format_execution_time(execution_time_ms) if execution_time_ms else "0.0s"
        
        # Extract just the numeric part and unit for our format
        if execution_time_formatted.endswith('ms'):
            duration_value = float(execution_time_formatted[:-2]) / 1000  # Convert ms to seconds
        elif execution_time_formatted.endswith('s') and 'm' not in execution_time_formatted:
            duration_value = float(execution_time_formatted[:-1])  # Already in seconds
        elif 'm' in execution_time_formatted and 's' in execution_time_formatted:
            # Format like "2m 15.3s"
            parts = execution_time_formatted.split('m ')
            minutes = float(parts[0])
            seconds = float(parts[1][:-1])  # Remove 's'
            duration_value = minutes * 60 + seconds
        else:
            duration_value = 0.0
        
        # Get action and verification counts from original step data
        actions = step.get('actions', [])
        verifications = step.get('verifications', [])
        verification_results = step.get('verification_results', [])
        
        actions_executed = len(actions) if actions else 0
        total_actions = len(actions) if actions else 0
        verifications_executed = len(verification_results) if verification_results else 0
        total_verifications = len(verifications) if verifications else 0
        
        # Get error message
        error_msg = "-"
        if not step_success and verification_results:
            error_msg = verification_results[0].get('error', 'Step failed') if verification_results[0] else 'Step failed'
        
        lines.append(f"STEP_DETAIL:{i+1}|{from_node}|{to_node}|{'PASS' if step_success else 'FAIL'}|{duration_value:.1f}s|{actions_executed}|{total_actions}|{verifications_executed}|{total_verifications}|{error_msg}")
    
    lines.append("="*60)
    
    return "\n".join(lines)


def print_validation_summary(context: ScriptExecutionContext, userinterface_name: str):
    """Print enhanced validation summary with recovery stats"""
    # Calculate verification statistics
    total_verifications = sum(len(step.get('verification_results', [])) for step in context.step_results)
    passed_verifications = sum(
        sum(1 for v in step.get('verification_results', []) if v.get('success', False)) 
        for step in context.step_results
    )
    
    successful_steps = sum(1 for step in context.step_results if step.get('success', False))
    failed_steps = sum(1 for step in context.step_results if not step.get('success', False))
    recovered_steps = context.recovered_steps
    
    print("\n" + "="*60)
    print(f"🎯 [VALIDATION] EXECUTION SUMMARY")
    print("="*60)
    print(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    print(f"🖥️  Host: {context.host.host_name}")
    print(f"📋 Interface: {userinterface_name}")
    print(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    print(f"📊 Steps: {successful_steps}/{len(context.step_results)} steps successful")
    print(f"✅ Successful: {successful_steps}")
    print(f"❌ Failed: {failed_steps}")
    print(f"🔄 Recovered: {recovered_steps}")
    print(f"🔍 Verifications: {passed_verifications}/{total_verifications} passed")
    print(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    print(f"🎯 Coverage: {((successful_steps + recovered_steps) / len(context.step_results) * 100):.1f}%")
    
    failed_step_details = [step for step in context.step_results if not step.get('success', False)]
    if failed_step_details:
        print(f"\n❌ Failed Steps Details:")
        for failed_step in failed_step_details:
            step_num = failed_step.get('step_number')
            from_node = failed_step.get('from_node')
            to_node = failed_step.get('to_node')
            # Get the error from step-level error field first, then verification results
            error = failed_step.get('error')
            if not error:
                # Check verification results as fallback
                verification_results = failed_step.get('verification_results', [])
                if verification_results and verification_results[0].get('error'):
                    error = verification_results[0].get('error')
                else:
                    error = 'Unknown error'
            print(f"   Step {step_num}: {from_node} → {to_node}")
            print(f"     Error: {error}")
    
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
        
        # Initialize current position to entry point for pathfinding
        from shared.lib.utils.navigation_cache import get_cached_unified_graph
        from shared.lib.utils.navigation_graph import get_entry_points
        
        unified_graph = get_cached_unified_graph(context.tree_id, context.team_id)
        if unified_graph:
            entry_points = get_entry_points(unified_graph)
            if entry_points:
                context.current_node_id = entry_points[0]
                print(f"📍 [validation] Starting validation from entry point: {context.current_node_id}")
            else:
                print(f"⚠️ [validation] No entry points found, starting with unknown position")
        
        # Get validation sequence
        print("📋 [validation] Getting validation sequence...")
        validation_sequence = find_optimal_edge_validation_sequence(context.tree_id, context.team_id)
        
        if not validation_sequence:
            context.error_message = "No validation sequence found"
            print(f"❌ [validation] {context.error_message}")
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        print(f"✅ [validation] Found {len(validation_sequence)} validation steps")
        
        # Execute validation sequence with custom step handler and recovery (no early stopping)
        success = executor.execute_navigation_sequence(
            context, validation_sequence, custom_validation_step_handler, early_stop_on_failure=False
        )
        
        # Calculate validation success based on actual step results
        successful_steps = sum(1 for step in context.step_results if step.get('success', False))
        total_steps = len(context.step_results)
        
        # Validation is successful only if ALL steps pass
        # For validation, we need 100% success rate
        context.overall_success = successful_steps == total_steps and total_steps > 0
        
        # Print custom validation summary and capture it
        summary_text = capture_validation_summary(context, args.userinterface_name)
        print_validation_summary(context, args.userinterface_name)
        
        # Print the detailed summary to stdout for frontend parsing
        print(summary_text)
        
        # Store summary for report
        context.execution_summary = summary_text
        
        if context.overall_success:
            print(f"🎉 [validation] All {successful_steps}/{total_steps} validation steps passed successfully!")
        else:
            print(f"❌ [validation] Validation failed: {successful_steps}/{total_steps} steps passed")
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        # Use the same cleanup approach as goto_live_fullscreen.py
        executor.cleanup_and_exit(context, args.userinterface_name)


if __name__ == "__main__":
    main() 