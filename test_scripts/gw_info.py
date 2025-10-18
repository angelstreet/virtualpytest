#!/usr/bin/env python3
"""
Go to Info Node Script for VirtualPyTest

This script navigates to the 'info' node in the navigation tree.
To change to a different info node (e.g., 'info_settings'), edit the TARGET_NODE constant below.

Usage:
    python test_scripts/gw_info.py [userinterface_name] [--host <host>] [--device <device>]
    
Examples:
    python test_scripts/gw_info.py                           # Goes to 'info' node
    python test_scripts/gw_info.py horizon_android_mobile
    python test_scripts/gw_info.py horizon_android_tv --device device2
"""

import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device

# Hard-coded target node - change this if you need a different info node
TARGET_NODE = "info"


def capture_navigation_summary(context, userinterface_name: str, target_node: str, already_at_destination: bool = False) -> str:
    """Capture navigation summary as text for report"""
    lines = []
    lines.append(f"🎯 [GW_INFO] EXECUTION SUMMARY")
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"🗺️  Target: {target_node}")
    
    if already_at_destination:
        lines.append(f"✅ Already at destination - no navigation needed")
        lines.append(f"📍 Navigation steps: 0 (already verified at target)")
    else:
        lines.append(f"📍 Navigation steps: {len(context.step_results)}")
    
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    lines.append(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"❌ Error: {context.error_message}")
    
    return "\n".join(lines)


@script("gw_info", f"Navigate to {TARGET_NODE} node")
def main():
    """Main navigation function to goto info node"""
    args = get_args()
    context = get_context()
    device = get_device()
    print(f"🎯 [gw_info] Target node: {TARGET_NODE}")
    print(f"📱 [gw_info] Device: {device.device_name} ({device.device_model})")
    
    # Load navigation tree
    nav_result = device.navigation_executor.load_navigation_tree(
        args.userinterface_name, 
        context.team_id
    )
    if not nav_result['success']:
        context.error_message = f"Navigation tree loading failed: {nav_result.get('error', 'Unknown error')}"
        return False
    
    context.tree_id = nav_result['tree_id']
    
    # Execute navigation using NavigationExecutor directly
    result = device.navigation_executor.execute_navigation(
        tree_id=context.tree_id,
        target_node_label=TARGET_NODE,
        team_id=context.team_id,
        context=context
    )
    
    success = result.get('success', False)
    if not success:
        context.error_message = result.get('error', 'Navigation failed')
    
    # Set overall_success BEFORE capturing summary so it shows correct status
    context.overall_success = success
    
    # Check if already at destination (no steps recorded)
    already_at_destination = (len(context.step_results) == 0 and success)
    
    # Always capture summary for report (regardless of success/failure)
    summary_text = capture_navigation_summary(context, args.userinterface_name, TARGET_NODE, already_at_destination)
    context.execution_summary = summary_text
    
    return success

# No script-specific arguments needed - TARGET_NODE is hard-coded
main._script_args = []

if __name__ == "__main__":
    main()

