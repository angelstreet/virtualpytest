"""Tree tool definitions for navigation tree CRUD operations"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get tree CRUD-related tool definitions"""
    return [
        {
            "name": "create_node",
            "description": """Create a node in navigation tree

Atomic primitive for building navigation structures.
Can be composed for AI exploration, manual tree building, or tree refactoring.

IMPORTANT - NODE ID USAGE:
The tool returns the PERMANENT database UUID immediately. Use this ID for creating edges.
- create_node() → Returns permanent UUID (e.g., "60f8c86e-d0ec-4dd9-bbf5-88f7f74e016e")
- Use this UUID directly in create_edge(source_node_id=..., target_node_id=...)
- NO need to call list_navigation_nodes() to get IDs

Workflow for building navigation trees:
  # Step 1: Create nodes
  result1 = create_node(tree_id="main", label="home")
  # Returns: Node created: home (ID: abc-123-uuid)
  home_id = "abc-123-uuid"  # Extract from response
  
  result2 = create_node(tree_id="main", label="settings")
  # Returns: Node created: settings (ID: def-456-uuid)
  settings_id = "def-456-uuid"  # Extract from response
  
  # Step 2: Create edges with the returned permanent IDs
  create_edge(
    tree_id="main",
    source_node_id=home_id,      # Use permanent UUID from step 1
    target_node_id=settings_id,   # Use permanent UUID from step 1
    action_sets=[
      {
        "id": "home_to_settings",
        "actions": [{"command": "click_element", "params": {"text": "Settings"}, "delay": 2000}]
      },
      {
        "id": "settings_to_home",
        "actions": [{"command": "press_key", "params": {"key": "BACK"}, "delay": 2000}]
      }
    ]
  )

Example:
  create_node(
    tree_id="main_tree",
    label="settings",
    type="screen",
    position={"x": 100, "y": 200}
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "label": {"type": "string", "description": "Node label/name"},
                    "node_id": {"type": "string", "description": "Node identifier (optional - auto-generated if omitted)"},
                    "type": {"type": "string", "description": "Node type (default: 'screen')"},
                    "position": {"type": "object", "description": "Position {x, y} coordinates (optional)"},
                    "data": {"type": "object", "description": "Custom metadata (optional)"}
                },
                "required": ["tree_id", "label"]
            }
        },
        {
            "name": "update_node",
            "description": """Update an existing node

Modify node properties like label, position, type, or custom data.

Example:
  update_node(
    tree_id="main_tree",
    node_id="settings",
    updates={"label": "settings_main", "position": {"x": 150, "y": 200}}
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "node_id": {"type": "string", "description": "Node identifier to update"},
                    "updates": {"type": "object", "description": "Fields to update (label, position, type, data)"}
                },
                "required": ["tree_id", "node_id", "updates"]
            }
        },
        {
            "name": "delete_node",
            "description": """Delete a node from navigation tree

Removes node and all connected edges.

Example:
  delete_node(
    tree_id="main_tree",
    node_id="old_node"
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "node_id": {"type": "string", "description": "Node identifier to delete"}
                },
                "required": ["tree_id", "node_id"]
            }
        },
        {
            "name": "create_edge",
            "description": """Create an edge between two nodes

Defines navigation path with forward and backward actions.

ELEMENT SELECTION (selector MUST be unique on page):

1. #id (always unique)
2. //xpath (e.g., //button[@name='login'])
3. [attr] or .class (verify uniqueness first)
4. plain text (fallback, slower)

Use dump_ui_elements() to verify selector appears only once on page.

IMPORTANT - INPUT FIELDS:
Before using input_text, click the input field first to focus it.
Example: click_element("Search") then input_text("Search", "text")

CRITICAL - NODE IDs MUST BE STRINGS (e.g., 'home'), NOT UUIDs!
- Use the 'node_id' field from list_navigation_nodes() or create_node() response.
- Examples: source_node_id='home' | source_node_id='ce97c317-...' (this is a database UUID and will error).
- If creating new nodes: create_node returns "node_id: 'home'" – use that string value.
- Validation will reject UUIDs with an error message.

HANDLES - FIXED TO MENU HANDLES ONLY:
- sourceHandle: ALWAYS "bottom-right-menu-source" (auto-applied)
- targetHandle: ALWAYS "top-right-menu-target" (auto-applied)
- These create vertical connections between nodes.

Best Practice Workflow (From Scratch):
1. Inspect UI to find element IDs:
   dump_ui_elements() # Returns: {"element_id": "customer_login_link", "text": "Log In", ...}

2. (Optional) List existing nodes to get string node_ids:
   list_navigation_nodes(userinterface_name='your_ui')  # Returns: • home (node_id: 'home', ...) → Use 'home'

3. Create nodes if needed (returns string node_id):
   result1 = create_node(tree_id='your_tree_id', label='home')  # Returns: Node created: home (node_id: 'home')
   home_id = 'home'  # Extract the string 'home'

   result2 = create_node(tree_id='your_tree_id', label='login')  # Returns: Node created: login (node_id: 'login')
   login_id = 'login'  # Extract the string 'login'

4. Create the edge - FORMAT DEPENDS ON DEVICE TYPE:

   MOBILE/ADB (Android) - ⭐ USE ELEMENT IDs:
   create_edge(
     tree_id='your_tree_id',
     source_node_id='home',
     target_node_id='login',
     source_label='home',
     target_label='login',
     action_sets=[
       {"id": "home_to_login", "label": "home → login",
        "actions": [{"command": "click_element_by_id", "params": {"element_id": "customer_login_link"}}],
        "retry_actions": [], "failure_actions": []},
       {"id": "login_to_home", "label": "login → home",
        "actions": [{"command": "press_key", "params": {"key": "BACK"}}],
        "retry_actions": [], "failure_actions": []}
     ]
   )

   WEB (Playwright) - ⭐ USE ELEMENT IDs or SELECTORS:
   create_edge(
     tree_id='your_tree_id',
     source_node_id='home',
     target_node_id='admin',
     source_label='home',
     target_label='admin',
     action_sets=[
       {"id": "home_to_admin", "label": "home → admin",
        "actions": [{"command": "click_element_by_id", "action_type": "web", "params": {"element_id": "admin_nav_link", "wait_time": 1000}}],
        "retry_actions": [], "failure_actions": []},
       {"id": "admin_to_home", "label": "admin → home",
        "actions": [{"command": "click_element_by_id", "action_type": "web", "params": {"element_id": "home_nav_link", "wait_time": 1000}}],
        "retry_actions": [], "failure_actions": []}
     ]
   )

   REMOTE/IR (STB/TV):
   create_edge(
     tree_id='your_tree_id',
     source_node_id='home',
     target_node_id='settings',
     source_label='home',
     target_label='settings',
     action_sets=[
       {"id": "home_to_settings", "label": "home → settings",
        "actions": [{"command": "press_key", "action_type": "remote", "params": {"key": "RIGHT", "wait_time": 1500}}],
        "retry_actions": [], "failure_actions": []},
       {"id": "settings_to_home", "label": "settings → home",
        "actions": [{"command": "press_key", "action_type": "remote", "params": {"key": "LEFT", "wait_time": 1500}}],
        "retry_actions": [], "failure_actions": []}
     ]
   )

   KEY DIFFERENCES:
   - Mobile: NO action_type, NO wait_time, use element_id
   - Web: MUST have action_type="web", wait_time in params, use element_id
   - Remote: MUST have action_type="remote", wait_time in params, use key
   - All need: id, label, actions, retry_actions, failure_actions

4. Test the edge:
   take_control(tree_id='your_tree_id')  # Once per session
   navigate_to_node(tree_id='your_tree_id', target_node_id='settings')  # Uses the new edge

Tips:
- action_sets: Must include id, label, actions, retry_actions, failure_actions for each set
- Bidirectional nav: Provide 2 action_sets (forward + backward) for best results
- Device-specific format: Follow the examples above for your device type (Mobile/Web/Remote)
- If error: "must be the node_id string... not database UUID" – switch to string IDs from list_navigation_nodes
- For existing nodes: Always use list_navigation_nodes to get the correct string node_id
- Subtrees: Create via create_subtree, then use the new tree_id for edges within it.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "source_node_id": {"type": "string", "description": "Source node ID (string like 'home' from list_navigation_nodes or create_node – NOT a UUID!)"},
                    "target_node_id": {"type": "string", "description": "Target node ID (string like 'settings' from list_navigation_nodes or create_node – NOT a UUID!)"},
                    "source_label": {"type": "string", "description": "Source node label (REQUIRED - matches the label used in create_node)"},
                    "target_label": {"type": "string", "description": "Target node label (REQUIRED - matches the label used in create_node)"},
                    "action_sets": {"type": "array", "description": "Array of action sets with bidirectional navigation. Each action_set requires: id, label, actions[], retry_actions[], failure_actions[]. Format differs by device type: Mobile uses element_id (NO action_type/wait_time), Web uses element_id + action_type='web' + wait_time in params, Remote uses key + action_type='remote' + wait_time in params. See examples in description above."},
                    "edge_id": {"type": "string", "description": "Edge identifier (optional - auto-generated if omitted)"},
                    "label": {"type": "string", "description": "Edge label in format 'source→target' (optional - auto-generated from action_sets if omitted)"},
                    "final_wait_time": {"type": "number", "description": "Wait time after edge execution in ms - default: 2000"},
                    "priority": {"type": "string", "description": "Edge priority: p1 (high), p2 (medium), p3 (low) - default: p3"},
                    "is_conditional": {"type": "boolean", "description": "Whether edge has conditions - default: false"},
                    "is_conditional_primary": {"type": "boolean", "description": "If conditional, is this primary path - default: false"}
                },
                "required": ["tree_id", "source_node_id", "target_node_id", "source_label", "target_label"]
            }
        },
        {
            "name": "update_edge",
            "description": """Update edge actions

Fix or modify navigation actions after testing.

Example:
  update_edge(
    tree_id="main_tree",
    edge_id="edge_home_settings",
    action_sets=[...new actions...]
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "edge_id": {"type": "string", "description": "Edge identifier to update"},
                    "action_sets": {"type": "array", "description": "New action sets (replaces existing)"}
                },
                "required": ["tree_id", "edge_id", "action_sets"]
            }
        },
        {
            "name": "delete_edge",
            "description": """Delete an edge from navigation tree

Example:
  delete_edge(
    tree_id="main_tree",
    edge_id="edge_old"
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "edge_id": {"type": "string", "description": "Edge identifier to delete"}
                },
                "required": ["tree_id", "edge_id"]
            }
        },
        {
            "name": "create_subtree",
            "description": """Create a subtree for a parent node

Required for recursive tree exploration - allows exploring deeper levels.

Example workflow:
  1. create_node(id="settings") in main tree
  2. create_subtree(parent_node_id="settings", subtree_name="settings_subtree")
     → Returns: {"subtree_tree_id": "subtree-123"}
  3. navigate_to_node(target="settings")
  4. create_node(tree_id="subtree-123", ...) in subtree
  5. Repeat for deeper levels

Example:
  create_subtree(
    parent_tree_id="main_tree",
    parent_node_id="settings",
    subtree_name="settings_subtree"
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "parent_tree_id": {"type": "string", "description": "Parent tree ID"},
                    "parent_node_id": {"type": "string", "description": "Parent node ID to attach subtree to"},
                    "subtree_name": {"type": "string", "description": "Name for the subtree (e.g., 'settings_subtree')"}
                },
                "required": ["parent_tree_id", "parent_node_id", "subtree_name"]
            }
        },
        {
            "name": "get_node",
            "description": """Get a specific node by ID

Returns full node details including position, data, and verifications.
Use this to inspect node structure before updating or to verify node creation.

Example:
  get_node(
    tree_id="main_tree",
    node_id="settings"
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "node_id": {"type": "string", "description": "Node identifier"}
                },
                "required": ["tree_id", "node_id"]
            }
        },
        {
            "name": "get_edge",
            "description": """Get a specific edge by ID

Returns full edge details including action_sets, handles, and metadata.
Use this to inspect edge structure before updating or to verify edge creation.

Example:
  get_edge(
    tree_id="main_tree",
    edge_id="edge_home_settings"
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "edge_id": {"type": "string", "description": "Edge identifier"}
                },
                "required": ["tree_id", "edge_id"]
            }
        },
        {
            "name": "save_node_screenshot",
            "description": """Capture and attach screenshot to a node

**CRITICAL: Call this during exploration for every node!**

Screenshots are essential for:
- Visual reference of each screen
- Node verification (comparing current vs expected)
- Documentation of the navigation tree

**WHEN to call (during exploration):**
1. After executing edge actions and you're on a new screen
2. After adding verifications to a node
3. For every node you create/validate

**Workflow:**
```
# 1. Get edge details
edge = get_edge(tree_id, edge_id)
# 2. Execute navigation
execute_device_action(actions=edge['action_sets'][0]['actions'], ...)
# ↓ Now on login screen
# 3. Capture it!
save_node_screenshot(
  tree_id='...',
  node_id='login',
  label='Login Screen',
  host_name='pi1',
  device_id='device1',
  userinterface_name='google_tv'
)
```

This tool does 3 things in one call:
1. Takes screenshot from device
2. Saves to /screenshots/{userinterface_name}/{label}.png
3. Updates node with screenshot URL

Example:
  save_node_screenshot({
    "tree_id": "ae9147a0-07eb-44d9-be71-aeffa3549ee0",
    "node_id": "home",
    "label": "Home Screen",
    "host_name": "sunri-pi1",
    "device_id": "device1",
    "userinterface_name": "netflix_mobile"
  })""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tree_id": {"type": "string", "description": "Navigation tree ID"},
                    "node_id": {"type": "string", "description": "Node identifier to attach screenshot to"},
                    "label": {"type": "string", "description": "Node label used as filename"},
                    "host_name": {"type": "string", "description": "Host where device is connected"},
                    "device_id": {"type": "string", "description": "Device identifier"},
                    "userinterface_name": {"type": "string", "description": "User interface name for organizing screenshots"},
                    "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                },
                "required": ["tree_id", "node_id", "label", "host_name", "device_id", "userinterface_name"]
            }
        }
    ]

