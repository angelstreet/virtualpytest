# AI Tree Creation - Automated Navigation Tree Generation

## Overview

AI Tree Creation automatically explores user interfaces and generates complete navigation trees with nodes, edges, and subtrees. The system uses a **UNIVERSAL algorithm** that works identically for mobile, web, TV, and STB platforms by focusing on **destinations (nodes)** and **navigation actions (edges)**.

---

## Core Principle: The Universal Algorithm

**Navigation targets (buttons, tabs, menu items) are EDGES, not nodes.**

- **Node** = A destination screen we can ENTER
- **Edge** = The actions required to reach that destination

### Example (Mobile):
- "TV Guide Tab" is an **EDGE** (the button you click)
- `tvguide` is the **NODE** (the screen you reach after clicking)

### Example (TV/STB):
- "tv_guide" menu item is an **EDGE** (what you navigate to + OK)
- `tvguide` is the **NODE** (the screen you enter after pressing OK)

---

## Quick Start

### Prerequisites
1. **NavigationEditor** - Open for your tree (e.g., `horizon_android_mobile`)
2. **Device Control** - Take control of device (button must be active)
3. **Home Screen** - Ensure device is on a stable home screen

### Starting AI Generation
1. Open NavigationEditor for your tree
2. Select host and device
3. Click "Take Control" button
4. **AI Generate** button appears in header (only when control is active)
5. Click **AI Generate** to open exploration modal
6. Set exploration depth (1-10 levels, default: 5)
7. Click **Start** (Phase 1: Analysis)

---

## The 3-Phase Workflow

### Phase 1: Analysis (AI Anticipation)

**What happens:**
- System analyzes the home screen
- **Mobile/Web**: Parses UI dump to find clickable elements
- **TV/STB**: Uses AI vision to identify menu items

**You'll see:**
- Screenshot of home screen
- List of navigation targets found (chips)
- AI reasoning about interface structure

**Your Decision:**
- ✅ **Create Nodes** → Proceed to Phase 2a
- 🔄 **Retry** → Re-analyze with new screenshot
- ❌ **Abort** → Cancel without changes

---

### Phase 2a: Structure Creation (Instant)

**What happens (automatically after approval):**
- Creates `home_temp` node (root)
- Creates destination nodes for each target
- Creates edges with **empty actions**

**Node Naming (UNIVERSAL):**
```
"TV Guide Tab" → tvguide_temp
"Replay Register" → replay_temp
"Films & Series" → movies_and_series_temp
"Aktuell gewählte Registerkarte Settings" → settings_temp
```

**Rules:**
- Remove: "Tab", "Register", "Button", "Screen", common phrases
- Lowercase
- Replace spaces/special chars with underscore

**You'll see:**
- `X nodes created`
- `Y edges created`
- All with `_temp` suffix

**Your Decision:**
- ✅ **Start Validation** → Proceed to Phase 2b
- ❌ **Cancel** → Delete temp structure

---

### Phase 2b: Validation (UNIVERSAL - Works for All!)

**What happens (incremental, with auto-continue):**

For each edge, system tests navigation:

#### Mobile/Web:
```
1. Click the target element
2. Wait 2s
3. Check if screen changed (home elements gone?)
4. Press BACK
5. Check if returned (home elements visible?)
6. Update edge with tested actions
```

#### TV/STB:
```
1. Try each direction (RIGHT, LEFT, DOWN, UP)
2. For each: Press DIRECTION → Press OK
3. Check if screen changed (AI vision)
4. When found working sequence:
   a. Press BACK
   b. Check if returned (AI vision)
5. Update edge with working direction + OK
```

**Modal behavior:**
- Small, fixed to top-right corner
- No shadow
- Watch ReactFlow graph update in real-time!

**Progress display:**
```
🔄 Validating 3/10
Current: TV Guide Tab
  ✅ Click success
  ✅ Back success
```

**When complete:**
- ✅ **Finalize** → Remove `_temp` suffix, save permanently
- ❌ **Cancel** → Delete all temp nodes/edges

---

## How the Universal Algorithm Works

### Key Insight: Edges vs Nodes

**OLD thinking (WRONG):**
- Every clickable element = a node
- Causes confusion between focus states and actual screens

**NEW thinking (CORRECT):**
- Clickable element = an EDGE (action to navigate)
- New screen entered = a NODE (destination)

---

### Phase 1: Analysis

#### For Mobile/Web:
```python
1. Parse UI dump (XML for Android, JSON for web)
2. Extract clickable elements:
   ["TV Guide Tab", "Replay Register", "Search Button", ...]
3. Filter out:
   - Non-interactive elements (checked via clickable property)
   - Generic labels ("image", "icon", "loading")
   - Dynamic content (> 30 chars, or contains price/date patterns)
4. Return list of navigation targets (max 20)
```

#### For TV/STB:
```python
1. Capture screenshot
2. AI vision analysis:
   "List all visible menu items line by line"
3. Extract menu items:
   ["home", "tv_guide", "replay", "search", ...]
4. Return list of navigation targets
```

---

### Phase 2a: Structure Creation

**For each navigation target:**

```python
# 1. Generate node name
target = "TV Guide Tab"
node_name = target_to_node_name(target)  # → "tvguide"

# 2. Create node
create_node(
  id="tvguide_temp",
  label="TV Guide",
  position=calculated
)

# 3. Create edge with empty actions
create_edge(
  id="edge_home_temp_to_tvguide_temp_temp",
  source="home_temp",
  target="tvguide_temp",
  action_sets=[
    {id: "home_to_tvguide", actions: []},     # Forward (empty)
    {id: "tvguide_to_home", actions: []}      # Reverse (empty)
  ]
)

# 4. Store mapping for validation
target_to_node_map["TV Guide Tab"] = "tvguide_temp"
```

---

### Phase 2b: Validation (UNIVERSAL!)

**The algorithm that works for EVERYTHING:**

```python
for each target in navigation_targets:
    
    node_name = target_to_node_map[target]
    
    # ═══════════════════════════════════════
    # STEP 1: TRY TO ENTER THE DESTINATION
    # ═══════════════════════════════════════
    
    if mobile or web:
        # Single action - click immediately enters
        actions = [{"command": "click_element", "params": {"text": target}}]
        execute(actions)
        wait(2s)
    
    elif tv or stb:
        # Must navigate + press OK to enter
        directions = ["RIGHT", "LEFT", "DOWN", "UP"]
        actions = None
        
        for direction in directions:
            # Navigate to element, then press OK to ENTER
            test_actions = [
                {"command": "press_key", "params": {"key": direction}},
                {"command": "press_key", "params": {"key": "OK"}}
            ]
            execute(test_actions)
            wait(2s)
            
            # Did we enter a new screen?
            if screen_changed():
                actions = test_actions
                break  # Found working sequence!
            
            # Didn't work, try next direction
            # (We're still on home, just different focus)
    
    # ═══════════════════════════════════════
    # STEP 2: VERIFY WE ENTERED NEW SCREEN
    # ═══════════════════════════════════════
    
    if screen_changed():
        # SUCCESS! We entered the destination
        
        # Save forward actions
        edge = get_edge(f"edge_home_temp_to_{node_name}_temp")
        edge.action_sets[0].actions = actions
        
        # ═══════════════════════════════════════
        # STEP 3: TEST RETURN (BACK)
        # ═══════════════════════════════════════
        
        execute([{"command": "press_key", "params": {"key": "BACK"}}])
        wait(2s)
        
        # Verify we're back on home
        if back_to_home():
            # Save reverse actions
            edge.action_sets[1].actions = [
                {"command": "press_key", "params": {"key": "BACK"}}
            ]
            result = "✅✅ Both directions work"
        else:
            result = "✅❌ Forward works, back failed"
        
        # Update edge in database
        update_edge(edge)
    
    else:
        # Failed to enter destination
        result = "❌ Could not enter destination"
```

---

## Screen Change Detection

### Mobile/Web:
```python
def screen_changed() -> bool:
    """Check if we left the home screen"""
    # Get all navigation targets from Phase 1
    home_elements = ["Home Tab", "TV Guide Tab", "Replay Tab", ...]
    
    # Try to find any of them
    for element in home_elements:
        if wait_for_element(element, timeout=1):
            return False  # Still see home element = still on home
    
    return True  # All home elements gone = entered new screen
```

### TV/STB:
```python
def screen_changed() -> bool:
    """Check if screen is different using AI vision"""
    current_screenshot = capture_screenshot()
    
    # Ask AI: "Is this a different screen from home?"
    is_different = ai_vision_compare(
        home_screenshot,
        current_screenshot
    )
    
    return is_different
```

### Verify Return to Home:
```python
def back_to_home() -> bool:
    """Check if we returned to home screen"""
    # Mobile/Web: Check if first navigation target is visible
    home_indicator = navigation_targets[0]  # e.g., "Home Tab"
    return wait_for_element(home_indicator, timeout=5)
    
    # TV/STB: Compare screenshot with original home screenshot
    return ai_vision_compare(current_screenshot, home_screenshot)
```

---

## Platform Comparison

| Aspect | Mobile/Web | TV/STB |
|--------|------------|--------|
| **Navigation** | Click once | Direction + OK |
| **Entry** | Immediate | After OK press |
| **Discovery** | UI Dump parsing | AI Vision |
| **Validation** | Same (screen_changed?) | Same (screen_changed?) |
| **Return** | Same (BACK key) | Same (BACK key) |
| **Intermediate states** | None | Yes (focus moves) |

---

## Node Naming Convention

### Target → Node Name Conversion

**Function:**
```python
def target_to_node_name(target_text: str) -> str:
    """
    Convert navigation target to node name
    
    Examples:
    "TV Guide Tab" → "tvguide"
    "Replay Register" → "replay"
    "Films & Series" → "movies_and_series"
    "Aktuell gewählte Registerkarte Settings" → "settings"
    """
    text = target_text.lower()
    
    # Remove common words
    remove_words = [
        'tab', 'register', 'button', 'screen', 'menu', 'page',
        'aktuell gewählte registerkarte',  # "currently selected tab" (German)
        'currently selected',
        'doppeltippen zum öffnen',  # "double tap to open" (German)
        'double tap to',
    ]
    
    for word in remove_words:
        text = text.replace(word, ' ')
    
    # Replace special chars with underscore
    text = re.sub(r'[^a-z0-9]+', '_', text)
    
    # Clean up
    text = re.sub(r'_+', '_', text)  # Remove consecutive underscores
    text = text.strip('_')  # Strip leading/trailing
    
    return text or 'unknown'
```

---

## Benefits of the Universal Algorithm

1. **Works everywhere**: Mobile, web, TV, STB - same logic
2. **Simple**: Edges = actions, Nodes = destinations
3. **No intermediate states**: Only care about screens we can ENTER
4. **Robust**: Tests both forward and reverse navigation
5. **Accurate**: Names derived from actual UI elements
6. **Efficient**: Creates structure first, validates incrementally
7. **Transparent**: User sees real-time progress

---

## Technical Implementation

### Backend Routes

**`/start-exploration` (Phase 1)**
- Captures screenshot
- Analyzes with UI dump (mobile/web) or AI vision (TV/STB)
- Returns list of navigation targets
- Status: `awaiting_approval`

**`/continue-exploration` (Phase 2a)**
- Creates `home_temp` node
- Creates destination nodes for each target (using `target_to_node_name`)
- Creates edges with empty `action_sets`
- Stores `target_to_node_map`
- Status: `structure_created`

**`/start-validation` (Phase 2b init)**
- Initializes validation index
- Status: `awaiting_validation`

**`/validate-next-item` (Phase 2b loop)**
- Gets current target from list
- Looks up node name from mapping
- Tests navigation (click or direction+OK)
- Tests return (BACK)
- Updates edge `action_sets`
- Increments index
- Status: `awaiting_validation` or `validation_complete`

---

## Troubleshooting

### Phase 1: No items found
- **Mobile/Web**: Check if UI dump is working (`dump_elements()`)
- **TV/STB**: Check if screenshot is captured and AI vision is responding

### Phase 2a: Nodes not created
- Check console logs for database errors
- Verify `target_to_node_name()` is generating valid node names

### Phase 2b: Click/navigation fails
- **Mobile/Web**: Element text may have changed - check UI dump
- **TV/STB**: Try different directions, check AI vision analysis

### Phase 2b: Back verification fails
- Home indicator may not be the first item
- Try using a stable home element (logo, app name)

---

## Future Enhancements

1. **Recursive exploration**: After validating depth 1, explore each child node
2. **Multiple AI models**: Allow user to select from 3 OpenRouter vision models
3. **Subtree creation**: Automatically create subtrees after 2 depth levels
4. **Edge confidence scores**: Rate edge quality based on validation success
5. **Smart retry**: If edge fails, try alternative navigation sequences
