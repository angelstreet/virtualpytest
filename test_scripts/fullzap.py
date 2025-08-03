#!/usr/bin/env python3
"""
Fullzap Script for VirtualPyTest

This script navigates to the live node and executes a zap action multiple times by:
1. Taking control of a device
2. Loading the navigation tree
3. Finding path to live node
4. Executing navigation steps directly using host controllers
5. Finding and executing the specified action from the live node multiple times
6. Releasing device control

Usage:
    python scripts/fullzap.py [userinterface_name] [--host <host>] [--device <device>] [--action <action>] [--max_iteration <count>]
    
Example:
    python scripts/fullzap.py
    python scripts/fullzap.py horizon_android_mobile
    python scripts/fullzap.py horizon_android_mobile --action live_chup --max_iteration 20
    python scripts/fullzap.py horizon_android_mobile --device device2 --action zap_chdown --max_iteration 5

"""

import sys
import argparse
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path for imports
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import utilities
from shared.lib.utils.script_utils import (
    setup_script_environment,
    select_device,
    take_device_control,
    release_device_control,
    load_navigation_tree,
    execute_navigation_with_verifications,
    capture_validation_screenshot,
    find_node_by_label,
    find_edge_by_target_label,
    find_edge_with_action_command,
    execute_edge_actions
)

# Import pathfinding for navigation
from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path

# Import report generation
from shared.lib.utils.report_utils import generate_validation_report
from shared.lib.utils.cloudflare_utils import upload_script_report, upload_validation_screenshots


def main():
    """Main function to navigate to live and execute live_chup action"""
    parser = argparse.ArgumentParser(description='Navigate to live and execute live_chup action')
    parser.add_argument('userinterface_name', nargs='?', default='horizon_android_mobile', help='Name of the userinterface to use (default: horizon_android_mobile)')
    parser.add_argument('--host', help='Specific host to use (default: sunri-pi1)')
    parser.add_argument('--device', help='Specific device to use (default: device1)')
    parser.add_argument('--action', default='live_chup', help='Action command to execute (default: live_chup)')
    parser.add_argument('--max_iteration', type=int, default=5, help='Number of times to execute the action (default: 10)')
    
    args = parser.parse_args()
    
    userinterface_name = args.userinterface_name
    host_name = args.host or 'sunri-pi1'
    device_id = args.device or "device1"
    action_command = args.action
    max_iteration = args.max_iteration
    
    print(f"🎯 [fullzap] Starting navigation to live and executing action '{action_command}' {max_iteration} times for: {userinterface_name}")
    
    # Initialize variables for cleanup
    device_key = None
    session_id = None
    start_time = time.time()
    overall_success = False
    error_message = ""
    screenshot_paths = []
    step_results = []
    
    try:
        # 1. Setup script environment (centralized)
        setup_result = setup_script_environment("goto_live")
        if not setup_result['success']:
            error_message = f"Setup failed: {setup_result['error']}"
            print(f"❌ [goto_live] {error_message}")
            sys.exit(1)
        
        host = setup_result['host']
        team_id = setup_result['team_id']
        
        # 2. Select device (centralized) - default to device1 if not provided
        device_id_to_use = device_id or "device1"
        device_result = select_device(host, device_id_to_use, "goto_live")
        if not device_result['success']:
            error_message = f"Device selection failed: {device_result['error']}"
            print(f"❌ [goto_live] {error_message}")
            sys.exit(1)
        
        selected_device = device_result['device']
        
        # 3. Take device control (centralized)
        control_result = take_device_control(host, selected_device, "goto_live")
        if not control_result['success']:
            error_message = f"Failed to take device control: {control_result['error']}"
            print(f"❌ [goto_live] {error_message}")
            sys.exit(1)
        
        session_id = control_result['session_id']
        device_key = control_result['device_key']
        
        # Capture initial state screenshot
        print("📸 [goto_live] Capturing initial state screenshot...")
        initial_screenshot = capture_validation_screenshot(host, selected_device, "initial_state", "goto_live")
        if initial_screenshot:
            screenshot_paths.append(initial_screenshot)
            print(f"✅ [goto_live] Initial screenshot captured")
        else:
            print("⚠️ [goto_live] Failed to capture initial screenshot, continuing...")
        
        # 4. Load navigation tree (centralized function)
        tree_result = load_navigation_tree(userinterface_name, "fullzap")
        if not tree_result['success']:
            error_message = f"Tree loading failed: {tree_result['error']}"
            print(f"❌ [fullzap] {error_message}")
            sys.exit(1)
        
        tree_data = tree_result['tree']
        tree_id = tree_result['tree_id']
        nodes = tree_result['nodes']
        edges = tree_result['edges']
        
        print(f"✅ [fullzap] Loaded tree with {len(nodes)} nodes and {len(edges)} edges")

        # 4.5 Validate action availability before navigation (fail fast)
        print(f"🔍 [fullzap] Validating action '{action_command}' availability before navigation...")
        
        # Find the live node
        live_node = find_node_by_label(nodes, "live")
        if not live_node:
            error_message = "Live node not found in navigation tree"
            print(f"❌ [fullzap] {error_message}")
            sys.exit(1)
        
        live_node_id = live_node.get('node_id')
        print(f"🔍 [fullzap] Found live node with ID: '{live_node_id}'")
        
        # Debug: Show all available nodes in the tree
        print(f"🔍 [fullzap] Available nodes in tree:")
        for i, node in enumerate(nodes, 1):
            node_id = node.get('node_id', 'unknown')
            label = node.get('label', 'unknown')
            node_type = node.get('node_type', 'unknown')
            print(f"   {i}. ID: '{node_id}' | Label: '{label}' | Type: '{node_type}'")
        
        # Debug: Show all edges from live node
        from shared.lib.utils.script_utils import find_edges_from_node
        live_edges = find_edges_from_node(live_node_id, edges)
        print(f"🔍 [fullzap] Available edges from live node:")
        for i, edge in enumerate(live_edges, 1):
            edge_id = edge.get('edge_id', 'unknown')
            target_id = edge.get('target_node_id', 'unknown')
            # Find target node label
            target_node = next((n for n in nodes if n.get('node_id') == target_id), None)
            target_label = target_node.get('label', 'unknown') if target_node else 'unknown'
            print(f"   {i}. Edge '{edge_id}' → Target ID: '{target_id}' | Target Label: '{target_label}'")
        
        # Validate action edge exists (including nested sub-trees)
        from shared.lib.utils.script_utils import find_action_in_nested_trees
        
        action_result = find_action_in_nested_trees(live_node_id, tree_id, nodes, edges, action_command, team_id)
        
        if not action_result.get('success'):
            available_actions = [next((n.get('label') for n in nodes if n.get('node_id') == e.get('target_node_id')), 'unknown') for e in live_edges]
            error_message = f"Action '{action_command}' not found from live node (checked main tree + sub-trees). Available actions: {available_actions}"
            print(f"❌ [fullzap] {error_message}")
            sys.exit(1)
        
        action_edge = action_result.get('edge')
        tree_type = action_result.get('tree_type')
        action_tree_id = action_result.get('tree_id')
        
        if tree_type == 'main':
            print(f"✅ [fullzap] Action '{action_command}' found in main tree - edge: {action_edge.get('edge_id')}")
        else:
            source_node_id = action_result.get('source_node_id')
            print(f"✅ [fullzap] Action '{action_command}' found in sub-tree {action_tree_id} - edge: {action_edge.get('edge_id')} (from node: {source_node_id})")

        # 4.6 Populate navigation cache with the loaded tree data
        from shared.lib.utils.navigation_cache import populate_cache
        print("🔄 [goto_live] Populating navigation cache...")
        populate_cache(tree_id, team_id, tree_result['nodes'], tree_result['edges'])
        
        # 5. Find path to live node
        print("🗺️ [fullzap] Finding path to live...")
        navigation_path = find_shortest_path(tree_id, "live", team_id)
        
        if not navigation_path:
            error_message = "No path found to live node"
            print(f"❌ [fullzap] {error_message}")
            sys.exit(1)
        
        print(f"✅ [fullzap] Found path with {len(navigation_path)} steps")
        
        # 6. Execute navigation steps directly using host controllers
        print("🎮 [goto_live] Starting navigation on device", selected_device.device_id)
        
        for i, step in enumerate(navigation_path):
            step_num = i + 1
            from_node = step.get('from_node_label', 'unknown')
            to_node = step.get('to_node_label', 'unknown')
            
            print(f"⚡ [goto_live] Executing step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
            
            # Execute the navigation step directly
            step_start_time = time.time()
            step_start_timestamp = datetime.now().strftime('%H:%M:%S')
            result = execute_navigation_with_verifications(host, selected_device, step, team_id, tree_id)
            step_end_timestamp = datetime.now().strftime('%H:%M:%S')
            step_execution_time = int((time.time() - step_start_time) * 1000)
            
            # Capture screenshot after step execution
            step_screenshot = None
            try:
                step_screenshot = capture_validation_screenshot(host, selected_device, f"step_{step_num}", "goto_live")
                if step_screenshot:
                    screenshot_paths.append(step_screenshot)
                    print(f"📸 [goto_live] Step {step_num} screenshot captured")
            except Exception as e:
                print(f"⚠️ [goto_live] Failed to capture screenshot: {e}")
            
            # Record step result
            step_results.append({
                'step_number': step_num,
                'success': result['success'],
                'screenshot_path': step_screenshot,
                'message': f"Navigation step {step_num}: {from_node} → {to_node}",
                'execution_time_ms': step_execution_time,
                'start_time': step_start_timestamp,
                'end_time': step_end_timestamp,
                'from_node': from_node,
                'to_node': to_node,
                'actions': step.get('actions', []),
                'retryActions': step.get('retryActions', []),  # Capture retry actions
                'verifications': step.get('verifications', []),
                'verification_results': result.get('verification_results', [])
            })
            
            if not result['success']:
                error_message = f"Navigation failed at step {step_num}: {result.get('error', 'Unknown error')}"
                print(f"❌ [goto_live] {error_message}")
                break
            
            print(f"✅ [goto_live] Step {step_num} completed successfully in {step_execution_time}ms")
        else:
            print("🎉 [fullzap] Successfully navigated to live!")
            
            # 7. Execute the validated action from the live node multiple times
            print(f"⚡ [fullzap] Executing pre-validated action '{action_command}' from live node...")
            
            # We already validated the action edge exists, so just find it again
            live_node = find_node_by_label(nodes, "live")
            live_node_id = live_node.get('node_id')
            
            # Use the pre-validated action edge from earlier validation
            print(f"✅ [fullzap] Using validated edge: {action_edge.get('edge_id')} (from {tree_type} tree)")
            print(f"🔄 [fullzap] Starting {max_iteration} iterations of action '{action_command}'...")
            
            # Capture pre-action screenshot
            pre_action_screenshot = capture_validation_screenshot(host, selected_device, "pre_action", "fullzap")
            if pre_action_screenshot:
                screenshot_paths.append(pre_action_screenshot)
            
            # Execute the action multiple times
            successful_iterations = 0
            total_action_time = 0
            
            for iteration in range(1, max_iteration + 1):
                print(f"🎬 [fullzap] Executing iteration {iteration}/{max_iteration} of action '{action_command}'...")
                iteration_start_time = time.time()
                
                action_result = execute_edge_actions(host, selected_device, action_edge, team_id=team_id)
                iteration_execution_time = int((time.time() - iteration_start_time) * 1000)
                total_action_time += iteration_execution_time
                
                if action_result.get('success'):
                    print(f"✅ [fullzap] Iteration {iteration} completed successfully in {iteration_execution_time}ms")
                    successful_iterations += 1
                    
                    # Brief pause between iterations to avoid overwhelming the device
                    if iteration < max_iteration:
                        time.sleep(0.5)
                else:
                    iteration_error = action_result.get('error', 'Unknown error')
                    print(f"❌ [fullzap] Iteration {iteration} failed: {iteration_error}")
                    # Continue with remaining iterations even if one fails
            
            # Capture post-action screenshot
            post_action_screenshot = capture_validation_screenshot(host, selected_device, "post_action", "fullzap")
            if post_action_screenshot:
                screenshot_paths.append(post_action_screenshot)
            
            # Summary of action execution
            average_time = total_action_time / max_iteration if max_iteration > 0 else 0
            success_rate = (successful_iterations / max_iteration * 100) if max_iteration > 0 else 0
            
            print(f"📊 [fullzap] Action execution summary:")
            print(f"   • Total iterations: {max_iteration}")
            print(f"   • Successful: {successful_iterations}")
            print(f"   • Success rate: {success_rate:.1f}%")
            print(f"   • Average time per iteration: {average_time:.0f}ms")
            print(f"   • Total action time: {total_action_time}ms")
            
            if successful_iterations == max_iteration:
                print(f"✅ [fullzap] All {max_iteration} iterations of action '{action_command}' completed successfully!")
                overall_success = True
            elif successful_iterations > 0:
                print(f"⚠️ [fullzap] {successful_iterations}/{max_iteration} iterations succeeded")
                overall_success = True  # Partial success is still considered success
            else:
                error_message = f"All {max_iteration} iterations of action '{action_command}' failed"
                print(f"❌ [fullzap] {error_message}")
                overall_success = False
        
        # 8. Summary
        total_execution_time = int((time.time() - start_time) * 1000)
        print("\n" + "="*60)
        print(f"🎯 [fullzap] FULLZAP EXECUTION SUMMARY")
        print("="*60)
        print(f"📱 Device: {selected_device.device_name} ({selected_device.device_model})")
        print(f"🖥️  Host: {host.host_name}")
        print(f"📋 Interface: {userinterface_name}")
        print(f"🗺️  Navigation: home → live ({len(navigation_path)} steps)")
        print(f"⚡ Action: {action_command} ({max_iteration} iterations)")
        print(f"⏱️  Total Time: {total_execution_time/1000:.1f}s")
        print(f"🎯 Result: {'SUCCESS' if overall_success else 'FAILED'}")
        if error_message:
            print(f"❌ Error: {error_message}")
        # Report URL will be added in the finally block after report generation
        print("="*60)
        
        # Exit with proper code based on result
        if overall_success:
            print("✅ [fullzap] Fullzap execution completed successfully - exiting with code 0")
            # Don't exit here, let finally block handle cleanup first
        else:
            print("❌ [fullzap] Fullzap execution failed - will exit with code 1")
            # Don't exit here, let finally block handle cleanup first
            
    except KeyboardInterrupt:
        error_message = "Fullzap execution interrupted by user"
        print(f"\n⚠️ [fullzap] {error_message}")
        overall_success = False
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(f"❌ [fullzap] {error_message}")
        overall_success = False
    finally:
        # Generate report regardless of success or failure
        try:
            # Capture final screenshot
            try:
                final_screenshot = capture_validation_screenshot(host, selected_device, "final_state", "fullzap")
                if final_screenshot:
                    screenshot_paths.append(final_screenshot)
                    print(f"📸 [fullzap] Final screenshot captured")
            except Exception as e:
                print(f"⚠️ [fullzap] Failed to capture final screenshot: {e}")
            
            # Generate and upload report
            if 'selected_device' in locals():
                # Use shared report generation function
                from shared.lib.utils.report_utils import generate_and_upload_script_report
                
                total_execution_time = int((time.time() - start_time) * 1000)
                device_info = {
                    'device_name': selected_device.device_name,
                    'device_model': selected_device.device_model,
                    'device_id': selected_device.device_id
                }
                host_info = {
                    'host_name': host.host_name
                }
                
                report_url = generate_and_upload_script_report(
                    script_name="fullzap.py",
                    device_info=device_info,
                    host_info=host_info,
                    execution_time=total_execution_time,
                    success=overall_success,
                    step_results=step_results,
                    screenshot_paths=screenshot_paths,
                    error_message=error_message,
                    userinterface_name=userinterface_name
                )
                
                if report_url:
                    print(f"📊 [fullzap] Report generated: {report_url}")
        except Exception as e:
            print(f"⚠️ [fullzap] Error in report generation: {e}")
            
        # Always release device control
        if device_key and session_id:
            print("🔓 [fullzap] Releasing control of device...")
            release_device_control(device_key, session_id, "fullzap")

    # Exit with proper code based on overall result
    if overall_success:
        print("✅ [fullzap] Exiting with success code 0")
        sys.exit(0)  # Success
    else:
        print("❌ [fullzap] Exiting with failure code 1")
        sys.exit(1)  # Failure


if __name__ == "__main__":
    main() 