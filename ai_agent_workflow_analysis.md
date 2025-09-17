# AI Agent Workflow Analysis

## Complete AI Agent Workflow

### 1. **Task Initiation** 
```
User Request: "go to node home_tvguide"
↓
Host Route: /host/aiagent/executeTask
↓
AIAgentController.execute_task()
```

### 2. **Navigation Tree Loading**
```python
# Step 1: Load unified navigation tree
navigation_tree = self._get_navigation_tree(userinterface_name)

# This calls load_navigation_tree_with_hierarchy() which:
# - Loads root tree: bbf2d95d-72c2-4701-80a7-0b9d131a5c38
# - Discovers 4 trees in hierarchy (root + 3 subtrees)
# - Populates unified cache with 17 nodes, 27 edges
# - Returns tree data for AI context
```

### 3. **Available Actions Collection**
```python
# From host_aiagent_routes.py - device capabilities are collected:
device_action_types = device.get_available_action_types()

# Example actions available:
available_actions = [
    {
        'command': 'press_key',
        'ai_name': 'go_back_button', 
        'description': 'Go back to previous screen',
        'params': {'key': 'BACK'}
    },
    {
        'command': 'click_element',
        'ai_name': 'click_ui_element',
        'description': 'Click on UI element by text/ID',
        'params': {'element_id': 'string'}
    },
    {
        'command': 'tap_coordinates',
        'ai_name': 'tap_screen_coordinates', 
        'description': 'Tap at specific screen coordinates',
        'params': {'x': 'number', 'y': 'number'}
    },
    # ... 15 total actions
]
```

### 4. **AI Prompt Generation**
```python
def _generate_plan(self, task_description, available_actions, available_verifications, device_model, navigation_tree):
    # Build action context string
    action_context = "\n".join([
        f"- {action.get('command', action)} (params: {action.get('params', {})}): {action.get('description', 'No description')}"
        for action in available_actions
    ])
    
    # Add navigation context if tree available
    navigation_context = """
- execute_navigation (params: {"target_node": "node_name"}): Navigate to a specific node in the navigation tree"""
    
    # Generate the massive prompt (lines 544-646)
```

## **THE ACTUAL PROMPT SENT TO AI**

```
You are a device automation AI for android_mobile. Analyze if this task is feasible with available actions.

Task: "go to node home_tvguide"
Device: android_mobile
Navigation Tree Available: True

Available Actions:
- press_key (params: {'key': 'BACK', 'wait_time': 1000}): Go back to previous screen (use for: 'go back', 'navigate back', 'return to previous page')
- press_key (params: {'key': 'HOME', 'wait_time': 1000}): Go to home screen (use for: 'go home', 'navigate to home', 'return to home')
- press_key (params: {'key': 'UP', 'wait_time': 500}): Press UP directional key
- press_key (params: {'key': 'DOWN', 'wait_time': 500}): Press DOWN directional key
- press_key (params: {'key': 'LEFT', 'wait_time': 500}): Press LEFT directional key
- press_key (params: {'key': 'RIGHT', 'wait_time': 500}): Press RIGHT directional key
- press_key (params: {'key': 'ENTER', 'wait_time': 500}): Press ENTER/OK key
- press_key (params: {'key': 'VOLUME_UP', 'wait_time': 300}): Press volume up key
- press_key (params: {'key': 'VOLUME_DOWN', 'wait_time': 300}): Press volume down key
- click_element (params: {'element_id': 'string', 'wait_time': 1000}): Click on UI element by text/ID (use for: 'click [element]', 'tap [element]', 'select [item]')
- tap_coordinates (params: {'x': 'number', 'y': 'number', 'wait_time': 1000}): Tap at specific screen coordinates (use for: 'tap at position', 'click coordinates')
- swipe_up (params: {'from_y': 'number', 'wait_time': 1000}): Swipe up gesture
- swipe_down (params: {'wait_time': 1000}): Swipe down gesture
- launch_app (params: {'package': 'com.lgi.upcch.prod', 'wait_time': 6000}): Launch/open an Android application (use for: 'open app', 'start app', 'launch')
- close_app (params: {'package': 'com.lgi.upcch.prod', 'wait_time': 2000}): Close/stop an Android application (use for: 'close app', 'stop app', 'exit app')
- execute_navigation (params: {"target_node": "node_name"}): Navigate to a specific node in the navigation tree

FEASIBILITY FOCUS: Determine if this task CAN be completed with available actions. Be optimistic - if there's a reasonable way to accomplish the task, mark it as feasible.

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
{
  "analysis": "brief analysis of the task and chosen approach",
  "feasible": true,
  "plan": [
    {
      "step": 1,
      "type": "action",
      "command": "execute_navigation",
      "params": {"target_node": "home"},
      "description": "Navigate to the home location within the app"
    }
  ]
}

Required JSON format for interaction:
{
  "analysis": "brief analysis of the task and chosen approach",
  "feasible": true,
  "plan": [
    {
      "step": 1,
      "type": "action",
      "command": "click_element",
      "params": {"element_id": "home_replay"},
      "description": "Click on the home_replay element"
    }
  ]
}

Required JSON format for system commands:
{
  "analysis": "brief analysis of the task and chosen approach",
  "feasible": true,
  "plan": [
    {
      "step": 1,
      "type": "action",
      "command": "press_key",
      "params": {"key": "HOME"},
      "description": "Press Android home button to go to home screen"
    }
  ]
}

For tasks that cannot be completed with available actions, return:
{
  "analysis": "explanation of why task cannot be completed",
  "feasible": false,
  "plan": []
}

If coordinates needed but not provided:
{
  "analysis": "task requires coordinates",
  "feasible": false,
  "plan": [],
  "needs_input": "Please provide x,y coordinates"
}

JSON ONLY - NO OTHER TEXT
```

## **5. AI Response Processing**

### What Should Happen:
```json
{
  "analysis": "Task requests navigation to home_tvguide node using navigation tree",
  "feasible": true,
  "plan": [
    {
      "step": 1,
      "type": "action", 
      "command": "execute_navigation",
      "params": {"target_node": "home_tvguide"},
      "description": "Navigate to the home_tvguide location within the app"
    }
  ]
}
```

### What Actually Happens (from logs):
```
AI Response: "Given the task 'go to live,' it's not entirely clear what exactly needs to be done..."
```

**PROBLEM**: The AI model is:
1. **Hallucinating** - thinks task is "go to live" instead of "go to node home_tvguide"
2. **Returning text instead of JSON** - ignoring the JSON-only instruction
3. **Getting confused by the complex prompt** - too many examples and distinctions

## **6. Plan Execution Flow**

When AI does generate a valid plan:

```python
# _execute() method processes the plan
def _execute(self, plan, navigation_tree, userinterface_name):
    plan_steps = plan.get('plan', [])
    
    # Separate actions and verifications
    action_steps = [step for step in plan_steps if step.get('type') == 'action']
    verification_steps = [step for step in plan_steps if step.get('type') == 'verification']
    
    # Execute actions first
    action_result = self._execute_actions(action_steps, navigation_tree, userinterface_name)
    
    # Execute verifications second  
    verification_result = self._execute_verifications(plan)
```

### Action Execution:
```python
def _execute_actions(self, action_steps, navigation_tree, userinterface_name):
    for step in action_steps:
        command = step.get('command', '')
        params = step.get('params', {})
        
        if command == "execute_navigation":
            target_node = params.get("target_node")
            result = self._execute_navigation(target_node, userinterface_name)
        else:
            # Use remote controller for other commands
            success = remote_controller.execute_command(command, params)
```

### Navigation Execution:
```python
def _execute_navigation(self, target_node, userinterface_name):
    # Load unified navigation tree
    tree_result = load_navigation_tree_with_hierarchy(userinterface_name, "ai_agent")
    
    # Find path using unified pathfinding
    path_sequence = find_shortest_path(tree_id, target_node, team_id)
    
    # Execute each transition in the path
    for transition in path_sequence:
        # Execute actions for this transition
        execute_navigation_with_verifications(...)
```

## **The Core Problems**

### 1. **Prompt Complexity**
- **Too many examples** confuse the small AI model (microsoft/phi-3-mini-128k-instruct)
- **Contradictory instructions** about "goto home" vs "go home"
- **Missing navigation context** - doesn't tell AI what nodes exist

### 2. **AI Model Limitations**
- **Small model gets overwhelmed** by complex prompts
- **Hallucinates task content** - sees "go to live" instead of actual task
- **Ignores JSON format** - returns text explanations

### 3. **Missing Navigation Context**
- **No available nodes listed** - AI doesn't know "home_tvguide" exists
- **No path information** - AI doesn't understand navigation structure
- **Generic navigation instruction** - doesn't explain the specific navigation tree

## **The Solution**

The prompt needs to be **dramatically simplified** and **more specific**:

1. **Reduce complexity** - remove confusing examples
2. **Add navigation nodes** - list available nodes from the tree
3. **Simplify JSON format** - make it clearer and more direct
4. **Focus on the task** - "go to node X" = execute_navigation with target_node="X"

### Recommended Simplified Prompt:
```
Task: "go to node home_tvguide"
Device: android_mobile

Available Navigation Nodes: home, home_tvguide, home_movies, home_replay, home_saved, live, live_fullscreen, tvguide_livetv

For "go to node X" tasks, use execute_navigation with target_node="X".

Respond with JSON only:
{
  "feasible": true,
  "plan": [{"step": 1, "type": "action", "command": "execute_navigation", "params": {"target_node": "home_tvguide"}, "description": "Navigate to home_tvguide"}]
}
```

This would be **much clearer** and **less confusing** for the AI model.
