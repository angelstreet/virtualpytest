# VirtualPyTest MCP Server

## Overview

**MCP (Model Context Protocol) Server** for VirtualPyTest enables external LLMs (Claude, ChatGPT, etc.) to control and automate physical devices through a standardized protocol.

**Location**: `backend_server/src/mcp/`

---

## 🎯 Core Capabilities

The MCP server exposes **11 tools** for complete device automation:

### 🔐 **Control Tools** (CRITICAL)
- **`take_control`** - Lock device & generate navigation cache (REQUIRED FIRST)
- **`release_control`** - Release device lock when done

### 🎮 **Action Tools**
- **`execute_device_action`** - Execute remote/ADB/web/desktop commands

### 🗺️ **Navigation Tools**
- **`navigate_to_node`** - Navigate through UI trees with pathfinding

### ✅ **Verification Tools**
- **`verify_device_state`** - Verify UI elements, video, text, ADB states

### 🧪 **TestCase Tools**
- **`execute_testcase`** - Run complete test cases from graph JSON

### 🤖 **AI Tools**
- **`generate_test_graph`** - Generate tests from natural language

### 📸 **Screenshot Tools**
- **`capture_screenshot`** - Capture screenshots for AI vision analysis

### 📝 **Transcript Tools**
- **`get_transcript`** - Fetch audio transcripts with translation

### ℹ️ **Device Tools**
- **`get_device_info`** - Get device capabilities and status
- **`get_execution_status`** - Poll async execution status

---

## 📋 Prerequisites

### Installation

```bash
cd backend_server
pip install -r requirements.txt
```

The `mcp>=1.0.0` package is included in requirements.txt.

### Configuration

Set the backend_server URL (default: `http://localhost:5001`):

```bash
export SERVER_BASE_URL=http://localhost:5001
```

---

## 🚀 Quick Start

### 1. Start the MCP Server

```bash
cd backend_server/src/mcp
python mcp_server.py
```

### 2. Example LLM Workflow

```python
# Step 1: ALWAYS take control first
take_control({
    "host_name": "ubuntu-host-1",
    "device_id": "device1",
    "team_id": "team_abc123",
    "tree_id": "main_navigation"  # Generates navigation cache
})

# Step 2: Perform operations
navigate_to_node({
    "tree_id": "main_navigation",
    "userinterface_name": "horizon_android_tv",
    "target_node_label": "Settings",
    "device_id": "device1",
    "team_id": "team_abc123"
})

# Step 3: Capture screenshot for vision analysis
capture_screenshot({
    "device_id": "device1",
    "team_id": "team_abc123"
})
# Returns: base64 image for AI vision

# Step 4: Release control when done
release_control({
    "host_name": "ubuntu-host-1",
    "device_id": "device1",
    "team_id": "team_abc123"
})
```

---

## 🔑 Critical: take_control

**⚠️ `take_control` MUST be called before ANY device operations!**

### What it does:
1. **Locks Device** - Prevents other users/sessions from interfering
2. **Session Management** - Creates session_id for tracking
3. **Cache Generation** - Generates unified navigation graph (if tree_id provided)
4. **Host Validation** - Ensures host is registered and reachable

### Without take_control:
- ❌ Actions will fail (device not locked)
- ❌ Navigation will fail (cache not ready)
- ❌ Verification will fail (cache not ready)
- ❌ Testcases will fail (cache not ready)

### Parameters:
```json
{
  "host_name": "ubuntu-host-1",    // REQUIRED
  "device_id": "device1",           // REQUIRED
  "team_id": "team_abc123",         // REQUIRED
  "tree_id": "main_navigation"      // OPTIONAL (triggers cache)
}
```

### Returns:
```json
{
  "success": true,
  "session_id": "abc-123-def-456",
  "cache_ready": true,
  "host_name": "ubuntu-host-1",
  "device_id": "device1"
}
```

---

## 🛠️ Tool Reference

### execute_device_action

Execute batch of remote/ADB/web/desktop commands.

```json
{
  "device_id": "device1",
  "team_id": "team_abc123",
  "actions": [
    {"command": "KEY_HOME", "params": {}, "delay": 500},
    {"command": "KEY_DOWN", "params": {}, "delay": 300}
  ]
}
```

**Returns**: `execution_id` for async polling

---

### navigate_to_node

Navigate to target UI node using pathfinding.

```json
{
  "tree_id": "main_navigation",
  "userinterface_name": "horizon_android_tv",  // MANDATORY
  "target_node_label": "Settings",
  "device_id": "device1",
  "team_id": "team_abc123"
}
```

**Returns**: Navigation path + results

---

### capture_screenshot

Capture screenshot for AI vision analysis.

```json
{
  "device_id": "device1",
  "team_id": "team_abc123",
  "include_ui_dump": false  // Optional: include UI hierarchy
}
```

**Returns**: `screenshot_base64` (ready for vision APIs)

---

### generate_test_graph

Generate test case from natural language.

```json
{
  "prompt": "Navigate to Settings and enable subtitles",
  "device_id": "device1",
  "team_id": "team_abc123",
  "userinterface_name": "horizon_android_tv"
}
```

**Returns**: `graph` JSON + `analysis`

---

## 🔄 Async Execution & Polling

Long-running operations return `execution_id`:

```python
# Execute action
result = execute_device_action({...})
execution_id = result['execution_id']

# Poll status
status = get_execution_status({
    "execution_id": execution_id,
    "operation_type": "action"  # or 'testcase', 'ai'
})

# status: 'running', 'completed', 'failed'
```

---

## 📁 Architecture

```
backend_server/src/mcp/
├── mcp_server.py          # Main MCP server
├── tools/
│   ├── control_tools.py   # take_control, release_control
│   ├── action_tools.py    # execute_device_action
│   ├── navigation_tools.py # navigate_to_node
│   ├── verification_tools.py # verify_device_state
│   ├── testcase_tools.py  # execute_testcase
│   ├── ai_tools.py        # generate_test_graph
│   ├── screenshot_tools.py # capture_screenshot
│   ├── transcript_tools.py # get_transcript
│   └── device_tools.py    # get_device_info, get_execution_status
├── config/
│   └── tools_config.json  # Tool definitions & schemas
└── utils/
    ├── api_client.py      # HTTP client for backend_server
    └── response_formatter.py # MCP response formatting
```

---

## 🌐 API Flow

```
LLM → MCP Server → Backend Server → Backend Host → Device
                      (routes)       (executors)   (controllers)
```

**Example**:
```
1. LLM calls: take_control(device_id, team_id, tree_id)
2. MCP → POST /server/control/takeControl
3. Backend → Locks device + generates cache
4. Returns: session_id, cache_ready=true
```

---

## 🔒 Security

- All operations require `team_id` for access control
- Device locking prevents concurrent access conflicts
- Session management tracks active control sessions

---

## 📊 Monitoring

MCP server logs all operations:

```bash
tail -f mcp_server.log
```

Available tools on startup:
```
[INFO] VirtualPyTest MCP Server initialized with 11 tools
[INFO] Available tools:
  - take_control: Lock device and generate cache
  - release_control: Release device lock
  - execute_device_action: Execute commands
  ...
```

---

## 🐛 Troubleshooting

### Error: "Device not found"
- Ensure `take_control` was called first
- Check device_id is correct
- Verify host is registered

### Error: "Cache not ready"
- Call `take_control` with `tree_id` parameter
- Wait for `cache_ready: true` response

### Error: "Device locked by another session"
- Another user/LLM has control
- Wait for release or use different device

---

## 📝 Complete Example

```python
# Full automation workflow
from mcp_client import MCPClient

client = MCPClient()

# 1. Take control (CRITICAL FIRST STEP)
control = client.call_tool("take_control", {
    "host_name": "ubuntu-host-1",
    "device_id": "device1",
    "team_id": "team_abc123",
    "tree_id": "main_navigation"
})
print(f"Control acquired: {control['session_id']}")

# 2. Navigate to target
nav = client.call_tool("navigate_to_node", {
    "tree_id": "main_navigation",
    "userinterface_name": "horizon_android_tv",
    "target_node_label": "Settings",
    "device_id": "device1",
    "team_id": "team_abc123"
})
print(f"Navigation: {nav['message']}")

# 3. Capture screenshot for vision
screenshot = client.call_tool("capture_screenshot", {
    "device_id": "device1",
    "team_id": "team_abc123"
})
image_base64 = screenshot['screenshot_base64']

# 4. Analyze screenshot with vision AI
# (Use image_base64 with Claude/GPT-4V)

# 5. Execute verification
verify = client.call_tool("verify_device_state", {
    "device_id": "device1",
    "team_id": "team_abc123",
    "userinterface_name": "horizon_android_tv",
    "verifications": [
        {
            "type": "image",
            "method": "DetectReference",
            "params": {"reference_id": "settings_icon"},
            "expected": True
        }
    ]
})
print(f"Verification: {verify['results']}")

# 6. Release control (ALWAYS AT END)
client.call_tool("release_control", {
    "host_name": "ubuntu-host-1",
    "device_id": "device1",
    "team_id": "team_abc123"
})
print("Control released")
```

---

## 🚀 Integration with LLMs

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "virtualpytest": {
      "command": "python",
      "args": ["/path/to/backend_server/src/mcp/mcp_server.py"]
    }
  }
}
```

### ChatGPT

Use MCP client library to expose tools to ChatGPT API.

---

## 📚 Additional Resources

- **API Routes**: See `backend_server/src/routes/`
- **Executors**: See `backend_host/src/services/`
- **Tool Config**: See `backend_server/src/mcp/config/tools_config.json`

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-04

