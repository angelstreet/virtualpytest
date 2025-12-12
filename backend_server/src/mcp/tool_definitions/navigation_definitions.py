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
            "description": """Navigate to target node using pathfinding.

Requires take_control() first. tree_id auto-resolved from userinterface_name.

Example: navigate_to_node(userinterface_name='google_tv', target_node_label='shop')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "userinterface_name": {"type": "string", "description": "UI name (auto-resolves tree_id)"},
                    "target_node_label": {"type": "string", "description": "Target screen (e.g., 'shop', 'home')"},
                    "host_name": {"type": "string", "description": "Host name"},
                    "device_id": {"type": "string", "description": "Device ID (default: device1)"},
                    "tree_id": {"type": "string", "description": "Tree ID (optional - auto-resolved)"},
                    "team_id": {"type": "string", "description": "Team ID (optional)"}
                },
                "required": ["userinterface_name", "target_node_label"]
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

