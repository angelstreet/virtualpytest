#!/usr/bin/env python3
"""
Validation Script for VirtualPyTest

This script validates all transitions in a navigation tree using navigate_to().

Usage:
    python scripts/validation.py <userinterface_name> [--max-iteration <number>]
    
Example:
    python scripts/validation.py horizon_android_mobile
    python scripts/validation.py horizon_android_mobile --max-iteration 10
"""

import sys
import os
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_args, get_context


def _get_validation_plan(context):
    """Get list of transitions to validate"""
    from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
    
    # Ensure navigation tree is loaded
    if not context.tree_id:
        device = context.selected_device
        args = context.args
        nav_result = device.navigation_executor.load_navigation_tree(
            args.userinterface_name, 
            context.team_id
        )
        if not nav_result['success']:
            print(f"❌ [_get_validation_plan] Navigation tree loading failed")
            return []
        
        context.tree_id = nav_result['tree_id']
        context.tree_data = nav_result
    
    return find_optimal_edge_validation_sequence(context.tree_id, context.team_id)


def capture_validation_summary(context, userinterface_name: str, max_iteration: int = None) -> str:
    """Capture validation summary as text for report - adapted from original comprehensive version"""
    
    # Get basic stats from context
    total_steps = getattr(context, 'validation_total_steps', 0)
    successful_steps = getattr(context, 'validation_successful_steps', 0)
    failed_steps = total_steps - successful_steps if total_steps > 0 else 0
    
    lines = []
    lines.append("-"*60)
    lines.append("🎯 [VALIDATION] EXECUTION SUMMARY")
    lines.append("-"*60)
    
    # Handle case where setup failed and device/host are None
    if context.selected_device:
        lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    else:
        lines.append(f"📱 Device: Setup failed - no device selected")
    
    if context.host:
        lines.append(f"🖥️  Host: {context.host.host_name}")
    else:
        lines.append(f"🖥️  Host: Setup failed - no host available")
    
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    
    # Add max_iteration info if it was used
    if max_iteration is not None:
        lines.append(f"🔢 Max Iteration Limit: {max_iteration} (executed {total_steps} steps)")
    
    lines.append(f"📊 Steps: {successful_steps}/{total_steps} steps successful")
    lines.append(f"✅ Successful: {successful_steps}")
    lines.append(f"❌ Failed: {failed_steps}")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    
    # Calculate coverage safely to avoid division by zero
    if total_steps > 0:
        coverage = (successful_steps / total_steps * 100)
        lines.append(f"🎯 Coverage: {coverage:.1f}%")
    else:
        lines.append(f"🎯 Coverage: 0.0% (no steps executed)")
    
    lines.append(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"\n❌ Error: {context.error_message}")
    
    lines.append("-"*60)
    
    return "\n".join(lines)


def validate_with_recovery(max_iteration: int = None, edges: str = None) -> bool:
    """Execute validation - test all transitions using NavigationExecutor directly"""
    context = get_context()
    
    # Get validation plan
    validation_sequence = _get_validation_plan(context)
    if not validation_sequence:
        context.error_message = "No validation sequence found"
        print(f"❌ [validation] {context.error_message}")
        return False
    
    print(f"✅ [validation] Found {len(validation_sequence)} validation steps")
    
    # Filter by selected edges if provided
    if edges:
        selected_edges = set(edges.split(','))
        original_count = len(validation_sequence)
        validation_sequence = [
            step for step in validation_sequence
            if f"{step.get('from_node')}-{step.get('to_node')}" in selected_edges
        ]
        print(f"🎯 [validation] Filtered to {len(validation_sequence)} selected transitions (from {original_count} total)")
    
    # Apply max_iteration limit
    if max_iteration and max_iteration > 0:
        validation_sequence = validation_sequence[:max_iteration]
        print(f"🔢 [validation] Limited to {max_iteration} steps")
    
    # Execute each transition using navigate_to() (same as goto.py)
    successful = 0
    for i, step in enumerate(validation_sequence):
        target = step.get('to_node_label', 'unknown')
        from_node = step.get('from_node_label', 'unknown')
        
        print(f"⚡ [validation] Step {i+1}/{len(validation_sequence)}: {from_node} → {target}")
        
        # Record step start time
        step_start_time = time.time()
        
        # Use NavigationExecutor directly
        device = context.selected_device
        result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=target,
            team_id=context.team_id,
            context=context
        )
        
        # Calculate step execution time
        step_execution_time = int((time.time() - step_start_time) * 1000)
        
        # Record step result in context for report generation
        step_result = {
            'step_number': i + 1,
            'success': result.get('success', False),
            'from_node': from_node,
            'to_node': target,
            'execution_time_ms': step_execution_time,
            'transitions_executed': result.get('transitions_executed', 0),
            'actions_executed': result.get('actions_executed', 0),
            'total_transitions': result.get('total_transitions', 1),
            'total_actions': result.get('total_actions', 1),
            'step_category': 'validation',
            'error': result.get('error') if not result.get('success', False) else None,
            'screenshots': [],  # Screenshots are handled by NavigationExecutor
            'message': f"Validation step {i+1}: {from_node} → {target}",
            'start_time': step_start_time,
            'end_time': time.time(),
            # Add additional fields that might be used by report formatting
            'from_node_label': from_node,
            'to_node_label': target,
            'fromName': from_node,
            'toName': target
        }
        
        # Record the step in context
        context.record_step_dict(step_result)
        
        if result.get('success', False):
            successful += 1
            print(f"✅ [validation] Step {i+1} successful")
        else:
            print(f"❌ [validation] Step {i+1} failed: {result.get('error', 'Unknown error')}")
    
    # Calculate success and store stats for summary generation
    context.overall_success = successful == len(validation_sequence)
    context.validation_successful_steps = successful
    context.validation_total_steps = len(validation_sequence)
    coverage = (successful / len(validation_sequence) * 100) if validation_sequence else 0
    
    print(f"🎉 [validation] Results: {successful}/{len(validation_sequence)} successful ({coverage:.1f}%)")
    return context.overall_success


@script("validation", "Validate navigation tree transitions")
def main():
    """Main validation function - simple and clean"""
    context = get_context()
    args = get_args()
    
    # Execute validation with selected edges if provided
    result = validate_with_recovery(args.max_iteration, args.edges)
    
    # Always capture summary for report (regardless of success/failure)
    summary_text = capture_validation_summary(context, args.userinterface_name, args.max_iteration)
    context.execution_summary = summary_text
    
    return result


# Define script-specific arguments
main._script_args = [
    '--max-iteration:int:10',
    '--edges:str:None'  # Comma-separated list of edge IDs (from_node-to_node)
]

if __name__ == "__main__":
    main()
