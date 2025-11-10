# MCP Testcase Tools

[← Back to MCP Documentation](../mcp.md)

---

### 🧪 TestCase Management

#### save_testcase

Save test case graph to database.

**Parameters:**
```json
{
  "testcase_name": "Home Screen Test",   // REQUIRED
  "graph_json": {                        // REQUIRED - from generate_test_graph
    "nodes": [...],
    "edges": [...],
    "scriptConfig": {...}
  },
  "description": "Verify home screen elements",  // Optional
  "userinterface_name": "horizon_android_mobile",  // Optional
  "folder": "smoke_tests",               // Optional - for organization
  "tags": ["regression", "critical"],    // Optional - for filtering
  "team_id": "team_1"                    // Optional (defaults to 'team_1')
}
```

**Returns:**
```json
{
  "success": true,
  "testcase_id": "tc-abc-123",
  "action": "created"
}
```

---

#### list_testcases

List all saved test cases.

**Parameters:**
```json
{
  "team_id": "team_1",                   // Optional (defaults to 'team_1')
  "include_inactive": false              // Optional (default: false)
}
```

**Returns:**
```json
{
  "testcases": [
    {
      "testcase_id": "tc-abc-123",
      "testcase_name": "Home Screen Test",
      "description": "Verify home screen elements",
      "userinterface_name": "horizon_android_mobile",
      "folder": "smoke_tests",
      "tags": ["regression", "critical"],
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-02T00:00:00Z"
    }
  ],
  "total": 42
}
```

---

#### load_testcase

Load saved test case by ID.

**Parameters:**
```json
{
  "testcase_id": "tc-abc-123",           // REQUIRED
  "team_id": "team_1"                    // Optional (defaults to 'team_1')
}
```

**Returns:**
```json
{
  "success": true,
  "testcase": {
    "testcase_id": "tc-abc-123",
    "testcase_name": "Home Screen Test",
    "graph_json": {
      "nodes": [...],
      "edges": [...],
      "scriptConfig": {...}
    },
    "userinterface_name": "horizon_android_mobile"
  }
}
```

---

#### execute_testcase

Execute test case graph on device.

**⚠️ PREREQUISITE:** `take_control()` must be called first.

**Parameters:**
```json
{
  "graph_json": {                        // REQUIRED - from generate_test_graph or load_testcase
    "nodes": [...],
    "edges": [...],
    "scriptConfig": {...}
  },
  "device_id": "device1",                // Optional (defaults to 'device1')
  "host_name": "sunri-pi1",              // Optional (defaults to 'sunri-pi1')
  "userinterface_name": "horizon_android_mobile",  // Optional
  "testcase_name": "My Test",            // Optional - for logging
  "team_id": "team_1"                    // Optional (defaults to 'team_1')
}
```

**Returns:** Execution results (polls automatically until complete, max 5 minutes)

**Example:**
```python
# Generate graph from prompt
graph = generate_test_graph({
    "prompt": "Navigate to home and verify Replay button",
    "userinterface_name": "horizon_android_mobile"
})

# Execute the generated graph
execute_testcase({
    "graph_json": graph['graph'],
    "testcase_name": "Home Verification"
})
# MCP automatically polls until execution completes
# Returns: ✅ Execution completed: SUCCESS (2.3s)
```

---

#### execute_testcase_by_id

MCP convenience wrapper to load and execute saved test case by ID in one call.

**⚠️ PREREQUISITE:** `take_control()` must be called first.

**Parameters:**
```json
{
  "testcase_id": "tc-abc-123",           // REQUIRED
  "device_id": "device1",                // Optional (defaults to 'device1')
  "host_name": "sunri-pi1",              // REQUIRED
  "userinterface_name": "horizon_android_mobile",  // Optional - overrides testcase's interface
  "team_id": "team_1"                    // Optional (defaults to 'team_1')
}
```

**Returns:** Execution results (polls automatically until complete)

**Example:**
```python
# Execute saved test case in one call
execute_testcase_by_id({
    "testcase_id": "tc-abc-123",
    "host_name": "sunri-pi1"
})
# Automatically loads + executes + polls
# Returns: ✅ Execution completed: SUCCESS
```
