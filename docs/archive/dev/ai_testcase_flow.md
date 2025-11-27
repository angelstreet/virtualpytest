# AI Test Case Generation & Execution Flow

## 🎯 Overview

The AI Test Case system converts natural language prompts into executable test cases that run through the same framework as regular Python scripts.

**🔑 Key Architectural Principle**: **Separation of Analysis and Execution**
- **Analysis Phase**: Server-side, no device access required
- **Execution Phase**: Host-side, requires device controllers

## 📋 Complete Flow: Prompt → Analysis → Generation → Execution

### **Step 1: User Input & Compatibility Analysis** 
```
User enters: "Go to live and check audio"
```

**Frontend: `AITestCaseGenerator.tsx`**
- User enters natural language prompt
- Calls `useAITestCase.analyzeTestCase(prompt)`

**Backend: `/server/aitestcase/analyzeTestCase`**
- **Uses NEW: `AITestCaseAnalyzer` class** (server-side, no device dependencies)
- Fetches all available user interfaces for the team
- Analyzes prompt compatibility using **pure heuristic logic**:
  - `"audio"` keywords → Compatible with `horizon_android_mobile`, `horizon_android_tv`
  - `"web"` keywords → Compatible with `perseus_360_web`
  - `"navigation"` keywords → Compatible with all interfaces
- **Navigation graph inspection** to verify required screens exist
- **NO device controllers** - purely static analysis
- Returns compatibility matrix with detailed reasoning

### **Step 2: User Validation & Test Case Generation**

**Frontend: Analysis Results Display**
- Shows AI's understanding of the prompt
- Displays compatibility matrix with checkboxes
- User selects which interfaces to generate test cases for

**User clicks "Generate Test Cases"**
- Calls `useAITestCase.generateTestCases(analysis_id, confirmed_interfaces)`

**Backend: `/server/aitestcase/generateTestCases`**
- **Uses SAME: `AITestCaseAnalyzer` class** (server-side, no device dependencies)
- Retrieves cached analysis results
- Generates **ONE unified test case** with all compatible interfaces
- Creates structured steps in **AI Agent format** using **static logic**:

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
- **IMPORTANT**: `AIAgentController` constructor now requires mandatory `device_id`
- **NO MORE**: `device_id: str = None` - this was bad coding practice
- **CLEAN API**: `AIAgentController(device_id: str, device_name: str = None)`
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

### **1. Separation of Concerns** ⭐ **NEW**
- **`AITestCaseAnalyzer`**: Server-side analysis and generation (NO device access)
- **`AIAgentController`**: Host-side execution (REQUIRES device access)
- **Clean APIs**: No optional-but-mandatory parameters
- **Clear responsibilities**: Analysis ≠ Execution

### **2. Format Compatibility**
- AI generated steps use **AI Agent format** (not ScriptExecutor format)
- Single format throughout: `{step, type, command, params, description}`
- No conversion needed between generation and execution

### **3. Execution Reuse**  
- **AIAgentController._execute()** handles all action/verification execution
- **ScriptExecutor** handles device control, setup, and reporting
- **No duplication** of execution logic

### **4. Unified Experience**
- AI test cases appear in script lists with badges
- Execute through same `RunTests.tsx` interface
- Generate same reports as regular scripts
- Use same device control and streaming

### **5. Clean Integration**
- AI test cases stored as data, not files
- Environment variable passing for subprocess isolation
- Standard script execution pipeline with AI detection

## 📊 Data Flow Summary

```
Prompt → AITestCaseAnalyzer → Analysis → Generation → Database → Script List → Execution → AIAgentController → Controllers → Report
```

**✨ Clean Architecture: Analysis (Server) ≠ Execution (Host)**

## 🔧 Technical Components

### **NEW: Server-Side Analysis & Generation**
- **`AITestCaseAnalyzer`** - Server-side class for analysis and generation (NO device dependencies)
  - `analyze_compatibility(prompt, userinterfaces)` - Heuristic analysis
  - `generate_test_steps(prompt, interface_name)` - Step generation
  - Pure logic, navigation graph inspection, keyword matching

### **UPDATED: Host-Side Execution**
- **`AIAgentController`** - Host-side execution (REQUIRES device access)
  - **FIXED API**: `AIAgentController(device_id: str, device_name: str = None)`
  - **NO MORE**: Optional-but-mandatory parameters
  - `_execute(plan, userinterface_name)` - Device execution only

### **Frontend Components**
- `AITestCaseGenerator.tsx` - Two-step generation UI
- `TestCaseEditor.tsx` - Integration into test case management
- `RunTests.tsx` - Unified script execution interface
- `useAITestCase.ts` - API hook for generation workflow

### **Backend Routes**
- `/server/aitestcase/analyzeTestCase` - Uses `AITestCaseAnalyzer` (no device)
- `/server/aitestcase/generateTestCases` - Uses `AITestCaseAnalyzer` (no device)
- `/server/script/list` - Combined script + AI test case listing
- `/server/script/execute` - Unified execution endpoint

### **Core Execution**
- `script_execution_utils.py` - AI test case detection and routing
- `ai_testcase_executor.py` - Specialized AI test case runner
- `AIAgentController._execute()` - Core execution engine (requires device)
- `script_framework.py` - Device control and reporting

### **Database Schema**
- `test_cases` table - Stores AI test cases with structured steps
- `ai_analysis_cache` table - Caches analysis results between steps
- AI-specific columns: `creator`, `original_prompt`, `compatible_userinterfaces`

---

## 🏗️ Implementation Details

### **NEW Component: AITestCaseAnalyzer**

**Location**: `backend_host/src/controllers/ai/ai_testcase_analyzer.py`

```python
class AITestCaseAnalyzer:
    """Server-side AI test case analysis and generation - NO device dependencies."""
    
    def __init__(self):
        # No device controllers needed
        # Pure logic and heuristic analysis
        pass
    
    def analyze_compatibility(self, prompt: str, userinterfaces: List[Dict]) -> Dict:
        """
        Analyze test case compatibility using heuristics and navigation graphs.
        
        Returns:
            {
                'analysis_id': 'uuid',
                'understanding': 'Parsed intent',
                'compatibility_matrix': {
                    'compatible_userinterfaces': ['interface1', 'interface2'],
                    'incompatible': ['interface3'],
                    'reasons': {'interface1': 'Has required navigation nodes'}
                }
            }
        """
        # Heuristic keyword matching
        # Navigation graph inspection  
        # Static compatibility logic
        # NO device access
        
    def generate_test_steps(self, prompt: str, interface_name: str, 
                          navigation_graph: Dict) -> List[Dict]:
        """
        Generate executable test steps using static logic.
        
        Returns:
            [
                {
                    'step': 1,
                    'type': 'action',
                    'command': 'execute_navigation',
                    'params': {'target_node': 'live'},
                    'description': 'Navigate to live content'
                }
            ]
        """
        # Generate AI Agent format steps
        # Use navigation graph for valid nodes
        # Pure logic, no device execution
```

### **UPDATED Component: AIAgentController**

**Location**: `backend_host/src/controllers/ai/ai_agent.py`

```python
class AIAgentController(BaseController):
    """Host-side AI execution controller - REQUIRES device access."""
    
    def __init__(self, device_id: str, device_name: str = None, **kwargs):
        """
        FIXED: device_id is now mandatory parameter (not optional).
        NO MORE: device_id: str = None (bad practice)
        """
        super().__init__("ai", device_name or device_id)
        
        # Store device_id for controller access
        self.device_id = device_id
        # ... rest of initialization
    
    def _execute(self, plan: Dict, userinterface_name: str) -> Dict:
        """Execute test steps on real device using controllers."""
        # Uses remote controllers via self.device_id
        # Executes navigation, actions, verifications
        # Returns execution results
```

### **Route Updates**

**`/server/aitestcase/analyzeTestCase`**:
```python
# OLD (BROKEN):
ai_agent = AIAgentController()  # Requires device_id!

# NEW (FIXED):
analyzer = AITestCaseAnalyzer()  # No device dependencies
result = analyzer.analyze_compatibility(prompt, userinterfaces)
```

**`/server/aitestcase/generateTestCases`**:
```python
# OLD (BROKEN):
ai_agent = AIAgentController()  # Requires device_id!

# NEW (FIXED):
analyzer = AITestCaseAnalyzer()  # No device dependencies
steps = analyzer.generate_test_steps(prompt, interface_name, navigation_graph)
```

---

## 🚀 Benefits of This Architecture

### **1. Clear Separation**
- **Analysis**: Server logic, no device coupling
- **Execution**: Host logic, device-specific

### **2. Better Error Handling**
- **No runtime failures** from missing device_id during analysis
- **Compile-time safety** with mandatory parameters

### **3. Maintainability**
- **Single responsibility** per component
- **No mixed concerns** between analysis and execution
- **Easier testing** - analysis can be unit tested without devices

### **4. Scalability**
- **Analysis scales independently** of device availability
- **Generation works offline** without host connection
- **Execution only when needed** on actual devices
