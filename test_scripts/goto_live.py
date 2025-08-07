#!/usr/bin/env python3
"""
Simple Navigation Script for VirtualPyTest

This script navigates to the live_fullscreen node using the unified script framework.

Usage:
    python scripts/goto_live.py [userinterface_name] [--host <host>] [--device <device>]
    
Example:
    python scripts/goto_live.py
    python scripts/goto_live.py horizon_android_mobile
    python scripts/goto_live.py horizon_android_mobile --device device2
"""

import sys
import os

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor, handle_keyboard_interrupt, handle_unexpected_error
from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path


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


def main():
    """Main navigation function to goto live_fullscreen"""
    script_name = "goto_live"
    executor = ScriptExecutor(script_name, "Navigate to live_fullscreen node")
    
    # Create argument parser
    parser = executor.create_argument_parser()
    args = parser.parse_args()
    
    # Setup execution context with database tracking enabled
    context = executor.setup_execution_context(args, enable_db_tracking=True)
    if context.error_message:
        executor.cleanup_and_exit(context, args.userinterface_name)
        return
    
    try:
        # Load navigation tree
        if not executor.load_navigation_tree(context, args.userinterface_name):
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        # Find path to live_fullscreen
        print(f"🗺️ [{script_name}] Finding path to live_fullscreen...")
        navigation_path = find_shortest_path(context.tree_id, "live_fullscreen", context.team_id)
        
        if not navigation_path:
            context.error_message = "No path found to live_fullscreen"
            print(f"❌ [{script_name}] {context.error_message}")
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        print(f"✅ [{script_name}] Found path with {len(navigation_path)} steps")
        
        # Execute navigation sequence
        success = executor.execute_navigation_sequence(context, navigation_path)
        context.overall_success = success
        
        # Capture summary for report
        summary_text = capture_navigation_summary(context, args.userinterface_name, "live_fullscreen", len(navigation_path))
        context.execution_summary = summary_text
        
        if success:
            print(f"🎉 [{script_name}] Successfully navigated to live_fullscreen!")
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)


if __name__ == "__main__":
    main() 