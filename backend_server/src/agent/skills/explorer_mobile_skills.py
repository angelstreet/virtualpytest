"""
Explorer skills for mobile platforms.
"""

EXPLORER_MOBILE_TOOLS = [
    # Host/Device discovery
    "get_compatible_hosts",
    "get_device_info",

    # Screen analysis
    "dump_ui_elements",
    "analyze_screen_for_action",
    "analyze_screen_for_verification",
    "capture_screenshot",

    # AI Exploration (automated tree building)
    "start_ai_exploration",
    "get_exploration_status",
    "approve_exploration_plan",
    "validate_exploration_edges",
    "get_node_verification_suggestions",
    "approve_node_verifications",
    "finalize_exploration",

    # Navigation preview
    "preview_userinterface",
    "list_navigation_nodes",

    # UserInterface management
    "create_userinterface",
    "list_userinterfaces",
    "get_userinterface_complete",
]


EXPLORER_MOBILE_TOOL_DESCRIPTIONS = """
You have access to these tools:

**Discovery:**
- get_compatible_hosts: Find devices that can run a userinterface
- get_device_info: Get device details
- capture_screenshot: Take screenshot of current screen

**Screen Analysis:**
- dump_ui_elements: Get all UI elements on screen
- analyze_screen_for_action: Find best selector for an action
- analyze_screen_for_verification: Find best element for verification

**AI Exploration (RECOMMENDED):**
- start_ai_exploration: Begin automated UI discovery
- get_exploration_status: Check exploration progress
- approve_exploration_plan: Approve AI-proposed nodes/edges
- validate_exploration_edges: Test all edges automatically
- get_node_verification_suggestions: Get AI verification suggestions
- approve_node_verifications: Apply verifications to nodes
- finalize_exploration: Complete the exploration

**Navigation:**
- preview_userinterface: Preview navigation tree
- list_navigation_nodes: List nodes in tree
- create_userinterface: Create new userinterface
- list_userinterfaces: List all userinterfaces
- get_userinterface_complete: Get a complete userinterface definition
"""

