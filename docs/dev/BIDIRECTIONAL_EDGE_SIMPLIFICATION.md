# Bidirectional Edge Simplification Plan

## Current Problems

### 1. **Overly Complex Action Set Management**
- Multiple action sets per edge with priorities (`_1`, `_2`, etc.)
- Dynamic ID generation with timestamps and priorities
- Complex logic to determine which action set to edit/display
- Inconsistent naming patterns across the system

### 2. **Direction Confusion**
- Hard to determine which action set represents which direction
- Complex parsing logic to extract direction from action set names
- Fallback panels and missing direction handling
- Priority-based direction logic that's not intuitive

### 3. **Code Complexity**
- Multiple places handling action set selection
- Complex dependency arrays and effect loops
- Inconsistent data structures between frontend and backend
- Edge cases for missing action sets or directions

## Proposed Solution: Hardcoded Bidirectional Convention

### Core Convention
**Every edge has exactly 2 action sets with hardcoded IDs:**
1. `source_to_target` - Actions to go FROM source TO target
2. `target_to_source` - Actions to go FROM target TO source

### Example
For an edge between nodes `home` and `home_saved`:
- **Forward:** `home_to_home_saved` (Click Saved Tab)
- **Reverse:** `home_saved_to_home` (Click Home Tab)

## Implementation Plan

### Phase 1: Database Schema Simplification

#### 1.1 Update Action Set Structure
```sql
-- Each edge will have exactly 2 action sets
-- Remove priority system, use hardcoded direction-based IDs
```

#### 1.2 Migration Script
```sql
-- Convert existing edges to new format
-- For each edge:
--   1. Create source_to_target action set from priority 1
--   2. Create target_to_source action set from priority 2
--   3. Remove all other action sets
--   4. Update default_action_set_id to source_to_target
```

### Phase 2: Frontend Simplification

#### 2.1 Remove Complex Logic
- **Delete:** Priority-based action set selection
- **Delete:** Dynamic ID generation with timestamps
- **Delete:** Fallback panel logic
- **Delete:** Action set ID parsing logic

#### 2.2 Simplify Components

##### EdgeSelectionPanel
```typescript
// NEW: Simple hardcoded direction determination
const getDirectionActionSets = (edge: UINavigationEdge) => {
  const sourceLabel = getNodeLabel(edge.source);
  const targetLabel = getNodeLabel(edge.target);
  
  return {
    forward: {
      id: `${sourceLabel}_to_${targetLabel}`,
      direction: `${sourceLabel} → ${targetLabel}`
    },
    reverse: {
      id: `${targetLabel}_to_${sourceLabel}`,
      direction: `${targetLabel} → ${sourceLabel}`
    }
  };
};

// Always show exactly 2 panels for each edge
const forwardActionSet = edge.action_sets.find(as => as.id === directions.forward.id);
const reverseActionSet = edge.action_sets.find(as => as.id === directions.reverse.id);
```

##### EdgeEditDialog
```typescript
// NEW: No more action set selection complexity
interface EdgeEditProps {
  edge: UINavigationEdge;
  direction: 'forward' | 'reverse'; // Simple enum
}

// Always know which action set to edit based on direction
const actionSetId = direction === 'forward' 
  ? `${sourceLabel}_to_${targetLabel}`
  : `${targetLabel}_to_${sourceLabel}`;
```

#### 2.3 Remove Unused Code
- **Delete:** `targetActionSetId` field from EdgeForm
- **Delete:** Priority handling logic
- **Delete:** Fallback action set creation
- **Delete:** Dynamic action set ID generation

### Phase 3: Backend Simplification

#### 3.1 Edge Creation
```python
def create_edge(source_node_id, target_node_id):
    source_label = get_node_label(source_node_id)
    target_label = get_node_label(target_node_id)
    
    return {
        'edge_id': f'edge-{source_node_id}-{target_node_id}',
        'action_sets': [
            {
                'id': f'{source_label}_to_{target_label}',
                'label': f'{source_label} → {target_label}',
                'actions': [],
                'retry_actions': [],
                'failure_actions': []
            },
            {
                'id': f'{target_label}_to_{source_label}',
                'label': f'{target_label} → {source_label}',
                'actions': [],
                'retry_actions': [],
                'failure_actions': []
            }
        ],
        'default_action_set_id': f'{source_label}_to_{target_label}'
    }
```

#### 3.2 Remove Complex Validation
- **Delete:** Priority validation logic
- **Delete:** Action set count limits
- **Delete:** Dynamic action set ID validation

### Phase 4: Benefits

#### 4.1 Predictable Structure
- Every edge has exactly 2 action sets
- Action set IDs are always predictable: `nodeA_to_nodeB` and `nodeB_to_nodeA`
- No more searching or parsing - direct lookup by formula

#### 4.2 Dynamic Node Label Updates
- If node label changes from `home` to `main_menu`, action sets automatically become:
  - `main_menu_to_home_saved`
  - `home_saved_to_main_menu`
- No manual ID updates needed

#### 4.3 Simplified UI Logic
```typescript
// OLD: Complex action set selection
const selectedActionSet = edge.action_sets.find(as => 
  as.id === targetActionSetId || 
  as.priority === selectedPriority ||
  as.id === defaultActionSetId
) || edge.action_sets[0];

// NEW: Simple direction-based lookup
const actionSet = edge.action_sets.find(as => 
  as.id === `${fromNode}_to_${toNode}`
);
```

#### 4.4 No Edge Cases
- No fallback panels (both directions always exist)
- No missing action sets (created automatically)
- No priority conflicts (hardcoded structure)
- No dynamic ID generation (formula-based)

## Files to Modify

### Frontend - Specific Complexity Areas Identified

#### 1. **Types (Navigation_Types.ts)**
**Remove:**
- `priority: number` from ActionSet interface (line 20)
- `priority?: 'p1' | 'p2' | 'p3'` from UINavigationEdgeData (line 83)
- `priority?: 'p1' | 'p2' | 'p3'` from EdgeForm (line 246)
- `targetActionSetId?: string` from EdgeForm (line 248)

**Replace with:**
```typescript
interface ActionSet {
  id: string; // Format: nodeA_to_nodeB
  label: string; // Format: nodeA → nodeB
  actions: Action[];
  retry_actions?: Action[];
  failure_actions?: Action[];
  // REMOVED: priority, conditions, timer
}

interface EdgeForm {
  edgeId: string;
  action_sets: [ActionSet, ActionSet]; // Always exactly 2
  default_action_set_id: string; // Always source_to_target
  final_wait_time: number;
  // REMOVED: priority, threshold, targetActionSetId
}
```

#### 2. **Edge Selection Panel (Navigation_EdgeSelectionPanel.tsx)**
**Remove:**
- Lines 69-84: Complex direction parsing from action set ID
- Lines 148-168: Fallback panel logic with priority handling
- Lines 151-160: Dynamic action set creation with priority

**Replace with:**
```typescript
// Simple hardcoded direction lookup
const directions = {
  forward: `${sourceLabel}_to_${targetLabel}`,
  reverse: `${targetLabel}_to_${sourceLabel}`
};

// Always show 2 panels, one per direction
const forwardActionSet = edge.action_sets.find(as => as.id === directions.forward);
const reverseActionSet = edge.action_sets.find(as => as.id === directions.reverse);
```

#### 3. **Edge Edit Hook (useEdgeEdit.ts)**
**Remove:**
- Lines 42-51: targetActionSetId selection logic
- Lines 88: Complex dependency array causing loops

**Replace with:**
```typescript
// Simple direction-based editing
const useEdgeEdit = ({ direction, edge, ... }) => {
  const actionSetId = direction === 'forward' 
    ? `${sourceLabel}_to_${targetLabel}`
    : `${targetLabel}_to_${sourceLabel}`;
    
  const actionSet = edge.action_sets.find(as => as.id === actionSetId);
  // No complex selection logic needed
};
```

#### 4. **Edge Creation (useNavigationEditor.ts)**
**Remove:**
- Dynamic ID generation with timestamps
- Priority-based action set creation

**Replace with:**
```typescript
const createEdgeData = (sourceLabel: string, targetLabel: string) => ({
  action_sets: [
    {
      id: `${sourceLabel}_to_${targetLabel}`,
      label: `${sourceLabel} → ${targetLabel}`,
      actions: [], retry_actions: [], failure_actions: []
    },
    {
      id: `${targetLabel}_to_${sourceLabel}`,
      label: `${targetLabel} → ${sourceLabel}`,
      actions: [], retry_actions: [], failure_actions: []
    }
  ],
  default_action_set_id: `${sourceLabel}_to_${targetLabel}`
});
```

#### 5. **Context Files**
**NavigationConfigContext.tsx:**
- Remove `priority: number` from ActionSet interface (line 56)

#### 6. **Component Simplification**
**Navigation_ActionSetPanel.tsx:**
- Remove priority-based logic
- Simplify to direction-based display only

#### 7. **Hook Simplification**
**useEdge.ts:**
- Remove `getDefaultActionSet` complexity
- Remove `executeActionSet` by ID lookup
- Simplify to direction-based action set access

### Backend
1. **Remove:**
   - Priority-based action set logic
   - Dynamic ID generation
   - Complex validation rules

2. **Simplify:**
   - Edge creation endpoints
   - Action set validation
   - Database queries

## Migration Steps

### Step 1: Database Migration
```sql
-- Migrate existing edges to new format
-- Create exactly 2 action sets per edge
-- Use node labels for predictable IDs
```

### Step 2: Update Types
```typescript
interface ActionSet {
  id: string; // Always: nodeA_to_nodeB format
  label: string; // Always: nodeA → nodeB format
  actions: Action[];
  retry_actions: Action[];
  failure_actions: Action[];
  // REMOVED: priority field
}

interface EdgeForm {
  edgeId: string;
  action_sets: [ActionSet, ActionSet]; // Always exactly 2
  default_action_set_id: string; // Always source_to_target
  // REMOVED: targetActionSetId
  // REMOVED: priority
}
```

### Step 3: Update Components
- Remove all priority-based logic
- Remove fallback handling
- Use simple direction enum: 'forward' | 'reverse'

### Step 4: Testing
- Verify all edges have exactly 2 action sets
- Test node label changes update action set IDs
- Confirm no more infinite loops or complex selection logic

## Expected Code Reduction

- **~40% reduction** in edge management code
- **~60% reduction** in action set selection logic
- **~80% reduction** in edge creation complexity
- **100% elimination** of fallback and priority handling

## Risk Mitigation

### Clean Slate Approach
- No backward compatibility
- No fallback systems
- Complete replacement of existing logic
- Full database migration required

### Testing Strategy
- Migration script testing on dev environment
- Component testing with new simplified structure
- End-to-end testing of edge creation/editing
- Performance testing of simplified queries

## Timeline

1. **Week 1:** Database migration and backend updates
2. **Week 2:** Frontend type updates and core logic
3. **Week 3:** Component simplification and testing
4. **Week 4:** Integration testing and deployment

This plan eliminates all the complexity we've been struggling with and creates a clean, predictable system that's easy to understand and maintain.
