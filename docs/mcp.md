# VirtualPyTest MCP Server

## Overview

**MCP (Model Context Protocol) Server** for VirtualPyTest enables external LLMs (Claude, ChatGPT, etc.) to control and automate physical devices through a standardized HTTP protocol.

**Endpoint**: `https://dev.virtualpytest.com/server/mcp`  
**Authentication**: Bearer token (required)  
**Transport**: HTTP/HTTPS

---

## 🎯 Core Capabilities

The MCP server exposes **21 tools** for complete device automation:

### 🔐 **Control Tools** (CRITICAL - MUST BE FIRST)
- **`take_control`** - Lock device & generate navigation cache (REQUIRED FIRST)
- **`release_control`** - Release device lock when done

### 🎮 **Action Tools**
- **`list_actions`** - List available actions for a device
- **`execute_device_action`** - Execute remote/ADB/web/desktop commands (async with polling)

### 🗺️ **Navigation Tools**
- **`list_navigation_nodes`** - List available navigation nodes in a tree
- **`navigate_to_node`** - Navigate through UI trees with pathfinding (async with polling)

### ✅ **Verification Tools**
- **`list_verifications`** - List available verification types for a device
- **`verify_device_state`** - Verify UI elements, video, text, ADB states (async with polling)

### 🧪 **TestCase Tools**
- **`save_testcase`** - Save test case graph to database
- **`list_testcases`** - List all saved test cases
- **`load_testcase`** - Load saved test case by ID
- **`execute_testcase`** - Run complete test cases from graph JSON (async with polling)
- **`execute_testcase_by_id`** - Load and execute saved test case in one call (convenience wrapper)

### 🐍 **Script Tools**
- **`execute_script`** - Execute Python scripts with CLI parameters (async with polling)

### 🤖 **AI Tools**
- **`generate_test_graph`** - Generate tests from natural language (handles disambiguation)

### 📸 **Screenshot Tools**
- **`capture_screenshot`** - Capture screenshots for AI vision analysis (returns base64)

### 📝 **Transcript Tools**
- **`get_transcript`** - Fetch audio transcripts with translation

### ℹ️ **Device & System Tools**
- **`get_device_info`** - Get device capabilities and status
- **`get_execution_status`** - Poll async execution status
- **`list_services`** - List available systemd services
- **`view_logs`** - View systemd service logs via journalctl

---

## 📋 Prerequisites

### Installation

```bash
cd backend_server
pip install -r requirements.txt
```

**Required packages:**
- `mcp>=1.0.0` - MCP protocol support
- `jsonschema>=4.0.0` - Input validation (NEW)
- `requests>=2.31.0` - HTTP client
- `flask>=2.3.0` - Web framework

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
      "url": "https://dev.virtualpytest.com/server/mcp",
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
     https://dev.virtualpytest.com/server/mcp/health

# Expected response:
# {"status": "healthy", "mcp_version": "1.0.0", "tools_count": 21}
```

### 2. Discover Available Commands (NEW!)

Before executing commands, discover what's available on your device:

```python
# Step 0: Take control first (ALWAYS REQUIRED)
take_control({
    "tree_id": "main_navigation",
    "device_id": "device1",
    "host_name": "sunri-pi1"
})

# Step 1: Discover available actions
list_actions({
    "device_id": "device1",
    "host_name": "sunri-pi1"
})
# Returns: Categorized list (remote, adb, web, desktop) with commands & params

# Step 2: Discover available verifications
list_verifications({
    "device_id": "device1",
    "host_name": "sunri-pi1"
})
# Returns: Categorized list (image, text, adb, video) with methods & params

# Step 3: Discover available navigation nodes
list_navigation_nodes({
    "tree_id": "main_navigation"
})
# Returns: List of nodes with labels, IDs, types, positions

# Now you know exactly what commands/verifications/nodes are available!
```

### 3. Example LLM Workflow (via Cursor)

**Simplified workflow with discovery:**
```python
# Step 1: ALWAYS take control first
take_control({
    "tree_id": "main_navigation"  # Uses default host/device/team
})

# Step 2: Discover what's available (optional but recommended)
actions = list_actions({})  # Uses defaults
nodes = list_navigation_nodes({"tree_id": "main_navigation"})

# Step 3: Execute commands
execute_device_action({
    "actions": [
        {"command": "swipe_up", "params": {}, "delay": 500}
    ]
})
# Returns: execution_id, polls automatically until complete

# Step 4: Navigate to target
navigate_to_node({
    "tree_id": "main_navigation",
    "userinterface_name": "horizon_android_mobile",
    "target_node_label": "home_saved"
})
# Returns: Success with path taken, polls automatically

# Step 5: Verify element exists
verify_device_state({
    "userinterface_name": "horizon_android_mobile",
    "verifications": [{
        "command": "waitForElementToAppear",
        "params": {"search_term": "Replay", "timeout": 5},
        "verification_type": "adb"
    }]
})
# Returns: Verification results (passed/failed)

# Step 6: Capture screenshot for vision analysis
capture_screenshot({})  # All params optional with defaults
# Returns: base64 image for AI vision

# Step 7: Release control when done (ALWAYS!)
release_control({})  # Uses default host/device/team
```

**Using defaults (recommended):**
```python
# All parameters are optional if using defaults:
# - device_id: 'device1'
# - host_name: 'sunri-pi1'  
# - team_id: 'team_1'

take_control({"tree_id": "main_navigation"})
list_actions({})
execute_device_action({"actions": [...]})
navigate_to_node({"tree_id": "...", "userinterface_name": "...", "target_node_label": "..."})
verify_device_state({"userinterface_name": "...", "verifications": [...]})
release_control({})
```

---

## 🔑 Smart Defaults & Configuration

### Default Values (NEW in 2025)

The MCP server now provides smart defaults for common parameters, making tool calls more convenient:

```python
# Defaults from shared/src/lib/config/constants.py
DEFAULT_TEAM_ID = os.getenv('DEFAULT_TEAM_ID', 'team_1')
DEFAULT_HOST_NAME = os.getenv('DEFAULT_HOST_NAME', 'sunri-pi1')
DEFAULT_DEVICE_ID = os.getenv('DEFAULT_DEVICE_ID', 'device_1')
```

### Optional Parameters

These parameters are now **optional** in most tool calls:
- `team_id` (defaults to `team_1` or `$DEFAULT_TEAM_ID`)
- `host_name` (defaults to `sunri-pi1` or `$DEFAULT_HOST_NAME`)
- `device_id` (defaults to `device_1` or `$DEFAULT_DEVICE_ID`)

### Example: Simplified Tool Calls

**Before (verbose):**
```python
take_control({
    "host_name": "sunri-pi1",
    "device_id": "device_1",
    "team_id": "team_1",
    "tree_id": "main_navigation"
})
```

**After (concise with defaults):**
```python
take_control({
    "tree_id": "main_navigation"  # Other params use defaults
})
```

### Custom Defaults

Override defaults via environment variables:

```bash
# backend_server/.env
DEFAULT_TEAM_ID=my_team
DEFAULT_HOST_NAME=my_host
DEFAULT_DEVICE_ID=my_device
```

---

## ✅ Input Validation

### JSON Schema Validation (NEW)

All tool inputs are validated against JSON Schema **before** execution:

**Benefits:**
- ❌ Invalid data rejected immediately
- 📋 Clear validation error messages
- 🛡️ Type safety (string, integer, boolean, etc.)
- 🔒 Required field enforcement
- 📊 Array/object structure validation

**Example Validation Error:**
```json
{
  "content": [{
    "type": "text",
    "text": "Validation failed for take_control: 'tree_id' must be string, got integer"
  }],
  "isError": true
}
```

### Error Categories

The MCP server categorizes errors for better handling:

```python
class ErrorCategory(str, Enum):
    VALIDATION = "validation"      # Invalid input (jsonschema)
    TIMEOUT = "timeout"            # Request timeout
    NETWORK = "network"            # Network error
    BACKEND = "backend"            # Backend API error
    NOT_FOUND = "not_found"        # Resource not found
    UNAUTHORIZED = "unauthorized"   # Auth failure
    UNKNOWN = "unknown"            # Unexpected error
```

**Example Error Response:**
```json
{
  "content": [{
    "type": "text",
    "text": "Error: Device not found"
  }],
  "isError": true,
  "_error_category": "not_found",
  "_error_details": {
    "device_id": "invalid_device",
    "host_name": "sunri-pi1"
  }
}
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

**Example:**
```python
result = execute_device_action({
    "actions": [
        {"command": "swipe_up", "params": {}, "delay": 500}
    ]
})
# MCP automatically polls until completion (max 180s)
# Returns: ✅ Action execution completed: 1/1 passed
```

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

---

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
├── mcp_server.py          # Main MCP server (synchronous)
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
    ├── api_client.py      # Reusable HTTP client (raw responses)
    ├── mcp_formatter.py   # MCP response formatting (7 error categories)
    └── input_validator.py # JSON Schema validation (NEW)
```

### Architecture Principles (2025 Update)

**✅ Clean Separation of Concerns:**
- **API Client** - Returns raw responses, reusable outside MCP
- **MCPFormatter** - Converts raw responses to MCP format
- **InputValidator** - Validates all inputs against JSON Schema
- **Tool Classes** - Pure business logic, minimal boilerplate

**✅ Production-Ready Quality:**
- **Synchronous Execution** - No asyncio overhead
- **Input Validation** - All parameters validated before execution
- **Error Categorization** - 7 error types (validation, timeout, network, backend, not_found, unauthorized, unknown)
- **Smart Defaults** - Optional `team_id`, `host_name`, `device_id` with sensible fallbacks
- **No Legacy Code** - Clean implementation, no backward compatibility cruft

---

## 🌐 Architecture & API Flow

### HTTP MCP Architecture

```
Cursor (Your Mac)
    ↓ HTTPS with Bearer token
https://dev.virtualpytest.com/server/mcp  (HTTP endpoint)
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
   POST https://dev.virtualpytest.com/server/mcp
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
- Verify URL is correct: `https://dev.virtualpytest.com/server/mcp`
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
      "url": "https://dev.virtualpytest.com/server/mcp",
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
      "url": "https://dev.virtualpytest.com/server/mcp",
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
      "url": "https://dev.virtualpytest.com/server/mcp",
      "headers": {
        "Authorization": "Bearer <your_secret>"
      }
    }
  }
}
```

---

## 🎤 MCP Playground - Web Interface (NEW!)

### Overview

The **MCP Playground** is a mobile-first web interface for executing MCP commands through natural language prompts with voice support. It provides a simplified, user-friendly alternative to the Test Case Builder for quick device automation.

**URL**: `https://dev.virtualpytest.com/builder/mcp-playground`

### Key Features

✅ **Voice-First Design**
- Web Speech API integration
- Real-time voice transcription
- Hold-to-speak button
- Automatic text-to-prompt conversion

✅ **Mobile-First Responsive**
- Single-column layout on mobile (< 768px)
- Two-column layout on tablet (768px - 1024px)
- Three-column layout on desktop (> 1024px)
- Large touch targets (56px on mobile, 40px on desktop)
- Collapsible sections for mobile

✅ **Discovery & Suggestions**
- Browse available actions, verifications, and navigation nodes
- Quick-action buttons for common commands
- Real-time device capability detection

✅ **AI-Powered Execution**
- Natural language prompt to executable command
- Automatic disambiguation handling
- Real-time execution progress
- Success/failure feedback

✅ **Command History**
- Persistent history (localStorage)
- Replay previous commands
- Success/failure indicators
- Last 50 commands stored

### User Interface Layout

#### Mobile Layout (< 768px)
```
┌─────────────────────────┐
│ 🎤 MCP Playground       │ ← Header
├─────────────────────────┤
│ Device Selection ▼      │ ← Collapsible
│ Prompt Input (large)    │ ← Full-width
│ 🎤 Voice | ⚡ Execute   │ ← Large buttons
│ Execution Result        │ ← Auto-expand
│ Quick Actions ▼         │ ← Collapsible
│ History ▼               │ ← Collapsible
└─────────────────────────┘
```

#### Desktop Layout (> 1024px)
```
┌───────────────────────────────────────────────────┐
│ 🎤 MCP Playground                                 │
├─────────────┬───────────────────┬─────────────────┤
│ Device      │   Prompt Input    │  Quick Actions  │
│ Selection   │                   │                 │
│             │   🎤 Voice        │  • Navigate...  │
│ [Control]   │   ⚡ Execute      │  • Screenshot   │
│             │                   │  • Swipe...     │
│             ├───────────────────┤                 │
│ History     │ Execution Result  │  [Show all ▾]  │
│             │                   │                 │
│ 1. Nav...   │ ✅ Success        │                 │
│ 2. Verify.. │ ⏱️  2.3s          │                 │
└─────────────┴───────────────────┴─────────────────┘
```

### Workflow

1. **Select Device**
   - Choose host, device ID, and interface from dropdowns
   - Device selector collapses on mobile, persistent on desktop

2. **Take Control**
   - Single button to lock device
   - Clear visual feedback (green = locked, gray = unlocked)
   - Control state persists across commands

3. **Enter Prompt**
   - Type in large text area (4 rows on mobile, 2 on desktop)
   - OR hold voice button to speak
   - Real-time voice transcription display

4. **Quick Actions (Optional)**
   - Browse available commands by category (Navigation, Actions, Verification)
   - Click to auto-fill prompt
   - Stats chips show available counts

5. **Execute**
   - Click "Execute" button (or Cmd/Ctrl + Enter)
   - AI generates test graph from prompt
   - Handles disambiguation automatically (modal popup)
   - Shows real-time progress bar during execution

6. **View Result**
   - Success/failure alert with duration
   - Step-by-step block status
   - Error messages if failed
   - Link to detailed report

7. **Replay from History**
   - Click any previous command to reload
   - Success/failure indicators
   - Timestamps (relative time)
   - Clear history button

### Component Architecture

```
MCPPlayground.tsx (Main Page)
├── MCPPlaygroundContext.tsx (State Management)
│   ├── Device selection & control
│   ├── Available options (interfaces, nodes, actions, verifications)
│   ├── AI prompt generation & execution
│   ├── Command history (localStorage)
│   └── Unified execution state
│
├── MCPDeviceSelector.tsx (Responsive)
│   ├── Host/device/interface dropdowns
│   ├── Take/Release control button
│   └── Collapsible on mobile
│
├── MCPPromptInput.tsx (Responsive)
│   ├── Large text input
│   ├── Voice button (Web Speech API)
│   ├── Real-time transcription
│   └── Execute button (Cmd/Ctrl + Enter)
│
├── MCPQuickActions.tsx (Responsive)
│   ├── Tabbed interface (Navigation, Actions, Verification)
│   ├── Quick-click suggestions
│   └── Stats chips
│
├── MCPExecutionResult.tsx (Responsive)
│   ├── Progress bar (during execution)
│   ├── Success/failure alert
│   ├── Block-by-block status
│   └── Report link
│
└── MCPCommandHistory.tsx (Responsive)
    ├── Last 50 commands
    ├── Replay button
    ├── Success/failure indicators
    └── Relative timestamps
```

### Voice Input Details

**Supported Browsers:**
- ✅ Chrome/Edge (desktop & mobile)
- ✅ Safari (iOS & macOS)
- ❌ Firefox (limited support)

**Usage:**
1. Click "Voice" button
2. Allow microphone access (browser will prompt)
3. Speak your command clearly
4. Watch real-time transcription
5. Click "Stop" to finish
6. Transcript auto-appends to prompt text

**Tips:**
- Speak slowly and clearly
- Use natural language (e.g., "Navigate to home and take a screenshot")
- Pause between phrases for better accuracy
- Background noise may affect accuracy

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + Enter` | Execute prompt |
| `Cmd/Ctrl + K` | Focus prompt input |
| `Escape` | Clear prompt (when focused) |

### Local Storage

The MCP Playground stores data locally in your browser:

```javascript
localStorage.setItem('mcp-playground-history', JSON.stringify([
  {
    timestamp: "2025-01-01T00:00:00Z",
    prompt: "Navigate to home",
    success: true,
    result: {...}
  }
]))
```

**Data Stored:**
- Last 50 commands
- Timestamps
- Success/failure status
- Result summaries

**Privacy:**
- Data stored locally only (not sent to server)
- Clear history anytime with "Clear" button
- Data persists across browser sessions

### Mobile Optimizations

✅ **Touch Targets:**
- Minimum 56px height on mobile
- Large button spacing (16px gaps)
- Full-width buttons on mobile

✅ **Font Sizes:**
- Body text: 16px (mobile) → 14px (desktop)
- Headers: 20px (mobile) → 16px (desktop)
- Inputs: 16px minimum (prevents iOS zoom)

✅ **Gestures:**
- Tap to expand/collapse sections
- Swipe-friendly dropdowns
- No hover states (click-only)

✅ **Performance:**
- Lazy-loaded components
- Debounced voice input
- Cached available options

### Use Cases

#### 1. Quick Smoke Test
```
1. Take control
2. Type: "Navigate to home and verify Replay button"
3. Execute
4. Done in seconds!
```

#### 2. Voice-Driven Testing (Mobile)
```
1. Take control
2. Hold voice button
3. Speak: "Swipe up three times and take a screenshot"
4. Release voice button
5. Execute
6. Perfect for on-the-go testing!
```

#### 3. Exploratory Testing
```
1. Browse Quick Actions
2. Click "Navigate to settings"
3. Execute
4. See available verifications
5. Click "Verify element exists"
6. Execute
7. Iterate quickly!
```

#### 4. Regression from History
```
1. Open History
2. Replay previous successful command
3. Verify still works
4. Fast regression testing!
```

### Comparison: MCP Playground vs Test Case Builder

| Feature | MCP Playground | Test Case Builder |
|---------|----------------|-------------------|
| **Focus** | Quick commands | Full test cases |
| **Interface** | Text prompt | Visual canvas |
| **Input** | Type or speak | Drag & drop blocks |
| **Mobile** | Optimized ✅ | Desktop-only |
| **Voice** | Built-in ✅ | Not available |
| **History** | Last 50 commands | Saved test cases |
| **Complexity** | Simple | Advanced |
| **Use Case** | Quick testing | Complex workflows |
| **Save** | Local history | Database |
| **Target** | Mobile-first | Desktop power users |

### Integration with MCP Tools

The MCP Playground uses the same backend MCP tools:

```
User Types Prompt
    ↓
MCPPlaygroundContext.handleGenerate()
    ↓
useTestCaseAI.generateTestGraph()
    ↓
Backend: /server/testcase/ai/generate
    ↓
Returns: Test graph JSON
    ↓
useTestCaseExecution.executeTestCase()
    ↓
Backend: /server/testcase/execute
    ↓
Polls: /server/testcase/execution/<id>/status
    ↓
Returns: Success/failure
    ↓
Display result + update history
```

**No new backend code needed!** The playground reuses all existing MCP tools and execution infrastructure.

### Best Practices

✅ **Discovery First:**
- Use `list_actions`, `list_verifications`, `list_navigation_nodes` to see what's available
- Browse Quick Actions before typing

✅ **Natural Language:**
- Write prompts as you would speak them
- Example: "Navigate to home and verify the Replay button exists"
- Not: "nav home verify Replay"

✅ **Voice Tips:**
- Use in quiet environment
- Speak clearly and slowly
- Review transcript before executing

✅ **Mobile Usage:**
- Collapse sections you're not using (saves screen space)
- Use voice input for hands-free testing
- Landscape mode recommended for tablets

✅ **History Management:**
- Review history periodically
- Clear failed commands
- Replay successful commands for regression

### Troubleshooting

**Voice Not Working:**
- Check browser supports Web Speech API (Chrome/Safari)
- Allow microphone access in browser settings
- Check microphone not muted
- Try Safari if Chrome fails on iOS

**Prompt Not Executing:**
- Ensure device control is active (green button)
- Check host/device/interface selected
- Verify backend server running
- Check network connectivity

**Disambiguation Modal Won't Close:**
- Select resolution from dropdown
- Click "Resolve" button
- Or click "Cancel" to abort

**History Not Saving:**
- Check browser allows localStorage
- Check not in Private/Incognito mode
- Try clearing browser cache

---

## 📚 Additional Resources

- **API Routes**: See `backend_server/src/routes/`
- **Executors**: See `backend_host/src/services/`
- **Tool Config**: See `backend_server/src/mcp/config/tools_config.json`

---

**Version**: 3.0.0  
**Last Updated**: 2025-01-04

## 🎉 What's New in v3.0.0

### Major New Features

#### 🔍 Discovery Tools (No More Guessing!)
- ✅ **`list_actions`** - See all available device actions before executing
- ✅ **`list_verifications`** - Discover verification methods with parameters
- ✅ **`list_navigation_nodes`** - Browse navigation tree before navigating
- **Impact**: No more trial-and-error! Know exactly what's available on your device.

#### 🧪 Complete TestCase Management
- ✅ **`save_testcase`** - Save AI-generated graphs to database
- ✅ **`list_testcases`** - Browse all saved test cases with folders & tags
- ✅ **`load_testcase`** - Load saved test case by ID
- ✅ **`execute_testcase_by_id`** - One-call load + execute convenience wrapper
- **Impact**: Full test case lifecycle management from MCP!

#### 🐍 Script Execution
- ✅ **`execute_script`** - Run Python scripts with CLI parameters
- ✅ Automatic polling (up to 2 hours for long scripts)
- **Impact**: Execute existing Python validation scripts directly from MCP!

#### 🎤 MCP Playground - Web Interface
- ✅ **Mobile-first responsive design** (phone, tablet, desktop)
- ✅ **Voice input with Web Speech API** (speak your commands!)
- ✅ **Quick Actions browser** (discover & click to auto-fill)
- ✅ **Command History** (replay last 50 commands from localStorage)
- ✅ **Real-time execution progress** (see blocks execute live)
- ✅ **AI-powered natural language** (type or speak, AI handles the rest)
- **URL**: `https://dev.virtualpytest.com/builder/mcp-playground`
- **Impact**: Mobile-friendly testing with voice support!

### Enhanced Tools

#### ⏱️ Automatic Async Polling
- All async operations now poll automatically until completion
- No manual polling needed! MCP handles it for you
- `execute_device_action`: Polls up to 180s
- `navigate_to_node`: Polls up to 60s
- `verify_device_state`: Polls up to 30s
- `execute_testcase`: Polls up to 5 minutes
- `execute_script`: Polls up to 2 hours

#### 📝 Better Tool Descriptions
- Clear prerequisites documented in tool schemas
- Step-by-step workflow examples
- Mandatory vs optional parameters clarified
- Error handling guidance

### Architecture Improvements

- **21 tools** (up from 11 in v2.0.0)
- **Zero new backend routes** - all tools reuse existing endpoints
- **Frontend integration** - MCP Playground demonstrates MCP + React
- **Consistent patterns** - All discovery tools follow same structure
- **Async polling** - Unified polling mechanism across all tools

### Breaking Changes from v2.0.0

None! All v2.0.0 tool calls remain compatible:
- All existing parameters still work
- New tools are additive (don't replace existing)
- Default values unchanged
- Response formats unchanged

### Migration Guide

**No migration needed!** Your existing MCP integrations will continue to work.

**Optional Enhancements:**
1. Use discovery tools before executing commands (recommended)
2. Try the new MCP Playground web interface
3. Save frequently-used prompts as test cases
4. Execute scripts directly via `execute_script`

### Tool Count Evolution

- **v1.0.0** (2024): 11 tools (basic automation)
- **v2.0.0** (2025-01): 11 tools (production-ready quality)
- **v3.0.0** (2025-01): **21 tools** (complete automation suite + web UI)

---

## 📈 MCP Adoption & Usage

### Integration Points

The MCP server is now accessible from:

1. **Cursor IDE** - Primary integration (HTTP MCP)
2. **Claude Desktop** - HTTP MCP client
3. **MCP Playground** - Web interface (mobile-first)
4. **Custom Clients** - Any HTTP MCP-compatible client

### Popular Workflows

**Quick Device Test (via Playground):**
```
1. Open /builder/mcp-playground on mobile
2. Take control
3. Speak: "Navigate to home and verify Replay button"
4. Execute
5. Done!
```

**Comprehensive Test (via Cursor):**
```
1. take_control with tree_id
2. list_navigation_nodes to see targets
3. navigate_to_node to target
4. list_verifications to see options
5. verify_device_state to check elements
6. capture_screenshot for vision analysis
7. release_control
```

**Test Case Automation (via Cursor):**
```
1. generate_test_graph from natural language
2. save_testcase to database
3. execute_testcase_by_id when needed
4. Reusable automation!
```

---

## 🚀 Future Roadmap

### Planned Features (v4.0.0)

- 🎯 **Multi-device orchestration** - Control multiple devices simultaneously
- 🔄 **Batch operations** - Execute same command on device fleet
- 📊 **Analytics & reporting** - Aggregate results from MCP executions
- 🌐 **Multi-language support** - Voice input in multiple languages
- 💾 **Cloud history sync** - Sync command history across devices
- 🤖 **Smart suggestions** - Learn from history, suggest next actions

### Community Requests

Have ideas? Open an issue or PR on GitHub!

---