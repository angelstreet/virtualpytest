"""AI Exploration tool definitions - Automated tree building"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get AI exploration tool definitions"""
    return [
        {
            "name": "auto_discover_screen",
            "description": """Auto-discover UI elements on current screen and create nodes/edges.
Analyzes screen dump, filters interactive elements, creates nodes with verifications and edges from parent.""",
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
                    "device_id": {
                        "type": "string",
                        "description": "Device ID (default: device1)"
                    },
                    "parent_node_id": {
                        "type": "string",
                        "description": "Parent node for edges (default: home)"
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID (optional)"
                    }
                },
                "required": ["tree_id", "host_name"]
            }
        }
    ]
