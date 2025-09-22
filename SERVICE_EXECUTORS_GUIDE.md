# Service Executors Usage Guide

This guide explains how to properly use each service executor in the VirtualPyTest architecture.

## 🏗️ **Architecture Overview**

Service executors provide orchestrated, high-level operations while maintaining clean separation from direct controller access:

```
Scripts/Routes → Service Executors → device._get_controller() (private) → Controllers
```

## ⚠️ **CRITICAL: Singleton Pattern**

**Each device has singleton service executor instances that MUST be reused to preserve state and memory.**

### **State That Gets Lost When Creating New Instances:**

- **NavigationExecutor**: `current_node_id`, `current_tree_id`, `current_node_label`
- **ActionExecutor**: `action_screenshots`, `_action_type_cache`, navigation context
- **VerificationExecutor**: Navigation context (`tree_id`, `node_id`)
- **AIExecutor**: Execution tracking (`_executions`), plan caches

### **✅ CORRECT Usage - Reuse Device's Executors:**
```python
# Always use device's existing executor instances
action_executor = device.action_executor
verification_executor = device.verification_executor  
navigation_executor = device.navigation_executor
ai_executor = device.ai_executor  # AIExecutor is an orchestrator (moved to executors/)
zap_executor = ZapExecutor(device)  # ZapExecutor takes device, uses its executors

# These preserve all state and caches
```

### **❌ INCORRECT Usage - Creates New Instances:**
```python
# DON'T create new instances - causes state loss!
action_executor = ActionExecutor(device)  # ❌ Loses state!
verification_executor = VerificationExecutor(device)  # ❌ Loses state!
```

### **Protection Mechanisms:**

1. **Constructor Warnings** - New instances outside device initialization show warnings:
```
⚠️ [ActionExecutor] WARNING: Creating new ActionExecutor instance for device device1
⚠️ [ActionExecutor] This may cause state loss! Use device.action_executor instead.
```

2. **Factory Methods** (Alternative):
```python
# Safe factory methods that return existing instances
action_executor = ActionExecutor.get_for_device(device)
verification_executor = VerificationExecutor.get_for_device(device)
```

3. **Documentation** - All service executors have clear warnings in class docstrings.

## 📋 **Available Service Executors**

1. **ActionExecutor** - Execute device actions with retry logic and orchestration
2. **VerificationExecutor** - Execute verification checks with batch processing
3. **NavigationExecutor** - Navigate between nodes with pathfinding
4. **ZapExecutor** - Execute zap actions with comprehensive analysis (specialized)
5. **AIExecutor** - Execute AI-driven plans with step orchestration (specialized)

---

## 🎮 **ActionExecutor Usage Guide**

**Purpose:** Execute device actions (remote, web, desktop, etc.) with retry logic, iteration support, and comprehensive orchestration.

### **✅ CORRECT Usage (Singleton Pattern):**
```python
# Use device's existing ActionExecutor instance
action_executor = device.action_executor

# ActionExecutor is created during device initialization with:
# ActionExecutor(device, _from_device_init=True)
# Contains state: action_screenshots, _action_type_cache, navigation context
```

### **❌ INCORRECT Usage (Creates New Instance):**
```python
# DON'T do this - causes state loss!
from backend_host.src.services.actions.action_executor import ActionExecutor
action_executor = ActionExecutor(device)  # ❌ Loses cached state!
```

### **Key Features:**
- ✅ **Retry Logic** - Main actions → Retry actions → Failure actions
- ✅ **Iterator Support** - Repeat actions N times with stop-on-failure
- ✅ **Dynamic Controller Detection** - Automatically determines which controller to use
- ✅ **Batch Processing** - Execute multiple actions in sequence
- ✅ **Screenshot Management** - Automatic screenshots before/after actions
- ✅ **Database Recording** - Records execution metrics to database
- ✅ **Error Handling** - Standardized error responses

### **Main Method:**
```python
result = action_executor.execute_actions(
    actions,                   # List[Dict] - Main actions to execute
    retry_actions=None,        # List[Dict] - Actions to try if main fails
    failure_actions=None,      # List[Dict] - Actions to try if retry fails
    team_id=None              # str - Team ID for database recording
)
```

### **Action Format:**
```python
action = {
    'command': 'press_key',           # Command name
    'params': {'key': 'OK'},          # Command parameters
    'action_type': 'remote',          # Optional - auto-detected if not provided
    'iterator': 3,                    # Optional - repeat 3 times
    'wait_time': 1000                 # Optional - wait 1s after execution
}
```

### **Usage Examples:**

#### **Basic Action Execution:**
```python
# Simple remote action
actions = [{'command': 'press_key', 'params': {'key': 'OK'}}]
result = action_executor.execute_actions(actions)

if result['success']:
    print(f"Action completed: {result['message']}")
else:
    print(f"Action failed: {result['error']}")
```

#### **Actions with Retry Logic:**
```python
# Main action with retry fallback
main_actions = [{'command': 'click_element', 'params': {'selector': '#button'}}]
retry_actions = [{'command': 'press_key', 'params': {'key': 'ENTER'}}]

result = action_executor.execute_actions(
    actions=main_actions,
    retry_actions=retry_actions,
    team_id="your-team-id"
)
```

#### **Batch Actions with Iterations:**
```python
# Multiple actions with iterations
actions = [
    {'command': 'press_key', 'params': {'key': 'UP'}, 'iterator': 3},
    {'command': 'press_key', 'params': {'key': 'OK'}, 'wait_time': 2000}
]
result = action_executor.execute_actions(actions)
```

### **Return Format:**
```python
{
    'success': True/False,
    'total_count': 2,
    'passed_count': 2,
    'failed_count': 0,
    'results': [...],              # Individual action results
    'action_screenshots': [...],   # Screenshot paths
    'message': 'Batch action execution completed: 2/2 passed',
    'error': None,                 # Error message if failed
    'execution_time_ms': 1500
}
```

---

## 🔍 **VerificationExecutor Usage Guide**

**Purpose:** Execute verification checks (image, text, video, audio) with batch processing and standardized results.

### **✅ CORRECT Usage (Singleton Pattern):**
```python
# Use device's existing VerificationExecutor instance
verification_executor = device.verification_executor

# VerificationExecutor is created during device initialization with:
# VerificationExecutor(device, _from_device_init=True)
# Contains state: navigation context (tree_id, node_id)
```

### **❌ INCORRECT Usage (Creates New Instance):**
```python
# DON'T do this - causes state loss!
from backend_host.src.services.verifications.verification_executor import VerificationExecutor
verification_executor = VerificationExecutor(device)  # ❌ Loses navigation context!
```

### **Key Features:**
- ✅ **Batch Processing** - Execute multiple verifications in sequence
- ✅ **Screenshot Management** - Automatic screenshot capture
- ✅ **Multiple Verification Types** - image, text, video, audio, adb, appium
- ✅ **Database Recording** - Records verification results
- ✅ **Error Handling** - Graceful failure handling

### **Main Method:**
```python
result = verification_executor.execute_verifications(
    verifications,             # List[Dict] - Verifications to execute
    image_source_url=None     # str - Optional image source URL
)
```

### **Verification Format:**
```python
verification = {
    'command': 'detect_motion_from_json',    # Verification command
    'verification_type': 'video',            # Type: image, text, video, audio, adb, appium
    'params': {                              # Command-specific parameters
        'json_count': 3,
        'strict_mode': False
    }
}
```

### **Usage Examples:**

#### **Motion Detection:**
```python
verifications = [{
    'command': 'detect_motion_from_json',
    'verification_type': 'video',
    'params': {
        'json_count': 3,
        'strict_mode': False
    }
}]

result = verification_executor.execute_verifications(verifications)
if result['success'] and result['results']:
    motion_detected = result['results'][0]['success']
    print(f"Motion detected: {motion_detected}")
```

#### **Text Verification:**
```python
verifications = [{
    'command': 'verify_text_present',
    'verification_type': 'text',
    'params': {
        'expected_text': 'Welcome',
        'screenshot_path': '/path/to/screenshot.jpg'
    }
}]

result = verification_executor.execute_verifications(verifications)
```

#### **Subtitle Analysis:**
```python
verifications = [{
    'command': 'detect_subtitles_ai',
    'verification_type': 'video',
    'params': {
        'screenshots': ['/path/to/screenshot.jpg'],
        'extract_text': True
    }
}]

result = verification_executor.execute_verifications(verifications)
if result['success']:
    subtitle_result = result['results'][0]
    if subtitle_result['subtitles_detected']:
        print(f"Subtitles found: {subtitle_result['extracted_text']}")
```

### **Return Format:**
```python
{
    'success': True/False,
    'results': [                   # Individual verification results
        {
            'success': True,
            'verification_type': 'video',
            'message': 'Motion detected',
            'motion_detected': True,
            # ... verification-specific fields
        }
    ],
    'total_count': 1,
    'passed_count': 1,
    'failed_count': 0,
    'execution_time_ms': 800
}
```

---

## 🗺️ **NavigationExecutor Usage Guide**

**Purpose:** Navigate between nodes in the navigation tree with intelligent pathfinding and execution.

### **✅ CORRECT Usage (Singleton Pattern):**
```python
# Use device's existing NavigationExecutor instance
navigation_executor = device.navigation_executor

# NavigationExecutor is created during device initialization with:
# NavigationExecutor(device, _from_device_init=True)
# Contains state: current_node_id, current_tree_id, current_node_label
```

### **❌ INCORRECT Usage (Creates New Instance):**
```python
# DON'T do this - causes state loss!
from backend_host.src.services.navigation.navigation_executor import NavigationExecutor
navigation_executor = NavigationExecutor(device)  # ❌ Loses current position!
```

### **Key Features:**
- ✅ **Pathfinding** - Finds optimal path between nodes
- ✅ **Tree Traversal** - Handles complex navigation trees
- ✅ **Action Execution** - Executes navigation actions automatically
- ✅ **State Management** - Tracks current position in tree
- ✅ **Error Recovery** - Handles navigation failures gracefully

### **Main Methods:**

#### **Navigate to Target Node:**
```python
success = navigation_executor.navigate_to_node(
    target_node_id,           # str - Target node ID
    current_node_id=None,     # str - Current position (auto-detected if None)
    tree_id=None,            # str - Tree ID (required for pathfinding)
    team_id=None             # str - Team ID for security
)
```

#### **Execute Navigation Path:**
```python
result = navigation_executor.execute_navigation_path(
    navigation_path,          # List[Dict] - Path steps to execute
    context                   # ScriptExecutionContext - Execution context
)
```

### **Usage Examples:**

#### **Simple Navigation:**
```python
# Navigate from current position to target
success = navigation_executor.navigate_to_node(
    target_node_id="live_fullscreen",
    tree_id="horizon_android_mobile",
    team_id="your-team-id"
)

if success:
    print("Navigation completed successfully")
else:
    print("Navigation failed")
```

#### **Navigation with Context:**
```python
# Navigate with full context (used in scripts)
from shared.src.lib.executors.script_decorators import navigate_to

# High-level navigation (recommended for scripts)
success = navigate_to("live")  # Uses current context automatically
```

### **Return Format:**
```python
# navigate_to_node returns boolean
success = True/False

# execute_navigation_path returns detailed result
{
    'success': True/False,
    'steps_executed': 3,
    'total_steps': 3,
    'execution_time_ms': 2500,
    'final_node_id': 'live_fullscreen',
    'error': None  # Error message if failed
}
```

---

## ⚡ **ZapExecutor Usage Guide**

**Purpose:** Execute zap actions (channel up/down) with comprehensive analysis including motion detection, subtitle analysis, and zapping detection.

### **✅ CORRECT Usage (Uses Device's Executors):**
```python
from shared.src.lib.executors.zap_executor import ZapExecutor

# ZapExecutor takes device and uses its existing service executors
zap_executor = ZapExecutor(device)

# Internally uses:
# - device.verification_executor (preserves navigation context)
# - device.action_executor (preserves action cache and screenshots)
```

### **❌ INCORRECT Usage (Old Pattern - Fixed):**
```python
# This was the old problematic pattern (now fixed):
# ZapExecutor was creating new VerificationExecutor/ActionExecutor instances
# This caused state loss - now it reuses device's existing executors
```

### **Key Features:**
- ✅ **Zap Action Execution** - Execute channel up/down actions
- ✅ **Motion Detection** - Detect content changes after zap
- ✅ **Subtitle Analysis** - Extract and analyze subtitles with AI
- ✅ **Audio Analysis** - Transcribe and analyze audio content
- ✅ **Zapping Detection** - Detect blackscreen/freeze transitions
- ✅ **Statistics Collection** - Comprehensive metrics and reporting
- ✅ **Database Recording** - Record detailed zap iteration data
- ✅ **Screenshot Management** - Capture screenshots throughout process

### **Main Method:**
```python
success = zap_executor.execute_zap_iterations(
    context,                  # ScriptExecutionContext - Execution context
    action_edge,             # Dict - Action edge from navigation tree
    action_command,          # str - Action command (e.g., 'live_chup')
    max_iterations,          # int - Number of zap iterations to execute
    goto_live=True           # bool - Whether to navigate to live first
)
```

### **Usage Examples:**

#### **Basic Zap Execution:**
```python
# Execute 5 channel up iterations
success = zap_executor.execute_zap_iterations(
    context=context,
    action_edge=action_edge,
    action_command='live_chup',
    max_iterations=5,
    goto_live=True
)

if success:
    print("All zap iterations completed successfully")
    # Access statistics
    zap_executor.statistics.print_summary('live_chup')
else:
    print("Some zap iterations failed")
```

#### **Zap with Analysis Results:**
```python
# Execute zaps and access detailed analysis
success = zap_executor.execute_zap_iterations(
    context, action_edge, 'live_chup', 3
)

# Access comprehensive statistics
stats = zap_executor.statistics
print(f"Motion detected: {stats.motion_detected_count}/{stats.total_iterations}")
print(f"Subtitles detected: {stats.subtitles_detected_count}/{stats.total_iterations}")
print(f"Audio speech detected: {stats.audio_speech_detected_count}/{stats.total_iterations}")
print(f"Zapping detected: {stats.zapping_detected_count}/{stats.total_iterations}")
print(f"Detected languages: {stats.detected_languages}")
print(f"Average zapping duration: {stats.average_zapping_duration:.2f}s")
```

#### **Access Individual Analysis Results:**
```python
# Get detailed analysis for each iteration
for i, analysis_result in enumerate(zap_executor.statistics.analysis_results, 1):
    print(f"Iteration {i}:")
    print(f"  Motion: {analysis_result.motion_detected}")
    print(f"  Subtitles: {analysis_result.subtitles_detected}")
    if analysis_result.detected_language:
        print(f"  Language: {analysis_result.detected_language}")
    if analysis_result.extracted_text:
        print(f"  Text: {analysis_result.extracted_text[:50]}...")
```

### **Statistics Available:**
```python
# ZapStatistics properties
stats.total_iterations              # Total iterations executed
stats.successful_iterations         # Successful iterations
stats.motion_detected_count         # Iterations with motion detected
stats.subtitles_detected_count      # Iterations with subtitles detected
stats.audio_speech_detected_count   # Iterations with audio speech detected
stats.zapping_detected_count        # Iterations with zapping detected
stats.detected_languages           # List of detected subtitle languages
stats.audio_languages              # List of detected audio languages
stats.average_zapping_duration      # Average zapping duration in seconds
stats.average_blackscreen_duration  # Average blackscreen duration in seconds
stats.detected_channels            # List of detected channel names
```

---

## 🔧 **Common Patterns & Best Practices**

### **1. Error Handling:**
```python
try:
    result = action_executor.execute_actions(actions)
    if not result['success']:
        print(f"Execution failed: {result['error']}")
        # Handle failure case
except Exception as e:
    print(f"Execution error: {e}")
    # Handle exception case
```

### **2. Context Usage in Scripts:**
```python
from shared.src.lib.executors.script_decorators import get_context

context = get_context()
device = context.selected_device

# ✅ CORRECT: Use device's existing service executors
action_executor = device.action_executor
verification_executor = device.verification_executor
navigation_executor = device.navigation_executor

# ❌ INCORRECT: Don't create new instances
# action_executor = ActionExecutor(device, context.tree_id, context.edge_id)  # Loses state!
```

### **3. Database Recording:**
```python
# Always provide team_id for database recording
result = action_executor.execute_actions(
    actions, 
    team_id=context.team_id  # Required for database recording
)
```

### **4. Screenshot Management:**
```python
# Service executors automatically manage screenshots
result = action_executor.execute_actions(actions)

# Screenshots are available in result
screenshots = result.get('action_screenshots', [])
for screenshot_path in screenshots:
    context.add_screenshot(screenshot_path)  # Add to context for reporting
```

### **5. Service Executor Selection:**

```python
# Use ActionExecutor for:
- Remote control actions (press_key, input_text)
- Web actions (click_element, fill_form)
- Desktop actions (execute_bash_command, mouse_click)
- Power actions (power_on, power_off)

# Use VerificationExecutor for:
- Motion detection
- Text verification
- Image comparison
- Audio analysis
- Element verification

# Use NavigationExecutor for:
- Moving between nodes in navigation tree
- Path finding and execution
- Tree traversal

# Use ZapExecutor for:
- Channel zapping with comprehensive analysis
- Motion + subtitle + audio + zapping detection
- Statistics collection and reporting
```

---

## ⚠️ **Important Notes**

### **Architecture Enforcement:**
- ✅ **Always use service executors** - Never access `device._get_controller()` directly
- ✅ **Service executors handle orchestration** - Retry logic, screenshots, DB recording
- ✅ **Controllers are private** - Only service executors can access them

### **Performance Considerations:**
- Service executors add orchestration overhead but provide significant value
- Use appropriate service executor for your use case
- Batch operations when possible (multiple actions/verifications in one call)

### **Debugging:**
- Service executors provide comprehensive logging
- Screenshots are automatically captured for debugging
- Database recording provides execution history
- Error messages are standardized and detailed

---

**This guide ensures proper usage of all service executors while maintaining clean architecture and getting the full benefit of the orchestration features.**
