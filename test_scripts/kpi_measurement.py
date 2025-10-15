#!/usr/bin/env python3
"""
KPI Measurement Script for VirtualPyTest

This script measures KPIs for a specific edge transition by repeatedly navigating it.
Uses edge_id selection to ensure DIRECT navigation transition between two nodes.
KPI measurements are post-processed by kpi_executor service and fetched from DB.

Workflow:
1. Select edge (by UUID) to get source and target nodes
2. Navigate in loop: goto(source) → goto(target) (like goto.py)
3. Wait 10 seconds for kpi_executor post-processing
4. Fetch KPI measurements from database
5. Display min/max/avg statistics

Usage:
    python test_scripts/kpi_measurement.py <userinterface_name> --edge-id <edge_uuid> [--iterations <count>]
    
Examples:
    python test_scripts/kpi_measurement.py horizon_android_mobile --edge-id abc123... --iterations 5
    python test_scripts/kpi_measurement.py horizon_android_tv --edge-id def456... --iterations 10
"""

import sys
import os
import time
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device


# Script arguments - defined early for backend parameter detection (must be within first 300 lines)
# NOTE: Framework params (userinterface_name, --host, --device) are automatic - don't declare them!
_script_args = [
    '--edge-id:str:',            # Script-specific param - Edge ID (UUID)
    '--iterations:int:3'         # Script-specific param - Number of iterations
]


def _get_available_edges(context):
    """Get list of all available edges from navigation tree"""
    from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
    from shared.src.lib.supabase.userinterface_db import get_userinterface_by_name
    from shared.src.lib.supabase.navigation_trees_db import get_root_tree_for_interface
    
    device = context.selected_device
    args = context.args
    
    # Get tree_id
    userinterface = get_userinterface_by_name(args.userinterface_name, context.team_id)
    if not userinterface:
        print(f"❌ User interface '{args.userinterface_name}' not found")
        return []
    
    root_tree = get_root_tree_for_interface(userinterface['id'], context.team_id)
    if not root_tree:
        print(f"❌ No root tree found for interface '{args.userinterface_name}'")
        return []
    
    context.tree_id = root_tree['id']
    
    # Load navigation tree to populate cache
    nav_result = device.navigation_executor.load_navigation_tree(
        args.userinterface_name, 
        context.team_id
    )
    if not nav_result['success']:
        print(f"❌ Navigation tree loading failed")
        return []
    
    return find_optimal_edge_validation_sequence(context.tree_id, context.team_id)


def _fetch_kpi_results_from_db(device_id: str, team_id: str, start_time: datetime, end_time: datetime):
    """Fetch KPI measurements from execution_results table"""
    from shared.src.lib.utils.supabase_utils import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("❌ [_fetch_kpi_results] Supabase client not available")
            return []
        
        # Query execution_results for KPI measurements in time range
        result = supabase.table('execution_results').select(
            'kpi_measurement_ms, kpi_measurement_success, kpi_measurement_error, executed_at, from_node_label, to_node_label'
        ).eq('team_id', team_id).eq('device_id', device_id).gte(
            'executed_at', start_time.isoformat()
        ).lte(
            'executed_at', end_time.isoformat()
        ).not_.is_('kpi_measurement_ms', 'null').order('executed_at', desc=False).execute()
        
        print(f"✅ [_fetch_kpi_results] Found {len(result.data)} KPI measurements from DB")
        return result.data
        
    except Exception as e:
        print(f"❌ [_fetch_kpi_results] Error fetching KPI results: {e}")
        return []


def capture_kpi_summary(context, userinterface_name: str, edge_label: str, from_label: str, to_label: str, iterations: int, kpi_db_results: list) -> str:
    """Capture KPI measurement summary as text for report"""
    lines = []
    lines.append("="*60)
    lines.append("📊 [KPI MEASUREMENT] EXECUTION SUMMARY")
    lines.append("="*60)
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"🎯 Edge: {edge_label}")
    lines.append(f"📍 Transition: {from_label} → {to_label}")
    lines.append(f"🔢 Requested Iterations: {iterations}")
    lines.append(f"⏱️  Total Script Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append("")
    
    # Calculate KPI statistics from DB results
    if kpi_db_results:
        successful_results = [r for r in kpi_db_results if r.get('kpi_measurement_success')]
        failed_results = [r for r in kpi_db_results if not r.get('kpi_measurement_success')]
        
        lines.append("📈 KPI STATISTICS (FROM DATABASE):")
        lines.append(f"✅ Successful: {len(successful_results)}/{len(kpi_db_results)}")
        lines.append(f"❌ Failed: {len(failed_results)}/{len(kpi_db_results)}")
        
        if successful_results:
            durations_ms = [r['kpi_measurement_ms'] for r in successful_results]
            min_duration = min(durations_ms)
            max_duration = max(durations_ms)
            avg_duration = sum(durations_ms) / len(durations_ms)
            
            lines.append("")
            lines.append("⏱️  TIMING METRICS (successful measurements only):")
            lines.append(f"   Min: {min_duration}ms ({min_duration/1000:.2f}s)")
            lines.append(f"   Max: {max_duration}ms ({max_duration/1000:.2f}s)")
            lines.append(f"   Avg: {avg_duration:.0f}ms ({avg_duration/1000:.2f}s)")
        
        # Per-iteration breakdown
        lines.append("")
        lines.append("📋 PER-ITERATION RESULTS:")
        for i, result in enumerate(kpi_db_results, 1):
            status = "✅" if result.get('kpi_measurement_success') else "❌"
            if result.get('kpi_measurement_success'):
                kpi_ms = result.get('kpi_measurement_ms')
                lines.append(f"   Iteration {i}: {status} {kpi_ms}ms ({kpi_ms/1000:.2f}s)")
            else:
                error = result.get('kpi_measurement_error', 'Unknown error')
                lines.append(f"   Iteration {i}: {status} Failed - {error}")
    else:
        lines.append("⚠️  No KPI measurements found in database")
        lines.append("   (Post-processing may still be in progress)")
    
    lines.append("")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    lines.append(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"\n❌ Error: {context.error_message}")
    
    lines.append("="*60)
    
    return "\n".join(lines)


@script("kpi_measurement", "Measure KPIs for specific navigation edge")
def main():
    """Main KPI measurement function - simple navigation + DB fetch"""
    args = get_args()
    context = get_context()
    device = get_device()
    
    print(f"📊 [kpi_measurement] Starting KPI measurement")
    print(f"📱 [kpi_measurement] Device: {device.device_name} ({device.device_model})")
    print(f"🔗 [kpi_measurement] Edge ID: {args.edge_id}")
    print(f"🔢 [kpi_measurement] Iterations: {args.iterations}")
    
    # Record script start time for DB query
    script_start_time = datetime.now()
    
    # Get available edges
    print(f"📥 [kpi_measurement] Loading available edges...")
    edges = _get_available_edges(context)
    if not edges:
        context.error_message = "No edges found in navigation tree"
        return False
    
    print(f"✅ [kpi_measurement] Found {len(edges)} edges in validation sequence")
    
    # Build edge map by edge_id
    edge_map = {}
    for edge in edges:
        edge_id = edge.get('edge_id')
        if edge_id:
            edge_map[edge_id] = edge
    
    # Find selected edge by ID
    if args.edge_id not in edge_map:
        available_edges = [f"{e.get('from_node_label')} → {e.get('to_node_label')}" for e in list(edge_map.values())[:10]]
        context.error_message = f"Edge ID '{args.edge_id}' not found. Available edges: {', '.join(available_edges)}"
        return False
    
    selected_edge = edge_map[args.edge_id]
    from_label = selected_edge['from_node_label']
    to_label = selected_edge['to_node_label']
    edge_label = f"{from_label} → {to_label}"
    
    print(f"✅ [kpi_measurement] Selected edge: '{edge_label}'")
    print(f"📍 [kpi_measurement] Transition: {from_label} → {to_label}")
    
    # Execute navigation loop (simple, like goto.py)
    navigation_success_count = 0
    
    for i in range(args.iterations):
        print(f"\n{'='*60}")
        print(f"🔄 [kpi_measurement] Iteration {i+1}/{args.iterations}")
        print(f"{'='*60}")
        
        # Step 1: Navigate to FROM node (like goto.py)
        print(f"📍 [kpi_measurement] Going to '{from_label}'")
        from_result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=from_label,
            team_id=context.team_id,
            context=context
        )
        
        if not from_result.get('success', False):
            print(f"❌ [kpi_measurement] Failed to reach '{from_label}'")
            continue
        
        print(f"✅ [kpi_measurement] Reached '{from_label}'")
        
        # Step 2: Navigate to TO node (like goto.py) - KPI measured automatically
        print(f"⏱️  [kpi_measurement] Navigating to '{to_label}' (KPI will be measured)")
        to_result = device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=to_label,
            team_id=context.team_id,
            context=context
        )
        
        if to_result.get('success', False):
            navigation_success_count += 1
            print(f"✅ [kpi_measurement] Iteration {i+1} navigation SUCCESS")
        else:
            print(f"❌ [kpi_measurement] Iteration {i+1} navigation FAILED")
    
    print(f"\n{'='*60}")
    print(f"🎉 [kpi_measurement] Completed {args.iterations} iterations")
    print(f"📊 [kpi_measurement] Navigation success: {navigation_success_count}/{args.iterations}")
    print(f"{'='*60}")
    
    # Wait for post-processing to complete
    print(f"\n⏳ [kpi_measurement] Waiting 10 seconds for KPI post-processing...")
    time.sleep(10)
    
    # Fetch KPI results from database
    script_end_time = datetime.now()
    print(f"📥 [kpi_measurement] Fetching KPI results from database...")
    print(f"   Time range: {script_start_time.isoformat()} to {script_end_time.isoformat()}")
    
    kpi_db_results = _fetch_kpi_results_from_db(
        device_id=device.device_id,
        team_id=context.team_id,
        start_time=script_start_time,
        end_time=script_end_time
    )
    
    # Calculate overall success
    successful_kpis = sum(1 for r in kpi_db_results if r.get('kpi_measurement_success'))
    context.overall_success = successful_kpis == args.iterations
    
    print(f"📊 [kpi_measurement] KPI Results: {successful_kpis}/{len(kpi_db_results)} successful")
    
    # Always capture summary for report
    summary_text = capture_kpi_summary(
        context, 
        args.userinterface_name, 
        edge_label,
        from_label, 
        to_label, 
        args.iterations, 
        kpi_db_results
    )
    context.execution_summary = summary_text
    
    return context.overall_success


# Assign script args to main function
main._script_args = _script_args

if __name__ == "__main__":
    main()
