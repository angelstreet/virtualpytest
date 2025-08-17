# AI Test Case Execution - Step 2 Implementation Plan

## 🎯 Core Understanding

### What We Have Already Built ✅
1. **AI Generation Working**: Two-step process (analyze → generate) creates structured test cases in database
2. **AIAgentController.execute_task()**: Fully functional AI execution engine 
3. **Script Framework**: Complete execution pipeline (`script_framework.py`, `script_execution_utils.py`)
4. **Database Storage**: AI test cases stored with structured steps and verifications

### What's Missing ❌
**Script Integration**: AI test cases cannot be executed through `RunTests.tsx` like normal `.py` scripts

---

## 🔧 The Correct Architecture

### Current Flow (Working)
```
1. User types prompt → "Go to live and check audio"
2. AI analyzes compatibility → Returns compatible interfaces
3. AI generates structured steps → Saved to database as test cases
4. Test cases stored with: {steps: [...], verifications: [...]}
```

### Missing Flow (What We Need)
```
5. RunTests.tsx lists AI test cases → Shows "ai_testcase_12345" alongside "goto.py"
6. User selects AI test case → Loads from database
7. Executes stored steps → Uses existing script_framework.py
8. Generates reports → Same as normal scripts
```

---

## 📋 Step-by-Step Implementation

### Step 1: Extend Script Listing (5 minutes)
**File**: `backend_server/src/routes/server_script_routes.py`

**Current Problem**: `/server/script/list` only returns `.py` files
**Solution**: Add AI test cases to the list

```python
@server_script_bp.route('/script/list', methods=['GET'])
def list_scripts():
    try:
        # Get regular Python scripts (EXISTING)
        from shared.lib.utils.script_execution_utils import list_available_scripts
        regular_scripts = list_available_scripts()
        
        # Get AI test cases from database (NEW)
        from shared.lib.utils.app_utils import get_team_id
        from shared.lib.supabase.testcase_db import get_all_test_cases
        
        team_id = get_team_id()
        all_test_cases = get_all_test_cases(team_id)
        
        # Convert AI test cases to script names (NEW)
        ai_scripts = []
        ai_test_cases_info = {}  # For frontend to show friendly names
        
        for tc in all_test_cases:
            if tc.get('creator') == 'ai':
                script_name = f"ai_testcase_{tc['test_id']}"
                ai_scripts.append(script_name)
                ai_test_cases_info[script_name] = {
                    'name': tc.get('name', 'Unknown AI Test'),
                    'original_prompt': tc.get('original_prompt', ''),
                    'compatible_userinterfaces': tc.get('compatible_userinterfaces', [])
                }
        
        # Combine both types (MODIFIED)
        all_scripts = regular_scripts + ai_scripts
        
        return jsonify({
            'success': True, 
            'scripts': all_scripts,
            'ai_test_cases_info': ai_test_cases_info  # For UI to show friendly names
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

### Step 2: Detect AI Scripts in Execution Pipeline (10 minutes)
**File**: `shared/lib/utils/script_execution_utils.py`

**Current Problem**: `execute_script()` only handles `.py` files
**Solution**: Detect `ai_testcase_` prefix and redirect

```python
def execute_script(script_name: str, device_id: str, parameters: str = "") -> Dict[str, Any]:
    """Execute script - handle both regular Python scripts and AI test cases"""
    
    # NEW: Check if this is an AI test case
    if script_name.startswith("ai_testcase_"):
        print(f"[@script_execution_utils:execute_script] AI test case detected: {script_name}")
        # Pass script name as environment variable for subprocess
        os.environ['AI_SCRIPT_NAME'] = script_name
        # Redirect to AI executor script
        return execute_script("ai_testcase_executor", device_id, parameters)
    
    # EXISTING: Regular script execution (unchanged)
    script_path = get_script_path(script_name)
    if not script_path:
        return {
            'success': False,
            'error': f'Script not found: {script_name}',
            'exit_code': 1
        }
    
    # ... rest of existing implementation unchanged
```

### Step 3: Create AI Test Case Executor Script (15 minutes)
**File**: `test_scripts/ai_testcase_executor.py`

**Purpose**: Bridge between AI test cases and script framework
**Key**: Use stored steps, NOT re-generate from prompt

```python
#!/usr/bin/env python3
"""
AI Test Case Executor
Loads stored AI test case from database and executes through script framework.
"""

import sys
import os
import argparse

# Add project paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

def main():
    try:
        # Parse standard script arguments
        parser = argparse.ArgumentParser(description='Execute AI-generated test case')
        parser.add_argument('userinterface_name', help='User interface name')
        parser.add_argument('--host', required=True, help='Host name')
        parser.add_argument('--device', required=True, help='Device ID')
        args = parser.parse_args()
        
        # Get test case ID from environment (passed by execute_script)
        script_name = os.environ.get('AI_SCRIPT_NAME', '')
        if not script_name.startswith('ai_testcase_'):
            print(f"ERROR: Invalid AI script name: {script_name}")
            sys.exit(1)
            
        test_case_id = script_name.replace('ai_testcase_', '')
        print(f"[@ai_testcase_executor] Executing test case: {test_case_id}")
        
        # Load test case from database (NOT re-generate)
        from shared.lib.utils.app_utils import DEFAULT_TEAM_ID
        from shared.lib.supabase.testcase_db import get_test_case
        
        test_case = get_test_case(test_case_id, DEFAULT_TEAM_ID)
        if not test_case:
            print(f"ERROR: Test case not found: {test_case_id}")
            sys.exit(1)
        
        print(f"[@ai_testcase_executor] Loaded: {test_case.get('name', 'Unknown')}")
        print(f"[@ai_testcase_executor] Original prompt: {test_case.get('original_prompt', 'N/A')}")
        
        # Use existing script framework (NOT AIAgentController.execute_task)
        from shared.lib.utils.script_framework import ScriptExecutor
        
        script_display_name = test_case.get('name', f"AI Test Case {test_case_id}")
        executor = ScriptExecutor(f"ai_testcase_{test_case_id}", script_display_name)
        
        # Setup execution context (EXISTING framework)
        context = executor.setup_execution_context(args, enable_db_tracking=True)
        if not context:
            print("ERROR: Failed to setup execution context")
            sys.exit(1)
        
        # Load navigation tree (EXISTING framework)
        if not executor.load_navigation_tree(context, args.userinterface_name):
            print(f"ERROR: Failed to load navigation tree: {context.error_message}")
            sys.exit(1)
        
        # Execute stored steps (KEY: Use stored steps, not AIAgentController)
        stored_steps = test_case.get('steps', [])
        stored_verifications = test_case.get('verification_conditions', [])
        
        print(f"[@ai_testcase_executor] Executing {len(stored_steps)} stored steps")
        
        # Convert stored steps to navigation path format
        navigation_path = []
        for i, step in enumerate(stored_steps):
            if step.get('type') == 'action' and step.get('command') == 'navigate':
                target_node = step.get('params', {}).get('target_node', 'home')
                navigation_path.append({
                    'step_number': i + 1,
                    'from_node_label': 'current',
                    'to_node_label': target_node,
                    'actions': [step],
                    'verifications': [v for v in stored_verifications if v.get('step_number') == i + 1]
                })
        
        # Execute using EXISTING navigation sequence framework
        success = executor.execute_navigation_sequence(context, navigation_path)
        context.overall_success = success
        
        # Generate report using EXISTING framework
        report_result = executor.generate_final_report(context, args.userinterface_name)
        
        # Output result in standard script format
        prompt = test_case.get('original_prompt', 'N/A')
        print(f"[@ai_testcase_executor] === EXECUTION COMPLETE ===")
        print(f"AI Test Case: {script_display_name}")
        print(f"Original Prompt: {prompt}")
        print(f"Steps Executed: {len(stored_steps)}")
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        if report_result.get('report_url'):
            print(f"Report: {report_result['report_url']}")
        
        # Standard script success marker
        print(f"SCRIPT_SUCCESS:{str(success).lower()}")
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"[@ai_testcase_executor] FATAL ERROR: {str(e)}")
        print("SCRIPT_SUCCESS:false")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Step 4: Update Frontend to Show AI Scripts (10 minutes)
**File**: `frontend/src/pages/RunTests.tsx`

**Add to useEffect for script loading**:
```tsx
useEffect(() => {
    const loadScripts = async () => {
        setLoading(true);
        try {
            const response = await fetch('/server/script/list');
            const data = await response.json();
            
            if (data.success) {
                setAvailableScripts(data.scripts || []);
                // NEW: Store AI test case info for display
                setAiTestCasesInfo(data.ai_test_cases_info || {});
            }
        } catch (error) {
            console.error('Failed to load scripts:', error);
        } finally {
            setLoading(false);
        }
    };
    
    loadScripts();
}, []);
```

**Add helper functions**:
```tsx
// NEW: Helper to get friendly display name
const getScriptDisplayName = useCallback((scriptName: string): string => {
    if (scriptName.startsWith('ai_testcase_') && aiTestCasesInfo[scriptName]) {
        return aiTestCasesInfo[scriptName].name;
    }
    return scriptName;
}, [aiTestCasesInfo]);

// NEW: Check if script is AI-generated
const isAIScript = useCallback((scriptName: string): boolean => {
    return scriptName.startsWith('ai_testcase_');
}, []);
```

**Update script dropdown**:
```tsx
<Select value={selectedScript} onChange={(e) => setSelectedScript(e.target.value)}>
    {availableScripts.map((script) => (
        <MenuItem key={script} value={script}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {isAIScript(script) && (
                    <Chip label="AI" size="small" color="primary" />
                )}
                <Typography>{getScriptDisplayName(script)}</Typography>
            </Box>
        </MenuItem>
    ))}
</Select>
```

### Step 5: Enable AI Script Execution from TestCase Page (5 minutes)
**File**: `frontend/src/pages/TestCaseEditor.tsx`

**Add execute button to each AI test case row**:
```tsx
// In test case table actions column
{testCase.creator === 'ai' && (
    <Tooltip title="Execute in RunTests">
        <IconButton 
            onClick={() => {
                // Store selection for RunTests page
                localStorage.setItem('preselected_script', `ai_testcase_${testCase.test_id}`);
                // Redirect to RunTests
                window.location.href = '/test-execution/run-tests';
            }}
            size="small"
        >
            <PlayArrowIcon />
        </IconButton>
    </Tooltip>
)}
```

**Add to RunTests.tsx to handle preselection**:
```tsx
// In RunTests.tsx - add to useEffect after scripts load
useEffect(() => {
    const preselectedScript = localStorage.getItem('preselected_script');
    if (preselectedScript && availableScripts.includes(preselectedScript)) {
        setSelectedScript(preselectedScript);
        setShowWizard(true);
        localStorage.removeItem('preselected_script'); // Clean up
    }
}, [availableScripts]);
```

---

## 🎯 Key Architectural Decisions

### ✅ What We KEEP (Existing, Working)
1. **AIAgentController.execute_task()** - Used ONLY for generation (analysis → structured steps)
2. **Script Framework** - Used for ALL executions (regular scripts + AI test cases)
3. **Database Storage** - AI test cases stored with structured steps/verifications
4. **RunTests.tsx** - Single execution interface for both script types

### ✅ What We ADD (New, Minimal)
1. **Script Listing Extension** - Include AI test cases in `/server/script/list`
2. **Script Detection** - Detect `ai_testcase_` prefix in `execute_script()`
3. **AI Executor Script** - Bridge between stored test cases and script framework
4. **UI Badges** - Show "AI" badges in script dropdown

### ❌ What We DON'T Do (Avoid Duplication)
1. **Don't rewrite AIAgentController** - Use existing execute_task()
2. **Don't rewrite script framework** - Use existing ScriptExecutor
3. **Don't create separate execution UI** - Use existing RunTests.tsx
4. **Don't re-generate from prompt** - Use stored structured steps

---

## 🚀 Implementation Order

### Phase 1: Backend Integration (20 minutes)
1. ✅ Update `/server/script/list` to include AI test cases
2. ✅ Update `execute_script()` to detect AI test case prefix
3. ✅ Create `ai_testcase_executor.py` script

### Phase 2: Frontend Integration (15 minutes)
1. ✅ Update RunTests.tsx to handle AI test case info
2. ✅ Add AI badges to script dropdown
3. ✅ Add execute button to TestCase table
4. ✅ Add preselection logic

### Phase 3: Testing (10 minutes)
1. ✅ Generate AI test case via dialog
2. ✅ Verify it appears in RunTests dropdown
3. ✅ Execute and verify report generation
4. ✅ Test direct execution from TestCase page

---

## 🎯 Expected Result

**User Experience**:
1. Generate AI test case: "Go to live and check audio" → Creates structured test case in database
2. Go to RunTests page → See "🔤 AI: Go to live and check audio" in dropdown
3. Select and execute → Runs stored steps through script framework
4. View report → Same format as regular Python scripts

**Technical Flow**:
```
AI Generation: prompt → AIAgentController.execute_task() → structured steps → database
AI Execution: database → stored steps → ScriptExecutor → report
```

This approach reuses ALL existing functionality and adds minimal bridge code to integrate AI test cases into the script execution pipeline.
