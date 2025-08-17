# AI Test Case Generation & Execution Flow

## 🎯 Overview

The AI Test Case system converts natural language prompts into executable test cases that run through the same framework as regular Python scripts.

## 📋 Complete Flow: Prompt → Generation → Execution

### **Step 1: User Input & Analysis** 
```
User enters: "Go to live and check audio"
```

**Frontend: `AITestCaseGenerator.tsx`**
- User enters natural language prompt
- Calls `useAITestCase.analyzeTestCase(prompt)`

**Backend: `/server/aitestcase/analyzeTestCase`**
- Fetches all available user interfaces for the team
- Analyzes prompt compatibility against each interface using heuristic logic:
  - `"audio"` keywords → Compatible with `horizon_android_mobile`, `horizon_android_tv`
  - `"web"` keywords → Compatible with `perseus_360_web`
  - `"navigation"` keywords → Compatible with all interfaces
- Returns compatibility matrix with reasoning

### **Step 2: User Validation & Generation**

**Frontend: Analysis Results Display**
- Shows AI's understanding of the prompt
- Displays compatibility matrix with checkboxes
- User selects which interfaces to generate test cases for

**User clicks "Generate Test Cases"**
- Calls `useAITestCase.generateTestCases(analysis_id, confirmed_interfaces)`

**Backend: `/server/aitestcase/generateTestCases`**
- Retrieves cached analysis results
- Generates **ONE unified test case** with all compatible interfaces
- Creates structured steps in **AI Agent format**:

```json
{
  "steps": [
    {
      "step": 1,
      "type": "action",
      "command": "execute_navigation", 
      "params": {"target_node": "live"},
      "description": "Navigate to live content"
    },
    {
      "step": 2, 
      "type": "verification",
      "verification_type": "verify_audio",
      "command": "check_audio_quality",
      "params": {"threshold": 0.8},
      "description": "Verify audio quality"
    }
  ]
}
```

- Saves to database with `compatible_userinterfaces` array
- Returns generated test case

### **Step 3: Script Integration**

**Script Discovery: `/server/script/list`**
- Regular scripts: Listed from `test_scripts/` folder
- AI test cases: Listed with `ai_testcase_` prefix from database
- Returns combined list with AI metadata for display names

**Frontend: `RunTests.tsx`**
- Shows AI test cases with `AI` badges
- Uses `getScriptDisplayName()` to show friendly names instead of UUIDs

### **Step 4: Execution Flow**

**User selects AI test case and clicks Execute**

**Script Detection: `script_execution_utils.py`**
```python
if script_name.startswith('ai_testcase_') and script_name != "ai_testcase_executor":
    # Set environment variable for AI script ID
    os.environ['AI_SCRIPT_NAME'] = script_name
    # Redirect to specialized executor
    return execute_script("ai_testcase_executor", script_config, device_id, team_id)
```

**AI Executor: `test_scripts/ai_testcase_executor.py`**
```python
# Extract test case ID from environment
test_case_id = os.environ.get('AI_SCRIPT_NAME', '').replace('ai_testcase_', '')

# Load test case from database  
test_case = get_test_case(test_case_id, team_id)
stored_steps = test_case.get('steps', [])

# Create fake plan for AI Agent execution
fake_plan = {
    'analysis': f'Pre-generated test case for: {original_prompt}',
    'feasible': True,
    'plan': stored_steps  # Steps are in AI Agent format!
}

# Execute using existing AI framework
ai_agent = AIAgentController(device_name=context.selected_device.device_name)
result = ai_agent._execute(plan=fake_plan, userinterface_name=userinterface_name)
```

**AI Agent Execution: `AIAgentController._execute()`**
- Separates action steps vs verification steps
- **Actions**: Calls `_execute_actions()` → Uses controller framework for navigation/clicks
- **Verifications**: Calls `_execute_verifications()` → Uses verification controllers
- Returns combined results

**Framework Integration: `ScriptExecutor`**
- Sets up device control, navigation trees, reporting
- Generates final HTML report with screenshots and video
- Outputs `SCRIPT_SUCCESS:true/false` for host parsing

### **Step 5: Results & Reporting**

**Same as Regular Scripts:**
- HTML reports with screenshots and execution logs
- Success/failure determination from `SCRIPT_SUCCESS` marker
- Video recordings of test execution
- Integration with execution history

## 🔄 Key Architecture Principles

### **1. Format Compatibility**
- AI generated steps use **AI Agent format** (not ScriptExecutor format)
- Single format throughout: `{step, type, command, params, description}`
- No conversion needed between generation and execution

### **2. Execution Reuse**  
- **AIAgentController._execute()** handles all action/verification execution
- **ScriptExecutor** handles device control, setup, and reporting
- **No duplication** of execution logic

### **3. Unified Experience**
- AI test cases appear in script lists with badges
- Execute through same `RunTests.tsx` interface
- Generate same reports as regular scripts
- Use same device control and streaming

### **4. Clean Integration**
- AI test cases stored as data, not files
- Environment variable passing for subprocess isolation
- Standard script execution pipeline with AI detection

## 📊 Data Flow Summary

```
Prompt → Analysis → Generation → Database → Script List → Execution → AI Agent → Controllers → Report
```

**No Legacy Code, No Fallbacks, One Clean Path! ✨**

## 🔧 Technical Components

### **Frontend Components**
- `AITestCaseGenerator.tsx` - Two-step generation UI
- `TestCaseEditor.tsx` - Integration into test case management
- `RunTests.tsx` - Unified script execution interface
- `useAITestCase.ts` - API hook for generation workflow

### **Backend Routes**
- `/server/aitestcase/analyzeTestCase` - Compatibility analysis
- `/server/aitestcase/generateTestCases` - Test case generation
- `/server/script/list` - Combined script + AI test case listing
- `/server/script/execute` - Unified execution endpoint

### **Core Execution**
- `script_execution_utils.py` - AI test case detection and routing
- `ai_testcase_executor.py` - Specialized AI test case runner
- `AIAgentController._execute()` - Core execution engine
- `script_framework.py` - Device control and reporting

### **Database Schema**
- `test_cases` table - Stores AI test cases with structured steps
- `ai_analysis_cache` table - Caches analysis results between steps
- AI-specific columns: `creator`, `original_prompt`, `compatible_userinterfaces`
