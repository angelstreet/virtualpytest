"""
Explorer skills for STB/TV platforms - AUTONOMOUS mode.

STB/TV uses D-pad navigation (no touch) and vision-based analysis
(no UI dump available). The agent builds trees autonomously.
"""

EXPLORER_STB_TOOLS = [
    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1: DISCOVERY
    # ═══════════════════════════════════════════════════════════════════
    "get_compatible_hosts",
    "get_device_info",
    "list_userinterfaces",
    "get_userinterface_complete",
    "create_userinterface",

    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: SCREEN ANALYSIS (VISION-ONLY - No UI dump on STB)
    # ═══════════════════════════════════════════════════════════════════
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


EXPLORER_STB_TOOL_DESCRIPTIONS = """
═══════════════════════════════════════════════════════════════════════════════
                    AUTONOMOUS STB/TV EXPLORATION TOOLKIT
═══════════════════════════════════════════════════════════════════════════════

You build navigation trees AUTONOMOUSLY for STB/TV using D-pad navigation.
No human approval needed. VISION-BASED analysis (no UI dump available).

┌─────────────────────────────────────────────────────────────────────────────┐
│ STB/TV DUAL-LAYER NAVIGATION MODEL                                          │
└─────────────────────────────────────────────────────────────────────────────┘

STB/TV uses a DUAL-LAYER structure:

LAYER 1 - FOCUS NODES (Menu positions):
  home → home_tvguide → home_apps → home_settings
       ←──── LEFT ──── RIGHT ────→

LAYER 2 - SCREEN NODES (Actual screens):
  home_tvguide ──OK──→ tvguide
              ←─BACK─┘
  
Complete navigation path:
  home → RIGHT → home_tvguide → OK → tvguide → BACK → home_tvguide → LEFT → home

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DISCOVERY - Understand what exists                                 │
└─────────────────────────────────────────────────────────────────────────────┘

• get_compatible_hosts(userinterface_name)
  → Returns: host_name, device_id, tree_id
  → ALWAYS call this FIRST
  
• get_device_info(host_name)
  → Returns: device_model (should be 'android_tv'), status
  → Verify device is STB/TV type
  
• list_userinterfaces()
  → Returns: All existing userinterfaces
  
• get_userinterface_complete(userinterface_id)
  → Returns: ALL nodes, edges, verifications
  
• create_userinterface(name, device_model='android_tv', description)
  → Creates new userinterface for TV

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SCREEN ANALYSIS - Vision-based (NO dump_ui_elements)               │
└─────────────────────────────────────────────────────────────────────────────┘

⚠️ STB/TV has NO dump_ui_elements! Use vision analysis:

• capture_screenshot(device_id, host_name)
  → Returns: Base64 screenshot
  → ⭐ PRIMARY method for STB - analyze visually
  → Look for: menu items, focus indicators, text labels
  
• analyze_screen_for_action(elements=None, intent, platform='tv')
  → For TV: Pass screenshot analysis results or describe what you see
  → Returns recommended D-pad sequence
  
• analyze_screen_for_verification(elements=None, node_label, platform='tv')
  → For TV: Vision-based verification suggestions
  → Often uses text detection or image matching

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: TREE BUILDING - Create dual-layer structure                        │
└─────────────────────────────────────────────────────────────────────────────┘

• create_node(tree_id, label, type='screen', position, data)
  → For FOCUS nodes: label='home_tvguide', type='focus'
  → For SCREEN nodes: label='tvguide', type='screen'
  
• create_edge(tree_id, source_node_id, target_node_id, source_label, target_label, action_sets)
  → ⭐ STB/TV action_sets format (D-pad navigation):
  
  HORIZONTAL (focus to focus):
    [
      {"id": "home_to_tvguide", "label": "home → home_tvguide",
       "actions": [{"command": "press_key", "action_type": "remote", 
                    "params": {"key": "RIGHT", "wait_time": 1500}}],
       "retry_actions": [], "failure_actions": []},
      {"id": "tvguide_to_home", "label": "home_tvguide → home",
       "actions": [{"command": "press_key", "action_type": "remote",
                    "params": {"key": "LEFT", "wait_time": 1500}}],
       "retry_actions": [], "failure_actions": []}
    ]
  
  VERTICAL (focus to screen):
    [
      {"id": "focus_to_screen", "label": "home_tvguide → tvguide",
       "actions": [{"command": "press_key", "action_type": "remote",
                    "params": {"key": "OK", "wait_time": 2000}}],
       "retry_actions": [], "failure_actions": []},
      {"id": "screen_to_focus", "label": "tvguide → home_tvguide",
       "actions": [{"command": "press_key", "action_type": "remote",
                    "params": {"key": "BACK", "wait_time": 2000}}],
       "retry_actions": [], "failure_actions": []}
    ]

• update_node(tree_id, node_id, updates)
  → Add verifications after testing
  
• create_subtree(parent_tree_id, parent_node_id, subtree_name)
  → For screens with their own navigation (e.g., Settings menu)

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: TESTING & VALIDATION                                               │
└─────────────────────────────────────────────────────────────────────────────┘

• execute_device_action(device_id, host_name, actions)
  → Test D-pad sequences directly
  → actions: [{"command": "press_key", "action_type": "remote", "params": {"key": "RIGHT", "wait_time": 1500}}]
  
• execute_edge(tree_id, edge_id, action_set_id)
  → Test specific edge
  → ⭐ ALWAYS test after creation
  
• verify_node(node_id, tree_id, userinterface_name)
  → Run node verifications
  
• take_control(tree_id, device_id, host_name)
  → Required before navigate_to_node
  
• save_node_screenshot(tree_id, node_id, label, host_name, device_id, userinterface_name)
  → Capture reference screenshot

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: NAVIGATION & REVIEW                                                │
└─────────────────────────────────────────────────────────────────────────────┘

• preview_userinterface(userinterface_name)
  → Quick text view of structure
  
• list_navigation_nodes(userinterface_name)
  → All nodes with IDs
  
• navigate_to_node(tree_id, userinterface_name, target_node_label, device_id, host_name)
  → Pathfinding navigation (needs take_control first)

═══════════════════════════════════════════════════════════════════════════════
                    STB/TV D-PAD COMMANDS REFERENCE
═══════════════════════════════════════════════════════════════════════════════

⬆️⬇️⬅️➡️ NAVIGATION KEYS:
   - press_key: {"key": "UP", "wait_time": 1000}
   - press_key: {"key": "DOWN", "wait_time": 1000}
   - press_key: {"key": "LEFT", "wait_time": 1000}
   - press_key: {"key": "RIGHT", "wait_time": 1000}

✅ SELECTION KEYS:
   - press_key: {"key": "OK", "wait_time": 2000}      ← Enter/Select
   - press_key: {"key": "ENTER", "wait_time": 2000}   ← Same as OK

🔙 BACK NAVIGATION:
   - press_key: {"key": "BACK", "wait_time": 2000}    ← Return to previous
   - press_key: {"key": "HOME", "wait_time": 3000}    ← Return to launcher

📺 MEDIA KEYS:
   - press_key: {"key": "PLAY", "wait_time": 1000}
   - press_key: {"key": "PAUSE", "wait_time": 1000}
   - press_key: {"key": "STOP", "wait_time": 1000}
   - press_key: {"key": "REWIND", "wait_time": 1000}
   - press_key: {"key": "FAST_FORWARD", "wait_time": 1000}

🔢 NUMERIC KEYS:
   - press_key: {"key": "0"} through {"key": "9"}

⚠️ CRITICAL: ALL STB commands need action_type: "remote" and wait_time in params!
"""
