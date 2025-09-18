# AI Agent System Documentation

## Overview

The AI Agent system provides intelligent task automation for TV application navigation and control. It uses sophisticated AI models to understand natural language tasks and generate execution plans that combine navigation and controller actions.

## Architecture

### Core Components

1. **AIAgentController** (`backend_core/src/controllers/ai/ai_agent.py`)
   - Main AI agent logic and execution
   - Task planning and step execution
   - Navigation and action coordination

2. **AI Utils** (`shared/lib/utils/ai_utils.py`)
   - AI model configuration and API calls
   - Dedicated agent model for complex reasoning

3. **Frontend Hook** (`frontend/src/hooks/aiagent/useAIAgent.ts`)
   - React hook for AI agent interaction
   - Real-time execution monitoring
   - Toast notifications and progress tracking

## Key Features

### 1. **Consolidated Context System**

The AI agent uses two main context types:

- **Navigation Context**: Available navigation nodes from the current tree
- **Action Context**: Available controller commands (IR, Appium, etc.)

```python
# Example contexts provided to AI
navigation_context = "Navigation - Available nodes: ['node-1', 'node-2', ...]"
action_context = "Actions - Available commands: ['press_key', 'click_element', 'wait']"
```

### 2. **Current Node Tracking**

The system maintains current position state:

```python
class AIAgentController:
    def __init__(self):
        self.current_node_id = None  # Tracks current position
        
    def _execute_navigation(self, target_node):
        # Navigation from current position to target
        result = execute_navigation_with_verification(
            tree_id=self.cached_tree_id,
            target_node_id=target_node,
            current_node_id=self.current_node_id,  # Start from current position
            team_id=self.team_id
        )
        
        # Update position after successful navigation
        if result.get('success'):
            self.current_node_id = result.get('final_position_node_id')
```

### 3. **Reusable Navigation System**

Instead of duplicating navigation logic, the AI agent reuses existing proven systems:

- **NavigationExecutor** for pathfinding and execution
- **Controller Config Factory** for available actions
- **Frontend Action System** for command execution

## AI Model Configuration

### Model Selection

The system uses different models for different tasks:

```python
# In ai_utils.py
'models': {
    'text': 'microsoft/phi-3-mini-128k-instruct',        # Basic text tasks
    'vision': 'qwen/qwen-2.5-vl-7b-instruct',           # Image analysis
    'translation': 'microsoft/phi-3-mini-128k-instruct', # Text translation
    'agent': 'meta-llama/llama-3.1-8b-instruct:free'    # AI agent reasoning
}
```

### Temperature Settings

- **Temperature = 0.0** for AI agent tasks
- Ensures deterministic, consistent JSON responses
- Reliable command generation without creative variations

## Task Execution Flow

### 1. **Task Planning**

```python
def execute_task(self, task_description: str) -> Dict[str, Any]:
    # 1. Get contexts
    navigation_context = self._get_navigation_context(available_nodes)
    action_context = self._get_action_context()
    
    # 2. Generate AI plan
    ai_response = call_text_ai(prompt, model=agent_model)
    
    # 3. Execute plan steps
    for step in ai_plan['plan']:
        if step['command'] == 'execute_navigation':
            result = self._execute_navigation(target_node)
        elif step['command'] in ['press_key', 'click_element', 'wait']:
            result = self._execute_action(command, params)
```

### 2. **Step Execution Types**

| Command Type | Handler | Description |
|--------------|---------|-------------|
| `execute_navigation` | `_execute_navigation()` | Navigate between screens/nodes |
| `press_key` | `_execute_action()` | Remote control key press |
| `click_element` | `_execute_action()` | UI element interaction |
| `wait` | `_execute_action()` | Pause execution |

### 3. **Action Delegation**

Controller actions are delegated to the frontend for execution:

```python
def _execute_action(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute controller action - delegate to frontend action system"""
    return {
        'success': True, 
        'action_type': 'controller_action',
        'command': command,
        'params': params,
        'message': f'Action {command} queued for frontend execution'
    }
```

## Frontend Integration

### useAIAgent Hook

The React hook provides:

- Task execution with real-time progress
- Execution log monitoring
- Toast notifications for step completion
- Error handling and retry logic

```typescript
const { executeTask, isExecuting, executionLog, taskResult } = useAIAgent({
  selectedHost,
  selectedDeviceId
});

// Execute AI task
await executeTask("go to live channel and check audio");
```

### Completion Toast Management

Uses a ref-based system to prevent duplicate notifications:

```typescript
const completionToastShown = useRef(false);

// Reset for new tasks
completionToastShown.current = false;

// Show toast only once per task
if (!completionToastShown.current) {
  toast.showSuccess(`🎉 Task completed in ${duration}s`);
  completionToastShown.current = true;
}
```

## Node Validation

### Strict Node Validation

The system prevents AI from generating invalid navigation targets:

```python
# Simple validation before execution
if target_node not in available_nodes:
    return {
        'success': False, 
        'error': f'Target node {target_node} not found. Available: {available_nodes}'
    }
```

### AI Prompt Rules

The AI is explicitly instructed to use only exact node IDs:

```
CRITICAL RULES:
- You MUST ONLY use nodes from the available list above
- For execute_navigation, target_node MUST be one of the exact node IDs listed
- DO NOT create or assume node names like "home", "live" - use only provided node IDs
```

## Error Handling

### Execution Errors

- **Navigation errors**: Invalid nodes, pathfinding failures
- **Action errors**: Controller communication issues
- **AI errors**: Invalid JSON responses, model failures

### Recovery Mechanisms

- Automatic retry for transient failures
- Clear error messages with available options
- Graceful degradation when components unavailable

## Best Practices

### 1. **Minimal Code Changes**

- Reuse existing navigation and action systems
- Avoid duplicating proven logic
- Leverage established patterns and infrastructure

### 2. **Clean Architecture**

- Separate concerns: planning vs execution
- Use dependency injection for testability
- Maintain single responsibility principle

### 3. **Robust Error Handling**

- Validate inputs before execution
- Provide clear error messages
- Implement proper fallback mechanisms

## Configuration

### Environment Variables

```bash
# AI model configuration
AI_PROVIDER=openrouter
AI_MODEL_AGENT=meta-llama/llama-3.1-8b-instruct:free

# Navigation settings
NAVIGATION_CACHE_TTL=3600
DEFAULT_USERINTERFACE=horizon_android_mobile
```

### Device Support

The AI agent works with any device that has:

- Navigation tree configuration
- Controller action definitions
- Host connectivity

## Troubleshooting

### Common Issues

1. **"Target node not found"**
   - Check navigation tree is loaded
   - Verify node IDs in available_nodes list
   - Ensure tree_id is cached properly

2. **"No controller actions available"**
   - Verify device configuration in controller factory
   - Check device_id parameter is correct
   - Ensure controller is properly initialized

3. **AI generates invalid JSON**
   - Check AI model configuration
   - Verify prompt format and rules
   - Consider increasing max_tokens if response truncated

### Debug Logging

Enable detailed logging:

```python
# In AI agent execution
print(f"AI[{self.device_name}]: {navigation_context}")
print(f"AI[{self.device_name}]: {action_context}")
print(f"AI[{self.device_name}]: Current position: {self.current_node_id}")
```

## Future Enhancements

### Planned Features

- **Multi-device coordination**: Execute tasks across multiple devices
- **Learning system**: Improve plans based on execution success
- **Visual verification**: Use computer vision for step validation
- **Voice control**: Natural language task input via speech

### Performance Optimizations

- **Context caching**: Cache navigation and action contexts
- **Parallel execution**: Execute independent steps simultaneously
- **Predictive loading**: Pre-load likely navigation targets
