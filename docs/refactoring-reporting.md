# Migration Plan: Simple Step Recording System

## Current Issue Analysis

### Problem
Steps are recorded during analysis phase, not execution phase, causing incorrect ordering in reports.

### Symptom
Navigation steps (16:37:42) appear before zap actions (16:37:11) in reports despite happening after.

### Root Cause
Complex hierarchical context system records steps when they're processed/analyzed, not when they're actually executed.

### Example of Wrong Order
```
1.1.1.1.1 Navigation step 1: live_fullscreen → live_fullscreen_audiomenu (16:37:42-16:37:50)
1.1.1.1.2 Navigation step 1: live_fullscreen_audiomenu → live_fullscreen (16:37:54-16:37:59)  
1.1.1.1.3 Zap iteration 1: live_fullscreen_chup (16:37:11-16:37:23) ← Should be first!
1.1.1.2.1 Zap iteration 2: live_fullscreen_chup (16:38:07-16:38:18)
```

## Migration Plan

### Phase 1: Simplify Step Recording (Core Fix)

#### 1.1 Remove Hierarchical Context System
**Files to modify:**
- `shared/lib/utils/script_framework.py`

**Remove from ScriptExecutionContext:**
```python
# DELETE these attributes:
- self.execution_context_stack: List[ExecutionContext] = []
- self.root_context = ExecutionContext("Script Execution")
- self.current_context = self.root_context

# DELETE these methods:
- push_context(self, name: str) -> ExecutionContext
- pop_context(self) -> ExecutionContext  
- record_step_in_context(self, step_data: Dict[str, Any])
- _get_context_path(self) -> str
```

**Remove ExecutionContext class entirely:**
```python
# DELETE entire class:
class ExecutionContext:
    # ... entire class
```

#### 1.2 Implement Simple Sequential Recording
**Add to ScriptExecutionContext:**
```python
class ScriptExecutionContext:
    def __init__(self, script_name: str):
        # ... existing attributes ...
        self.step_counter = 0  # Simple sequential counter
    
    def record_step(self, step_data: Dict[str, Any]):
        """Record step immediately when it happens - no hierarchy"""
        self.step_counter += 1
        step_data['step_number'] = self.step_counter
        step_data['execution_timestamp'] = time.time()
        self.step_results.append(step_data)
```

### Phase 2: Fix ZapController Recording

#### 2.1 Record Zap Action Immediately
**File:** `shared/lib/utils/zap_controller.py`

**Current Problem:**
```python
# WRONG: Record step during analysis phase
def _execute_single_zap(self):
    # Execute action
    action_result = execute_edge_actions(...)
    
    # Wait and do analysis
    time.sleep(8)
    analysis_result = self.analyze_after_zap(...)
    
    # Record step AFTER analysis (wrong timing)
    self._record_step_result_hierarchical(...)
```

**Solution:**
```python
def _execute_single_zap(self, context, action_edge, action_command, iteration, max_iterations):
    print(f"🎬 [ZapController] Iteration {iteration}/{max_iterations}: {action_command}")
    
    # RECORD ZAP STEP IMMEDIATELY when it executes
    start_time = time.time()
    action_result = execute_edge_actions(context.host, context.selected_device, action_edge, team_id=context.team_id)
    end_time = time.time()
    execution_time = int((end_time - start_time) * 1000)
    
    # Record main zap step NOW (not during analysis)
    zap_step = {
        'success': action_result.get('success', False),
        'message': f"Zap iteration {iteration}: {action_command} ({iteration}/{max_iterations})",
        'execution_time_ms': execution_time,
        'start_time': datetime.fromtimestamp(start_time).strftime('%H:%M:%S'),
        'end_time': datetime.fromtimestamp(end_time).strftime('%H:%M:%S'),
        'step_category': 'zap_action',
        'action_name': action_command,
        'iteration': iteration,
        'max_iterations': max_iterations
    }
    context.record_step(zap_step)
    
    # THEN do analysis (which records its own sub-steps)
    time.sleep(8)  # Wait for banner to disappear
    analysis_result = self.analyze_after_zap(iteration, action_command, context)
    
    return action_result.get('success', False)
```

#### 2.2 Remove Context Management from ZapController
**Remove from execute_zap_iterations:**
```python
# DELETE:
iteration_context = context.push_context(f"Zap iteration {iteration}")
try:
    # ...
finally:
    context.pop_context()
```

**Simplified version:**
```python
def execute_zap_iterations(self, context, action_edge, action_command, max_iterations, blackscreen_area=None, goto_live=True):
    print(f"🔄 [ZapController] Starting {max_iterations} iterations of '{action_command}'...")
    
    self.statistics = ZapStatistics()
    self.statistics.total_iterations = max_iterations
    self.blackscreen_area = blackscreen_area
    self.goto_live = goto_live
    
    # Simple loop - no context management
    for iteration in range(1, max_iterations + 1):
        success = self._execute_single_zap(context, action_edge, action_command, iteration, max_iterations)
        if success:
            self.statistics.successful_iterations += 1
    
    return self.statistics.successful_iterations == max_iterations
```

### Phase 3: Fix Navigation Utils Recording

#### 3.1 Record Navigation Steps When They Execute
**File:** `shared/lib/utils/navigation_utils.py`

**In goto_node function:**
```python
def goto_node(host, device, target_node_label, tree_id, team_id, context=None):
    # ... pathfinding logic ...
    
    for i, step in enumerate(navigation_path):
        step_num = i + 1
        from_node = step.get('from_node_label', 'unknown')
        to_node = step.get('to_node_label', 'unknown')
        
        # RECORD STEP IMMEDIATELY when navigation executes
        step_start_time = time.time()
        result = execute_navigation_with_verifications(...)
        step_end_time = time.time()
        
        # Record navigation step immediately
        if context:
            step_result = {
                'success': result.get('success', False),
                'message': f"Navigation step {step_num}: {from_node} → {to_node}",
                'execution_time_ms': int((step_end_time - step_start_time) * 1000),
                'start_time': datetime.fromtimestamp(step_start_time).strftime('%H:%M:%S'),
                'end_time': datetime.fromtimestamp(step_end_time).strftime('%H:%M:%S'),
                'step_category': 'navigation',
                'from_node': from_node,
                'to_node': to_node
            }
            context.record_step(step_result)
```

### Phase 4: Clean Up Script Files

#### 4.1 Remove Context Management from Scripts
**Files:**
- `test_scripts/fullzap.py`
- `test_scripts/validation.py`

**Remove all push_context/pop_context calls:**
```python
# DELETE from fullzap.py:
zap_actions_context = context.push_context("Zap Actions")
nav_context = context.push_context("Navigation to Live") 
context.pop_context()

# DELETE from validation.py:
validation_context = context.push_context("Validation Sequence")
step_context = context.push_context(f"Validation step {step_num}")
context.pop_context()
```

#### 4.2 Update Step Recording Calls
**Replace all instances:**
```python
# REPLACE:
context.record_step_in_context(step_result)

# WITH:
context.record_step(step_result)
```

### Phase 5: Simplify Report Generation

#### 5.1 Remove Hierarchical Display Logic
**File:** `shared/lib/utils/script_framework.py`

**Remove from print_execution_summary:**
```python
# DELETE:
if hasattr(context, 'root_context') and context.root_context.children:
    print(f"\n📋 Execution Structure:")
    self._print_hierarchical_structure(context.root_context, 0)

# DELETE entire method:
def _print_hierarchical_structure(self, exec_context: ExecutionContext, indent: int):
    # ... entire method
```

#### 5.2 Add Simple Step List Display
**Add to print_execution_summary:**
```python
def print_execution_summary(self, context: ScriptExecutionContext, userinterface_name: str):
    # ... existing summary info ...
    
    # Show simple step list in execution order
    if context.step_results:
        print(f"\n📋 Execution Steps:")
        for step in context.step_results:
            status = "✅" if step.get('success', False) else "❌"
            step_time = step.get('execution_time_ms', 0)
            duration = f" ({step_time}ms)" if step_time > 0 else ""
            print(f"  {step.get('step_number', '?')}. {status} {step.get('message', 'Unknown step')}{duration}")
```

## Expected Results

### Before (Wrong Order)
```
1.1.1.1.1 PASS Navigation step 1: live_fullscreen → live_fullscreen_audiomenu (16:37:42)
1.1.1.1.2 PASS Navigation step 1: live_fullscreen_audiomenu → live_fullscreen (16:37:54)  
1.1.1.1.3 PASS Zap iteration 1: live_fullscreen_chup (16:37:11) ← Wrong position!
1.1.1.2.1 PASS Zap iteration 2: live_fullscreen_chup (16:38:07)
```

### After (Correct Order)
```
1. PASS Navigation to live_fullscreen (16:37:05-16:37:10)
2. PASS Zap iteration 1: live_fullscreen_chup (16:37:11-16:37:23)
3. PASS Navigation step: live_fullscreen → live_fullscreen_audiomenu (16:37:42-16:37:50)
4. PASS Navigation step: live_fullscreen_audiomenu → live_fullscreen (16:37:54-16:37:59)
5. PASS Zap iteration 2: live_fullscreen_chup (16:38:07-16:38:18)
```

## Benefits of This Approach

1. **Correct Execution Order**: Steps recorded when they actually execute
2. **Simple Sequential Numbering**: 1, 2, 3, 4... (no complex hierarchy)
3. **No Legacy Code**: Complete removal of hierarchical context system
4. **Minimal Changes**: Most code changes are deletions
5. **Easy to Debug**: Simple linear step recording
6. **Performance**: No context management overhead

## Files to Modify

1. `shared/lib/utils/script_framework.py` - Remove hierarchical system, add simple recording
2. `shared/lib/utils/zap_controller.py` - Record steps immediately during execution
3. `shared/lib/utils/navigation_utils.py` - Record navigation steps when they execute
4. `test_scripts/fullzap.py` - Remove context management
5. `test_scripts/validation.py` - Remove context management

## Migration Strategy

1. **Start with script_framework.py** - implement simple recording system
2. **Update ZapController** - record zap steps immediately
3. **Update navigation_utils** - record navigation steps immediately  
4. **Clean up scripts** - remove context management calls
5. **Test with fullzap.py** - verify correct step ordering
6. **Verify all scripts work** - validation.py, goto_live.py, etc.

This migration completely eliminates the over-engineered hierarchical system and replaces it with simple, immediate step recording that preserves execution order.
