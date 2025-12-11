"""Action tool definitions for device actions and commands"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get action-related tool definitions"""
    return [
        {
            "name": "list_actions",
            "description": """List available actions for a device

Returns categorized list of actions with commands and parameters.
Useful for discovering what actions can be executed on a device.

Device Model Specific:
- android_mobile/android_tv: Returns mobile commands (click_element with text only, press_key, swipe, etc)
- web/desktop: Returns web automation commands (click_element_by_id, click_element, input_text, etc)

Example:
  # First get compatible host
  hosts = get_compatible_hosts(userinterface_name='your-interface')
  
  list_actions(
    device_id=hosts['recommended_device'],
    host_name=hosts['recommended_host']
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "host_name": {"type": "string", "description": "Host name where device is connected"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                },
                "required": ["host_name"]
            }
        },
        {
            "name": "execute_device_action",
            "description": """Execute actions on device. Call list_actions() first to get available commands.

REQUIRED: device_id, host_name (from get_compatible_hosts()), actions array.

MOBILE: click_element(element_id="Text", "wait_time": 2000), press_key, swipe_up/down/left/right, launch_app, input_text
WEB: click_element_by_id(element_id="selector", "wait_time": 2000), click_element(text), input_text, press_key

params.wait_time (ms): wait after action. Default 2000ms if not specified.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier (REQUIRED)"},
                    "host_name": {"type": "string", "description": "Host name (REQUIRED)"},
                    "team_id": {"type": "string", "description": "Team ID (optional)"},
                    "actions": {
                        "type": "array",
                        "description": "Action objects with command and params. Include wait_time in params (default 2000ms).",
                        "items": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string", "description": "Action command"},
                                "params": {"type": "object", "description": "Command params. Include wait_time (ms), default 2000"}
                            },
                            "required": ["command"]
                        }
                    },
                    "retry_actions": {
                        "type": "array",
                        "description": "Retry actions on failure",
                        "items": {"type": "object", "properties": {"command": {"type": "string"}, "params": {"type": "object"}}, "required": ["command"]}
                    },
                    "failure_actions": {
                        "type": "array",
                        "description": "Actions on failure",
                        "items": {"type": "object", "properties": {"command": {"type": "string"}, "params": {"type": "object"}}, "required": ["command"]}
                    }
                },
                "required": ["device_id", "host_name", "actions"]
            }
        }
    ]

