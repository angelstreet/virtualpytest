"""Verification tool definitions for device state verification"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get verification-related tool definitions"""
    return [
        {
            "name": "list_verifications",
            "description": """List available verification types for a device

Returns categorized list of verification methods with parameters.
Useful for discovering what verifications can be performed on a device.

PREREQUISITE: Device must be registered with the host.

Device Model Specific:
- android_mobile/android_tv: Returns ADB/Remote verifications (check_element_exists, check_text_on_screen, getMenuInfo, etc)
- web/desktop: Returns web verification methods

Example:
  list_verifications(
    device_id='device1',
    host_name='sunri-pi1'
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
            "name": "verify_device_state",
            "description": """Verify device state with batch verifications (image, text, video, ADB)

✅ NO PREREQUISITES - Just call this directly.

Can be called MULTIPLE times in the same session.

Device Model Specific:
- android_mobile/android_tv: Use ADB/Remote verification commands discovered via list_verifications()
  Must use CORRECT field names: 'command' (not 'method') and 'verification_type' (not 'type')
- web/desktop: Use web verification methods

IMPORTANT: Call list_verifications() first to see exact command structure for the device model.

**CRITICAL - VERIFICATION FORMAT:**
Each verification object MUST use:
- 'command': The verification method name (e.g., 'waitForElementToAppear')
- 'verification_type': The category (e.g., 'adb', 'image', 'text', 'video')
- 'params': Method-specific parameters (e.g., 'search_term' for waitForElementToAppear)
- 'expected': Expected result (optional)

Example:
```json
{
  "command": "waitForElementToAppear",
  "verification_type": "adb",
  "params": {"search_term": "Home", "timeout": 5000}
}
```

**CRITICAL - PARAMETER NAMES:**
For waitForElementToAppear, use 'search_term' (NOT 'text'):
- CORRECT: {"search_term": "Home", "timeout": 10}
- WRONG: {"text": "Home", "timeout": 10}

search_term selector priority (MUST be unique on page):
1. #id (always unique)
2. //xpath (e.g., //button[@name='login'])
3. [attr] or .class (verify uniqueness first)
4. plain text (fallback, slower)

1 unique selector is enough. Only use multiple verifications if single selector is not unique.
Prefer stable structural elements (form fields, buttons) over dynamic content (product names, prices)
""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "userinterface_name": {"type": "string", "description": "User interface name"},
                    "verifications": {
                        "type": "array",
                        "description": "Array of verification objects. Each object MUST use 'command' (not 'method') and 'verification_type' (not 'type') to match frontend expectations.",
                        "items": {"type": "object"}
                    },
                    "tree_id": {"type": "string", "description": "Navigation tree ID (optional)"},
                    "node_id": {"type": "string", "description": "Node ID to verify (optional)"},
                    "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"}
                },
                "required": ["userinterface_name", "verifications"]
            }
        },
        {
            "name": "dump_ui_elements",
            "description": """Dump UI elements from current device screen

⚠️ **DEVICE MODEL COMPATIBILITY:**
- ✅ **android_mobile**: Use this tool (gets UI hierarchy via ADB)
- ✅ **web**: Use this tool (gets DOM elements)
- ❌ **android_tv / other**: Use capture_screenshot + AI vision instead (no UI dump support)

**How to choose:**
1. Call get_device_info() first to check device_model
2. If device_model is "android_mobile" or "web" → use dump_ui_elements()
3. If device_model is "android_tv" or other → use capture_screenshot() + AI vision

CRITICAL for debugging failed navigation or verification.
Returns all UI elements with text, resource-id, clickable status, bounds.

Use cases:
- Debug failed edge: "Element not found" → dump to see actual element names
- Verify screen: Check if expected elements are present
- Discover navigation targets: See what's clickable on current screen
- AI exploration: Identify clickable elements to create nodes/edges

Example:
  # Step 1: Check device model
  device_info = get_device_info(device_id="device1")
  device_model = device_info['device_model']  # e.g., "android_mobile"
  
  # Step 2: Choose inspection method
  if device_model in ["android_mobile", "web"]:
      elements = dump_ui_elements(device_id="device1", platform="mobile")
      # Returns: [{"text": "Settings Tab", "clickable": true, "resource-id": "tab_settings"}, ...]
  else:
      screenshot = capture_screenshot(device_id="device1")
      # Use AI vision to analyze screenshot
  
  # LLM analyzes: "Ah! It's 'Settings Tab', not 'Settings'"
  # Fix edge with correct element name
  update_edge(edge_id="...", actions=[...click "Settings Tab"...])""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "host_name": {"type": "string", "description": "Host name (optional - defaults to 'sunri-pi1')"},
                    "platform": {"type": "string", "description": "Platform type (optional: 'mobile', 'web', 'tv')"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": []
            }
        },
        {
            "name": "verify_node",
            "description": """Execute verifications for a specific node (frontend: useNode.ts line 403-411)

This runs the embedded verifications in a node, useful for:
- Testing node verifications without navigation
- Debugging verification logic
- Manual verification execution from UI

Args:
    node_id: Node identifier (REQUIRED)
    tree_id: Navigation tree ID (REQUIRED)
    device_id: Device identifier (optional - defaults to 'device1')
    host_name: Host name (optional - defaults to 'sunri-pi1')
    userinterface_name: User interface name (REQUIRED)
    team_id: Team ID (optional - defaults to default)

Returns:
    Verification results with pass/fail status

Example:
    verify_node({
        "node_id": "home",
        "tree_id": "ae9147a0-07eb-44d9-be71-aeffa3549ee0",
        "userinterface_name": "netflix_mobile"
    })""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "Node identifier"},
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "userinterface_name": {"type": "string", "description": "User interface name"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "host_name": {"type": "string", "description": "Host name (optional - defaults to 'sunri-pi1')"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["node_id", "tree_id", "userinterface_name"]
            }
        }
    ]

