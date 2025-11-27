# AI Plan Execution Documentation

## 🎯 **Overview**

The AI Agent system uses a unified plan execution approach that works identically for both real-time tasks and stored test cases. The same plan format, execution engine, and status polling interface are used across all use cases.

## 🏗️ **Unified Execution Architecture**

### **Core Principle: One Plan, One Execution**

```
AI Plan Generation → Unified Execution Engine → Status Polling
      ↓                       ↓                      ↓
  Same Format            Same Logic            Same Interface
```

## 📋 **Plan Format (Universal)**

All AI plans use the same standardized format:

```python
{
    'analysis': 'AI reasoning about the task',
    'feasible': True,  # Whether task can be executed
    'plan': [
        {
            'step': 1,
            'command': 'execute_navigation',
            'params': {'target_node': 'home'},
            'description': 'Navigate to home screen'
        },
        {
            'step': 2, 
            'command': 'press_key',
            'params': {'key': 'OK'},
            'description': 'Press OK button'
        },
        {
            'step': 3,
            'command': 'wait',
            'params': {'duration': 2000},
            'description': 'Wait 2 seconds'
        }
    ]
}
```

## 🔄 **Execution Flow**

### **Phase 1: Plan Generation**

```python
def generate_plan_only(self, task_description: str, available_actions: List[Dict], 
                      available_verifications: List[Dict], device_model: str = None, 
                      userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
    """
    Generate AI plan without executing (for 2-phase execution).
    
    Process:
    1. Load navigation tree for context
    2. Extract available nodes (using labels for semantic mapping)
    3. Create consolidated AI prompt with navigation and action contexts
    4. Call AI model for plan generation
    5. Validate plan feasibility
    6. Cache plan for execution
    
    Returns:
        {
            'success': True,
            'plan': {...},  # AI generated plan
            'execution_log': [...],
            'current_step': 'Plan generated, ready for execution'
        }
    """
```

### **Phase 2: Plan Execution (No Duplication)**

```python
def execute_plan_only(self, userinterface_name: str = None) -> Dict[str, Any]:
    """
    Execute previously generated plan by delegating to existing infrastructure.
    NO DUPLICATE CODE - reuses proven execution from ai_testcase_executor.py
    
    Process:
    1. Validate cached plan exists
    2. Delegate to existing _execute() method (same as test case executor)
    3. Uses proven infrastructure: setup_script_environment(), execute_action_directly()
    4. Returns execution results with step tracking
    
    Returns:
        {
            'success': True,
            'executed_steps': 3,
            'total_steps': 3,
            'action_result': {...},
            'verification_result': {...}
        }
    """
    
    # Simple delegation - NO DUPLICATE CODE
    result = self._execute(
        plan=self.cached_plan,
        navigation_tree=None,
        userinterface_name=interface_name
    )
    
    return result
```

## 🎮 **Step Execution Details**

### **Step Types and Handlers (No Duplication)**

| Command Type | Handler | Service Used | Description |
|--------------|---------|--------------|-------------|
| `execute_navigation` | `_execute()` → `execute_navigation_with_verification()` | Existing navigation service | Navigate between screens/nodes |
| `press_key` | `_execute()` → `execute_action_directly()` | Existing action infrastructure | Remote control key press |
| `click_element` | `_execute()` → `execute_action_directly()` | Existing action infrastructure | UI element interaction |
| `wait` | `_execute()` → `execute_action_directly()` | Existing action infrastructure | Pause execution |

**Key Point:** All execution delegates to existing `_execute()` method which uses proven infrastructure from `ai_testcase_executor.py`

### **Step Execution Process**

```python
for i, step in enumerate(plan_steps):
    step_num = i + 1
    command = step.get('command')
    params = step.get('params', {})
    description = step.get('description', f'Step {step_num}')
    
    # 1. Update status for polling
    self.current_step = f"Step {step_num}/{total_steps}: {description}"
    
    # 2. Record step start
    step_start_time = time.time()
    self._add_to_log("execution", "step_start", {
        'step': step_num,
        'total_steps': total_steps,
        'command': command, 
        'description': description
    })
    
    # 3. Execute step using existing services
    if command == 'execute_navigation':
        result = self._execute_navigation_via_service(target_node, interface_name)
    elif command in ['press_key', 'click_element', 'wait']:
        result = self._execute_action_via_service(command, params)
    
    # 4. Record step completion
    step_duration = time.time() - step_start_time
    
    if result.get('success'):
        self._add_to_log("execution", "step_success", {
            'step': step_num, 
            'command': command, 
            'duration': step_duration
        })
    else:
        self._add_to_log("execution", "step_failed", {
            'step': step_num, 
            'command': command, 
            'duration': step_duration,
            'error': result.get('error')
        })
        break  # Stop on first failure
```

## 🔧 **Execution Infrastructure (Zero Duplication)**

### **Core Principle: Reuse Existing `_execute()` Method**

Both real-time and test case execution use the **exact same `_execute()` method**:

```python
# Real-time execution
def execute_plan_only(self, userinterface_name: str = None) -> Dict[str, Any]:
    """Delegate to existing _execute method - NO DUPLICATE CODE"""
    
    # Simple delegation to proven method
    result = self._execute(
        plan=self.cached_plan,
        navigation_tree=None,
        userinterface_name=interface_name
    )
    
    return result

# Test case execution (ai_testcase_executor.py line 143)
ai_result = ai_agent._execute(
    plan=fake_plan,
    navigation_tree=None,
    userinterface_name=args.userinterface_name
)
```

### **How `_execute()` Works (Existing Proven Infrastructure)**

```python
def _execute(self, plan: Dict[str, Any], navigation_tree: Dict = None, userinterface_name: str = "horizon_android_mobile"):
    """Execute AI plan using existing system infrastructure (same as ai_testcase_executor.py)"""
    
    # 1. Classify steps (existing method)
    action_steps, verification_steps = self._classify_ai_steps(plan_steps)
    
    # 2. Setup execution environment (existing infrastructure)
    from shared.lib.utils.script_execution_utils import setup_script_environment, select_device
    from shared.lib.utils.action_utils import execute_action_directly
    
    setup_result = setup_script_environment("ai_agent")
    host = setup_result['host']
    device = select_device(host, self.device_id, "ai_agent")['device']
    
    # 3. Execute actions (existing infrastructure - NO HARDCODING)
    for step in action_steps:
        if command == 'execute_navigation':
            # Use existing navigation service
            result = execute_navigation_with_verification(...)
        else:
            # Use existing action infrastructure - automatic controller selection
            action = self._convert_step_to_action(step)
            result = execute_action_directly(host, device, action)
```

### **Why This Approach is Superior:**

- ✅ **Zero code duplication** - reuses existing proven `_execute()` method
- ✅ **Same as test case execution** - identical to `ai_testcase_executor.py` line 143
- ✅ **No hardcoded logic** - uses `execute_action_directly()` for automatic controller selection
- ✅ **Proven reliability** - leverages working infrastructure from test case system
- ✅ **Automatic device handling** - `setup_script_environment()` and `select_device()` handle all device context

## 📊 **Status Polling System**

### **Real-Time Status Updates**

The AI Agent provides consistent status information for frontend polling:

```python
def get_status(self) -> Dict[str, Any]:
    """Get current AI agent status for polling"""
    return {
        'success': True,
        'is_executing': self.is_executing,          # Boolean: currently running
        'current_step': self.current_step,          # String: current operation
        'current_position': self.current_node_id,   # String: current location
        'cached_tree_id': self.cached_tree_id,      # String: loaded tree
        'cached_interface': self.cached_userinterface_name,
        'execution_log_size': len(self.execution_log),
        'execution_log': self.execution_log,        # List: detailed step history
        'device_id': self.device_id
    }
```

### **Execution Log Format**

The execution log provides detailed step tracking compatible with frontend polling:

```python
# Step start
{
    'timestamp': 1642534567.123,
    'log_type': 'execution',
    'action_type': 'step_start',
    'data': {
        'step': 1,
        'total_steps': 3,
        'command': 'execute_navigation',
        'description': 'Navigate to home screen'
    },
    'description': 'Step 1/3: Navigate to home screen'
}

# Step success
{
    'timestamp': 1642534569.456,
    'log_type': 'execution', 
    'action_type': 'step_success',
    'data': {
        'step': 1,
        'command': 'execute_navigation',
        'duration': 2.3
    },
    'description': 'Step 1 completed in 2.3s'
}

# Task completion
{
    'timestamp': 1642534575.789,
    'log_type': 'execution',
    'action_type': 'task_completed',
    'data': {
        'executed_steps': 3,
        'total_steps': 3,
        'duration': 8.2,
        'success': True
    },
    'description': 'Task completed in 8.2s'
}
```

## 🔄 **Use Case Comparison**

### **Real-Time Execution (Rec Modal)**

**Flow:**
```typescript
// Frontend: useAIAgent.ts
executeTask() 
    ↓
fetch('/server/aiagent/executeTask')  // With task_id for async
    ↓
proxy_to_host('/host/aiagent/executeTask')
    ↓
AIAgentController.generate_plan_only()  // Phase 1: Generate plan
    ↓
AIAgentController.execute_plan_only()   // Phase 2: Execute plan (async)
    ↓
Polling: fetch('/server/aiagent/getStatus')  // Real-time updates
```

**Benefits:**
- ✅ **Immediate plan feedback** - user sees plan before execution
- ✅ **Real-time progress** - step-by-step updates via polling
- ✅ **Async execution** - doesn't block frontend
- ✅ **Live error handling** - immediate feedback on failures

### **Test Case Execution**

**Flow:**
```typescript
// Frontend: useAITestCase.ts  
executeTestCase()
    ↓
fetch('/server/aitestcase/executeTestCase')
    ↓
proxy_to_host('/host/aitestcase/executeTestCase')
    ↓
AIAgentController.execute_stored_test_case()  // Uses stored plan
    ↓
AIAgentController.execute_plan_only()         // Same execution engine
```

**Benefits:**
- ✅ **Identical execution** - same engine as real-time tasks
- ✅ **Consistent behavior** - no differences between execution types
- ✅ **Reusable plans** - store once, execute many times
- ✅ **Cross-device support** - same plan works on compatible devices

## 🎯 **Key Design Decisions**

### **1. No Code Duplication**

**Instead of duplicating navigation logic:**
```python
# ❌ OLD: Custom navigation execution
def _execute_navigation(self, target_node: str):
    # 50+ lines of custom pathfinding logic
    # Duplicate error handling
    # Custom position tracking

# ✅ NEW: Service delegation  
def _execute_navigation_via_service(self, target_node: str):
    # Uses existing navigation_service.execute_navigation_with_verification()
    # Proven pathfinding and error handling
    # Established position tracking
```

### **2. Consistent Status Interface**

**Same polling interface for both use cases:**
```python
# Real-time execution polling
status = ai_agent.get_status()
# Returns: is_executing, current_step, execution_log

# Test case execution polling  
status = ai_agent.get_status() 
# Returns: Same exact format and fields
```

### **3. Service Integration**

**Leverages existing proven infrastructure:**
- **Navigation**: `navigation_service.execute_navigation_with_verification()`
- **Actions**: `host_utils.get_controller()` + `controller.execute_command()`
- **Error Handling**: Existing service error patterns
- **Position Tracking**: Established navigation position management

## 📊 **Execution States and Tracking**

### **Execution States**

| State | Description | Polling Response |
|-------|-------------|------------------|
| `Planning` | AI generating plan | `is_executing: False, current_step: 'Generating plan...'` |
| `Executing` | Running plan steps | `is_executing: True, current_step: 'Step 2/5: Navigate to menu'` |
| `Completed` | Task finished | `is_executing: False, current_step: 'Task completed'` |
| `Failed` | Task failed | `is_executing: False, current_step: 'Error: Navigation failed'` |

### **Step Tracking**

Each step goes through consistent tracking:

```python
# 1. Step Start
self.current_step = f"Step {step_num}/{total_steps}: {description}"
self._add_to_log("execution", "step_start", {...})

# 2. Step Execution  
result = self._execute_[navigation|action]_via_service(...)

# 3. Step Completion
if result.get('success'):
    self._add_to_log("execution", "step_success", {...})
else:
    self._add_to_log("execution", "step_failed", {...})
```

## 🚀 **Frontend Integration**

### **Real-Time Execution (useAIAgent)**

```typescript
// 1. Execute task
const executeTask = async () => {
    // Start execution
    const response = await fetch('/server/aiagent/executeTask', {
        body: JSON.stringify({
            task_description: taskInput,
            host: host,
            device_id: device?.device_id
        })
    });
    
    // 2. Start status polling
    const pollStatus = async () => {
        while (isExecuting) {
            const statusResponse = await fetch('/server/aiagent/getStatus');
            const status = await statusResponse.json();
            
            // Update UI with current step and progress
            setCurrentStep(status.current_step);
            setExecutionLog(status.execution_log);
            
            // Check for completion
            if (!status.is_executing) {
                setIsExecuting(false);
                break;
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    };
    
    pollStatus();
};
```

### **Test Case Execution (useAITestCase)**

```typescript
// Execute stored test case
const executeTestCase = async (testCaseId: string, deviceId: string) => {
    const response = await fetch('/server/aitestcase/executeTestCase', {
        body: JSON.stringify({
            test_case_id: testCaseId,
            device_id: deviceId
        })
    });
    
    // Same execution engine, same status format
    // Could use same polling pattern if needed
};
```

## 🔧 **Service Integration Details**

### **Navigation Service Integration**

**How it works:**
```python
# AI Agent delegates to existing navigation service
from backend_host.src.services.navigation.navigation_executor import NavigationExecutor

# Initialize NavigationExecutor with host configuration
executor = NavigationExecutor(host=self.host, device_id=self.device_id, team_id=self.team_id)

result = executor.execute_navigation(
    tree_id=self.cached_tree_id,           # Loaded navigation tree
    target_node_id=target_node,            # AI-specified target
    current_node_id=self.current_node_id   # Current position tracking
)

# Service handles:
# - Pathfinding from current to target position
# - Action execution via NavigationExecutor
# - Verification execution if configured
# - Error handling and recovery
# - Final position reporting
```

**Benefits:**
- ✅ **No duplicate pathfinding** - uses proven NetworkX algorithms
- ✅ **Automatic position tracking** - maintains current location
- ✅ **Cross-tree navigation** - handles complex navigation hierarchies
- ✅ **Verification support** - executes node verifications automatically

### **Action Service Integration**

**How it works:**
```python
# AI Agent delegates to existing controller services
from shared.lib.utils.host_utils import get_controller

# Get appropriate controller for command type
if command in ['press_key']:
    controller = get_controller(self.device_id, 'remote')
elif command in ['click_element']:
    controller = get_controller(self.device_id, 'appium')

# Execute using existing controller infrastructure
success = controller.execute_command(command, params)

# Controller handles:
# - Device communication (IR, ADB, etc.)
# - Command validation and formatting
# - Error handling and retries
# - Device-specific adaptations
```

**Benefits:**
- ✅ **No duplicate device communication** - uses proven controller factory
- ✅ **Device compatibility** - supports all existing device types
- ✅ **Error handling** - established retry and recovery patterns
- ✅ **Consistent behavior** - same actions as manual operations

## 📈 **Progress Tracking and Polling**

### **Execution Log Structure**

The execution log provides detailed tracking compatible with frontend polling:

```python
# Log entry format (consistent across all steps)
{
    'timestamp': float,      # Unix timestamp
    'log_type': 'execution', # Always 'execution' for plan steps
    'action_type': str,      # 'step_start', 'step_success', 'step_failed', 'task_completed', 'task_failed'
    'data': dict,           # Step-specific data (step number, duration, etc.)
    'description': str      # Human-readable description
}
```

### **Frontend Polling Pattern**

```typescript
// Consistent polling for both real-time and test case execution
const pollStatus = async () => {
    while (isExecuting) {
        const status = await fetch('/server/aiagent/getStatus');
        const result = await status.json();
        
        // Update progress from execution log
        const newEntries = result.execution_log.slice(prevLogLength);
        for (const entry of newEntries) {
            if (entry.action_type === 'step_success') {
                toast.showSuccess(`✅ Step ${entry.data.step} completed`);
            } else if (entry.action_type === 'step_failed') {
                toast.showError(`❌ Step ${entry.data.step} failed`);
            } else if (entry.action_type === 'task_completed') {
                toast.showSuccess(`🎉 Task completed in ${entry.data.duration}s`);
            }
        }
        
        // Update current step
        setCurrentStep(result.current_step);
        
        // Check completion
        if (!result.is_executing) {
            setIsExecuting(false);
            break;
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
};
```

## 🎮 **Usage Examples**

### **Real-Time Execution**

```python
# Server endpoint: /server/aiagent/executeTask
ai_agent = AIAgentController(device_id="device1")

# Phase 1: Generate plan
plan_result = ai_agent.generate_plan_only(
    task_description="go to live channel and check audio",
    available_actions=device_actions,
    available_verifications=device_verifications,
    device_model="android_mobile",
    userinterface_name="horizon_android_mobile"
)

# Phase 2: Execute plan (async)
execution_result = ai_agent.execute_plan_only("horizon_android_mobile")

# Polling: Get status
status = ai_agent.get_status()
```

### **Test Case Execution**

```python
# Server endpoint: /server/aitestcase/executeTestCase
ai_agent = AIAgentController(device_id="device1")

# Load stored test case
test_case = get_test_case(test_case_id, team_id)

# Execute stored plan (same engine)
execution_result = ai_agent.execute_stored_test_case(test_case)

# Same status interface
status = ai_agent.get_status()
```

## 🔮 **Benefits of Zero-Duplication Approach**

### **For Developers:**
- ✅ **Single execution method** - only `_execute()` needs maintenance (same as test cases)
- ✅ **Zero code duplication** - reuses existing `ai_testcase_executor.py` infrastructure
- ✅ **Consistent behavior** - real-time and test cases use identical execution path
- ✅ **No hardcoded logic** - automatic controller selection via `execute_action_directly()`

### **For Users:**
- ✅ **Identical experience** - real-time and test case execution behave exactly the same
- ✅ **Proven reliability** - uses battle-tested test case execution infrastructure
- ✅ **Consistent error handling** - same error patterns across all execution types
- ✅ **Predictable behavior** - same plan produces same results regardless of execution type

### **For System:**
- ✅ **Maintainable architecture** - single execution path to maintain and debug
- ✅ **Proven reliability** - builds on working `ai_testcase_executor.py` foundation
- ✅ **No regression risk** - reuses existing working code instead of reimplementing
- ✅ **Future-ready** - any improvements to test case execution automatically benefit real-time execution

---

## 📝 **Summary**

The unified AI plan execution system provides:

1. **One Plan Format** - universal structure for all AI tasks
2. **One Execution Engine** - same logic for real-time and test cases
3. **One Status Interface** - consistent polling for all execution types
4. **Service Integration** - reuses existing proven infrastructure
5. **No Duplication** - eliminates redundant navigation and action logic

This approach ensures consistent behavior, maintainable code, and reliable execution across all AI automation use cases.
