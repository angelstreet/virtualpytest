"""Control tool definitions for device control and locking"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get control-related tool definitions"""
    return [
        {
            "name": "take_control",
            "description": """Take exclusive control of a device.

Locks the device for exclusive use to prevent conflicts.
Required before executing any device operations.

USE CASES:
- Execute device actions (click, swipe, type)
- Capture screenshots
- Dump UI elements
- Run verifications
- Navigate through UI (used with navigate_to_node)

WORKFLOW:
1. take_control(host_name='...', userinterface_name='...')  ← Lock device + build navigation cache
2. Do your work (actions, screenshots, navigation)
3. [Optional] release_control(host_name='...', device_id='...')  ← Unlock device

Example:
  # Take control of device with UI interface for navigation
  take_control(host_name='sunri-pi1', device_id='device1', userinterface_name='google_tv')
  
  # Execute operations - navigation cache is ready!
  execute_device_action(...)
  capture_screenshot(...)
  navigate_to_node(userinterface_name='google_tv', target_node_label='home')
  
  # Release when done
  release_control(host_name='sunri-pi1', device_id='device1')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name where device is connected"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "userinterface_name": {"type": "string", "description": "User interface name (e.g. 'google_tv') - required for navigation cache"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                },
                "required": ["host_name", "userinterface_name"]
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

