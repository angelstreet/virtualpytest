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

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend_host.src.lib.utils.script_utils import ScriptExecutor, handle_keyboard_interrupt, handle_unexpected_error
from backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path


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
    """Main navigation function to goto specified node"""
    script_name = "goto"
    executor = ScriptExecutor(script_name, "Navigate to specified node")
    
    # Create argument parser with custom --node parameter
    parser = executor.create_argument_parser()
    parser.add_argument('--node', type=str, default='home', 
                       help='Target node to navigate to (default: home)')
    args = parser.parse_args()
    
    target_node = args.node
    
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
        
        print(f"🎯 [{script_name}] Target node: {target_node}")
        print(f"📱 [{script_name}] Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
        
        # Find path to target node
        print(f"🗺️ [{script_name}] Finding path to {target_node}...")
        navigation_path = find_shortest_path(context.tree_id, target_node, context.team_id)
        
        if not navigation_path:
            context.error_message = f"No path found to '{target_node}'"
            print(f"❌ [{script_name}] {context.error_message}")
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        print(f"✅ [{script_name}] Found path with {len(navigation_path)} steps")
        
        # Execute navigation sequence with early stopping for goto functions
        success = executor.execute_navigation_sequence(context, navigation_path, early_stop_on_failure=True)
        context.overall_success = success
        
        # Capture summary for report
        summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, len(navigation_path))
        context.execution_summary = summary_text
        
        if success:
            print(f"🎉 [{script_name}] Successfully navigated to '{target_node}'!")
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)


if __name__ == "__main__":
    main()
