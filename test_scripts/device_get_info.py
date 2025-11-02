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
_script_args = [
    '--userinterface_name:str:iad_gui',  # UI navigation required
    '--node:str:info'                     # Target node - defaults to 'info'
]


# ❌ REMOVED: Direct controller access - use VerificationExecutor instead
# The orchestrator pattern handles controller routing automatically


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
    # Order matters: more specific patterns should come before generic ones
    patterns = {
        "serial_number": [
            r"cable\s+modem\s+serial\s+number\s*[:\s]+([A-Z0-9-]+)",
            r"serial\s*(?:number|#)?\s*[:\s]+([A-Z0-9-]+)",
            r"s/n\s*[:\s]+([A-Z0-9-]+)",
        ],
        "mac_address": [
            r"cable\s+mac\s+address\s*[:\s]+([0-9A-Fa-f:]{17})",
            r"mac\s*(?:address)?\s*[:\s]+([0-9A-Fa-f:]{17})",
            r"ethernet\s*[:\s]+([0-9A-Fa-f:]{17})"
        ],
        "software_version": [
            r"software\s+version\s*[:\s]+([A-Z0-9._-]+)",
            r"firmware\s*(?:version)?\s*[:\s]+([A-Z0-9._-]+)"
        ],
        "hardware_version": [
            r"hardware\s+version\s*[:\s]+([\d.]+)",
            r"hw\s+version\s*[:\s]+([\d.]+)"
        ],
        "docsis_version": [
            r"docsis\s+([\d.]+)",
            r"standard\s+specification\s+compliant\s*[:\s]+docsis\s+([\d.]+)"
        ],
        "system_uptime": [
            r"system\s+up\s+time\s*[:\s]+(.+?)(?:\s*$|\s*\n)",
            r"uptime\s*[:\s]+(.+?)(?:\s*$|\s*\n)"
        ],
        "network_access": [
            r"network\s+access\s*[:\s]+(\w+)",
            r"access\s*[:\s]+(\w+)"
        ],
        "ipv4_address": [
            r"ipv4\s+address\s*[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
            r"wan\s+ip\s*(?:address)?\s*[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
            r"ip\s*(?:address)?\s*[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
        ],
        "default_gateway": [
            r"default\s+gateway\s*[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
            r"gateway\s*[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        ],
        "dns_servers": [
            r"ipv4\s+dns\s+servers\s*[:\s]+([\d.,\s]+)",
            r"dns\s+servers?\s*[:\s]+([\d.,\s]+)",
            r"primary\s+dns\s*[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        ],
        "ipv4_lease_time": [
            r"ipv4\s+lease\s+time\s*[:\s]+(.+?)(?:\s*$|\s*\n)",
            r"dhcp\s+lease\s+time\s*[:\s]+(.+?)(?:\s*$|\s*\n)"
        ],
        "ipv4_lease_expire": [
            r"ipv4\s+lease\s+expire\s*[:\s]+(.+?)(?:\s*$|\s*\n)",
            r"lease\s+expir(?:y|e|ation)\s*[:\s]+(.+?)(?:\s*$|\s*\n)"
        ],
        "model_number": [
            r"model\s*(?:number|#)?\s*[:\s]+([A-Z0-9-]+)",
        ]
    }
    
    # Extract text content from all elements
    print(f"📝 [get_info:parse] Checking {len(elements)} elements for device info patterns...")
    
    # STEP 1: Full raw dump
    import json
    print(f"\n{'=' * 100}")
    print(f"🔍 STEP 1: FULL RAW DUMP (Complete JSON)")
    print(f"{'=' * 100}")
    print(json.dumps(elements, indent=2))
    print(f"{'=' * 100}\n")
    
    # STEP 2: Pattern matching (silent, only show matches)
    print(f"{'=' * 100}")
    print(f"✅ STEP 2: MATCHED FIELDS")
    print(f"{'=' * 100}")
    
    for idx, element in enumerate(elements):
        text_content = element.get('textContent', '').strip()
        if not text_content or len(text_content) < 3:
            continue
            
        # Store raw text for debugging
        device_info["raw_text_elements"].append(text_content)
        
        # Try to match each pattern (silent)
        for field_name, field_patterns in patterns.items():
            if field_name in device_info["extracted_fields"]:
                continue  # Already found this field
                
            for pattern in field_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    device_info["extracted_fields"][field_name] = match.group(1).strip()
                    print(f"✅ {field_name}: {match.group(1).strip()}")
                    break
    
    print(f"{'=' * 100}")
    print(f"\n📊 Summary: Checked {len(device_info['raw_text_elements'])} text elements")
    print(f"📊 [get_info:parse] Extracted {len(device_info['extracted_fields'])} fields: {list(device_info['extracted_fields'].keys())}")
    
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
    Dump all elements from the current page using the device's web controller directly.
    
    Args:
        device: Device object with web controller
        
    Returns:
        Dict with success status and elements list
    """
    print(f"📋 [get_info:dump] Dumping page elements via web controller...")
    
    try:
        # Get web controller directly from device
        web_controller = device._get_controller('web')
        
        if not web_controller:
            return {
                'success': False,
                'error': 'No web controller available on this device',
                'elements': []
            }
        
        # Call dump_elements directly on the web controller
        result = web_controller.dump_elements(element_types='all', include_hidden=False)
        
        if result.get('success'):
            elements = result.get('elements', [])
            summary = result.get('summary', {})
            
            print(f"📋 [get_info:dump] Found {summary.get('total_count', len(elements))} elements")
            print(f"📋 [get_info:dump] Page: {summary.get('page_title', 'Unknown')} - {summary.get('page_url', 'Unknown')}")
            
            return {
                'success': True,
                'elements': elements,
                'summary': summary
            }
        else:
            error_msg = result.get('error', 'Unknown error')
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
        userinterface_name=context.userinterface_name,  # MANDATORY parameter
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
    
    action_result = ExecutionOrchestrator.execute_actions(
        device=device,
        actions=[action],
        team_id=context.team_id,
        context=context
    )
    
    if not action_result.get('success'):
        error_msg = action_result.get('error', 'getMenuInfo action failed')
        print(f"⚠️  [get_info] Warning: {error_msg}")
        context.overall_success = True
        summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, already_at_destination)
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
        summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, already_at_destination)
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
        "userinterface_name": args.userinterface_name,
        "element_count": element_count,
    }
    
    print(f"\n✅ [get_info] Device info extraction complete!")
    print(f"✅ [get_info] Metadata will be saved to script_results.metadata column")
    print(f"✅ [get_info] Structure: metadata['info'] = {list(parsed_data.keys())}")
    
    # Set overall_success BEFORE capturing summary
    context.overall_success = True
    
    # Capture summary with metadata for display
    summary_text = capture_navigation_summary(context, args.userinterface_name, target_node, already_at_destination, context.metadata)
    context.execution_summary = summary_text
    
    return True

# Assign script arguments to main function
main._script_args = _script_args

if __name__ == "__main__":
    main()

