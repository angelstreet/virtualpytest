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


def validate_with_recovery(max_iteration: int = None) -> bool:
    """Execute validation - test all transitions using NavigationExecutor directly"""
    context = get_context()
    
    # Get validation plan
    validation_sequence = _get_validation_plan(context)
    if not validation_sequence:
        context.error_message = "No validation sequence found"
        print(f"❌ [validation] {context.error_message}")
        return False
    
    print(f"✅ [validation] Found {len(validation_sequence)} validation steps")
    
    # Apply max_iteration limit
    if max_iteration and max_iteration > 0:
        validation_sequence = validation_sequence[:max_iteration]
        print(f"🔢 [validation] Limited to {max_iteration} steps")
    
    # Execute each transition using navigate_to() (same as goto.py)
    successful = 0
    for i, step in enumerate(validation_sequence):
        target = step.get('to_node_label', 'unknown')
        print(f"⚡ [validation] Step {i+1}/{len(validation_sequence)}: → {target}")
        
        # Use NavigationExecutor directly
        device = context.selected_device
        result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=target,
            team_id=context.team_id,
            context=context
        )
        
        if result.get('success', False):
            successful += 1
            print(f"✅ [validation] Step {i+1} successful")
        else:
            print(f"❌ [validation] Step {i+1} failed: {result.get('error', 'Unknown error')}")
    
    # Calculate success
    context.overall_success = successful == len(validation_sequence)
    coverage = (successful / len(validation_sequence) * 100) if validation_sequence else 0
    
    print(f"🎉 [validation] Results: {successful}/{len(validation_sequence)} successful ({coverage:.1f}%)")
    return context.overall_success


@script("validation", "Validate navigation tree transitions")
def main():
    """Main validation function - simple and clean"""
    args = get_args()
    return validate_with_recovery(args.max_iteration)


# Define script-specific arguments
main._script_args = ['--max-iteration:int:10']

if __name__ == "__main__":
    main()
