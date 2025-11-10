# MCP Navigation Tools

[← Back to MCP Documentation](../mcp.md)

---

### 🗺️ Navigation

#### navigate_to_node

Navigate to target node in UI tree using pathfinding.

**⚠️ PREREQUISITES:** 
- `take_control(tree_id='<tree>')` must be called first with the SAME tree_id
- All parameters (device_id, tree_id, userinterface_name) MUST match the take_control call

**Parameters:**
```json
{
  "tree_id": "main_navigation",           // REQUIRED - MUST match take_control
  "userinterface_name": "horizon_android_mobile",  // REQUIRED
  "target_node_label": "home_saved",      // Provide label OR id
  "target_node_id": "node-123",           // Provide label OR id
  "device_id": "device1",                 // Optional (defaults to 'device1')
  "host_name": "sunri-pi1",               // Optional (defaults to 'sunri-pi1')
  "current_node_id": "node-000",          // Optional (auto-detected if omitted)
  "team_id": "team_1"                     // Optional (defaults to 'team_1')
}
```

**Returns:** Navigation path + results (polls automatically until complete, max 60s)

**Example:**
```python
# Step 1: Take control with tree_id
take_control({"tree_id": "main_navigation"})

# Step 2: Navigate (must use SAME tree_id and userinterface_name)
navigate_to_node({
    "tree_id": "main_navigation",
    "userinterface_name": "horizon_android_mobile",
    "target_node_label": "home_saved"
})
# MCP automatically polls until navigation completes
# Returns: ✅ Navigation to home_saved completed
```

