# Mobile Automation Prompt (AI Exploration)

Automate [APP_NAME] for userinterface [USERINTERFACE_NAME] on Android mobile devices.

**Device Model**: `android_mobile`

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
  original_prompt='Build navigation for [APP_TYPE: streaming/social/e-commerce/etc.]'
)
exploration_id = result['exploration_id']
```

AI analyzes home screen and proposes:
- Strategy: `click` (touch elements)
- Items: Menu tabs, buttons, screens
- Selectors: resource-id, content-desc, XPath, text

**3. Approve and create structure:**
```python
approve_exploration_plan(
  exploration_id=exploration_id,
  host_name=host_name,
  userinterface_name='[USERINTERFACE_NAME]',
  selected_items=['home', 'search', 'profile', 'settings']  # Customize
)
```

AI creates:
- Nodes for each screen
- Bidirectional edges with click_element_by_id + BACK
- Proper selectors (prioritizes resource-id > content-desc > XPath > text)

**4. Validate all edges:**
```python
while True:
  result = validate_exploration_edges(
    exploration_id=exploration_id,
    host_name=host_name,
    userinterface_name='[USERINTERFACE_NAME]'
  )
  
  print(f"✅ {result['item']}: {result['click_result']}")
  
  if not result.get('has_more_items'):
    break
```

AI tests each edge:
- home → search: click element (resource-id)
- search → home: BACK
- Captures screenshots as proof

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

### PHASE 2: State-Dependent Flows (MANUAL)

**7. Handle authenticated states and deep navigation:**

Common patterns requiring manual handling:
- **Login/Logout**: Authentication flows
- **Deep navigation**: Player controls, content detail screens
- **Dynamic lists**: Search results, product catalogs
- **Swipe gestures**: Tab switching, carousel navigation

Example - Player controls (after play action):
```python
# a. Navigate to content, then play
navigate_to_node(
  userinterface_name='[USERINTERFACE_NAME]',
  target_node_label='content_detail'
)

# b. Trigger play action (not part of navigation tree)
execute_device_action(
  actions=[
    {'command': 'click_element', 'params': {'text': 'Play', 'wait_time': 3000}}
  ]
)

# c. Inspect player screen
elements = dump_ui_elements(device_id=device_id, host_name=host_name, platform='mobile')

# d. Analyze for player controls
action = analyze_screen_for_action(
  elements=elements['elements'],
  intent='pause button',
  platform='mobile'
)

# e. Create player node and edge
create_node(tree_id=tree_id, label='player', type='Screen')

create_edge(
  tree_id=tree_id,
  source_node_id='content_detail',
  target_node_id='player',
  source_label='content_detail',
  target_label='player',
  action_sets=[{
    'id': 'content_to_player',
    'label': 'content_detail → player',
    'actions': [{'command': 'click_element', 'params': {'text': 'Play', 'wait_time': 3000}}],
    'retry_actions': [],
    'failure_actions': []
  }, {
    'id': 'player_to_content',
    'label': 'player → content_detail',
    'actions': [{'command': 'press_key', 'params': {'key': 'BACK', 'wait_time': 1500}}],
    'retry_actions': [],
    'failure_actions': []
  }]
)

# f. Test edge
execute_edge(edge_id='edge-...', tree_id=tree_id, userinterface_name='[USERINTERFACE_NAME]')
```

Example - Swipe navigation (tab switching):
```python
# For horizontal tab navigation
create_edge(
  tree_id=tree_id,
  source_node_id='tab_home',
  target_node_id='tab_search',
  source_label='tab_home',
  target_label='tab_search',
  action_sets=[{
    'id': 'home_to_search_swipe',
    'label': 'tab_home → tab_search',
    'actions': [{'command': 'swipe', 'params': {'direction': 'left', 'wait_time': 1000}}],
    'retry_actions': [],
    'failure_actions': []
  }, {
    'id': 'search_to_home_swipe',
    'label': 'tab_search → tab_home',
    'actions': [{'command': 'swipe', 'params': {'direction': 'right', 'wait_time': 1000}}],
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
  requirement_code='REQ_PLAY_001',
  requirement_name='User can play video content',
  description='Users must be able to select and play video content',
  priority='P1',
  category='playback'
)
```

**9. Create test cases:**
```python
generate_and_save_testcase(
  prompt='Navigate to content detail, verify content loads, navigate to player, verify playback',
  testcase_name='TC_PLAY_01_BasicPlayback',
  userinterface_name='[USERINTERFACE_NAME]',
  host_name=host_name,
  device_id=device_id,
  description='Validates basic video playback flow',
  folder='playback',
  tags=['video', 'critical']
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
  testcase_name='TC_PLAY_01_BasicPlayback',
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

## Mobile-Specific Best Practices

### 1. Selector Priority (AI handles automatically)
1. **resource-id** - Most reliable, unique per screen
2. **content-desc** - Accessibility labels
3. **//xpath** - For specific elements: `//android.widget.Button[@text='Login']`
4. **text** - Fallback, can change with localization

### 2. Action Types
```python
# Click/Tap
{'command': 'click_element_by_id', 'params': {'element_id': 'search_button'}}

# Swipe
{'command': 'swipe', 'params': {'direction': 'up'}}  # up, down, left, right

# Input text (after click to focus)
{'command': 'click_element_by_id', 'params': {'element_id': 'search_field'}},
{'command': 'input_text', 'params': {'text': 'query'}}

# Back navigation
{'command': 'press_key', 'params': {'key': 'BACK'}}
```

### 3. Wait Times
- Click element: 1000-2000ms
- Swipe: 500-1000ms
- Input text: 500ms
- BACK: 1500ms
- Video playback: 3000-5000ms

### 4. Verification Strategy
Use **stable structural elements**:
- ✅ Tab labels: "Home", "Search", "Profile"
- ✅ Headings: "Trending", "My Library"
- ✅ resource-id: Stable across versions
- ❌ Dynamic content: Video titles, thumbnails, dates

---

## Common Mobile Patterns

### Streaming App
**Nodes**: home, search, content_detail, player, my_library, settings

**Example edges**:
- home → search: click search icon (resource-id)
- content_detail → player: click "Play"
- player → content_detail: BACK

**Swipe navigation**:
- home ↔ search: swipe left/right (tab switching)

### Social Media App
**Nodes**: feed, profile, messages, notifications, settings

**Example edges**:
- feed → profile: click profile icon
- feed → messages: click messages icon
- Vertical swipe: refresh feed (swipe down)

### E-commerce App
**Nodes**: home, product_catalog, product_detail, cart, checkout, account

**Example edges**:
- home → product_catalog: click category
- product_detail → cart: click "Add to Cart", click cart icon
- Horizontal swipe: browse product images

---

## Troubleshooting

### Element not found
1. Check if resource-id changed:
   ```python
   elements = dump_ui_elements(device_id=device_id, host_name=host_name, platform='mobile')
   # Inspect actual resource-id values
   ```

2. Re-analyze for better selector:
   ```python
   action = analyze_screen_for_action(
     elements=elements['elements'],
     intent='[ELEMENT_DESCRIPTION]',
     platform='mobile'
   )
   ```

3. Update edge:
   ```python
   update_edge(
     tree_id=tree_id,
     edge_id='[EDGE_ID]',
     action_sets=[...]  # New actions with updated selectors
   )
   ```

### BACK doesn't return to expected screen
- Some apps use custom back stack
- Use explicit navigation instead of BACK
- Test and adjust based on app behavior

### Swipe doesn't work reliably
- Increase wait_time after swipe
- Use click on tabs instead of swipe if available
- Consider coordinates-based swipe if needed

### Verification fails intermittently
- Elements may load asynchronously
- Increase timeout in verification params
- Use resource-id instead of text (more stable)

---

## Time Estimate

**For typical mobile app (7 nodes, 14 edges):**
- Phase 1 (AI Exploration): 10-15 minutes
- Phase 2 (Manual deep flows): 20-30 minutes
- Phase 3 (Requirements & tests): 1 hour
- **Total: ~1.5-2 hours**

**vs. Manual: 5-6 hours**

**Time Saved: ~70%**

---

## Example: Streaming App

```python
# Complete workflow for Netflix mobile

# 1. Setup
hosts = get_compatible_hosts(userinterface_name='netflix_mobile')

# 2. AI builds tree (home, search, my_list, etc.)
result = start_ai_exploration(
  userinterface_name='netflix_mobile',
  original_prompt='Build streaming app navigation'
)

# 3. Approve (home, search, my_list, settings)
approve_exploration_plan(
  exploration_id=result['exploration_id'],
  host_name=hosts['recommended_host'],
  userinterface_name='netflix_mobile',
  selected_items=['home', 'search', 'my_list', 'settings']
)

# 4. Validate
while validate_exploration_edges(...)['has_more_items']: pass

# 5. Add verifications
suggestions = get_node_verification_suggestions(...)
approve_node_verifications(approved_verifications=suggestions['suggestions'])

# 6. Finalize
finalize_exploration(...)

# 7. Manual: Add content_detail → player (deep navigation)
# ... (see PHASE 2 above)

# 8. Requirements & test cases
# ... (see PHASE 3 above)

# Done! ✅
```

---

## Launch App Pattern

For apps not already running:
```python
# Entry → home edge should launch app
create_edge(
  tree_id=tree_id,
  source_node_id='entry',
  target_node_id='home',
  source_label='entry',
  target_label='home',
  action_sets=[{
    'id': 'entry_to_home',
    'label': 'entry → home',
    'actions': [
      {'command': 'launch_app', 'params': {'package': 'com.netflix.mediaclient', 'wait_time': 8000}}
    ],
    'retry_actions': [],
    'failure_actions': []
  }]
)
```

---

**Recommendation**: Use AI Exploration for 90% of mobile automation. Manual tools for deep navigation and state flows.

