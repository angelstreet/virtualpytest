"""Navigation tool definitions for UI tree navigation"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get navigation-related tool definitions"""
    return [
        {
            "name": "list_navigation_nodes",
            "description": """List navigation nodes available in a tree

Returns list of nodes with labels, IDs, types, and positions.
Useful for discovering what nodes are available for navigation.

Can accept EITHER tree_id OR userinterface_name (recommended).

Example:
  list_navigation_nodes(
    userinterface_name='horizon_android_mobile'
  )
  OR
  list_navigation_nodes(
    tree_id='abc-123'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID (optional - provide this OR userinterface_name)"},
                    "userinterface_name": {"type": "string", "description": "User interface name (optional - provide this OR tree_id). Recommended approach."},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "page": {"type": "integer", "description": "Page number (optional, default: 0)"},
                    "limit": {"type": "integer", "description": "Results per page (optional, default: 100)"}
                },
                "required": []
            }
        },
        {
            "name": "navigate_to_node",
            "description": """Navigate to target node in UI tree using pathfinding

PREREQUISITE: take_control(tree_id='<tree>') must be called ONCE first with the SAME tree_id.
If you get "cache not ready" error, call take_control() first then retry this tool.

Can be called MULTIPLE times in the same session to navigate to different nodes.
All parameters (device_id, tree_id, userinterface_name) MUST match the take_control call.

The tool polls automatically until navigation completes (up to 3 minutes).

Example workflow:
1. take_control(device_id='device1', tree_id='abc-123')
2. navigate_to_node(device_id='device1', tree_id='abc-123', userinterface_name='horizon_android_tv', target_node_label='home')
3. navigate_to_node(device_id='device1', tree_id='abc-123', userinterface_name='horizon_android_tv', target_node_label='settings')
4. release_control(device_id='device1')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID - MUST match the tree_id used in take_control"},
                    "userinterface_name": {"type": "string", "description": "User interface name (e.g., 'horizon_android_tv', 'horizon_android_mobile')"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1') - MUST match take_control"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "target_node_id": {"type": "string", "description": "Target node ID (provide either this or target_node_label)"},
                    "target_node_label": {"type": "string", "description": "Target node label (provide either this or target_node_id)"},
                    "current_node_id": {"type": "string", "description": "Current node ID (optional)"},
                    "host_name": {"type": "string", "description": "Host name where device is connected (use get_compatible_hosts to discover)"}
                },
                "required": ["tree_id", "userinterface_name"]
            }
        },
        {
            "name": "preview_userinterface",
            "description": """Get compact text preview of userinterface navigation tree

Shows all nodes, edges, actions, and verifications in 8-10 lines.
Perfect for answering "What do we test and how?"

NO PREREQUISITES - Just call with userinterface_name

Output format:
  netflix_mobile (7 nodes, 13 transitions)
  
  Entry→home: launch_app + tap(540,1645) [✓ Startseite]
  home⟷search: click(Suchen) ⟷ click(Nach oben navigieren) [✓ Suchen]
  home⟷content_detail: click(The Witcher) ⟷ BACK [✓ abspielen]
  ...

Use cases:
- Quick overview of test coverage
- Share navigation structure with stakeholders
- Understand what actions are tested
- Verify navigation completeness

Example:
  preview_userinterface(userinterface_name='netflix_mobile')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "userinterface_name": {"type": "string", "description": "User interface name (e.g., 'netflix_mobile', 'horizon_android_tv')"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                },
                "required": ["userinterface_name"]
            }
        }
    ]

