#!/usr/bin/env python3
"""
Simple Navigation Script for VirtualPyTest

This script navigates to the live_fullscreen node by:
1. Taking control of a device
2. Loading the navigation tree
3. Finding path to live_fullscreen
4. Executing navigation steps directly using host controllers
5. Releasing device control

Usage:
    python scripts/goto_live_fullscreen.py [userinterface_name] [--host <host>] [--device <device>]
    
Example:
    python scripts/goto_live_fullscreen.py
    python scripts/goto_live_fullscreen.py horizon_android_mobile
    python scripts/goto_live_fullscreen.py horizon_android_mobile --device device2

"""

import sys
import argparse
import time
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
    execute_navigation_with_verifications
)

# Import pathfinding for navigation
from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path

# Import report generation
from shared.lib.utils.report_utils import generate_validation_report
from shared.lib.utils.cloudflare_utils import upload_script_report, upload_validation_screenshots


def main():
    """Main navigation function to goto live_fullscreen"""
    parser = argparse.ArgumentParser(description='Navigate to live_fullscreen node')
    parser.add_argument('userinterface_name', nargs='?', default='horizon_android_mobile', help='Name of the userinterface to use (default: horizon_android_mobile)')
    parser.add_argument('--host', help='Specific host to use (default: sunri-pi1)')
    parser.add_argument('--device', help='Specific device to use (default: device1)')
    
    args = parser.parse_args()
    
    userinterface_name = args.userinterface_name
    host_name = args.host or 'sunri-pi1'
    device_id = args.device or "device1"
    
    print(f"🎯 [goto_live_fullscreen] Starting navigation to live_fullscreen for: {userinterface_name}")
    
    # Initialize variables for cleanup
    device_key = None
    session_id = None
    start_time = time.time()
    overall_success = False
    error_message = ""
    
    try:
        # 1. Setup script environment (centralized)
        setup_result = setup_script_environment("goto_live_fullscreen")
        if not setup_result['success']:
            error_message = f"Setup failed: {setup_result['error']}"
            print(f"❌ [goto_live_fullscreen] {error_message}")
            sys.exit(1)
        
        host = setup_result['host']
        team_id = setup_result['team_id']
        
        # 2. Select device (centralized) - default to device1 if not provided
        device_id_to_use = device_id or "device1"
        device_result = select_device(host, device_id_to_use, "goto_live_fullscreen")
        if not device_result['success']:
            error_message = f"Device selection failed: {device_result['error']}"
            print(f"❌ [goto_live_fullscreen] {error_message}")
            sys.exit(1)
        
        selected_device = device_result['device']
        
        # 3. Take device control (centralized)
        control_result = take_device_control(host, selected_device, "goto_live_fullscreen")
        if not control_result['success']:
            error_message = f"Failed to take device control: {control_result['error']}"
            print(f"❌ [goto_live_fullscreen] {error_message}")
            sys.exit(1)
        
        session_id = control_result['session_id']
        device_key = control_result['device_key']
        
        # Capture initial state screenshot
        print("📸 [goto_live_fullscreen] Capturing initial state screenshot...")
        initial_screenshot = capture_validation_screenshot(host, selected_device, "initial_state", "goto_live_fullscreen")
        if initial_screenshot:
            screenshot_paths.append(initial_screenshot)
            print(f"✅ [goto_live_fullscreen] Initial screenshot captured")
        else:
            print("⚠️ [goto_live_fullscreen] Failed to capture initial screenshot, continuing...")
        
        # 4. Load navigation tree (centralized function)
        tree_result = load_navigation_tree(userinterface_name, "goto_live_fullscreen")
        if not tree_result['success']:
            error_message = f"Tree loading failed: {tree_result['error']}"
            print(f"❌ [goto_live_fullscreen] {error_message}")
            sys.exit(1)
        
        tree_data = tree_result['tree']
        tree_id = tree_result['tree_id']
        
        print(f"✅ [goto_live_fullscreen] Loaded tree with {len(tree_result['nodes'])} nodes and {len(tree_result['edges'])} edges")

        # 4.5 Populate navigation cache with the loaded tree data
        from shared.lib.utils.navigation_cache import populate_cache
        print("🔄 [goto_live_fullscreen] Populating navigation cache...")
        populate_cache(tree_id, team_id, tree_result['nodes'], tree_result['edges'])
        
        # 5. Find path to live_fullscreen
        print("🗺️ [goto_live_fullscreen] Finding path to live_fullscreen...")
        navigation_path = find_shortest_path(tree_id, "live_fullscreen", team_id)
        
        if not navigation_path:
            error_message = "No path found to live_fullscreen"
            print(f"❌ [goto_live_fullscreen] {error_message}")
            sys.exit(1)
        
        print(f"✅ [goto_live_fullscreen] Found path with {len(navigation_path)} steps")
        
        # 6. Execute navigation steps directly using host controllers
        print("🎮 [goto_live_fullscreen] Starting navigation on device", selected_device.device_id)
        
        for i, step in enumerate(navigation_path):
            step_num = i + 1
            from_node = step.get('from_node_label', 'unknown')
            to_node = step.get('to_node_label', 'unknown')
            
            print(f"⚡ [goto_live_fullscreen] Executing step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
            
            # Execute the navigation step directly
            step_start_time = time.time()
            step_start_timestamp = datetime.now().strftime('%H:%M:%S')
            result = execute_navigation_with_verifications(host, selected_device, step, team_id, tree_id)
            step_end_timestamp = datetime.now().strftime('%H:%M:%S')
            step_execution_time = int((time.time() - step_start_time) * 1000)
            
            # Capture screenshot after step execution
            step_screenshot = None
            try:
                step_screenshot = capture_validation_screenshot(host, selected_device, f"step_{step_num}", "goto_live_fullscreen")
                if step_screenshot:
                    screenshot_paths.append(step_screenshot)
                    print(f"📸 [goto_live_fullscreen] Step {step_num} screenshot captured")
            except Exception as e:
                print(f"⚠️ [goto_live_fullscreen] Failed to capture screenshot: {e}")
            
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
                'verifications': step.get('verifications', []),
                'verification_results': result.get('verification_results', [])
            })
            
            if not result['success']:
                error_message = f"Navigation failed at step {step_num}: {result.get('error', 'Unknown error')}"
                print(f"❌ [goto_live_fullscreen] {error_message}")
                break
            
            print(f"✅ [goto_live_fullscreen] Step {step_num} completed successfully in {step_execution_time}ms")
        else:
            print("🎉 [goto_live_fullscreen] Successfully navigated to live_fullscreen!")
            overall_success = True
        
        # 7. Summary
        total_execution_time = int((time.time() - start_time) * 1000)
        print("\n" + "="*60)
        print(f"🎯 [goto_live_fullscreen] NAVIGATION SUMMARY")
        print("="*60)
        print(f"📱 Device: {selected_device.device_name} ({selected_device.device_model})")
        print(f"🖥️  Host: {host.host_name}")
        print(f"📋 Interface: {userinterface_name}")
        print(f"🎯 Target: live_fullscreen")
        print(f"⏱️  Total Time: {total_execution_time/1000:.1f}s")
        print(f"📊 Steps: {len(navigation_path)} total")
        print(f"🎯 Result: {'SUCCESS' if overall_success else 'FAILED'}")
        if error_message:
            print(f"❌ Error: {error_message}")
        # Report URL will be added in the finally block after report generation
        print("="*60)
            
    except KeyboardInterrupt:
        error_message = "Navigation interrupted by user"
        print(f"\n⚠️ [goto_live_fullscreen] {error_message}")
        sys.exit(1)
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(f"❌ [goto_live_fullscreen] {error_message}")
        sys.exit(1)
    finally:
        # Generate report regardless of success or failure
        try:
            # Capture final screenshot
            try:
                final_screenshot = capture_validation_screenshot(host, selected_device, "final_state", "goto_live_fullscreen")
                if final_screenshot:
                    screenshot_paths.append(final_screenshot)
                    print(f"📸 [goto_live_fullscreen] Final screenshot captured")
            except Exception as e:
                print(f"⚠️ [goto_live_fullscreen] Failed to capture final screenshot: {e}")
            
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
                    script_name="goto_live_fullscreen.py",
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
                    print(f"📊 [goto_live_fullscreen] Report generated: {report_url}")
        except Exception as e:
            print(f"⚠️ [goto_live_fullscreen] Error in report generation: {e}")
            
        # Always release device control
        if device_key and session_id:
            print("🔓 [goto_live_fullscreen] Releasing control of device...")
            release_device_control(device_key, session_id, "goto_live_fullscreen")


if __name__ == "__main__":
    main() 