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
from datetime import datetime
import time


def custom_validation_step_handler(context: ScriptExecutionContext, step, step_num):
    """Enhanced validation step handler with force navigation recovery on failure"""
    try:
        # Attempt normal navigation execution first
        result = execute_navigation_with_verifications(
            context.host, context.selected_device, step, context.team_id, 
            context.tree_id, context.script_result_id, 'validation', 
            context.global_verification_counter
        )
        
        # Update global verification counter for next step
        counter_increment = result.get('global_verification_counter_increment', 0)
        context.global_verification_counter += counter_increment
        print(f"🔢 [validation] Updated global verification counter: +{counter_increment} = {context.global_verification_counter}")
        
        # If step was successful, update position and return
        if result.get('success', False):
            context.current_node_id = step.get('to_node_id')
            print(f"📍 [validation] Updated current position to: {context.current_node_id} ({step.get('to_node_label', 'unknown')})")
            return result
        
        # Step failed - attempt force navigation recovery to target node
        target_node_label = step.get('to_node_label')
        if not target_node_label:
            print(f"❌ [validation] No target node for force navigation recovery")
            return result
        
        print(f"🔄 [validation] Step {step_num} failed, attempting force navigation to '{target_node_label}'...")
        
        # Try force navigation using goto_node (which uses unified pathfinding)
        try:
            from shared.lib.utils.navigation_utils import goto_node
            
            force_nav_start_time = time.time()
            force_nav_result = goto_node(
                context.host, 
                context.selected_device, 
                target_node_label, 
                context.tree_id, 
                context.team_id,
                context  # Pass context for position tracking
            )
            force_nav_time = int((time.time() - force_nav_start_time) * 1000)
            
            if force_nav_result.get('success'):
                print(f"✅ [validation] Force navigation to '{target_node_label}' successful in {force_nav_time}ms")
                
                # Update position to target node since force navigation succeeded
                context.current_node_id = step.get('to_node_id')
                print(f"📍 [validation] Updated current position to: {context.current_node_id} ({target_node_label})")
                
                # Return successful result with force navigation flag
                return {
                    'success': True,
                    'force_navigation_used': True,
                    'force_navigation_time_ms': force_nav_time,
                    'verification_results': force_nav_result.get('verification_results', []),
                    'global_verification_counter_increment': force_nav_result.get('global_verification_counter_increment', 0),
                    'message': f"Force navigation to '{target_node_label}' successful after step failure"
                }
            else:
                # Force navigation also failed - this is a critical failure
                force_nav_error = force_nav_result.get('error', 'Force navigation failed')
                print(f"❌ [validation] Force navigation to '{target_node_label}' failed: {force_nav_error}")
                print(f"🛑 [validation] CRITICAL: Both normal step and force navigation failed - stopping validation")
                
                # Mark this as a critical failure that should stop the script
                return {
                    'success': False,
                    'critical_failure': True,
                    'error': f'Both normal navigation and force navigation failed: {force_nav_error}',
                    'verification_results': [],
                    'global_verification_counter_increment': 0,
                    'original_error': result.get('error', 'Original step failed'),
                    'force_navigation_error': force_nav_error
                }
                
        except Exception as force_nav_exception:
            print(f"❌ [validation] Force navigation exception: {str(force_nav_exception)}")
            print(f"🛑 [validation] CRITICAL: Force navigation failed with exception - stopping validation")
            
            # Critical failure due to force navigation exception
            return {
                'success': False,
                'critical_failure': True,
                'error': f'Force navigation exception: {str(force_nav_exception)}',
                'verification_results': [],
                'global_verification_counter_increment': 0,
                'original_error': result.get('error', 'Original step failed')
            }
        
    except Exception as e:
        # Even if step handler fails, don't crash entire validation
        print(f"⚠️ [validation] Step handler error: {e}")
        return {
            'success': False,
            'error': f'Step handler exception: {str(e)}',
            'verification_results': [],
            'global_verification_counter_increment': 0
        }


def execute_validation_sequence_with_force_recovery(executor: ScriptExecutor, context: ScriptExecutionContext, 
                                                   navigation_path: list, custom_step_handler) -> bool:
    """
    Execute validation sequence with force navigation recovery.
    Stops immediately if both normal navigation and force navigation fail for any step.
    """
    try:
        print(f"🎮 [validation] Starting validation sequence with force recovery on device {context.selected_device.device_id}")
        
        for i, step in enumerate(navigation_path):
            step_num = i + 1
            from_node = step.get('from_node_label', 'unknown')
            to_node = step.get('to_node_label', 'unknown')
            
            print(f"⚡ [validation] Executing step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
            
            # Execute the navigation step using custom handler
            step_start_time = time.time()
            step_start_timestamp = datetime.now().strftime('%H:%M:%S')
            
            result = custom_step_handler(context, step, step_num)
            
            step_end_timestamp = datetime.now().strftime('%H:%M:%S')
            step_execution_time = int((time.time() - step_start_time) * 1000)
            
            # Collect screenshots from result
            action_screenshots = result.get('action_screenshots', [])
            for screenshot_path in action_screenshots:
                context.add_screenshot(screenshot_path)
            
            # Add step screenshots
            if result.get('step_start_screenshot_path'):
                context.add_screenshot(result.get('step_start_screenshot_path'))
            if result.get('step_end_screenshot_path'):
                context.add_screenshot(result.get('step_end_screenshot_path'))
            if result.get('screenshot_path'):
                context.add_screenshot(result.get('screenshot_path'))
            
            # Collect verification images
            verification_images = result.get('verification_images', [])
            for verification_image in verification_images:
                context.add_screenshot(verification_image)
            
            # Update global verification counter
            counter_increment = result.get('global_verification_counter_increment', 0)
            context.global_verification_counter += counter_increment
            
            # Record step result
            step_result = {
                'step_number': step_num,
                'success': result.get('success', False),
                'step_start_screenshot_path': result.get('step_start_screenshot_path'),
                'step_end_screenshot_path': result.get('step_end_screenshot_path'),
                'screenshot_path': result.get('screenshot_path'),
                'screenshot_url': result.get('screenshot_url'),
                'action_screenshots': action_screenshots,
                'verification_images': verification_images,
                'message': f"Validation step {step_num}: {from_node} → {to_node}",
                'execution_time_ms': step_execution_time,
                'start_time': step_start_timestamp,
                'end_time': step_end_timestamp,
                'from_node': from_node,
                'to_node': to_node,
                'actions': step.get('actions', []),
                'verifications': step.get('verifications', []),
                'verification_results': result.get('verification_results', []),
                'error': result.get('error'),
                'recovered': result.get('force_navigation_used', False),
                'force_navigation_used': result.get('force_navigation_used', False),
                'force_navigation_time_ms': result.get('force_navigation_time_ms', 0)
            }
            context.step_results.append(step_result)
            
            # Check for critical failure (both normal and force navigation failed)
            if result.get('critical_failure', False):
                critical_error = result.get('error', 'Critical failure occurred')
                print(f"🛑 [validation] CRITICAL FAILURE at step {step_num}: {critical_error}")
                print(f"🛑 [validation] Stopping validation - cannot continue after failed force navigation")
                
                # Record the failed step
                context.failed_steps.append({
                    'step_number': step_num,
                    'from_node': from_node,
                    'to_node': to_node,
                    'error': critical_error,
                    'verification_results': result.get('verification_results', []),
                    'critical_failure': True,
                    'original_error': result.get('original_error'),
                    'force_navigation_error': result.get('force_navigation_error')
                })
                
                context.error_message = f"Critical failure at step {step_num}: {critical_error}"
                context.overall_success = False
                return False
            
            # Handle regular step failure (should not happen with our new logic, but safety check)
            if not result.get('success', False):
                failure_msg = f"Step {step_num} failed: {result.get('error', 'Unknown error')}"
                print(f"⚠️ [validation] {failure_msg}")
                
                context.failed_steps.append({
                    'step_number': step_num,
                    'from_node': from_node,
                    'to_node': to_node,
                    'error': result.get('error'),
                    'verification_results': result.get('verification_results', [])
                })
                
                # Continue to next step (this shouldn't happen with force navigation, but handle gracefully)
                continue
            else:
                # Step was successful (either normally or via force navigation)
                if result.get('force_navigation_used'):
                    print(f"🔄 [validation] Step {step_num} recovered via force navigation in {step_execution_time}ms")
                    context.recovered_steps += 1
                else:
                    print(f"✅ [validation] Step {step_num} completed successfully in {step_execution_time}ms")
        
        # Calculate overall success
        total_successful = len([s for s in context.step_results if s.get('success', False)])
        total_steps = len(navigation_path)
        success_rate = total_successful / total_steps if total_steps > 0 else 0
        
        print(f"🎉 [validation] Validation sequence completed!")
        print(f"📊 [validation] Results: {total_successful}/{total_steps} steps successful ({success_rate:.1%})")
        print(f"🔄 [validation] Recovery: {context.recovered_steps} steps recovered via force navigation")
        
        return total_successful == total_steps
        
    except Exception as e:
        print(f"❌ [validation] Execution sequence error: {e}")
        context.error_message = f"Validation sequence execution failed: {str(e)}"
        context.overall_success = False
        return False


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
    recovered_steps = sum(1 for step in context.step_results if step.get('force_navigation_used', False))
    context.recovered_steps = recovered_steps  # Update context for consistency
    
    lines = []
    lines.append("🎯 [VALIDATION] EXECUTION SUMMARY")
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📊 Steps: {successful_steps}/{len(context.step_results)} steps successful")
    lines.append(f"✅ Successful: {successful_steps}")
    lines.append(f"❌ Failed: {failed_steps}")
    lines.append(f"🔄 Force Navigation Recoveries: {recovered_steps}")
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
    recovered_steps = sum(1 for step in context.step_results if step.get('force_navigation_used', False))
    
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
    print(f"🔄 Force Navigation Recoveries: {recovered_steps}")
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
        
        # Execute validation sequence with custom step handler and critical failure detection
        success = execute_validation_sequence_with_force_recovery(
            executor, context, validation_sequence, custom_validation_step_handler
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