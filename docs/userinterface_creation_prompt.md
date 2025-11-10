# Automated UserInterface Creation Prompt

## 🎯 Purpose

This prompt guides automation engineers to quickly generate navigation tree models for new apps (Netflix, YouTube, etc.) using MCP primitive tools. The result is a complete, testable userinterface with nodes, edges, and verifications.

---

## 📋 Prerequisites

**Required Information:**
- App name: `<app_name>` (e.g., "netflix", "youtube")
- Device model: `<device_model>` (e.g., "android_mobile", "android_tv", "web")
- App package: `<package_name>` (e.g., "com.netflix.mediaclient")
- Device location: `<device_id>` @ `<host_name>` (e.g., "device1" @ "sunri-pi1")
- Main screens to cover: List 4-6 primary navigation targets

**Tools Required:**
- All MCP primitive tools available
- Device connected and accessible
- App installed on device

---

## ⏱️ Action Wait Time Standards

**CRITICAL:** All actions MUST include proper wait times to prevent race conditions and ensure reliable automation.

### Standard Wait Times Table

| Operation | Wait Time (ms) | When to Use |
|-----------|----------------|-------------|
| **launch_app** | 8000 | Entry→Home (app launch) |
| **click_element** | 2000 | Tab navigation, menu items |
| **tap_coordinates** | 2000 | Screen taps |
| **press_key (BACK)** | 1500 | Back navigation |
| **press_key (other)** | 1000 | Other keys |
| **type_text** | 1000 | Text input |
| **Video operations** | 5000 | Player initialization |
| **Content load** | 3000 | Heavy pages with images |

### Critical Rules

1. **wait_time goes INSIDE params** field, NOT as top-level
2. **Always in milliseconds** (1 second = 1000ms)
3. **Missing wait_time = race condition = unreliable test**
4. **Increase by +2000ms** if operation fails due to timing

### Example Structure

```json
✅ CORRECT:
{
  "command": "launch_app",
  "params": {
    "package": "com.example.app",
    "wait_time": 8000
  }
}

❌ WRONG:
{
  "command": "launch_app",
  "params": {"package": "com.example.app"},
  "delay": 8000
}
```

**See:** [MCP Action Tools - Wait Time Guidelines](mcp/mcp_tools_action.md#⏱️-action-wait-time-guidelines) for complete reference.

---

## 🚀 The Prompt

```markdown
# Build Navigation Tree for <APP_NAME>

## Context
I'm an automation engineer validating the <APP_NAME> app. I need to quickly generate a complete userinterface model with main nodes, actions, and verifications for testing.

## Configuration
- **App**: <app_name> (<package_name>)
- **Device Model**: <device_model>
- **Device**: <device_id> @ <host_name>
- **Coverage**: Main screens only (home, search, profile, settings, etc.)
- **Quality Standard**: All edges tested and working, 1+ verification per node

---

## Phase 1: Setup & Discovery

### Step 1: Check Existing UserInterface
```
list_userinterfaces()
```
**Action:**
- Search output for `<app_name>_<device_model>` (e.g., "netflix_mobile")
- If EXISTS → Note the `root_tree.id` and SKIP to Phase 2
- If NOT EXISTS → Proceed to Step 2

---

### Step 2: Create UserInterface (if needed)
```
create_userinterface({
    "name": "<app_name>_<device_model>",
    "device_model": "<device_model>",
    "description": "<APP_NAME> <Device Model> UI Model"
})
```
**Expected Response:**
```json
{
  "userinterface_id": "abc-123-def",
  "root_tree_id": "tree-xyz-789"
}
```
**Action:** Save `root_tree_id` as `TREE_ID` for all subsequent steps

---

### Step 3: Take Device Control
```
take_control({
    "tree_id": "<TREE_ID>",
    "device_id": "<device_id>",
    "host_name": "<host_name>"
})
```
**Critical:** This MUST succeed before any device operations

---

### Step 4: Launch Application

**⚠️ ANDROID DEVICES ONLY: Force Close First**

For `android_mobile` and `android_tv`, the entry→home edge MUST close the app before launching to ensure a clean state:

```
execute_edge({
    "edge_id": "edge-entry-node-to-home",
    "tree_id": "<TREE_ID>"
})
```

**Default Entry→Home Edge Structure:**
- **For Android**: close_app → launch_app → (optional dismiss popup)
- **For Web/STB**: Just launch_app or navigate

**Why Android Needs This:**
- If app is already running, `launch_app` resumes where user left off (not home screen)
- `close_app` uses `am force-stop` to ensure clean launch
- This prevents navigation failures when tests run multiple times

**Example Android Entry→Home Actions:**
```json
{
  "actions": [
    {"command": "close_app", "params": {"package": "com.example.app", "wait_time": 1000}},
    {"command": "launch_app", "params": {"package": "com.example.app", "wait_time": 8000}}
  ]
}
```

**Validation:** Wait 8-10 seconds for app to fully load before proceeding

---

### Step 5: Discover Device Capabilities
```
list_actions({
    "device_id": "<device_id>",
    "host_name": "<host_name>"
})

list_verifications({
    "device_id": "<device_id>",
    "host_name": "<host_name>"
})
```
**Action:** Review available commands for later use (click_element, press_key, waitForElementToAppear, etc.)

---

## Phase 2: Explore Home Screen

### Step 6: Dump UI Elements
```
dump_ui_elements({
    "device_id": "<device_id>",
    "platform": "<mobile|tv|web>"
})
```
**Expected Output:**
```json
{
  "elements": [
    {"text": "Search", "clickable": true, "resource-id": "search_tab"},
    {"text": "Home", "clickable": true, "resource-id": "home_tab"},
    {"text": "My List", "clickable": true, "resource-id": "mylist_tab"}
  ]
}
```

---

### Step 7: Visual Confirmation
```
capture_screenshot({
    "device_id": "<device_id>"
})
```
**Action:** Review screenshot to confirm what's visible

---

### Step 8: Identify Navigation Targets
**Analyze Step 6 output and identify:**
- Tab bars (bottom navigation)
- Persistent UI elements
- Main feature screens

**Create Target List:**
```
Primary Targets: ["search", "profile", "downloads", "settings"]
```

**For each target, assign:**
- Node label (lowercase, no spaces): e.g., "search"
- Element identifier from dump: e.g., "Search" or "search_tab"
- Position (x coordinate): 200, 400, 600, 800 (space evenly)

---

## Phase 3: Build Navigation Tree (Repeat for EACH Target)

### Step 9: Test Navigation Action FIRST
```
execute_device_action({
    "device_id": "<device_id>",
    "actions": [{
        "command": "click_element",
        "params": {"element_id": "<target_element>"},
        "delay": 2000
    }]
})
```
**Validation:**
- ✅ Success? → Proceed to Step 10
- ❌ Failed? → Try different element_id/text/resource-id, retry Step 9

---

### Step 10: Verify Screen Changed
```
dump_ui_elements({
    "device_id": "<device_id>",
    "platform": "<platform>"
})

capture_screenshot({
    "device_id": "<device_id>"
})
```
**Validation:**
- New elements visible? ✅ Good!
- Still on same screen? ❌ Fix action in Step 9

---

### Step 11: Identify Verification Element
**From Step 10 dump output, find:**
- Unique element that proves we're on this screen
- Example: Search screen → "Search for a title"
- Example: Profile screen → "Account"

**Save:** `verification_element = "<unique_text>"`

---

### Step 12: Create Node
```
create_node({
    "tree_id": "<TREE_ID>",
    "label": "<target_label>",
    "type": "screen",
    "position": {"x": <x_coordinate>, "y": 0}
})
```
**Example:**
```
create_node({
    "tree_id": "tree-xyz-789",
    "label": "search",
    "type": "screen",
    "position": {"x": 200, "y": 0}
})
```

---

### Step 13: Add Verification to Node
```
update_node({
    "tree_id": "<TREE_ID>",
    "node_id": "<target_label>",
    "updates": {
        "verifications": [{
            "command": "waitForElementToAppear",
            "params": {
                "search_term": "<verification_element>",
                "timeout": 10
            },
            "verification_type": "adb"
        }]
    }
})
```

---

### Step 14: Test Verification
```
verify_node({
    "node_id": "<target_label>",
    "tree_id": "<TREE_ID>",
    "userinterface_name": "<app_name>_<device_model>"
})
```
**Validation:**
- ✅ Pass (1/1)? → Proceed to Step 15
- ❌ Fail? → Fix verification_element in Step 13, retry

---

### Step 15: Test Navigation Back
```
execute_device_action({
    "device_id": "<device_id>",
    "actions": [{
        "command": "press_key",
        "params": {"key": "BACK"},
        "delay": 1500
    }]
})
```
**Alternative (for tabs):**
```
execute_device_action({
    "device_id": "<device_id>",
    "actions": [{
        "command": "click_element",
        "params": {"element_id": "Home"},
        "delay": 2000
    }]
})
```
**Validation:** Confirm we're back on home screen (dump or screenshot)

---

### Step 16: Create Bidirectional Edge
```
create_edge({
    "tree_id": "<TREE_ID>",
    "source_node_id": "home",
    "target_node_id": "<target_label>",
    "source_label": "home",
    "target_label": "<target_label>",
    "action_sets": [
        {
            "id": "home_to_<target_label>",
            "label": "home → <target_label>",
            "actions": [{
                "command": "click_element",
                "params": {"element_id": "<target_element>"},
                "delay": 2000
            }],
            "retry_actions": [],
            "failure_actions": []
        },
        {
            "id": "<target_label>_to_home",
            "label": "<target_label> → home",
            "actions": [{
                "command": "press_key",
                "params": {"key": "BACK"},
                "delay": 1500
            }],
            "retry_actions": [],
            "failure_actions": []
        }
    ]
})
```

---

### Step 17: Test Edge End-to-End
```
execute_edge({
    "edge_id": "<edge_id_from_step_16>",
    "tree_id": "<TREE_ID>"
})
```
**Validation:**
- ✅ Works? → Excellent! Move to next target
- ❌ Fails? → Debug with dump_ui_elements, fix edge, retry

---

### Step 18: Repeat for All Targets
**Go back to Step 9 for each remaining target:**
- Target 2: profile
- Target 3: downloads
- Target 4: settings
- etc.

---

## Phase 4: Validation & Finalization

### Step 19: Test Full Navigation
```
navigate_to_node({
    "tree_id": "<TREE_ID>",
    "userinterface_name": "<app_name>_<device_model>",
    "target_node_label": "search"
})

navigate_to_node({
    "tree_id": "<TREE_ID>",
    "userinterface_name": "<app_name>_<device_model>",
    "target_node_label": "profile"
})
```
**What This Tests:**
- Pathfinding algorithm
- All edges work correctly
- Verifications pass automatically

---

### Step 20: Review Complete Structure
```
get_userinterface_complete({
    "userinterface_id": "<userinterface_id_from_step_2>"
})
```
**Validation Checklist:**
- ✅ All planned nodes created?
- ✅ All edges bidirectional?
- ✅ All nodes have verifications?
- ✅ Node count matches target count?
- ✅ Edge count = 2 × node_count (for bidirectional)?

---

### Step 21: List Final Nodes & Edges
```
list_nodes({
    "tree_id": "<TREE_ID>"
})

list_edges({
    "tree_id": "<TREE_ID>"
})
```
**Action:** Document the final structure for team reference

---

### Step 22: Release Control
```
release_control({
    "device_id": "<device_id>",
    "host_name": "<host_name>"
})
```
**Critical:** Always release control when done!

---

## ✅ Success Criteria

Your userinterface is complete when:
- ✅ 4-6 main nodes created (home + targets)
- ✅ 4-6 bidirectional edges (8-12 action_sets total)
- ✅ Every node has 1+ verification
- ✅ All edges tested with `execute_edge`
- ✅ Full navigation tested with `navigate_to_node`
- ✅ `get_userinterface_complete` shows complete structure
- ✅ Control released

---

## 🎯 Key Principles

1. **Test-First** → Always test actions BEFORE creating nodes/edges
2. **Iterative** → Fix failures immediately, don't continue with broken edges
3. **Verification-First** → Identify verification element BEFORE creating node
4. **Bidirectional** → Always create forward + backward action_sets
5. **Visual Confirmation** → Use screenshots when in doubt
6. **No Assumptions** → Use dump_ui_elements to see actual element names
7. **Validate Everything** → Test edges individually, then test full navigation

---

## ⏱️ Time Estimate

- **Setup (Phase 1)**: 2 minutes
- **Per Node/Edge (Phase 3)**: 3-5 minutes (with testing)
- **Validation (Phase 4)**: 2 minutes
- **Total for 5 nodes**: ~20-30 minutes

---

## 🐛 Error Handling

### If Step 9 Fails (Action doesn't work)
1. Run `dump_ui_elements()` again
2. Look for alternative element identifiers:
   - Try `text` instead of `resource-id`
   - Try `resource-id` instead of `text`
   - Try `content-desc` if available
3. Check element is `clickable: true`
4. Add longer delay (3000ms instead of 2000ms)
5. Retry Step 9

### If Step 10 Fails (Screen didn't change)
1. Capture screenshot to confirm
2. Element might not be clickable → choose different element
3. Action might need longer delay → increase delay
4. App might have modal/popup → handle popup first
5. Go back to Step 9

### If Step 14 Fails (Verification fails)
1. Run `dump_ui_elements()` on target screen
2. Find different unique element
3. Check spelling/capitalization exactly
4. Update Step 13 with correct element
5. Retry Step 14

### If Step 17 Fails (Edge execution fails)
1. Check which action_set failed (forward or backward)
2. Run `dump_ui_elements()` to see current state
3. Update `create_edge` with correct actions
4. Use `update_edge` to fix existing edge
5. Retry Step 17

### If Stuck
1. Use `capture_screenshot()` for visual debugging
2. Use `dump_ui_elements()` to see actual UI state
3. Document the issue
4. Skip that node and move to next target
5. Return to problematic node after completing others

---

## 🚀 Advanced: Subtrees (Optional)

For apps with deeper navigation (e.g., Settings → Account → Privacy):

### Step 23: Create Subtree
```
create_subtree({
    "parent_tree_id": "<TREE_ID>",
    "parent_node_id": "settings",
    "subtree_name": "settings_subtree"
})
```
**Returns:** `subtree_tree_id`

### Step 24: Navigate to Parent
```
navigate_to_node({
    "tree_id": "<TREE_ID>",
    "userinterface_name": "<app_name>_<device_model>",
    "target_node_label": "settings"
})
```

### Step 25: Explore Subtree
Repeat Phase 2-3 using `subtree_tree_id` instead of `TREE_ID`

---

## 📊 Example Complete Workflow

### Netflix Mobile Example

**Phase 1: Setup**
```
create_userinterface → netflix_mobile
take_control → device1@sunri-pi1
execute_edge → Launch Netflix
list_actions → See available commands
```

**Phase 2: Discovery**
```
dump_ui_elements → Found: Home, Search, Coming Soon, Downloads, More
capture_screenshot → Confirmed bottom navigation bar
```

**Phase 3: Build (4 targets)**
```
Target 1: search
  → Test click → ✅
  → Verify element → "Top Searches"
  → Create node → search
  → Add verification → waitForElementToAppear("Top Searches")
  → Test verification → ✅
  → Create edge → home ↔ search
  → Test edge → ✅

Target 2: downloads
  → Test click → ✅
  → Verify element → "Smart Downloads"
  → Create node → downloads
  → Add verification → waitForElementToAppear("Smart Downloads")
  → Test verification → ✅
  → Create edge → home ↔ downloads
  → Test edge → ✅

[Repeat for "coming_soon" and "more"]
```

**Phase 4: Validation**
```
navigate_to_node(search) → ✅
navigate_to_node(downloads) → ✅
get_userinterface_complete → 5 nodes, 8 edges, all verified
release_control → Done!
```

**Result:** Complete netflix_mobile model in ~25 minutes

---

## 📚 Reference

**Tool Documentation:** See `docs/mcp.md` for detailed tool reference

**Key Tools Used:**
- `create_userinterface` - Setup
- `take_control` / `release_control` - Device management
- `dump_ui_elements` - Discovery
- `execute_device_action` - Testing actions
- `create_node` / `update_node` - Node creation
- `create_edge` - Edge creation
- `execute_edge` - Edge testing
- `verify_node` - Verification testing
- `navigate_to_node` - Full navigation testing
- `get_userinterface_complete` - Structure review

---

## 💡 Tips for Automation Engineers

1. **Start Small** - Build 2-3 nodes first, validate, then expand
2. **Test Frequently** - Test each edge immediately after creation
3. **Document Issues** - Note any problematic screens for later
4. **Use Screenshots** - Visual reference prevents mistakes
5. **Verify First** - Good verifications = reliable testing
6. **Naming Conventions** - Use lowercase, no spaces, descriptive labels
7. **Save Progress** - Use `list_nodes` periodically to confirm structure
8. **Reuse Patterns** - Once you have working actions, reuse them

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-10  
**Compatible with**: MCP Server v4.2.0+

