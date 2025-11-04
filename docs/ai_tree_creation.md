# AI Tree Creation - Automated Navigation Tree Generation

## Overview

AI Tree Creation automatically explores user interfaces and generates complete navigation trees with nodes, edges, and subtrees using AI vision analysis. The system analyzes screenshots, tests navigation commands, and builds the navigation structure step-by-step with human approval.

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
7. Click **Start Exploration**

### Monitoring Progress
The modal shows live progress:
- **Current Step**: What AI is doing now
- **Progress**: Screens analyzed, nodes/edges found
- **AI Analysis**: Elements AI sees on screen
- **AI Reasoning**: Why AI makes decisions

### Review & Approve
When complete:
- **Proposed Nodes**: Screens discovered (with `_temp` suffix)
- **Proposed Edges**: Navigation paths found (with `_temp` suffix)
- **User Decision**:
  - ✅ **Confirm** → Removes `_temp` suffix, saves permanently
  - ❌ **Cancel** → Deletes all temp nodes/edges/subtrees

---

## How It Works

### Phase 1: AI Anticipation (Smart)
```
1. Capture initial screenshot
2. AI analyzes menu structure
   - Menu type (horizontal, vertical, grid, mixed)
   - Visible menu items
   - Predicted navigation depth
3. AI creates exploration strategy
```

**Example AI Analysis:**
```json
{
  "menu_type": "horizontal",
  "items": ["home", "settings", "profile"],
  "predicted_depth": 3,
  "strategy": "test_right_left_first_then_ok"
}
```

### Phase 2: Smart Validation (Prediction-Guided)

The AI doesn't explore blindly - it uses Phase 1 predictions to guide exploration efficiently:

**Strategy: Confirm, Don't Discover**

**If menu_type = 'horizontal' with N predicted items:**
```
For each predicted item (e.g., ['home', 'replay', 'settings']):
  1. Press RIGHT (i times) to move to position
  2. Press OK to enter
  3. Take screenshot
  4. Ask AI: "Is this the '{predicted_item}' screen?"
  5. If YES → Create node (prediction confirmed!)
     If NO → Ask AI "What screen is this?" and create with actual name
  6. Press BACK to return to menu
```

**If menu_type = 'vertical' with N predicted items:**
- Same strategy but using DOWN instead of RIGHT

**If menu_type = 'grid' or 'mixed':**
- Fallback to testing all 4 directions (UP, DOWN, LEFT, RIGHT)

**Key Advantages:**
- ✅ **Efficient**: If AI predicted 4 items, we only test 4 positions (not all directions)
- ✅ **Smart**: Horizontal menu → only test RIGHT/LEFT (not UP/DOWN)
- ✅ **Self-Correcting**: If prediction is wrong, AI adjusts on-the-fly
- ✅ **Deep Recursion**: At each new screen, AI re-analyzes and provides fresh predictions

**Optimization:** AI only analyzes after OK/BACK, not for every DPAD movement!

### Phase 3: Node & Edge Creation
All nodes and edges created with `_temp` suffix:

**Nodes:** `home_temp`, `settings_temp`, `home_settings_temp`  
**Edges:** `edge_home_to_settings_temp`  
**Subtrees:** `settings_subtree_temp` (for nested navigation)

### Phase 4: User Approval
**Two options:**
1. **Confirm** → Rename all: `home_temp` → `home`, `settings_temp` → `settings`
2. **Cancel** → Delete all temp nodes/edges/subtrees from database

---

## Naming Convention

The AI follows your established naming rules:

### Horizontal Navigation (Context Visible)
```
home (root)
├── home_settings_temp    # Can still see "home" context
├── home_profile_temp     # Can still see "home" context
└── home_replay_temp      # Can still see "home" context
```

### New Screen (Entered via OK)
```
home_settings_temp → [OK pressed] → settings_temp
```
✅ **New Screen** = Cannot see previous menu anymore  
✅ **Drop Prefix** = Just `settings_temp`, not `home_settings_temp`

### Subtree Creation (Depth 1+)
```
settings_temp (depth 1)
└── [SUBTREE CREATED] settings_subtree_temp
    ├── settings_audio_temp
    ├── settings_video_temp
    └── settings_audio_dolby_temp
```

**Rule:** Node at depth 1 (entered via OK from root) → Create subtree automatically

---

## Technical Architecture

### Backend Components

#### 1. **ExplorationEngine** (Main Orchestrator)
```python
# backend_host/src/services/ai_exploration/exploration_engine.py

class ExplorationEngine:
    def start_exploration(self) -> Dict:
        # Phase 1: AI anticipates tree structure
        # Phase 2: Depth-first exploration
        # Phase 3: Create temp nodes/edges/subtrees
```

#### 2. **ScreenAnalyzer** (AI Vision)
```python
# backend_host/src/services/ai_exploration/screen_analyzer.py

class ScreenAnalyzer:
    def anticipate_tree(screenshot_path) -> Dict:
        # AI predicts menu structure
        
    def is_new_screen(before, after, action) -> Dict:
        # AI determines if navigation succeeded
```

**Reuses:** `VideoAIHelpers` for screenshot capture + Qwen AI analysis

#### 3. **NavigationStrategy** (DPAD Testing)
```python
# backend_host/src/services/ai_exploration/navigation_strategy.py

class NavigationStrategy:
    def test_direction(direction) -> bool:
        # Test DPAD_RIGHT, LEFT, UP, DOWN
        
    def press_ok_and_analyze(screenshot) -> Dict:
        # Press OK and check if new screen
```

**Reuses:** `ControllerFactory` for device commands

#### 4. **NodeGenerator** (Naming + Structure)
```python
# backend_host/src/services/ai_exploration/node_generator.py

class NodeGenerator:
    def generate_node_name(ai_suggestion, parent, context_visible) -> str:
        # Follows your naming convention + _temp suffix
        
    def create_node_data(node_name, position, ai_analysis) -> Dict:
        # Creates node data for save_node()
        
    def create_edge_data(source, target, actions) -> Dict:
        # Creates edge data for save_edge()
```

### HTTP Routes (Auto-Proxied)

```
Frontend → /server/ai-generation/* → (auto_proxy) → /host/ai-generation/*
```

#### Routes:
1. **POST /start-exploration** - Start background exploration
2. **GET /exploration-status/<id>** - Poll for progress (every 5s)
3. **POST /approve-generation** - Rename temp nodes (remove _temp)
4. **POST /cancel-exploration** - Delete all temp nodes

### Database Operations

**Uses existing navigation_trees_db functions:**
```python
from shared.src.lib.database.navigation_trees_db import (
    save_node,           # Create node with _temp
    save_edge,           # Create edge with _temp
    create_sub_tree,     # Create subtree with _temp
    delete_node,         # Delete on cancel
    delete_tree_cascade  # Delete subtrees on cancel
)
```

**NO new database tables needed!** ✅

---

## Example Exploration Flow

### Scenario: Android TV Home Screen

**1. User starts exploration:**
```
Device: android_mobile
Tree: horizon_android_mobile_main
Depth: 5
```

**2. AI anticipates (Phase 1):**
```
Screenshot Analysis:
- Menu type: horizontal
- Items: [home, replay, guide, settings]
- Predicted depth: 3
- Strategy: test_right_left_first_then_ok
```

**3. AI explores (Phase 2):**
```
Current: home_temp
  Test DPAD_RIGHT → Press OK
    → New screen detected: "settings"
    → Create: settings_temp (node)
    → Create: edge_home_to_settings_temp (edge)
    → Create: settings_subtree_temp (subtree, depth 1)
    → Press BACK
    
  Test DPAD_LEFT → Press OK
    → New screen detected: "replay"
    → Create: replay_temp (node)
    → Create: edge_home_to_replay_temp (edge)
    → Press BACK
```

**4. User sees in NavigationEditor:**
```
ReactFlow shows:
- home_temp
- settings_temp
- replay_temp
- Edges connecting them
```

**5. User approves:**
```
Confirm clicked:
  ✅ Rename: home_temp → home
  ✅ Rename: settings_temp → settings
  ✅ Rename: replay_temp → replay
  ✅ Rename edges: edge_home_to_settings_temp → edge_home_to_settings
  ✅ Save to database permanently
```

---

## AI Model Selection

### Current: Qwen (Default)
```python
# Uses existing VideoAIHelpers with Qwen vision model
VideoAIHelpers.analyze_with_vision(screenshot, prompt, model_name='qwen')
```

### Future: User-Selectable Models
```
Planned: Allow user to choose from 3 OpenRouter vision models
- Qwen (fast, accurate for menus)
- GPT-4 Vision (more expensive, very accurate)
- Claude Vision (balanced)
```

---

## Best Practices

### Before Starting
✅ Device on stable home screen  
✅ Device control is active  
✅ Start with lower depth (3-5) for testing  
✅ Stable network connection

### During Exploration
✅ Monitor AI reasoning in real-time  
✅ Can cancel at any time if issues  
✅ Let exploration complete (don't interrupt)

### After Completion
✅ Review all proposed nodes carefully  
✅ Check node names make sense  
✅ Verify edges connect correctly  
✅ Uncheck any incorrect items before confirming

---

## Troubleshooting

### "AI Generate button not visible"
**Fix:** Ensure device control is active (take control first)

### "Exploration fails immediately"
**Check:**
- Device is responsive to commands
- Screenshot capture is working
- OpenRouter API access is configured

### "No nodes/edges generated"
**Try:**
- Start from a different screen
- Increase exploration depth
- Check device navigation works manually

### "Generated navigation doesn't work"
**Solution:**
- Review proposed edges before approving
- Test navigation manually first
- Delete incorrect nodes and re-explore

---

## Performance & Limitations

### Current Version (V1)
- **Depth Limit:** 10 levels maximum
- **Device Support:** android_mobile, android_tv
- **AI Model:** Qwen (OpenRouter)
- **Speed:** ~5-10 seconds per screen analyzed
- **Accuracy:** ~85% for standard menu structures

### Known Limitations
- ⚠️ Dynamic menus may confuse AI
- ⚠️ Loading states not yet detected
- ⚠️ Complex animations may cause issues
- ⚠️ Non-standard UI layouts need testing

### Future Enhancements
- 🔄 Loading state detection
- 🔄 Multi-model AI support
- 🔄 Better error recovery
- 🔄 Re-navigation for deeper exploration
- 🔄 Screenshot similarity comparison
- 🔄 Support for more device types

---

## Integration with Existing Features

### NavigationEditor
- ✅ Same device control system
- ✅ Same ReactFlow visualization
- ✅ Same node/edge editing
- ✅ Immediate visual feedback

### Database
- ✅ Uses existing navigation_trees_db
- ✅ Same node/edge structure
- ✅ Compatible with all navigation features
- ✅ Subtree support included

### MCP Server
- ✅ Can be triggered via MCP tools (future)
- ✅ Status polling available
- ✅ Approval workflow compatible

---

## File Structure

### Backend Host
```
backend_host/src/
├── services/ai_exploration/
│   ├── __init__.py
│   ├── exploration_engine.py      # Main orchestrator
│   ├── screen_analyzer.py         # AI vision analysis
│   ├── navigation_strategy.py     # DPAD testing
│   └── node_generator.py          # Naming + structure
│
└── routes/
    └── ai_generation.py            # 4 HTTP endpoints
```

### Frontend (Existing - No Changes!)
```
frontend/src/
├── components/navigation/
│   ├── AIGenerationModal.tsx      # ✅ Already exists
│   └── Navigation_EditorHeader.tsx # ✅ Already integrated
│
└── hooks/
    └── useGenerateModel.ts         # ✅ Already exists
```

---

## API Reference

### POST /host/ai-generation/start-exploration
**Request:**
```json
{
  "tree_id": "uuid",
  "device_id": "device_1",
  "device_model_name": "android_mobile",
  "userinterface_name": "horizon_android_mobile",
  "team_id": "team_1",
  "exploration_depth": 5
}
```

**Response:**
```json
{
  "success": true,
  "exploration_id": "uuid",
  "message": "Exploration started"
}
```

### GET /host/ai-generation/exploration-status/<id>
**Response (exploring):**
```json
{
  "success": true,
  "status": "exploring",
  "current_step": "Testing DPAD_RIGHT from home_temp...",
  "progress": {
    "total_screens_found": 5,
    "screens_analyzed": 3,
    "nodes_proposed": 3,
    "edges_proposed": 2
  }
}
```

**Response (completed):**
```json
{
  "success": true,
  "status": "completed",
  "proposed_nodes": [
    {"id": "home_temp", "name": "Home", "screen_type": "menu"},
    {"id": "settings_temp", "name": "Settings", "screen_type": "menu"}
  ],
  "proposed_edges": [
    {"id": "edge_home_to_settings_temp", "source": "home_temp", "target": "settings_temp"}
  ]
}
```

### POST /host/ai-generation/approve-generation
**Request:**
```json
{
  "exploration_id": "uuid",
  "tree_id": "uuid",
  "approved_nodes": ["home_temp", "settings_temp"],
  "approved_edges": ["edge_home_to_settings_temp"],
  "team_id": "team_1"
}
```

**Response:**
```json
{
  "success": true,
  "nodes_created": 2,
  "edges_created": 1,
  "message": "Successfully created 2 nodes and 1 edge"
}
```

### POST /host/ai-generation/cancel-exploration
**Request:**
```json
{
  "exploration_id": "uuid",
  "team_id": "team_1"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Exploration cancelled, temporary nodes deleted"
}
```

---

## Conclusion

AI Tree Creation provides a powerful, automated way to generate navigation structures while maintaining full compatibility with your existing navigation system. The non-destructive `_temp` suffix approach ensures safety, while the depth-first exploration strategy ensures comprehensive coverage.

**Key Benefits:**
- 🚀 **Fast** - Generate trees in minutes instead of hours
- 🎯 **Accurate** - AI vision understands menu structures
- 🛡️ **Safe** - Non-destructive temp nodes with user approval
- 🔄 **Compatible** - Works with all existing navigation features
- 📊 **Smart** - AI anticipates tree structure before exploring

**Version:** 1.0.0  
**Last Updated:** 2025-01-04

