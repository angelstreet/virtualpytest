# Invalid Plan User Flow - What Happens When Validation Fails

**Question:** If plan validation fails (post-processing), what message does the user see?

---

## 🔄 **Current Flow (Post-Processing Validation Failure)**

### **Step 1: AI Generates Plan with Invalid Node**

```python
# AI mistakenly generates:
{
  "steps": [
    {"command": "execute_navigation", "params": {"target_node": "settigns"}}  # Typo!
  ]
}
```

---

### **Step 2: Post-Processing Validation** (`ai_executor.py` line 1126)

```python
validation_result = validate_plan(ai_response, available_nodes, team_id, userinterface_name)

# Returns:
{
    'valid': False,
    'invalid_nodes': [
        {
            'original': 'settigns',
            'suggestions': ['settings'],  # Fuzzy match found 1 suggestion
            'step_index': 0
        }
    ],
    'modified': False
}
```

**Since only 1 suggestion:** Auto-fixes to `'settings'` ✅  
**Plan becomes valid!** User never sees the error.

---

### **Step 3: If Multiple or No Suggestions**

```python
# AI generates node that matches multiple or no nodes
validation_result = validate_plan(...)

# Returns:
{
    'valid': False,
    'invalid_nodes': [
        {
            'original': 'channel_unknown',
            'suggestions': [],  # No matches
            'step_index': 0
        }
    ],
    'modified': False
}
```

**Backend marks plan as not feasible:**

```python
# ai_executor.py line 1144-1151
if not validation_result['valid']:
    ai_response['feasible'] = False
    ai_response['needs_disambiguation'] = True
    ai_response['invalid_nodes'] = validation_result['invalid_nodes']
    ai_response['error'] = f"Plan contains {invalid_count} invalid navigation node(s)"
    print(f"[@ai_executor:generate_plan] Plan validation failed: {invalid_count} invalid nodes")
```

---

### **Step 4: Backend Returns Error** (`ai_executor.py` line 188-195)

```python
def execute_prompt(...):
    # ...
    plan_dict = self.generate_plan(prompt, context, current_node_id)
    
    if not plan_dict.get('feasible', True):  # ← Catches it here!
        return {
            'success': False,
            'execution_id': execution_id,
            'error': 'Task not feasible',  # ← Generic message
            'analysis': plan_dict.get('analysis', ''),
            'execution_time': time.time() - start_time
        }
```

**Returned to route:** `host_ai_routes.py` line 192

```python
result = device.ai_executor.execute_prompt(...)
print(f"[@host_ai] Prompt execution result: success={result.get('success')}")  # False
return jsonify(result)  # ← Returns HTTP 200 with success: False
```

---

### **Step 5: Frontend Receives Response** (`useAI.ts` line 315-329)

```typescript
const response = await fetch(buildServerUrl('/host/ai/executePrompt'), {
  method: 'POST',
  body: JSON.stringify({ prompt, userinterface_name, device_id, team_id })
});

const result = await response.json();
// result = { success: false, error: "Task not feasible", execution_id: "..." }

if (!response.ok) throw new Error(result.error);  // ← NOT triggered (HTTP 200)
```

**Problem:** Backend returns HTTP 200 even when `success: false`, so this check doesn't catch it!

---

### **Step 6: Frontend Starts Polling** (`useAI.ts` line 334)

```typescript
const executionId = result.execution_id;  // Gets execution_id

// Poll for status
const pollStatus = async () => {
  while (true) {
    const statusResponse = await fetch(`/server/ai-execution/getStatus`, {
      body: JSON.stringify({ execution_id: executionId, device_id, host_name })
    });
    const status = await statusResponse.json();
    
    // ...
  }
};
```

**What happens during polling?**

The execution was never started (because `feasible: false`), so:
- Polling finds no execution
- After 10 "not found" errors → stops polling
- Shows error: "Execution not found after 10 attempts"

---

## ❌ **Current User Experience (Bad)**

**User sees:**
```
🤖 Starting AI task
🔄 Monitoring AI execution...
❌ Execution not found after 10 attempts - execution may have failed to start
```

**Problems:**
1. ❌ Generic error message ("not found")
2. ❌ Doesn't explain the real issue (invalid navigation nodes)
3. ❌ User doesn't know which node is invalid
4. ❌ User doesn't see suggestions to fix it

---

## ✅ **Improved Flow (What We Should Do)**

### **Option 1: Return Invalid Nodes to Frontend**

**Backend change** (`ai_executor.py` line 188-195):

```python
if not plan_dict.get('feasible', True):
    # Check if it's due to invalid nodes (post-processing validation)
    if plan_dict.get('needs_disambiguation'):
        return {
            'success': False,
            'execution_id': execution_id,
            'error': plan_dict.get('error', 'Plan contains invalid navigation nodes'),
            'needs_disambiguation': True,
            'invalid_nodes': plan_dict.get('invalid_nodes', []),  # ← Pass to frontend
            'analysis': plan_dict.get('analysis', ''),
            'execution_time': time.time() - start_time
        }
    
    # Other infeasibility reasons
    return {
        'success': False,
        'execution_id': execution_id,
        'error': 'Task not feasible',
        'analysis': plan_dict.get('analysis', ''),
        'execution_time': time.time() - start_time
    }
```

**Frontend change** (`useAI.ts` line 328):

```typescript
const result = await response.json();

// Check for invalid nodes (post-processing validation failure)
if (!result.success && result.needs_disambiguation) {
  setIsExecuting(false);
  setDisambiguationData({
    status: 'needs_disambiguation',
    original_prompt: prompt,
    ambiguities: result.invalid_nodes.map(inv => ({
      original: inv.original,
      suggestions: inv.suggestions
    })),
    available_nodes: result.available_nodes || []
  });
  return; // Show disambiguation modal
}

// Check for other errors
if (!result.success) {
  throw new Error(result.error || 'AI execution failed');
}
```

**User experience:**
```
🤖 Starting AI task
💭 AI generated plan...
🤔 Clarify Navigation Nodes (modal appears)

We found: "channel_unknown"
Suggestions:
  ⭐ channel_guide (default)
  channel_list

[Confirm] [Edit Prompt]
```

---

### **Option 2: Better Error Message (Minimal Change)**

**Backend change** (`ai_executor.py` line 188-195):

```python
if not plan_dict.get('feasible', True):
    error_msg = plan_dict.get('error', 'Task not feasible')
    
    # Add details about invalid nodes
    if plan_dict.get('invalid_nodes'):
        invalid_list = [node['original'] for node in plan_dict['invalid_nodes']]
        error_msg = f"{error_msg}: {', '.join(invalid_list)}"
    
    return {
        'success': False,
        'execution_id': execution_id,
        'error': error_msg,  # ← More descriptive
        'analysis': plan_dict.get('analysis', ''),
        'execution_time': time.time() - start_time
    }
```

**Frontend change** (`useAI.ts` line 328):

```typescript
const result = await response.json();

// Better error handling for success: false
if (!result.success) {
  setIsExecuting(false);
  const errorMessage = enhanceErrorMessage(result.error || 'AI execution failed');
  setError(errorMessage);
  toast.showError(`❌ ${errorMessage}`, { duration: 5000 });
  return; // Stop here, don't poll
}
```

**User experience:**
```
🤖 Starting AI task
❌ Plan contains 1 invalid navigation node(s): channel_unknown
```

---

## 🎯 **Recommendation: Option 1 (Full Disambiguation)**

**Why?**
- ✅ Consistent UX (same modal as pre-processing)
- ✅ User can fix the issue interactively
- ✅ Suggestions shown to help user
- ✅ Choice saved to DB for learning
- ✅ Complete user experience

**Implementation:**
1. Backend: Pass `invalid_nodes` and `needs_disambiguation` in response
2. Frontend: Check for `needs_disambiguation` after `executePrompt` call
3. Frontend: Show disambiguation modal if detected
4. Frontend: Re-execute with corrected nodes

---

## 📊 **Complete Flow (After Fix)**

```
User: "go to settigns"
  ↓
Pre-processing: Clear (no ambiguity detected)
  ↓
AI generates: execute_navigation(settigns)
  ↓
Post-processing: Fuzzy match finds 1 suggestion → Auto-fixes to 'settings' ✅
  ↓
Execution succeeds (user never saw the typo)
```

**Or:**

```
User: "go to channel_unknown"
  ↓
Pre-processing: Clear (unknown word, not a potential node)
  ↓
AI generates: execute_navigation(channel_unknown)
  ↓
Post-processing: No fuzzy matches found
  ↓
Frontend shows modal:
  "We found: 'channel_unknown' 
   Did you mean:
   - Enter custom node
   or
   - Edit prompt"
  ↓
User edits prompt → Re-executes
```

---

## 🚀 **Should I implement Option 1?**

This would give users a complete experience for handling invalid nodes from AI mistakes.


