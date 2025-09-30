# AI Agent System Documentation

## Overview

The AI Agent system provides intelligent task automation for TV application navigation and control using:
- **Vision AI** for visual context and position detection
- **Intelligent planning** with cached execution plans
- **Clean, minimal UI** with structured reasoning display
- **Confidence-based position handling** for drift detection
- **No legacy fallback code** - fail fast, fix root causes

---

## Architecture

### Core Components

1. **AI Executor** (`shared/src/lib/executors/ai_executor.py`)
   - Plan generation with Vision AI integration
   - Execution tracking and status reporting
   - Cache management with automatic validation
   - Navigation reassessment with visual context
   - Confidence-based position detection and handling

2. **AI Plan Cache** (`shared/src/lib/executors/ai_plan_cache.py`)
   - Fingerprint-based plan caching
   - Automatic cache validation (format, transitions, descriptions)
   - Auto-deletion of invalid/outdated plans
   - Manual cache reset functionality

3. **Frontend Components**
   - **AIExecutionPanel** (`frontend/src/components/ai/AIExecutionPanel.tsx`) - Main execution UI
   - **AIStepDisplay** (`frontend/src/components/ai/AIStepDisplay.tsx`) - Shared step display
   - **UserinterfaceSelector** (`frontend/src/components/common/UserinterfaceSelector.tsx`) - Dynamic userinterface selection

4. **Frontend Hooks**
   - **useAI** (`frontend/src/hooks/useAI.ts`) - Execution, polling, status management

---

## Key Features

### 1. **Vision AI Position Detection** 🔥 NEW

The AI agent now uses **Vision AI** to detect the current screen position from a screenshot:

#### Single AI Call Integration
```python
def _call_ai(self, prompt: str, context: Dict) -> Dict:
    # Take screenshot for visual context
    success, screenshot_b64, error = self.device.verification_executor.take_screenshot()
    
    # Build AI prompt with BOTH position detection AND planning
    ai_prompt = f"""You are controlling a TV application...
    
    STEP 1: IDENTIFY CURRENT POSITION
    Look at the screenshot and identify which node from this list matches:
    Available nodes: {node_list}
    
    STEP 2: GENERATE PLAN
    Task: "{prompt}"
    ...
    
    Response JSON:
    {{
      "detected_current_node": "node_name_from_visual",
      "position_confidence": "high|medium|low",
      "analysis": "Goal: ... Thinking: ...",
      "feasible": true/false,
      "plan": [...]
    }}
    """
    
    # Call Vision AI if screenshot available, otherwise Text AI
    if screenshot_b64:
        result = call_vision_ai(prompt=ai_prompt, image_base64=screenshot_b64, ...)
    else:
        result = call_text_ai(prompt=ai_prompt, ...)
```

#### Benefits
- ✅ **Detects user navigation outside system** (e.g., manual remote control)
- ✅ **Confirms stored position accuracy** before execution
- ✅ **Single AI call** - efficient, no redundant API requests
- ✅ **Visual context improves planning** - AI sees actual UI state

---

### 2. **Confidence-Based Position Handling** 🔥 NEW

The system intelligently handles position detection based on confidence levels:

#### The 3 Simple Rules
```python
if confidence == 'high' and detected_label:
    
    # Rule 1: NULL + confident detection → USE detected
    if not current_node_id:
        update_position(detected_node_id)
    
    # Rule 2: Match + confident → CONFIRM (keep current)
    elif detected_label == current_label:
        # Position confirmed, no update needed
        pass
    
    # Rule 3: Mismatch + confident → DRIFT (use detected)
    else:
        update_position(detected_node_id)  # Fix drift

elif confidence != 'high':
    # Rule 4: LOW confidence → DISCARD stored, USE NULL
    clear_position()
```

#### Example Scenarios

**Scenario 1: Unknown Position**
```
Device state: current_node_id = NULL
Vision AI: detected="home_replay", confidence="high"

Result:
  ✅ Position detected: home_replay
  device.navigation_context['current_node_id'] = "node-1749014440260"
  AI plans from: home_replay
```

**Scenario 2: Position Drift (User moved with remote)**
```
Device state: current_node_id = "node-1" (home)
User navigated manually to home_replay!
Vision AI: detected="home_replay", confidence="high"

Result:
  ⚠️ Position drift: stored=home, visual=home_replay
  UPDATE: device.navigation_context['current_node_id'] = "node-1749014440260"
  AI plans from: home_replay (correct!)
```

**Scenario 3: Low Confidence (Unclear Screenshot)**
```
Device state: current_node_id = "node-1" (home)
Vision AI: detected="???", confidence="low"

Result:
  ⚠️ Low confidence (low) - discarding stored position, using NULL
  CLEAR: device.navigation_context['current_node_id'] = NULL
  AI plans from: ENTRY point (safe default)
```

#### Safety Rules
1. **Only trust HIGH confidence** - anything else → use NULL
2. **Discard unreliable state** - better to start from entry than wrong position
3. **Update device state** - so execute_navigation uses correct position
4. **Convert label → node_id** - vision AI returns labels, executor needs node_ids
5. **Handle invalid detections** - if detected label not in graph → use NULL

---

### 3. **Intelligent Plan Caching**

#### Cache Fingerprinting
```python
# Unique fingerprint based on task context
fingerprint = hashlib.sha256(
    f"{prompt}:{sorted_nodes}:{sorted_actions}:{tree_id}".encode()
).hexdigest()
```

#### Automatic Cache Validation 🔥 NEW

The system validates cached plans and auto-deletes invalid ones:

```python
def _is_plan_format_valid(self, cached_plan: Dict) -> bool:
    # Check 1: Must have 'command' field (new format)
    if 'command' not in step:
        return False
    
    # Check 2: Navigation steps must have pre-fetched transitions
    if step['command'] == 'execute_navigation':
        if 'transitions' not in step:
            return False
    
    # Check 3: No verbose AI descriptions (old format)
    description = step.get('description', '')
    if any(phrase in description.lower() for phrase in [
        'navigate directly', 'navigate to the', 'task is to',
        'closest node', 'proceed to', 'visually locate'
    ]):
        return False  # Old AI verbose format
    
    return True
```

**Invalid cache behaviors:**
- ❌ Old plan format → Auto-deleted, logged
- ❌ Missing transitions → Auto-deleted
- ❌ Verbose AI descriptions → Auto-deleted
- ✅ Valid cache → Used immediately, no AI call

#### Cache-Only Mode

```python
# User ticks "Use Cache"
use_cache = True

# System finds invalid cache → FAIL FAST (no AI generation)
if use_cache and not valid_cached_plan:
    return {
        'success': False,
        'error': 'No cached plan available. Uncheck "Use Cache" or execute once to populate.',
        'cache_miss': True
    }
```

**Benefits:**
- ✅ **No unexpected AI calls** when user wants cached execution
- ✅ **Clear error message** guides user action
- ✅ **Fast failure** instead of silent fallback

#### Manual Cache Reset 🔥 NEW

Users can manually clear all cached plans:

```typescript
// Frontend: AIExecutionPanel.tsx
const handleResetCache = async () => {
  const result = await fetch('/server/ai-execution/resetCache', {
    method: 'POST',
    body: JSON.stringify({ team_id })
  });
  // Shows: "Cache cleared: 5 plans deleted"
};
```

---

### 4. **Clean Step Formatting**

#### AI Prompt Constraints
```
DESCRIPTION FIELD RULES (CRITICAL):
1. For navigation steps: ONLY the target node name (e.g., "home_replay")
2. For reassessment: ONLY "reassess"
3. For tap_coordinates: ONLY "tap(x, y)"
4. NO AI interpretations like "Navigate directly to...", "Proceed to...", etc.
```

#### Formatted Display

**Old (verbose AI text):**
```
Executing step 1: Navigate directly to home_replay
```

**New (clean command format):**
```
Executing step 1: execute_navigation(home_replay)
```

**Implementation:**
```python
def _format_step_display(self, step_data: Dict) -> str:
    command = step_data.get('command', 'unknown')
    params = step_data.get('params', {})
    
    if command == 'execute_navigation':
        target_node = params.get('target_node', 'unknown')
        return f"{command}({target_node})"
    elif command == 'navigation_reassessment':
        original_target = params.get('original_target', 'unknown')
        return f"reassess_navigation({original_target})"
    # ... other commands ...
```

---

### 5. **Pre-fetched Transitions** 🔥 NEW

Navigation transitions are **pre-fetched during planning** and **passed through execution**, eliminating redundant API calls in the UI.

#### Backend: Pre-fetch During Planning
```python
def _prefetch_navigation_transitions(self, plan_steps: List[Dict], context: Dict):
    """Pre-fetch navigation transitions for all navigation steps"""
    for step in plan_steps:
        if step.get('command') == 'execute_navigation':
            target_node = step['params'].get('target_node')
            
            # Find path using navigation executor
            path = self.device.navigation_executor.find_shortest_path(
                target_node_id=target_node,
                start_node_id=context.get('current_node_id')
            )
            
            # Store transitions in step data
            step['transitions'] = path.get('path', [])
```

#### Backend: Include in Execution Results
```python
# In _execute_navigation_step
if result.get('navigation_path'):
    step_result['transitions'] = result['navigation_path']

# In _execute_step
if result.get('transitions'):
    step_result['transitions'] = result['transitions']
```

#### Frontend: No More Fetching
```typescript
// OLD (redundant API calls):
useEffect(() => {
  if (step.command === 'execute_navigation') {
    fetchTreeId().then(() => fetchTransitions());  // ❌ DELETED
  }
}, [step]);

// NEW (use pre-fetched data):
const transitions = step.transitions || [];  // ✅ Always available
```

**Benefits:**
- ✅ **Faster UI rendering** - no loading states
- ✅ **Reduced server load** - 1 API call instead of N
- ✅ **Simpler code** - no fetch logic, loading states, error handling
- ✅ **No legacy fallback** - transitions always provided

---

### 6. **Navigation Reassessment**

When navigation fails due to incomplete graphs, the AI visually reassesses the situation:

#### Trigger Conditions
```python
if not navigation_success and error_type == 'incomplete_graph':
    # Visual reassessment triggered
    reassessment_result = self._navigation_reassess_with_visual(
        original_target=target_node,
        current_screenshot=screenshot_b64
    )
```

#### Visual Reassessment Process
```python
def _navigation_reassess_with_visual(self, original_target: str, current_screenshot: str):
    # Call Vision AI with screenshot
    prompt = f"""The navigation to '{original_target}' failed (incomplete graph).
    
    Looking at the current screen, what specific UI actions can reach this target?
    Generate steps like: tap_coordinates, swipe, press_key, etc.
    
    Response: {{"analysis": "...", "steps": [...]}}
    """
    
    result = call_vision_ai(prompt=prompt, image_base64=current_screenshot)
    
    # Inject generated steps into execution
    return {
        'success': True,
        'injected_steps': result['steps'],
        'analysis': result['analysis']
    }
```

#### UI Display

**Reassessment step shows clean format:**
```
Step 2: reassess_navigation(live)  [current]
```

**Injected steps from reassessment:**
```
Step 2.1: tap_coordinates(x=500, y=300)  [completed]
Step 2.2: wait(duration=2)  [completed]
```

**Analysis appended to AI Reasoning:**
```
AI Reasoning:
  Goal: Navigate to 'live'
  Thinking: Direct path available via home → tvguide → live
  
  Reassessment: Navigation graph incomplete. Visually detected...
```

---

### 7. **Structured Analysis Display**

#### Backend: Concise Analysis Format
```python
ai_prompt = """
ANALYSIS FORMAT:
Goal: [One concise sentence describing the objective]
Thinking: [Brief reasoning about the approach - max 2 sentences]

EXAMPLE:
{
  "analysis": "Goal: Navigate to 'home_replay' screen\\nThinking: Direct navigation available via exact node match",
  "feasible": true,
  "plan": [...]
}
"""
```

#### Frontend: Structured Rendering
```typescript
const renderAnalysis = (analysis: string) => {
  const lines = analysis.split('\n');
  return lines.map(line => {
    if (line.startsWith('Goal:')) {
      return <Typography sx={{ color: '#4caf50' }}>{line}</Typography>;
    } else if (line.startsWith('Thinking:')) {
      return <Typography sx={{ color: '#2196f3' }}>{line}</Typography>;
    }
    // ... reassessment, other sections ...
  });
};
```

**Example Display:**
```
🧠 AI Reasoning
  Goal: Navigate to 'home_replay' screen
  Thinking: Direct navigation available via exact node match
```

---

### 8. **Dynamic Userinterface Selection** 🔥 NEW

Replaced hardcoded userinterface mappings with database-driven, user-selectable system.

#### Database Schema
```sql
-- userinterfaces.models[] contains compatible device models
{
  "id": "a3257816-...",
  "name": "horizon_android_mobile",
  "models": ["android_mobile", "android_tablet"]
}
```

#### Frontend Component
```typescript
<UserinterfaceSelector
  deviceModel="android_mobile"
  value={selectedUserinterface}
  onChange={setSelectedUserinterface}
  label="Userinterface"
/>
```

#### Backend Endpoint
```python
@server_userinterface_bp.route('/getCompatibleInterfaces', methods=['GET'])
def get_compatible_interfaces():
    device_model = request.args.get('device_model')
    
    # Query database: WHERE models @> ARRAY[device_model]
    compatible_interfaces = get_interfaces_by_model(device_model)
    
    return jsonify({'interfaces': compatible_interfaces})
```

**Benefits:**
- ✅ **User choice** - select any compatible userinterface
- ✅ **Database-driven** - no hardcoded mappings
- ✅ **Global consistency** - same component in AIExecutionPanel, TestCaseEditor, etc.

---

## Execution Flow

### Complete Task Execution

```
1. User: "go to live"
   Device state: current_node_id = "node-1" (home)
   User manually navigated to "home_replay" using remote
   
2. Take screenshot
   
3. Vision AI analyzes (SINGLE CALL):
   - Position detection: "home_replay" (confidence: high)
   - Plan generation: [home_replay → home_tvguide → tvguide_livetv → live]
   
4. Position handling:
   - Detected: "home_replay" vs Stored: "home"
   - Mismatch + HIGH confidence → UPDATE device state
   - device.navigation_context['current_node_id'] = "node-1749014440260"
   
5. Check cache:
   - Fingerprint: sha256("go to live:nodes:actions:tree_id")
   - Found cached plan → validate format
   - Valid? → Use cache (skip AI generation)
   - Invalid? → Auto-delete + generate new OR fail fast (cache-only mode)
   
6. Pre-fetch transitions:
   - For each execute_navigation step
   - Find path: home_replay → home_tvguide → tvguide_livetv → live
   - Store in step['transitions']
   
7. Execute plan:
   - Step 1: execute_navigation(home_tvguide)
     - Start from: "home_replay" (visual truth)
     - Navigate: Press DOWN → Press OK
     - Success → update position
   
8. UI Display:
   - Analysis: "Goal: ... Thinking: ..."
   - Step 1: execute_navigation(home_tvguide) ✅
     - Expand to show transitions (pre-fetched, no API call)
   
9. Store plan in cache (if successful)
```

---

## Error Handling

### Fail-Fast Mechanisms

**No legacy fallback code** - fix root causes instead:

```python
# ❌ FORBIDDEN - Legacy fallback
try:
    new_implementation()
except:
    legacy_implementation()  # NO!

# ✅ CORRECT - Fail fast, fix root cause
def new_implementation():
    if not valid_input:
        raise ValueError("Fix the input, don't add fallbacks")
    return process_data()
```

### Polling Timeout
```typescript
const MAX_WAIT_TIME = 30000; // 30 seconds
const MAX_NOT_FOUND_ATTEMPTS = 5;

// Stop polling if execution not found or timeout
if (elapsed > MAX_WAIT_TIME || notFoundCount > MAX_NOT_FOUND_ATTEMPTS) {
  setIsAIExecuting(false);
  setError('Execution timeout or not found');
}
```

### JSON Sanitization
```python
def _sanitize_json_string(self, json_str: str) -> str:
    """Escape control characters in AI JSON responses"""
    # Escape \n, \r, \t, \b, \f in string values
    pattern = r'"((?:[^"\\]|\\.)*)"'
    return re.sub(pattern, escape_control_chars, json_str)
```

---

## Configuration

### AI Model Settings
```python
# In shared/src/lib/utils/ai_utils.py
'models': {
    'text': 'microsoft/phi-3-mini-128k-instruct',
    'vision': 'qwen/qwen-2.5-vl-7b-instruct',  # Used for position detection + planning
    'agent': 'meta-llama/llama-3.1-8b-instruct:free'
}

# Temperature = 0.0 for deterministic responses
```

### Cache Configuration
```python
# Cache TTL
PLAN_CACHE_TTL = 86400  # 24 hours

# Cache validation
VALIDATE_ON_LOAD = True  # Auto-delete invalid caches
```

---

## Best Practices

### 1. **No Legacy Code**
- ❌ Never implement backward compatibility or fallback mechanisms
- ✅ Delete obsolete code completely after implementing new architecture
- ✅ Fail fast and fix root causes instead of patching

### 2. **Single Source of Truth**
- ✅ Database-driven configuration (userinterfaces, navigation trees)
- ✅ Pre-fetch data once, pass through execution chain
- ✅ No redundant API calls in UI

### 3. **Clean UI/UX**
- ✅ Minimal, structured analysis (Goal + Thinking)
- ✅ Command-like step display (e.g., `execute_navigation(home)`)
- ✅ Pre-fetched transitions (no loading states)
- ✅ Consistent styling across components

### 4. **Confidence-Based Safety**
- ✅ Only trust high-confidence position detection
- ✅ Discard unreliable state (better NULL than wrong)
- ✅ Update device state after visual detection

---

## Troubleshooting

### Common Issues

**1. "No cached plan available"**
- **Cause**: User ticked "Use Cache" but cache is invalid or missing
- **Fix**: Uncheck "Use Cache" to generate new plan, or click "Reset Cache"

**2. "Position drift detected"**
- **Cause**: User navigated manually, device state outdated
- **Fix**: Automatic - Vision AI detects and updates position

**3. "Low confidence - using NULL"**
- **Cause**: Screenshot unclear, AI can't reliably detect position
- **Fix**: Automatic - system uses ENTRY point as safe default

**4. Execution stuck in loop**
- **Cause**: Polling timeout or "not found" limit not reached
- **Fix**: Check `MAX_WAIT_TIME` and `MAX_NOT_FOUND_ATTEMPTS` in `useAI.ts`

**5. Old cached plans show verbose descriptions**
- **Cause**: Cache from before format update
- **Fix**: Automatic - invalid cache auto-deleted on next execution, or manual "Reset Cache"

### Debug Logging

**Backend:**
```python
print(f"[@ai_executor] ✅ Position detected: {detected_label}")
print(f"[@ai_executor] ⚠️ Position drift: stored={current_label}, visual={detected_label}")
print(f"[@ai_plan_cache:validation] ❌ Invalid: Old AI verbose description detected")
```

**Frontend:**
```typescript
console.log('[useAI] Status response:', status);
console.log('[useAI] Setting plan:', status.plan);
```

---

## Future Enhancements

### Planned Features
- **Multi-step reassessment** - chain multiple visual analyses
- **Confidence learning** - improve detection accuracy over time
- **Parallel execution** - execute independent steps simultaneously
- **Voice control** - natural language task input via speech

### Performance Optimizations
- **Context caching** - cache navigation/action contexts per device
- **Batch transitions** - pre-fetch multiple paths in single query
- **Lazy screenshot** - only capture if position uncertain