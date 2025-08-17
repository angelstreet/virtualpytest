# AI Test Case Script Integration Plan

## 🎯 Current State Analysis

### ✅ What's Already Implemented
1. **Database Schema**: `test_cases` table enhanced with AI-specific fields
2. **AI Generation**: Working two-step process (analyze → generate)
3. **Backend Routes**: `server_aitestcase_routes.py` with generate/analyze endpoints
4. **Frontend Dialog**: `AITestCaseGenerator.tsx` for creating test cases
5. **Test Case Storage**: AI test cases saved to database as JSON

### ❌ What's Missing - Script Integration
The AI test cases are currently **isolated** from the script execution system. They cannot be run through:
- `RunTests.tsx` (script dropdown)
- `useScript.ts` (execution hook) 
- `script_execution_utils.py` (execution pipeline)
- `script_framework.py` (reporting system)

---

## 🎯 Integration Goal

**Make AI test cases appear and execute like normal scripts** in `RunTests.tsx`:

1. **Script List**: AI test cases appear in script dropdown alongside `.py` files
2. **Execution**: AI test cases execute through same pipeline as normal scripts  
3. **Reporting**: AI test cases generate same reports as normal scripts
4. **Progress**: AI test cases show same progress/status as normal scripts

---

## 🔧 Required Changes

### 1. **Extend Script Listing** (`/server/script/list`)

**File**: `backend_server/src/routes/server_script_routes.py`

**Current**: Only lists `.py` files from `test_scripts/` directory
```python
# Current implementation
available_scripts = list_available_scripts()  # Only .py files
return jsonify({'success': True, 'scripts': available_scripts})
```

**Required**: Include AI test cases from database
```python
@server_script_bp.route('/script/list', methods=['GET'])
def list_scripts():
    try:
        # Get regular Python scripts
        from shared.lib.utils.script_execution_utils import list_available_scripts
        regular_scripts = list_available_scripts()
        
        # Get AI test cases from database  
        from shared.lib.utils.app_utils import get_team_id
        from shared.lib.supabase.testcase_db import get_all_test_cases
        
        team_id = get_team_id()
        all_test_cases = get_all_test_cases(team_id)
        
        # Filter for AI-created test cases and format as script names
        ai_scripts = []
        for tc in all_test_cases:
            if tc.get('creator') == 'ai':
                script_name = f"ai_testcase_{tc['test_id']}"
                ai_scripts.append(script_name)
        
        # Combine both types
        all_scripts = regular_scripts + ai_scripts
        
        return jsonify({
            'success': True, 
            'scripts': all_scripts,
            'ai_test_cases': ai_scripts,  # For UI to distinguish
            'regular_scripts': regular_scripts
        })
```

### 2. **Extend Script Execution** (`execute_script()`)

**File**: `shared/lib/utils/script_execution_utils.py`

**Current**: Only executes `.py` files
```python
def execute_script(script_name: str, device_id: str, parameters: str = "") -> Dict[str, Any]:
    script_path = get_script_path(script_name)  # Looks for .py file
    # Execute Python file...
```

**Required**: Detect and handle AI test cases
```python
def execute_script(script_name: str, device_id: str, parameters: str = "") -> Dict[str, Any]:
    # Check if this is an AI test case
    if script_name.startswith("ai_testcase_"):
        return execute_ai_test_case_as_script(script_name, device_id, parameters)
    
    # Regular script execution (existing code)
    script_path = get_script_path(script_name)
    # ... existing implementation
```

### 3. **Create AI Test Case Script Executor**

**File**: `shared/lib/utils/script_execution_utils.py` (new function)

**Purpose**: Convert AI test case to script execution format
```python
def execute_ai_test_case_as_script(script_name: str, device_id: str, parameters: str = "") -> Dict[str, Any]:
    """Execute AI test case through script framework pipeline"""
    start_time = time.time()
    
    try:
        # Extract test case ID
        test_case_id = script_name.replace("ai_testcase_", "")
        
        # Load test case from database
        from shared.lib.utils.app_utils import get_team_id
        from shared.lib.supabase.testcase_db import get_test_case
        
        team_id = get_team_id()
        test_case = get_test_case(test_case_id, team_id)
        
        if not test_case:
            raise ValueError(f"AI test case not found: {test_case_id}")
        
        # Create virtual script executor
        from shared.lib.utils.script_framework import ScriptExecutor
        
        script_display_name = test_case.get('name', f"AI Test Case {test_case_id}")
        executor = ScriptExecutor(script_name, script_display_name)
        
        # Parse parameters (same as regular scripts)
        userinterface_name = "horizon_android_mobile"  # Default
        host_name = None
        device_name = None
        
        if parameters:
            # Parse parameters: "horizon_android_tv --host sunri-pi1 --device device2"
            parts = parameters.split()
            if parts:
                userinterface_name = parts[0]
            
            # Extract --host and --device
            if '--host' in parts:
                host_idx = parts.index('--host')
                if host_idx + 1 < len(parts):
                    host_name = parts[host_idx + 1]
            
            if '--device' in parts:
                device_idx = parts.index('--device')
                if device_idx + 1 < len(parts):
                    device_name = parts[device_idx + 1]
        
        # Create args object (similar to argparse)
        class Args:
            def __init__(self):
                self.userinterface_name = userinterface_name
                self.host = host_name
                self.device = device_name
        
        args = Args()
        
        # Execute through script framework
        context = executor.setup_execution_context(args, enable_db_tracking=True)
        
        if context.error_message:
            raise Exception(context.error_message)
        
        # Load navigation tree
        if not executor.load_navigation_tree(context, userinterface_name):
            raise Exception(context.error_message or "Failed to load navigation tree")
        
        # Convert AI test case steps to navigation sequence
        navigation_path = convert_ai_steps_to_navigation_path(test_case.get('steps', []))
        
        # Execute navigation sequence
        success = executor.execute_navigation_sequence(context, navigation_path)
        context.overall_success = success
        
        # Generate report (same as regular scripts)
        report_result = executor.generate_final_report(context, userinterface_name)
        
        # Return same format as regular script execution
        total_execution_time = int((time.time() - start_time) * 1000)
        
        return {
            'stdout': f"AI Test Case: {script_display_name}\nSteps: {len(navigation_path)}\nResult: {'SUCCESS' if success else 'FAILED'}",
            'stderr': context.error_message if not success else '',
            'exit_code': 0 if success else 1,
            'script_name': script_name,
            'device_id': device_id,
            'script_path': f"ai_testcase:{test_case_id}",
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': report_result.get('report_url', ''),
            'script_success': success  # Critical for UI
        }
        
    except Exception as e:
        total_execution_time = int((time.time() - start_time) * 1000)
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'exit_code': 1,
            'script_name': script_name,
            'device_id': device_id,
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': "",
            'script_success': False
        }

def convert_ai_steps_to_navigation_path(ai_steps: List[Dict]) -> List[Dict]:
    """Convert AI test case steps to navigation framework format"""
    navigation_path = []
    
    for i, step in enumerate(ai_steps):
        if step.get('type') == 'action' and step.get('command') == 'navigate':
            target_node = step.get('params', {}).get('target_node')
            if target_node:
                navigation_path.append({
                    'step_number': i + 1,
                    'from_node_label': 'current',
                    'to_node_label': target_node,
                    'actions': [step],
                    'verifications': []
                })
    
    return navigation_path
```

### 4. **Update Frontend Script Display**

**File**: `frontend/src/pages/RunTests.tsx`

**Current**: Shows all scripts equally
**Required**: Distinguish AI test cases with badges

```tsx
// In script dropdown
{availableScripts.map((script) => (
  <MenuItem key={script} value={script}>
    {script.startsWith('ai_testcase_') ? (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Chip label="AI" size="small" color="primary" />
        <Typography>{getAITestCaseName(script)}</Typography>
      </Box>
    ) : (
      script
    )}
  </MenuItem>
))}
```

### 5. **Add AI Test Case Name Resolution**

**File**: `frontend/src/hooks/script/useScript.ts`

**Purpose**: Get friendly names for AI test cases
```tsx
const getAITestCaseName = useCallback(async (scriptName: string): Promise<string> => {
  if (!scriptName.startsWith('ai_testcase_')) return scriptName;
  
  const testCaseId = scriptName.replace('ai_testcase_', '');
  
  try {
    const response = await fetch(`/server/testcases/getTestCase/${testCaseId}`);
    const result = await response.json();
    
    if (result.success && result.test_case) {
      return `AI: ${result.test_case.name}`;
    }
  } catch (error) {
    console.warn('Failed to get AI test case name:', error);
  }
  
  return `AI Test Case ${testCaseId}`;
}, []);
```

---

## 📋 Implementation Steps

### Phase 1: Backend Integration
1. ✅ **Database schema** - Already done
2. ✅ **AI generation routes** - Already done  
3. 🔄 **Extend `/server/script/list`** - Add AI test cases to script listing
4. 🔄 **Extend `execute_script()`** - Add AI test case detection and routing
5. 🔄 **Create `execute_ai_test_case_as_script()`** - Bridge to script framework

### Phase 2: Frontend Integration  
1. 🔄 **Update `RunTests.tsx`** - Add AI test case badges in script dropdown
2. 🔄 **Update `useScript.ts`** - Add AI test case name resolution
3. 🔄 **Test execution flow** - Ensure AI test cases execute like normal scripts

### Phase 3: Testing & Polish
1. 🔄 **End-to-end testing** - Generate AI test case and execute in RunTests
2. 🔄 **Report validation** - Ensure same report format as normal scripts
3. 🔄 **UI polish** - Consistent experience between AI and regular scripts

---

## 🎯 Expected Result

After implementation:

1. **Script Dropdown**: Shows `"AI: Go to live and check audio"` alongside `"goto.py"`
2. **Execution**: AI test cases execute through same pipeline as Python scripts
3. **Reports**: AI test cases generate same HTML reports with screenshots
4. **Progress**: Same loading/completion states for AI and regular scripts
5. **Error Handling**: Same error display and recovery for both types

**User Experience**: Seamless integration - users won't distinguish between AI and regular scripts except for the "AI" badge.

---

## 🚨 Critical Requirements

1. **No Separate UI**: AI test cases MUST appear in existing `RunTests.tsx`
2. **Same Pipeline**: AI test cases MUST use `script_execution_utils.py` → `script_framework.py`
3. **Same Reports**: AI test cases MUST generate identical report format
4. **Same API**: Frontend continues using `useScript.ts` without changes
5. **Performance**: Script listing should remain fast even with many AI test cases

This plan ensures AI test cases become **first-class citizens** in the script execution system while maintaining all existing functionality.
