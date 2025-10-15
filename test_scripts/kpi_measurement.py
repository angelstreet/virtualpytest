#!/usr/bin/env python3
"""
KPI Measurement Script for VirtualPyTest

This script measures KPIs for navigation between two nodes by repeatedly navigating between them.
It provides min, max, and average performance metrics.

Usage:
    python test_scripts/kpi_measurement.py <userinterface_name> --from-node <source> --to-node <target> [--iterations <count>]
    
Examples:
    python test_scripts/kpi_measurement.py horizon_android_mobile --from-node home --to-node live --iterations 5
    python test_scripts/kpi_measurement.py horizon_android_tv --from-node settings --to-node home --iterations 10
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


# Script arguments - defined early for backend parameter detection (must be within first 300 lines)
# NOTE: Framework params (userinterface_name, --host, --device) are automatic - don't declare them!
_script_args = [
    '--from-node:str:home',      # Script-specific param - Source node
    '--to-node:str:live',        # Script-specific param - Target node
    '--iterations:int:3'         # Script-specific param - Number of iterations
]


def capture_kpi_summary(context, userinterface_name: str, from_node: str, to_node: str, iterations: int, kpi_results: list) -> str:
    """Capture KPI measurement summary as text for report"""
    lines = []
    lines.append("="*60)
    lines.append("📊 [KPI MEASUREMENT] EXECUTION SUMMARY")
    lines.append("="*60)
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"📍 Transition: {from_node} → {to_node}")
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


@script("kpi_measurement", "Measure KPIs for navigation between two nodes")
def main():
    """Main KPI measurement function - uses same navigation as goto.py"""
    args = get_args()
    context = get_context()
    device = get_device()
    from_node = args.from_node
    to_node = args.to_node
    
    print(f"📊 [kpi_measurement] Starting KPI measurement")
    print(f"📱 [kpi_measurement] Device: {device.device_name} ({device.device_model})")
    print(f"📍 [kpi_measurement] Measuring: {from_node} → {to_node}")
    print(f"🔢 [kpi_measurement] Iterations: {args.iterations}")
    
    # Load navigation tree (same as goto.py)
    nav_result = device.navigation_executor.load_navigation_tree(
        args.userinterface_name, 
        context.team_id
    )
    if not nav_result['success']:
        context.error_message = f"Navigation tree loading failed: {nav_result.get('error', 'Unknown error')}"
        return False
    
    context.tree_id = nav_result['tree_id']
    print(f"✅ [kpi_measurement] Navigation tree loaded (tree_id: {context.tree_id})")
    
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
        
        # Step 1: Navigate to FROM node (starting position) - same as goto.py
        print(f"📍 [kpi_measurement] Step 1: Going to starting position '{from_node}'")
        from_result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=from_node,  # Use label, not ID (same as goto.py)
            team_id=context.team_id,
            context=context
        )
        
        if not from_result.get('success', False):
            error_msg = from_result.get('error', 'Unknown error')
            print(f"❌ [kpi_measurement] Failed to reach starting position: {error_msg}")
            iteration_result['error'] = f"Failed to reach {from_node}: {error_msg}"
            kpi_results.append(iteration_result)
            continue
        
        print(f"✅ [kpi_measurement] Reached starting position '{from_node}'")
        
        # Step 2: Navigate to TO node (measure this!) - same as goto.py
        print(f"⏱️  [kpi_measurement] Step 2: Measuring transition to '{to_node}'")
        start_time = time.time()
        
        to_result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=to_node,  # Use label, not ID (same as goto.py)
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
    summary_text = capture_kpi_summary(
        context, 
        args.userinterface_name, 
        from_node, 
        to_node, 
        args.iterations, 
        kpi_results
    )
    context.execution_summary = summary_text
    
    return context.overall_success


# Assign script args to main function
main._script_args = _script_args

if __name__ == "__main__":
    main()
