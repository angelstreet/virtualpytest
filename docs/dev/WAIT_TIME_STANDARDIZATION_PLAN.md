# Wait Time Standardization Plan

## Overview
This plan standardizes naming conventions for wait time parameters across the VirtualPyTest codebase:
- **Action-level**: `params.wait_time` (instead of `waitTime`)
- **Edge-level**: `final_wait_time` (instead of `finalWaitTime`)

## Current Problem
- Actions are saved with `params.wait_time` in database
- Navigation cache creates `waitTime` property, losing original `params.wait_time`
- Frontend looks for `params.wait_time` but finds `waitTime`, shows default values
- Edge-level uses `finalWaitTime` but docs specify `final_wait_time`

## Execution Order

### Phase 1: Fix Action-Level Wait Time (CRITICAL - Fixes Immediate Issue)

#### Backend Changes

**1. `shared/lib/supabase/navigation_trees_db.py` ⚠️ CRITICAL**
```python
# REMOVE these lines (681, 691):
action['waitTime'] = action.get('params', {}).get('wait_time', 500)

# KEEP original params.wait_time in resolved actions
# Actions should maintain their original params structure
```

**2. `backend_server/src/routes/server_actions_routes.py` ⚠️ CRITICAL**
```python
# Line 112: Change from:
'wait_time': action.get('waitTime', 0),

# To:
'wait_time': action.get('params', {}).get('wait_time', 0),
```

#### Frontend Changes

**3. `frontend/src/types/controller/Action_Types.ts`**
```typescript
// Line 71: Remove this property:
waitTime?: number; // Optional: wait time after execution

// Line 162: Change from:
waitTime: number; // Required field to match Navigation_Types expectation

// To: Use params.wait_time instead of separate waitTime property
```

**4. `frontend/src/components/navigation/Navigation_EdgeEditDialog.tsx`**
```typescript
// Lines 226, 282: Change from:
waitTime: 500,

// To:
params: { wait_time: 500 },
```

### Phase 2: Database JSON Fix

**Export and Update Navigation Tree JSON:**
1. Export navigation tree from database
2. Remove all `waitTime` properties from action objects
3. Ensure all actions only have `params.wait_time`
4. Change all `finalWaitTime` → `final_wait_time` in edge data
5. Re-import to database

### Phase 3: Fix Edge-Level Wait Time (Complete Standardization)

#### Backend Changes

**5. `shared/lib/utils/navigation_graph.py`**
```python
# Line 138: Change from:
'finalWaitTime': edge_data.get('finalWaitTime', 2000),

# To:
'final_wait_time': edge_data.get('final_wait_time', 2000),
```

**6. `backend_core/src/services/navigation/navigation_pathfinding.py`**
```python
# Lines 181, 309, 632: Change from:
'finalWaitTime': edge_data.get('finalWaitTime', 2000),

# To:
'final_wait_time': edge_data.get('final_wait_time', 2000),
```

#### Frontend Changes

**7. `frontend/src/types/pages/Navigation_Types.ts`**
```typescript
// Lines 65, 126, 148, 410: Change from:
finalWaitTime?: number; // Wait time after all actions
finalWaitTime: number;

// To:
final_wait_time?: number; // Wait time after all actions
final_wait_time: number;

// Line 413: Change parameter name:
onFinalWaitTimeChange: (waitTime: number) => void;
// To:
onFinalWaitTimeChange: (final_wait_time: number) => void;
```

**8. `frontend/src/hooks/navigation/useNavigationEditor.ts`**
```typescript
// Lines 293, 401, 413: Change from:
finalWaitTime: edgeForm?.finalWaitTime,
finalWaitTime: edgeForm.finalWaitTime,
finalWaitTime: updatedEdge.finalWaitTime,

// To:
final_wait_time: edgeForm?.final_wait_time,
final_wait_time: edgeForm.final_wait_time,
final_wait_time: updatedEdge.final_wait_time,
```

**9. `frontend/src/hooks/navigation/useEdge.ts`**
```typescript
// Line 221: Change from:
finalWaitTime: edge.data?.finalWaitTime ?? 2000,

// To:
final_wait_time: edge.data?.final_wait_time ?? 2000,
```

**10. `frontend/src/utils/navigation/navigationUtils.ts`**
```typescript
// Lines 203-204: Change from:
finalWaitTime:
  edge.finalWaitTime !== undefined ? edge.finalWaitTime : edge.data?.finalWaitTime,

// To:
final_wait_time:
  edge.final_wait_time !== undefined ? edge.final_wait_time : edge.data?.final_wait_time,
```

**11. `frontend/src/contexts/navigation/NavigationContext.tsx`**
```typescript
// Lines 227, 491, 527, 565: Change from:
finalWaitTime: 2000,
finalWaitTime: edge.data?.finalWaitTime || 2000,

// To:
final_wait_time: 2000,
final_wait_time: edge.data?.final_wait_time || 2000,
```

**12. `frontend/src/contexts/navigation/NavigationConfigContext.tsx`**
```typescript
// Lines 377-378: Change from:
finalWaitTime:
  edge.finalWaitTime !== undefined ? edge.finalWaitTime : edge.data?.finalWaitTime,

// To:
final_wait_time:
  edge.final_wait_time !== undefined ? edge.final_wait_time : edge.data?.final_wait_time,
```

## Validation Steps

### After Phase 1:
1. Test action editing - wait_time values should persist after save
2. Verify actions execute with correct wait_time from params
3. Check that ActionItem.tsx shows updated values

### After Phase 2:
1. Verify navigation tree loads correctly from updated JSON
2. Test edge editing and action execution
3. Confirm database consistency

### After Phase 3:
1. Test edge-level wait time functionality
2. Verify all references use final_wait_time consistently
3. Run full navigation and action execution tests

## Files Changed Summary

### Phase 1 (Action-level - CRITICAL):
- `shared/lib/supabase/navigation_trees_db.py`
- `backend_server/src/routes/server_actions_routes.py`
- `frontend/src/types/controller/Action_Types.ts`
- `frontend/src/components/navigation/Navigation_EdgeEditDialog.tsx`

### Phase 2 (Database):
- Navigation tree JSON export/import

### Phase 3 (Edge-level):
- `shared/lib/utils/navigation_graph.py`
- `backend_core/src/services/navigation/navigation_pathfinding.py`
- 6 frontend files (types, hooks, contexts, utils)

## Expected Outcome

After completion:
- All action wait times use consistent `params.wait_time` naming
- All edge wait times use consistent `final_wait_time` naming
- Frontend displays actual database values instead of defaults
- No more naming confusion between waitTime/wait_time/finalWaitTime/final_wait_time
- Aligned with documentation standards in GLOBAL_NAMING_CONVENTION.md 