# AI Agent Code Flow - Exact File Locations

## 🚀 **Complete Workflow with File Locations**

### **1. Entry Point: Host Route**
**File**: `backend_host/src/routes/host_aiagent_routes.py`
```python
@host_aiagent_bp.route('/executeTask', methods=['POST'])
def execute_task():  # Line 14
    """Execute AI task using AI agent controller."""
    
    # Get request data
    data = request.get_json() or {}
    device_id = data.get('device_id', 'device1')  # Line 19
    task_description = data.get('task_description', '')  # Line 20
    
    # Get AI controller instance
    ai_controller = get_controller(device_id, 'ai')  # Line 26
    
    # Get device capabilities
    device = get_device_by_id(device_id)  # Line 45
    device_action_types = device.get_available_action_types()  # Line 56
```

### **2. Action Collection & Enhancement**
**File**: `backend_host/src/routes/host_aiagent_routes.py` (Lines 59-136)
```python
# Enhanced action flattening with better AI context
for category, actions in device_action_types.items():  # Line 60
    if isinstance(actions, list):
        for action in actions:
            # Build enhanced action description for AI
            base_command = action.get('command', '')  # Line 64
            
            # Enhance specific actions with common user task mappings
            if base_command == 'press_key' and base_params.get('key') == 'BACK':  # Line 73
                ai_action_name = "go_back_button"
                ai_description = "Go back to previous screen..."
                
            elif base_command == 'click_element':  # Line 85
                ai_action_name = "click_ui_element"
                ai_description = "Click on UI element by text/ID..."
            
            # Build comprehensive action context for AI
            ai_action = {  # Line 102
                'command': base_command,
                'ai_name': ai_action_name,
                'description': ai_description,
                'params': base_params,
                'category': category
            }
            available_actions.append(ai_action)  # Line 136
```

### **3. AI Agent Controller Execution**
**File**: `backend_core/src/controllers/ai/ai_agent.py`
```python
def execute_task(self, task_description, available_actions, available_verifications, 
                device_model=None, userinterface_name="horizon_android_mobile"):  # Line 401
    """Execute a task: generate plan with AI, execute it, and summarize results."""
    
    print(f"AI[{self.device_name}]: Starting task: {task_description}")  # Line 413
    
    # Load navigation tree only when needed
    navigation_tree = self._get_navigation_tree(userinterface_name)  # Line 420
    
    # Step 1: Generate plan using AI
    ai_plan = self._generate_plan(task_description, available_actions, 
                                 available_verifications, device_model, navigation_tree)  # Line 423
    
    # Step 2: Execute the plan
    execute_result = self._execute(ai_plan['plan'], navigation_tree, userinterface_name)  # Line 436
    
    # Step 3: Generate result summary
    summary_result = self._result_summary(ai_plan['plan'], execute_result)  # Line 441
```

### **4. Navigation Tree Loading**
**File**: `backend_core/src/controllers/ai/ai_agent.py` (Lines 35-80)
```python
def _get_navigation_tree(self, userinterface_name: str) -> Dict[str, Any]:  # Line 35
    """Get navigation tree using unified hierarchy loading."""
    
    # Check if already cached
    if userinterface_name in self._navigation_trees_cache:  # Line 46
        return self._navigation_trees_cache[userinterface_name]
    
    try:
        # Load tree lazily with unified hierarchy support
        from shared.lib.utils.navigation_utils import load_navigation_tree_with_hierarchy  # Line 53
        
        tree_result = load_navigation_tree_with_hierarchy(userinterface_name, "ai_agent")  # Line 57
        
        if tree_result.get('success'):
            # Cache the root tree data
            root_tree = tree_result.get('root_tree', {})  # Line 61
            self._navigation_trees_cache[userinterface_name] = root_tree.get('tree')  # Line 62
            print(f"AI[{self.device_name}]: Unified cache populated with {tree_result.get('unified_graph_nodes', 0)} nodes")  # Line 64
```

### **5. AI Prompt Generation**
**File**: `backend_core/src/controllers/ai/ai_agent.py` (Lines 467-646)
```python
def _generate_plan(self, task_description, available_actions, available_verifications, 
                  device_model=None, navigation_tree=None):  # Line 467
    """Generate execution plan using AI API."""
    
    # Build simple action list - let AI figure out what to use
    action_context = "\n".join([  # Line 533
        f"- {action.get('command', action)} (params: {action.get('params', {})}): {action.get('description', 'No description')}"
        for action in available_actions
    ])
    
    # Add navigation context if tree is available
    navigation_context = ""
    if navigation_tree:  # Line 540
        navigation_context = """
- execute_navigation (params: {"target_node": "node_name"}): Navigate to a specific node in the navigation tree"""
    
    # THE MASSIVE PROMPT STARTS HERE
    prompt = f"""You are a device automation AI for {device_model}. Analyze if this task is feasible with available actions.

Task: "{task_description}"
Device: {device_model}
Navigation Tree Available: {context['has_navigation_tree']}

Available Actions:
{action_context}{navigation_context}

FEASIBILITY FOCUS: Determine if this task CAN be completed with available actions...

CRITICAL COMMAND DISTINCTIONS:

NAVIGATION COMMANDS (use execute_navigation):
- "goto X", "go to X", "navigate to X", "navigate X" = NAVIGATE to location/screen X in the app
- Examples: "goto home", "go to home", "navigate to settings", "navigate home"
- These move between screens/pages within the application using the navigation tree

INTERACTION COMMANDS (use click_element):
- "click X", "tap X", "select X" = INTERACT with UI element X
- Examples: "click home_button", "tap settings", "select menu"
- These interact with visible UI elements on the current screen

SYSTEM COMMANDS (use press_key):
- "go back", "go home" (without "to") = SYSTEM-level actions
- "go back" = Android back button → press_key with key="BACK"
- "go home" = Android home screen → press_key with key="HOME"
- "press up", "press down" = Directional keys → press_key with key="UP"/"DOWN"

IMPORTANT EXAMPLES:
- "goto home" → execute_navigation with target_node="home" (navigate within app)
- "go to home" → execute_navigation with target_node="home" (navigate within app)  
- "navigate to settings" → execute_navigation with target_node="settings" (navigate within app)
- "go home" → press_key with key="HOME" (Android home screen)
- "go back" → press_key with key="BACK" (Android back button)
- "click home_replay" → click_element with element_id="home_replay" (interact with element)
- "press up arrow" → press_key with key="UP" (directional navigation)

The available actions are TEMPLATES - you fill in the parameter values based on what the task asks for.

CRITICAL: Respond with ONLY valid JSON. No other text.

Required JSON format for navigation:
{{
  "analysis": "brief analysis of the task and chosen approach",
  "feasible": true,
  "plan": [
    {{
      "step": 1,
      "type": "action",
      "command": "execute_navigation",
      "params": {{"target_node": "home"}},
      "description": "Navigate to the home location within the app"
    }}
  ]
}}

[... MORE JSON EXAMPLES ...]

JSON ONLY - NO OTHER TEXT"""  # Line 646
```

### **6. AI Service Call**
**File**: `backend_core/src/controllers/ai/ai_agent.py` (Lines 648-655)
```python
# Call centralized AI utilities with automatic provider fallback
print(f"AI[{self.device_name}]: Making AI call with automatic provider fallback")  # Line 649

result = call_text_ai(  # Line 651
    prompt=prompt,
    max_tokens=1000,
    temperature=0.0
)
```

**File**: `shared/lib/utils/ai_utils.py` (Lines 76-78)
```python
def call_text_ai(prompt: str, max_tokens: int = 200, temperature: float = 0.1) -> Dict[str, Any]:  # Line 76
    """Simple text AI call with OpenRouter (primary) and Hugging Face (fallback)."""
    return _call_ai(prompt, task_type='text', max_tokens=max_tokens, temperature=temperature)  # Line 78
```

**File**: `shared/lib/utils/ai_utils.py` (Lines 84-96)
```python
def _call_ai(prompt: str, task_type: str = 'text', image=None, max_tokens=None, temperature=None):  # Line 84
    """Centralized AI call with automatic provider fallback."""
    
    # Try OpenRouter first
    try:
        model = AI_CONFIG['providers']['openrouter']['models'].get(task_type)  # Line 95
        # model = 'microsoft/phi-3-mini-128k-instruct'
```

### **7. AI Response Processing**
**File**: `backend_core/src/controllers/ai/ai_agent.py` (Lines 657-685)
```python
if result['success']:  # Line 657
    content = result['content']
    provider_used = result.get('provider_used', 'unknown')
    print(f"AI[{self.device_name}]: AI call successful using {provider_used}")  # Line 660
    
    # Parse JSON response
    try:
        # Clean up markdown code blocks
        json_content = content.strip()  # Line 665
        if json_content.startswith('```json'):
            json_content = json_content.replace('```json', '').replace('```', '').strip()
        
        ai_plan = json.loads(json_content)  # Line 671
        print(f"AI[{self.device_name}]: AI plan generated successfully")  # Line 672
        
    except json.JSONDecodeError as e:  # Line 678
        print(f"AI[{self.device_name}]: Failed to parse AI JSON: {e}")  # Line 679
        print(f"AI[{self.device_name}]: Raw AI response: {content[:200]}...")  # Line 680
        print(f"AI[{self.device_name}]: Cleaned content: {json_content[:200]}...")  # Line 681
```

### **8. Plan Execution**
**File**: `backend_core/src/controllers/ai/ai_agent.py` (Lines 702-787)
```python
def _execute(self, plan, navigation_tree=None, userinterface_name="horizon_android_mobile"):  # Line 702
    """Execute the AI plan."""
    
    plan_steps = plan.get('plan', [])  # Line 720
    
    # Separate actions and verifications
    action_steps = [step for step in plan_steps if step.get('type') == 'action']  # Line 733
    verification_steps = [step for step in plan_steps if step.get('type') == 'verification']  # Line 734
    
    # Execute actions first
    if action_steps:
        action_result = self._execute_actions(action_steps, navigation_tree, userinterface_name)  # Line 741
```

### **9. Action Execution**
**File**: `backend_core/src/controllers/ai/ai_agent.py` (Lines 789-850)
```python
def _execute_actions(self, action_steps, navigation_tree=None, userinterface_name="horizon_android_mobile"):  # Line 789
    """Execute action steps using direct controller access."""
    
    # Get remote controller for this device
    remote_controller = get_controller(self.device_id, 'remote')  # Line 802
    
    for i, step in enumerate(action_steps):  # Line 818
        command = step.get('command', '')  # Line 820
        params = step.get('params', {})  # Line 821
        
        if command == "execute_navigation":  # Line 827
            target_node = params.get("target_node")  # Line 828
            result = self._execute_navigation(target_node, userinterface_name)  # Line 829
        else:
            success = remote_controller.execute_command(command, params)  # Line 833
```

### **10. Navigation Execution**
**File**: `backend_core/src/controllers/ai/ai_agent.py` (Lines 117-139)
```python
def _execute_navigation(self, target_node: str, userinterface_name: str = "horizon_android_mobile"):  # Line 79
    """Execute navigation by doing exactly what validation.py does."""
    
    # Load navigation tree with unified hierarchy support
    tree_result = load_navigation_tree_with_hierarchy(userinterface_name, "ai_agent")  # Line 126
    
    tree_id = tree_result['tree_id']  # Line 130
    
    # Get navigation sequence using pathfinding
    from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path  # Line 141
    
    path_sequence = find_shortest_path(tree_id, target_node, team_id)  # Line 143
    
    # Execute navigation sequence
    for transition in path_sequence:  # Line 149
        # Execute actions for this transition
        execute_navigation_with_verifications(...)
```

## 🔍 **Key Configuration Files**

### **AI Model Configuration**
**File**: `shared/lib/utils/ai_utils.py` (Lines 21-46)
```python
AI_CONFIG = {
    'providers': {
        'openrouter': {
            'models': {
                'text': 'microsoft/phi-3-mini-128k-instruct',  # Line 31 - THE MODEL USED
                'vision': 'qwen/qwen-2.5-vl-7b-instruct',
                'translation': 'microsoft/phi-3-mini-128k-instruct'
            }
        },
        'huggingface': {
            'models': {
                'text': 'microsoft/DialoGPT-medium',  # Line 41 - FALLBACK MODEL
            }
        }
    }
}
```

### **Navigation Tree Loading**
**File**: `shared/lib/utils/navigation_utils.py` (Lines 98-165)
```python
def load_navigation_tree_with_hierarchy(userinterface_name: str, script_name: str = "script"):  # Line 98
    """Load complete navigation tree hierarchy and populate unified cache."""
    
    # 1. Load root tree
    root_tree_result = load_navigation_tree(userinterface_name, script_name)  # Line 117
    
    # 2. Discover complete tree hierarchy
    hierarchy_data = discover_complete_hierarchy(root_tree_id, team_id, script_name)  # Line 127
    
    # 3. Build unified tree data structure
    all_trees_data = build_unified_tree_data(hierarchy_data, script_name)  # Line 136
    
    # 4. Populate unified cache (MANDATORY)
    unified_graph = populate_unified_cache(root_tree_id, team_id, all_trees_data)  # Line 142
```

## 🚨 **The Problem Location**

**The massive confusing prompt is generated at:**
- **File**: `backend_core/src/controllers/ai/ai_agent.py`
- **Lines**: 544-646 (102 lines of complex prompt)
- **Function**: `_generate_plan()`

**The AI model that gets confused:**
- **File**: `shared/lib/utils/ai_utils.py`
- **Line**: 31
- **Model**: `microsoft/phi-3-mini-128k-instruct` (small model, gets overwhelmed)

**The JSON parsing that fails:**
- **File**: `backend_core/src/controllers/ai/ai_agent.py`
- **Lines**: 678-685
- **Issue**: AI returns text instead of JSON due to prompt complexity

This is exactly where the fix needs to be applied - simplifying the prompt in the `_generate_plan()` method.
