"""
Explorer skills for mobile platforms - AUTONOMOUS mode.

The agent builds navigation trees autonomously using atomic tools,
without requiring human approval gates.
"""

EXPLORER_MOBILE_TOOLS = [
    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1: DISCOVERY
    # ═══════════════════════════════════════════════════════════════════
    "get_compatible_hosts",
    "get_device_info",
    "list_userinterfaces",
    "get_userinterface_complete",
    "create_userinterface",

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: SCREEN ANALYSIS
    # ═══════════════════════════════════════════════════════════════════
    "dump_ui_elements",
    "capture_screenshot",
    "analyze_screen_for_action",
    "analyze_screen_for_verification",

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 3: TREE BUILDING (AUTONOMOUS)
    # ═══════════════════════════════════════════════════════════════════
    "create_node",
    "update_node",
    "delete_node",
    "get_node",
    "create_edge",
    "update_edge",
    "delete_edge",
    "get_edge",
    "create_subtree",

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 4: TESTING & VALIDATION
    # ═══════════════════════════════════════════════════════════════════
    "execute_device_action",
    "execute_edge",
    "verify_node",
    "take_control",
    "save_node_screenshot",

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 5: NAVIGATION & REVIEW
    # ═══════════════════════════════════════════════════════════════════
    "preview_userinterface",
    "list_navigation_nodes",
    "navigate_to_node",
]


EXPLORER_MOBILE_TOOL_DESCRIPTIONS = """
═══════════════════════════════════════════════════════════════════════════════
                    AUTONOMOUS MOBILE EXPLORATION TOOLKIT
═══════════════════════════════════════════════════════════════════════════════

You build navigation trees AUTONOMOUSLY using atomic tools. No human approval needed.

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DISCOVERY - Understand what exists                                 │
└─────────────────────────────────────────────────────────────────────────────┘

• get_compatible_hosts(userinterface_name)
  → Returns: host_name, device_id, tree_id
  → ALWAYS call this FIRST to get device/host info
  
• get_device_info(host_name)
  → Returns: device_model, status, capabilities
  → Verify device is ready before proceeding
  
• list_userinterfaces()
  → Returns: All existing userinterfaces with tree_ids
  → Check if userinterface already exists
  
• get_userinterface_complete(userinterface_id)
  → Returns: ALL nodes, edges, verifications in ONE call
  → Use to understand existing structure before adding
  
• create_userinterface(name, device_model, description)
  → Returns: userinterface_id, tree_id
  → Creates new userinterface with root tree + entry node
  → device_model: 'android_mobile', 'android_tv', 'web', 'host_vnc'

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SCREEN ANALYSIS - Identify clickable elements                      │
└─────────────────────────────────────────────────────────────────────────────┘

• dump_ui_elements(device_id, host_name)
  → Returns: ALL UI elements with text, resource-id, bounds, clickable status
  → ✅ MOBILE: Use this (ADB uiautomator dump)
  → Contains: element_id, text, clickable, bounds, class
  
• capture_screenshot(device_id, host_name)
  → Returns: Base64 screenshot image
  → Use for visual reference alongside dump_ui_elements
  
• analyze_screen_for_action(elements, intent, platform='mobile')
  → INPUT: elements from dump_ui_elements, intent like "login button"
  → Returns: {command, action_params, selector_type, score, unique}
  → ⭐ CRITICAL: Always use this to get BEST selector before create_edge
  → Example output: {command: 'click_element_by_id', action_params: {element_id: 'btn_login'}, unique: true}
  
• analyze_screen_for_verification(elements, node_label, platform='mobile')
  → INPUT: elements from dump_ui_elements, node_label like "home"
  → Returns: {command, params, verification_type, score, unique}
  → Use this to create reliable verifications for nodes

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: TREE BUILDING - Create nodes and edges                             │
└─────────────────────────────────────────────────────────────────────────────┘

• create_node(tree_id, label, type='screen', position, data)
  → Returns: node_id (string like 'home', 'login')
  → position: {x, y} for visual layout (auto if omitted)
  → data: {verifications: [...]} for node detection
  
• update_node(tree_id, node_id, updates)
  → Updates: label, position, type, data (including verifications)
  → Use to add verifications AFTER testing navigation
  
• delete_node(tree_id, node_id)
  → Removes node and ALL connected edges
  → Use when node is wrong or unreachable
  
• get_node(tree_id, node_id)
  → Returns full node details including verifications
  
• create_edge(tree_id, source_node_id, target_node_id, source_label, target_label, action_sets)
  → ⭐ CRITICAL: This is where navigation actions are defined
  → action_sets format for MOBILE:
    [
      {"id": "source_to_target", "label": "source → target",
       "actions": [{"command": "click_element_by_id", "params": {"element_id": "..."}}],
       "retry_actions": [], "failure_actions": []},
      {"id": "target_to_source", "label": "target → source",
       "actions": [{"command": "press_key", "params": {"key": "BACK"}}],
       "retry_actions": [], "failure_actions": []}
    ]
  → ALWAYS include bidirectional actions (forward + back)
  
• update_edge(tree_id, edge_id, action_sets)
  → Fix actions if edge test fails
  
• delete_edge(tree_id, edge_id)
  → Remove broken edge
  
• get_edge(tree_id, edge_id)
  → Inspect edge details
  
• create_subtree(parent_tree_id, parent_node_id, subtree_name)
  → Creates nested tree for deeper exploration
  → Use when a screen has its own navigation (e.g., Settings menu)

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: TESTING & VALIDATION - Verify everything works                     │
└─────────────────────────────────────────────────────────────────────────────┘

• execute_device_action(device_id, host_name, actions)
  → Direct device control for testing
  → actions: [{"command": "...", "params": {...}}]
  → Commands: launch_app, click_element_by_id, click_element, press_key, input_text, swipe_up
  
• execute_edge(tree_id, edge_id, action_set_id)
  → Test specific edge by executing its actions
  → Returns success/failure
  → ⭐ ALWAYS test edges after creation
  
• verify_node(node_id, tree_id, userinterface_name)
  → Run node's embedded verifications
  → Returns pass/fail status
  
• take_control(tree_id, device_id, host_name)
  → REQUIRED before navigate_to_node
  → Builds navigation cache
  
• save_node_screenshot(tree_id, node_id, label, host_name, device_id, userinterface_name)
  → Capture and attach screenshot to node
  → Use AFTER navigating to the screen

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: NAVIGATION & REVIEW - Move and inspect                             │
└─────────────────────────────────────────────────────────────────────────────┘

• preview_userinterface(userinterface_name)
  → Quick text view of entire tree structure
  → Shows all nodes, edges, actions
  
• list_navigation_nodes(userinterface_name)
  → Returns all nodes with IDs and labels
  
• navigate_to_node(tree_id, userinterface_name, target_node_label, device_id, host_name)
  → Uses pathfinding to reach target node
  → REQUIRES take_control first

═══════════════════════════════════════════════════════════════════════════════
                    MOBILE-SPECIFIC COMMANDS REFERENCE
═══════════════════════════════════════════════════════════════════════════════

📱 CLICK COMMANDS (Priority Order):
   1. click_element_by_id: {"element_id": "resource_id"}     ← PREFERRED
   2. click_element: {"text": "Button Text"}                 ← Fallback
   3. tap_coordinates: {"x": 540, "y": 960}                  ← Last resort

⌨️ INPUT COMMANDS:
   - input_text: {"text": "search query"}  (types into focused field)
   - First click field, then input_text

🔙 NAVIGATION COMMANDS:
   - press_key: {"key": "BACK"}    ← Return to previous screen
   - press_key: {"key": "HOME"}    ← Return to launcher
   - press_key: {"key": "ENTER"}   ← Confirm/submit

🚀 APP COMMANDS:
   - launch_app: {"package": "com.example.app"}

👆 GESTURE COMMANDS:
   - swipe_up: {}                  ← Scroll down
   - swipe_down: {}                ← Scroll up
   - swipe_left: {}                ← Next item
   - swipe_right: {}               ← Previous item
"""
