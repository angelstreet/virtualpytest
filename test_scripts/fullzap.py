#!/usr/bin/env python3

import sys
import os
import time
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args

def execute_zap_actions(context, action_edge, action_command: str, max_iteration: int, zap_controller, goto_live: bool = True):
    from shared.src.lib.executors.step_executor import StepExecutor
    
    step_executor = StepExecutor(context)
    success = zap_controller.execute_zap_iterations(context, action_edge, action_command, max_iteration, goto_live)
    
    zap_result = {
        'success': success,
        'execution_time_ms': context.custom_data.get('total_action_time', 0),
        'motion_details': context.custom_data.get('motion_analysis', {}),
        'subtitle_details': context.custom_data.get('subtitle_analysis', {}),
        'audio_details': context.custom_data.get('audio_analysis', {}),
        'zapping_details': context.custom_data.get('zapping_analysis', {}),
        'error': None if success else 'Zap execution failed'
    }
    
    zap_step = step_executor.create_zap_step(
        iteration=max_iteration, 
        action_command=action_command, 
        analysis_result=zap_result,
        max_iterations=max_iteration
    )
    
    context.record_step_dict(zap_step)
    return success




def print_fullzap_summary(context, userinterface_name: str):
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

def execute_zap_iterations(max_iterations: int, action: str = 'live_chup', goto_live: bool = True, audio_analysis: bool = False) -> bool:
    from shared.src.lib.executors.zap_executor import ZapExecutor
    from shared.src.lib.executors.script_decorators import navigate_to
    from backend_host.src.lib.utils.audio_menu_analyzer import analyze_audio_menu
    
    context = get_context()
    zap_controller = ZapExecutor(context.selected_device)
    
    if "mobile" in context.selected_device.device_model.lower():
        target_node = "live_fullscreen"
        mapped_action = f"live_fullscreen_{action.split('_')[-1]}" if action.startswith("live_") else action
    else:
        target_node = "live"
        mapped_action = action
    
    if goto_live:
        success = navigate_to(target_node)
        if not success:
            context.error_message = f"Failed to navigate to {target_node}"
            return False
    else:
        # Find target node in loaded tree
        target_node_obj = None
        for node in context.nodes:
            if node.get('label') == target_node:
                target_node_obj = node
                break
        if target_node_obj:
            context.current_node_id = target_node_obj.get('node_id')
    
    context.custom_data['action_command'] = mapped_action
    context.audio_menu_node = "live_fullscreen_audiomenu" if "mobile" in context.selected_device.device_model.lower() else "live_audiomenu"
    
    # Find edge for the mapped action
    action_edge = None
    if context.current_node_id:
        # Use NavigationExecutor's method to find edge
        nav_executor = context.selected_device.navigation_executor
        action_edge = nav_executor.find_edge_by_target_label(context.current_node_id, context.edges, context.nodes, mapped_action)
    if not action_edge:
        context.error_message = f"No edge found from current node to '{mapped_action}'"
        return False
    
    try:
        zap_success = execute_zap_actions(context, action_edge, mapped_action, max_iterations, zap_controller, goto_live)
    except Exception as e:
        zap_success = False
    
    if zap_success and audio_analysis:
        device_model = context.selected_device.device_model if context.selected_device else 'unknown'
        if device_model != 'host_vnc':
            audio_result = analyze_audio_menu(context)
            context.custom_data['audio_menu_analysis'] = audio_result
    
    return zap_success

@script("fullzap", "Execute zap iterations with analysis")
def main():
    args = get_args()
    context = get_context()
    context.userinterface_name = args.userinterface_name
    
    success = execute_zap_iterations(
        max_iterations=args.max_iteration,
        action=args.action,
        goto_live=args.goto_live,
        audio_analysis=args.audio_analysis
    )
    
    if success:
        from shared.src.lib.utils.zap_utils import print_zap_summary_table
        print_zap_summary_table(context)
    
    return success


if __name__ == "__main__":
    main() 