#!/usr/bin/env python3

import sys
import os
import time
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_device, get_args, get_context

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
    
    device = get_device()
    context = get_context()
    args = get_args()
    
    # ZapExecutor handles complete zap workflow
    zap_executor = ZapExecutor(device, context.userinterface)
    return zap_executor.execute_zap_iterations(action, max_iteration, goto_live, audio_analysis)

@script("fullzap", "Execute zap iterations with analysis")
def main():
    args = get_args()
    context = get_context()
    device = get_device()
    
    # Load navigation tree (required for ZapExecutor navigation)
    nav_result = device.navigation_executor.load_navigation_tree(
        context.userinterface, 
        context.team_id
    )
    if not nav_result['success']:
        context.error_message = f"Navigation tree loading failed: {nav_result.get('error', 'Unknown error')}"
        return False
    
    context.tree_id = nav_result['tree_id']
    
    success = execute_zap_iterations(
        max_iteration=args.max_iteration,
        action=args.action,
        goto_live=args.goto_live,
        audio_analysis=args.audio_analysis
    )
    
    # Print zap summary table and fullzap summary
    from shared.src.lib.utils.zap_utils import print_zap_summary_table
    
    context = get_context()
    print_zap_summary_table(context)  # This was removed - restored!
    print_fullzap_summary(context, context.userinterface)
    
    return success

# Script arguments (framework params have defaults, script params are specific)
main._script_args = [
    '--userinterface:str:horizon_android_mobile',  # Framework param with default
    '--max-iteration:int:3', 
    '--action:str:live_chup', 
    '--goto-live:bool:true', 
    '--audio-analysis:bool:false'
]

if __name__ == "__main__":
    main() 