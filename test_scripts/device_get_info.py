#!/usr/bin/env python3
"""
Go to Info Node Script for VirtualPyTest

This script navigates to the 'info' node in the navigation tree (default),
dumps the page elements, extracts device information, and stores it in metadata.

Usage:
    python test_scripts/get_info.py [userinterface_name] [--node <node_name>] [--host <host>] [--device <device>]
    
Examples:
    python test_scripts/get_info.py                           # Goes to 'info' node (default)
    python test_scripts/get_info.py --node info_settings      # Goes to 'info_settings' node
    python test_scripts/get_info.py horizon_android_mobile --node info
    python test_scripts/get_info.py horizon_android_tv --node info_settings --device device2
"""

import sys
import os
import re
from typing import Dict, Any, List

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # test_scripts/ -> project root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device

# Script arguments
# MUST be defined near top of file (within first 300 lines) for script analyzer
# Script arguments (framework params like host/device/userinterface are automatic)
_script_args = [
    '--node:str:info'                     # Target node - defaults to 'info'
]


# ✅ getMenuInfo action handles all parsing via ExecutionOrchestrator
# Controller returns parsed_data directly - no manual parsing needed


def capture_navigation_summary(context, userinterface_name: str, target_node: str, already_at_destination: bool = False, metadata: Dict[str, Any] = None) -> str:
    """Capture navigation summary as text for report"""
    lines = []
    lines.append(f"🎯 [GET_INFO] EXECUTION SUMMARY")
    lines.append(f"📱 Device: {context.selected_device.device_name} ({context.selected_device.device_model})")
    lines.append(f"🖥️  Host: {context.host.host_name}")
    lines.append(f"📋 Interface: {userinterface_name}")
    lines.append(f"🗺️  Target: {target_node}")
    
    if already_at_destination:
        lines.append(f"✅ Already at destination - no navigation needed")
        lines.append(f"📍 Navigation steps: 0 (already verified at target)")
    else:
        lines.append(f"📍 Navigation steps: {len(context.step_results)}")
    
    lines.append(f"⏱️  Total Time: {context.get_execution_time_ms()/1000:.1f}s")
    lines.append(f"📸 Screenshots: {len(context.screenshot_paths)} captured")
    
    # Add device info extraction with parsed data display (like dns_lookuptime.py)
    if metadata and 'info' in metadata:
        parsed_data = metadata['info']
        element_count = metadata.get('element_count', 0)
        
        lines.append(f"\n{'='*80}")
        lines.append(f"📊 DEVICE INFO PARSED RESULTS")
        lines.append(f"{'='*80}")
        lines.append(f"🔍 Elements Scanned: {element_count}")
        lines.append(f"📝 Fields Extracted: {len(parsed_data)}")
        lines.append(f"")
        
        if parsed_data:
            lines.append(f"📋 EXTRACTED DEVICE DATA:")
            for field_name, field_value in parsed_data.items():
                # Format field name nicely (replace underscores with spaces, capitalize)
                display_name = field_name.replace('_', ' ').title()
                lines.append(f"   • {display_name}: {field_value}")
        else:
            lines.append(f"⚠️  No device info fields extracted (check info page format)")
        
        lines.append(f"{'='*80}")
    
    lines.append(f"\n🎯 Result: {'SUCCESS' if context.overall_success else 'FAILED'}")
    
    if context.error_message:
        lines.append(f"❌ Error: {context.error_message}")
    
    return "\n".join(lines)


@script("get_info", "Navigate to info node and extract device information")
def main():
    """Main function: navigate to info node, extract device info, and store in metadata"""
    args = get_args()
    context = get_context()
    target_node = args.node
    device = get_device()
    print(f"🎯 [get_info] Target node: {target_node}")
    print(f"📱 [get_info] Device: {device.device_name} ({device.device_model})")
    
    # Load navigation tree
    nav_result = device.navigation_executor.load_navigation_tree(
        context.userinterface, 
        context.team_id
    )
    if not nav_result['success']:
        context.error_message = f"Navigation tree loading failed: {nav_result.get('error', 'Unknown error')}"
        return False
    
    context.tree_id = nav_result['tree_id']
    
    # Execute navigation using NavigationExecutor directly
    # ✅ Wrap async call with asyncio.run for script context
    import asyncio
    result = asyncio.run(device.navigation_executor.execute_navigation(
        tree_id=context.tree_id,
        userinterface_name=context.userinterface_name,  # MANDATORY parameter
        target_node_label=target_node,
        team_id=context.team_id,
        context=context
    ))
    
    success = result.get('success', False)
    if not success:
        context.error_message = result.get('error', 'Navigation failed')
        context.overall_success = False
        summary_text = capture_navigation_summary(context, context.userinterface, target_node)
        context.execution_summary = summary_text
        return False
    
    # Navigation successful - now extract device info
    already_at_destination = (len(context.step_results) == 0 and success)
    
    print(f"\n📋 [get_info] ==========================================")
    print(f"📋 [get_info] EXTRACTING DEVICE INFORMATION")
    print(f"📋 [get_info] ==========================================\n")
    
    # ✅ Use ExecutionOrchestrator pattern (same as frontend UniversalBlock)
    # Determine verification_type based on device model
    device_model = device.device_model.lower()
    if 'android_mobile' in device_model:
        verification_type = 'adb'  # ADB for Android mobile
    elif 'host_vnc' in device_model:
        verification_type = 'web'  # Playwright for host VNC
    else:
        verification_type = 'text'  # OCR for all others (video, audio, etc.)
    
    print(f"📋 [get_info] Detected verification_type: {verification_type} for device model: {device_model}")
    
    # Build action with verification (same format as frontend UniversalBlock)
    action = {
        'command': 'getMenuInfo',
        'name': 'Get Menu Info',  # EdgeAction requires name field
        'params': {
            'area': None  # Full screen extraction
        },
        'action_type': 'verification',  # ✅ Treat verification as action (routes through orchestrator)
        'verification_type': verification_type,
    }
    
    print(f"📋 [get_info] Device model: {device.device_model}")
    print(f"📋 [get_info] Executing getMenuInfo as action via ExecutionOrchestrator...")
    
    # Execute through ActionExecutor (same as frontend) - orchestrator routes to verification executor
    from backend_host.src.orchestrator.execution_orchestrator import ExecutionOrchestrator
    
    # ✅ Wrap async call with asyncio.run for script context
    action_result = asyncio.run(ExecutionOrchestrator.execute_actions(
        device=device,
        actions=[action],
        team_id=context.team_id,
        context=context
    ))
    
    if not action_result.get('success'):
        error_msg = action_result.get('error', 'getMenuInfo action failed')
        print(f"⚠️  [get_info] Warning: {error_msg}")
        context.overall_success = True
        summary_text = capture_navigation_summary(context, context.userinterface, target_node, already_at_destination)
        context.execution_summary = summary_text
        return True
    
    # Extract output_data from action result (same as frontend UniversalBlock line 368)
    output_data = action_result.get('output_data', {})
    if not output_data:
        # Try results array format
        results = action_result.get('results', [])
        if results:
            output_data = results[0].get('output_data', {})
    
    parsed_data = output_data.get('parsed_data', {})
    element_count = output_data.get('element_count', 0)
    
    if not parsed_data:
        print(f"⚠️  [get_info] Warning: No parsed_data in output")
        context.overall_success = True
        summary_text = capture_navigation_summary(context, context.userinterface, target_node, already_at_destination)
        context.execution_summary = summary_text
        return True
    
    print(f"✅ [get_info] Action completed: {len(parsed_data)} fields extracted from {element_count} elements")
    
    # Step 3: Store to context.metadata['info'] (aligned with testcase builder)
    from datetime import datetime
    extraction_timestamp = datetime.fromtimestamp(context.start_time).isoformat() if hasattr(context, 'start_time') and context.start_time else None
    
    # NESTED structure: parsed_data goes under 'info' key
    context.metadata = {
        "info": parsed_data,  # Controller's parsed_data
        "extraction_timestamp": extraction_timestamp,
        "extraction_method": "script",
        "device_name": device.device_name,
        "device_model": device.device_model,
        "host_name": context.host.host_name,
        "userinterface_name": context.userinterface,
        "element_count": element_count,
    }
    
    print(f"\n✅ [get_info] Device info extraction complete!")
    print(f"✅ [get_info] Metadata will be saved to script_results.metadata column")
    print(f"✅ [get_info] Structure: metadata['info'] = {list(parsed_data.keys())}")
    
    # Set overall_success BEFORE capturing summary
    context.overall_success = True
    
    # Capture summary with metadata for display
    summary_text = capture_navigation_summary(context, context.userinterface, target_node, already_at_destination, context.metadata)
    context.execution_summary = summary_text
    
    return True

# Assign script arguments to main function
main._script_args = _script_args

if __name__ == "__main__":
    main()