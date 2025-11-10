# MCP Script Tools

[← Back to MCP Documentation](../mcp.md)

---

### 🐍 Script Execution

#### execute_script

Execute Python script on device with CLI parameters.

**⚠️ PREREQUISITE:** `take_control()` should be called first if script uses device controls.

**Parameters:**
```json
{
  "script_name": "my_validation.py",     // REQUIRED
  "host_name": "sunri-pi1",              // REQUIRED
  "device_id": "device1",                // Optional (defaults to 'device1')
  "userinterface_name": "horizon_android_mobile",  // Optional (if script needs it)
  "parameters": "--param1 value1 --param2 value2",  // Optional - CLI args
  "team_id": "team_1"                    // Optional (defaults to 'team_1')
}
```

**Returns:** Script execution results (polls automatically until complete, max 2 hours)

**Example:**
```python
execute_script({
    "script_name": "stress_test.py",
    "host_name": "sunri-pi1",
    "parameters": "--iterations 100 --timeout 30"
})
# MCP automatically polls until script completes
# Returns: ✅ Script completed successfully (45.2s)
```
