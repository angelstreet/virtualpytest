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

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, execute_zaps, get_context, get_args, capture_fullzap_summary

def create_zap_controller(context: ScriptExecutionContext) -> ZapController:
    """Create a ZapController with direct Python video analysis capabilities"""
    print("🔧 [fullzap] Creating ZapController with direct Python video analysis...")
    
    # Create ZapController - it will use get_controller() internally
    zap_controller = ZapController()
    
    print("✅ [fullzap] ZapController ready with direct Python analysis capabilities")
    
    return zap_controller

def execute_zap_actions(context: ScriptExecutionContext, action_edge, action_command: str, max_iteration: int, zap_controller: ZapController, goto_live: bool = True):
    """Execute zap actions using ZapController and StepExecutor for step recording"""
    print(f"⚡ [fullzap] Executing {max_iteration} zap iterations with step recording...")
    print(f"🎯 [fullzap] Audio menu analysis will be performed after zap execution")
    
    # Create StepExecutor for recording steps
    step_executor = StepExecutor(context)
    
    # Execute zap iterations using ZapController (without step recording)
    # ZapController will handle analysis but not step recording
    success = zap_controller.execute_zap_iterations(context, action_edge, action_command, max_iteration, goto_live)
    
    # Since ZapController no longer records steps, we need to create them based on the results
    # The ZapController stores analysis results in context.custom_data, so we can use those
    # to create steps retroactively
    
    # For now, create a single summary step for all zap iterations
    # This maintains the same reporting structure while using the new step system
    zap_result = {
        'success': success,
        'execution_time_ms': context.custom_data.get('total_action_time', 0),
        'motion_details': context.custom_data.get('motion_analysis', {}),
        'subtitle_details': context.custom_data.get('subtitle_analysis', {}),
        'audio_details': context.custom_data.get('audio_analysis', {}),
        'zapping_details': context.custom_data.get('zapping_analysis', {}),
        'error': None if success else 'Zap execution failed'
    }
    
    # Create a summary step for all zap iterations
    zap_step = step_executor.create_zap_step(
        iteration=max_iteration, 
        action_command=action_command, 
        analysis_result=zap_result,
        max_iterations=max_iteration
    )
    
    # Record the zap summary step
    context.record_step_dict(zap_step)
    
    return success


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
            lines.append(f"   ⬛ Average blackscreen/freeze duration: {avg_blackscreen_duration:.2f}s")
            
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

@script("fullzap", "Execute zap iterations with analysis")
def main():
    """Main function to optionally navigate to live and execute zap action multiple times"""
    args = get_args()
    context = get_context()
    
    nav_msg = "with navigation to live" if args.goto_live else "without navigation to live"
    print(f"🎯 [fullzap] Starting execution of action '{args.action}' {args.max_iteration} times {nav_msg} for: {args.userinterface_name}")
    
    # Set userinterface_name in context for zap database recording
    context.userinterface_name = args.userinterface_name
    
    print(f"🔢 [fullzap] Max iterations: {args.max_iteration}")
    print(f"🗺️ [fullzap] Goto live: {args.goto_live}")
    print(f"📱 [fullzap] Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    
    # Execute zap actions using helper function
    success = execute_zaps(
        max_iterations=args.max_iteration,
        action=args.action,
        goto_live=args.goto_live,
        audio_analysis=args.audio_analysis
    )
    
    if success:
        # Print zap summary table from database
        from backend_host.src.lib.utils.zap_controller import ZapController
        zap_controller = ZapController()
        zap_controller.print_zap_summary_table(context)
        
        # Capture and store summary for report
        summary_text = capture_fullzap_summary(args.userinterface_name)
        context.execution_summary = summary_text
        
        print("✅ [fullzap] Fullzap execution completed successfully!")
    
    return success


if __name__ == "__main__":
    main() 