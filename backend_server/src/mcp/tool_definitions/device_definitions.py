"""Device tool definitions for device information and management"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get device-related tool definitions"""
    return [
        {
            "name": "list_hosts",
            "description": """List all registered hosts with their device counts.

Use this tool FIRST to discover available hosts before calling get_device_info.
Returns host names, URLs, status, and device counts.

Example:
  list_hosts()
  # Returns: sunri-pi1 (3 devices), prod-host (2 devices)""",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_device_info",
            "description": """Get device information from hosts.

If host_name is omitted, returns devices from ALL hosts.
If host_name is provided, returns devices only from that host.

Example:
  get_device_info()  # All devices from all hosts
  get_device_info(host_name='sunri-pi1')  # Only devices from sunri-pi1""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Specific device ID, or omit for all devices"},
                    "host_name": {"type": "string", "description": "Filter by host name (optional - omit for all hosts)"}
                },
                "required": []
            }
        },
        {
            "name": "get_compatible_hosts",
            "description": """Get hosts and devices compatible with a userinterface

CRITICAL: Use this tool BEFORE execute_device_action, navigate_to_node, 
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

