"""Control tool definitions for device control and locking"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get control-related tool definitions"""
    return [
        {
            "name": "take_control",
            "description": """CALL THIS FIRST before ANY navigation or device actions!

Takes exclusive control of a device and builds navigation cache.

MANDATORY FIRST STEP for:
- navigate_to_node (will fail with "cache not ready" without this)
- execute_device_action (when working with navigation tree/userinterface)
- Any exploration or navigation workflow

WORKFLOW (ALWAYS FOLLOW THIS ORDER):
1. take_control(tree_id='...', host_name='...', device_id='...')  ← CALL FIRST!
2. Do your work (navigate_to_node, execute_device_action, etc.)
3. [Optional] release_control(host_name='...', device_id='...')

Example:
  # STEP 1: Take control FIRST
  take_control(tree_id='abc-123', host_name='sunri-pi1', device_id='device1')
  
  # STEP 2: Now you can navigate
  navigate_to_node(target_node_label='shop', ...)
  
  # STEP 3: (Optional) Release when completely done
  release_control(host_name='sunri-pi1', device_id='device1')""",
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

