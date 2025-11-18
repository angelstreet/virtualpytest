# VirtualPyTest MCP Server Documentation

**Version**: 4.5.0  
**Last Updated**: 2025-11-18  
**Total Tools**: 54

This documentation has been modularized for easier navigation and maintenance.

---

## 📚 Quick Navigation

### Core Documentation
- **[MCP Core](mcp/mcp_core.md)** - Overview, architecture, prerequisites, setup, security, and quick start

### Tool Documentation by Category

#### 🔐 Control & Discovery
- **[Control Tools](mcp/mcp_tools_control.md)** (1 tool) - `take_control` ⚠️ **MUST BE FIRST**
- **[Action Tools](mcp/mcp_tools_action.md)** (2 tools) - `execute_device_action`, `list_actions` ⏱️ **[Wait Time Guidelines](mcp/mcp_tools_action.md#⏱️-action-wait-time-guidelines)**
- **[Navigation Tools](mcp/mcp_tools_navigation.md)** (3 tools) - `navigate_to_node`, `list_navigation_nodes`, `preview_userinterface` 🆕
- **[Verification Tools](mcp/mcp_tools_verification.md)** (4 tools) - `verify_device_state`, `verify_node`, `list_verifications`, `dump_ui_elements`

#### 🔧 Tree Building (Primitives)
- **[Tree Tools](mcp/mcp_tools_tree.md)** (11 tools) - Create/update/delete nodes/edges, subtrees, execute_edge, get_node, get_edge, save_node_screenshot

#### 🧪 Test Management
- **[TestCase Tools](mcp/mcp_tools_testcase.md)** (6 tools) - Save, load, list, execute, rename testcases
- **[Script Tools](mcp/mcp_tools_script.md)** (2 tools) - `execute_script`, `list_scripts`
- **[AI Tools](mcp/mcp_tools_ai.md)** (2 tools) - `generate_test_graph`, `generate_and_save_testcase`

#### 🎨 App & Requirements
- **[UserInterface Tools](mcp/mcp_tools_userinterface.md)** (6 tools) - Create/list/delete userinterfaces, nodes, edges
- **[Requirements Tools](mcp/mcp_tools_requirements.md)** (10 tools) - Requirements & coverage tracking

#### 📸 Media & Monitoring
- **[Screenshot Tools](mcp/mcp_tools_screenshot.md)** (1 tool) - `capture_screenshot`
- **Device Tools** (3 tools) - `get_device_info`, `get_compatible_hosts`, `get_execution_status` *(in mcp_core.md)*
- **Transcript Tools** (1 tool) - `get_transcript` *(in mcp_core.md)*
- **Logs Tools** (2 tools) - `view_logs`, `list_services` *(in mcp_core.md)*

### Additional Resources
- **[MCP Playground](mcp/mcp_playground.md)** - Web interface with voice input (mobile-first)

---

## 🚀 Quick Start Guide

### 1. Prerequisites & Setup
→ [Installation & Security Configuration](mcp/mcp_core.md#prerequisites)

### 2. First Steps
1. **[Take Control](mcp/mcp_tools_control.md)** - Lock device (CRITICAL FIRST STEP)
2. **[Discover Actions](mcp/mcp_tools_action.md#list_actions)** - See what commands are available
3. **[Execute Action](mcp/mcp_tools_action.md#execute_device_action)** - Swipe, tap, type
4. **[Navigate](mcp/mcp_tools_navigation.md)** - Move through UI tree
5. **[Verify State](mcp/mcp_tools_verification.md)** - Check elements exist

### 3. Advanced Usage
- **[Build Navigation Trees](mcp/mcp_tools_tree.md)** - Create nodes & edges
- **[Generate Tests with AI](mcp/mcp_tools_ai.md)** - Natural language → test case
- **[Manage Requirements](mcp/mcp_tools_requirements.md)** - Track coverage

---

## 📖 Common Workflows

### Quick Device Test
```
1. take_control (REQUIRED FIRST)
2. list_navigation_nodes (discover targets)
3. navigate_to_node (go to screen)
4. capture_screenshot (verify visually)
```
→ See: [Control](mcp/mcp_tools_control.md) | [Navigation](mcp/mcp_tools_navigation.md) | [Screenshot](mcp/mcp_tools_screenshot.md)

### Build Navigation Tree
```
1. create_userinterface (create app model)
2. dump_ui_elements (see what's on screen)
3. create_node (for each screen)
4. create_edge (navigation between screens)
5. save_node_screenshot (visual documentation)
```
→ See: [UserInterface](mcp/mcp_tools_userinterface.md) | [Tree Tools](mcp/mcp_tools_tree.md)

### Automated Testing
```
1. generate_test_graph (from natural language)
2. save_testcase (to database)
3. execute_testcase (run test)
4. link_testcase_to_requirement (track coverage)
```
→ See: [AI Tools](mcp/mcp_tools_ai.md) | [TestCase](mcp/mcp_tools_testcase.md) | [Requirements](mcp/mcp_tools_requirements.md)

---

## 🧭 Navigation Autonomy Concept

**CRITICAL UNDERSTANDING FOR AI TEST GENERATION:**

### The Two-Layer Architecture

**Layer 1: Navigation Tree (App-Specific)**
- Defines HOW to move between screens
- Contains explicit actions (click_element, press_key, etc.)
- Built once per app (Netflix, YouTube, etc.)
- Example: `home -(click "Play")→ player`

**Layer 2: Test Cases (Reusable)**
- Defines WHAT to test
- References navigation tree nodes by label
- Reusable across apps by changing `userinterface_name`
- Example: Navigate to "player" → Verify video plays

### Why This Matters

❌ **Wrong Approach (Manual Navigation in Test Cases):**
```json
{
  "type": "action",
  "data": {"command": "click_element", "text": "Play"}
}
```
*Problem: Hardcodes Netflix-specific actions, not reusable*

✅ **Correct Approach (Reference Navigation Tree):**
```json
{
  "type": "navigation",
  "data": {"target_node_label": "player"}
}
```
*Solution: Uses navigation tree, works for any streaming app*

### When to Use What

- **`navigate_to_node`**: Go to screens defined in navigation tree (DECLARATIVE)
- **`execute_device_action`**: One-off actions NOT part of navigation (pause video, adjust volume)
- **`verify_device_state`**: Check screen state after navigation

### Benefits

1. **Reusability**: Same test case works on Netflix, YouTube, Hulu
2. **Maintainability**: UI changes only affect navigation tree, not test cases
3. **Separation of Concerns**: Navigation logic vs. test logic
4. **Declarative Testing**: Say "go to player" not "click this, then that"

→ See: [Navigation Tools](mcp/mcp_tools_navigation.md) | [TestCase Tools](mcp/mcp_tools_testcase.md)

---

## 🎯 Tool Categories Overview

### By Functionality

**Discovery & Inspection** (5 tools)
- `list_actions`, `list_verifications`, `list_navigation_nodes`, `dump_ui_elements`, `preview_userinterface` 🆕

**Execution** (5 tools)
- `execute_device_action`, `navigate_to_node`, `verify_device_state`, `execute_edge`, `verify_node`

**Tree Management** (11 tools)
- `create_node`, `update_node`, `delete_node`, `create_edge`, `update_edge`, `delete_edge`, `create_subtree`, `get_node`, `get_edge`, `save_node_screenshot`, `dump_ui_elements`

**Test Management** (9 tools)
- `save_testcase`, `load_testcase`, `list_testcases`, `rename_testcase`, `execute_testcase`, `execute_testcase_by_id`, `execute_script`, `list_scripts`, `generate_test_graph`, `generate_and_save_testcase`

**App & Requirements** (16 tools)
- `create_userinterface`, `list_userinterfaces`, `delete_userinterface`, `list_nodes`, `list_edges`, `get_userinterface_complete`
- `create_requirement`, `update_requirement`, `get_requirement`, `list_requirements`, `link_testcase_to_requirement`, `unlink_testcase_from_requirement`, `get_testcase_requirements`, `get_requirement_coverage`, `get_coverage_summary`, `get_uncovered_requirements`

**Media & Monitoring** (7 tools)
- `capture_screenshot`, `save_node_screenshot`, `get_transcript`, `get_device_info`, `get_compatible_hosts`, `get_execution_status`, `view_logs`, `list_services`

---

## 🔗 Integration Options

### 1. Cursor IDE ⭐ PRIMARY
Native MCP integration via `~/.cursor/mcp.json`  
→ [Setup Guide](mcp/mcp_core.md#integration-with-llms)

### 2. Claude Desktop
HTTP MCP client configuration  
→ [Setup Guide](mcp/mcp_core.md#integration-with-llms)

### 3. MCP Playground
Web interface with voice input (mobile-first)  
→ [Full Documentation](mcp/mcp_playground.md)

---

## ⚠️ Important Notes

### Critical Prerequisites
- **`take_control` MUST be called first** before any device operations
- Bearer token authentication required for all endpoints
- Tree cache required for navigation operations

→ [Control Tools](mcp/mcp_tools_control.md)

### Smart Defaults
Most tools support optional parameters with sensible defaults:
- `team_id` → `team_1`
- `host_name` → `sunri-pi1`
- `device_id` → `device_1`

→ [Core Documentation - Smart Defaults](mcp/mcp_core.md#smart-defaults--configuration)

---

## 📊 Statistics

- **Total Tools**: 54
- **Tool Categories**: 12
- **Documentation Pages**: 13
- **Supported Integrations**: 3 (Cursor, Claude Desktop, MCP Playground)
- **Lines of Documentation**: 3,400+
- **MCP Server Code**: 327 lines (refactored from 2,028 lines)

---

## 🆘 Troubleshooting

### Common Issues

**Authentication errors**  
→ [Core Documentation - Troubleshooting](mcp/mcp_core.md#troubleshooting)

**Device not found**  
→ [Control Tools - Prerequisites](mcp/mcp_tools_control.md)

**Navigation failures**  
→ [Navigation Tools](mcp/mcp_tools_navigation.md)

**Verification issues**  
→ [Verification Tools](mcp/mcp_tools_verification.md)

### Debug Tools

**See what's on screen**  
→ `dump_ui_elements` in [Tree Tools](mcp/mcp_tools_tree.md#dump_ui_elements)

**Check device capabilities**  
→ `get_device_info` in [Core Documentation](mcp/mcp_core.md)

**View system logs**  
→ `view_logs` in [Core Documentation](mcp/mcp_core.md)

---

## 📞 Support

For issues or questions:
1. Check the relevant tool documentation
2. Review [Core Documentation - Troubleshooting](mcp/mcp_core.md#troubleshooting)
3. Check system logs via `view_logs`
4. Open an issue on GitHub

---

## 📈 Version History

- **v4.5.0** (2025-11-18): 54 tools (+ generate_and_save_testcase, rename_testcase, get_compatible_hosts + MCP server refactor: 327 lines)
- **v4.4.0** (2025-11): 51 tools (+ preview_userinterface - "What do we test?")
- **v4.3.0** (2025-11): 49 tools (+ requirements management)
- **v4.2.1** (2025-11): 39 tools (documentation alignment)
- **v4.2.0** (2025-11): 39 tools (+ execute_edge & verify_node)
- **v4.1.0** (2025-01): 35 tools (+ userinterface management)
- **v4.0.0** (2025-01): 29 tools (+ primitive tree tools)
- **v3.0.0** (2025-01): 21 tools (+ discovery & web UI)
- **v2.0.0** (2025-01): 11 tools (production-ready)
- **v1.0.0** (2024): 11 tools (basic automation)

→ [Full Version History](mcp/mcp_core.md#version-history)

---

**Made with ❤️ by the VirtualPyTest team**

---

## 📁 File Structure

```
docs/
├── mcp.md (this file)                # Main index & navigation
└── mcp/
    ├── mcp_core.md                   # Core: Overview, architecture, setup
    ├── mcp_tools_control.md          # take_control (CRITICAL FIRST)
    ├── mcp_tools_action.md           # execute_device_action, list_actions
    ├── mcp_tools_navigation.md       # navigate_to_node, list_navigation_nodes
    ├── mcp_tools_verification.md     # verify_device_state, verify_node, list_verifications
    ├── mcp_tools_tree.md             # 12 primitive tools (create/update/delete node/edge)
    ├── mcp_tools_testcase.md         # save/load/list/execute testcases
    ├── mcp_tools_script.md           # execute_script, list_scripts
    ├── mcp_tools_ai.md               # generate_test_graph
    ├── mcp_tools_screenshot.md       # capture_screenshot, save_node_screenshot
    ├── mcp_tools_userinterface.md    # create/list/delete userinterfaces
    ├── mcp_tools_requirements.md     # 10 requirements management tools
    └── mcp_playground.md             # Web interface documentation
```
