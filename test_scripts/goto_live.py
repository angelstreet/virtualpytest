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

from shared.src.lib.executors.script_executor import ScriptExecutor, ScriptExecutionContext, handle_keyboard_interrupt, handle_unexpected_error
# Navigation is now handled entirely by the script executor - high-level methods with auto-recording


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
    """Main navigation function to goto live"""
    script_name = "goto_live"
    executor = ScriptExecutor(script_name, "Navigate to live node")
    
    # Create argument parser
    parser = executor.create_argument_parser()
    args = parser.parse_args()
    
    # Setup execution context with database tracking enabled
    context = executor.setup_execution_context(args, enable_db_tracking=True)
    if context.error_message:
        executor.cleanup_and_exit(context, args.userinterface_name)
        return
    
    try:
        # Determine target node based on device model
        device = context.selected_device
        if "mobile" in device.device_model.lower():
            target_node = "live_fullscreen"
        else:
            target_node = "live"
        
        print(f"🎯 [{script_name}] Device model: {device.device_model}")
        print(f"🎯 [{script_name}] Target node: {target_node}")
        
        # Navigate using high-level method (auto-loads tree, executes, records step)
        success = executor.navigate_to(context, target_node, args.userinterface_name)
        
        if success:
            executor.test_success(context)
            # Capture summary for report
            summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, 1)
            if not hasattr(context, 'custom_data'):
                context.custom_data = {}
            context.custom_data['execution_summary'] = summary_text
        else:
            executor.test_fail(context)
        
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)


if __name__ == "__main__":
    main() 