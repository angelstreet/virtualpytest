# MCP Ai Tools

[← Back to MCP Documentation](../mcp.md)

---

### 🤖 AI Generation

#### generate_test_graph

Generate test case from natural language using AI.

**Parameters:**
```json
{
  "prompt": "Navigate to settings and enable subtitles",  // REQUIRED
  "userinterface_name": "horizon_android_tv",  // REQUIRED
  "device_id": "device1",                // Optional (defaults to 'device1')
  "host_name": "sunri-pi1",              // Optional (defaults to 'sunri-pi1')
  "resolutions": {},                     // Optional - for disambiguation
  "team_id": "team_1"                    // Optional (defaults to 'team_1')
}
```

**Returns:**
```json
{
  "success": true,
  "graph": {
    "nodes": [...],
    "edges": [...],
    "scriptConfig": {...}
  },
  "analysis": "Generated 3-step test case...",
  "requires_disambiguation": false
}
```

**Disambiguation Handling:**
If `requires_disambiguation: true`, the response includes:
```json
{
  "requires_disambiguation": true,
  "ambiguities": [
    {
      "phrase": "settings",
      "suggestions": ["Settings Menu", "Account Settings", "System Settings"]
    }
  ],
  "auto_corrections": [...],
  "available_nodes": [...]
}
```

Resolve by calling again with `resolutions`:
```python
generate_test_graph({
    "prompt": "Navigate to settings and enable subtitles",
    "userinterface_name": "horizon_android_tv",
    "resolutions": {
        "settings": "Settings Menu"
    }
})
```
