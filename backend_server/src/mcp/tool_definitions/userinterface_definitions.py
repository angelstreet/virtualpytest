"""UserInterface tool definitions for app/interface management"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get userinterface-related tool definitions"""
    return [
        {
            "name": "create_userinterface",
            "description": """Create a new userinterface (app model) like Netflix, YouTube, etc.

Automatically creates:
- Userinterface metadata
- Root navigation tree
- Entry node

Example:
  create_userinterface(
    name="netflix_android",
    device_model="android_mobile",
    description="Netflix Android TV app"
  )

Returns: userinterface_id and root tree_id""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Interface name (e.g., 'netflix_android', 'youtube_tv')"},
                    "device_model": {"type": "string", "description": "Device model: 'android_mobile', 'android_tv', 'web', 'host_vnc'"},
                    "description": {"type": "string", "description": "Optional description"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["name", "device_model"]
            }
        },
        {
            "name": "list_userinterfaces",
            "description": """List all userinterfaces (app models) for the team

Shows which apps have navigation trees ready.

Example:
  list_userinterfaces()

Returns: List of all interfaces with root tree info""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                    "force_refresh": {"type": "boolean", "description": "Force cache refresh (optional - default false)"}
                },
                "required": []
            }
        },
        {
            "name": "get_userinterface_complete",
            "description": """Get COMPLETE userinterface with ALL nodes, edges, subtrees, and metrics

This is the RECOMMENDED way to get full tree data in ONE call.
Returns everything from root tree + all nested subtrees.

Example:
  complete_tree = get_userinterface_complete(
    userinterface_id="abc-123-def"
  )
  # Returns: {nodes: [...], edges: [...], metrics: {...}}

Replaces multiple calls:
  OLD: get_userinterface() → list_nodes() → list_edges() = 3 calls
  NEW: get_userinterface_complete() = 1 call""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "userinterface_id": {"type": "string", "description": "User interface UUID (from list_userinterfaces or create_userinterface)"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                    "include_metrics": {"type": "boolean", "description": "Include metrics data (optional - default true)"}
                },
                "required": ["userinterface_id"]
            }
        },
        {
            "name": "list_nodes",
            "description": """List all nodes in a navigation tree

Useful for checking what nodes exist after create/delete operations.

Example:
  list_nodes(tree_id="tree-abc-123")

Returns: List of nodes with verifications count""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                    "page": {"type": "integer", "description": "Page number (optional - default 0)"},
                    "limit": {"type": "integer", "description": "Results per page (optional - default 100)"}
                },
                "required": ["tree_id"]
            }
        },
        {
            "name": "list_edges",
            "description": """List all edges in a navigation tree

Useful for checking what navigation paths exist after create/delete operations.

Example:
  list_edges(tree_id="tree-abc-123")

Returns: List of edges with action sets""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                    "node_ids": {"type": "array", "items": {"type": "string"}, "description": "Optional list of node IDs to filter edges"}
                },
                "required": ["tree_id"]
            }
        },
        {
            "name": "delete_userinterface",
            "description": """Delete a userinterface (soft delete)

DESTRUCTIVE OPERATION - Requires explicit confirmation

Removes a user interface model from the system.
This operation is destructive and requires explicit confirmation.

Args:
    userinterface_id: User interface UUID to delete
    confirm: REQUIRED - Must be true to proceed (safety check)
    team_id: Team ID (optional - uses default)

Example:
  # Step 1: Attempt to delete (will ask for confirmation)
  delete_userinterface(
    userinterface_id="abc-123-def-456"
  )
  # Returns: DESTRUCTIVE OPERATION - Confirmation Required
  
  # Step 2: Confirm and delete
  delete_userinterface(
    userinterface_id="abc-123-def-456",
    confirm=true
  )
  # Returns: Userinterface deleted

Returns: Success confirmation or confirmation request""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "userinterface_id": {"type": "string", "description": "User interface UUID to delete"},
                    "confirm": {"type": "boolean", "description": "REQUIRED - Must be true to proceed (safety check)"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["userinterface_id"]
            }
        }
    ]

