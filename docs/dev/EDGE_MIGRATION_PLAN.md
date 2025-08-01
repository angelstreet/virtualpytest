# Edge Migration Plan: Single Edge to Action Sets

## ⚠️ CRITICAL: NO BACKWARD COMPATIBILITY
**This migration will NOT maintain backward compatibility. All legacy code, fallbacks, and old references will be completely removed. This is a clean break from the old structure.**

## Overview
Migrate from current single-action edge structure to optimized action sets structure, enabling multiple ways to navigate between the same nodes while maintaining single edge relationships.

## Current vs New Structure

### Current Structure
```json
{
  "edge_id": "uuid",
  "source_node_id": "live",
  "target_node_id": "zap", 
  "actions": [{"command": "press_key", "params": {"key": "CH+"}}],
  "retry_actions": [{"command": "press_key", "params": {"key": "BACK"}}],
  "final_wait_time": 2000
}
```

### New Structure
```json
{
  "edge_id": "uuid",
  "source_node_id": "live",
  "target_node_id": "zap",
  "action_sets": [
    {
      "id": "ch_plus",
      "label": "Channel+",
      "actions": [{"command": "press_key", "params": {"key": "CH+"}}],
      "retry_actions": [{"command": "press_key", "params": {"key": "BACK"}}],
      "priority": 1,
      "conditions": {},
      "timer": 0
    },
    {
      "id": "digit_btn", 
      "label": "Digit Button",
      "actions": [{"command": "press_key", "params": {"key": "1"}}],
      "retry_actions": [{"command": "press_key", "params": {"key": "MENU"}}],
      "priority": 2,
      "conditions": {},
      "timer": 2000
    }
  ],
  "default_action_set_id": "ch_plus",
  "final_wait_time": 2000
}
```

## Migration Phases

### Phase 1: Database Schema Update

#### 1.1 Add New Columns (Non-Breaking)
```sql
-- Add new columns to navigation_edges table
ALTER TABLE navigation_edges 
ADD COLUMN action_sets JSONB DEFAULT '[]',
ADD COLUMN default_action_set_id VARCHAR(255) DEFAULT NULL;

-- Create index for better performance
CREATE INDEX idx_navigation_edges_action_sets ON navigation_edges USING GIN (action_sets);
```

#### 1.2 Data Migration Script (ONE-TIME ONLY)
```python
# migration_script.py
def migrate_edges_to_action_sets():
    """ONE-TIME migration: Convert existing edges to action_sets structure"""
    
    supabase = get_supabase()
    
    # Get all edges with existing actions
    edges = supabase.table('navigation_edges')\
        .select('*')\
        .neq('actions', '[]')\
        .execute()
    
    for edge in edges.data:
        # Create action set from existing actions
        action_set = {
            'id': 'default',
            'label': 'Default Actions',
            'actions': edge.get('actions', []),
            'retry_actions': edge.get('retry_actions', []),
            'priority': 1,
            'conditions': {},
            'timer': 0
        }
        
        # Update edge with new structure
        supabase.table('navigation_edges')\
            .update({
                'action_sets': [action_set],
                'default_action_set_id': 'default'
            })\
            .eq('edge_id', edge['edge_id'])\
            .execute()
    
    print(f"Migrated {len(edges.data)} edges to action_sets structure")

# ⚠️ IMPORTANT: This script will be deleted after migration is complete
```

### Phase 2: Backend Code Updates

#### 2.1 Update Database Functions (`navigation_trees_db.py`)

```python
# NEW ONLY: save_edge function - NO LEGACY SUPPORT
def save_edge(tree_id: str, edge_data: Dict, team_id: str) -> Dict:
    """Save edge with action_sets structure ONLY"""
    try:
        supabase = get_supabase()
        
        # STRICT: Only accept new action_sets format
        if not edge_data.get('action_sets'):
            raise ValueError("action_sets is required - no legacy format accepted")
        
        normalized_edge = {
            'edge_id': edge_data.get('edge_id'),
            'source_node_id': edge_data.get('source_node_id'),
            'target_node_id': edge_data.get('target_node_id'),
            'action_sets': edge_data.get('action_sets'),
            'default_action_set_id': edge_data.get('default_action_set_id'),
            'final_wait_time': edge_data.get('final_wait_time', 2000)
        }
        
        result = supabase.table('navigation_edges')\
            .upsert(normalized_edge)\
            .execute()
            
        return {'success': True, 'edge': result.data[0]}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# NEW ONLY: get_tree_edges function - NO LEGACY SUPPORT
def get_tree_edges(tree_id: str, team_id: str) -> Dict:
    """Get edges with action_sets structure ONLY"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('navigation_edges')\
            .select('edge_id', 'source_node_id', 'target_node_id', 'action_sets', 'default_action_set_id', 'final_wait_time')\
            .eq('tree_id', tree_id)\
            .eq('team_id', team_id)\
            .execute()
        
        # STRICT: All edges must have action_sets
        for edge in result.data:
            if not edge.get('action_sets'):
                raise ValueError(f"Edge {edge.get('edge_id')} missing action_sets - migration incomplete")
        
        return {'success': True, 'edges': result.data}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

#### 2.2 Update NetworkX Graph Creation (`navigation_graph.py`)

```python
def create_networkx_graph(nodes: List[Dict], edges: List[Dict]) -> nx.DiGraph:
    """NEW ONLY: Graph creation with action_sets structure - NO LEGACY SUPPORT"""
    
    G = nx.DiGraph()
    
    # Add nodes (unchanged)
    for node in nodes:
        # ... existing node logic
    
    # NEW ONLY: action_sets processing
    for edge in edges:
        source_id = edge.get('source_node_id')
        target_id = edge.get('target_node_id')
        
        # STRICT: Require action_sets structure
        action_sets = edge.get('action_sets')
        if not action_sets:
            raise ValueError(f"Edge {edge.get('edge_id')} missing action_sets - no legacy support")
        
        default_action_set_id = edge.get('default_action_set_id')
        if not default_action_set_id:
            raise ValueError(f"Edge {edge.get('edge_id')} missing default_action_set_id")
        
        # Find default action set
        default_set = next(
            (s for s in action_sets if s['id'] == default_action_set_id),
            None
        )
        
        if not default_set:
            raise ValueError(f"Edge {edge.get('edge_id')} default action set '{default_action_set_id}' not found")
        
        # Add edge with NEW structure only
        G.add_edge(source_id, target_id, **{
            'edge_id': edge.get('edge_id'),
            'action_sets': action_sets,
            'default_action_set_id': default_action_set_id,
            'default_actions': default_set['actions'],
            'go_action': default_set['actions'][0]['command'] if default_set['actions'] else None,
            'alternatives_count': len(action_sets),
            'has_timer_actions': any(s.get('timer', 0) > 0 for s in action_sets),
            'final_wait_time': edge.get('final_wait_time', 2000),
            'weight': 1
        })
    
    return G
```

#### 2.3 Update Pathfinding (`navigation_pathfinding.py`)

```python
def find_shortest_path_with_action_selection(
    tree_id: str, 
    target_node_id: str, 
    team_id: str, 
    start_node_id: str = None,
    preferences: Dict = None
) -> Optional[List[Dict]]:
    """Enhanced pathfinding with action set selection"""
    
    # Get base path (unchanged)
    path = nx.shortest_path(G, actual_start_node, actual_target_node)
    
    navigation_transitions = []
    
    for i in range(len(path) - 1):
        from_node = path[i]
        to_node = path[i + 1]
        
        edge_data = G.edges[from_node, to_node]
        action_sets = edge_data.get('action_sets', [])
        
        # Select best action set based on preferences and context
        chosen_action_set = select_optimal_action_set(
            action_sets, 
            preferences, 
            from_node, 
            to_node
        )
        
        transition = {
            'transition_number': i + 1,
            'from_node_id': from_node,
            'to_node_id': to_node,
            'chosen_action_set': chosen_action_set,
            'available_action_sets': action_sets,
            'actions': chosen_action_set['actions'],
            'retryActions': chosen_action_set.get('retry_actions', []),
            'timer': chosen_action_set.get('timer', 0),
            'final_wait_time': edge_data.get('final_wait_time', 2000)
        }
        
        navigation_transitions.append(transition)
    
    return navigation_transitions

def select_optimal_action_set(
    action_sets: List[Dict], 
    preferences: Dict = None,
    from_node: str = None,
    to_node: str = None
) -> Dict:
    """Select best action set based on context and preferences"""
    
    if not action_sets:
        return {}
    
    # Default: use priority-based selection
    sorted_sets = sorted(action_sets, key=lambda x: x.get('priority', 999))
    
    # Apply preferences if provided
    if preferences:
        # Prefer timer actions if in "quick mode"
        if preferences.get('prefer_timer_actions'):
            timer_sets = [s for s in sorted_sets if s.get('timer', 0) > 0]
            if timer_sets:
                return timer_sets[0]
        
        # Prefer specific action types
        preferred_commands = preferences.get('preferred_commands', [])
        if preferred_commands:
            for action_set in sorted_sets:
                if any(action.get('command') in preferred_commands 
                      for action in action_set.get('actions', [])):
                    return action_set
    
    # Default: return highest priority (lowest number)
    return sorted_sets[0]
```

### Phase 3: Frontend Updates

#### 3.1 Update Type Definitions

```typescript
// types/pages/Navigation_Types.ts - NEW ONLY, NO LEGACY

interface ActionSet {
  id: string;
  label: string;
  actions: Action[];
  retry_actions?: Action[];
  priority: number;
  conditions?: any;
  timer?: number; // Timer action support
}

interface UINavigationEdge {
  id: string;
  source: string;
  target: string;
  data: {
    // NEW STRUCTURE ONLY - NO LEGACY FIELDS
    action_sets: ActionSet[]; // REQUIRED
    default_action_set_id: string; // REQUIRED
    final_wait_time: number;
  };
}
```

#### 3.2 Update useEdge Hook

```typescript
// hooks/navigation/useEdge.ts - NEW ONLY, NO LEGACY

export const useEdge = (props?: UseEdgeProps) => {
  // NEW ONLY: action_sets extraction
  const getActionSetsFromEdge = useCallback((edge: UINavigationEdge): ActionSet[] => {
    // STRICT: Only accept new format
    if (!edge.data?.action_sets) {
      throw new Error("Edge missing action_sets - no legacy support");
    }
    
    return edge.data.action_sets;
  }, []);

  const getDefaultActionSet = useCallback((edge: UINavigationEdge): ActionSet => {
    const actionSets = getActionSetsFromEdge(edge);
    const defaultId = edge.data.default_action_set_id;
    
    if (!defaultId) {
      throw new Error("Edge missing default_action_set_id");
    }
    
    const defaultSet = actionSets.find(set => set.id === defaultId);
    if (!defaultSet) {
      throw new Error(`Default action set '${defaultId}' not found`);
    }
    
    return defaultSet;
  }, [getActionSetsFromEdge]);

  const executeActionSet = useCallback(async (
    edge: UINavigationEdge,
    actionSetId: string
  ) => {
    const actionSets = getActionSetsFromEdge(edge);
    const actionSet = actionSets.find(set => set.id === actionSetId);
    
    if (!actionSet) {
      throw new Error(`Action set ${actionSetId} not found`);
    }

    return await actionHook.executeActions(
      actionSet.actions.map(convertToControllerAction),
      (actionSet.retry_actions || []).map(convertToControllerAction)
    );
  }, [getActionSetsFromEdge, actionHook, convertToControllerAction]);

  return {
    // NEW METHODS ONLY - NO LEGACY
    getActionSetsFromEdge,
    getDefaultActionSet,
    executeActionSet,
    
    // ... other methods using action_sets structure
  };
};
```

#### 3.3 Update EdgeSelectionPanel Component

```typescript
// components/navigation/Navigation_EdgeSelectionPanel.tsx

interface EdgeSelectionPanelProps {
  selectedEdge: UINavigationEdge;
  actionSet?: ActionSet; // NEW: specific action set to display
  actionSetIndex?: number; // NEW: for multiple panels
  onClose: () => void;
  // ... other props
}

export const EdgeSelectionPanel: React.FC<EdgeSelectionPanelProps> = ({
  selectedEdge,
  actionSet,
  actionSetIndex = 0,
  onClose,
  // ... other props
}) => {
  const edgeHook = useEdge({ selectedHost, selectedDeviceId, isControlActive });
  
  // If specific action set provided, use it; otherwise use default
  const displayActionSet = actionSet || edgeHook.getDefaultActionSet(selectedEdge);
  const actions = displayActionSet?.actions || [];
  const retryActions = displayActionSet?.retry_actions || [];

  return (
    <Paper
      sx={{
        position: 'absolute',
        top: 16,
        right: 16 + actionSetIndex * 380, // Position multiple panels
        width: 360,
        border: displayActionSet?.priority === 1 ? '2px solid #1976d2' : undefined,
      }}
    >
      {/* Panel header with action set info */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6">
            {displayActionSet?.label || 'Edge Actions'}
          </Typography>
          {displayActionSet?.priority === 1 && (
            <Typography variant="caption" sx={{ color: '#1976d2', fontWeight: 'bold' }}>
              DEFAULT
            </Typography>
          )}
          {displayActionSet?.timer && displayActionSet.timer > 0 && (
            <Typography variant="caption" sx={{ color: '#ff9800', fontWeight: 'bold' }}>
              AUTO-RETURN {displayActionSet.timer}ms
            </Typography>
          )}
        </Box>
        <IconButton size="small" onClick={onClose}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Actions display (same as before, but using displayActionSet) */}
      {actions.length > 0 && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="caption">Actions:</Typography>
          {actions.map((action, index) => (
            <Typography key={index} variant="body2">
              {index + 1}. {formatActionDisplay(action)}
            </Typography>
          ))}
        </Box>
      )}

      {/* Retry actions */}
      {retryActions.length > 0 && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="caption" sx={{ color: 'warning.main' }}>
            Retry Actions:
          </Typography>
          {retryActions.map((action, index) => (
            <Typography key={`retry-${index}`} variant="body2" sx={{ color: 'warning.main' }}>
              R{index + 1}. {formatActionDisplay(action)}
            </Typography>
          ))}
        </Box>
      )}

      {/* Action buttons */}
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        <Button onClick={() => handleEditActionSet(displayActionSet)}>
          Edit
        </Button>
        <Button onClick={() => handleRunActionSet(displayActionSet)}>
          Run
        </Button>
      </Box>
    </Paper>
  );
};
```

#### 3.4 Update Parent Component to Show Multiple Panels

```typescript
// In navigation editor component
const selectedActionSets = useMemo(() => {
  if (!selectedEdge) return [];
  
  const edgeHook = useEdge();
  return edgeHook.getActionSetsFromEdge(selectedEdge);
}, [selectedEdge]);

// Render multiple panels
{selectedActionSets.map((actionSet, index) => (
  <EdgeSelectionPanel
    key={`${selectedEdge.id}-${actionSet.id}`}
    selectedEdge={selectedEdge}
    actionSet={actionSet}
    actionSetIndex={index}
    onClose={() => setSelectedEdge(null)}
    // ... other props
  />
))}
```

### Phase 4: Integration with Timer Actions

#### 4.1 Enhanced Timer Actions Hook

```typescript
// hooks/navigation/useTimerActions.ts (enhanced)

export const useTimerActions = ({
  currentNodeId,
  edges,
  nodes,
  onNavigateToNode
}: UseTimerActionsProps) => {
  
  const checkTimerActions = useCallback((nodeId: string) => {
    if (!nodeId) return;

    // Find all edges from this node
    const outgoingEdges = edges.filter(edge => edge.source === nodeId);

    outgoingEdges.forEach(edge => {
      const actionSets = edge.data?.action_sets || [];
      
      // Check each action set for timer actions
      actionSets.forEach((actionSet, index) => {
        if (actionSet.timer && actionSet.timer > 0) {
          const timerId = `${edge.id}-${actionSet.id}`;
          
          console.log(`[@useTimerActions] Setting timer for ${actionSet.timer}ms: ${actionSet.label}`);
          
          const timeoutId = setTimeout(() => {
            console.log(`[@useTimerActions] Timer fired! Auto-executing: ${actionSet.label}`);
            
            if (onNavigateToNode) {
              onNavigateToNode(edge.target);
            }
          }, actionSet.timer);

          activeTimersRef.current.set(timerId, timeoutId);
        }
      });
    });
  }, [edges, onNavigateToNode]);

  // ... rest of hook implementation
};
```

### Phase 5: Testing & Validation

#### 5.1 Migration Testing Checklist

- [ ] **Database Migration**
  - [ ] Run migration script on test data
  - [ ] Verify all existing edges converted properly
  - [ ] Test new edge creation with action_sets
  - [ ] Test legacy edge loading (backward compatibility)

- [ ] **Backend Testing**
  - [ ] Test edge CRUD operations with new structure
  - [ ] Test pathfinding with action set selection
  - [ ] Test NetworkX graph creation with action_sets
  - [ ] Test cross-tree navigation with new structure

- [ ] **Frontend Testing**
  - [ ] Test single action set display (legacy edges)
  - [ ] Test multiple action sets display (new edges)
  - [ ] Test panel positioning with multiple action sets
  - [ ] Test action set execution
  - [ ] Test timer actions integration

- [ ] **Integration Testing**
  - [ ] Test nested tree navigation with action sets
  - [ ] Test pathfinding across trees
  - [ ] Test cache invalidation with new structure
  - [ ] Test performance with large trees

#### 5.2 Performance Benchmarks

Before migration:
- Tree loading time: X ms
- Pathfinding time: X ms
- Memory usage: X MB

After migration:
- Tree loading time: X ms (target: ≤ current)
- Pathfinding time: X ms (target: ≤ current)
- Memory usage: X MB (target: ≤ 1.2x current)

### Phase 6: Rollout Strategy

#### 6.1 NO FEATURE FLAGS - DIRECT DEPLOYMENT

**This migration will be deployed directly without feature flags or gradual rollout. All systems must be migrated simultaneously.**

#### 6.2 Direct Deployment Strategy

1. **Pre-Migration**: Run data migration script to convert all edges
2. **Deployment Day**: Deploy all backend and frontend changes simultaneously
3. **Post-Migration**: Verify all systems working with new structure
4. **Immediate Cleanup**: Remove old database columns and legacy code

### Phase 7: MANDATORY CLEANUP - NO LEGACY CODE ALLOWED

#### 7.1 COMPLETE Legacy Code Removal (IMMEDIATE)

**ALL legacy code must be removed immediately after deployment:**

- ✅ **Database**: Drop legacy `actions` and `retry_actions` columns completely
- ✅ **Backend**: Remove ALL legacy code paths, fallbacks, and compatibility functions
- ✅ **Frontend**: Remove ALL legacy TypeScript interfaces and compatibility methods
- ✅ **Documentation**: Update ALL documentation to reflect new structure only
- ✅ **Migration Scripts**: Delete migration scripts after successful deployment

#### 7.2 Verification Checklist - NO BACKWARD COMPATIBILITY

**Mandatory verification that NO legacy code remains:**

- [ ] Search codebase for `actions` field references (must be 0)
- [ ] Search codebase for `retry_actions` field references (must be 0)
- [ ] Search codebase for legacy compatibility comments (must be 0)
- [ ] Search codebase for fallback logic (must be 0)
- [ ] Verify all edges have `action_sets` structure (must be 100%)
- [ ] Verify no old edge format can be loaded (must fail with error)

#### 7.3 Performance Optimization (NEW STRUCTURE ONLY)

- Add database indexes for action_sets queries
- Optimize NetworkX graph creation for action_sets
- Cache action set selections
- Implement action set preloading

## 🚨 FINAL WARNING: NO BACKWARD COMPATIBILITY

**This migration completely breaks backward compatibility. After deployment:**

- ❌ Old edge format will NOT work
- ❌ Legacy code will NOT exist
- ❌ Fallback mechanisms will NOT be available
- ❌ Old data format will NOT be supported

**All systems must be migrated simultaneously. There is no rollback to old format.**

## Success Metrics

- **Functionality**: All existing navigation flows work unchanged
- **Performance**: No degradation in tree loading or pathfinding speed
- **User Experience**: Multiple action options visible and testable
- **Developer Experience**: Easier to add new navigation alternatives
- **System Reliability**: No increase in error rates

## 🚨 NO ROLLBACK PLAN - FORWARD ONLY

**There is NO rollback plan. This migration is irreversible.**

If critical issues arise:
1. **Fix forward** - patch the new implementation immediately
2. **No rollback** - old format will not be supported
3. **Emergency patches** - must work with action_sets structure only
4. **Database backup** - only for disaster recovery, not format rollback

## Timeline

- **Phase 1-2 (Backend)**: 2 weeks
- **Phase 3 (Frontend)**: 1 week  
- **Phase 4 (Timer Integration)**: 1 week
- **Phase 5 (Testing)**: 1 week
- **Phase 6 (Rollout)**: 2 weeks
- **Phase 7 (Cleanup)**: 1 week

**Total Estimated Time**: 8 weeks