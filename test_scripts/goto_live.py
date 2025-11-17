#!/usr/bin/env python3
"""
Smart Navigation Script for VirtualPyTest

This script intelligently navigates to the appropriate live node based on device type:
- For mobile devices: navigates to 'live_fullscreen'
- For other devices: navigates to 'live'

Device type is determined by checking if the device model contains 'mobile' (case-insensitive).

Usage:
    python scripts/goto_live.py [userinterface_name] [--host <host>] [--device <device>]
    
Example:
    python scripts/goto_live.py
    python scripts/goto_live.py horizon_android_mobile    # Will go to live_fullscreen
    python scripts/goto_live.py horizon_android_tv        # Will go to live
    python scripts/goto_live.py horizon_android_mobile --device device2
"""

import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args


def capture_navigation_summary(context, userinterface_name: str, target_node: str, already_at_destination: bool = False) -> str:
    """Capture navigation summary as text for report"""
    lines = []
    lines.append(f"🎯 [GOTO_{target_node.upper()}] EXECUTION SUMMARY")
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


@script("goto_live", "Navigate to live node")
def main():
    """Main navigation function to goto live"""
    context = get_context()
    args = get_args()
    device = context.selected_device
    
    # Determine target node based on device model
    target_node = "live_fullscreen" if device.is_mobile_device() else "live"
    
    print(f"🎯 [goto_live] Device model: {device.device_model}")
    print(f"🎯 [goto_live] Target node: {target_node}")
    
    # Load navigation tree
    nav_result = device.navigation_executor.load_navigation_tree(
        context.userinterface, 
        context.team_id
    )
    if not nav_result['success']:
        context.error_message = f"Navigation tree loading failed: {nav_result.get('error', 'Unknown error')}"
        return False
    
    context.tree_id = nav_result['tree_id']
    
    # Execute navigation using NavigationExecutor directly
    # ✅ Wrap async call with asyncio.run for script context
    import asyncio
    result = asyncio.run(device.navigation_executor.execute_navigation(
        tree_id=context.tree_id,
        userinterface_name=context.userinterface_name,  # MANDATORY parameter
        target_node_label=target_node,
        team_id=context.team_id,
        context=context
    ))
    
    success = result.get('success', False)
    if not success:
        context.error_message = result.get('error', 'Navigation failed')
    
    # Set overall_success BEFORE capturing summary so it shows correct status
    context.overall_success = success
    
    # Check if already at destination (no steps recorded)
    already_at_destination = (len(context.step_results) == 0 and success)
    
    # Always capture summary for report (regardless of success/failure)
    summary_text = capture_navigation_summary(context, context.userinterface, target_node, already_at_destination)
    context.execution_summary = summary_text
    
    return success

# Script arguments (framework params like host/device/userinterface are automatic)
main._script_args = []

if __name__ == "__main__":
    main() 