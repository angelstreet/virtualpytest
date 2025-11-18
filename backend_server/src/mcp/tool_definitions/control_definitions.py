"""Control tool definitions for device control and locking"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get control-related tool definitions"""
    return [
        {
            "name": "take_control",
            "description": """🔒 ONLY FOR NAVIGATION: Take control of a device for UI tree navigation

⚠️ This is ONLY required if you plan to use navigate_to_node.
DO NOT call this for simple actions like execute_device_action.

This locks the device and builds navigation cache for the specified tree_id.

WORKFLOW (for navigation only):
1. Call take_control(device_id='device1', tree_id='<tree-id>') ONCE
2. Call navigate_to_node multiple times
3. Done - no need to release

For simple actions (swipe, click, type), just call execute_device_action directly.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name where device is connected (use get_compatible_hosts to discover)"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "tree_id": {"type": "string", "description": "Navigation tree ID - REQUIRED for navigation"}
                },
                "required": []
            }
        }
    ]

