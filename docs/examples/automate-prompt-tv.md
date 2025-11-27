# TV/STB Automation Prompt (AI Exploration)

Automate [APP_NAME] for userinterface [USERINTERFACE_NAME] on TV/STB devices.

**Device Model**: `android_tv`, `stb`, or other non-mobile/non-web

**Requirements to cover:**
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]
...

---

## Process

### PHASE 1: Setup & AI Exploration (AUTOMATED)

**1. Get compatible host/device:**
```python
hosts = get_compatible_hosts(userinterface_name='[USERINTERFACE_NAME]')
host_name = hosts['recommended_host']
device_id = hosts['recommended_device']
```

**2. Start AI exploration:**
```python
result = start_ai_exploration(
  userinterface_name='[USERINTERFACE_NAME]',
  original_prompt='Build TV navigation for [APP_TYPE: streaming/IPTV/VOD/etc.]'
)
exploration_id = result['exploration_id']
```

AI analyzes home screen and proposes:
- Strategy: `dpad` (D-pad navigation)
- Menu type: `horizontal`, `vertical`, or `grid`
- Items: Menu positions detected on screen

**3. Approve and create structure:**
```python
approve_exploration_plan(
  exploration_id=exploration_id,
  host_name=host_name,
  userinterface_name='[USERINTERFACE_NAME]',
  selected_items=['tv guide', 'apps', 'watch', 'settings'],  # Menu items
  selected_screen_items=['tv guide', 'apps', 'watch']  # Which screens to create (optional)
)
```

AI creates **DUAL-LAYER navigation automatically**:
- **Focus nodes**: Menu positions (home_tvguide, home_apps, home_watch)
- **Screen nodes**: Actual screens (tvguide, apps, watch)
- **Horizontal edges**: RIGHT/LEFT between focus nodes
- **Vertical edges**: OK/BACK between focus and screen

**4. Validate all edges (depth-first):**
```python
while True:
  result = validate_exploration_edges(
    exploration_id=exploration_id,
    host_name=host_name,
    userinterface_name='[USERINTERFACE_NAME]'
  )
  
  print(f"✅ {result['item']}")
  print(f"   Horizontal: {result['edge_results']['horizontal']}")
  print(f"   Enter (OK): {result['edge_results']['enter']}")
  print(f"   Exit (BACK): {result['edge_results']['exit']}")
  
  if not result.get('has_more_items'):
    break
```

AI tests complete cycles per item:
1. home → home_tvguide: RIGHT
2. home_tvguide ↓ tvguide: OK (screenshot)
3. tvguide ↑ home_tvguide: BACK
4. Repeat for next item

**5. Get and apply verifications:**
```python
suggestions = get_node_verification_suggestions(
  exploration_id=exploration_id,
  host_name=host_name
)

approve_node_verifications(
  exploration_id=exploration_id,
  host_name=host_name,
  userinterface_name='[USERINTERFACE_NAME]',
  approved_verifications=suggestions['suggestions']
)
```

**6. Finalize tree:**
```python
nodes = list_navigation_nodes(userinterface_name='[USERINTERFACE_NAME]')
tree_id = nodes['tree_id']

finalize_exploration(
  exploration_id=exploration_id,
  host_name=host_name,
  tree_id=tree_id
)
```

---

## TV Dual-Layer Architecture (AI Handles Automatically)

### What AI Creates

**Layer 1: Focus Nodes (Menu Positions)**
- Node IDs: `home_tvguide`, `home_apps`, `home_watch`
- Purpose: Represent focus positions in main menu
- Navigation: RIGHT/LEFT (horizontal), DOWN/UP (vertical rows)

**Layer 2: Screen Nodes (Actual Screens)**
- Node IDs: `tvguide`, `apps`, `watch`
- Purpose: Screens that open when pressing OK
- Navigation: OK to enter, BACK to exit

### Example Structure

```
home (existing)
  ↓ RIGHT (1500ms)
home_tvguide (focus)
  ↓ OK (5000ms)
tvguide (screen)
  ↓ BACK (5000ms)
home_tvguide (focus)
  ↓ RIGHT (1500ms)
home_apps (focus)
  ↓ OK (5000ms)
apps (screen)
  ↓ BACK (5000ms)
home_apps (focus)
```

### Automatic Wait Times
- **RIGHT/LEFT/DOWN/UP**: 1500ms
- **OK/BACK**: 5000ms

---

### PHASE 2: Deep Navigation & Subtrees (MANUAL)

**7. Handle deep navigation within screens:**

Many TV apps have nested menus requiring subtrees:
- **Settings**: Settings menu → Network → WiFi settings
- **VOD**: Content catalog → Category → Content detail → Player
- **EPG**: TV Guide → Channel → Program detail

Example - Settings subtree:
```python
# a. Navigate to settings screen
navigate_to_node(
  userinterface_name='[USERINTERFACE_NAME]',
  target_node_label='settings'
)

# b. Create subtree for settings
create_subtree(
  parent_tree_id=tree_id,
  parent_node_id='settings',
  subtree_name='settings_subtree'
)
# Returns: subtree_tree_id

# c. Navigate within settings and create nodes
execute_device_action(
  actions=[
    {'command': 'press_key', 'params': {'key': 'DOWN', 'wait_time': 1500}},
    {'command': 'press_key', 'params': {'key': 'OK', 'wait_time': 3000}}
  ]
)

# d. Inspect settings submenu
elements = dump_ui_elements(device_id=device_id, host_name=host_name, platform='tv')
# Note: May return empty for IR-controlled devices (use screenshots instead)

# e. Create settings submenu nodes
create_node(tree_id=subtree_tree_id, label='network_settings', type='Screen')

create_edge(
  tree_id=subtree_tree_id,
  source_node_id='settings',  # Parent node
  target_node_id='network_settings',
  source_label='settings',
  target_label='network_settings',
  action_sets=[{
    'id': 'settings_to_network',
    'label': 'settings → network_settings',
    'actions': [
      {'command': 'press_key', 'params': {'key': 'DOWN', 'wait_time': 1500}},
      {'command': 'press_key', 'params': {'key': 'OK', 'wait_time': 3000}}
    ],
    'retry_actions': [],
    'failure_actions': []
  }, {
    'id': 'network_to_settings',
    'label': 'network_settings → settings',
    'actions': [
      {'command': 'press_key', 'params': {'key': 'BACK', 'wait_time': 2000}}
    ],
    'retry_actions': [],
    'failure_actions': []
  }]
)
```

Example - VOD content flow:
```python
# Multi-level navigation: home → vod → category → content → player

# Navigate to VOD screen
navigate_to_node(userinterface_name='[USERINTERFACE_NAME]', target_node_label='vod')

# Create subtree for VOD content
create_subtree(parent_tree_id=tree_id, parent_node_id='vod', subtree_name='vod_content')

# Navigate to category, create node
execute_device_action(actions=[
  {'command': 'press_key', 'params': {'key': 'DOWN', 'wait_time': 1500}},
  {'command': 'press_key', 'params': {'key': 'OK', 'wait_time': 3000}}
])

create_node(tree_id=vod_subtree_id, label='category_movies', type='Screen')

# Create edges for category navigation
# ... (similar to settings example)

# Create player node (deep in subtree)
create_node(tree_id=vod_subtree_id, label='player', type='Screen')

create_edge(
  tree_id=vod_subtree_id,
  source_node_id='content_detail',
  target_node_id='player',
  source_label='content_detail',
  target_label='player',
  action_sets=[{
    'id': 'content_to_player',
    'label': 'content_detail → player',
    'actions': [
      {'command': 'press_key', 'params': {'key': 'OK', 'wait_time': 5000}}
    ],
    'retry_actions': [],
    'failure_actions': []
  }]
)
```

---

### PHASE 3: Requirements & Test Cases

**8. Create requirements:**
```python
create_requirement(
  requirement_code='REQ_NAV_001',
  requirement_name='User can navigate main menu with D-pad',
  description='Users must navigate horizontally using RIGHT/LEFT and enter screens with OK',
  priority='P1',
  category='navigation'
)
```

**9. Create test cases:**
```python
generate_and_save_testcase(
  prompt='Navigate from home to TV guide using D-pad, verify TV guide screen loads',
  testcase_name='TC_NAV_01_TVGuideNavigation',
  userinterface_name='[USERINTERFACE_NAME]',
  host_name=host_name,
  device_id=device_id,
  description='Validates TV guide navigation with D-pad',
  folder='navigation',
  tags=['dpad', 'critical']
)
```

**10. Link to requirements:**
```python
link_testcase_to_requirement(
  testcase_id='[TESTCASE_ID]',
  requirement_id='[REQUIREMENT_ID]',
  coverage_type='full'
)
```

**11. Execute end-to-end test:**
```python
execute_testcase(
  testcase_name='TC_NAV_01_TVGuideNavigation',
  host_name=host_name,
  device_id=device_id,
  userinterface_name='[USERINTERFACE_NAME]'
)
```

**12. Verify coverage:**
```python
summary = get_coverage_summary()
print(f"Coverage: {summary['coverage_percentage']}%")
```

---

## TV-Specific Best Practices

### 1. D-pad Keys
```python
# Directional navigation
{'command': 'press_key', 'params': {'key': 'UP'}}
{'command': 'press_key', 'params': {'key': 'DOWN'}}
{'command': 'press_key', 'params': {'key': 'LEFT'}}
{'command': 'press_key', 'params': {'key': 'RIGHT'}}

# Selection
{'command': 'press_key', 'params': {'key': 'OK'}}  # Enter/Select

# Navigation
{'command': 'press_key', 'params': {'key': 'BACK'}}  # Return/Exit

# Special keys (if available)
{'command': 'press_key', 'params': {'key': 'HOME'}}
{'command': 'press_key', 'params': {'key': 'MENU'}}
```

### 2. Wait Times (Critical for TV)
- **RIGHT/LEFT/DOWN/UP**: 1500ms (menu focus animation)
- **OK**: 5000ms (screen loading)
- **BACK**: 5000ms (screen closing)
- **HOME**: 3000ms
- **Video playback**: 8000ms (player initialization)

**Why longer?** TV UIs have animations and slower processors.

### 3. Verification Strategy

**For IR-controlled devices (no UI dump):**
- Use **screenshots** for visual verification
- Text-based verification may not work
- Rely on image comparison or manual inspection

**For Android TV (UI dump available):**
- Use **focused element** as verification
- resource-id of selected menu item
- Screen title or heading

### 4. Menu Types

**Horizontal Menu** (most common):
- Main menu: LEFT/RIGHT to navigate
- OK to enter, BACK to exit
- AI detects automatically

**Vertical Menu** (settings, lists):
- UP/DOWN to navigate
- OK to select, BACK to return
- Create manually in subtrees

**Grid Menu** (VOD catalogs):
- UP/DOWN/LEFT/RIGHT to navigate grid
- OK to select item
- Requires manual creation

---

## Common TV Patterns

### IPTV/Live TV
**Main menu**: TV Guide, Live TV, VOD, Settings

**Subtrees**:
- TV Guide → Channel list → Program detail
- VOD → Categories → Content → Player
- Settings → Network, Display, Audio

### Streaming Box (Roku/Fire TV style)
**Main menu**: Home, Search, My Channels, Settings

**Subtrees**:
- Search → Results → Content
- My Channels → App grid → App details
- Settings → Various settings pages

### STB (Cable/Satellite)
**Main menu**: Live TV, Guide, Recordings, On Demand

**Subtrees**:
- Guide → Channel grid → Program info
- Recordings → Recording list → Playback
- On Demand → Categories → Content browser

---

## Troubleshooting

### Focus position not consistent
- Menu may have variable number of items
- Use position counting: RIGHT × N from known state
- Add focus verification at each step

### OK doesn't open screen
- Wait time may be too short (increase to 5000ms)
- May need multiple key presses
- Check if different key needed (SELECT vs OK)

### BACK doesn't exit screen
- Some apps use HOME or MENU instead
- May need multiple BACK presses
- Test alternative exit methods

### UI dump not available (IR devices)
- This is normal for infrared-controlled devices
- Use screenshots for verification
- Rely on manual navigation pattern discovery
- Test with actual remote timing

### Subtree navigation fails
- Verify parent node is correct start point
- Check tree_id is subtree ID, not parent tree
- Ensure navigation path is repeatable

---

## Time Estimate

**For typical TV app (5 main menu items + 3 subtrees):**
- Phase 1 (AI Exploration - main menu): 15-20 minutes
- Phase 2 (Manual subtrees): 30-45 minutes
- Phase 3 (Requirements & tests): 1 hour
- **Total: ~2-2.5 hours**

**vs. Manual: 6-8 hours**

**Time Saved: ~70%**

---

## Example: IPTV App

```python
# Complete workflow for Horizon TV

# 1. Setup
hosts = get_compatible_hosts(userinterface_name='horizon_tv')

# 2. AI builds main menu (horizontal navigation)
result = start_ai_exploration(
  userinterface_name='horizon_tv',
  original_prompt='Build IPTV navigation'
)

# 3. Approve main menu items
approve_exploration_plan(
  exploration_id=result['exploration_id'],
  host_name=hosts['recommended_host'],
  userinterface_name='horizon_tv',
  selected_items=['tv guide', 'live tv', 'vod', 'settings'],
  selected_screen_items=['tv guide', 'vod', 'settings']  # Skip live tv screen
)

# 4. Validate (dual-layer: focus + screen)
while validate_exploration_edges(...)['has_more_items']: pass

# 5. Add verifications
suggestions = get_node_verification_suggestions(...)
approve_node_verifications(approved_verifications=suggestions['suggestions'])

# 6. Finalize main menu
finalize_exploration(...)

# 7. Manual: Create VOD subtree (categories, content, player)
# ... (see PHASE 2 above)

# 8. Manual: Create Settings subtree (network, display, etc.)
# ... (see PHASE 2 above)

# 9. Requirements & test cases
# ... (see PHASE 3 above)

# Done! ✅
```

---

## Special Considerations

### Channel Zapping
For live TV channel changing:
```python
# UP/DOWN to change channels
create_edge(
  source_node_id='channel_101',
  target_node_id='channel_102',
  action_sets=[{
    'actions': [{'command': 'press_key', 'params': {'key': 'UP', 'wait_time': 2000}}]
  }]
)
```

### Numeric Input (Channel entry)
```python
# Direct channel entry
execute_device_action(
  actions=[
    {'command': 'press_key', 'params': {'key': 'NUM_1', 'wait_time': 500}},
    {'command': 'press_key', 'params': {'key': 'NUM_0', 'wait_time': 500}},
    {'command': 'press_key', 'params': {'key': 'NUM_1', 'wait_time': 500}},
    {'command': 'press_key', 'params': {'key': 'OK', 'wait_time': 3000}}
  ]
)
```

### EPG Navigation
```python
# Grid navigation in electronic program guide
create_edge(
  source_node_id='epg_current',
  target_node_id='epg_next_time',
  action_sets=[{
    'actions': [{'command': 'press_key', 'params': {'key': 'RIGHT', 'wait_time': 1000}}]
  }]
)
```

---

**Recommendation**: Use AI Exploration for main menu (saves 90% time). Manual tools for subtrees and complex navigation patterns.

