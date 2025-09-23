# Navigation Architecture Refactor Plan

## Goal: Single Public Interface

**Current Problem**: Multiple levels of navigation access confuse users
**Solution**: Hide all complexity, expose only `navigate_to()` and `validate_all_transitions()`

## Public Interface (User-Facing)

```python
# For all navigation scripts
result = navigate_to(target_node) -> NavigationResult

# For validation scripts  
result = validate_all_transitions(max_iterations=None) -> ValidationResult
```

## Files to Modify

### 1. **shared/src/lib/executors/script_decorators.py** - Public Interface
**Changes:**
- ✅ Keep: `navigate_to(target_node)` 
- ✅ Add: `validate_all_transitions(max_iterations=None)`
- ❌ Remove: `ensure_navigation_tree_loaded()` (make private)
- ❌ Remove: `get_context()`, `get_executor()` (make private)
- ✅ Keep: `get_device()`, `is_mobile_device()`, `get_args()` (useful helpers)

### 2. **shared/src/lib/executors/_private_navigation.py** - NEW Private Module
**Purpose:** Hide all low-level navigation functions
**Contains:**
- `_ensure_navigation_tree_loaded()`
- `_get_context()`, `_get_executor()`  
- `_find_optimal_edge_validation_sequence()`
- All pathfinding and cache functions

### 3. **shared/src/lib/executors/navigation_result.py** - NEW Result Classes
**Purpose:** Rich result objects with all data users need
```python
@dataclass
class NavigationResult:
    success: bool
    target_reached: str
    path_taken: List[str]
    timing: Dict[str, float]
    screenshots: List[str]
    verifications: List[Dict]
    error: Optional[str] = None

@dataclass  
class ValidationResult:
    success: bool
    total_transitions: int
    successful_transitions: int
    failed_transitions: int
    coverage_percentage: float
    timing: Dict[str, float]
    screenshots: List[str]
    detailed_results: List[Dict]
    error: Optional[str] = None
```

### 4. **test_scripts/validation.py** - Simplified Validation
**Before:** 700+ lines of complex logic
**After:** ~50 lines using public interface
```python
@script("validation", "Validate navigation tree transitions")
def main():
    args = get_args()
    result = validate_all_transitions(max_iterations=args.max_iteration)
    
    # All data available in result object
    print(f"Coverage: {result.coverage_percentage}%")
    print(f"Success: {result.successful_transitions}/{result.total_transitions}")
    
    return result.success
```

### 5. **backend_host/src/services/navigation/** - Make Private
**Changes:**
- Move public functions to private module
- Keep only internal implementation
- No direct imports allowed from scripts

## Implementation Steps

### Step 1: Create Private Module
```bash
# Create new private module
touch shared/src/lib/executors/_private_navigation.py
```

### Step 2: Create Result Classes  
```bash
# Create result classes
touch shared/src/lib/executors/navigation_result.py
```

### Step 3: Move Functions to Private
- Move `ensure_navigation_tree_loaded()` → `_private_navigation.py`
- Move `get_context()`, `get_executor()` → `_private_navigation.py`
- Add validation planning logic to private module

### Step 4: Implement Public Interface
- Enhance `navigate_to()` to return rich `NavigationResult`
- Add `validate_all_transitions()` that returns `ValidationResult`
- Both functions handle all complexity internally

### Step 5: Refactor Scripts
- **validation.py**: Use `validate_all_transitions()` instead of complex logic
- **goto.py**, **goto_live.py**: Already use `navigate_to()` ✅
- **fullzap.py**: Already uses `navigate_to()` ✅

### Step 6: Remove Legacy Imports
- Block direct imports from `backend_host/src/services/navigation/`
- Block direct imports from cache modules
- Only allow imports from `script_decorators.py`

## New Script Structure

### Simple Navigation Script
```python
from shared.src.lib.executors.script_decorators import script, navigate_to

@script("goto", "Navigate to specified node")
def main():
    args = get_args()
    result = navigate_to(args.node)
    
    # Rich data available
    print(f"Path: {' → '.join(result.path_taken)}")
    print(f"Time: {result.timing['total_ms']}ms")
    print(f"Screenshots: {len(result.screenshots)}")
    
    return result.success
```

### Simple Validation Script
```python
from shared.src.lib.executors.script_decorators import script, validate_all_transitions

@script("validation", "Validate navigation tree")  
def main():
    args = get_args()
    result = validate_all_transitions(max_iterations=args.max_iteration)
    
    # Rich validation data available
    print(f"Coverage: {result.coverage_percentage}%")
    print(f"Failed: {result.failed_transitions}")
    
    return result.success
```

## Benefits

### ✅ For Users
- **Single Interface**: Only `navigate_to()` and `validate_all_transitions()`
- **Rich Data**: All timing, screenshots, paths in result objects
- **No Complexity**: No tree loading, cache management, context setup
- **Consistent**: Same interface for all navigation needs

### ✅ For System
- **Clean Separation**: Public vs private clearly defined
- **No Legacy**: Remove all complex exposed functions
- **Maintainable**: Changes to algorithms don't affect user scripts
- **Extensible**: Can add new navigation features without breaking scripts

## Migration Guide

### Current validation.py (700+ lines)
```python
# Complex setup
ensure_navigation_tree_loaded()
context = get_context()
unified_graph = get_cached_unified_graph(context.tree_id, context.team_id)
validation_sequence = find_optimal_edge_validation_sequence(context.tree_id, context.team_id)
# ... 600 more lines of complexity
```

### New validation.py (~50 lines)
```python
# Simple interface
result = validate_all_transitions(max_iterations=args.max_iteration)
print(f"Coverage: {result.coverage_percentage}%")
return result.success
```

**Reduction: 700+ lines → ~50 lines (93% reduction!)**

## File Structure After Refactor

```
shared/src/lib/executors/
├── script_decorators.py          # PUBLIC: navigate_to(), validate_all_transitions()
├── navigation_result.py          # PUBLIC: Result classes
├── _private_navigation.py        # PRIVATE: All complex logic
├── script_executor.py           # INTERNAL: Framework implementation
└── step_executor.py             # INTERNAL: Step recording

test_scripts/
├── goto.py                      # ✅ Already clean (uses navigate_to)
├── goto_live.py                 # ✅ Already clean (uses navigate_to)  
├── fullzap.py                   # ✅ Already clean (uses navigate_to)
├── validation.py                # 🔄 REFACTOR: Use validate_all_transitions()
└── ai_testcase_executor.py      # ✅ Already clean

backend_host/src/services/navigation/  # 🔒 PRIVATE: No direct access from scripts
```

## Import Rules After Refactor

### ✅ Allowed in Scripts
```python
from shared.src.lib.executors.script_decorators import script, navigate_to, validate_all_transitions
```

### ❌ Forbidden in Scripts  
```python
# These become private - scripts cannot import
from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
from backend_host.src.lib.utils.navigation_cache import get_cached_unified_graph
from shared.src.lib.executors.script_executor import ScriptExecutor, ScriptExecutionContext
```

## Success Metrics

- **User Complexity**: 90%+ reduction in script complexity
- **Public Interface**: Only 2 functions exposed (`navigate_to`, `validate_all_transitions`)
- **Legacy Code**: 0% - complete removal of complex exposed functions
- **Script Length**: validation.py: 700+ lines → ~50 lines
- **Import Statements**: Scripts need only 1 import line

This refactor achieves your goal: **Users only see `navigate_to()`, all complexity is hidden.**
