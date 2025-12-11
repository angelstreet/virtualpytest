"""AI Exploration tool definitions - Automated tree building"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get AI exploration tool definitions"""
    return [
        {
            "name": "auto_discover_screen",
            "description": """Auto-discover UI elements, create nodes/edges, AND validate them.

Runs 3 phases automatically:
1. AI vision analysis (finds UI elements)
2. Creates nodes/edges
3. Validates each edge (same validation as frontend)

Returns raw validation_results - check for failures and fix with update_edge().""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {
                        "type": "string",
                        "description": "Navigation tree ID"
                    },
                    "host_name": {
                        "type": "string",
                        "description": "Host name"
                    },
                    "userinterface_name": {
                        "type": "string",
                        "description": "User interface name"
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Device ID (default: device1)"
                    },
                    "parent_node_id": {
                        "type": "string",
                        "description": "Parent node for edges (default: home)"
                    }
                },
                "required": ["tree_id", "host_name", "userinterface_name"]
            }
        }
    ]
