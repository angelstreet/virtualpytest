#!/usr/bin/env python3
"""
Generic Navigation Script for VirtualPyTest

This script navigates to a specified node in the navigation tree.
If no node is specified, it defaults to 'home'.

Usage:
    python test_scripts/goto.py [userinterface_name] [--node <node_name>] [--host <host>] [--device <device>]
    
Examples:
    python test_scripts/goto.py                           # Goes to 'home' node
    python test_scripts/goto.py --node live               # Goes to 'live' node
    python test_scripts/goto.py horizon_android_mobile --node settings
    python test_scripts/goto.py horizon_android_tv --node live_fullscreen --device device2
"""

import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, navigate_to, get_context, get_args


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


@script("goto", "Navigate to specified node")
def main():
    """Main navigation function to goto specified node"""
    args = get_args()
    context = get_context()
    target_node = args.node
    
    print(f"🎯 [goto] Target node: {target_node}")
    print(f"📱 [goto] Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    
    # Navigate using high-level method (auto-loads tree, executes, records step)
    success = navigate_to(target_node)
    
    # Always capture summary for report (regardless of success/failure)
    summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, 1)
    context.execution_summary = summary_text
    
    return success

# Define script-specific arguments
main._script_args = ['--node:str:home']

if __name__ == "__main__":
    main()
