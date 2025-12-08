# Autonomous UI Exploration

AI-driven navigation tree building. No human approval gates.

---

## 1. Overview

### What is Autonomous Exploration?

The Explorer agent builds complete navigation models for apps **without human intervention**. It analyzes screens, creates nodes/edges, tests them, and iterates until done.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AUTONOMOUS EXPLORATION FLOW                             │
│                                                                              │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│   │ Analyze │ →  │ Create  │ →  │  Test   │ →  │  Fix    │ →  │  Next   │  │
│   │ Screen  │    │Node/Edge│    │  Edge   │    │ if fail │    │ Screen  │  │
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│        ↑                                                            │       │
│        └────────────────────────────────────────────────────────────┘       │
│                              REPEAT UNTIL COMPLETE                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why Autonomous?

| Aspect | Human Workflow (Old) | Autonomous (New) |
|--------|---------------------|------------------|
| Approval gates | 3+ human reviews | 0 - Agent decides |
| Tools | 7 orchestrated exploration tools | 20+ atomic tools |
| Flexibility | Fixed workflow | Agent-driven decisions |
| Testing | Batch validation at end | Test-per-edge immediately |
| Error recovery | Wait for human | Fix and retry autonomously |
| Speed | Minutes per approval | Continuous operation |

---

## 2. Architecture

### Old: Human-in-the-Loop (Deleted)

```
❌ OLD WORKFLOW (Removed):

start_ai_exploration()     → Human reviews plan
         ↓
approve_exploration_plan() → Human approves
         ↓
validate_exploration_edges()
         ↓
get_node_verification_suggestions()
         ↓
approve_node_verifications() → Human approves
         ↓
finalize_exploration()

Problem: 3 approval gates, agent cannot make decisions
```

### New: Autonomous with Atomic Tools

```
✅ NEW WORKFLOW (Current):

┌────────────────────────────────────────────────────────────────────────────┐
│                          EXPLORER AGENT                                     │
│                                                                            │
│  Has atomic tools for every operation:                                     │
│                                                                            │
│  ANALYZE          BUILD           TEST            ITERATE                  │
│  ─────────        ─────           ────            ────────                 │
│  dump_ui_elements create_node     execute_edge    navigate_to_node         │
│  capture_screenshot create_edge   verify_node     (repeat for each screen) │
│  analyze_screen_* update_node     execute_action                           │
│                   create_subtree                                           │
│                                                                            │
│  Agent decides what to create, tests immediately, fixes if needed          │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tools by Phase

### Phase 1: Discovery

| Tool | Purpose |
|------|---------|
| `get_compatible_hosts` | Find device/host for userinterface |
| `get_device_info` | Check device status and model |
| `list_userinterfaces` | See existing interfaces |
| `get_userinterface_complete` | Get ALL nodes/edges in one call |
| `create_userinterface` | Create new interface + root tree |

### Phase 2: Screen Analysis

| Tool | Platform | Purpose |
|------|----------|---------|
| `dump_ui_elements` | Mobile, Web | Get UI hierarchy (ADB/DOM) |
| `capture_screenshot` | All | Visual capture for AI analysis |
| `analyze_screen_for_action` | All | Find best selector for clicking |
| `analyze_screen_for_verification` | All | Find best element for node detection |

**Platform Availability:**
```
                    dump_ui_elements    capture_screenshot
Mobile (Android)         ✅                   ✅
Web (Playwright)         ✅                   ✅
STB/TV                   ❌                   ✅ (vision only)
```

### Phase 3: Tree Building

| Tool | Purpose |
|------|---------|
| `create_node` | Add screen/focus node to tree |
| `update_node` | Add verifications, update data |
| `delete_node` | Remove node + connected edges |
| `get_node` | Inspect node details |
| `create_edge` | Define navigation path with actions |
| `update_edge` | Fix actions if test fails |
| `delete_edge` | Remove broken edge |
| `get_edge` | Inspect edge details |
| `create_subtree` | Nested tree for deep navigation |

### Phase 4: Testing & Validation

| Tool | Purpose |
|------|---------|
| `execute_device_action` | Direct device commands |
| `execute_edge` | Test specific edge actions |
| `verify_node` | Run node verifications |
| `take_control` | Lock device for navigation |
| `save_node_screenshot` | Attach screenshot to node |

### Phase 5: Navigation & Review

| Tool | Purpose |
|------|---------|
| `preview_userinterface` | Quick text view of tree |
| `list_navigation_nodes` | All nodes with IDs |
| `navigate_to_node` | Pathfinding navigation |

---

## 4. The Autonomous Workflow

### Step 1: Initialize

```python
# 1. Get compatible host/device
result = get_compatible_hosts(userinterface_name='netflix_mobile')
host_name = result['recommended_host']
device_id = result['recommended_device']
tree_id = result['tree_id']

# 2. Check if interface exists (create if not)
interfaces = list_userinterfaces()
# If not found: create_userinterface(name='netflix_mobile', device_model='android_mobile')

# 3. Get existing structure
complete = get_userinterface_complete(userinterface_id=...)

# 4. Take control for navigation
take_control(tree_id=tree_id, device_id=device_id, host_name=host_name)
```

### Step 2: Analyze Screen

```python
# Get all UI elements
elements = dump_ui_elements(device_id=device_id, host_name=host_name)

# Identify navigation targets
for each clickable element:
    action = analyze_screen_for_action(
        elements=elements['elements'],
        intent='login button',  # What we're looking for
        platform='mobile'
    )
    # Returns: {command, action_params, selector_type, score, unique}
```

**Decision Logic:**
```
For each element, decide:
  ├─ Is it navigable? (leads to distinct screen)
  ├─ Is selector unique? (score > 500, unique=true)
  ├─ Is it worth exploring? (not logout, not external)
  └─ Create node + edge if YES to all
```

### Step 3: Create Node + Edge

```python
# Create target node
create_node(
    tree_id=tree_id,
    label='login',
    type='screen',
    position={'x': 200, 'y': 100}
)

# Create bidirectional edge
create_edge(
    tree_id=tree_id,
    source_node_id='home',
    target_node_id='login',
    source_label='home',
    target_label='login',
    action_sets=[
        {
            "id": "home_to_login",
            "label": "home → login",
            "actions": [action['action_params']],  # From analyze_screen_for_action
            "retry_actions": [],
            "failure_actions": []
        },
        {
            "id": "login_to_home",
            "label": "login → home",
            "actions": [{"command": "press_key", "params": {"key": "BACK"}}],
            "retry_actions": [],
            "failure_actions": []
        }
    ]
)
```

### Step 4: Test Immediately

```python
# Test forward navigation
result = execute_edge(
    tree_id=tree_id,
    edge_id='edge-home-login',
    action_set_id='home_to_login'
)

if result.success:
    # Capture screenshot for verification
    screenshot = capture_screenshot(device_id=device_id, host_name=host_name)
    
    # Test return navigation
    result = execute_edge(..., action_set_id='login_to_home')
else:
    # FIX: Re-analyze and update edge
    elements = dump_ui_elements(...)
    new_action = analyze_screen_for_action(elements, 'login button', 'mobile')
    update_edge(tree_id, edge_id, new_action_sets=[...])
    # Retry
```

### Step 5: Add Verifications

```python
# While on login screen, find verification element
verification = analyze_screen_for_verification(
    elements=elements['elements'],
    node_label='login',
    platform='mobile'
)

# Update node with verification
update_node(
    tree_id=tree_id,
    node_id='login',
    updates={
        'data': {
            'verifications': [{
                'command': verification['command'],
                'verification_type': verification['verification_type'],
                'params': verification['params']
            }]
        }
    }
)

# Save reference screenshot
save_node_screenshot(
    tree_id=tree_id,
    node_id='login',
    label='Login Screen',
    host_name=host_name,
    device_id=device_id,
    userinterface_name='netflix_mobile'
)
```

### Step 6: Recursive Exploration

```python
# Navigate to each new node
navigate_to_node(
    tree_id=tree_id,
    userinterface_name='netflix_mobile',
    target_node_label='settings',
    device_id=device_id,
    host_name=host_name
)

# Repeat: Analyze → Create → Test → Verify → Next
```

### Step 7: Final Validation

```python
# Review complete structure
preview = preview_userinterface(userinterface_name='netflix_mobile')

# Test navigation paths
navigate_to_node(..., target_node_label='deepest_node')
navigate_to_node(..., target_node_label='home')
```

---

## 5. Platform-Specific Formats

### Mobile (Android)

```python
# Click action (NO action_type needed)
{
    "command": "click_element_by_id",
    "params": {"element_id": "btn_login"}  # No wait_time at top level
}

# Back navigation
{
    "command": "press_key",
    "params": {"key": "BACK"}
}

# Text input (click field first)
{
    "command": "input_text",
    "params": {"text": "search query"}
}
```

### Web (Playwright)

```python
# Click action (MUST have action_type + wait_time)
{
    "command": "click_element_by_id",
    "action_type": "web",
    "params": {"element_id": "login-btn", "wait_time": 2000}
}

# Text input (uses 'selector' not 'element_text')
{
    "command": "input_text",
    "action_type": "web",
    "params": {"selector": "#email", "text": "user@example.com", "wait_time": 500}
}
```

### STB/TV (D-pad)

```python
# Horizontal navigation (MUST have action_type + wait_time)
{
    "command": "press_key",
    "action_type": "remote",
    "params": {"key": "RIGHT", "wait_time": 1500}
}

# Selection
{
    "command": "press_key",
    "action_type": "remote",
    "params": {"key": "OK", "wait_time": 2000}
}
```

---

## 6. STB/TV Dual-Layer Model

STB/TV uses a special navigation structure:

```
LAYER 1 - FOCUS NODES (Menu positions on home bar):
  home → home_tvguide → home_apps → home_settings
       ←──── LEFT ──── RIGHT ────→

LAYER 2 - SCREEN NODES (Actual screens accessed via OK):
  home_tvguide ──OK──→ tvguide
              ←─BACK─┘
  home_apps ──OK──→ apps
           ←─BACK─┘
```

**Edge Pattern for TV:**
```python
# Horizontal: Focus to Focus
action_sets = [
    {"id": "home_to_tvguide", "actions": [{"command": "press_key", "action_type": "remote", "params": {"key": "RIGHT", "wait_time": 1500}}], ...},
    {"id": "tvguide_to_home", "actions": [{"command": "press_key", "action_type": "remote", "params": {"key": "LEFT", "wait_time": 1500}}], ...}
]

# Vertical: Focus to Screen
action_sets = [
    {"id": "focus_to_screen", "actions": [{"command": "press_key", "action_type": "remote", "params": {"key": "OK", "wait_time": 2000}}], ...},
    {"id": "screen_to_focus", "actions": [{"command": "press_key", "action_type": "remote", "params": {"key": "BACK", "wait_time": 2000}}], ...}
]
```

---

## 7. Decision Making Guidelines

### When to CREATE a Node

✅ Create when:
- Distinct screen with unique content
- Reachable via user interaction
- Has identifiable elements for verification
- Worth including in navigation model

❌ Skip when:
- Popup/toast that disappears quickly
- Loading/splash screens
- Error states
- External websites/apps
- Logout (destructive)

### Selector Priority

```
Best → Worst:

1. Element ID (resource_id / #id)     ← Always unique, most reliable
2. Content description / data-testid  ← Designed for automation
3. XPath                              ← When ID not available
4. Text content                       ← Fragile, avoid if possible
```

### Error Recovery

| Error | Solution |
|-------|----------|
| Element not found | Re-dump elements, check visibility |
| Wrong screen reached | Selector ambiguous, use more specific |
| Timeout | Increase wait_time in params |
| App crash | Report failure, skip this path |
| Back doesn't work | Try alternative (e.g., click home tab) |

---

## 8. Example: Complete Exploration Session

```
## Exploration Summary

**Userinterface:** netflix_mobile
**Device:** sunri-pi1 / device1
**Tree ID:** abc-123-def

### Nodes Created
1. home (entry point)
2. search → Verification: waitForElementToAppear(#search-results-container)
3. profile → Verification: waitForElementToAppear(#profile-settings)
4. content_detail → Verification: waitForElementToAppear(#play-button)

### Edges Created
1. home ↔ search: click(#search-tab) / click(#home-tab)
2. home ↔ profile: click(#profile-icon) / BACK
3. home ↔ content_detail: click(#featured-content) / BACK

### Test Results
- ✅ home → search: SUCCESS
- ✅ search → home: SUCCESS
- ✅ home → profile: SUCCESS
- ⚠️ profile → home: FIXED (BACK didn't work, changed to click #home-tab)
- ✅ home → content_detail: SUCCESS
- ✅ content_detail → home: SUCCESS

### Issues Found
- Profile screen BACK key goes to launcher, not home
  - Fixed: Use explicit click(#home-tab) instead

### Recommended Next Steps
- Explore search results (create subtree)
- Explore content_detail playback states
```

---

## 9. File Structure

```
backend_server/src/agent/
├── agents/
│   └── explorer.py              # Explorer agent with autonomous prompt
├── skills/
│   ├── explorer_mobile_skills.py   # Mobile tools + descriptions
│   ├── explorer_web_skills.py      # Web tools + descriptions
│   └── explorer_stb_skills.py      # STB/TV tools + descriptions
```

---

## 10. Troubleshooting

### "analyze_screen_for_action returns low score"

The element may have ambiguous selectors. Try:
1. Check if element has ID in dump_ui_elements
2. Use more specific intent description
3. Consider using coordinates as last resort

### "Edge test passes but verification fails"

The node verification may be too strict:
1. Re-analyze with `analyze_screen_for_verification`
2. Use more reliable element (ID over text)
3. Check if element appears after delay

### "Cannot navigate back"

Some screens don't respond to BACK key:
1. Check for explicit back button in UI
2. Use alternative navigation (click home tab)
3. Update edge with working return action

### "Subtree not connecting to parent"

Ensure:
1. Parent node exists in parent tree
2. create_subtree returns subtree_tree_id
3. Use subtree_tree_id for all nodes in subtree

---

*Document Version: 1.0*  
*Last Updated: December 2024*  
*Changelog: Initial autonomous exploration documentation*

