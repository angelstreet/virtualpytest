# Failure Action Implementation Plan

## Overview
Implement `failure_action` functionality for edge actions, providing a final cleanup/reset mechanism when both main actions and retry actions fail. This feature follows the exact same pattern as `retry_action` but executes as the final step in the failure chain.

## Execution Flow
```
Main Actions → Retry Actions → Failure Actions
     ↓              ↓              ↓
   Success      (if main fails)  (if retry fails)
     ✓              ↓              ↓
   Return         Success       Success/Fail
                     ✓              ✓
                   Return         Return
```

## Implementation Checklist

### 🗄️ Database Schema Updates
- [ ] **File**: `setup/db/schema/002_ui_navigation_tables.sql`
  - [ ] Update action set structure documentation (lines 76-80)
  - [ ] Add `failure_actions` to the JSON structure example

- [ ] **File**: `setup/db/schema/005_monitoring_analytics.sql`  
  - [ ] Add `failure_action_count` column to `edge_metrics` table (after line 97)
  - [ ] Add `is_failure_action` column to `action_execution_history` table (after line 136)
  - [ ] Update trigger functions to handle failure action metrics (lines 366-384)

### 🔧 Backend Core Implementation

#### Action Execution Logic
- [ ] **File**: `shared/lib/utils/action_utils.py`
  - [ ] Line 332: Add `failure_actions = action_set.get('failure_actions', [])`
  - [ ] Line 335: Update print statement to include failure actions count
  - [ ] Line 349: Add `valid_failure_actions = [a for a in failure_actions if a.get('command')]`
  - [ ] After line 456: Add failure action execution logic block
  - [ ] Update success calculation to consider failure actions

- [ ] **File**: `backend_core/src/services/actions/action_executor.py`
  - [ ] Line 49: Add `failure_actions: Optional[List[Dict[str, Any]]] = None` parameter
  - [ ] After line 125: Add failure action execution logic
  - [ ] Lines 126-131: Update overall success calculation logic
  - [ ] Add failure action validation in `_validate_actions` method

- [ ] **File**: `backend_core/src/controllers/base_controller.py`
  - [ ] Line 44: Add `failure_actions: List[Dict[str, Any]]` parameter
  - [ ] After line 114: Add failure action execution block
  - [ ] Update return logic to handle failure action results

#### Database Recording & Metrics
- [ ] **File**: `shared/lib/supabase/execution_results_db.py`
  - [ ] Line 233: Add `is_failure_action: bool` parameter
  - [ ] Line 253: Add `'is_failure_action': is_failure_action` to record
  - [ ] Line 510: Add `failure_actions: List[Dict] = None` parameter
  - [ ] Lines 523-536: Add failure action processing loop
  - [ ] Update metrics calculation to include failure action count

#### Utility Functions
- [ ] **File**: `shared/lib/utils/navigation_utils.py`
  - [ ] Line 588: Add failure_actions_count to error details check
  - [ ] Line 589: Add failure actions reporting to print statement

- [ ] **File**: `shared/lib/utils/report_utils.py`
  - [ ] After line 129: Add failure action reporting section
  - [ ] Create failure action loop similar to retry action loop (lines 124-129)

- [ ] **File**: `shared/lib/utils/zap_controller.py`
  - [ ] Line 341: Update `_extract_edge_actions` return to include failure actions
  - [ ] Line 359: Add `'failureActions': real_failure_actions` to result
  - [ ] Line 372: Initialize `real_failure_actions = []`
  - [ ] Line 383: Add `real_failure_actions = default_action_set.get('failure_actions', [])`
  - [ ] Line 385: Update return statement to include failure actions

- [ ] **File**: `shared/lib/utils/navigation_graph.py`
  - [ ] Line 105: Add `failure_actions_list = default_set.get('failure_actions', [])`
  - [ ] Line 134: Add failure actions to debug print statement
  - [ ] Line 300: Add `'failure_actions': []` to default structure
  - [ ] Line 318: Add `'failure_actions': []` to default structure

### 🎨 Frontend Implementation

#### Type Definitions
- [ ] **File**: `frontend/src/types/pages/Navigation_Types.ts`
  - [ ] Line 15: Add `failure_actions?: Action[];` to ActionSet interface
  - [ ] Line 258: Add `total_failure_actions?: number;` to metrics interface

#### React Hooks
- [ ] **File**: `frontend/src/hooks/actions/useAction.ts`
  - [ ] Line 109: Add `failure_actions: validFailureActions,` field
  - [ ] Add failure action validation logic similar to retry actions

- [ ] **File**: `frontend/src/hooks/navigation/useEdge.ts`
  - [ ] Line 101: Add failure actions mapping alongside retry actions
  - [ ] Line 162: Add `failureActions` variable similar to `retryActions`

- [ ] **File**: `frontend/src/hooks/navigation/useNavigationEditor.ts`
  - [ ] Line 137: Add `failure_actions: [],` to default structure
  - [ ] Line 394: Add `failure_actions: [],` to default structure

- [ ] **File**: `frontend/src/hooks/navigation/useEdgeEdit.ts`
  - [ ] Add failure action handling in edge edit operations
  - [ ] Add validation for failure actions

#### React Components
- [ ] **File**: `frontend/src/components/navigation/Navigation_EdgeEditDialog.tsx`
  - [ ] Line 144: Add `failure_actions: edgeEdit.localFailureActions,` field
  - [ ] Add failure action UI elements similar to retry actions

- [ ] **File**: `frontend/src/components/navigation/Navigation_EdgeSelectionPanel.tsx`
  - [ ] Line 75: Add `failureActions` variable similar to `retryActions`
  - [ ] Add failure action display in UI

#### Context & State Management
- [ ] **File**: `frontend/src/contexts/navigation/NavigationContext.tsx`
  - [ ] Line 1153: Add `failure_actions: failureActions,` field
  - [ ] Add failure action state management

### 📊 Monitoring & Analytics
- [ ] **File**: `docs/architecture/navigation_metrics.md`
  - [ ] Line 61: Add `failure_action_count` to metrics documentation
  - [ ] Line 93: Add `is_failure_action` to execution history documentation
  - [ ] Line 201: Update function signature to include failure_actions

### 🧪 Testing & Validation
- [ ] Create test cases for failure action execution
- [ ] Validate failure actions execute only after retry actions fail
- [ ] Test failure action metrics recording
- [ ] Verify UI displays failure actions correctly
- [ ] Test database schema updates

## Implementation Notes

### Execution Logic
```python
# Execution order in action_utils.py
1. Execute main actions
2. If main actions fail AND retry_actions exist:
   - Execute retry actions
3. If retry actions fail AND failure_actions exist:
   - Execute failure actions
4. Calculate overall success based on final state
```

### Database Structure
```json
{
  "id": "action_set_1",
  "label": "Navigate to Settings",
  "actions": [...],
  "retry_actions": [...],
  "failure_actions": [...],  // ← NEW FIELD
  "priority": 1
}
```

### Success Calculation
```python
# Overall success logic
if main_actions_failed:
    if retry_actions_exist and retry_actions_failed:
        if failure_actions_exist:
            overall_success = failure_actions_success
        else:
            overall_success = False
    else:
        overall_success = retry_actions_success
else:
    overall_success = True
```

## Completion Criteria
- [ ] All database schema updates applied
- [ ] Backend execution logic handles failure actions
- [ ] Frontend UI supports failure action configuration
- [ ] Metrics and monitoring include failure actions
- [ ] Documentation updated
- [ ] Tests pass for all failure action scenarios

## Risk Assessment
- **Low Risk**: Following exact same pattern as retry_actions
- **No Legacy Impact**: Clean implementation without backward compatibility
- **Database Impact**: Additive changes only, no breaking changes

---

**Status**: 🔄 In Progress  
**Estimated Completion**: TBD  
**Last Updated**: $(date)