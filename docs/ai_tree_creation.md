# AI Tree Creation - Automated Navigation Tree Generation

## Overview

AI Tree Creation automatically explores user interfaces and generates complete navigation trees with nodes, edges, and subtrees. The system uses a **UNIVERSAL algorithm** that works identically for mobile, web, TV, and STB platforms by focusing on **destinations (nodes)** and **navigation actions (edges)**.

## Architecture: 3-Component Design

The AI generation flow uses **3 separate components** for clean separation of concerns:

```
┌─────────────────────────────────────────┐
│  AIGenerationModal (Phase 1)            │
│  ├─ Configuration (depth)               │
│  ├─ AI explores & analyzes screen       │
│  ├─ Shows plan preview                  │
│  └─ Buttons: Abort | Retry | Create     │
└──────────────┬──────────────────────────┘
               │ onStructureCreated()
               ▼
┌─────────────────────────────────────────┐
│  ValidationReadyPrompt (Transition)     │
│  ├─ "✅ Preview"                         │
│  ├─ Stats: X nodes, Y edges             │
│  └─ Button: Start Validation            │
└──────────────┬──────────────────────────┘
               │ Opens ValidationModal
               ▼
┌─────────────────────────────────────────┐
│  ValidationModal (Phase 2b)             │
│  ├─ Progress: Step X/Y                  │
│  ├─ Real-time test results (✅/❌)      │
│  ├─ Auto-tests each step                │
│  └─ Buttons: Confirm & Save | Cancel    │
└─────────────────────────────────────────┘
```

### Why 3 Components?

**Benefits:**
- ✅ **Single Responsibility**: Each component does ONE thing
- ✅ **Clean Transitions**: Visual feedback at each phase
- ✅ **Easy to Maintain**: Test and debug independently
- ✅ **Better UX**: User sees clear progress through workflow
- ✅ **No Complex State**: No nested conditions or complex logic

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
- **Collects all destination nodes data**
- **Collects all edges data with ACTIONS FILLED IN**
- **Batch saves all nodes at once**
- **Batch saves all edges at once**

**Important:** Edges are created WITH actions immediately, not empty!

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

**Performance:** Batch saving reduces database writes from 20+ to 2 operations for 10 items!

**You'll see:**
- `X nodes created`
- `Y edges created`
- All with `_temp` suffix

**Your Decision:**
- ✅ **Start Validation** → Proceed to Phase 2b
- ❌ **Cancel** → Delete temp structure

---

### Phase 2b: Validation (INFORMATIVE ONLY)

**Modal: ValidationModal (small, fixed top-right corner)**

**Purpose:** Test if the created actions work correctly (INFORMATIVE - does NOT modify edges)

**What happens (auto-running test):**

For each edge, system tests navigation:

#### Mobile/Web:
```
1. Execute saved action: click_element("TV Guide Tab")
2. Wait 2s
3. Check if screen changed → Show ✅ or ❌
4. Execute saved action: press_key(BACK)
5. Check if returned home → Show ✅ or ⚠️
```

#### TV/STB:
```
1. Execute saved action: press_key(RIGHT) + press_key(OK)
2. Wait 2s
3. Check if screen changed (AI vision) → Show ✅ or ❌
4. Execute saved action: press_key(BACK)
5. Check if returned (AI vision) → Show ✅ or ⚠️
```

**Modal behavior:**
- Small, fixed to top-right corner
- No shadow
- Watch ReactFlow graph (edges already created with actions!)
- Modal just shows TESTING results

**Progress display:**
```
🔄 Testing 3/10

Step 1: "TV Guide Tab"
  Step 1.1 (Forward): home → tvguide
  ✅ SUCCESS (click_element "TV Guide Tab")
  
  Step 1.2 (Backward): tvguide → home  
  ✅ SUCCESS (press_key BACK)
```

**When complete:**
- ✅ **Confirm & Save** → Remove `_temp` suffix, make permanent
- ❌ **Cancel & Delete** → Delete all `_temp` nodes/edges

**User can decide** after seeing test results! If too many failures → Cancel instead of saving.

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

# 3. Create edge WITH actions (not empty!)
create_edge(
  id="edge_home_temp_to_tvguide_temp_temp",
  source="home_temp",
  target="tvguide_temp",
  action_sets=[
    {
      id: "home_to_tvguide",
      actions: [
        {"command": "click_element", "params": {"text": "TV Guide Tab"}, "delay": 2000}
      ]
    },
    {
      id: "tvguide_to_home",
      actions: [
        {"command": "press_key", "params": {"key": "BACK"}, "delay": 2000}
      ]
    }
  ]
)

# 4. Store mapping for testing
target_to_node_map["TV Guide Tab"] = "tvguide_temp"
```

**Key Point:** Edges are created WITH actions already filled in! Phase 2b just TESTS them.

---

### Phase 2b: Testing (INFORMATIVE ONLY!)

**The testing algorithm (does NOT modify edges):**

```python
for each target in navigation_targets:
    
    node_name = target_to_node_map[target]
    edge = get_edge(f"edge_home_temp_to_{node_name}_temp")
    
    # Edge already has actions! We just TEST them
    forward_actions = edge.action_sets[0].actions
    backward_actions = edge.action_sets[1].actions
    
    # ═══════════════════════════════════════
    # STEP 1: TEST FORWARD ACTION
    # ═══════════════════════════════════════
    
    try:
        execute(forward_actions)
        wait(2s)
        
        if screen_changed():
            forward_result = "✅ SUCCESS"
        else:
            forward_result = "❌ FAILURE - screen didn't change"
    except Exception as e:
        forward_result = f"❌ FAILURE - {e}"
    
    # ═══════════════════════════════════════
    # STEP 2: TEST BACKWARD ACTION
    # ═══════════════════════════════════════
    
    try:
        execute(backward_actions)
        wait(2s)
        
        if back_to_home():
            backward_result = "✅ SUCCESS"
        else:
            backward_result = "⚠️ WARNING - not back home"
    except Exception as e:
        backward_result = f"❌ FAILURE - {e}"
    
    # ═══════════════════════════════════════
    # STEP 3: SHOW RESULTS (don't modify edge!)
    # ═══════════════════════════════════════
    
    print(f"Step {idx}.1 (Forward): {source} → {target}")
    print(f"  {forward_result} ({forward_actions})")
    
    print(f"Step {idx}.2 (Backward): {target} → {source}")
    print(f"  {backward_result} ({backward_actions})")
```

**Key Point:** Testing is INFORMATIVE. Edges keep their actions regardless of test results!

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

## Frontend Architecture

### Component Structure

**1. AIGenerationModal** (`frontend/src/components/navigation/AIGenerationModal.tsx`)
- **Phase 1**: Exploration & Approval
- Shows configuration (depth input)
- Displays AI analysis results
- Shows screenshot + plan preview
- Buttons: Abort, Retry, Create Nodes
- Closes after structure creation

**2. ValidationReadyPrompt** (`frontend/src/components/navigation/ValidationReadyPrompt.tsx`)
- **Transition**: Between Phase 2a and 2b
- Small prompt in top-right corner
- Shows nodes/edges created count
- Blinking "Start Validation" button
- Can cancel to abort workflow

**3. ValidationModal** (`frontend/src/components/navigation/ValidationModal.tsx`)
- **Phase 2b**: Testing (Informative)
- Small modal in top-right corner
- Auto-starts testing on mount
- Shows progress (Step X/Y)
- Displays real-time test results (✅/❌)
- Step X.1 (Forward): source → target
- Step X.2 (Backward): target → source
- Auto-continues through all steps
- **Two buttons when complete**:
  - ✅ **Confirm & Save** → Rename _temp to permanent
  - ❌ **Cancel & Delete** → Delete all _temp nodes/edges

### State Management

**NavigationEditor orchestrates all 3 components:**

```typescript
// Phase 1: AIGenerationModal
const [isAIGenerationOpen, setIsAIGenerationOpen] = useState(false);

// Transition: ValidationReadyPrompt
const [showValidationPrompt, setShowValidationPrompt] = useState(false);
const [validationNodesCount, setValidationNodesCount] = useState(0);
const [validationEdgesCount, setValidationEdgesCount] = useState(0);
const [explorationId, setExplorationId] = useState<string | null>(null);
const [explorationHostName, setExplorationHostName] = useState<string | null>(null);

// Phase 2b: ValidationModal
const [isValidationModalOpen, setIsValidationModalOpen] = useState(false);
```

**Flow:**
1. User clicks "AI Generate" → opens `AIGenerationModal`
2. After structure creation → closes modal, shows `ValidationReadyPrompt`
3. User clicks "Start Validation" → opens `ValidationModal`
4. Testing shows ✅/❌ for each step
5. User decides:
   - ✅ **Confirm & Save** → Remove _temp suffix, permanent nodes/edges
   - ❌ **Cancel & Delete** → Delete all _temp, nothing saved

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
- Creates edges with ACTIONS FILLED IN (not empty!)
- Stores `target_to_node_map`
- Status: `structure_created`

**`/start-validation` (Phase 2b init)**
- Initializes validation index
- Status: `awaiting_validation`

**`/validate-next-item` (Phase 2b loop)**
- Gets current target from list
- Looks up node name from mapping
- Gets edge (already has actions!)
- Tests forward action → Show ✅ or ❌
- Tests backward action → Show ✅ or ⚠️
- Does NOT modify edge
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
- Check that edges are created with correct action format:
  ```json
  {"command": "click_element", "params": {"text": "..."}, "delay": 2000}
  ```

### Phase 2b: Test failures
- **If forward test fails**: Element text may have changed - check UI dump
- **If backward test fails**: Try different BACK strategy or check home detection
- **Important**: Test failures don't break the workflow! Edges keep their actions.

### Edges show "No action selected"
- This was a bug in older versions (action format mismatch)
- Fixed in Phase 2a - edges now use correct format: `{"command": ..., "params": ...}`
- If still seeing this, check backend logs for edge creation

---

## Future Enhancements

1. **Recursive exploration**: After validating depth 1, explore each child node
2. **Multiple AI models**: Allow user to select from 3 OpenRouter vision models
3. **Subtree creation**: Automatically create subtrees after 2 depth levels
4. **Edge confidence scores**: Rate edge quality based on validation success
5. **Smart retry**: If edge fails, try alternative navigation sequences
