# Script Steps Refactoring Plan - SIMPLIFIED

## 🎯 **Goal: Clean Step Architecture - Minimal Files, Maximum Impact**

Refactor all test scripts to use a unified, clean step architecture that preserves exact reporting functionality while eliminating duplicate code and inconsistencies. **KEEP IT SIMPLE** - minimal file creation, minimal code changes.

## 📋 **Current State Analysis**

### **Current Problems:**
- **4 different step recording patterns** across scripts
- **ZapController** creates steps directly (violates separation of concerns)
- **NavigationExecutor** vs **script_utils** duplicate navigation logic (already fixed)
- **Mixed responsibilities** - executors both execute AND record steps
- **Inconsistent step data structures** across scripts

### **Current Reporting Requirements (MUST PRESERVE EXACTLY):**
- **goto_live.py**: Simple navigation summary
- **goto.py**: Simple navigation summary  
- **validation.py**: Complex validation summary with recovery stats, verification counts
- **fullzap.py**: Complex zap summary + database table + rich HTML reports with analysis

## 🏗️ **Simplified Architecture**

### **Core Principle: Single Responsibility + Minimal Changes**
- **Executors**: Execute actions, return standardized results (lightweight wrapper)
- **Scripts**: Orchestrate steps, manage screenshots, handle reporting (enhanced existing)
- **Steps**: Simple data containers (just dict with helper methods)

## 📁 **Files to Create/Edit - MINIMAL APPROACH**

### **1. Only 2 New Files Needed**
```
shared/src/lib/executors/
├── script_executor.py     # Enhanced (existing file - add step methods)
└── step_executor.py       # New simple wrapper (lightweight)
```

### **2. Update Existing Controllers (Minimal Changes)**
```
backend_host/src/lib/utils/
└── zap_controller.py      # Remove step recording, return data only
```

### **3. Update Existing Scripts (Minimal Changes)**
```
test_scripts/
├── fullzap.py            # Use StepExecutor wrapper
├── goto_live.py          # Use StepExecutor wrapper
├── goto.py              # Use StepExecutor wrapper  
└── validation.py        # Use StepExecutor wrapper
```

### **4. No New Reporting System Needed**
- Reuse existing reporting code
- Steps convert to existing dict format
- Zero breaking changes to reports

## 🔧 **Required Executor Modifications**

### **Current State Analysis:**
- **ActionExecutor**: Already returns standardized dict with `success`, `execution_time_ms`, `action_screenshots`, etc. ✅
- **NavigationExecutor**: Already returns standardized dict with `success`, `execution_time`, `transitions_executed`, etc. ✅  
- **VerificationExecutor**: Already returns standardized dict with `success`, `passed_count`, `results`, etc. ✅

### **Required Changes to Executors:**

#### **1. ActionExecutor (backend_host/src/services/actions/action_executor.py)**
**Status**: ✅ **NO CHANGES NEEDED** - Already returns standardized format
```python
# Current return format is already perfect:
return {
    'success': bool,
    'execution_time_ms': int,
    'action_screenshots': list,  # Already includes all screenshots
    'passed_count': int,
    'total_count': int,
    'error': str,
    'results': list
}
```

#### **2. NavigationExecutor (backend_host/src/services/navigation/navigation_executor.py)**
**Status**: ✅ **NO CHANGES NEEDED** - Already returns standardized format
```python
# Current return format is already perfect:
return {
    'success': bool,
    'execution_time': float,
    'transitions_executed': int,
    'actions_executed': int,
    'total_transitions': int,
    'total_actions': int,
    'error': str
}
```

#### **3. VerificationExecutor (backend_host/src/services/verifications/verification_executor.py)**
**Status**: ✅ **NO CHANGES NEEDED** - Already returns standardized format
```python
# Current return format is already perfect:
return {
    'success': bool,
    'passed_count': int,
    'total_count': int,
    'results': list,
    'error': str
}
```

### **Key Insight: Executors Are Already Standardized!**
All three executors already return consistent, standardized dictionary formats. The StepExecutor wrapper will simply convert these existing formats to step dictionaries without requiring any executor changes.

## 🔄 **Simplified Migration Steps**

### **Phase 1: Create Simple StepExecutor Wrapper**

#### **Step 1.1: Create StepExecutor** 
**File**: `shared/src/lib/executors/step_executor.py` (NEW - 50 lines max)
```python
"""
Simple Step Executor Wrapper
Lightweight wrapper that standardizes step creation without changing existing executors.
"""

class StepExecutor:
    """Simple wrapper that creates standardized steps from existing executor results"""
    
    def __init__(self, context):
        self.context = context
    
    def create_navigation_step(self, nav_result: dict, from_node: str, to_node: str) -> dict:
        """Convert NavigationExecutor result to standardized step dict"""
        return {
            'success': nav_result.get('success', False),
            'from_node': from_node,
            'to_node': to_node,
            'execution_time_ms': nav_result.get('execution_time', 0) * 1000,
            'transitions_executed': nav_result.get('transitions_executed', 0),
            'actions_executed': nav_result.get('actions_executed', 0),
            'step_category': 'navigation',
            'error': nav_result.get('error'),
            'screenshots': []  # Populated by script
        }
    
    def create_zap_step(self, iteration: int, action_command: str, analysis_result: dict) -> dict:
        """Convert ZapController analysis to standardized step dict"""
        return {
            'success': analysis_result.get('success', False),
            'iteration': iteration,
            'action_command': action_command,
            'from_node': 'live',
            'to_node': 'live',
            'step_category': 'zap_action',
            'motion_analysis': analysis_result.get('motion_details', {}),
            'subtitle_analysis': analysis_result.get('subtitle_details', {}),
            'audio_analysis': analysis_result.get('audio_details', {}),
            'zapping_analysis': analysis_result.get('zapping_details', {}),
            'error': analysis_result.get('error'),
            'screenshots': []  # Populated by script
        }
    
    def create_validation_step(self, validation_result: dict, from_node: str, to_node: str) -> dict:
        """Convert validation result to standardized step dict"""
        return {
            'success': validation_result.get('success', False),
            'from_node': from_node,
            'to_node': to_node,
            'step_category': 'validation',
            'actions': validation_result.get('actions', []),
            'verifications': validation_result.get('verifications', []),
            'verification_results': validation_result.get('verification_results', []),
            'recovered': validation_result.get('recovered', False),
            'recovery_used': validation_result.get('recovery_used', False),
            'error': validation_result.get('error'),
            'screenshots': []  # Populated by script
        }
```

### **Phase 2: Enhance ScriptExecutor (Minimal Changes)**

#### **Step 2.1: Add step recording method to ScriptExecutor**
**File**: `shared/src/lib/executors/script_executor.py` (EXISTING - add 10 lines)
```python
class ScriptExecutionContext:
    def record_step_dict(self, step_dict: dict):
        """Record a step using dict format (backward compatible)"""
        # Add step number
        step_dict['step_number'] = len(self.step_results) + 1
        
        # Add to step_results (existing reporting expects this)
        self.step_results.append(step_dict)
        
        # Add screenshots to context if present
        screenshots = step_dict.get('screenshots', [])
        for screenshot in screenshots:
            if screenshot:
                self.add_screenshot(screenshot)
```

### **Phase 3: Update ZapController (Remove Step Recording Only)**

#### **Step 3.1: Remove step recording from ZapController**
**File**: `backend_host/src/lib/utils/zap_controller.py` (EXISTING - remove 30 lines)
```python
# REMOVE: Delete _record_zap_step_immediately() method entirely
# REMOVE: Delete context.record_step_immediately() calls
# KEEP: All analysis logic intact
# KEEP: All execution logic intact
# RESULT: ZapController only does analysis, returns results
```

### **Phase 4: Update Scripts (Minimal Changes)**

#### **Step 4.1: Update fullzap.py (5 line change)**
```python
# OLD: ZapController records steps directly
zap_success = execute_zap_actions(context, action_edge, mapped_action, args.max_iteration, zap_controller)

# NEW: Use StepExecutor to create and record steps
step_executor = StepExecutor(context)
for iteration in range(1, args.max_iteration + 1):
    # Execute zap iteration (existing logic)
    analysis_result = zap_controller.execute_single_zap(context, action_edge, mapped_action, iteration)
    
    # Create and record step
    zap_step = step_executor.create_zap_step(iteration, mapped_action, analysis_result)
    context.record_step_dict(zap_step)
```

#### **Step 4.2: Update goto_live.py (3 line change)**
```python
# OLD: NavigationExecutor called directly
navigation_result = context.selected_device.navigation_executor.execute_navigation(...)

# NEW: Use StepExecutor to create and record step
step_executor = StepExecutor(context)
navigation_result = context.selected_device.navigation_executor.execute_navigation(...)
nav_step = step_executor.create_navigation_step(navigation_result, "entry", target_node)
context.record_step_dict(nav_step)
```

#### **Step 4.3: Update validation.py (2 line change)**
```python
# OLD: Direct step recording
context.record_step_immediately(step_result)

# NEW: Use StepExecutor
step_executor = StepExecutor(context)
val_step = step_executor.create_validation_step(validation_result, from_node, to_node)
context.record_step_dict(val_step)
```

## 🗂️ **What Gets Deleted (Minimal)**

### **Methods to Delete:**
- `ZapController._record_zap_step_immediately()` (30 lines)
- `ZapController.context.record_step_immediately()` calls (5 locations)

### **No Files Deleted:**
- All existing files stay
- No breaking changes to any APIs
- All existing functionality preserved

## ✅ **Success Criteria**

### **Must Preserve Exactly (Zero Changes to Reports):**
1. **goto_live.py**: Same navigation summary format
2. **goto.py**: Same navigation summary format  
3. **validation.py**: Same validation summary with all recovery stats
4. **fullzap.py**: Same zap summary + database table + HTML reports

### **Must Achieve (Clean Architecture):**
1. **Single Responsibility**: Executors execute, Scripts orchestrate
2. **Standardized Steps**: All steps created via StepExecutor
3. **Clean Separation**: Clear separation between execution and reporting
4. **Minimal Changes**: <100 lines of code changes total

### **Must NOT Break:**
1. Any existing reporting functionality
2. Any existing database integration
3. Any existing screenshot handling
4. Any existing error handling

## 📊 **Progress Tracking (Simplified)**

- [ ] **Phase 1**: Create StepExecutor (1 new file, 50 lines)
  - [ ] Create `shared/src/lib/executors/step_executor.py`
- [ ] **Phase 2**: Enhance ScriptExecutor (10 lines added)
  - [ ] Add `record_step_dict()` method to ScriptExecutionContext
- [ ] **Phase 3**: Update ZapController (30 lines removed)
  - [ ] Remove `_record_zap_step_immediately()` method
  - [ ] Remove step recording calls
- [ ] **Phase 4**: Update Scripts (15 lines changed total)
  - [ ] Update fullzap.py (5 lines)
  - [ ] Update goto_live.py (3 lines)
  - [ ] Update goto.py (3 lines)
  - [ ] Update validation.py (2 lines)
  - [ ] Update ai_testcase_executor.py (2 lines)

## 🎯 **End State (Simple & Clean)**

**Unified architecture with minimal changes:**
- **1 new file**: `step_executor.py` (50 lines)
- **4 updated scripts**: Use StepExecutor for step creation
- **1 updated controller**: ZapController removes step recording
- **1 enhanced executor**: ScriptExecutor adds step recording method
- **Zero breaking changes**: All existing functionality preserved
- **Same exact reporting**: No changes to any report formats
