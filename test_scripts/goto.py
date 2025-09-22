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

# Set up project paths
from shared.src.lib.executors.script_executor import setup_project_paths
setup_project_paths()

from shared.src.lib.executors.script_executor import ScriptExecutor, ScriptExecutionContext, handle_keyboard_interrupt, handle_unexpected_error
from shared.src.lib.executors.step_executor import StepExecutor
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
        
        # Execute navigation using proper navigation executor (same as goto_live.py)
        print(f"🗺️ [{script_name}] Navigating to {target_node} using proper navigation executor...")
        
        navigation_result = context.selected_device.navigation_executor.execute_navigation(
            tree_id=context.tree_id,
            target_node_label=target_node,
            team_id=context.team_id,
            context=context
        )
        success = navigation_result['success']
        context.overall_success = success
        
        # Create and record navigation step using StepExecutor
        step_executor = StepExecutor(context)
        nav_step = step_executor.create_navigation_step(navigation_result, "entry", target_node)
        context.record_step_dict(nav_step)
        
        if not success:
            context.error_message = navigation_result.get('error', 'Navigation failed')
        
        # Capture summary for report
        path_length = navigation_result.get('total_transitions', 0)
        summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, path_length)
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
