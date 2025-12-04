"""
Maintainer Agent Skills

Tools for fixing broken selectors, updating edges, and self-healing.
"""

# Tools that Maintainer Agent can use
MAINTAINER_TOOLS = [
    # Screen analysis (for finding new selectors)
    "dump_ui_elements",
    "analyze_screen_for_action",
    "analyze_screen_for_verification",
    "capture_screenshot",
    
    # Node/Edge inspection
    "get_node",
    "get_edge",
    "list_nodes",
    "list_edges",
    
    # Node/Edge updates
    "update_node",
    "update_edge",
    "delete_node",
    "delete_edge",
    
    # Testing fixes
    "execute_edge",
    "verify_node",
    
    # Screenshots
    "save_node_screenshot",
]

# Tool descriptions for system prompt
MAINTAINER_TOOL_DESCRIPTIONS = """
You have access to these tools:

**Screen Analysis:**
- dump_ui_elements: Get current UI elements
- analyze_screen_for_action: Find best selector for action
- analyze_screen_for_verification: Find best verification element
- capture_screenshot: Take screenshot

**Inspection:**
- get_node: Get node details
- get_edge: Get edge details (including selectors)
- list_nodes: List all nodes
- list_edges: List all edges

**Updates:**
- update_node: Update node properties
- update_edge: Update edge selectors/actions
- delete_node: Remove a node
- delete_edge: Remove an edge

**Testing:**
- execute_edge: Test if edge works after fix
- verify_node: Test if verification works
- save_node_screenshot: Update node screenshot
"""

