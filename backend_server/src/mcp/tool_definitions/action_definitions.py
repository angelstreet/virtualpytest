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

MOBILE: click_element(element_id="Text"), press_key, swipe_up/down/left/right, launch_app, input_text
WEB: click_element_by_id(element_id="selector"), click_element(text), input_text, press_key""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier (REQUIRED) - Get from get_compatible_hosts() or list_devices()"},
                    "host_name": {"type": "string", "description": "Host name where device is connected (REQUIRED) - Get from get_compatible_hosts()"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "actions": {
                        "type": "array",
                        "description": "Array of action objects. Each action must have a 'command' field. Use list_actions() to discover available commands and their required parameters.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "Action command to execute (e.g., 'launch_app', 'click_element', 'swipe', 'type_text', 'press_key'). Call list_actions() first to see all available commands."
                                },
                                "params": {
                                    "type": "object",
                                    "description": "Parameters for the command. Structure varies by command - use list_actions() to see required params."
                                },
                                "delay": {
                                    "type": "number",
                                    "description": "Optional delay in seconds after executing this action"
                                }
                            },
                            "required": ["command"]
                        }
                    },
                    "retry_actions": {
                        "type": "array",
                        "description": "Actions to retry on failure",
                        "items": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string"},
                                "params": {"type": "object"},
                                "delay": {"type": "number"}
                            },
                            "required": ["command"]
                        }
                    },
                    "failure_actions": {
                        "type": "array",
                        "description": "Actions to execute on failure",
                        "items": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string"},
                                "params": {"type": "object"},
                                "delay": {"type": "number"}
                            },
                            "required": ["command"]
                        }
                    }
                },
                "required": ["device_id", "host_name", "actions"]
            }
        }
    ]

