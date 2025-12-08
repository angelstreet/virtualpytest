"""
Explorer skills for web platforms - AUTONOMOUS mode.

Web uses Playwright for browser automation. The agent builds
navigation trees autonomously using atomic tools.
"""

EXPLORER_WEB_TOOLS = [
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


EXPLORER_WEB_TOOL_DESCRIPTIONS = """
═══════════════════════════════════════════════════════════════════════════════
                    AUTONOMOUS WEB EXPLORATION TOOLKIT
═══════════════════════════════════════════════════════════════════════════════

You build navigation trees AUTONOMOUSLY for web apps. No human approval needed.
Uses Playwright for browser automation with CSS/ID selectors.

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DISCOVERY - Understand what exists                                 │
└─────────────────────────────────────────────────────────────────────────────┘

• get_compatible_hosts(userinterface_name)
  → Returns: host_name, device_id, tree_id
  → ALWAYS call this FIRST
  
• get_device_info(host_name)
  → Returns: device_model (should be 'web' or 'host_vnc'), status
  
• list_userinterfaces()
  → Returns: All existing userinterfaces
  
• get_userinterface_complete(userinterface_id)
  → Returns: ALL nodes, edges, verifications in ONE call
  
• create_userinterface(name, device_model='web', description)
  → Creates new userinterface for web
  → device_model: 'web' or 'host_vnc'

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SCREEN ANALYSIS - DOM inspection                                   │
└─────────────────────────────────────────────────────────────────────────────┘

• dump_ui_elements(device_id, host_name, platform='web')
  → Returns: ALL DOM elements with id, class, text, clickable status
  → ✅ WEB: Full DOM access
  → Contains: element_id, tag, text, attributes, clickable
  
• capture_screenshot(device_id, host_name)
  → Returns: Base64 screenshot
  → Visual reference for analysis
  
• analyze_screen_for_action(elements, intent, platform='web')
  → INPUT: elements from dump_ui_elements
  → Returns: {command, action_params, selector_type, score, unique}
  → ⭐ CRITICAL: Get BEST selector before create_edge
  → Selector priority: #id > [data-testid] > .class > //xpath > text
  → Example: {command: 'click_element_by_id', action_params: {element_id: 'login-btn'}, unique: true}
  
• analyze_screen_for_verification(elements, node_label, platform='web')
  → Returns verification for node detection
  → Uses unique page elements as indicators

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: TREE BUILDING - Create nodes and edges                             │
└─────────────────────────────────────────────────────────────────────────────┘

• create_node(tree_id, label, type='screen', position, data)
  → Returns: node_id (string like 'home', 'login')
  → data: {verifications: [...]} for page detection
  
• create_edge(tree_id, source_node_id, target_node_id, source_label, target_label, action_sets)
  → ⭐ WEB action_sets format (MUST include action_type='web' and wait_time):
    [
      {"id": "home_to_login", "label": "home → login",
       "actions": [
         {"command": "click_element_by_id", "action_type": "web",
          "params": {"element_id": "login-link", "wait_time": 2000}}
       ],
       "retry_actions": [], "failure_actions": []},
      {"id": "login_to_home", "label": "login → home",
       "actions": [
         {"command": "click_element_by_id", "action_type": "web",
          "params": {"element_id": "home-link", "wait_time": 2000}}
       ],
       "retry_actions": [], "failure_actions": []}
    ]
  
  FOR FORMS (click then type):
    "actions": [
      {"command": "click_element_by_id", "action_type": "web",
       "params": {"element_id": "username-field", "wait_time": 500}},
      {"command": "input_text", "action_type": "web",
       "params": {"selector": "#username-field", "text": "user@example.com", "wait_time": 500}},
      {"command": "click_element_by_id", "action_type": "web",
       "params": {"element_id": "submit-btn", "wait_time": 2000}}
    ]
  
• update_node(tree_id, node_id, updates)
  → Add verifications after testing
  
• update_edge(tree_id, edge_id, action_sets)
  → Fix actions if test fails
  
• create_subtree(parent_tree_id, parent_node_id, subtree_name)
  → For sections with deep navigation (e.g., Admin panel)

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: TESTING & VALIDATION                                               │
└─────────────────────────────────────────────────────────────────────────────┘

• execute_device_action(device_id, host_name, actions)
  → Test web actions directly
  → WEB actions MUST have action_type: "web"
  
• execute_edge(tree_id, edge_id, action_set_id)
  → Test specific edge
  → ⭐ ALWAYS test after creation
  
• verify_node(node_id, tree_id, userinterface_name)
  → Run page verifications
  
• take_control(tree_id, device_id, host_name)
  → Required before navigate_to_node
  
• save_node_screenshot(tree_id, node_id, label, host_name, device_id, userinterface_name)
  → Capture page screenshot

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: NAVIGATION & REVIEW                                                │
└─────────────────────────────────────────────────────────────────────────────┘

• preview_userinterface(userinterface_name)
  → Quick text view of structure
  
• list_navigation_nodes(userinterface_name)
  → All nodes with IDs
  
• navigate_to_node(tree_id, userinterface_name, target_node_label, device_id, host_name)
  → Pathfinding navigation

═══════════════════════════════════════════════════════════════════════════════
                    WEB-SPECIFIC COMMANDS REFERENCE
═══════════════════════════════════════════════════════════════════════════════

⚠️ ALL WEB COMMANDS MUST INCLUDE: action_type: "web" AND wait_time in params!

🖱️ CLICK COMMANDS (Priority Order):
   1. click_element_by_id: {"element_id": "login-btn", "wait_time": 2000}     ← PREFERRED
   2. click_element: {"selector": "#login-btn", "wait_time": 2000}            ← CSS selector
   3. click_element: {"selector": "//button[@id='login']", "wait_time": 2000} ← XPath
   4. click_element: {"text": "Log In", "wait_time": 2000}                    ← Text fallback

⌨️ INPUT COMMANDS:
   - input_text: {"selector": "#email", "text": "user@example.com", "wait_time": 500}
   - ⚠️ WEB uses 'selector' parameter (not 'element_text' like mobile)
   - Always click field FIRST to focus, then input_text
   
   Example form workflow:
   1. {"command": "click_element_by_id", "action_type": "web", "params": {"element_id": "email", "wait_time": 300}}
   2. {"command": "input_text", "action_type": "web", "params": {"selector": "#email", "text": "test@test.com", "wait_time": 300}}
   3. {"command": "click_element_by_id", "action_type": "web", "params": {"element_id": "password", "wait_time": 300}}
   4. {"command": "input_text", "action_type": "web", "params": {"selector": "#password", "text": "secret123", "wait_time": 300}}
   5. {"command": "click_element_by_id", "action_type": "web", "params": {"element_id": "submit", "wait_time": 2000}}

🔗 NAVIGATION COMMANDS:
   - navigate_to_url: {"url": "https://example.com/page", "wait_time": 3000}
   - press_key: {"key": "Escape", "wait_time": 500}    ← Close modals
   - press_key: {"key": "Enter", "wait_time": 1000}    ← Submit forms

🔙 BACK NAVIGATION:
   - For web, prefer clicking navigation links over browser back
   - Use explicit "home" or "back" links when available
   - Browser back as last resort: navigate_to_url with previous URL

📋 SELECTOR PRIORITY (Best → Worst):
   1. #element-id           ← Most reliable, always unique
   2. [data-testid="..."]   ← Test IDs, designed for automation
   3. [name="..."]          ← Form elements
   4. .unique-class         ← If class is unique
   5. //xpath               ← Complex selections
   6. text content          ← Fragile, avoid if possible
"""
