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

⚠️ CRITICAL: Use this tool BEFORE execute_edge, navigate_to_node, 
execute_testcase, or generate_test_graph to find compatible hosts/devices.

This tool automatically filters hosts based on the userinterface's device models
and returns the first compatible host/device for immediate use.

Example:
  get_compatible_hosts(userinterface_name='sauce-demo')
  # Returns: recommended_host='sunri-pi1', recommended_device='device1'""",
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

