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
        lines.append(f"🔢 Max Iteration Limit: {max_iteration} (validated {validation_total} transitions, executed {detailed_steps} total steps)")
    else:
        lines.append(f"🔢 Validated {validation_total} transitions (executed {detailed_steps} total steps)")
    
    # Note about recovery steps if more steps than transitions
    if detailed_steps > validation_total:
        recovery_steps = detailed_steps - validation_total
        lines.append(f"🔄 Recovery: {recovery_steps} navigation step(s) used for recovery")
    
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
    
    # Execute each edge transition directly (without pathfinding)
    # This ensures 29 validation transitions = 29 steps in report
    successful = 0
    device = context.selected_device
    
    for i, step in enumerate(validation_sequence):
        from_node = step.get('from_node_label', 'unknown')
        to_node = step.get('to_node_label', 'unknown')
        from_node_id = step.get('from_node_id', 'unknown')
        to_node_id = step.get('to_node_id', 'unknown')
        
        print(f"⚡ [validation] Step {i+1}/{len(validation_sequence)}: {from_node} → {to_node}")
        
        # RECOVERY MECHANISM: Check if we're at the expected starting position
        current_position = device.navigation_executor.get_current_position(context.tree_id)
        if current_position and current_position != from_node_id:
            print(f"🔄 [validation] Recovery needed: current position '{current_position}' != expected '{from_node_id}'")
            print(f"🔄 [validation] Navigating from '{current_position}' to '{from_node}' before executing edge")
            
            # Use execute_navigation to recover position (will record recovery steps)
            recovery_result = device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                target_node_id=from_node_id,
                team_id=context.team_id,
                context=context
            )
            
            if not recovery_result.get('success', False):
                print(f"❌ [validation] Recovery navigation failed - skipping step {i+1}")
                # Record failed step due to recovery failure
                step_result = {
                    'success': False,
                    'message': f"{from_node} → {to_node}",
                    'error': f"Recovery navigation failed: {recovery_result.get('error', 'Unknown error')}",
                    'execution_time_ms': 0,
                    'step_category': 'validation'
                }
                context.record_step_immediately(step_result)
                continue
            
            print(f"✅ [validation] Recovery successful - now at '{from_node}'")
        elif not current_position:
            print(f"⚠️  [validation] No current position tracked - assuming at correct position")
        else:
            print(f"✓ [validation] Already at starting position '{from_node}'")
        
        # Record step start time and capture start screenshot
        step_start_time = time.time()
        from datetime import datetime
        step_start_timestamp = datetime.fromtimestamp(step_start_time).strftime('%H:%M:%S')
        
        from shared.src.lib.utils.device_utils import capture_screenshot_for_script
        step_start_screenshot_path = ""
        screenshot_id = capture_screenshot_for_script(device, context, f"step_{i+1}_start")
        if screenshot_id and context.screenshot_paths:
            step_start_screenshot_path = context.screenshot_paths[-1]
            print(f"📸 [validation] Step-start screenshot captured: {screenshot_id}")
        
        # Set edge context for action executor (for KPI tracking)
        device.action_executor.tree_id = context.tree_id
        device.action_executor.edge_id = step.get('edge_id')
        device.action_executor.action_set_id = step.get('action_set_id')
        
        # Execute the edge's actions directly
        actions = step.get('actions', [])
        retry_actions = step.get('retryActions', [])
        failure_actions = step.get('failureActions', [])
        
        action_result = device.action_executor.execute_actions(
            actions=actions,
            retry_actions=retry_actions,
            failure_actions=failure_actions,
            team_id=context.team_id,
            context=context
        )
        
        # Execute verifications on the target node
        verification_result = device.verification_executor.verify_node(
            node_id=to_node_id,
            team_id=context.team_id,
            tree_id=context.tree_id
        )
        
        # Capture end screenshot
        step_end_screenshot_path = ""
        screenshot_id = capture_screenshot_for_script(device, context, f"step_{i+1}_end")
        if screenshot_id and context.screenshot_paths:
            step_end_screenshot_path = context.screenshot_paths[-1]
            print(f"📸 [validation] Step-end screenshot captured: {screenshot_id}")
        
        # Calculate execution time
        step_execution_time = int((time.time() - step_start_time) * 1000)
        step_end_timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Determine overall success for this step
        actions_succeeded = action_result.get('success', False) and action_result.get('main_actions_succeeded', False)
        verifications_succeeded = verification_result.get('success', False)
        has_verifications = verification_result.get('has_verifications', True)
        
        # Step succeeds if actions pass AND (verifications pass OR no verifications defined)
        step_success = actions_succeeded and (verifications_succeeded or not has_verifications)
        
        # Extract action name for labeling
        action_name = "validation_edge"
        if actions and len(actions) > 0:
            first_action = actions[0]
            if isinstance(first_action, dict) and first_action.get('command'):
                action_name = first_action.get('command')
        
        # Record the step result (exactly one step per validation transition)
        step_result = {
            'success': step_success,
            'screenshot_path': step_end_screenshot_path,
            'step_start_screenshot_path': step_start_screenshot_path,
            'step_end_screenshot_path': step_end_screenshot_path,
            'message': f"{from_node} → {to_node}",
            'execution_time_ms': step_execution_time,
            'start_time': step_start_timestamp,
            'end_time': step_end_timestamp,
            'from_node': from_node,
            'to_node': to_node,
            'action_name': action_name,
            'actions': actions,
            'retry_actions': retry_actions,
            'failure_actions': failure_actions,
            'action_results': action_result.get('results', []),
            'action_screenshots': action_result.get('action_screenshots', []),
            'verifications': step.get('verifications', []),
            'verification_results': verification_result.get('results', []),
            'error': action_result.get('error') if not actions_succeeded else (verification_result.get('error') if not verifications_succeeded else None),
            'step_category': 'validation'
        }
        
        # Record step to context
        context.record_step_immediately(step_result)
        
        # Update navigation position if step succeeded
        if step_success:
            device.navigation_executor.update_current_position(to_node_id, context.tree_id, to_node)
            successful += 1
            print(f"✅ [validation] Step {i+1} successful")
        else:
            error_msg = step_result.get('error', 'Unknown error')
            print(f"❌ [validation] Step {i+1} failed: {error_msg}")
    
    # Store validation-level stats for summary generation
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
    '--max-iteration:int:0',  # 0 = no limit, validate all transitions
    '--edges:str:'  # Comma-separated list of edge IDs (from_node-to_node), default: empty (validate all)
]

if __name__ == "__main__":
    main()
