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


def get_node_label_from_id(node_id: str, tree_id: str, team_id: str) -> str:
    """
    Helper function to get node label from node ID for better error logging
    
    Args:
        node_id: Node ID to resolve
        tree_id: Tree ID for unified graph access
        team_id: Team ID for security
        
    Returns:
        Node label if found, otherwise returns the node_id with (unknown) suffix
    """
    try:
        from shared.lib.utils.navigation_cache import get_cached_unified_graph
        from shared.lib.utils.navigation_graph import get_node_info
        
        unified_graph = get_cached_unified_graph(tree_id, team_id)
        if unified_graph:
            node_info = get_node_info(unified_graph, node_id)
            if node_info:
                label = node_info.get('label', 'unknown')
                return f"{label} ({node_id})"
        
        return f"{node_id} (unknown label)"
        
    except Exception as e:
        print(f"[@validation] Error resolving node label for {node_id}: {e}")
        return f"{node_id} (label lookup failed)"


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
            target_label = step.get('to_node_label', 'unknown')
            print(f"📍 [validation] Updated current position to: {target_label} ({context.current_node_id})")
            return result
        
        # Step failed - mark as failed and reset position for recovery
        print(f"❌ [validation] Step {step_num} failed, resetting position for recovery...")
        
        # Reset position to start fresh from Entry for next steps
        context.current_node_id = None
        print(f"📍 [validation] Reset current position to Entry for recovery")
        
        # Return failed result but with recovery flag - validation will continue
        # Preserve all screenshot and image data from the original result
        return {
            'success': False,  # Original step still failed
            'recovered': True,  # But we recovered position for next steps
            'recovery_used': True,
            'error': result.get('error', 'Step failed'),
            'verification_results': result.get('verification_results', []),
            'global_verification_counter_increment': result.get('global_verification_counter_increment', 0),
            'message': f"Step failed but reset to Entry - validation continues",
            # Preserve screenshot data so failed steps show images in reports
            'step_start_screenshot_path': result.get('step_start_screenshot_path'),
            'step_end_screenshot_path': result.get('step_end_screenshot_path'),
            'screenshot_path': result.get('screenshot_path'),
            'screenshot_url': result.get('screenshot_url'),
            'action_screenshots': result.get('action_screenshots', []),
            'verification_images': result.get('verification_images', [])
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


def _record_skipped_steps(context: ScriptExecutionContext, navigation_path: list, start_step_num: int):
    """Record all remaining steps as skipped when validation stops early"""
    if not hasattr(context, 'skipped_steps'):
        context.skipped_steps = []
    
    total_steps = len(navigation_path)
    for i in range(start_step_num - 1, total_steps):  # start_step_num is 1-based
        step = navigation_path[i]
        step_num = i + 1
        from_node = step.get('from_node_label', 'unknown')
        to_node = step.get('to_node_label', 'unknown')
        
        skipped_step = {
            'step_number': step_num,
            'from_node': from_node,
            'to_node': to_node,
            'skipped': True,
            'reason': 'Validation stopped due to critical failure in previous step'
        }
        context.skipped_steps.append(skipped_step)
        
        # Also add to step_results for consistent reporting
        step_result = {
            'step_number': step_num,
            'success': False,
            'skipped': True,
            'message': f"Skipped step {step_num}: {from_node} → {to_node}",
            'from_node': from_node,
            'to_node': to_node,
            'actions': step.get('actions', []),
            'verifications': step.get('verifications', []),
            'verification_results': [],
            'error': 'Skipped due to critical failure',
            'execution_time_ms': 0
        }
        context.step_results.append(step_result)
    
    skipped_count = total_steps - (start_step_num - 1)
    print(f"⏭️  [validation] Marked {skipped_count} remaining steps as skipped")


def execute_validation_sequence_with_force_recovery(executor: ScriptExecutor, context: ScriptExecutionContext, 
                                                   navigation_path: list, custom_step_handler) -> bool:
    """
    Execute validation sequence with force navigation recovery - each step as top-level.
    Stops immediately if both normal navigation and force navigation fail for any step.
    """
    try:
        # Initialize skipped steps tracking
        if not hasattr(context, 'skipped_steps'):
            context.skipped_steps = []
            
        print(f"🎮 [validation] Starting validation sequence with force recovery on device {context.selected_device.device_id}")
        
        for i, step in enumerate(navigation_path):
            step_num = i + 1
            from_node = step.get('from_node_label', 'unknown')
            to_node = step.get('to_node_label', 'unknown')
            
            # Each validation step is a top-level step
            # Simple sequential recording - no context needed
            
            try:
                print(f"⚡ [validation] Executing step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
                
                # Execute the navigation step using custom handler
                step_start_time = time.time()
                step_start_timestamp = datetime.now().strftime('%H:%M:%S')
                
                result = custom_step_handler(context, step, step_num)
                
                step_end_timestamp = datetime.now().strftime('%H:%M:%S')
                step_execution_time = int((time.time() - step_start_time) * 1000)
            finally:
                context.pop_context()
            
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
            
            # Record step result using hierarchical context
            step_result = {
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
                'recovered': result.get('recovered', False),
                'recovery_used': result.get('recovery_used', False),
                'recovery_time_ms': result.get('recovery_time_ms', 0),
                'additional_context': result.get('additional_context'),
                'recovery_error': result.get('recovery_error'),
                'step_category': 'validation'
            }
            
            # Record step immediately and get step number
            step_number = context.record_step_immediately(step_result)
            # Update message with actual step number
            step_result['message'] = f"Step {step_number} - Validation step {step_num}: {from_node} → {to_node}"
            
            # Check for critical failure (both normal and force navigation failed)
            if result.get('critical_failure', False):
                critical_error = result.get('error', 'Critical failure occurred')
                print(f"🛑 [validation] CRITICAL FAILURE at step {step_num}: {critical_error}")
                print(f"🛑 [validation] Stopping validation - cannot continue after failed recovery")
                
                # Record the failed step
                context.failed_steps.append({
                    'step_number': step_num,
                    'from_node': from_node,
                    'to_node': to_node,
                    'error': critical_error,
                    'verification_results': result.get('verification_results', []),
                    'critical_failure': True,
                    'original_error': result.get('original_error'),
                    'recovery_error': result.get('recovery_error')
                })
                
                # Record all remaining steps as skipped
                _record_skipped_steps(context, navigation_path, step_num + 1)
                
                context.error_message = f"Critical failure at step {step_num}: {critical_error}"
                context.overall_success = False
                return False
            
            # Handle regular step failure with recovery
            if not result.get('success', False):
                if result.get('recovered', False):
                    # Step failed but we recovered - continue validation
                    print(f"🔄 [validation] Step {step_num} failed but recovered to Entry in {step_execution_time}ms - continuing validation")
                    context.recovered_steps += 1
                else:
                    # Step failed and no recovery - this should not happen with new logic
                    failure_msg = f"Step {step_num} failed: {result.get('error', 'Unknown error')}"
                    print(f"⚠️ [validation] {failure_msg}")
                    
                    context.failed_steps.append({
                        'step_number': step_num,
                        'from_node': from_node,
                        'to_node': to_node,
                        'error': result.get('error'),
                        'verification_results': result.get('verification_results', [])
                    })
                    
                    # Continue to next step (this shouldn't happen with recovery, but handle gracefully)
                    continue
            else:
                # Step was successful normally
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
    failed_steps = sum(1 for step in context.step_results if not step.get('success', False) and not step.get('skipped', False))
    skipped_steps = sum(1 for step in context.step_results if step.get('skipped', False))
    recovered_steps = sum(1 for step in context.step_results if step.get('recovered', False))
    context.recovered_steps = recovered_steps  # Update context for consistency
    
    lines = []
    lines.append("-"*60)
    lines.append("🎯 [VALIDATION] EXECUTION SUMMARY")
    lines.append("-"*60)
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📊 Steps: {successful_steps}/{len(context.step_results)} steps successful")
    lines.append(f"✅ Successful: {successful_steps}")
    lines.append(f"❌ Failed: {failed_steps}")
    lines.append(f"⏭️ Skipped: {skipped_steps}")
    lines.append(f"🔄 Recovery Navigations: {recovered_steps}")
    lines.append(f"🔍 Verifications: {passed_verifications}/{total_verifications} passed")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    
    # Add report URL if available
    report_url = context.custom_data.get('report_url') if hasattr(context, 'custom_data') else None
    if report_url:
        lines.append(f"📋 Report: {report_url}")
    
    lines.append(f"🎯 Coverage: {((successful_steps + recovered_steps) / len(context.step_results) * 100):.1f}%")
    
    failed_step_details = [step for step in context.step_results if not step.get('success', False) and not step.get('skipped', False)]
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
            
            # Show additional context if available (e.g., force navigation failure details)
            additional_context = failed_step.get('additional_context')
            if additional_context:
                lines.append(f"     Additional: {additional_context}")
    
    # Add skipped steps summary in one line
    skipped_step_details = [step for step in context.step_results if step.get('skipped', False)]
    if skipped_step_details:
        skipped_step_numbers = [str(step.get('step_number')) for step in skipped_step_details]
        lines.append(f"\n⏭️ Skipped Steps: {', '.join(skipped_step_numbers)}")
    
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
        
        # Get error message and status
        error_msg = "-"
        step_status = "PASS"
        
        if step.get('skipped', False):
            step_status = "SKIP"
            error_msg = "Skipped due to critical failure"
        elif not step_success:
            step_status = "FAIL"
            if verification_results:
                error_msg = verification_results[0].get('error', 'Step failed') if verification_results[0] else 'Step failed'
            else:
                error_msg = step.get('error', 'Step failed')
        
        lines.append(f"STEP_DETAIL:{i+1}|{from_node}|{to_node}|{step_status}|{duration_value:.1f}s|{actions_executed}|{total_actions}|{verifications_executed}|{total_verifications}|{error_msg}")
    
    lines.append("="*60)
    
    # Add script report URL if available
    if hasattr(context, 'script_report_url') and context.script_report_url:
        lines.append("")
        lines.append(f"SCRIPT_REPORT_URL:{context.script_report_url}")
    
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
    failed_steps = sum(1 for step in context.step_results if not step.get('success', False) and not step.get('skipped', False))
    skipped_steps = sum(1 for step in context.step_results if step.get('skipped', False))
    recovered_steps = sum(1 for step in context.step_results if step.get('recovered', False))
    
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
    print(f"⏭️ Skipped: {skipped_steps}")
    print(f"🔄 Recovery Navigations: {recovered_steps}")
    print(f"🔍 Verifications: {passed_verifications}/{total_verifications} passed")
    print(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    print(f"🎯 Coverage: {((successful_steps + recovered_steps) / len(context.step_results) * 100):.1f}%")
    
    failed_step_details = [step for step in context.step_results if not step.get('success', False) and not step.get('skipped', False)]
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
            
            # Show additional context if available (e.g., force navigation failure details)
            additional_context = failed_step.get('additional_context')
            if additional_context:
                print(f"     Additional: {additional_context}")
    
    # Add skipped steps summary in one line
    skipped_step_details = [step for step in context.step_results if step.get('skipped', False)]
    if skipped_step_details:
        skipped_step_numbers = [str(step.get('step_number')) for step in skipped_step_details]
        print(f"\n⏭️ Skipped Steps: {', '.join(skipped_step_numbers)}")
    
    print("="*60)
    
    # Add script report URL if available
    if hasattr(context, 'script_report_url') and context.script_report_url:
        print("")
        print(f"SCRIPT_REPORT_URL:{context.script_report_url}")


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
        
        if context.overall_success:
            print(f"🎉 [validation] All {successful_steps}/{total_steps} validation steps passed successfully!")
        else:
            print(f"❌ [validation] Validation failed: {successful_steps}/{total_steps} steps passed")
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        # Generate report first to get the URL
        report_url = None
        report_result = None
        if 'context' in locals() and context and context.host and context.selected_device:
            try:
                report_result = executor.generate_final_report(context, args.userinterface_name)
                if report_result and report_result.get('success') and report_result.get('report_url'):
                    report_url = report_result.get('report_url')
                    print(f"SCRIPT_REPORT_URL:{report_url}")
            except Exception as e:
                print(f"⚠️ [validation] Error generating report: {e}")
        
        # Print detailed validation summary and store extra info for framework summary
        if 'context' in locals() and context:
            summary_text = capture_validation_summary(context, args.userinterface_name)
            print(summary_text)
            context.execution_summary = summary_text
            
            # Extract validation-specific metrics for framework summary
            if report_url:
                context.custom_data['report_url'] = report_url
            
            # Calculate validation-specific stats
            successful_steps = sum(1 for step in context.step_results if step.get('success', False))
            failed_steps = sum(1 for step in context.step_results if not step.get('success', False) and not step.get('skipped', False))
            skipped_steps = sum(1 for step in context.step_results if step.get('skipped', False))
            recovered_steps = sum(1 for step in context.step_results if step.get('recovered', False))
            
            total_verifications = sum(len(step.get('verification_results', [])) for step in context.step_results)
            passed_verifications = sum(
                sum(1 for v in step.get('verification_results', []) if v.get('success', False)) 
                for step in context.step_results
            )
            
            coverage = ((successful_steps + recovered_steps) / len(context.step_results) * 100) if context.step_results else 0
            
            # Store validation metrics in custom_data
            context.custom_data['successful_steps'] = f"{successful_steps}/{len(context.step_results)}"
            context.custom_data['failed_steps'] = str(failed_steps)
            context.custom_data['skipped_steps'] = str(skipped_steps)
            context.custom_data['recovery_navigations'] = str(recovered_steps)
            context.custom_data['verifications'] = f"{passed_verifications}/{total_verifications}"
            context.custom_data['coverage'] = f"{coverage:.1f}%"
            
            # Add failed steps details if any
            failed_step_details = [step for step in context.step_results if not step.get('success', False) and not step.get('skipped', False)]
            if failed_step_details:
                failed_details = []
                for failed_step in failed_step_details:
                    step_num = failed_step.get('step_number')
                    from_node = failed_step.get('from_node')
                    to_node = failed_step.get('to_node')
                    error = failed_step.get('error')
                    if not error:
                        verification_results = failed_step.get('verification_results', [])
                        if verification_results and verification_results[0].get('error'):
                            error = verification_results[0].get('error')
                        else:
                            error = 'Unknown error'
                    failed_details.append(f"Step {step_num}: {from_node} → {to_node} ({error})")
                context.custom_data['failed_steps_details'] = "; ".join(failed_details)
        
        # Use the same cleanup approach as goto_live_fullscreen.py
        executor.cleanup_and_exit(context, args.userinterface_name)


if __name__ == "__main__":
    main() 