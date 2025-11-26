"""Device tool definitions for device information and management"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get device-related tool definitions"""
    return [
        {
            "name": "get_device_info",
            "description": "Get device information, capabilities, and controller status.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Specific device ID, or omit for all devices"},
                    "host_name": {"type": "string", "description": "Host name to query (use get_compatible_hosts to discover)"}
                },
                "required": []
            }
        },
        {
            "name": "get_compatible_hosts",
            "description": """Get hosts and devices compatible with a userinterface

⚠️ CRITICAL: This is your FIRST step. Call this ONCE at the start of your session.

📋 SAVE AND REUSE these values in ALL subsequent calls:
- host_name: Required for execute_edge, create_edge, dump_ui_elements, etc.
- device_id: Required for device interactions
- tree_id: Required for navigation operations

Example workflow:
  # Step 1: Get session context (ONCE)
  hosts = get_compatible_hosts(userinterface_name='sauce-demo')
  host_name = hosts['recommended_host']      # Save this!
  device_id = hosts['recommended_device']    # Save this!
  tree_id = hosts['tree_id']                 # Save this!
  
  # Step 2+: Reuse in ALL subsequent calls
  execute_edge(..., host_name=host_name, device_id=device_id)
  dump_ui_elements(host_name=host_name, device_id=device_id)
  navigate_to_node(..., host_name=host_name, device_id=device_id)""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "userinterface_name": {"type": "string", "description": "Interface name (e.g., 'sauce-demo') (REQUIRED)"}
                },
                "required": ["userinterface_name"]
            }
        },
        {
            "name": "get_execution_status",
            "description": "Poll async execution status for actions, testcases, or AI operations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "Execution ID from async operation"},
                    "operation_type": {
                        "type": "string",
                        "description": "Operation type (action, testcase, ai)",
                        "enum": ["action", "testcase", "ai"]
                    }
                },
                "required": ["execution_id"]
            }
        }
    ]

