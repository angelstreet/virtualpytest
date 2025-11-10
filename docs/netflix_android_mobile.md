# Netflix Android Mobile - Test Automation Prompt

## 🎯 Goal

Build complete Netflix Android mobile test automation: create UI model, define requirements, generate testcases from navigation graph, execute tests, and report coverage.

---

## 📱 Context

- **App:** Netflix (com.netflix.mediaclient)
- **Device:** android_mobile (device_id: device1)
- **Host:** sunri-pi1
- **Assumptions:**
  - User already logged in (skip authentication testing)
  - Default language (skip multi-language testing)
  - Device connected and app installed
  - Network connectivity available

---

## ⏱️ Action Delay Standards

**CRITICAL:** All edge actions MUST include proper `delay` fields to ensure reliable navigation.

### Standard Delays
- **launch_app:** 8000ms (app initialization)
- **click_element:** 2000ms (screen transitions)
- **tap_coordinates:** 2000ms (screen taps)
- **press_key (BACK):** 1500ms (back navigation)
- **press_key (other):** 1000ms (key presses)
- **video playback:** 5000ms (player init)
- **content load:** 3000ms (heavy pages)

### Critical Rules
1. **delay is TOP-LEVEL** field in action object, NOT in params
2. **Always in milliseconds** (1 second = 1000ms)
3. **Missing delay = immediate execution = race condition**

### Example
```json
✅ CORRECT:
{
  "command": "launch_app",
  "params": {"package": "com.netflix.mediaclient"},
  "delay": 8000
}

❌ WRONG:
{
  "command": "launch_app",
  "params": {"package": "com.netflix.mediaclient", "delay": 8000}
}
```

**See:** [MCP Action Tools - Delay Guidelines](mcp/mcp_tools_action.md#⏱️-action-delay-guidelines)

---

## 📋 Phase 1: Build Navigation Model (45 minutes)

### Step 1: Create User Interface
Create userinterface "netflix_mobile" for device_model "android_mobile"

### Step 2: Launch & Discover
1. Launch Netflix app (package: com.netflix.mediaclient, delay: 8000ms)
2. Dump UI elements to identify all clickable elements and their IDs
3. Capture screenshot for visual reference
4. Get tree_id using list_navigation_nodes

### Step 3: Create Nodes
Create nodes for key screens (entry and home already exist):
- **search** - Search functionality screen
- **content_detail** - Content information page
- **player** - Video playback screen
- **downloads** - Downloaded content screen
- **more** - Profile/settings screen

### Step 4: Create Edges
Create edges with bidirectional action_sets using actual element_ids from UI dump:

1. **entry → home** (update existing edge)
   - **CRITICAL**: First close_app (com.netflix.mediaclient, wait_time 1000ms) to ensure clean state
   - Then: launch_app with package com.netflix.mediaclient, wait_time 8000ms
   - Then: tap_coordinates to dismiss popup, wait_time 2000ms
   - **Why**: If app is already running, launch_app won't return to home screen. Always close first!

2. **home ↔ search**
   - Forward: click_element on search tab, wait_time 2000ms
   - Backward: click_element on home tab, wait_time 2000ms

3. **home → content_detail**
   - Forward: click_element on first content card, wait_time 2000ms
   - Backward: press_key BACK, wait_time 1500ms

4. **content_detail → player**
   - Forward: click_element on play button, wait_time 5000ms
   - Backward: press_key BACK, wait_time 1500ms

5. **home ↔ downloads**
   - Forward: click_element on downloads tab, wait_time 2000ms
   - Backward: click_element on home tab, wait_time 2000ms

6. **home ↔ more**
   - Forward: click_element on more/profile tab, wait_time 2000ms
   - Backward: click_element on home tab, wait_time 2000ms

7. **search → content_detail**
   - Forward: click_element on search input, type_text "Stranger Things", click_element on first result
   - Backward: press_key BACK, wait_time 1500ms

**Format:** All edges must have action_sets with id, label, actions, retry_actions, failure_actions. Use element_id from UI dump, not guesses.

**Example JSON structure for entry → home edge:**
```json
{
  "id": "entry_to_home",
  "label": "entry → home",
  "actions": [
    {"command": "close_app", "params": {"package": "com.netflix.mediaclient", "wait_time": 1000}},
    {"command": "launch_app", "params": {"package": "com.netflix.mediaclient", "wait_time": 8000}},
    {"command": "tap_coordinates", "params": {"x": 540, "y": 1645, "wait_time": 2000}}
  ],
  "retry_actions": [],
  "failure_actions": []
}
```

### Step 5: Add Verifications
Update each node with verifications using update_node:

- **home:** waitForElementToAppear with text "Home" or home indicator, timeout 5000ms
- **search:** waitForElementToAppear with search input element_id, timeout 5000ms
- **content_detail:** waitForElementToAppear with play button element_id, timeout 5000ms
- **player:** waitForElementToAppear with player controls element_id, timeout 10000ms
- **downloads:** waitForElementToAppear with text "Downloads", timeout 5000ms
- **more:** waitForElementToAppear with text "Account" or "Profile", timeout 5000ms

### Step 6: Validate Navigation Tree (CRITICAL - DO NOT SKIP)

**This step MUST be completed before Phase 3 (creating testcases).**

Test and validate EVERY edge and node to ensure the navigation tree works:

#### 6.1: Test Entry → Home Edge
```
execute_edge for entry→home edge
- If fails: dump_ui_elements, check element_ids, update_edge with correct actions
- Verify app launches and reaches home screen
```

#### 6.2: Test Each Node Navigation
For each node (home, search, content_detail, player, downloads, more):
```
navigate_to_node(target_node_label='node_name')
- If fails: check logs, dump UI, verify edge actions
- Fix edge actions with correct element_ids
- Retry until success
```

#### 6.3: Test Each Node Verification
For each node:
```
verify_node(node_id='node_name')
- If fails: dump_ui_elements to see actual elements on screen
- Update node verifications with correct element_ids/text
- Retry until verification passes
```

#### 6.4: Test Critical Edges Individually
```
execute_edge for home→search
execute_edge for search→home
execute_edge for home→content_detail
execute_edge for content_detail→player
execute_edge for player→content_detail (back button)
- Debug and fix each edge that fails
```

#### 6.5: Full Navigation Path Test
```
navigate_to_node from entry to each node in sequence:
entry → home → search → downloads → more → home
entry → home → content_detail → player
- Ensure complete navigation flow works end-to-end
```

**SUCCESS CRITERIA**: All nodes reachable, all verifications pass, all edges work bidirectionally.

**DO NOT proceed to Phase 3 until this step is 100% complete!**

---

## 📝 Phase 2: Define Requirements (10 minutes)

Create 12 requirements using backend Requirements API:

### P1 Critical Requirements (6)

1. **REQ_PLAYBACK_001**
   - Title: User can play video content
   - Description: Users must be able to select and play video content from the catalog
   - Priority: P1
   - Category: playback

2. **REQ_PLAYBACK_002**
   - Title: User can pause and resume video
   - Description: Users can pause video playback and resume from the same position
   - Priority: P1
   - Category: playback

3. **REQ_PLAYBACK_003**
   - Title: User can exit video playback
   - Description: Users can exit video player and return to previous screen
   - Priority: P1
   - Category: playback

4. **REQ_NAV_001**
   - Title: User can navigate between main tabs
   - Description: Users can switch between Home, Search, Downloads, and More tabs
   - Priority: P1
   - Category: navigation

5. **REQ_NAV_002**
   - Title: User can access content detail page
   - Description: Users can view detailed information about content by clicking on it
   - Priority: P1
   - Category: navigation

6. **REQ_NAV_003**
   - Title: User can return to previous screen using back button
   - Description: Android back button navigation works correctly throughout the app
   - Priority: P1
   - Category: navigation

### P2 High Priority Requirements (6)

7. **REQ_SEARCH_001**
   - Title: User can search for content by title
   - Description: Users can use search functionality to find content by entering title
   - Priority: P2
   - Category: search

8. **REQ_SEARCH_002**
   - Title: User can view search results
   - Description: Search results are displayed with relevant content matching the query
   - Priority: P2
   - Category: search

9. **REQ_SEARCH_003**
   - Title: User can navigate to content from search results
   - Description: Users can click on search results to view content details
   - Priority: P2
   - Category: search

10. **REQ_UI_001**
    - Title: App launches within acceptable time
    - Description: Netflix app launches and displays home screen within 5 seconds
    - Priority: P2
    - Category: ui

11. **REQ_UI_002**
    - Title: Screen transitions are smooth
    - Description: All screen transitions complete within 3 seconds
    - Priority: P2
    - Category: ui

12. **REQ_UI_003**
    - Title: Content images load correctly
    - Description: Content thumbnails and images load and display correctly
    - Priority: P2
    - Category: ui

---

## 🧪 Phase 3: Create Testcases from Graph (30 minutes)

### 🎯 CRITICAL CONCEPT - NAVIGATION IS AUTONOMOUS

**Understanding the Two-Layer Architecture:**

**Layer 1: Navigation Tree (Phase 1 - App-Specific)**
- ✅ Already defines HOW to move between screens
- ✅ Contains all click actions, delays, element IDs
- ✅ Example: `home -(click "The Witcher")→ content_detail -(click "Play")→ player`
- ✅ Built once per app (Netflix, YouTube, Hulu each have their own tree)

**Layer 2: Test Cases (Phase 3 - Reusable)**
- ✅ Defines WHAT to test, not HOW to navigate
- ✅ Uses navigation nodes that reference tree node labels
- ✅ Example: `{"type": "navigation", "data": {"target_node_label": "player"}}`
- ✅ Reusable across apps by changing only `userinterface_name`

**Why This Matters:**
1. **Test cases are DECLARATIVE**: "Go to player" not "Click this, then that"
2. **Navigation tree is IMPERATIVE**: Contains all the explicit actions
3. **Reusability**: Same testcase works on Netflix, YouTube, Hulu (different nav trees, same test logic)
4. **Maintainability**: UI changes only require updating navigation tree, not all testcases

**Correct Test Case Structure:**
```json
{
  "nodes": [
    {"id": "nav1", "type": "navigation", "data": {"target_node_label": "player"}},
    {"id": "verify1", "type": "verification", "data": {"waitForElement": "play_button"}}
  ]
}
```

**❌ WRONG (Don't Duplicate Navigation Actions):**
```json
{
  "nodes": [
    {"id": "action1", "type": "action", "data": {"command": "click_element", "text": "The Witcher"}},
    {"id": "action2", "type": "action", "data": {"command": "click_element", "text": "Play"}}
  ]
}
```

**When to Use Action Nodes:**
- ✅ Non-navigation actions: pause video, adjust volume, search text
- ❌ NOT for navigation between screens (use navigation nodes!)

---

Create 12-15 testcases by **manually constructing graph_json** from node sequences.

**CRITICAL:** Do NOT use `generate_test_graph`. Manually construct graph_json following the template in `testcase_graph_template.md`.

**CRITICAL:** Use **GENERIC** testcase names and descriptions (not Netflix-specific) so they can be reused on YouTube, Hulu, etc. by changing only the `userinterface_name`. The navigation tree is what makes testcases app-specific, not the testcase itself.

### Testcase Creation Process

For each test:
1. Define node sequence (e.g., ["entry", "home", "content_detail", "player"])
2. **Manually construct graph_json** with nodes and edges arrays following `testcase_graph_template.md`
3. Use actual node UUIDs from `list_navigation_nodes()` for `target_node_id`
4. Use actual element_ids from UI dump for verification/action params
5. **Use generic testcase name** (e.g., `Playback_001_BasicVideoPlayback` NOT `Netflix_Playback_001`)
6. **Use generic description** (e.g., "Navigate from home to player" NOT "Navigate Netflix home to Netflix player")
7. Save testcase using `save_testcase(testcase_name="...", graph_json={...})`
8. Link testcase to relevant requirements using `link_testcase_to_requirement`

### Testcase Definitions

#### Playback Tests (4 tests)

**Test 1: Playback_001_BasicVideoPlayback** [P1]
- Description: Navigate from entry to player and verify video starts within 5 seconds
- Path: entry → home → content_detail → player
- Tags: ["P1", "playback", "critical", "smoke"]
- Folder: playback
- Link to: REQ_PLAYBACK_001

**Test 2: Playback_002_PauseResume** [P1]
- Description: Pause video playback and resume from same position
- Path: player (prerequisite: already at player) → pause action → wait → resume action
- Tags: ["P1", "playback", "critical"]
- Folder: playback
- Link to: REQ_PLAYBACK_002

**Test 3: Playback_003_ExitPlayer** [P1]
- Description: Exit video player using back button and return to content detail then home
- Path: player → content_detail → home (via back button navigation)
- Tags: ["P1", "playback", "navigation", "critical"]
- Folder: playback
- Link to: REQ_PLAYBACK_003, REQ_NAV_003

**Test 4: Playback_004_PlaybackControls** [P2]
- Description: Verify playback controls are visible and functional
- Path: player (verify controls visible, interact with pause/play/timeline)
- Tags: ["P2", "playback", "ui"]
- Folder: playback
- Link to: REQ_PLAYBACK_001, REQ_PLAYBACK_002

#### Navigation Tests (4 tests)

**Test 5: Nav_001_MainTabNavigation** [P1]
- Description: Navigate through all main tabs (home, search, downloads, more) and verify each screen loads
- Path: home → search → downloads → more → home
- Tags: ["P1", "navigation", "smoke"]
- Folder: navigation
- Link to: REQ_NAV_001

**Test 6: Nav_002_ContentDetailAccess** [P1]
- Description: Access content detail page from home screen and verify content information loads
- Path: home → content_detail
- Tags: ["P1", "navigation"]
- Folder: navigation
- Link to: REQ_NAV_002

**Test 7: Nav_003_BackButtonNavigation** [P1]
- Description: Verify Android back button works correctly from multiple screens
- Path: content_detail → home (back), player → content_detail (back)
- Tags: ["P1", "navigation", "critical"]
- Folder: navigation
- Link to: REQ_NAV_003

**Test 8: Nav_004_DeepNavigation** [P2]
- Description: Navigate through deep path and return using back button multiple times
- Path: home → content_detail → player → content_detail → home
- Tags: ["P2", "navigation"]
- Folder: navigation
- Link to: REQ_NAV_002, REQ_NAV_003

#### Search Tests (3 tests)

**Test 9: Search_001_ContentSearch** [P2]
- Description: Search for content by title and verify search input accepts text
- Path: home → search (type "Stranger Things")
- Tags: ["P2", "search"]
- Folder: search
- Link to: REQ_SEARCH_001

**Test 10: Search_002_SearchResults** [P2]
- Description: Verify search results are displayed with relevant content matching query
- Path: search (with typed query) → verify results visible
- Tags: ["P2", "search"]
- Folder: search
- Link to: REQ_SEARCH_002

**Test 11: Search_003_SearchToDetail** [P2]
- Description: Search for content, click first result, and verify content detail page opens
- Path: home → search → type "Stranger Things" → click first result → content_detail
- Tags: ["P2", "search", "navigation"]
- Folder: search
- Link to: REQ_SEARCH_001, REQ_SEARCH_003

#### UI/Performance Tests (3 tests)

**Test 12: UI_001_AppLaunch** [P2]
- Description: Launch Netflix app and verify home screen appears within 5 seconds
- Path: entry → home (measure load time)
- Tags: ["P2", "ui", "performance", "smoke"]
- Folder: ui
- Link to: REQ_UI_001

**Test 13: UI_002_ScreenTransitions** [P2]
- Description: Verify screen transitions between tabs complete within 3 seconds
- Path: home → search → home (measure transition times)
- Tags: ["P2", "ui", "performance"]
- Folder: ui
- Link to: REQ_UI_002

**Test 14: UI_003_ContentImagesLoad** [P2]
- Description: Verify content thumbnails and images load correctly on home screen
- Path: home (verify content cards visible with images)
- Tags: ["P2", "ui", "visual"]
- Folder: ui
- Link to: REQ_UI_003

### Graph Construction Format

**Refer to `testcase_graph_template.md` for complete graph_json structure.**

Key requirements:
- **nodes array:** Must include `start`, `success`, `failure`, and functional nodes
- **edges array:** Connect nodes with success/failure paths
- **scriptConfig:** Include required inputs (device_model_name, host_name, device_name, userinterface_name)

**Node types:**
- `navigation` - Navigate to tree nodes (use target_node_label: "home", "search", etc.)
- `verification` - Verify screen state (waitForElementToAppear, check_text_on_screen)
- `action` - Execute device actions (click_element, type_text, press_key)

Use node IDs that match the navigation tree (entry, home, search, content_detail, player, downloads, more).

---

## ▶️ Phase 4: Execute & Report (20 minutes)

### Step 1: Execute Tests
Execute all testcases in priority order:
1. UI_001_AppLaunch (smoke)
2. Nav_001_MainTabNavigation (smoke)
3. Playback_001_BasicVideoPlayback (P1)
4. Playback_003_ExitPlayer (P1)
5. Nav_002_ContentDetailAccess (P1)
6. Nav_003_BackButtonNavigation (P1)
7. Playback_002_PauseResume (P1)
8. Nav_004_DeepNavigation (P2)
9. Search_001_ContentSearch (P2)
10. Search_002_SearchResults (P2)
11. Search_003_SearchToDetail (P2)
12. UI_002_ScreenTransitions (P2)
13. UI_003_ContentImagesLoad (P2)
14. Playback_004_PlaybackControls (P2)

Use execute_testcase for each test and monitor with get_execution_status.

### Step 2: Debug Failures
If tests fail:
1. Navigate to failing screen manually
2. Dump UI elements to see actual state
3. Capture screenshot for visual inspection
4. Compare expected vs actual element_ids
5. Update edges/verifications with correct element_ids
6. Re-execute failed tests

Use view_logs for backend errors.

### Step 3: Generate Coverage Report
Get coverage metrics:
1. Coverage summary: GET /server/requirements/coverage/summary
2. Detailed coverage: GET /server/requirements/coverage/detailed
3. Uncovered requirements: GET /server/requirements/coverage/uncovered

### Step 4: Display Final Summary

Report format:
```
# Netflix Android Mobile - Test Automation Summary

## Navigation Model
- User Interface: netflix_mobile
- Nodes: 6 (entry, home, search, content_detail, player, downloads, more)
- Edges: 7+
- All nodes have verifications: ✅
- All navigation paths tested: ✅

## Requirements
- Total Requirements: 12
- P1 Critical: 6
- P2 High: 6
- Categories: playback (3), navigation (3), search (3), ui (3)

## Test Cases
- Total Tests Created: 14
- P1 Tests: 7
- P2 Tests: 7
- By Category:
  - Playback: 4 tests
  - Navigation: 4 tests
  - Search: 3 tests
  - UI/Performance: 3 tests

## Test Execution Results
- Total Executed: 14
- Passed: X (Y%)
- Failed: Z (W%)
- Execution Time: ~X minutes

## Requirements Coverage
- Total Coverage: X%
- P1 Requirements Coverage: Y% (Z/6)
- P2 Requirements Coverage: W% (V/6)
- Fully Covered Requirements: X
- Partially Covered Requirements: Y
- Uncovered Requirements: Z

## Coverage by Category
- Playback: X/3 requirements covered
- Navigation: Y/3 requirements covered
- Search: Z/3 requirements covered
- UI: W/3 requirements covered

## Known Issues
[List any failures or limitations]

## Recommendations
[Suggest additional tests or improvements if coverage < 80%]
```

---

## ✅ Success Criteria

- ✅ User interface "netflix_mobile" created
- ✅ 6 nodes with verifications
- ✅ 7+ edges with bidirectional actions
- ✅ All navigation paths work (tested with navigate_to_node)
- ✅ 12 requirements defined (6 P1, 6 P2)
- ✅ 12-15 testcases created from navigation graph
- ✅ All testcases linked to requirements
- ✅ All testcases executed
- ✅ 80%+ requirements coverage achieved
- ✅ Coverage report generated and displayed

---

## ⚠️ Error Handling

**Device offline:** Check get_device_info, reconnect device, retry

**Element not found:** Dump UI elements, take screenshot, update element_id in edge/verification, retry

**Navigation timeout:** Check logs with view_logs, test edge individually with execute_edge, debug action, update edge, retry

**Verification fails:** Navigate to node, dump UI, verify element exists, update verification criteria, retry

**App crash:** Check logs, relaunch app, report issue, skip test if app bug

**Test execution hangs:** Check get_execution_status, verify device responsive, cancel and retry

---

## ⏱️ Time Estimate

- Phase 1 (Model): 45 minutes
- Phase 2 (Requirements): 10 minutes
- Phase 3 (Testcases): 30 minutes
- Phase 4 (Execute & Report): 20 minutes
- **Buffer (Debugging):** 20-30 minutes
- **Total:** 2-2.5 hours

---

## 🚀 Ready to Execute

Provide this prompt to MCP-enabled AI to fully automate Netflix Android mobile testing.

