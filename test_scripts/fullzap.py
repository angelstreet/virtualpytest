#!/usr/bin/env python3

import sys
import os
import time
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, navigate_to, get_device, get_args, _get_context

def print_fullzap_summary(context, userinterface_name: str):
    device = get_device()
    print("\n" + "="*60)
    print(f"🎯 [FULLZAP] EXECUTION SUMMARY")
    print("="*60)
    print(f"📱 Device: {device.device_name} ({device.device_model})")
    print(f"🖥️  Host: {context.host.host_name}")
    print(f"📋 Interface: {userinterface_name}")
    print(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    print(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    print(f"🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if hasattr(context, 'error_message') and context.error_message:
        print(f"❌ Error: {context.error_message}")
    
    print("="*60)

def execute_zap_iterations(max_iteration: int, action: str = 'live_chup', goto_live: bool = True, audio_analysis: bool = False) -> bool:
    from backend_host.src.lib.utils.audio_menu_analyzer import analyze_audio_menu
    
    device = get_device()
    
    # Determine target based on device (same logic as goto_live.py)
    if "mobile" in device.device_model.lower():
        target_node = "live_fullscreen"
        action_node = f"live_fullscreen_{action.split('_')[-1]}" if action.startswith("live_") else action
    else:
        target_node = "live"
        action_node = action
    
    # Navigate to live first (if requested)
    if goto_live:
        success = navigate_to(target_node)
        if not success:
            print(f"❌ [fullzap] Failed to navigate to {target_node}")
            return False
        print(f"✅ [fullzap] Navigated to {target_node}")
    
    # Execute zap iterations by navigating to action node repeatedly
    print(f"🔄 [fullzap] Starting {max_iteration} iterations of '{action_node}'...")
    
    successful_iterations = 0
    for iteration in range(1, max_iteration + 1):
        print(f"🎬 [fullzap] Iteration {iteration}/{max_iteration}: {action_node}")
        
        success = navigate_to(action_node)
        if success:
            successful_iterations += 1
            print(f"✅ [fullzap] Iteration {iteration} completed successfully")
        else:
            print(f"❌ [fullzap] Iteration {iteration} failed")
    
    zap_success = successful_iterations == max_iteration
    print(f"📊 [fullzap] Completed {successful_iterations}/{max_iteration} iterations successfully")
    
    # Audio analysis if requested
    if zap_success and audio_analysis and device.device_model != 'host_vnc':
        context = _get_context()
        context.audio_menu_node = "live_fullscreen_audiomenu" if "mobile" in device.device_model.lower() else "live_audiomenu"
        audio_result = analyze_audio_menu(context)
        context.custom_data['audio_menu_analysis'] = audio_result
    
    return zap_success

@script("fullzap", "Execute zap iterations with analysis")
def main():
    args = get_args()
    
    success = execute_zap_iterations(
        max_iteration=args.max_iteration,
        action=args.action,
        goto_live=args.goto_live,
        audio_analysis=args.audio_analysis
    )
    
    # Print summary
    context = _get_context()
    print_fullzap_summary(context, args.userinterface_name)
    
    return success

# Define script-specific arguments
main._script_args = ['--max-iteration:int:50', '--action:str:live_chup', '--goto-live:bool:true', '--audio-analysis:bool:false']

if __name__ == "__main__":
    main() 