"""Control tool definitions for device control and locking"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get control-related tool definitions"""
    return [
        {
            "name": "take_control",
            "description": """Lock device for navigation or exploration

Takes exclusive control of a device and builds navigation cache.

**CRITICAL: Always call release_control when done!**

WORKFLOW:
1. take_control(tree_id='...', host_name='...', device_id='...')
2. Do your work (navigate_to_node, create_node, execute_device_action, etc.)
3. release_control(host_name='...', device_id='...')  ← DON'T FORGET!

Example:
  take_control(tree_id='abc-123', host_name='pi1', device_id='device1')
  # ... exploration or navigation ...
  release_control(host_name='pi1', device_id='device1')""",
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
        },
        {
            "name": "release_control",
            "description": """Release device control when done

Unlocks the device so others can use it.

**CRITICAL: Always call this after take_control!**

Must be called:
- After exploration is complete
- After navigation session ends
- After any operation that used take_control
- Even if errors occurred (in finally block)

Example:
  # After exploration
  release_control(host_name='pi1', device_id='device1')
  
  # Report results
  "Exploration complete. Created 5 nodes, 4 edges. Device released." """,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name where device is connected"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                },
                "required": ["host_name"]
            }
        }
    ]

