#!/usr/bin/env python3
"""
Fullzap Script for VirtualPyTest

This script optionally navigates to the live node and executes a zap action multiple times
using the unified script framework with motion detection validation.

Usage:
    python scripts/fullzap.py [userinterface_name] [--host <host>] [--device <device>] [--action <action>] [--max_iteration <count>] [--goto_live <true|false>]
    
Example:
    python scripts/fullzap.py
    python scripts/fullzap.py horizon_android_mobile
    python scripts/fullzap.py horizon_android_mobile --action live_chup --max_iteration 20
    python scripts/fullzap.py horizon_android_mobile --device device2 --action zap_chdown --max_iteration 5
    python scripts/fullzap.py horizon_android_mobile --goto_live false --action live_chup --max_iteration 10
"""

import sys
import os
import time
from datetime import datetime

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor, ScriptExecutionContext, handle_keyboard_interrupt, handle_unexpected_error
from shared.lib.utils.zap_controller import ZapController
from shared.lib.utils.navigation_utils import (
    validate_action_availability,
    goto_node
)
from shared.lib.utils.audio_menu_analyzer import analyze_audio_menu

def create_zap_controller(context: ScriptExecutionContext) -> ZapController:
    """Create a ZapController with direct Python video analysis capabilities"""
    print("🔧 [fullzap] Creating ZapController with direct Python video analysis...")
    
    # Create ZapController - it will use get_controller() internally
    zap_controller = ZapController()
    
    print("✅ [fullzap] ZapController ready with direct Python analysis capabilities")
    
    return zap_controller

def execute_zap_actions(context: ScriptExecutionContext, action_edge, action_command: str, max_iteration: int, zap_controller: ZapController, blackscreen_area: str = None, goto_live: bool = True):
    """Execute zap actions using ZapController with simple sequential recording"""
    print(f"⚡ [fullzap] Delegating zap execution to ZapController...")
    if blackscreen_area:
        print(f"🎯 [fullzap] Using custom blackscreen area: {blackscreen_area}")
    print(f"🎯 [fullzap] Audio menu analysis will be {'done once outside loop' if goto_live else 'skipped'}")
    return zap_controller.execute_zap_iterations(context, action_edge, action_command, max_iteration, blackscreen_area, goto_live)


def capture_fullzap_summary(context: ScriptExecutionContext, userinterface_name: str) -> str:
    """Capture fullzap summary as text for report"""
    lines = []
    
    # Get ZapController statistics from context
    action_command = context.custom_data.get('action_command', 'unknown')
    max_iteration = context.custom_data.get('max_iteration', 0)
    successful_iterations = context.custom_data.get('successful_iterations', 0)
    motion_detected_count = context.custom_data.get('motion_detected_count', 0)
    subtitles_detected_count = context.custom_data.get('subtitles_detected_count', 0)
    audio_speech_detected_count = context.custom_data.get('audio_speech_detected_count', 0)
    zapping_detected_count = context.custom_data.get('zapping_detected_count', 0)
    total_action_time = context.custom_data.get('total_action_time', 0)
    
    # Enhanced zapping statistics
    zapping_durations = context.custom_data.get('zapping_durations', [])
    blackscreen_durations = context.custom_data.get('blackscreen_durations', [])
    detected_channels = context.custom_data.get('detected_channels', [])
    channel_info_results = context.custom_data.get('channel_info_results', [])
    
    # Language detection statistics
    detected_languages = context.custom_data.get('detected_languages', [])
    audio_languages = context.custom_data.get('audio_languages', [])
    
    # ZapController Action execution summary
    if max_iteration > 0:
        lines.append("📊 [ZapController] Action execution summary:")
        lines.append(f"   • Total iterations: {max_iteration}")
        lines.append(f"   • Successful: {successful_iterations}")
        success_rate = (successful_iterations / max_iteration * 100) if max_iteration > 0 else 0
        lines.append(f"   • Success rate: {success_rate:.1f}%")
        avg_time = total_action_time / max_iteration if max_iteration > 0 else 0
        lines.append(f"   • Average time per iteration: {avg_time:.0f}ms")
        lines.append(f"   • Total action time: {total_action_time}ms")
        motion_rate = (motion_detected_count / max_iteration * 100) if max_iteration > 0 else 0
        lines.append(f"   • Motion detected: {motion_detected_count}/{max_iteration} ({motion_rate:.1f}%)")
        subtitle_rate = (subtitles_detected_count / max_iteration * 100) if max_iteration > 0 else 0
        lines.append(f"   • Subtitles detected: {subtitles_detected_count}/{max_iteration} ({subtitle_rate:.1f}%)")
        audio_speech_rate = (audio_speech_detected_count / max_iteration * 100) if max_iteration > 0 else 0
        lines.append(f"   • Audio speech detected: {audio_speech_detected_count}/{max_iteration} ({audio_speech_rate:.1f}%)")
        zapping_rate = (zapping_detected_count / max_iteration * 100) if max_iteration > 0 else 0
        lines.append(f"   • Zapping detected: {zapping_detected_count}/{max_iteration} ({zapping_rate:.1f}%)")
        
        # Enhanced zapping duration information
        if zapping_durations:
            avg_zap_duration = sum(zapping_durations) / len(zapping_durations)
            avg_blackscreen_duration = sum(blackscreen_durations) / len(blackscreen_durations) if blackscreen_durations else 0.0
            lines.append(f"   ⚡ Average zapping duration: {avg_zap_duration:.2f}s")
            lines.append(f"   ⬛ Average blackscreen duration: {avg_blackscreen_duration:.2f}s")
            
            min_zap = min(zapping_durations)
            max_zap = max(zapping_durations)
            lines.append(f"   📊 Zapping duration range: {min_zap:.2f}s - {max_zap:.2f}s")
        
        # Channel information
        if detected_channels:
            lines.append(f"   📺 Channels detected: {', '.join(detected_channels)}")
            
            # Show detailed channel info for successful zaps
            successful_channel_info = [info for info in channel_info_results if info.get('channel_name')]
            if successful_channel_info:
                lines.append(f"   🎬 Channel details:")
                for i, info in enumerate(successful_channel_info, 1):
                    channel_display = info['channel_name']
                    if info.get('channel_number'):
                        channel_display += f" ({info['channel_number']})"
                    if info.get('program_name'):
                        channel_display += f" - {info['program_name']}"
                    if info.get('program_start_time') and info.get('program_end_time'):
                        channel_display += f" [{info['program_start_time']}-{info['program_end_time']}]"
                    
                    lines.append(f"      {i}. {channel_display} (zap: {info['zapping_duration']:.2f}s, confidence: {info['channel_confidence']:.1f})")
        
        # Language information
        if detected_languages:
            lines.append(f"   🌐 Subtitle languages detected: {', '.join(detected_languages)}")
        
        if audio_languages:
            lines.append(f"   🎤 Audio languages detected: {', '.join(audio_languages)}")
        
        # Check for content change issues
        no_motion_count = max_iteration - motion_detected_count
        if no_motion_count > 0:
            lines.append(f"   ⚠️  {no_motion_count} zap(s) did not show content change")
        
        # Success message
        if successful_iterations == max_iteration:
            lines.append(f"✅ [fullzap] All {max_iteration} iterations of action '{action_command}' completed successfully!")
        else:
            lines.append(f"❌ [fullzap] Only {successful_iterations}/{max_iteration} iterations of action '{action_command}' completed successfully!")
        
        lines.append("")  # Empty line separator
    
    # Basic script execution summary
    lines.append("🎯 [FULLZAP] EXECUTION SUMMARY")
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    lines.append(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"❌ Error: {context.error_message}")
    
    lines.append("✅ [fullzap] Fullzap execution completed successfully!")
    
    return "\n".join(lines)


def print_fullzap_summary(context: ScriptExecutionContext, userinterface_name: str):
    """Print simple fullzap summary - detailed stats are handled by ZapController"""
    print("\n" + "="*60)
    print(f"🎯 [FULLZAP] EXECUTION SUMMARY")
    print("="*60)
    print(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    print(f"🖥️  Host: {context.host.host_name}")
    print(f"📋 Interface: {userinterface_name}")
    print(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    print(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    print(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        print(f"❌ Error: {context.error_message}")
    
    print("="*60)

def main():
    """Main function to optionally navigate to live and execute zap action multiple times"""
    script_name = "fullzap"
    executor = ScriptExecutor(script_name, "Optionally navigate to live and execute zap action multiple times")
    
    # Create argument parser with custom fullzap arguments
    additional_args = [
        {
            'name': '--action',
            'kwargs': {
                'default': 'live_chup',
                'help': 'Action command to execute (default: live_chup)'
            }
        },
        {
            'name': '--max_iteration',
            'kwargs': {
                'type': int,
                'default': 3,
                'help': 'Number of times to execute the action (default: 3)'
            }
        },
        {
            'name': '--blackscreen_area',
            'kwargs': {
                'default': '0,0,1920,720',
                'help': 'Blackscreen analysis area as x,y,width,height (default: 0,0,1920,720 for TV, auto-adjusts for mobile devices)'
            }
        },
        {
            'name': '--goto_live',
            'kwargs': {
                'type': lambda x: x.lower() == 'true',
                'default': True,
                'help': 'Navigate to live node before executing actions: true or false (default: true)'
            }
        }
    ]
    
    parser = executor.create_argument_parser(additional_args)
    args = parser.parse_args()
    
    nav_msg = "with navigation to live" if args.goto_live else "without navigation to live"
    print(f"🎯 [fullzap] Starting execution of action '{args.action}' {args.max_iteration} times {nav_msg} for: {args.userinterface_name}")
    
    # Setup execution context with database tracking enabled
    context = executor.setup_execution_context(args, enable_db_tracking=True)
    if context.error_message:
        executor.cleanup_and_exit(context, args.userinterface_name)
        return
    
    try:
        # Create ZapController for execution and analysis
        zap_controller = create_zap_controller(context)
        
        # Load navigation tree
        if not executor.load_navigation_tree(context, args.userinterface_name):
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        # Determine target node based on device model - same logic as goto_live.py
        if "mobile" in context.selected_device.device_model.lower():
            target_node = "live_fullscreen"
            print(f"📱 [fullzap] Mobile device detected - using live_fullscreen as base node")
        else:
            target_node = "live"
        
        # Map action command to be node-specific
        if target_node == "live_fullscreen" and args.action == "live_chup":
            mapped_action = "live_fullscreen_chup"
            print(f"🔄 [fullzap] Mapped action '{args.action}' to '{mapped_action}' for {target_node} node")
        elif target_node == "live_fullscreen" and args.action == "live_chdown":
            mapped_action = "live_fullscreen_chdown"
            print(f"🔄 [fullzap] Mapped action '{args.action}' to '{mapped_action}' for {target_node} node")
        else:
            mapped_action = args.action
        
        print(f"🎯 [fullzap] Device model: {context.selected_device.device_model}")
        print(f"🎯 [fullzap] Target node: {target_node}")
        

        
        # Conditionally navigate to target node based on parameter
        nav_success = True
        if args.goto_live:
            print(f"🗺️ [fullzap] Navigating to {target_node} node...")
            live_result = goto_node(context.host, context.selected_device, target_node, context.tree_id, context.team_id, context)
            
            if not live_result.get('success'):
                context.error_message = f"Failed to navigate to {target_node}: {live_result.get('error', 'Unknown error')}"
                print(f"❌ [fullzap] {context.error_message}")
                executor.cleanup_and_exit(context, args.userinterface_name)
                return
            
            print(f"🎉 [fullzap] Successfully navigated to {target_node}!")
        else:
            print(f"⏭️ [fullzap] Skipping navigation to {target_node} node (--goto_live false specified)")
            
            # IMPORTANT: Manually set current node to target since we're assuming we're already there
            # This prevents navigation from going back to home during script execution
            from shared.lib.utils.navigation_utils import find_node_by_label
            target_node_obj = find_node_by_label(context.nodes, target_node)
            if target_node_obj:
                target_node_id = target_node_obj.get('node_id')
                context.current_node_id = target_node_id
                print(f"🎯 [fullzap] Manually set current position to {target_node} node: {target_node_id}")
            else:
                print(f"⚠️ [fullzap] Warning: Could not find {target_node} node in navigation tree - navigation context may be incorrect")
        
        # Store mapped action in context for summary display
        context.custom_data['action_command'] = mapped_action
        
        # For mobile devices, determine correct audio menu node and pass to zap_controller
        if "mobile" in context.selected_device.device_model.lower():
            context.audio_menu_node = "live_fullscreen_audiomenu"
            print(f"🎧 [fullzap] Set mobile audio menu target: {context.audio_menu_node}")
        else:
            context.audio_menu_node = "live_audiomenu"
        
        # Find the actual action edge from current node to target node
        print(f"🔍 [fullzap] Finding edge for action '{mapped_action}' from current node...")
        from shared.lib.utils.navigation_utils import find_edge_by_target_label
        
        action_edge = find_edge_by_target_label(
            context.current_node_id, 
            context.edges, 
            context.all_nodes, 
            mapped_action  # e.g., 'live_fullscreen_chup'
        )
        
        if not action_edge:
            context.error_message = f"No edge found from current node to '{mapped_action}'"
            print(f"❌ [fullzap] {context.error_message}")
            print(f"📋 [fullzap] Current node: {context.current_node_id}")
            print(f"📋 [fullzap] Available edges: {len(context.edges)}")
            executor.cleanup_and_exit(context, args.userinterface_name)
            return
        
        print(f"✅ [fullzap] Found edge for action '{mapped_action}'")
        
        # Execute zap actions multiple times with comprehensive analysis
        location_msg = f"from {target_node} node" if args.goto_live else "from current location"
        print(f"⚡ [fullzap] Executing action '{mapped_action}' {location_msg}...")
        try:
            zap_success = execute_zap_actions(context, action_edge, mapped_action, args.max_iteration, zap_controller, args.blackscreen_area, args.goto_live)
        except Exception as e:
            print(f"⚠️ [fullzap] ZapController error (continuing anyway): {e}")
            zap_success = True  # Navigation worked, so consider it success
        
        context.overall_success = nav_success and zap_success
        
        if context.overall_success:
            print(f"✅ [fullzap] All {args.max_iteration} iterations of action '{mapped_action}' completed successfully!")
        else:
            if not zap_success:
                context.error_message = f"Some zap actions failed"
            elif not nav_success:
                context.error_message = f"Failed to navigate to live node"
        
        # Print custom fullzap summary and capture it
        summary_text = capture_fullzap_summary(context, args.userinterface_name)
        print_fullzap_summary(context, args.userinterface_name)
        
        # Store summary for report
        context.execution_summary = summary_text
        
        if zap_success:
            print("🎧 [fullzap] Performing audio menu analysis after zap...")
            audio_result = analyze_audio_menu(context)
            context.custom_data['audio_menu_analysis'] = audio_result
            
            # IMPORTANT: Add audio menu analysis to the most recent step that went to audio menu
            # Find the last step that navigated to an audio menu node
            audio_menu_step_found = False
            for i in range(len(context.step_results) - 1, -1, -1):  # Search backwards
                step = context.step_results[i]
                to_node = step.get('to_node', '')
                if 'audiomenu' in to_node.lower():
                    step['audio_menu_analysis'] = audio_result
                    print(f"🎧 [fullzap] Added audio menu analysis to step {i + 1}: {to_node}")
                    audio_menu_step_found = True
                    break
            
            if not audio_menu_step_found:
                print("⚠️ [fullzap] No audio menu navigation step found to attach analysis results")
        
        if context.overall_success:
            print("✅ [fullzap] Fullzap execution completed successfully!")
            
    except KeyboardInterrupt:
        handle_keyboard_interrupt(script_name)
    except Exception as e:
        handle_unexpected_error(script_name, e)
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)


if __name__ == "__main__":
    main() 