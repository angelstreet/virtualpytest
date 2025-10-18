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
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device


def parse_device_info_from_elements(elements: List[Dict[str, Any]], device_model: str) -> Dict[str, Any]:
    """
    Parse device information from dumped elements.
    This function extracts common device info fields like serial number, build version, etc.
    
    Args:
        elements: List of dumped elements from the page
        device_model: Device model to help determine parsing strategy
        
    Returns:
        Dict containing parsed device information
    """
    device_info = {
        "device_model": device_model,
        "extracted_fields": {},
        "raw_text_elements": []
    }
    
    # Common patterns for device info fields
    patterns = {
        "serial_number": [
            r"serial\s*(?:number|#)?[:\s]+([A-Z0-9-]+)",
            r"s/n[:\s]+([A-Z0-9-]+)",
            r"serial[:\s]+([A-Z0-9-]+)"
        ],
        "build_version": [
            r"build\s*(?:version)?[:\s]+([\d.]+[a-zA-Z0-9.-]*)",
            r"version[:\s]+([\d.]+[a-zA-Z0-9.-]*)",
            r"sw\s*version[:\s]+([\d.]+[a-zA-Z0-9.-]*)"
        ],
        "software_version": [
            r"software\s*(?:version)?[:\s]+([\d.]+[a-zA-Z0-9.-]*)",
            r"firmware[:\s]+([\d.]+[a-zA-Z0-9.-]*)"
        ],
        "hardware_version": [
            r"hardware\s*(?:version)?[:\s]+([\d.]+[a-zA-Z0-9.-]*)",
            r"hw\s*version[:\s]+([\d.]+[a-zA-Z0-9.-]*)"
        ],
        "model_number": [
            r"model\s*(?:number|#)?[:\s]+([A-Z0-9-]+)",
            r"model[:\s]+([A-Z0-9-]+)"
        ],
        "mac_address": [
            r"mac\s*(?:address)?[:\s]+([0-9A-Fa-f:]{17})",
            r"ethernet[:\s]+([0-9A-Fa-f:]{17})"
        ],
        "ip_address": [
            r"ip\s*(?:address)?[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
        ]
    }
    
    # Extract text content from all elements
    for element in elements:
        text_content = element.get('textContent', '').strip()
        if not text_content or len(text_content) < 3:
            continue
            
        # Store raw text for debugging
        device_info["raw_text_elements"].append(text_content)
        
        # Try to match each pattern
        for field_name, field_patterns in patterns.items():
            if field_name in device_info["extracted_fields"]:
                continue  # Already found this field
                
            for pattern in field_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    device_info["extracted_fields"][field_name] = match.group(1).strip()
                    print(f"📝 [get_info:parse] Found {field_name}: {match.group(1).strip()}")
                    break
    
    # Add metadata about extraction
    device_info["extraction_summary"] = {
        "total_elements": len(elements),
        "text_elements_checked": len(device_info["raw_text_elements"]),
        "fields_extracted": len(device_info["extracted_fields"]),
        "fields_found": list(device_info["extracted_fields"].keys())
    }
    
    return device_info


def dump_page_elements(device) -> Dict[str, Any]:
    """
    Dump all elements from the current page using the device's action executor.
    
    Args:
        device: Device object with action_executor
        
    Returns:
        Dict with success status and elements list
    """
    print(f"📋 [get_info:dump] Dumping page elements via action_executor...")
    
    try:
        # Build action list (execute_actions expects a list)
        actions = [{
            'command': 'dump_elements',
            'params': {
                'element_types': 'all',
                'include_hidden': False
            },
            'action_type': 'web'
        }]
        
        # Execute actions using device's action_executor
        # execute_actions returns a result dict with 'actions' key containing results array
        result = device.action_executor.execute_actions(actions)
        
        # Check if execution was successful
        if result.get('success') and result.get('results'):
            action_result = result['results'][0]  # Get first action result
            
            if action_result.get('success'):
                # Extract elements from the action result
                elements = action_result.get('elements', [])
                summary = action_result.get('summary', {})
                
                print(f"📋 [get_info:dump] Found {summary.get('total_count', len(elements))} elements")
                print(f"📋 [get_info:dump] Page: {summary.get('page_title', 'Unknown')} - {summary.get('page_url', 'Unknown')}")
                
                return {
                    'success': True,
                    'elements': elements,
                    'summary': summary
                }
            else:
                error_msg = action_result.get('error', 'Unknown error')
                print(f"❌ [get_info:dump] Action failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elements': []
                }
        else:
            error_msg = result.get('error', 'Batch execution failed')
            print(f"❌ [get_info:dump] Failed to dump elements: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'elements': []
            }
            
    except Exception as e:
        error_msg = f"Exception during element dump: {str(e)}"
        print(f"❌ [get_info:dump] {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': error_msg,
            'elements': []
        }


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
    
    # Add device info extraction summary
    if metadata and 'device_info' in metadata:
        device_info = metadata['device_info']
        extraction_summary = device_info.get('extraction_summary', {})
        extracted_fields = device_info.get('extracted_fields', {})
        
        lines.append(f"\n📊 DEVICE INFO EXTRACTION")
        lines.append(f"   Elements scanned: {extraction_summary.get('total_elements', 0)}")
        lines.append(f"   Fields extracted: {extraction_summary.get('fields_extracted', 0)}")
        
        if extracted_fields:
            lines.append(f"\n📝 EXTRACTED DEVICE DATA:")
            for field_name, field_value in extracted_fields.items():
                lines.append(f"   • {field_name}: {field_value}")
        else:
            lines.append(f"   ⚠️  No device info fields extracted (check info page format)")
    
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
        args.userinterface_name, 
        context.team_id
    )
    if not nav_result['success']:
        context.error_message = f"Navigation tree loading failed: {nav_result.get('error', 'Unknown error')}"
        return False
    
    context.tree_id = nav_result['tree_id']
    
    # Execute navigation using NavigationExecutor directly
    result = device.navigation_executor.execute_navigation(
        tree_id=context.tree_id,
        target_node_label=target_node,
        team_id=context.team_id,
        context=context
    )
    
    success = result.get('success', False)
    if not success:
        context.error_message = result.get('error', 'Navigation failed')
        context.overall_success = False
        summary_text = capture_navigation_summary(context, args.userinterface_name, target_node)
        context.execution_summary = summary_text
        return False
    
    # Navigation successful - now extract device info
    already_at_destination = (len(context.step_results) == 0 and success)
    
    print(f"\n📋 [get_info] ==========================================")
    print(f"📋 [get_info] EXTRACTING DEVICE INFORMATION")
    print(f"📋 [get_info] ==========================================\n")
    
    # Step 1: Dump page elements
    dump_result = dump_page_elements(device)
    
    if not dump_result.get('success'):
        print(f"⚠️  [get_info] Warning: Could not dump page elements: {dump_result.get('error', 'Unknown error')}")
        # Continue anyway - mark as successful navigation but without metadata
        context.overall_success = True
        summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, already_at_destination)
        context.execution_summary = summary_text
        return True
    
    # Step 2: Parse device info from elements
    elements = dump_result.get('elements', [])
    device_info = parse_device_info_from_elements(elements, device.device_model)
    
    # Step 3: Store device info in context.metadata (will be saved to script_results.metadata)
    context.metadata = {
        "device_info": device_info,
        "extraction_timestamp": context.start_time.isoformat() if hasattr(context, 'start_time') else None,
        "page_url": dump_result.get('summary', {}).get('page_url'),
        "page_title": dump_result.get('summary', {}).get('page_title'),
        "device_name": device.device_name,
        "host_name": context.host.host_name,
        "userinterface_name": args.userinterface_name
    }
    
    print(f"\n✅ [get_info] Device info extraction complete!")
    print(f"✅ [get_info] Metadata will be saved to script_results.metadata column")
    print(f"✅ [get_info] Fields extracted: {list(device_info.get('extracted_fields', {}).keys())}")
    
    # Set overall_success BEFORE capturing summary
    context.overall_success = True
    
    # Capture summary with metadata for display
    summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, already_at_destination, context.metadata)
    context.execution_summary = summary_text
    
    return True

# Script arguments (framework params are automatic)
main._script_args = [
    '--node:str:info'           # Script-specific param - defaults to 'info'
]

if __name__ == "__main__":
    main()

