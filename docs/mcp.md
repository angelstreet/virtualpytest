# VirtualPyTest MCP Server

## Overview

**MCP (Model Context Protocol) Server** for VirtualPyTest enables external LLMs (Claude, ChatGPT, etc.) to control and automate physical devices through a standardized HTTP protocol.

**Endpoint**: `https://dev.virtualpytest.com/mcp`  
**Authentication**: Bearer token (required)  
**Transport**: HTTP/HTTPS

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

### Security Configuration

**1. Generate a secure secret:**
```bash
python3 -c "import secrets; print(f'vpt_mcp_{secrets.token_urlsafe(32)}')"
```

**2. Add to backend_server `.env`:**
```bash
MCP_SECRET_KEY=vpt_mcp_X3k9Vp2mQrYn8TzL4jWh6Ns1Fb7Gd5Mc9Ae0Rb3Kt8
```

**3. Configure Cursor (`~/.cursor/mcp.json`):**
```json
{
  "mcpServers": {
    "virtualpytest": {
      "url": "https://dev.virtualpytest.com/mcp",
      "transport": {
        "type": "http"
      },
      "headers": {
        "Authorization": "Bearer vpt_mcp_X3k9Vp2mQrYn8TzL4jWh6Ns1Fb7Gd5Mc9Ae0Rb3Kt8"
      }
    }
  }
}
```

**⚠️ Important:** Secret must match in both `.env` and `mcp.json`!

**4. Restart:**
- Restart backend_server (to load `.env`)
- Restart Cursor (Cmd+Q, reopen)

---

## 🚀 Quick Start

### 1. Verify MCP Endpoint

The MCP server runs as an HTTP endpoint on your backend_server:

```bash
# Test health endpoint (requires auth)
curl -H "Authorization: Bearer vpt_mcp_secret_key_2025" \
     https://dev.virtualpytest.com/mcp/health

# Expected response:
# {"status": "healthy", "mcp_version": "1.0.0", "tools_count": 11}
```

### 2. Example LLM Workflow (via Cursor)

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

## 🌐 Architecture & API Flow

### HTTP MCP Architecture

```
Cursor (Your Mac)
    ↓ HTTPS with Bearer token
https://dev.virtualpytest.com/mcp  (HTTP endpoint)
    ↓ Local calls
Backend Server routes
    ↓ SSH/HTTP
Backend Host (remote)
    ↓
Physical Devices
```

### API Flow Example

```
1. Cursor makes HTTP POST request:
   POST https://dev.virtualpytest.com/mcp
   Headers: Authorization: Bearer <token>
   Body: {
     "tool": "take_control",
     "params": {
       "host_name": "ubuntu-host-1",
       "device_id": "device1",
       "team_id": "team_abc123",
       "tree_id": "main_navigation"
     }
   }

2. MCP endpoint validates Bearer token

3. Calls: POST /server/control/takeControl

4. Backend locks device + generates cache

5. Returns: {
     "content": [{
       "type": "text",
       "text": "{\"session_id\": \"xyz\", \"cache_ready\": true}"
     }]
   }
```

---

## 🔒 Security

### Bearer Token Authentication

All MCP endpoints require Bearer token authentication:

```bash
Authorization: Bearer <your_secret_key>
```

**How It Works:**

1. **Generate random token** (cryptographically secure random string):
   ```bash
   python3 -c "import secrets; print(f'vpt_mcp_{secrets.token_urlsafe(32)}')"
   ```

2. **Store in both places:**
   - Backend: `MCP_SECRET_KEY` in `.env`
   - Cursor: `Authorization: Bearer <token>` in `mcp.json`

3. **Validation is simple string comparison:**
   ```
   Cursor sends: Authorization: Bearer vpt_mcp_abc123...
   Backend reads token from header
   Backend compares: received_token == MCP_SECRET_KEY
   If match → Allow ✅
   If not → 403 Forbidden ❌
   ```

No encryption, no JWT, no database - just a **shared secret** with HTTPS transport security.

### Security Features

✅ **Bearer Token Required** - All endpoints protected  
✅ **Environment Variable** - Secret stored in `.env`, not hardcoded  
✅ **401 Unauthorized** - Missing auth header  
✅ **403 Forbidden** - Invalid token  
✅ **Team-based Access** - All operations require `team_id`  
✅ **Device Locking** - Prevents concurrent access  
✅ **Session Tracking** - Audit trail for all operations  

### Protected Endpoints

- `POST /mcp` - Tool execution
- `GET /mcp/tools` - List available tools
- `GET /mcp/health` - Health check

### Rotating Secrets

```bash
# 1. Generate new secret
python3 -c "import secrets; print(f'vpt_mcp_{secrets.token_urlsafe(32)}')"

# 2. Update backend_server/.env
MCP_SECRET_KEY=<new_secret>

# 3. Restart backend_server

# 4. Update ~/.cursor/mcp.json
"Authorization": "Bearer <new_secret>"

# 5. Restart Cursor
```

### Best Practices

1. ✅ **Never commit secrets** to git
2. ✅ **Use strong random secrets** (32+ characters)
3. ✅ **Different secrets per environment** (dev/prod)
4. ✅ **Rotate secrets periodically** (every 90 days)
5. ✅ **Keep Cursor config local** (~/.cursor/mcp.json is not synced)

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

### Authentication Errors

**"Missing Authorization header"**
- Add `headers` section to Cursor MCP config
- Ensure Bearer token is included
- Format: `Authorization: Bearer <token>`

**"Invalid MCP authentication token"**
- Check secret matches in both `.env` and `mcp.json`
- Restart backend_server after changing `.env`
- Restart Cursor after changing `mcp.json`

**"Invalid Authorization header format"**
- Ensure format is: `Bearer <token>` (space after "Bearer")
- Check for extra spaces or newlines

### MCP Tools Not Showing in Cursor

- Restart Cursor completely (Cmd+Q, then reopen)
- Check `~/.cursor/mcp.json` exists and is valid JSON
- Verify URL is correct: `https://dev.virtualpytest.com/mcp`
- Test health endpoint manually with curl

### Device Operation Errors

**"Device not found"**
- Ensure `take_control` was called first
- Check device_id is correct
- Verify host is registered

**"Cache not ready"**
- Call `take_control` with `tree_id` parameter
- Wait for `cache_ready: true` response

**"Device locked by another session"**
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

### Cursor (Primary Integration)

**Configuration**: `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "virtualpytest": {
      "url": "https://dev.virtualpytest.com/mcp",
      "transport": {
        "type": "http"
      },
      "headers": {
        "Authorization": "Bearer vpt_mcp_your_secret_here"
      }
    }
  }
}
```

After configuration:
1. Restart Cursor (Cmd+Q, reopen)
2. Open chat window
3. Look for "🔌 MCP Tools" - you'll see 11 VirtualPyTest tools
4. Use natural language to control devices!

**Example prompts:**
- "Take control of device1 on ubuntu-host-1 with team abc123"
- "Navigate to Settings page"
- "Capture a screenshot"
- "Execute remote command KEY_HOME"

### Multiple Environments

Configure dev and prod separately:

```json
{
  "mcpServers": {
    "virtualpytest-dev": {
      "url": "https://dev.virtualpytest.com/mcp",
      "headers": {
        "Authorization": "Bearer dev_secret_here"
      }
    },
    "virtualpytest-prod": {
      "url": "https://prod.virtualpytest.com/mcp",
      "headers": {
        "Authorization": "Bearer prod_secret_here"
      }
    }
  }
}
```

### Claude Desktop / Other LLMs

Same HTTP endpoint can be used by any MCP-compatible client:

```json
{
  "mcpServers": {
    "virtualpytest": {
      "url": "https://dev.virtualpytest.com/mcp",
      "headers": {
        "Authorization": "Bearer <your_secret>"
      }
    }
  }
}
```

---

## 📚 Additional Resources

- **API Routes**: See `backend_server/src/routes/`
- **Executors**: See `backend_host/src/services/`
- **Tool Config**: See `backend_server/src/mcp/config/tools_config.json`

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-04

