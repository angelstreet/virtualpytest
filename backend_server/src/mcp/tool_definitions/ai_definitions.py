"""AI tool definitions for test generation"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get AI-related tool definitions"""
    return [
        {
            "name": "generate_test_graph",
            "description": """Generate test case graph from natural language using AI

CRITICAL - NAVIGATION IS AUTONOMOUS:
The navigation tree (from Phase 1) already defines HOW to move between screens.
Test cases should use 'navigation' nodes that reference tree nodes by label.

**Architecture:**
- Navigation Tree = HOW to navigate (app-specific, built once)
- Test Case = WHAT to test (reusable across apps)

**Correct Usage:**
```json
{
  "type": "navigation",
  "data": {
    "target_node_id": "fb860f60-1f04-4b45-a952-5debf48f20c5",
    "target_node_label": "player"
  }
}
```
This automatically uses the pre-built navigation tree to go home→content_detail→player.

**REQUIRED FIELDS for Navigation Nodes:**
- `target_node_id`: UUID from navigation tree (REQUIRED)
- `target_node_label`: Human-readable label like "home", "player" (REQUIRED)

**DO NOT** create manual action sequences for navigation:
```json
{"type": "action", "data": {"command": "click_element", "text": "Play"}}
```

**When to Use Actions:**
- Use 'action' nodes ONLY for non-navigation actions (pause, volume, text input)
- Use 'navigation' nodes to move between screens in the tree
- Use 'verification' nodes to check screen state

Takes a prompt like "Navigate to settings and verify WiFi is enabled"
Returns executable graph that can be:
1. Passed to execute_testcase() to run immediately
2. Passed to save_testcase() to save for later

GRAPH STRUCTURE (auto-generated):
The AI generates a graph with these required elements:
- `type: "start"` node (entry point)
- `type: "success"` node (test passed terminal)
- All edges with `type: "success"` or `type: "failure"`

Example workflow:
1. graph = generate_test_graph(prompt="Check home screen")
2. execute_testcase(graph_json=graph['graph'])
   OR
   save_testcase(testcase_name="Home Check", graph_json=graph['graph'])""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Natural language test description"},
                    "userinterface_name": {"type": "string", "description": "User interface name (e.g., 'horizon_android_tv', 'horizon_android_mobile')"},
                    "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'use get_compatible_hosts to discover')"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "current_node_id": {"type": "string", "description": "Current node ID for context (optional)"}
                },
                "required": ["prompt", "userinterface_name"]
            }
        },
        {
            "name": "generate_and_save_testcase",
            "description": """Generate test case graph AND save it in one step

This tool combines AI generation + saving to work around MCP protocol limitations.
Use this instead of generate_test_graph when you want to save the result immediately.

CRITICAL: Use get_compatible_hosts(userinterface_name='...') FIRST to find host/device.

CRITICAL: Testcase Naming Convention (REQUIRED)
- Format: TC_<CATEGORY>_<NUMBER>_<CamelCaseAction>
- Examples: TC_AUTH_01_LoginFlow, TC_SRCH_01_ProductSearch (note: SRCH not SEARCH)
- Categories: AUTH, NAV, SRCH, PLAY, PROD, CART, VOD, etc.

Example workflow:
1. hosts = get_compatible_hosts(userinterface_name='sauce-demo')
2. generate_and_save_testcase(
     prompt="Test login flow",
     testcase_name="TC_AUTH_01_LoginFlow",
     host_name=hosts['recommended_host'],
     device_id=hosts['recommended_device'],
     userinterface_name='sauce-demo',
     description="Tests login with valid credentials",
     folder="authentication",
     tags=["auth", "critical"]
   )
3. execute_testcase(testcase_name="TC_AUTH_01_LoginFlow")""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Natural language test description"},
                    "testcase_name": {"type": "string", "description": "Name following TC_<CATEGORY>_<NUMBER>_<CamelCaseAction> format (e.g. TC_AUTH_01_LoginFlow)"},
                    "userinterface_name": {"type": "string", "description": "User interface name"},
                    "host_name": {"type": "string", "description": "Host name (get from get_compatible_hosts)"},
                    "device_id": {"type": "string", "description": "Device ID (get from get_compatible_hosts)"},
                    "description": {"type": "string", "description": "Test description (optional)"},
                    "folder": {"type": "string", "description": "Folder path (optional)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags (optional)"},
                    "team_id": {"type": "string", "description": "Team ID (optional)"},
                    "current_node_id": {"type": "string", "description": "Current node ID for context (optional)"}
                },
                "required": ["prompt", "testcase_name", "userinterface_name", "host_name", "device_id"]
            }
        }
    ]

