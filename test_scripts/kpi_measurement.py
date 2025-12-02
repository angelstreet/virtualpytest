#!/usr/bin/env python3
"""
KPI Measurement Script for VirtualPyTest

This script measures KPIs for a specific edge transition by repeatedly navigating it.
Uses action_set label selection to ensure DIRECT navigation transition.
KPI measurements are post-processed by kpi_executor service and fetched from DB.

Workflow:
1. Frontend: User selects action_set from dropdown (e.g., "live → live_fullscreen")
2. Frontend: Sends edge parameter with action_set label
3. Script: Maps action_set label to correct from/to nodes (handles forward/backward)
4. Script: Navigate in loop: goto(from) → goto(to) (like goto.py)
5. Script: Wait 10 seconds for kpi_executor post-processing
6. Script: Fetch KPI measurements from database
7. Script: Display min/max/avg statistics

Usage:
    python test_scripts/kpi_measurement.py <userinterface_name> --edge <action_set_label> [--iterations <count>]
    
Examples:
    python test_scripts/kpi_measurement.py horizon_android_mobile --edge "live → live_fullscreen" --iterations 5
    python test_scripts/kpi_measurement.py horizon_android_tv --edge "settings → home" --iterations 10
"""

import sys
import os
import time
from datetime import datetime, timezone

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device


# Script arguments - defined early for backend parameter detection (must be within first 300 lines)
# Script arguments (framework params have defaults, script params are specific)
_script_args = [
    '--userinterface:str:horizon_android_mobile',  # Framework param with default
    '--edge:str:',                                 # Script-specific param
    '--iterations:int:3'                           # Script-specific param
]


def _get_available_edges(context):
    """Get list of all available edges from navigation tree"""
    from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
    from shared.src.lib.database.userinterface_db import get_userinterface_by_name
    from shared.src.lib.database.navigation_trees_db import get_root_tree_for_interface
    
    device = context.selected_device
    args = context.args
    
    # Get tree_id
    userinterface = get_userinterface_by_name(context.userinterface, context.team_id)
    if not userinterface:
        print(f"❌ User interface '{context.userinterface}' not found")
        return []
    
    root_tree = get_root_tree_for_interface(userinterface['id'], context.team_id)
    if not root_tree:
        print(f"❌ No root tree found for interface '{context.userinterface}'")
        return []
    
    context.tree_id = root_tree['id']
    
    # Load navigation tree to populate cache
    nav_result = device.navigation_executor.load_navigation_tree(
        context.userinterface, 
        context.team_id
    )
    if not nav_result['success']:
        print(f"❌ Navigation tree loading failed")
        return []
    
    return find_optimal_edge_validation_sequence(context.tree_id, context.team_id)


def _fetch_kpi_results_from_db(team_id: str, device_name: str, start_time: datetime, end_time: datetime):
    """Fetch KPI measurements from execution_results table filtered by team, device, and time range"""
    from shared.src.lib.utils.supabase_utils import get_supabase_client
    
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("❌ [_fetch_kpi_results] Supabase client not available")
            return []
        
        # Query execution_results for KPI measurements in time range
        # Filter by team_id, device_name, and time window for precise device-specific results
        result = supabase.table('execution_results').select(
            'kpi_measurement_ms, kpi_measurement_success, kpi_measurement_error, executed_at, action_set_id, edge_id'
        ).eq('team_id', team_id).eq('device_name', device_name).gte(
            'executed_at', start_time.isoformat()
        ).lte(
            'executed_at', end_time.isoformat()
        ).not_.is_('kpi_measurement_ms', 'null').order('executed_at', desc=False).execute()
        
        print(f"✅ [_fetch_kpi_results] Found {len(result.data)} KPI measurements from DB for device '{device_name}'")
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
    print(f"🔗 [kpi_measurement] Action Set: {args.edge}")
    print(f"🔢 [kpi_measurement] Iterations: {args.iterations}")
    
    # Record script start time for DB query (use UTC to match database timestamps)
    script_start_time = datetime.now(timezone.utc)
    
    # Get available edges and build action_set map
    print(f"📥 [kpi_measurement] Loading available edges...")
    edges = _get_available_edges(context)
    if not edges:
        context.error_message = "No edges found in navigation tree"
        return False
    
    print(f"✅ [kpi_measurement] Found {len(edges)} edges in validation sequence")
    
    # Build action_set_map with forward/backward support
    action_set_map = {}
    
    for edge in edges:
        edge_data = edge.get('original_edge_data', {})
        action_sets = edge_data.get('action_sets', [])
        source_label = edge.get('from_node_label', '')
        target_label = edge.get('to_node_label', '')
        
        # Forward action_set (index 0)
        if len(action_sets) > 0:
            forward_set = action_sets[0]
            forward_label = forward_set.get('label', '')
            forward_id = forward_set.get('id', '')
            if forward_label and forward_set.get('actions'):
                action_set_map[forward_label] = {
                    'from_node': source_label,    # Normal direction
                    'to_node': target_label,
                    'action_set_id': forward_id   # Store action_set_id for filtering
                }
        
        # Reverse action_set (index 1) - SWAP source/target
        if len(action_sets) > 1:
            reverse_set = action_sets[1]
            reverse_label = reverse_set.get('label', '')
            reverse_id = reverse_set.get('id', '')
            if reverse_label and reverse_set.get('actions'):
                action_set_map[reverse_label] = {
                    'from_node': target_label,    # Swapped!
                    'to_node': source_label,      # Swapped!
                    'action_set_id': reverse_id   # Store action_set_id for filtering
                }
    
    print(f"✅ [kpi_measurement] Built action_set map with {len(action_set_map)} action sets")
    
    # Find selected action_set
    if args.edge not in action_set_map:
        available_labels = list(action_set_map.keys())[:10]
        context.error_message = f"Action set '{args.edge}' not found. Available (first 10): {', '.join(available_labels)}"
        return False
    
    selected = action_set_map[args.edge]
    from_label = selected['from_node']
    to_label = selected['to_node']
    selected_action_set_id = selected['action_set_id']
    
    print(f"✅ [kpi_measurement] Selected action_set: '{args.edge}'")
    print(f"📍 [kpi_measurement] Will navigate: {from_label} → {to_label}")
    print(f"🔑 [kpi_measurement] Action set ID: {selected_action_set_id}")
    
    # Execute navigation loop (simple, like goto.py)
    navigation_success_count = 0
    import asyncio
    
    for i in range(args.iterations):
        print(f"\n{'='*60}")
        print(f"🔄 [kpi_measurement] Iteration {i+1}/{args.iterations}")
        print(f"{'='*60}")
        
        # Step 1: Navigate to FROM node (skip if ENTRY - it's a virtual starting point)
        if from_label.upper() == 'ENTRY':
            # ENTRY is a conceptual starting point, not a real screen
            # We assume we're at ENTRY (app starting position) - just proceed to target
            print(f"📍 [kpi_measurement] From node is ENTRY - skipping navigation (virtual start point)")
            print(f"✅ [kpi_measurement] Assuming at ENTRY position")
        else:
            print(f"📍 [kpi_measurement] Going to '{from_label}'")
            from_result = asyncio.run(device.navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                userinterface_name=context.userinterface_name,  # MANDATORY parameter
                target_node_label=from_label,
                team_id=context.team_id,
                context=context
            ))
            
            if not from_result.get('success', False):
                print(f"❌ [kpi_measurement] Failed to reach '{from_label}'")
                continue
            
            print(f"✅ [kpi_measurement] Reached '{from_label}'")
        
        # Step 2: Navigate to TO node (like goto.py) - KPI measured automatically
        print(f"⏱️  [kpi_measurement] Navigating to '{to_label}' (KPI will be measured)")
        to_result = asyncio.run(device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            userinterface_name=context.userinterface_name,  # MANDATORY parameter
            target_node_label=to_label,
            team_id=context.team_id,
            context=context
        ))
        
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
    script_end_time = datetime.now(timezone.utc)
    print(f"📥 [kpi_measurement] Fetching KPI results from database...")
    print(f"   Time range: {script_start_time.isoformat()} to {script_end_time.isoformat()}")
    
    kpi_db_results = _fetch_kpi_results_from_db(
        team_id=context.team_id,
        device_name=device.device_name,
        start_time=script_start_time,
        end_time=script_end_time
    )
    
    print(f"\n{'='*60}")
    print(f"📊 [kpi_measurement] RAW DATABASE FETCH RESULTS:")
    print(f"{'='*60}")
    print(f"Total KPI measurements found: {len(kpi_db_results)}")
    
    if kpi_db_results:
        print(f"\nAll fetched KPI measurements:")
        for idx, result in enumerate(kpi_db_results, 1):
            action_set = result.get('action_set_id', 'N/A')
            kpi_ms = result.get('kpi_measurement_ms', 'N/A')
            success = result.get('kpi_measurement_success', False)
            executed = result.get('executed_at', 'N/A')
            status_icon = "✅" if success else "❌"
            print(f"  {idx}. {status_icon} action_set: {action_set}, KPI: {kpi_ms}ms, time: {executed}")
    else:
        print(f"⚠️  No KPI measurements found in the time range")
    
    print(f"{'='*60}\n")
    
    # Filter KPI results to only include the selected action_set_id
    filtered_kpi_results = [
        r for r in kpi_db_results 
        if r.get('action_set_id') == selected_action_set_id
    ]
    
    print(f"🔍 [kpi_measurement] Filtering for action_set: '{selected_action_set_id}'")
    print(f"📊 [kpi_measurement] Filtered results: {len(filtered_kpi_results)}/{len(kpi_db_results)} match the selected action_set")
    
    # Calculate overall success using filtered results
    successful_kpis = sum(1 for r in filtered_kpi_results if r.get('kpi_measurement_success'))
    expected_count = args.iterations
    
    print(f"📊 [kpi_measurement] KPI Results: {successful_kpis}/{len(filtered_kpi_results)} successful")
    print(f"🎯 [kpi_measurement] Expected: {expected_count} iterations, Got: {len(filtered_kpi_results)} matching KPIs")
    
    # Consider success if we have at least the expected count (not exact match to be more forgiving)
    context.overall_success = successful_kpis >= args.iterations and len(filtered_kpi_results) >= args.iterations
    
    # Always capture summary for report (use filtered results)    
    summary_text = capture_kpi_summary(
        context, 
        context.userinterface, 
        args.edge,
        from_label,
        to_label, 
        args.iterations, 
        filtered_kpi_results
    )
    context.execution_summary = summary_text
    
    return context.overall_success


# Assign script args to main function
main._script_args = _script_args

if __name__ == "__main__":
    main()
