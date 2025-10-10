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
    """Get list of transitions to validate - optimized to use cache"""
    from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
    from backend_host.src.lib.utils.navigation_cache import get_cached_unified_graph
    from shared.src.lib.supabase.userinterface_db import get_userinterface_by_name
    from shared.src.lib.supabase.navigation_trees_db import get_root_tree_for_interface
    
    # Ensure we have tree_id
    if not context.tree_id:
        device = context.selected_device
        args = context.args
        
        # OPTIMIZATION: Get tree_id without loading full tree (lightweight DB query)
        userinterface = get_userinterface_by_name(args.userinterface_name, context.team_id)
        if not userinterface:
            print(f"❌ [_get_validation_plan] User interface '{args.userinterface_name}' not found")
            return []
        
        root_tree = get_root_tree_for_interface(userinterface['id'], context.team_id)
        if not root_tree:
            print(f"❌ [_get_validation_plan] No root tree found for interface '{args.userinterface_name}'")
            return []
        
        context.tree_id = root_tree['id']
        print(f"✅ [_get_validation_plan] Found tree_id: {context.tree_id}")
        
        # Check if cache exists
        cached_graph = get_cached_unified_graph(context.tree_id, context.team_id)
        
        if cached_graph:
            print(f"🚀 [_get_validation_plan] Using cached graph: {len(cached_graph.nodes)} nodes, {len(cached_graph.edges)} edges (FAST PATH)")
        else:
            # Cache miss - load tree and populate cache
            print(f"📥 [_get_validation_plan] Cache miss - loading tree from database (SLOW PATH)")
            nav_result = device.navigation_executor.load_navigation_tree(
                args.userinterface_name, 
                context.team_id
            )
            if not nav_result['success']:
                print(f"❌ [_get_validation_plan] Navigation tree loading failed")
                return []
            
            context.tree_data = nav_result
    
    return find_optimal_edge_validation_sequence(context.tree_id, context.team_id)


def capture_validation_summary(context, userinterface_name: str, max_iteration: int = None) -> str:
    """Capture validation summary as text for report - uses validation-level stats"""
    
    # Use validation-level stats (high-level transitions tested)
    validation_total = getattr(context, 'validation_total_steps', 0)
    validation_successful = getattr(context, 'validation_successful_steps', 0)
    validation_failed = validation_total - validation_successful
    
    # Detailed steps count (for reference - includes all navigation sub-steps)
    detailed_steps = len(context.step_results)
    
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
    
    # Show validation iterations and actual navigation steps executed
    if max_iteration is not None:
        lines.append(f"🔢 Max Iteration Limit: {max_iteration} (validated {validation_total} transitions, executed {detailed_steps} navigation steps)")
    else:
        lines.append(f"🔢 Validated {validation_total} transitions (executed {detailed_steps} navigation steps)")
    
    lines.append(f"📊 Steps: {validation_successful}/{validation_total} steps successful")
    lines.append(f"✅ Successful: {validation_successful}")
    lines.append(f"❌ Failed: {validation_failed}")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    
    # Calculate coverage based on validation transitions
    if validation_total > 0:
        coverage = (validation_successful / validation_total * 100)
        lines.append(f"🎯 Coverage: {coverage:.1f}%")
    else:
        lines.append(f"🎯 Coverage: 0.0% (no validation steps)")
    
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
    
    # Filter by selected edges if provided (skip if None or empty string)
    if edges and edges.strip():
        selected_edges = set(edges.split(','))
        original_count = len(validation_sequence)
        
        # Debug: Show what we're comparing
        print(f"🔍 [validation] DEBUG: Received {len(selected_edges)} selected edge IDs")
        if len(selected_edges) > 0:
            sample_selected = list(selected_edges)[:2]
            print(f"🔍 [validation] DEBUG: Sample selected edges: {sample_selected}")
        
        if len(validation_sequence) > 0:
            sample_step = validation_sequence[0]
            constructed_id = f"{sample_step.get('from_node_id')}-{sample_step.get('to_node_id')}"
            print(f"🔍 [validation] DEBUG: Sample step edge ID format: {constructed_id}")
        
        validation_sequence = [
            step for step in validation_sequence
            if f"{step.get('from_node_id')}-{step.get('to_node_id')}" in selected_edges
        ]
        print(f"🎯 [validation] Filtered to {len(validation_sequence)} selected transitions (from {original_count} total)")
    
    # Apply max_iteration limit
    if max_iteration and max_iteration > 0:
        validation_sequence = validation_sequence[:max_iteration]
        print(f"🔢 [validation] Limited to {max_iteration} steps")
    
    # Track validation-level results separately (don't interfere with detailed step recording)
    validation_results = []
    
    # Execute each transition using navigate_to() (NavigationExecutor records detailed steps)
    successful = 0
    for i, step in enumerate(validation_sequence):
        target = step.get('to_node_label', 'unknown')
        from_node = step.get('from_node_label', 'unknown')
        
        print(f"⚡ [validation] Step {i+1}/{len(validation_sequence)}: {from_node} → {target}")
        
        # Record step start time
        step_start_time = time.time()
        
        # Use NavigationExecutor directly (it will record detailed steps automatically)
        device = context.selected_device
        result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=target,
            team_id=context.team_id,
            context=context
        )
        
        # Track validation-level result (separate from detailed steps)
        validation_result = {
            'validation_step': i + 1,
            'from_node': from_node,
            'to_node': target,
            'success': result.get('success', False),
            'error': result.get('error', ''),
            'duration_ms': int((time.time() - step_start_time) * 1000)
        }
        validation_results.append(validation_result)
        
        if result.get('success', False):
            successful += 1
            print(f"✅ [validation] Step {i+1} successful")
        else:
            print(f"❌ [validation] Step {i+1} failed: {result.get('error', 'Unknown error')}")
    
    # Store validation-level stats for summary generation (separate from step-level details)
    context.overall_success = successful == len(validation_sequence)
    context.validation_results = validation_results  # Store validation-level results
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
    '--max-iteration:int:0',  # 0 = no limit, validate all transitions
    '--edges:str:'  # Comma-separated list of edge IDs (from_node-to_node), default: empty (validate all)
]

if __name__ == "__main__":
    main()
