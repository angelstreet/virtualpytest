"""AI Exploration tool definitions - Automated tree building"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get AI exploration tool definitions"""
    return [
        {
            "name": "auto_discover_screen",
            "description": """Auto-discover UI elements and create nodes/edges.
Calls start_exploration() + continue_exploration() with all elements selected.""",
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
