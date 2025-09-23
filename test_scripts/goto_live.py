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

from shared.src.lib.executors.script_decorators import script, is_mobile_device, navigate_to, get_context, get_args


def capture_navigation_summary(context, userinterface_name: str, target_node: str, path_length: int) -> str:
    """Capture navigation summary as text for report"""
    lines = []
    lines.append(f"🎯 [GOTO_{target_node.upper()}] EXECUTION SUMMARY")
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"🗺️  Target: {target_node}")
    lines.append(f"📍 Path length: {path_length} steps")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    lines.append(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"❌ Error: {context.error_message}")
    
    return "\n".join(lines)


@script("goto_live", "Navigate to live node")
def main():
    """Main navigation function to goto live"""
    # Determine target node based on device model
    target_node = "live_fullscreen" if is_mobile_device() else "live"
    
    context = get_context()
    args = get_args()
    device = context.selected_device
    
    print(f"🎯 [goto_live] Device model: {device.device_model}")
    print(f"🎯 [goto_live] Target node: {target_node}")
    
    # Navigate using high-level method (auto-loads tree, executes, records step)
    success = navigate_to(target_node)
    
    # Always capture summary for report (regardless of success/failure)
    summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, 1)
    context.execution_summary = summary_text
    
    return success

# Define script-specific arguments (none needed for this script)
main._script_args = []

if __name__ == "__main__":
    main() 