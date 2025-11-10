# MCP Action Tools

[← Back to MCP Documentation](../mcp.md)

---

## 🛠️ Tool Reference

### 🔍 Discovery Tools (NEW!)

#### list_actions

List all available actions for a device (categorized by type).

**Parameters:**
```json
{
  "device_id": "device1",        // Optional (defaults to 'device1')
  "host_name": "sunri-pi1",      // REQUIRED
  "team_id": "team_1"            // Optional (defaults to 'team_1')
}
```

**Returns:**
```json
{
  "device_action_types": {
    "remote": [
      {
        "id": "KEY_HOME",
        "label": "Home Button",
        "command": "KEY_HOME",
        "params": {},
        "description": "Press home button"
      }
    ],
    "adb": [
      {
        "id": "swipe_up",
        "label": "Swipe Up",
        "command": "swipe_up",
        "params": {"distance": 500},
        "description": "Swipe up gesture"
      }
    ],
    "web": [...],
    "desktop": [...]
  },
  "device_model": "Android TV"
}
```

**Use Case:** Discover what actions can be executed before calling `execute_device_action`.

---

#### list_verifications

List all available verification types for a device.

**Parameters:**
```json
{
  "device_id": "device1",        // Optional (defaults to 'device1')
  "host_name": "sunri-pi1",      // REQUIRED
  "team_id": "team_1"            // Optional (defaults to 'team_1')
}
```

**Returns:**
```json
{
  "device_verification_types": {
    "adb": [
      {
        "command": "waitForElementToAppear",
        "label": "Wait for Element to Appear",
        "params": {
          "search_term": {"type": "string", "required": true},
          "timeout": {"type": "number", "required": false}
        },
        "description": "Wait for UI element to appear",
        "verification_type": "adb"
      }
    ],
    "image": [...],
    "text": [...],
    "video": [...]
  },
  "device_model": "Android TV"
}
```

**Use Case:** Discover what verifications can be performed before calling `verify_device_state`.

---

#### list_navigation_nodes

List all available navigation nodes in a tree.

**Parameters:**
```json
{
  "tree_id": "main_navigation",  // REQUIRED
  "team_id": "team_1",           // Optional (defaults to 'team_1')
  "page": 0,                     // Optional (default: 0)
  "limit": 100                   // Optional (default: 100)
}
```

**Returns:**
```json
{
  "nodes": [
    {
      "id": "node-123",
      "label": "home_saved",
      "type": "screen",
      "position": {"x": 100, "y": 200}
    },
    {
      "id": "node-456",
      "label": "settings",
      "type": "screen",
      "position": {"x": 300, "y": 200}
    }
  ],
  "total": 42
}
```

**Use Case:** Discover available navigation targets before calling `navigate_to_node`.

---

### 🎮 Action Execution

#### execute_device_action

Execute batch of actions on device (remote commands, ADB, web, desktop).

**⚠️ PREREQUISITE:** `take_control()` must be called first.

**Executes direct device commands including:**
- 🚀 **Launch apps** (`launch_app`)
- 📱 **UI interactions** (swipe, click, type)
- 🔑 **Key presses** (`press_key`)
- And more...

**Parameters:**
```json
{
  "device_id": "device1",
  "actions": [
    {"command": "KEY_HOME", "params": {}, "delay": 500},
    {"command": "swipe_up", "params": {"distance": 300}, "delay": 300}
  ],
  "retry_actions": [],          // Optional: Actions to retry on failure
  "failure_actions": [],        // Optional: Actions to execute on failure
  "team_id": "team_1"           // Optional (defaults to 'team_1')
}
```

**Returns:** `execution_id` for async polling (polls automatically)

**Common Examples:**

**🚀 Launch App:**
```python
execute_device_action({
    "device_id": "device1",
    "actions": [{
        "command": "launch_app",
        "params": {"package": "com.netflix.mediaclient"},
        "delay": 2000
    }]
})
# MCP automatically polls until completion
# Returns: ✅ Action execution completed: 1/1 passed
```

**📱 Swipe:**
```python
execute_device_action({
    "actions": [{"command": "swipe_up", "params": {}, "delay": 500}]
})
```

**👆 Click Element:**
```python
execute_device_action({
    "actions": [{
        "command": "click_element",
        "params": {"text": "Home"},
        "delay": 1000
    }]
})
```

**⌨️ Type Text:**
```python
execute_device_action({
    "actions": [{
        "command": "type_text",
        "params": {"text": "Hello World"},
        "delay": 500
    }]
})
```

**🔑 Press Key:**
```python
execute_device_action({
    "actions": [{
        "command": "press_key",
        "params": {"key": "BACK"},
        "delay": 500
    }]
})
```

**Device Model Specific:**
- **android_mobile/android_tv**: Use ADB/Remote commands
  - Examples: `launch_app`, `swipe_up`, `swipe_down`, `click_element`, `click_element_by_id`, `type_text`, `press_key`
- **web/desktop**: Use web automation commands
  - Examples: `web_click`, `web_type`, `web_navigate`

**💡 Tip:** Call `list_actions()` first to discover all available commands for your device.

