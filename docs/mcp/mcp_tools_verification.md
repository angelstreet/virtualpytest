# MCP Verification Tools

[← Back to MCP Documentation](../mcp.md)

---

### ✅ Verification

#### verify_device_state

Verify device state with batch verifications (image, text, video, ADB).

**⚠️ PREREQUISITE:** `take_control()` should be called first.

**Parameters:**
```json
{
  "device_id": "device1",                 // REQUIRED
  "userinterface_name": "horizon_android_mobile",  // REQUIRED
  "verifications": [                      // REQUIRED
    {
      "command": "waitForElementToAppear",
      "params": {"search_term": "Replay", "timeout": 5},
      "verification_type": "adb"
    }
  ],
  "host_name": "sunri-pi1",               // Optional (defaults to 'sunri-pi1')
  "team_id": "team_1",                    // Optional (defaults to 'team_1')
  "tree_id": "main_navigation",           // Optional
  "node_id": "node-123"                   // Optional
}
```

**Verification Structure:**
- `command`: Verification method name (from `list_verifications`)
- `params`: Method-specific parameters
- `verification_type`: Type category (adb, image, text, video)

**Returns:** Verification results (polls automatically until complete, max 30s)

**Example:**
```python
verify_device_state({
    "userinterface_name": "horizon_android_mobile",
    "verifications": [{
        "command": "waitForElementToAppear",
        "params": {"search_term": "Replay", "timeout": 5},
        "verification_type": "adb"
    }]
})
# MCP automatically polls until verification completes
# Returns: ✅ Verification completed: 1/1 passed
```
