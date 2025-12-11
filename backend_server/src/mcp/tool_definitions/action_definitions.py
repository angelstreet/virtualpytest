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

PREREQUISITE: Device must be registered with the host.

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
            "description": """Execute actions on device (ADB, web, remote)

CLICK STRATEGY BY PLATFORM:
- MOBILE (android_mobile/android_tv): ONLY click_element with text parameter, NOT coordinates. Do not use IDs. Use Tap coordinates as a last resort.
- WEB (web/desktop): Use click_element_by_id for stable selectors, or click_element(text) as fallback.

PREREQUISITES:
1. host_name REQUIRED - use get_compatible_hosts() first
2. For navigation: call take_control() once before any operations

MOBILE COMMANDS (android_mobile/android_tv):
- click_element(element_id="Search") - Click by text, resource_id, or content_desc (searches all)
- press_key(key="BACK") - Press hardware key
- swipe_up, swipe_down, swipe_left, swipe_right - Swipe gestures
- launch_app(package="com.example.app") - Launch application
- input_text(text="hello") - Type text into focused field

WEB COMMANDS (web/desktop):
- click_element_by_id(element_id="btn") - Click by CSS selector or ID
- click_element(text="Search") - Click by visible text
- input_text(selector="#field", text="...") - Type into specific field
- press_key(key="Enter") - Press keyboard key

WAIT TIMES (in params):
- launch_app: 8000ms, click_element: 2000ms, press_key: 1500ms, input_text: 1000ms

Examples:
  # Mobile click by text/id/desc (searches content_desc, resource_id, text)
  {"command": "click_element", "params": {"element_id": "Shop", "wait_time": 2000}}
  
  # Web click by ID
  {"command": "click_element_by_id", "params": {"element_id": "login-btn", "wait_time": 2000}}
  
  # Press key
  {"command": "press_key", "params": {"key": "BACK", "wait_time": 1500}}

Use list_actions() to see all available commands.""",
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

