# AI Central Architecture - Unified Execution System

## 🎯 **Core Principle: Zero Execution Duplication**

The AI system **REUSES** all existing execution infrastructure instead of duplicating it. The AI acts as an **orchestration layer** that delegates to proven executors.

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI CENTRAL                               │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   AI Planner    │    │  AI Orchestrator │    │ AI Tracker  │ │
│  │                 │    │                  │    │             │ │
│  │ • Context Load  │    │ • Step Routing   │    │ • Progress  │ │
│  │ • AI Generation │    │ • Executor       │    │ • Status    │ │
│  │ • Plan Validate │    │   Selection      │    │ • Polling   │ │
│  └─────────────────┘    │ • Result Agg     │    │ • Logging   │ │
│                         └─────────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
        ┌───────────▼────────┐ ┌────▼─────────┐ ┌──▼──────────────┐
        │  ActionExecutor    │ │ Verification │ │ Navigation      │
        │  (EXISTING)        │ │ Executor     │ │ Executor        │
        │                    │ │ (EXISTING)   │ │ (EXISTING)      │
        │ • Remote Actions   │ │              │ │                 │
        │ • Web Actions      │ │ • Image      │ │ • Pathfinding   │
        │ • Desktop Actions  │ │ • Text       │ │ • Cross-tree    │
        │ • Retry Logic      │ │ • Audio      │ │ • Orchestration │
        │ • DB Tracking      │ │ • Video      │ │ • DB Tracking   │
        └────────────────────┘ │ • ADB        │ └─────────────────┘
                               │ • DB Track   │
                               └──────────────┘
```

## 🏗️ **AI Central Components**

### **1. AI Planner (Plan Generation)**

```python
class AIPlanGenerator:
    """Generate execution plans from natural language prompts"""
    
    def __init__(self, team_id: str):
        self.team_id = team_id
        self.context_loader = AIContextLoader()
    
    def generate_plan(self, prompt: str, userinterface_name: str) -> AIPlan:
        """Generate AI plan for specific userinterface"""
        context = self.context_loader.load_context(userinterface_name, self.team_id)
        
        # Use existing AI generation logic (from ai_agent_core.py)
        ai_response = self._call_ai_with_context(prompt, context)
        
        return AIPlan.from_ai_response(ai_response, context)
    
    def analyze_compatibility(self, prompt: str) -> CompatibilityAnalysis:
        """Analyze prompt compatibility across ALL userinterfaces"""
        all_interfaces = get_all_userinterfaces(self.team_id)
        results = []
        
        for interface in all_interfaces:
            try:
                plan = self.generate_plan(prompt, interface['name'])
                results.append({
                    'userinterface': interface['name'],
                    'compatible': plan.feasible,
                    'reasoning': plan.analysis,
                    'plan': plan if plan.feasible else None
                })
            except Exception as e:
                results.append({
                    'userinterface': interface['name'],
                    'compatible': False,
                    'reasoning': f'Analysis failed: {str(e)}'
                })
        
        return CompatibilityAnalysis(prompt, results)
```

### **2. AI Orchestrator (Execution Delegation)**

```python
class AIOrchestrator:
    """Orchestrate AI plan execution using EXISTING executors"""
    
    def __init__(self, host: Dict, device_id: str, team_id: str):
        self.host = host
        self.device_id = device_id
        self.team_id = team_id
        
        # NO execution logic here - only delegation to existing executors
    
    def execute_plan(self, plan: AIPlan, options: ExecutionOptions) -> ExecutionResult:
        """Execute AI plan by delegating to existing executors"""
        
        result = ExecutionResult(plan.id)
        
        for step in plan.steps:
            step_result = self._execute_step(step, options)
            result.add_step_result(step_result)
            
            if not step_result.success and options.stop_on_first_error:
                break
        
        return result
    
    def _execute_step(self, step: AIStep, options: ExecutionOptions) -> StepResult:
        """Route step to appropriate EXISTING executor"""
        
        if step.type == AIStepType.NAVIGATION:
            return self._execute_navigation_step(step, options)
        elif step.type == AIStepType.ACTION:
            return self._execute_action_step(step, options)
        elif step.type == AIStepType.VERIFICATION:
            return self._execute_verification_step(step, options)
        elif step.type == AIStepType.WAIT:
            return self._execute_wait_step(step, options)
        else:
            raise ValueError(f"Unknown step type: {step.type}")
    
    def _execute_navigation_step(self, step: AIStep, options: ExecutionOptions) -> StepResult:
        """Delegate to EXISTING NavigationExecutor"""
        from backend_core.src.services.navigation.navigation_execution import NavigationExecutor
        
        executor = NavigationExecutor(
            host=self.host,
            device_id=self.device_id,
            team_id=self.team_id
        )
        
        # Convert AI step to navigation parameters
        target_node = step.params.get('target_node')
        tree_id = options.context.get('tree_id')
        current_node = options.context.get('current_node_id')
        
        result = executor.execute_navigation(tree_id, target_node, current_node)
        
        return StepResult.from_navigation_result(step, result)
    
    def _execute_action_step(self, step: AIStep, options: ExecutionOptions) -> StepResult:
        """Delegate to EXISTING ActionExecutor"""
        from backend_core.src.services.actions.action_executor import ActionExecutor
        
        executor = ActionExecutor(
            host=self.host,
            device_id=self.device_id,
            tree_id=options.context.get('tree_id'),
            edge_id=options.context.get('edge_id'),
            team_id=self.team_id
        )
        
        # Convert AI step to action format
        action = {
            'command': step.command,
            'params': step.params,
            'action_type': step.params.get('action_type', 'remote')
        }
        
        result = executor.execute_actions([action])
        
        return StepResult.from_action_result(step, result)
    
    def _execute_verification_step(self, step: AIStep, options: ExecutionOptions) -> StepResult:
        """Delegate to EXISTING VerificationExecutor"""
        from backend_core.src.services.verifications.verification_executor import VerificationExecutor
        
        executor = VerificationExecutor(
            host=self.host,
            device_id=self.device_id,
            tree_id=options.context.get('tree_id'),
            node_id=options.context.get('node_id'),
            team_id=self.team_id
        )
        
        # Convert AI step to verification format
        verification = {
            'verification_type': step.params.get('verification_type', 'text'),
            'command': step.command,
            'params': step.params
        }
        
        result = executor.execute_verifications([verification])
        
        return StepResult.from_verification_result(step, result)
    
    def _execute_wait_step(self, step: AIStep, options: ExecutionOptions) -> StepResult:
        """Execute wait step (simple time.sleep)"""
        import time
        
        duration_ms = step.params.get('duration', 1000)
        time.sleep(duration_ms / 1000.0)
        
        return StepResult(step.step_id, True, f"Waited {duration_ms}ms")
```

### **3. AI Tracker (Status & Progress)**

```python
class AITracker:
    """Track AI execution progress and provide status polling"""
    
    def __init__(self):
        self.executions = {}  # execution_id -> ExecutionStatus
    
    def start_execution(self, execution_id: str, plan: AIPlan) -> None:
        """Start tracking an execution"""
        self.executions[execution_id] = ExecutionStatus(
            execution_id=execution_id,
            plan=plan,
            status='executing',
            current_step=0,
            start_time=time.time()
        )
    
    def update_step(self, execution_id: str, step_number: int, step_result: StepResult) -> None:
        """Update step progress"""
        if execution_id in self.executions:
            status = self.executions[execution_id]
            status.current_step = step_number
            status.step_results.append(step_result)
            status.last_update = time.time()
    
    def complete_execution(self, execution_id: str, result: ExecutionResult) -> None:
        """Mark execution as complete"""
        if execution_id in self.executions:
            status = self.executions[execution_id]
            status.status = 'completed' if result.success else 'failed'
            status.result = result
            status.end_time = time.time()
    
    def get_status(self, execution_id: str) -> Dict[str, Any]:
        """Get current execution status for polling"""
        if execution_id not in self.executions:
            return {'success': False, 'error': 'Execution not found'}
        
        status = self.executions[execution_id]
        
        return {
            'success': True,
            'is_executing': status.status == 'executing',
            'current_step': f"Step {status.current_step}/{len(status.plan.steps)}",
            'execution_log': [r.to_log_entry() for r in status.step_results],
            'progress_percentage': (status.current_step / len(status.plan.steps)) * 100
        }
```

## 🔄 **Unified Data Structures**

### **AI Plan Format**

```python
@dataclass
class AIPlan:
    """Unified plan format for all AI operations"""
    id: str
    prompt: str
    analysis: str
    feasible: bool
    steps: List[AIStep]
    userinterface_name: str
    created_at: datetime
    
    @classmethod
    def from_ai_response(cls, ai_response: Dict, context: AIContext) -> 'AIPlan':
        """Convert AI response to standardized plan"""
        steps = []
        for i, step_data in enumerate(ai_response.get('plan', [])):
            step = AIStep(
                step_id=i + 1,
                type=AIStepType.from_command(step_data.get('command')),
                command=step_data.get('command'),
                params=step_data.get('params', {}),
                description=step_data.get('description', ''),
                expected_result=step_data.get('expected_result')
            )
            steps.append(step)
        
        return cls(
            id=str(uuid.uuid4()),
            prompt=context.original_prompt,
            analysis=ai_response.get('analysis', ''),
            feasible=ai_response.get('feasible', True),
            steps=steps,
            userinterface_name=context.userinterface_name,
            created_at=datetime.utcnow()
        )

@dataclass
class AIStep:
    """Standardized AI step format"""
    step_id: int
    type: AIStepType
    command: str
    params: Dict[str, Any]
    description: str
    expected_result: Optional[str] = None

class AIStepType(Enum):
    """AI step types that map to existing executors"""
    NAVIGATION = "navigation"    # -> NavigationExecutor
    ACTION = "action"           # -> ActionExecutor  
    VERIFICATION = "verification" # -> VerificationExecutor
    WAIT = "wait"              # -> Simple time.sleep
    
    @classmethod
    def from_command(cls, command: str) -> 'AIStepType':
        """Determine step type from command"""
        if command == 'execute_navigation':
            return cls.NAVIGATION
        elif command in ['press_key', 'click_element', 'input_text']:
            return cls.ACTION
        elif command.startswith('verify_') or command.startswith('check_'):
            return cls.VERIFICATION
        elif command == 'wait':
            return cls.WAIT
        else:
            return cls.ACTION  # Default fallback
```

### **Execution Options**

```python
@dataclass
class ExecutionOptions:
    """Configure execution behavior for different use cases"""
    mode: ExecutionMode
    context: Dict[str, Any]  # tree_id, node_id, etc.
    enable_progress_tracking: bool = True
    enable_db_tracking: bool = False
    enable_screenshots: bool = False
    stop_on_first_error: bool = True
    timeout_seconds: int = 300

class ExecutionMode(Enum):
    REAL_TIME = "real_time"    # Live execution with polling
    TEST_CASE = "test_case"    # Stored test case execution
    SCRIPT = "script"          # Script framework execution
```

## 🚀 **AI Central Implementation**

### **Main AI Central Class**

```python
class AICentral:
    """Unified AI system that orchestrates all AI operations"""
    
    def __init__(self, team_id: str, host: Dict = None, device_id: str = None):
        self.team_id = team_id
        self.host = host
        self.device_id = device_id
        
        # Core components
        self.planner = AIPlanGenerator(team_id)
        self.orchestrator = AIOrchestrator(host, device_id, team_id) if host else None
        self.tracker = AITracker()
    
    # COMPATIBILITY ANALYSIS (No device required)
    def analyze_compatibility(self, prompt: str) -> CompatibilityAnalysis:
        """Analyze prompt compatibility across all userinterfaces"""
        return self.planner.analyze_compatibility(prompt)
    
    # PLAN GENERATION (Specific userinterface, no device required)
    def generate_plan(self, prompt: str, userinterface_name: str) -> AIPlan:
        """Generate plan for specific userinterface"""
        return self.planner.generate_plan(prompt, userinterface_name)
    
    # PLAN EXECUTION (Requires device)
    def execute_plan(self, plan: AIPlan, options: ExecutionOptions) -> str:
        """Execute plan and return execution_id for tracking"""
        if not self.orchestrator:
            raise ValueError("Cannot execute plan without host/device configuration")
        
        execution_id = str(uuid.uuid4())
        
        # Start tracking
        self.tracker.start_execution(execution_id, plan)
        
        # Execute asynchronously (for real-time polling)
        if options.mode == ExecutionMode.REAL_TIME:
            threading.Thread(
                target=self._execute_plan_async,
                args=(execution_id, plan, options)
            ).start()
        else:
            # Execute synchronously for test cases and scripts
            result = self.orchestrator.execute_plan(plan, options)
            self.tracker.complete_execution(execution_id, result)
        
        return execution_id
    
    def _execute_plan_async(self, execution_id: str, plan: AIPlan, options: ExecutionOptions):
        """Execute plan asynchronously with progress tracking"""
        try:
            result = self.orchestrator.execute_plan(plan, options)
            self.tracker.complete_execution(execution_id, result)
        except Exception as e:
            error_result = ExecutionResult(plan.id, success=False, error=str(e))
            self.tracker.complete_execution(execution_id, error_result)
    
    # STATUS POLLING
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status for polling"""
        return self.tracker.get_status(execution_id)
    
    # ONE-SHOT EXECUTION
    def execute_task(self, prompt: str, userinterface_name: str, options: ExecutionOptions) -> str:
        """Generate plan and execute in one call"""
        plan = self.generate_plan(prompt, userinterface_name)
        return self.execute_plan(plan, options)
```

## 🎮 **Usage Examples**

### **Real-Time Execution (useAIAgent.ts)**

```typescript
// Frontend: Real-time execution with polling
const executeTask = async () => {
    // 1. Start execution
    const response = await fetch('/server/ai/executeTask', {
        method: 'POST',
        body: JSON.stringify({
            prompt: taskInput,
            userinterface_name: 'horizon_android_mobile',
            host: host,
            device_id: device.device_id,
            mode: 'real_time'
        })
    });
    
    const { execution_id } = await response.json();
    
    // 2. Poll for status
    const pollStatus = async () => {
        while (isExecuting) {
            const statusResponse = await fetch(`/server/ai/status/${execution_id}`);
            const status = await statusResponse.json();
            
            setCurrentStep(status.current_step);
            setExecutionLog(status.execution_log);
            
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

### **Test Case Execution**

```python
# Backend: Test case execution
@ai_bp.route('/executeTestCase', methods=['POST'])
def execute_test_case():
    data = request.get_json()
    
    # Load stored plan
    plan = load_test_case_plan(data['test_case_id'])
    
    # Execute using AI Central
    ai_central = AICentral(
        team_id=get_team_id(),
        host=data['host'],
        device_id=data['device_id']
    )
    
    options = ExecutionOptions(
        mode=ExecutionMode.TEST_CASE,
        context={'tree_id': plan.tree_id},
        enable_db_tracking=True
    )
    
    execution_id = ai_central.execute_plan(plan, options)
    
    # Wait for completion (synchronous for test cases)
    while True:
        status = ai_central.get_execution_status(execution_id)
        if not status['is_executing']:
            break
        time.sleep(0.5)
    
    return jsonify(status)
```

### **Script Execution**

```python
# test_scripts/ai_testcase_executor.py (simplified)
def main():
    # Load test case
    test_case = get_test_case(test_case_id, team_id)
    plan = AIPlan.from_stored_test_case(test_case)
    
    # Setup script context
    context = executor.setup_execution_context(args, enable_db_tracking=True)
    
    # Execute using AI Central
    ai_central = AICentral(
        team_id=context.team_id,
        host={'host_name': context.host.host_name},
        device_id=context.selected_device.device_id
    )
    
    options = ExecutionOptions(
        mode=ExecutionMode.SCRIPT,
        context={
            'tree_id': plan.tree_id,
            'script_result_id': context.script_result_id
        },
        enable_db_tracking=True,
        enable_screenshots=True
    )
    
    execution_id = ai_central.execute_plan(plan, options)
    
    # Wait for completion and update script context
    final_status = wait_for_completion(ai_central, execution_id)
    context.overall_success = final_status['success']
    
    executor.cleanup_and_exit(context, args.userinterface_name)
```

## 🎯 **Key Benefits**

### **1. Zero Execution Duplication**
- AI system **ONLY** orchestrates existing executors
- All execution logic remains in proven `ActionExecutor`, `VerificationExecutor`, `NavigationExecutor`
- No duplicate device communication, retry logic, or error handling

### **2. Consistent Behavior**
- Same execution results whether triggered by AI, manual navigation, or scripts
- Same error handling patterns across all execution types
- Same database tracking and reporting

### **3. Maintainable Architecture**
- Single place to fix execution bugs (existing executors)
- AI changes don't affect execution reliability
- Clear separation between planning and execution

### **4. Flexible Integration**
- Easy to add new step types by extending existing executors
- Frontend hooks can use same polling interface
- Script framework integration remains unchanged

### **5. Proven Reliability**
- Builds on battle-tested execution infrastructure
- No regression risk from AI implementation
- Existing navigation, action, and verification logic unchanged

## 📝 **Implementation Priority**

1. **Create AI Central data structures** (`AIPlan`, `AIStep`, `ExecutionOptions`)
2. **Implement AIPlanGenerator** (reuse existing AI generation logic)
3. **Build AIOrchestrator** (pure delegation to existing executors)
4. **Add AITracker** for status polling
5. **Update frontend hooks** to use unified AI Central
6. **Refactor existing AI controllers** to use AI Central
7. **Clean up duplicate code** (delete old AI execution logic)

This architecture ensures that your AI system is a **thin orchestration layer** that leverages all your existing, proven execution infrastructure without any duplication or reimplementation.
