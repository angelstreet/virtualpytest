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
    from shared.src.lib.executors.zap_executor import ZapExecutor
    from backend_host.src.lib.utils.audio_menu_analyzer import analyze_audio_menu
    from shared.src.lib.executors.script_decorators import _get_context
    
    device = get_device()
    context = _get_context()  # Only for zap-specific data storage
    zap_controller = ZapExecutor(device)
    
    # Determine target based on device (same logic as goto_live.py)
    if "mobile" in device.device_model.lower():
        target_node = "live_fullscreen"
        mapped_action = f"live_fullscreen_{action.split('_')[-1]}" if action.startswith("live_") else action
    else:
        target_node = "live"
        mapped_action = action
    
    # Navigate to live using public interface (same as goto.py)
    if goto_live:
        success = navigate_to(target_node)
        if not success:
            print(f"❌ [fullzap] Failed to navigate to {target_node}")
            return False
        print(f"✅ [fullzap] Navigated to {target_node}")
    
    # Execute zap actions (this is the fullzap-specific part)
    context.custom_data['action_command'] = mapped_action
    context.audio_menu_node = "live_fullscreen_audiomenu" if "mobile" in device.device_model.lower() else "live_audiomenu"
    
    try:
        # Get the action edge for the zap action
        context = _get_context()
        
        # Find the action edge that matches our mapped_action
        action_edge = None
        for edge in context.edges:
            edge_actions = edge.get('actions', [])
            for action in edge_actions:
                if action.get('action_command') == mapped_action:
                    action_edge = edge
                    break
            if action_edge:
                break
        
        if not action_edge:
            print(f"❌ [fullzap] No action edge found for command: {mapped_action}")
            zap_success = False
        else:
            # Use ZapExecutor with the found action edge
            zap_success = zap_controller.execute_zap_iterations(context, action_edge, mapped_action, max_iteration, goto_live)
    except Exception as e:
        print(f"❌ [fullzap] Zap execution failed: {e}")
        zap_success = False
    
    # Audio analysis if requested
    if zap_success and audio_analysis and device.device_model != 'host_vnc':
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
    
    # Print summary (zap-specific reporting)
    from shared.src.lib.executors.script_decorators import _get_context
    from shared.src.lib.utils.zap_utils import print_zap_summary_table
    
    context = _get_context()
    print_zap_summary_table(context)
    print_fullzap_summary(context, args.userinterface_name)
    
    return success

# Define script-specific arguments
main._script_args = ['--max-iteration:int:50', '--action:str:live_chup', '--goto-live:bool:true', '--audio-analysis:bool:false']

if __name__ == "__main__":
    main() 