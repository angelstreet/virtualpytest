# Evaluate Condition Block - Complete Execution Flow

## NO NEW ROUTES - Uses Existing Infrastructure

The `evaluate_condition` block is executed through the **existing** standard block route infrastructure. NO new routes are needed.

---

## Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                    │
│  TestCaseBuilder / BlockExecutor Component                           │
│                                                                       │
│  User configures:                                                    │
│  - operand_type: "int"                                              │
│  - condition: "greater_than"                                        │
│  - left_operand: "{user_age}"                                       │
│  - right_operand: "18"                                              │
│                                                                       │
│  Clicks "Execute" →                                                  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │ POST /server/builder/execute
                                │ {
                                │   "command": "evaluate_condition",
                                │   "params": {
                                │     "operand_type": "int",
                                │     "condition": "greater_than",
                                │     "left_operand": "{user_age}",
                                │     "right_operand": "18"
                                │   },
                                │   "device_id": "device1"
                                │ }
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     SERVER (Proxy Layer)                             │
│  backend_server/src/routes/server_builder_routes.py                 │
│                                                                       │
│  Proxies request to host:                                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │ POST /host/builder/execute
                                │ (same payload)
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     HOST - ROUTE LAYER                               │
│  backend_host/src/routes/host_builder_routes.py                     │
│                                                                       │
│  @host_builder_bp.route('/execute', methods=['POST'])               │
│  def execute_standard_block():                                      │
│                                                                       │
│    Step 1: Generate execution_id                                    │
│       execution_id = str(uuid.uuid4())                              │
│                                                                       │
│    Step 2: Store initial state                                      │
│       device.standard_block_executor._executions[id] = {            │
│         'status': 'running',                                        │
│         'result': None,                                             │
│         'start_time': time.time()                                   │
│       }                                                              │
│                                                                       │
│    Step 3: Start background thread                                  │
│       threading.Thread(                                             │
│         target=_execute_blocks_thread,                              │
│         args=(device, execution_id, blocks)                         │
│       ).start()                                                      │
│                                                                       │
│    Step 4: Return immediately (<100ms)                              │
│       return {"execution_id": "..."}                                │
│                                                                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │ Background Thread Starts
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  BACKGROUND THREAD (_execute_blocks_thread)          │
│  backend_host/src/routes/host_builder_routes.py (line 18)          │
│                                                                       │
│  def _execute_blocks_thread(device, execution_id, blocks):          │
│                                                                       │
│    Call ExecutionOrchestrator.execute_blocks()                      │
│       ↓                                                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  EXECUTION ORCHESTRATOR                              │
│  backend_host/src/orchestrator/execution_orchestrator.py            │
│                                                                       │
│  @staticmethod                                                       │
│  def execute_blocks(device, blocks, context):                       │
│                                                                       │
│    Purpose: Wrap execution with LoggingManager                      │
│                                                                       │
│    def execute():                                                    │
│      return device.standard_block_executor.execute_blocks(...)      │
│                                                                       │
│    return LoggingManager.execute_with_logging(execute)              │
│       ↓                                                              │
│    (Captures stdout/stderr logs for frontend)                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  STANDARD BLOCK EXECUTOR                             │
│  backend_host/src/services/blocks/standard_block_executor.py        │
│                                                                       │
│  def execute_blocks(blocks, context):                               │
│    for block in blocks:                                             │
│      result = self._execute_single_block(block, context)            │
│                                                                       │
│  def _execute_single_block(block, context):                         │
│    block_type = block['command']  # "evaluate_condition"            │
│    params = block['params']                                         │
│                                                                       │
│    # PRIORITY 1: Try BlockRegistry (NEW blocks)                     │
│    from backend_host.src.builder.block_registry import execute_block│
│                                                                       │
│    result = execute_block(                                          │
│      command="evaluate_condition",                                  │
│      params=params,                                                 │
│      context=context                                                │
│    )                                                                 │
│       ↓                                                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     BLOCK REGISTRY                                   │
│  backend_host/src/builder/block_registry.py                         │
│                                                                       │
│  def execute_block(command, params, context):                       │
│                                                                       │
│    Step 1: Discover blocks                                          │
│       blocks = discover_blocks()                                    │
│       # Auto-scans: backend_host/src/builder/blocks/*.py            │
│       # Returns: {                                                  │
│       #   'evaluate_condition': <module>,                           │
│       #   'sleep': <module>,                                        │
│       #   ...                                                        │
│       # }                                                            │
│                                                                       │
│    Step 2: Get module                                               │
│       module = blocks['evaluate_condition']                         │
│       # → backend_host/src/builder/blocks/evaluate_condition.py    │
│                                                                       │
│    Step 3: Execute                                                  │
│       result = module.execute(                                      │
│         operand_type=params['operand_type'],                        │
│         condition=params['condition'],                              │
│         left_operand=params['left_operand'],                        │
│         right_operand=params['right_operand'],                      │
│         context=context                                             │
│       )                                                              │
│       ↓                                                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  EVALUATE CONDITION BLOCK                            │
│  backend_host/src/builder/blocks/evaluate_condition.py              │
│                                                                       │
│  @capture_logs  # Decorator captures print() statements             │
│  def execute(operand_type, condition, left_operand,                 │
│              right_operand, context, **kwargs):                     │
│                                                                       │
│    Step 1: Resolve operands                                         │
│       left_value = _resolve_operand(                                │
│         "{user_age}",  # Input                                      │
│         context,       # Has context.variables = {'user_age': 25}   │
│         "int"          # Type                                       │
│       )                                                              │
│       # Result: left_value = 25                                     │
│                                                                       │
│       right_value = _resolve_operand(                               │
│         "18",          # Input (literal)                            │
│         context,                                                    │
│         "int"                                                        │
│       )                                                              │
│       # Result: right_value = 18                                    │
│                                                                       │
│    Step 2: Validate types                                           │
│       if not isinstance(left_value, int):                           │
│         return {'result_success': -1, 'error_msg': '...'}           │
│                                                                       │
│    Step 3: Evaluate condition                                       │
│       result_output = _evaluate_int_condition(                      │
│         25,           # left                                        │
│         18,           # right                                       │
│         "greater_than"                                              │
│       )                                                              │
│       # Result: True (25 > 18)                                      │
│                                                                       │
│    Step 4: Store in context                                         │
│       context.variables['result_output'] = True                     │
│       context.variables['result_success'] = 0                       │
│       context.variables['error_msg'] = ''                           │
│                                                                       │
│    Step 5: Return result                                            │
│       return {                                                       │
│         'result_success': 0,    # Success                           │
│         'error_msg': '',                                            │
│         'result_output': True   # The boolean result                │
│       }                                                              │
│       ↓                                                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │ Result bubbles back up
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  BLOCK REGISTRY                                      │
│  Returns result to StandardBlockExecutor                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  STANDARD BLOCK EXECUTOR                             │
│  Returns result to ExecutionOrchestrator                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  EXECUTION ORCHESTRATOR                              │
│  LoggingManager adds captured logs to result:                       │
│  {                                                                   │
│    'result_success': 0,                                             │
│    'error_msg': '',                                                 │
│    'result_output': True,                                           │
│    'logs': '[@block:evaluate_condition] ...\n...'                   │
│  }                                                                   │
│  Returns to background thread                                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  BACKGROUND THREAD                                   │
│  Updates execution state:                                           │
│                                                                       │
│  with device.standard_block_executor._lock:                         │
│    device.standard_block_executor._executions[execution_id] = {     │
│      'status': 'completed',                                         │
│      'result': result,  # Complete result with logs                │
│      'progress': 100                                                │
│    }                                                                 │
│                                                                       │
│  Thread exits                                                        │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                    │
│  Polling: GET /server/builder/execution/{id}/status                 │
│                                                                       │
│  Poll #1 (1s): {"status": "running", "progress": 0}                │
│  Poll #2 (2s): {"status": "completed", "result": {...}}            │
│                                                                       │
│  Receives final result:                                             │
│  {                                                                   │
│    "status": "completed",                                           │
│    "result": {                                                      │
│      "success": true,                                               │
│      "results": [                                                   │
│        {                                                             │
│          "result_success": 0,                                       │
│          "error_msg": "",                                           │
│          "result_output": true,                                     │
│          "logs": "[@block:evaluate_condition] ...",                 │
│          "execution_time_ms": 5                                     │
│        }                                                             │
│      ]                                                               │
│    }                                                                 │
│  }                                                                   │
│                                                                       │
│  Displays result to user                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Points

### ✅ NO New Routes Needed
- Uses existing `/host/builder/execute` route
- Uses existing `/host/builder/execution/{id}/status` for polling
- Frontend code already supports this pattern

### ✅ Auto-Discovery via BlockRegistry
- `BlockRegistry.discover_blocks()` automatically finds `evaluate_condition.py`
- Just need to create the file in `backend_host/src/builder/blocks/`
- No manual registration needed

### ✅ Async Execution (Prevents Timeouts)
- Route returns `execution_id` immediately (<100ms)
- Execution happens in background thread
- Frontend polls for status every 1s
- No HTTP timeout risk (even for slow operations)

### ✅ Proper Log Capture
- `@capture_logs` decorator captures print() statements
- `LoggingManager` in orchestrator captures all output
- Logs included in result for frontend display

### ✅ Context Management
- Context flows through entire stack
- Block reads from `context.variables['user_age']`
- Block writes to `context.variables['result_output']`
- Variables persist for next blocks in sequence

---

## File Locations

### Route Layer
- **Host Route**: `backend_host/src/routes/host_builder_routes.py` (line 100-217)
- **Server Proxy**: `backend_server/src/routes/server_builder_routes.py` (proxies to host)

### Orchestration Layer
- **Orchestrator**: `backend_host/src/orchestrator/execution_orchestrator.py` (line 150-175)
- **Logging Manager**: `backend_host/src/orchestrator/logging_manager.py`

### Execution Layer
- **Block Executor**: `backend_host/src/services/blocks/standard_block_executor.py` (line 39-136)
- **Block Registry**: `backend_host/src/builder/block_registry.py` (line 118-159)

### Block Implementation
- **Evaluate Condition**: `backend_host/src/builder/blocks/evaluate_condition.py` (NEW - just created)
- **Other Blocks**: `backend_host/src/builder/blocks/*.py` (sleep, set_variable, etc.)

---

## Frontend Integration

### 1. Get Available Blocks
```typescript
// GET /server/builder/blocks?device_id=device1
{
  "success": true,
  "blocks": [
    {
      "command": "evaluate_condition",
      "label": "Evaluate Condition",
      "description": "Evaluate condition with typed operands",
      "params": {
        "operand_type": {
          "type": "enum",
          "required": true,
          "choices": [
            {"label": "Integer", "value": "int"},
            {"label": "String", "value": "str"},
            ...
          ]
        },
        "condition": {...},
        "left_operand": {...},
        "right_operand": {...}
      },
      "output_schema": {
        "result_success": "int",
        "error_msg": "str",
        "result_output": "any"
      }
    },
    ...
  ]
}
```

### 2. Execute Block
```typescript
// POST /server/builder/execute
{
  "command": "evaluate_condition",
  "params": {
    "operand_type": "int",
    "condition": "greater_than",
    "left_operand": "{user_age}",
    "right_operand": "18"
  },
  "device_id": "device1"
}

// Response (immediate):
{
  "success": true,
  "execution_id": "a1b2c3d4-..."
}
```

### 3. Poll Status
```typescript
// GET /server/builder/execution/{id}/status?device_id=device1

// While running:
{
  "status": "running",
  "progress": 0,
  "message": "Executing blocks..."
}

// When completed:
{
  "status": "completed",
  "result": {
    "success": true,
    "results": [
      {
        "result_success": 0,  // 0=success, 1=failure, -1=error
        "error_msg": "",
        "result_output": true,
        "logs": "[@block:evaluate_condition] Evaluating...\n..."
      }
    ]
  }
}
```

---

## Testing the Block

### Example 1: Integer Comparison
```bash
curl -X POST http://localhost:8000/host/builder/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "evaluate_condition",
    "params": {
      "operand_type": "int",
      "condition": "greater_than",
      "left_operand": "25",
      "right_operand": "18"
    },
    "device_id": "device1"
  }'

# Response: {"execution_id": "..."}

# Then poll:
curl http://localhost:8000/host/builder/execution/{id}/status?device_id=device1
```

### Example 2: String Contains (with variable)
```bash
curl -X POST http://localhost:8000/host/builder/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "evaluate_condition",
    "params": {
      "operand_type": "str",
      "condition": "contains",
      "left_operand": "{error_message}",
      "right_operand": "timeout"
    },
    "device_id": "device1"
  }'
```

---

## Summary

1. **NO new routes** - uses existing `/host/builder/execute`
2. **Auto-discovery** - BlockRegistry finds the block automatically
3. **Async by default** - prevents HTTP timeouts
4. **Logs captured** - LoggingManager + @capture_logs decorator
5. **Context flows** - variables accessible across blocks
6. **Frontend ready** - existing polling pattern works

The `evaluate_condition` block is now fully integrated into the existing infrastructure! 🎉

