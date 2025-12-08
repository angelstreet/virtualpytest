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
- android_mobile/android_tv: Returns ADB/Remote commands (swipe_up, click_element, type_text, key, etc)
- web/desktop: Returns web automation commands (web_click, web_type, etc)

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
            "description": """Execute batch of actions on device (remote commands, ADB, web, desktop)

NO PREREQUISITES - Just call this directly for any device actions.

Executes direct device commands including:
- Launch apps (launch_app)
- UI interactions (swipe, click, type)
- Key presses (press_key)
- And more...

Returns execution_id for async operations - polls automatically until completion.

ELEMENT SELECTION (selector MUST be unique on page):

1. #id (always unique) - PREFERRED
2. //xpath (e.g., //button[@name='login'])
3. [attr] or .class (verify uniqueness first)
4. plain text (fallback, slower, AVOID if text appears multiple times)

UNIQUENESS-FIRST PATTERN (Critical for Reliable Automation):
The AI exploration system demonstrates best practice - ALWAYS verify uniqueness:

1. dump_ui_elements() BEFORE any click action
2. Call analyze_screen_for_action(elements, intent, platform) to get best selector
3. Use returned action params in create_edge

Example workflow:
```
elements = dump_ui_elements(device_id='device1')
action = analyze_screen_for_action(
  elements=elements['elements'],
  intent='search field',
  platform='web'
)
# Returns: {command: 'click_element_by_id', params: {element_id: 'search-field'}, unique: true}

create_edge(actions=[{command: action['command'], params: action['action_params']}])
```

Platform-Specific Priority (shared/src/selector_scoring.py):
- Mobile: ID (resource_id) > CONTENT_DESC > XPATH > TEXT
- Web: ID (#id) > XPATH > TEXT

This pattern prevents ambiguous clicks and ensures automation reliability.
Without analyze_screen_for_action, you risk clicking the WRONG element.

DEVICE-SPECIFIC COMMANDS & PARAMETERS:

MOBILE/ADB (android_mobile/android_tv):
- Commands: launch_app, swipe_up, click_element_by_id (preferred), click_element, input_text, press_key
- input_text: Sends text to focused element (no selector needed)
- Example: {"command": "input_text", "params": {"text": "Hello", "wait_time": 1000}}

WEB (host_vnc/web):
- Commands: click_element, click_element_by_id, input_text, navigate_to_url
- CRITICAL: Web uses DIFFERENT parameter names:
  • click_element_by_id: Use 'element_id' NOT 'text'
  • input_text: Use 'selector' NOT 'element_text'
- Example: {"command": "input_text", "params": {"selector": "#search-field", "text": "Hello", "wait_time": 1000}}

INPUT PATTERN (both platforms):
1. Click field to focus
2. Then input text with appropriate params
See examples below for correct syntax per platform.

CRITICAL - ACTION WAIT TIMES:
Each action MUST include a 'wait_time' field (milliseconds) INSIDE params to wait AFTER execution.

CORRECT: {"command": "launch_app", "params": {"package": "...", "wait_time": 8000}}
WRONG: {"command": "launch_app", "params": {"package": "..."}, "delay": 8000}

Standard Wait Times (milliseconds) - INSIDE params:
- launch_app:     8000  (app initialization)
- click_element:  2000  (screen transition)
- tap_coordinates: 2000  (screen taps)
- press_key (BACK): 1500  (back navigation)
- press_key (other): 1000  (key response)
- type_text:      1000  (input processing)
- video playback: 5000  (player initialization)

Common Examples:

Launch App:
  execute_device_action({
    "device_id": "device1",
    "actions": [{
      "command": "launch_app",
      "params": {"package": "com.netflix.mediaclient", "wait_time": 8000}
    }]
  })

Swipe:
  execute_device_action({
    "actions": [{"command": "swipe_up", "params": {"wait_time": 1000}}]
  })

Click Element (⭐ PREFERRED - Use ID):
  execute_device_action({
    "actions": [{
      "command": "click_element_by_id",
      "params": {"element_id": "customer_login_link", "wait_time": 2000}
    }]
  })

Click Element (fallback - text when no ID available):
  execute_device_action({
    "actions": [{
      "command": "click_element",
      "params": {"text": "Home", "wait_time": 2000}
    }]
  })

Type Text:
  
  WEB (host_vnc/web):
  execute_device_action({
    "actions": [
      {"command": "click_element_by_id", "params": {"element_id": "search-field", "wait_time": 500}},
      {"command": "input_text", "params": {"selector": "#search-field", "text": "Hello", "wait_time": 1000}}
    ]
  })
  
  MOBILE (android_mobile/android_tv):
  execute_device_action({
    "actions": [
      {"command": "click_element", "params": {"text": "Search", "wait_time": 500}},
      {"command": "input_text", "params": {"text": "Hello", "wait_time": 1000}}
    ]
  })

Press Key:
  execute_device_action({
    "actions": [{
      "command": "press_key",
      "params": {"key": "BACK", "wait_time": 1500}
    }]
  })

If you're unsure about available commands, call list_actions() first.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1') - MUST match take_control"},
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
                "required": ["actions"]
            }
        }
    ]

