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
  # First get compatible host
  hosts = get_compatible_hosts(userinterface_name='your-interface')
  
  list_verifications(
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
            "name": "dump_ui_elements",
            "description": """Dump UI elements from current device screen

**DEVICE MODEL COMPATIBILITY:**
- **android_mobile**: Use this tool (gets UI hierarchy via ADB)
- **web**: Use this tool (gets DOM elements)
- **android_tv / other**: Use capture_screenshot + AI vision instead (no UI dump support)

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
                    "host_name": {"type": "string", "description": "Host name (optional - defaults to 'use get_compatible_hosts to discover')"},
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
    userinterface_name: User interface name (REQUIRED)
    host_name: Host name where device is connected (REQUIRED - use get_compatible_hosts to discover)
    device_id: Device identifier (optional - defaults to 'device1')
    team_id: Team ID (optional - defaults to default)

Returns:
    Verification results with pass/fail status

Example:
    # First get compatible host for the interface
    hosts = get_compatible_hosts(userinterface_name='netflix_mobile')
    
    verify_node({
        "node_id": "home",
        "tree_id": "ae9147a0-07eb-44d9-be71-aeffa3549ee0",
        "userinterface_name": "netflix_mobile",
        "host_name": hosts['recommended_host']
    })""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "Node identifier"},
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "userinterface_name": {"type": "string", "description": "User interface name"},
                    "host_name": {"type": "string", "description": "Host name where device is connected (use get_compatible_hosts to discover)"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["node_id", "tree_id", "userinterface_name", "host_name"]
            }
        }
    ]

