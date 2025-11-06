# AI Interface Generation Plan (Model AI Generation)

## Overview

This document outlines the comprehensive plan for implementing AI-driven interface exploration and automated navigation tree generation. The system will allow AI to explore user interfaces step-by-step, analyze screens using image analysis and UI element detection, and automatically generate complete navigation trees with nodes and edges.

## System Architecture

### Integration with Navigation Editor
- **Same Device Control**: Use identical device selection and control mechanisms as NavigationEditor.tsx
- **Device Management**: Leverage existing host manager context for device connectivity
- **Interface Selection**: Select userinterface from available options (horizon_android_mobile, horizon_android_tv, etc.)
- **Entry Point**: Ensure home node exists as starting point for exploration

### AI Exploration Modal
- **Left Panel**: Real-time exploration dashboard showing:
  - Current screen analysis (what AI sees)
  - AI reasoning and decision making
  - Each command being executed
  - Progress status (screens analyzed, elements tested)
- **Polling**: Frontend polls server every 5 seconds for progress updates
- **Final Result**: When exploration completes, shows proposed nodes and edges
- **User Decision**: Simple **Confirm** or **Cancel** buttons
- **Generate Action**: If Confirm → Create in database, if Cancel → Do nothing

### New Components Structure
```
useGenerateModel.ts - Main hook for AI interface generation
backend routes:
- /server/ai-generation/start-exploration - Start AI exploration
- /server/ai-generation/exploration-status/<id> - Get progress + final results
- /server/ai-generation/approve-generation - Create approved nodes/edges in DB
- /server/ai-generation/cancel-exploration - Stop exploration
```

### Polling & Status Flow
1. **Start**: Call `/start-exploration` → Get exploration_id
2. **Poll**: Every 5 seconds call `/exploration-status/<id>`
   - **While Running**: Shows progress, current step, AI reasoning
   - **When Complete**: Shows final proposed nodes and edges
3. **User Decision**: 
   - **Confirm** → Call `/approve-generation` with selected nodes/edges
   - **Cancel** → Call `/cancel-exploration` or just close modal
4. **Result**: Nodes/edges created in database, ReactFlow refreshes

## Exploration Strategy

### Starting Point
- **Home Detection**: AI must identify and start from home/main menu
- **Entry Validation**: Ensure entry node exists with proper navigation structure
- **Baseline Screenshot**: Capture initial state for reference

### Step-by-Step Process
1. **Screen Analysis**: AI analyzes current screenshot using image analysis
2. **Element Detection**: Identify interactive elements (buttons, menus, etc.)
3. **Action Execution**: Try each interactive element through controller
4. **State Verification**: Confirm navigation worked by taking new screenshot
5. **Node Creation**: Generate appropriate node for discovered screen
6. **Edge Creation**: Create edge connecting previous node to new node
7. **Backtrack**: Return to previous screen to continue exploration

### Exploration Parameters
- **Default Depth**: 5 levels maximum for testing
- **User Configurable**: Allow depth adjustment before starting
- **No Boundaries**: No restrictions on exploration scope initially
- **Wait Time**: 5 seconds between commands (user adjustable)

## Image Analysis & Detection

### Mobile Device Analysis
- **Screenshot Capture**: High-resolution screen capture
- **UI Element Detection**: Identify buttons, menus, text, images
- **dumpui Integration**: Use Android dumpui for detailed element information
- **Coordinate Mapping**: Map UI elements to screen coordinates

### Analysis Capabilities
- **Element Classification**: Distinguish between buttons, text, containers
- **Navigation Elements**: Identify menu items, back buttons, navigation bars
- **Interactive Detection**: Determine which elements are clickable/actionable
- **State Recognition**: Recognize loading states, dialogs, overlays

### Screen Uniqueness
- **Image Comparison**: Compare screenshots to detect screen changes
- **Element Signature**: Create unique fingerprint for each screen
- **State Detection**: Identify when navigation was successful
- **Error Recovery**: Detect when navigation failed or got lost

## Node & Edge Generation

### Naming Convention
- **Root Level**: `home` for main menu
- **Sibling Exploration**: `home_menu1`, `home_menu2` for siblings
- **Nested Navigation**: `settings` -> `settings_submenu1`, `settings_submenu2`
- **Consistent Pattern**: Follow existing tree naming logic

### Node Structure
```json
{
  "id": "generated_node_id",
  "label": "Screen Name",
  "type": "screen",
  "position": {"x": 250, "y": 250},
  "data": {
    "type": "screen",
    "description": "AI-generated screen description",
    "screenshot_path": "/path/to/screenshot",
    "ui_elements": ["button1", "menu2", "text3"],
    "detected_at": "2024-01-01T12:00:00Z"
  }
}
```

### Edge Structure
```json
{
  "id": "generated_edge_id",
  "source": "source_node_id",
  "target": "target_node_id",
  "type": "navigation",
  "data": {
    "action_sets": [{
      "id": "ai_generated_action_set",
      "direction": "forward",
      "actions": [{
        "controller_type": "android_mobile",
        "command": "tap",
        "params": {"x": 500, "y": 300}
      }]
    }],
    "default_action_set_id": "ai_generated_action_set",
    "final_wait_time": 5000
  }
}
```

## Exploration Logic

### Sibling-First Strategy
1. **Current Level**: Identify all interactive elements on current screen
2. **Test Each Element**: Try every button/menu item before going deeper
3. **Document Siblings**: Create nodes for all same-level screens
4. **Depth Navigation**: Only after completing current level, go deeper
5. **Breadth-First**: Ensures complete mapping of each menu level

### Navigation Flow
```
Home Screen Analysis
├── Identify all menu items (e.g., Live, VOD, Settings, Guide)
├── Test "Live" → Create live node + edge
├── Test "VOD" → Create vod node + edge  
├── Test "Settings" → Create settings node + edge
├── Test "Guide" → Create guide node + edge
└── Enter "Settings" for deeper exploration
    ├── Identify Settings submenu items
    ├── Test each settings option
    └── Create settings_* nodes + edges
```

### Error Handling
- **Lost Detection**: If AI gets lost, fail immediately for now
- **Screenshot Comparison**: Detect when navigation didn't work
- **Retry Logic**: Simple retry mechanism for failed actions
- **Recovery**: Basic backtrack if possible, otherwise abort

## Implementation Components

### Backend Routes

#### `/server/ai-generation/start-exploration`
```python
POST /server/ai-generation/start-exploration
{
  "tree_id": "uuid",
  "host_ip": "192.168.1.100",
  "device_id": "uuid",
  "exploration_depth": 5,
  "start_node_id": "home_id"  // Optional
}
Response: {
  "success": true,
  "exploration_id": "uuid",
  "message": "Exploration started"
}
```

#### `/server/ai-generation/exploration-status/<id>`
```python
GET /server/ai-generation/exploration-status/<exploration_id>?host_ip=192.168.1.100

// While Running:
Response: {
  "success": true,
  "exploration_id": "uuid",
  "status": "exploring",
  "current_step": "Testing Live button from home screen...",
  "progress": {
    "total_screens_found": 8,
    "screens_analyzed": 3,
    "nodes_proposed": 0,
    "edges_proposed": 0
  },
  "current_analysis": {
    "screen_name": "home",
    "elements_found": ["Live", "VOD", "Settings", "Guide"],
    "reasoning": "Found 4 main menu items, testing navigation to each"
  }
}

// When Complete:
Response: {
  "success": true,
  "exploration_id": "uuid", 
  "status": "completed",
  "current_step": "Exploration completed. Found 12 screens.",
  "progress": {
    "total_screens_found": 12,
    "screens_analyzed": 12,
    "nodes_proposed": 12,
    "edges_proposed": 15
  },
  "proposed_nodes": [
    {
      "id": "home",
      "name": "Home",
      "screen_type": "menu",
      "reasoning": "Main home screen with 4 menu options"
    },
    {
      "id": "home_live", 
      "name": "Live TV",
      "screen_type": "content",
      "reasoning": "Live TV screen accessed from home via right arrow"
    }
  ],
  "proposed_edges": [
    {
      "id": "home_to_live",
      "source": "home",
      "target": "home_live",
      "action_sets": [...],
      "reasoning": "Navigate from home to live via right arrow key"
    }
  ]
}
```

#### `/server/ai-generation/approve-generation`
```python
POST /server/ai-generation/approve-generation
{
  "exploration_id": "uuid",
  "tree_id": "uuid", 
  "host_ip": "192.168.1.100",
  "approved_nodes": ["home", "home_live", "home_vod"],
  "approved_edges": ["home_to_live", "home_to_vod"]
}
Response: {
  "success": true,
  "nodes_created": 3,
  "edges_created": 2,
  "message": "Successfully created 3 nodes and 2 edges"
}
```

### Frontend Components

#### useGenerateModel Hook
```typescript
interface UseGenerateModelProps {
  treeId: string;
  selectedHost: Host;
  selectedDeviceId: string;
  isControlActive: boolean;
}

const useGenerateModel = ({...props}) => {
  return {
    // State
    explorationId: string | null;
    isExploring: boolean;
    status: 'idle' | 'exploring' | 'completed' | 'failed';
    currentStep: string;
    progress: {
      total_screens_found: number;
      screens_analyzed: number;
      nodes_proposed: number;
      edges_proposed: number;
    };
    currentAnalysis: {
      screen_name: string;
      elements_found: string[];
      reasoning: string;
    };
    proposedNodes: ProposedNode[];
    proposedEdges: ProposedEdge[];
    
    // Actions
    startExploration: (depth: number) => Promise<void>;
    cancelExploration: () => Promise<void>;
    approveGeneration: (nodeIds: string[], edgeIds: string[]) => Promise<void>;
  }
}
```

#### Polling Implementation
```typescript
// Auto-polls every 5 seconds when exploring
useEffect(() => {
  if (isExploring && explorationId) {
    const interval = setInterval(() => {
      fetchExplorationStatus(explorationId);
    }, 5000);
    return () => clearInterval(interval);
  }
}, [isExploring, explorationId]);
```

#### AI Exploration Modal Component
```typescript
interface AIExplorationModalProps {
  isOpen: boolean;
  onClose: () => void;
  treeId: string;
  selectedHost: Host;
  selectedDeviceId: string;
  onGenerated: () => void;  // Refresh ReactFlow after generation
}

// Modal Layout:
// Left Panel: Real-time exploration view
// - Current step: "Testing Live button from home screen..."
// - Progress: "Screens: 3/8 analyzed, Elements: 12 tested"
// - Current analysis: "Found 4 main menu items: Live, VOD, Settings, Guide"
// - AI reasoning: "Testing navigation to each menu item..."
//
// Bottom: When status === 'completed'
// - Proposed nodes list with checkboxes
// - Proposed edges list with checkboxes  
// - Confirm button (creates selected items)
// - Cancel button (discards everything)
```

### Database Integration

#### Use Existing Tables
- **navigation_trees**: Store generated tree metadata
- **navigation_nodes**: Store AI-generated nodes
- **navigation_edges**: Store AI-generated edges
- **Same Schema**: Follow existing table structure exactly

#### AI Exploration Tracking
```sql
-- New table for tracking exploration sessions
CREATE TABLE ai_exploration_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID NOT NULL REFERENCES teams(id),
  userinterface_id UUID NOT NULL REFERENCES userinterfaces(id),
  tree_id UUID NOT NULL REFERENCES navigation_trees(id),
  host_name TEXT NOT NULL,
  device_model TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
  depth_limit INTEGER NOT NULL DEFAULT 5,
  wait_time_ms INTEGER NOT NULL DEFAULT 5000,
  nodes_created INTEGER DEFAULT 0,
  edges_created INTEGER DEFAULT 0,
  exploration_log JSONB NOT NULL DEFAULT '[]',
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Minimalist First Version

### Scope Limitations
- **Single Device Type**: Start with android_mobile only
- **Basic Analysis**: Simple screenshot comparison and element detection
- **No Verification**: Skip verification logic initially
- **Manual Approval**: Always require user approval before generating
- **Fixed Timing**: 5-second wait between actions
- **No Recovery**: If lost, fail immediately

### Success Criteria
- AI can explore 5 levels deep in a mobile interface
- Correctly identifies and clicks menu items
- Generates proper node and edge structures
- Creates nodes with consistent naming convention
- Saves results to existing database tables
- User can approve/reject proposed changes

### Technical Requirements
- Leverage existing NavigationEditor device control
- Use existing screenshot capture mechanisms
- Integrate with current image analysis functions
- Follow existing node/edge data structures
- Use same database tables and APIs

## Future Enhancements

### Advanced Analysis
- **Loading State Detection**: Recognize and wait for loading screens
- **Dynamic Content**: Handle dynamic menus and content
- **Multi-Device**: Support for android_tv, web interfaces
- **Verification Integration**: Add verification after generation

### Intelligent Navigation  
- **Context Awareness**: Understand menu hierarchy and context
- **Smart Timing**: Adaptive wait times based on screen analysis
- **Error Recovery**: Sophisticated recovery from navigation errors
- **State Preservation**: Save and restore exploration state

### User Experience
- **Progress Visualization**: Visual tree building in real-time
- **Selective Generation**: Choose which nodes/edges to create
- **Preview Mode**: Dry run without actual generation
- **Batch Operations**: Generate multiple trees simultaneously

## Implementation Timeline

### Phase 1: Core Infrastructure (Week 1)
- Backend routes for exploration API
- Basic AI agent integration
- Screenshot analysis pipeline
- Database schema additions

### Phase 2: Exploration Engine (Week 2)  
- Step-by-step navigation logic
- Element detection and interaction
- Node/edge generation logic
- Error handling and recovery

### Phase 3: Frontend Integration (Week 3)
- useGenerateModel hook implementation
- AI exploration modal component
- Integration with NavigationEditor
- User approval workflow

## Frontend Integration Architecture

### NavigationEditor Integration (Minimal Impact)

#### UI Integration Requirements
- **Button Location**: Add "AI Generate" button to NavigationEditorHeader Section 4 (rightmost)
- **Control State Dependency**: Button ONLY visible when `isControlActive` is true (same as validation buttons)
- **Button State Logic**: 
  ```typescript
  disabled={!selectedHost || !selectedDeviceId || !isControlActive}
  ```
- **Modal Overlay**: Add AIGenerationModal at same level as existing dialogs (NodeEditDialog, EdgeEditDialog)

#### Required Code Changes

**1. NavigationEditorHeader.tsx**:
```typescript
// Add to props interface
onToggleAIGeneration: () => void;

// Add to Section 4 - ONLY show when control is active
{isControlActive && (
  <Button
    variant="outlined"
    startIcon={<SmartToyIcon />}
    onClick={onToggleAIGeneration}
    disabled={!selectedHost || !selectedDeviceId}
    size="small"
  >
    AI Generate
  </Button>
)}
```

**2. NavigationEditor.tsx**:
```typescript
// Add state
const [isAIGenerationOpen, setIsAIGenerationOpen] = useState(false);

// Add handler
const handleToggleAIGeneration = () => setIsAIGenerationOpen(true);

// Add to NavigationEditorHeader props
onToggleAIGeneration={handleToggleAIGeneration}

// Add modal after existing dialogs - ONLY when control active
{isAIGenerationOpen && isControlActive && (
  <AIGenerationModal
    isOpen={isAIGenerationOpen}
    treeId={actualTreeId}
    selectedHost={selectedHost}
    selectedDeviceId={selectedDeviceId}
    onClose={() => setIsAIGenerationOpen(false)}
    onGenerated={handleRefreshTree}
  />
)}
```

#### Component Architecture
- **useGenerateModel Hook**: Handles all AI exploration logic and state
- **AIGenerationModal Component**: Left panel for real-time exploration view
- **Zero Layout Disruption**: Existing grid layout remains unchanged
- **Consistent UX Pattern**: Same approach as node/edge edit dialogs

### Phase 4: Testing & Refinement (Week 4)
- Test with existing userinterfaces
- Refine AI analysis accuracy
- Optimize timing and reliability
- User experience improvements

This plan provides a solid foundation for implementing AI-driven interface exploration while maintaining integration with your existing navigation system and following established patterns.
