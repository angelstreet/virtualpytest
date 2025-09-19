# AI Agent System - New Architecture

## Overview

The AI Agent System has been completely refactored to use a clean service-oriented architecture where the AI asks each service to provide context based on device model and user interface, rather than directly accessing controllers.

## Architecture Principles

### 1. **Clean Separation of Concerns**
- **AI Central**: Focuses purely on AI logic and plan generation
- **Service Executors**: Handle domain-specific context loading and execution
- **Controllers**: Remain focused on device interaction

### 2. **Service-Oriented Context Loading**
- AI asks services for context instead of loading directly from controllers
- Each service provides structured context with descriptions
- Consistent interface across all services

### 3. **Dynamic Action Type Detection**
- No hardcoded command mappings
- Action types detected by querying actual device controllers
- Supports device-specific capabilities

## System Components

### AI Central (`shared/lib/utils/ai_central.py`)

**Core Responsibilities:**
- Generate AI plans based on user prompts
- Load context from service executors
- Execute plans using appropriate executors
- Provide minimal, relevant context to AI to avoid hallucinations

**Key Methods:**
- `generate_plan(prompt, userinterface_name, device_id)`: Main entry point
- `_load_context()`: Asks services for available context
- `_call_ai()`: Sends minimal context to AI with command descriptions
- `execute_task()`: Executes generated plans

### Service Executors

#### ActionExecutor (`backend_core/src/services/actions/action_executor.py`)

**Responsibilities:**
- Provide available action context for AI
- Execute action sequences with retry logic
- Dynamic action type detection based on device controllers

**Key Methods:**
- `get_available_context(device_model, userinterface_name)`: Returns available actions with descriptions
- `execute_actions(actions, retry_actions, failure_actions)`: Execute action sequences
- `_detect_action_type_from_device(command)`: Dynamically detect action type from device controllers

#### VerificationExecutor (`backend_core/src/services/verifications/verification_executor.py`)

**Responsibilities:**
- Provide available verification context for AI
- Execute verification sequences
- Support multiple verification types (image, text, adb, appium, video, audio)

**Key Methods:**
- `get_available_context(device_model, userinterface_name)`: Returns available verifications with descriptions
- `execute_verifications(verifications, image_source_url)`: Execute verification sequences

#### NavigationExecutor (`backend_core/src/services/navigation/navigation_executor.py`)

**Responsibilities:**
- Provide available navigation context for AI
- Execute navigation between nodes
- Manage navigation trees and pathfinding

**Key Methods:**
- `get_available_context(device_model, userinterface_name)`: Returns available navigation nodes
- `execute_navigation(tree_id, target_node_id, current_node_id)`: Execute navigation sequences

## Full Workflow

### 1. **Plan Generation Request**

```
Frontend → Server → Host → AI Central
POST /host/aiagent/executeTask
{
  "prompt": "Navigate to home and click replay",
  "userinterface_name": "horizon_android_mobile",
  "device_id": "device1"
}
```

### 2. **Context Loading Phase**

AI Central asks each service for context:

```python
# AI Central loads context from services
action_context = action_executor.get_available_context(device_model, userinterface_name)
verification_context = verification_executor.get_available_context(device_model, userinterface_name)
navigation_context = navigation_executor.get_available_context(device_model, userinterface_name)
```

**ActionExecutor Context Loading:**
```python
# Queries device controllers dynamically
controller_types = ['remote', 'web', 'desktop_bash', 'desktop_pyautogui', 'av', 'power']
for controller_type in controller_types:
    controller = get_controller(device_id, controller_type)
    actions = controller.get_available_actions()
    # Extract commands with descriptions
```

**VerificationExecutor Context Loading:**
```python
# Queries verification controllers
verification_types = ['image', 'text', 'adb', 'appium', 'video', 'audio']
for v_type in verification_types:
    controller = get_controller(device_id, f'verification_{v_type}')
    verifications = controller.get_available_verifications()
    # Extract verification commands with descriptions
```

**NavigationExecutor Context Loading:**
```python
# Loads navigation tree for user interface
root_tree = get_root_tree_for_interface(userinterface_name, team_id)
G = get_cached_graph(tree_id, team_id)
available_nodes = get_all_nodes(G)
```

### 3. **AI Prompt Generation**

AI Central creates a minimal prompt with context:

```
Task: "Navigate to home and click replay"

Available nodes: ['home', 'replay', 'settings', 'live']
Available commands: 
- click_element(remote): Click UI element
- press_key(remote): Press keyboard key
- execute_navigation(navigation): Navigate to specific node
- waitForImageToAppear(verification_image): Wait for image to appear on screen
- waitForTextToAppear(verification_text): Wait for text to appear on screen using OCR

Rules:
- "navigate to X" → execute_navigation, target_node="X"
- Use commands with their specified controller type
- ALWAYS specify action_type in params matching the controller

Response format:
{"analysis": "reasoning", "feasible": true/false, "plan": [{"step": 1, "command": "execute_navigation", "params": {"target_node": "home", "action_type": "navigation"}, "description": "Navigate to home"}]}
```

### 4. **AI Response Processing**

AI Central converts AI response to structured plan:

```python
# Convert AI response to AIPlan object
steps = []
for step_data in ai_response.get('plan', []):
    steps.append(AIStep(
        step_id=i + 1,
        type=self._get_step_type(step_data.get('command')),
        command=step_data.get('command'),
        params=step_data.get('params', {}),
        description=step_data.get('description', '')
    ))
```

### 5. **Plan Execution**

AI Central executes each step using appropriate executor:

```python
def _execute_action(self, step: AIStep) -> Dict[str, Any]:
    if step.type == 'navigation':
        # Use NavigationExecutor
        return self.navigation_executor.execute_navigation(...)
    elif step.type == 'verification':
        # Use VerificationExecutor  
        return self.verification_executor.execute_verifications(...)
    else:
        # Use ActionExecutor
        return self.action_executor.execute_actions(...)
```

### 6. **Dynamic Action Type Detection**

When executing actions, ActionExecutor dynamically detects action types:

```python
def _detect_action_type_from_device(self, command: str) -> str:
    # Check each controller type in priority order
    for controller_type in ['remote', 'web', 'desktop', 'av', 'power']:
        controller = get_controller(self.device_id, controller_type)
        if controller and self._command_exists_in_actions(command, controller.get_available_actions()):
            return controller_type
    
    # Check verification controllers
    for v_type in ['image', 'text', 'adb', 'appium', 'video', 'audio']:
        controller = get_controller(self.device_id, f'verification_{v_type}')
        if controller and self._command_exists_in_actions(command, controller.get_available_verifications()):
            return f'verification_{v_type}'
    
    return 'remote'  # Default fallback
```

### 7. **Execution Results**

Results flow back through the chain:

```
ActionExecutor → AI Central → Host → Server → Frontend
{
  "success": true,
  "results": [...],
  "message": "Plan executed successfully"
}
```

## Key Improvements

### 1. **No Hardcoded Mappings**
- Old: Hardcoded `web_commands = {'click_element', 'type_text'}`
- New: Dynamic detection by querying actual device controllers

### 2. **Service-Oriented Architecture**
- Old: AI directly accessed controllers
- New: AI asks services for context, services handle controller interaction

### 3. **Consistent Context Interface**
- All services provide `get_available_context(device_model, userinterface_name)`
- Standardized context format with descriptions

### 4. **Enhanced Action Descriptions**
- Controllers provide 1-line descriptions for each command
- AI receives context like `click_element(remote): Click UI element`
- Reduces AI hallucinations by providing clear command purposes

### 5. **Device-Aware Context**
- Context loading considers device model and capabilities
- Only available controllers are queried for actions
- Mobile devices won't see web actions if Playwright isn't available

## Error Handling

### 1. **Graceful Degradation**
- If a controller fails to load, system continues with available controllers
- Fallback to basic functionality if context loading fails

### 2. **Action Type Fallbacks**
- If dynamic detection fails, defaults to 'remote' action type
- Prevents system crashes from missing controllers

### 3. **Service Isolation**
- Failures in one service don't affect others
- Each service handles its own error cases

## Configuration

### AI Model Configuration
```python
AI_CONFIG = {
    'providers': {
        'openrouter': {
            'models': {
                'agent': 'anthropic/claude-3.5-sonnet'  # AI model for plan generation
            }
        }
    }
}
```

### Context Limits
- Maximum 20 commands shown to AI to avoid token overflow
- Commands prioritized by controller type (remote, web, desktop, etc.)

## Monitoring and Logging

### Context Loading
```
[@ai_central] Loading context from services for interface: horizon_android_mobile, device: device1
[@action_executor] Loading action context for device: device1, model: android_mobile
[@verification_executor] Loading verification context for device: device1, model: android_mobile
[@navigation_executor] Loading navigation context for interface: horizon_android_mobile
```

### Execution Tracking
```
[@ai_central] Loaded context from services:
  - Actions: 15
  - Verifications: 12
  - Navigation nodes: 8
[@action_executor] Detected action_type: remote
[@action_executor] Action 1 result: success=true, time=142ms
```

## Future Enhancements

### 1. **Context Caching**
- Cache service contexts to avoid repeated controller queries
- Invalidate cache when device capabilities change

### 2. **Smart Context Filtering**
- Filter actions based on current UI state
- Show only relevant commands for current context

### 3. **Learning from Execution**
- Track successful action patterns
- Improve context relevance based on execution history

### 4. **Multi-Device Context**
- Support context loading for multiple devices
- Cross-device action coordination

## Conclusion

The new AI architecture provides a clean, maintainable, and extensible foundation for AI-driven automation. By separating concerns and using service-oriented context loading, the system is more robust, easier to debug, and capable of handling diverse device types and capabilities.
