#!/usr/bin/env python3
"""
KPI Measurement Script for VirtualPyTest

This script measures KPIs for a specific edge transition by repeatedly navigating it.
It provides min, max, and average performance metrics.

Usage:
    python test_scripts/kpi_measurement.py <userinterface_name> --edge <from>:<to> --iterations <count>
    
Examples:
    python test_scripts/kpi_measurement.py horizon_android_mobile --edge home:live --iterations 5
    python test_scripts/kpi_measurement.py horizon_android_tv --edge live:settings --iterations 10
"""

import sys
import os
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device


def _get_available_edges(context):
    """Get list of all available edges from navigation tree"""
    from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
    from shared.src.lib.supabase.userinterface_db import get_userinterface_by_name
    from shared.src.lib.supabase.navigation_trees_db import get_root_tree_for_interface
    
    # Ensure we have tree_id
    if not context.tree_id:
        device = context.selected_device
        args = context.args
        
        # Get tree_id without loading full tree (lightweight DB query)
        userinterface = get_userinterface_by_name(args.userinterface_name, context.team_id)
        if not userinterface:
            print(f"❌ [_get_available_edges] User interface '{args.userinterface_name}' not found")
            return []
        
        root_tree = get_root_tree_for_interface(userinterface['id'], context.team_id)
        if not root_tree:
            print(f"❌ [_get_available_edges] No root tree found for interface '{args.userinterface_name}'")
            return []
        
        context.tree_id = root_tree['id']
        print(f"✅ [_get_available_edges] Found tree_id: {context.tree_id}")
        
        # Load navigation tree to populate cache
        nav_result = device.navigation_executor.load_navigation_tree(
            args.userinterface_name, 
            context.team_id
        )
        if not nav_result['success']:
            print(f"❌ [_get_available_edges] Navigation tree loading failed")
            return []
        
        context.tree_data = nav_result
    
    return find_optimal_edge_validation_sequence(context.tree_id, context.team_id)


def capture_kpi_summary(context, userinterface_name: str, edge_str: str, iterations: int, kpi_results: list) -> str:
    """Capture KPI measurement summary as text for report"""
    lines = []
    lines.append("="*60)
    lines.append("📊 [KPI MEASUREMENT] EXECUTION SUMMARY")
    lines.append("="*60)
    
    # Device and host info
    if context.selected_device:
        lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    else:
        lines.append(f"📱 Device: Setup failed - no device selected")
    
    if context.host:
        lines.append(f"🖥️  Host: {context.host.host_name}")
    else:
        lines.append(f"🖥️  Host: Setup failed - no host available")
    
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"🔗 Edge: {edge_str}")
    lines.append(f"🔢 Iterations: {iterations}")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append("")
    
    # Calculate KPI statistics
    if kpi_results:
        successful_results = [r for r in kpi_results if r['success']]
        failed_results = [r for r in kpi_results if not r['success']]
        
        lines.append("📈 KPI STATISTICS:")
        lines.append(f"✅ Successful: {len(successful_results)}/{len(kpi_results)}")
        lines.append(f"❌ Failed: {len(failed_results)}/{len(kpi_results)}")
        
        if successful_results:
            durations = [r['duration'] for r in successful_results]
            min_duration = min(durations)
            max_duration = max(durations)
            avg_duration = sum(durations) / len(durations)
            
            lines.append("")
            lines.append("⏱️  TIMING METRICS (successful iterations only):")
            lines.append(f"   Min: {min_duration:.2f}s")
            lines.append(f"   Max: {max_duration:.2f}s")
            lines.append(f"   Avg: {avg_duration:.2f}s")
        
        # Per-iteration breakdown
        lines.append("")
        lines.append("📋 PER-ITERATION RESULTS:")
        for i, result in enumerate(kpi_results, 1):
            status = "✅" if result['success'] else "❌"
            if result['success']:
                lines.append(f"   Iteration {i}: {status} {result['duration']:.2f}s")
            else:
                lines.append(f"   Iteration {i}: {status} Failed - {result.get('error', 'Unknown error')}")
    else:
        lines.append("⚠️  No KPI results collected")
    
    lines.append("")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    lines.append(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"\n❌ Error: {context.error_message}")
    
    lines.append("="*60)
    
    return "\n".join(lines)


@script("kpi_measurement", "Measure KPIs for specific navigation edge")
def main():
    """Main KPI measurement function"""
    args = get_args()
    context = get_context()
    device = get_device()
    
    print(f"📊 [kpi_measurement] Starting KPI measurement")
    print(f"📱 [kpi_measurement] Device: {device.device_name} ({device.device_model})")
    print(f"🔗 [kpi_measurement] Edge: {args.edge}")
    print(f"🔢 [kpi_measurement] Iterations: {args.iterations}")
    
    # Get available edges
    print(f"📥 [kpi_measurement] Loading available edges...")
    edges = _get_available_edges(context)
    if not edges:
        context.error_message = "No edges found in navigation tree"
        return False
    
    print(f"✅ [kpi_measurement] Found {len(edges)} edges")
    
    # Parse edge argument (format: from_label:to_label)
    if ':' not in args.edge:
        context.error_message = f"Invalid edge format. Expected 'from:to', got '{args.edge}'"
        return False
    
    from_label, to_label = args.edge.split(':', 1)
    print(f"🔍 [kpi_measurement] Looking for edge: {from_label} → {to_label}")
    
    # Find matching edge
    selected_edge = None
    for edge in edges:
        if edge.get('from_node_label') == from_label and edge.get('to_node_label') == to_label:
            selected_edge = edge
            break
    
    if not selected_edge:
        # Show available edges for debugging
        available_edges_str = ", ".join([f"{e.get('from_node_label')}:{e.get('to_node_label')}" for e in edges[:10]])
        context.error_message = f"Edge '{args.edge}' not found. Available edges (first 10): {available_edges_str}"
        return False
    
    print(f"✅ [kpi_measurement] Found edge: {from_label} → {to_label}")
    
    # Execute KPI measurement loop
    kpi_results = []
    
    for i in range(args.iterations):
        print(f"\n{'='*60}")
        print(f"🔄 [kpi_measurement] Iteration {i+1}/{args.iterations}")
        print(f"{'='*60}")
        
        iteration_result = {
            'iteration': i + 1,
            'success': False,
            'duration': 0,
            'error': None
        }
        
        # Step 1: Navigate to FROM node (starting position)
        print(f"📍 [kpi_measurement] Step 1: Going to starting position '{from_label}'")
        from_result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=from_label,
            team_id=context.team_id,
            context=context
        )
        
        if not from_result.get('success', False):
            print(f"❌ [kpi_measurement] Failed to reach starting position: {from_result.get('error', 'Unknown error')}")
            iteration_result['error'] = f"Failed to reach {from_label}: {from_result.get('error', 'Unknown error')}"
            kpi_results.append(iteration_result)
            continue
        
        print(f"✅ [kpi_measurement] Reached starting position '{from_label}'")
        
        # Step 2: Navigate to TO node (measure this!)
        print(f"⏱️  [kpi_measurement] Step 2: Measuring transition to '{to_label}'")
        start_time = time.time()
        
        to_result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=to_label,
            team_id=context.team_id,
            context=context
        )
        
        duration = time.time() - start_time
        iteration_result['duration'] = duration
        
        if to_result.get('success', False):
            iteration_result['success'] = True
            print(f"✅ [kpi_measurement] Iteration {i+1} SUCCESS - Duration: {duration:.2f}s")
        else:
            iteration_result['error'] = to_result.get('error', 'Unknown error')
            print(f"❌ [kpi_measurement] Iteration {i+1} FAILED - Error: {iteration_result['error']}")
        
        kpi_results.append(iteration_result)
    
    # Calculate overall success
    successful_count = sum(1 for r in kpi_results if r['success'])
    context.overall_success = successful_count == args.iterations
    
    print(f"\n{'='*60}")
    print(f"🎉 [kpi_measurement] Completed {args.iterations} iterations")
    print(f"📊 [kpi_measurement] Results: {successful_count}/{args.iterations} successful")
    print(f"{'='*60}")
    
    # Always capture summary for report
    summary_text = capture_kpi_summary(context, args.userinterface_name, args.edge, args.iterations, kpi_results)
    context.execution_summary = summary_text
    
    return context.overall_success


# Define script-specific arguments
main._script_args = [
    '--edge:str:home:live',  # Default edge for testing
    '--iterations:int:3'      # Default 3 iterations
]

if __name__ == "__main__":
    main()

