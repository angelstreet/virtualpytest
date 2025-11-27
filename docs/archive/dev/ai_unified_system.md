# AI Unified System Documentation

## 🎯 **Overview**

The AI Unified System combines real-time task execution and test case generation in a single, powerful AI Agent. This consolidated approach eliminates code duplication while providing both interactive automation and persistent test case management.

## 🏗️ **Unified Architecture**

### **Split Architecture - 3 Focused Files**

```
AIAgentCore (ai_agent_core.py)
├── Basic execution and navigation
├── Device capability fetching  
├── AI prompt construction
├── Navigation tree management
└── Real-time task execution

AIAgentTestCase (ai_agent_testcase.py)  
├── Test case generation from prompts
├── Test case storage and management
├── Stored test case execution
└── Test case format conversion

AIAgentAnalysis (ai_agent_analysis.py)
├── Cross-device compatibility analysis
├── Quick feasibility checking
├── Task complexity analysis
└── Device model extraction

AIAgentController = AIAgentAnalysis
└── Unified interface providing all capabilities
```

### **Inheritance Chain**

```
BaseController
    ↓
AIAgentCore (basic execution)
    ↓  
AIAgentTestCase (+ test case generation)
    ↓
AIAgentAnalysis (+ compatibility analysis)
    ↓
AIAgentController (alias for AIAgentAnalysis)
```

### **Shared Core Services**

All capabilities use the same underlying infrastructure:

- **Device Capability Fetching**: `_get_available_actions(device_id)`
- **AI Prompt Construction**: `_get_navigation_context()` + `_get_action_context()`
- **Feasibility Analysis**: Real AI model analysis (not heuristics)
- **Step Execution**: Integrated execution with existing navigation system

## 📋 **Core Features**

### **1. Real-Time Task Execution**

**Interactive automation for immediate tasks:**

```python
# Execute task immediately on current device
ai_agent = AIAgentController(device_id="device1")
result = ai_agent.execute_task("go to live channel and check audio")

# Features:
# - Current node position tracking
# - Live step-by-step progress
# - Real-time error handling
# - Toast notifications in frontend
```

**Key Benefits:**
- ✅ **Immediate execution** - no storage, direct action
- ✅ **Current session context** - works with current device state
- ✅ **Live feedback** - real-time progress and error reporting
- ✅ **Interactive debugging** - see exactly what's happening

### **2. Test Case Generation & Management**

**Create reusable test cases for repeated execution:**

```python
# Generate test case for storage and reuse
test_case_result = ai_agent.generate_test_case(
    prompt="go to live channel and check audio",
    userinterface_name="horizon_android_mobile",
    store_in_db=True
)

# Features:
# - Cross-device compatibility analysis
# - Persistent storage in database
# - Execution history tracking
# - Test case library management
```

**Key Benefits:**
- ✅ **Reusable tests** - create once, execute many times
- ✅ **Cross-device support** - works across multiple devices/interfaces
- ✅ **Test management** - organize, categorize, track execution history
- ✅ **Regression testing** - automated test suite execution

### **3. Cross-Device Compatibility Analysis**

**Analyze test case compatibility across multiple devices:**

```python
# Analyze compatibility across interfaces
compatibility_results = ai_agent.analyze_cross_device_compatibility(
    test_case=generated_test_case,
    target_interfaces=["horizon_android_mobile", "perseus_web", "fire_tv_interface"]
)

# Results show:
# - Compatibility score per interface
# - Missing capabilities
# - Required vs available navigation nodes
# - Adaptation suggestions
```

## 🔧 **Technical Implementation**

### **Unified Device Capability Fetching**

**Single method serves both use cases:**

```python
def _get_available_actions(self, device_id: str) -> Dict[str, Any]:
    """Get available actions from controller - reuse existing controller system"""
    from backend_host.src.controllers.controller_config_factory import get_controller_config
    controller_config = get_controller_config(device_id)
    return controller_config.get('available_actions', {})

# Used by:
# - Real-time execution: Get current device actions
# - Test case generation: Analyze required vs available actions
# - Compatibility analysis: Compare actions across devices
```

### **Consolidated AI Prompt Construction**

**Shared context generation for consistent AI analysis:**

```python
# Unified context system
navigation_context = self._get_navigation_context(available_nodes)
action_context = self._get_action_context()

prompt = f"""You are controlling a TV application...
{navigation_context}  # Navigation - Available nodes: [...]
{action_context}      # Actions - Available commands: [...]

CRITICAL RULES:
- You MUST ONLY use nodes from the available list above
- For execute_navigation, target_node MUST be one of the exact node IDs listed
"""

# Benefits:
# - Consistent AI behavior across use cases
# - No duplicate prompt logic
# - Centralized rule enforcement
```

### **Superior AI Analysis vs Heuristics**

**Real AI model analysis instead of keyword matching:**

```python
# AI Agent: Real AI analysis
agent_model = AI_CONFIG['providers']['openrouter']['models']['agent']
result = call_text_ai(prompt=analysis_prompt, model=agent_model)
ai_response = json.loads(result['response'])

# vs Old Test Case System: Heuristic rules
if any(word in prompt_lower for word in ['go to', 'navigate']):
    requirements['navigation'] = True  # Simple keyword matching
```

**AI Analysis Advantages:**
- ✅ **Context understanding** - AI understands intent, not just keywords
- ✅ **Complex reasoning** - handles multi-step logic and dependencies
- ✅ **Adaptive analysis** - learns from available capabilities
- ✅ **Natural language** - processes complex, nuanced requests

### **Integrated Step Execution**

**Unified execution system for both use cases:**

```python
# Real-time execution: Direct execution
if command == 'execute_navigation':
    result = self._execute_navigation(target_node, cached_interface)
elif command in ['press_key', 'click_element', 'wait']:
    result = self._execute_action(command, params)

# Test case execution: Same methods, different context
# Test cases store steps, then execute using identical logic
```

## 🎨 **Frontend Integration**

### **Dual Hook System**

**Two hooks for different use cases:**

```typescript
// Real-time interactive tasks
const { executeTask, isExecuting, executionLog } = useAIAgent({
  selectedHost,
  selectedDeviceId
});

// Test case generation and management  
const { generateTestCase, analyzeTestCase, executeTestCase } = useAITestCase();
```

### **Unified Backend API**

**Single AI Agent serves both frontend hooks:**

```python
# Real-time execution endpoint
@host_aiagent_bp.route('/executeTask', methods=['POST'])
def execute_task():
    ai_agent = AIAgentController(device_id=device_id)
    return ai_agent.execute_task(task_description)

# Test case generation endpoint  
@server_aitestcase_bp.route('/generateTestCase', methods=['POST'])
def generate_test_case():
    ai_agent = AIAgentController(device_id="server")  # Server-side generation
    return ai_agent.generate_test_case(prompt, interface_name)
```

## 📊 **Use Case Comparison**

### **When to Use Real-Time Execution**

**Perfect for:**
- ✅ **Interactive debugging** - "go to live and see what happens"
- ✅ **One-off tasks** - quick actions that don't need to be repeated
- ✅ **Exploratory testing** - trying different approaches
- ✅ **Current session work** - operating on current device state

**Example:**
```typescript
// Quick interactive task
await executeTask("navigate to settings and check current volume level");
// → Executes immediately, shows live progress, no storage
```

### **When to Use Test Case Generation**

**Perfect for:**
- ✅ **Regression testing** - tests that run repeatedly
- ✅ **Cross-device validation** - same test on multiple devices
- ✅ **Test documentation** - building a library of automated tests
- ✅ **CI/CD integration** - automated test suite execution

**Example:**
```typescript
// Create reusable test case
const testCase = await generateTestCase("verify live channel audio works correctly");
// → Stores in database, analyzes compatibility, can execute later on any device
```

## 🗃️ **Database Schema**

### **Unified Test Cases Table**

```sql
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    creator VARCHAR(20) NOT NULL CHECK (creator IN ('ai', 'manual')),
    
    -- AI-specific fields (only for AI-created test cases)
    original_prompt TEXT,
    ai_analysis JSONB,
    
    -- Device/Interface context
    device_model VARCHAR(100) NOT NULL,
    interface_name VARCHAR(100) NOT NULL,
    
    -- Compatibility metadata
    compatible_devices JSONB DEFAULT '["all"]',
    compatible_userinterfaces JSONB DEFAULT '["all"]',
    device_adaptations JSONB DEFAULT '{}',
    
    -- Test definition
    test_steps JSONB NOT NULL,
    expected_outcomes JSONB,
    
    -- Execution context
    estimated_duration_ms INTEGER,
    required_capabilities TEXT[],
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'ready',
    
    -- Execution history
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    last_execution_at TIMESTAMP,
    last_execution_result VARCHAR(20)
);
```

## 🔄 **Migration from Separate Systems**

### **Consolidation Benefits**

**Before (Separate Systems):**
- ❌ **Duplicate capability fetching** - different methods for same data
- ❌ **Inconsistent AI prompts** - different prompt construction logic
- ❌ **Heuristic analysis** - keyword matching vs real AI analysis
- ❌ **Separate execution paths** - different logic for same actions

**After (Unified System):**
- ✅ **Single capability source** - `_get_available_actions()` for all use cases
- ✅ **Consistent AI analysis** - same model and prompt system
- ✅ **Shared execution logic** - identical step execution for both use cases
- ✅ **Maintainable codebase** - one system to maintain and improve

### **Migration Steps**

1. **✅ Enhanced AI Agent** with test case generation methods
2. **✅ Added cross-device compatibility analysis**
3. **✅ Unified capability fetching and prompt construction**
4. **🔄 Update frontend hooks** to use unified backend
5. **🔄 Migrate existing test cases** to new format
6. **🔄 Remove old AI Test Case system** (eliminate duplication)

## 🎯 **API Reference**

### **Real-Time Execution**

```python
# Execute task immediately
ai_agent.execute_task(
    task_description="go to live channel and check audio",
    userinterface_name="horizon_android_mobile"  # optional
) -> Dict[str, Any]

# Returns:
{
    'success': True,
    'executed_steps': 3,
    'total_steps': 3,
    'execution_time_ms': 12500,
    'current_position': 'node-live-123'
}
```

### **Test Case Generation**

```python
# Generate test case
ai_agent.generate_test_case(
    prompt="go to live channel and check audio",
    userinterface_name="horizon_android_mobile",  # optional
    store_in_db=True  # optional
) -> Dict[str, Any]

# Returns:
{
    'success': True,
    'test_case': {
        'id': 'ai_1234567890_horizon_android_mobile',
        'name': 'AI: go to live channel and check audio',
        'creator': 'ai',
        'test_steps': [...],
        'ai_analysis': {...}
    },
    'ai_confidence': 0.9
}
```

### **Cross-Device Analysis**

```python
# Analyze compatibility
ai_agent.analyze_cross_device_compatibility(
    test_case=generated_test_case,
    target_interfaces=["horizon_android_mobile", "perseus_web"]
) -> List[Dict[str, Any]]

# Returns:
[
    {
        'interface_name': 'horizon_android_mobile',
        'compatible': True,
        'compatibility_score': 1.0,
        'reasoning': 'Compatible with 3/3 steps'
    },
    {
        'interface_name': 'perseus_web',
        'compatible': False,
        'compatibility_score': 0.6,
        'reasoning': 'Incompatible: Navigation node not available'
    }
]
```

### **Quick Feasibility Check**

```python
# Real-time feasibility for UI feedback
ai_agent.quick_feasibility_check(
    prompt="go to live channel",
    interface_name="horizon_android_mobile"  # optional
) -> Dict[str, Any]

# Returns:
{
    'success': True,
    'feasible': True,
    'reason': 'Navigation and actions available',
    'suggestions': []
}
```

## 🔧 **Configuration**

### **AI Model Configuration**

```python
# In shared/lib/utils/ai_utils.py
'models': {
    'text': 'microsoft/phi-3-mini-128k-instruct',        # Basic text tasks
    'vision': 'qwen/qwen-2.5-vl-7b-instruct',           # Image analysis  
    'translation': 'microsoft/phi-3-mini-128k-instruct', # Text translation
    'agent': 'meta-llama/llama-3.1-8b-instruct:free'    # AI agent reasoning (unified)
}
```

### **System Configuration**

```python
# AI Agent settings
AI_AGENT_CONFIG = {
    'default_interface': 'horizon_android_mobile',
    'step_timeout_ms': 30000,
    'compatibility_threshold': 0.8,  # 80% compatibility required
    'max_execution_steps': 20,
    'enable_position_tracking': True,
    'enable_test_case_storage': True
}
```

## 🚀 **Best Practices**

### **1. Choose the Right Mode**

```python
# Real-time execution for immediate needs
if task_is_one_off or debugging_session:
    result = ai_agent.execute_task(prompt)

# Test case generation for reusable tests  
if task_needs_repetition or cross_device_testing:
    test_case = ai_agent.generate_test_case(prompt)
```

### **2. Leverage Cross-Device Analysis**

```python
# Always analyze compatibility for test cases
test_case = ai_agent.generate_test_case(prompt)
compatibility = ai_agent.analyze_cross_device_compatibility(
    test_case, 
    all_available_interfaces
)

# Store compatibility results with test case
test_case['compatibility_analysis'] = compatibility
```

### **3. Use Feasibility Checks for UX**

```typescript
// Real-time feasibility feedback in UI
const debouncedFeasibilityCheck = useDebounce(async (prompt: string) => {
    if (prompt.length > 10) {
        const result = await ai_agent.quick_feasibility_check(prompt);
        setFeasibilityIndicator(result);
    }
}, 500);
```

## 🤖 **AI Model Generation Workflow**

### **Automated Navigation Model Creation**

The AI system can automatically generate navigation models through intelligent exploration:

#### **Phase 1: Manual Setup (Entry Point)**
```
User creates: Entry → Home node
- Takes screenshot of home screen  
- Sets as entry point and starting position
- Defines device model and available commands
```

#### **Phase 2: AI Exploration (Automated)**
```python
class AINavigationExplorer(AIAgentController):
    def explore_and_generate_model(self, home_id: str):
        """AI-driven navigation model generation"""
        
        # 1. Start from user-defined home
        current_position = home_id
        exploration_queue = [home_id]
        
        while exploration_queue:
            current_node = exploration_queue.pop(0)
            
            # 2. Take screenshot and analyze
            screenshot = self.take_screenshot(current_node)
            analysis = self.analyze_screen_with_ai(screenshot)
            
            # 3. Try each available action
            for action in analysis['suggested_actions']:
                # Execute action and capture result
                result = self.execute_exploratory_action(action)
                
                # If screen changed, create new node and edge
                if result['screen_changed']:
                    new_node = self.create_node_from_analysis(result)
                    self.create_edge_with_actions(current_node, new_node, action)
                    exploration_queue.append(new_node['id'])
                
                # Return to starting position
                self.return_to_position(current_node)
```

#### **Phase 3: Model Optimization (AI-Driven)**
```python
# AI optimizes the generated model:
# - Removes redundant nodes
# - Creates subtrees for complex menus  
# - Adds appropriate verifications
# - Generates meaningful labels
# - Validates pathfinding connectivity
```

### **Key AI Capabilities Required:**

1. **Visual Understanding**
   - Screenshot analysis for UI elements
   - Before/after comparison for state changes
   - Content vs navigation area detection

2. **Action Intelligence** 
   - Map visual elements to device commands
   - Determine return actions (OK→BACK, UP→DOWN)
   - Handle navigation dead ends and recovery

3. **Model Generation**
   - Create meaningful node labels from visual content
   - Generate bidirectional action sets
   - Decide when to create subtrees vs flat structure

### **Integration with Existing System:**

**Reuses Proven Infrastructure:**
- ✅ **useNode methods** - screenshot capture, node creation
- ✅ **useEdge methods** - action execution, validation
- ✅ **Device capabilities** - available commands from controller factory
- ✅ **Pathfinding system** - connectivity validation
- ✅ **AI Agent** - intelligent analysis and decision making

**Benefits:**
- ✅ **80-90% automation** - only Entry→Home needs manual setup
- ✅ **Leverages existing systems** - no new infrastructure required
- ✅ **Intelligent exploration** - AI understands UI patterns
- ✅ **Automatic optimization** - creates efficient, well-structured models

## 🔮 **Future Enhancements**

### **Planned Features**

1. **Enhanced Learning System**
   - Success pattern recognition from execution history
   - Automatic test case optimization suggestions
   - Cross-device adaptation learning

2. **Advanced Compatibility Analysis**
   - Automatic device adaptation generation
   - Smart fallback strategy suggestions
   - Performance impact analysis

3. **AI Model Generation**
   - Automated navigation model creation from device exploration
   - Visual UI analysis and intelligent action mapping
   - Cross-device model adaptation and optimization

4. **Integration Expansion**
   - CI/CD pipeline integration for automated testing
   - Test case scheduling and batch execution
   - Advanced reporting and analytics

### **Performance Optimizations**

1. **Capability Caching**
   - Cache device capabilities across sessions
   - Smart cache invalidation strategies
   - Distributed caching for multi-host setups

2. **AI Model Optimization**
   - Fine-tuned models for specific device types
   - Context-aware prompt optimization
   - Parallel analysis for multiple interfaces

3. **Exploration Efficiency**
   - Smart exploration prioritization
   - Duplicate state detection
   - Optimal return path calculation

---

## 📝 **Summary**

The AI Unified System consolidates real-time execution and test case generation into a single, powerful AI Agent. This approach:

- ✅ **Eliminates code duplication** - shared capability fetching, prompt construction, and execution logic
- ✅ **Provides superior analysis** - real AI model analysis vs heuristic keyword matching  
- ✅ **Maintains clear separation** - different use cases served by same underlying system
- ✅ **Enables powerful features** - cross-device compatibility, unified execution, consistent behavior
- ✅ **Simplifies maintenance** - one system to maintain, enhance, and debug

The unified system serves both interactive automation needs and persistent test case management while providing a foundation for advanced AI-powered testing capabilities.
