"""Navigation tool definitions for UI tree navigation"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get navigation-related tool definitions"""
    return [
        {
            "name": "list_navigation_nodes",
            "description": """List nodes in a navigation tree (labels, IDs, types, positions).
Provide EITHER userinterface_name (recommended) OR tree_id.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Tree ID (or use userinterface_name)"},
                    "userinterface_name": {"type": "string", "description": "UI name (recommended)"},
                    "team_id": {"type": "string", "description": "Team ID (optional)"},
                    "page": {"type": "integer", "description": "Page (default: 0)"},
                    "limit": {"type": "integer", "description": "Per page (default: 100)"}
                },
                "required": []
            }
        },
        {
            "name": "navigate_to_node",
            "description": """Navigate to target node using pathfinding. Auto-verifies target.

PREREQUISITE: Call take_control() ONCE before any navigation.
navigate_to_node tool executes all actions and verification to reach end node autonomously using pathfinding.
On "cache not ready" error: call take_control() then retry.

Parameters must match take_control call. Polls until complete (max 3min).""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Tree ID (must match take_control)"},
                    "userinterface_name": {"type": "string", "description": "UI name"},
                    "device_id": {"type": "string", "description": "Device ID (default: device1)"},
                    "team_id": {"type": "string", "description": "Team ID (optional)"},
                    "target_node_id": {"type": "string", "description": "Target node ID"},
                    "target_node_label": {"type": "string", "description": "Target node label"},
                    "current_node_id": {"type": "string", "description": "Current node (optional)"},
                    "host_name": {"type": "string", "description": "Host name"}
                },
                "required": ["tree_id", "userinterface_name"]
            }
        },
        {
            "name": "preview_userinterface",
            "description": """Get compact text preview of UI navigation tree.
Shows nodes, edges, actions, verifications. No prerequisites.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "userinterface_name": {"type": "string", "description": "UI name"},
                    "team_id": {"type": "string", "description": "Team ID (optional)"}
                },
                "required": ["userinterface_name"]
            }
        }
    ]

