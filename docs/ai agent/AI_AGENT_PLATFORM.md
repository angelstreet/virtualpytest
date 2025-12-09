# AI Agent Platform

VirtualPyTest AI Agent - YAML-driven platform with specialized managers.

---

## 1. Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ATLAS (Orchestrator)                     │
│                                                                  │
│   • Handles simple queries (list, count, show)                  │
│   • Browser navigation (navigate_to_page)                       │
│   • Delegates device tasks to platform managers                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ DELEGATE TO [agent_id]
          ┌────────────────┼────────────────┬────────────────┐
          ▼                ▼                ▼                ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │   Scout    │   │  Sherlock  │   │  Watcher   │   │  Guardian  │
   │  (Mobile)  │   │   (Web)    │   │   (STB)    │   │ (Monitor)  │
   │     🔍     │   │     🧪     │   │     📺     │   │     🛡️     │
   └────────────┘   └────────────┘   └────────────┘   └────────────┘
```

**Key Principles:**
- No sub-agents (all skills inline)
- Each manager has ALL skills for its platform
- One selectable agent = one chat bubble
- YAML is the single source of truth

---

## 2. Agents

| Agent ID | Nickname | Icon | Platform | Role |
|----------|----------|------|----------|------|
| `ai-assistant` | Atlas | 🤖 | All | Orchestrator, simple queries |
| `qa-mobile-manager` | Scout | 🔍 | Mobile | Android/iOS device control |
| `qa-web-manager` | Sherlock | 🧪 | Web | Browser automation |
| `qa-stb-manager` | Watcher | 📺 | STB/TV | Remote control, TV testing |
| `monitoring-manager` | Guardian | 🛡️ | All | Alerts, incidents |

All agents have `selectable: true` in YAML.

---

## 3. Two Domains (Never Mix)

### Domain A: Browser Navigation

```
Tool: navigate_to_page
Agent: Atlas (handles directly)
Purpose: Navigate VirtualPyTest web UI

Example:
  User: "go to incidents page"
  Atlas: navigate_to_page("incidents")
  Result: Browser goes to /monitoring/incidents
```

### Domain B: Device Navigation

```
Tools: take_control + navigate_to_node
Agent: Platform manager (Scout/Sherlock/Watcher)
Purpose: Control physical/virtual devices

Example:
  User: "go to home on horizon_android_mobile"
  Atlas: DELEGATE TO qa-mobile-manager
  Scout: take_control(userinterface="horizon_android_mobile")
  Scout: navigate_to_node(node="home")
  Result: Device navigates to home screen
```

---

## 4. Tool Usage

### Correct Workflow

```
User: "go to home on horizon_android_mobile"

Scout receives request:
  1. take_control(userinterface="horizon_android_mobile")
  2. navigate_to_node(node="home")

Done. Two calls. No prep work needed.
```

### What NOT To Do

```
❌ Don't call get_compatible_hosts first
❌ Don't call preview_userinterface first
❌ Don't call capture_screenshot first
❌ Don't call dump_ui_elements first

The tools are self-sufficient. Just use them.
```

---

## 5. Autonomous Exploration

Agents build navigation trees **autonomously** using atomic CRUD tools.
No human approval gates required.

### Available Tools

| Tool | Purpose |
|------|---------|
| `create_node` | Add screen/node to tree |
| `update_node` | Modify node (add verifications) |
| `delete_node` | Remove node |
| `create_edge` | Add navigation path with actions |
| `update_edge` | Fix edge actions |
| `delete_edge` | Remove edge |
| `execute_edge` | Test edge immediately |
| `save_node_screenshot` | Attach screenshot to node |

### Exploration Workflow

```
User: "Explore google_tv and create its navigation model"

Scout:
  1. get_compatible_hosts(userinterface_name='google_tv')
  2. take_control(tree_id=..., device_id=..., host_name=...)
  3. dump_ui_elements(...)  → Analyze screen
  4. analyze_screen_for_action(elements, intent='search button', platform='mobile')
  5. create_node(tree_id=..., label='search')
  6. create_edge(tree_id=..., source='home', target='search', action_sets=[...])
  7. execute_edge(...)  → Test it works
  8. Repeat for all screens
```

**Key:** Agent decides what to create, tests immediately, fixes if needed.

---

## 6. YAML Configuration

### Atlas (Orchestrator)

```yaml
metadata:
  id: ai-assistant
  nickname: Atlas
  selectable: true

skills:
  - list_testcases
  - list_userinterfaces
  - list_requirements
  - get_coverage_summary
  - navigate_to_page      # Browser only

subagents:
  - id: qa-mobile-manager
    delegate_for: [mobile_navigation, android_testing]
  - id: qa-web-manager
    delegate_for: [web_navigation, browser_testing]
  - id: qa-stb-manager
    delegate_for: [stb_navigation, tv_testing]
  - id: monitoring-manager
    delegate_for: [alert_investigation]
```

### Scout (Mobile Manager)

```yaml
metadata:
  id: qa-mobile-manager
  nickname: Scout
  selectable: true

skills:
  # Navigation
  - take_control
  - navigate_to_node
  
  # Screen Analysis
  - dump_ui_elements
  - analyze_screen_for_action
  - analyze_screen_for_verification
  - capture_screenshot
  
  # Autonomous Exploration (CRUD)
  - create_node
  - update_node
  - delete_node
  - create_edge
  - update_edge
  - delete_edge
  - execute_edge
  - save_node_screenshot
  
  # Execution
  - execute_device_action
  - execute_testcase
  - get_compatible_hosts
  - list_navigation_nodes

subagents: []  # No sub-agents
```

---

## 7. Chat Bubbles

**Rule:** Each YAML agent with `selectable: true` gets its own chat bubble.

```
┌─────────────────────────────────────┐
│ Atlas                                │
│ Delegating to Scout for mobile task  │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Scout                                │
│ ✓ take_control                       │
│ ✓ navigate_to_node                   │
│ Navigated to home successfully       │
└─────────────────────────────────────┘
```

No hidden sub-agent bubbles. What you see is what you get.

---

## 8. Delegation Flow

```
User sends: "go to home on horizon_android_mobile"
                    │
                    ▼
┌───────────────────────────────────────────────────────────┐
│ Atlas                                                      │
│ • Loads YAML config                                        │
│ • Checks skills: navigate_to_node? NO                     │
│ • Identifies platform: mobile                             │
│ • Delegates: "DELEGATE TO qa-mobile-manager"              │
└───────────────────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────┐
│ Scout (qa-mobile-manager)                                  │
│ • Has take_control ✓                                       │
│ • Has navigate_to_node ✓                                   │
│ • Executes directly - no further delegation               │
└───────────────────────────────────────────────────────────┘
```

---

## 9. API Reference

### Agent Registry

```bash
# List all agents
GET /server/agents

# List selectable only
GET /server/agents?selectable=true

# Reload from YAML
POST /server/agents/reload
```

### Chat

```bash
# SocketIO: send_message
{
  "session_id": "uuid",
  "message": "go to home on horizon_android_mobile",
  "agent_id": "ai-assistant"
}
```

---

## 10. File Structure

```
backend_server/src/agent/
├── core/
│   ├── manager.py              # QAManagerAgent (THE ONLY agent class)
│   ├── session.py
│   └── tool_bridge.py
├── registry/
│   ├── templates/              # YAML configs (SOURCE OF TRUTH)
│   │   ├── ai-assistant.yaml       # Atlas
│   │   ├── qa-mobile-manager.yaml  # Scout
│   │   ├── qa-web-manager.yaml     # Sherlock
│   │   ├── qa-stb-manager.yaml     # Watcher
│   │   └── monitoring-manager.yaml # Guardian
│   ├── registry.py
│   └── validator.py
├── skills/
│   └── skill_registry.py       # Validates YAML skills against MCP tools
└── config.py
```

**Note:** Python agent classes have been removed. YAML is the single source of truth.

---

## 11. Troubleshooting

### "Cannot delegate to X"

Check Atlas's `subagents` list in YAML includes the target agent.

### Agent not in dropdown

Check `selectable: true` in agent's YAML metadata.

### Tool not found

Check agent's `skills` list in YAML.

### Agent doing too much prep work

Update system prompt to emphasize: "Just use take_control + navigate_to_node. No screenshots or dumps needed first."

### Exploration not working

Ensure agent has CRUD tools: `create_node`, `create_edge`, `execute_edge`, etc.

### Agent returning empty responses

**Cause:** Context overload (too many tools + conversation history)

**Symptoms:**
```
[AGENT DEBUG] Scout EMPTY RESPONSE:
  - stop_reason: end_turn
  - input_tokens: 13452
  - output_tokens: 3
  - content blocks: []
```

**Root Causes:**
1. **Too many tools**: Agent has >20 tools or >6k tool tokens
2. **History bloat**: Delegated agent receiving parent's conversation history
3. **Combined overload**: Tools + history exceed model's practical limit

**Solutions:**

1. **Reduce tool count** (target: <20 tools per agent)
   ```yaml
   # BAD: 28 tools
   skills:
     - take_control
     - navigate_to_node
     - dump_ui_elements
     - analyze_screen_for_action
     - ... (24 more tools)
   
   # GOOD: Split into specialized agents
   # Or remove redundant tools
   ```

2. **Verify delegation context** (check manager.py)
   ```python
   # Should see this behavior:
   if _is_delegated:
       # Delegated agents get clean slate
       turn_messages = [{"role": "user", "content": message}]
   else:
       # Root agents get full history
       turn_messages = session.messages
   ```

3. **Split complex agents**
   - Create focused sub-agents for specific tasks
   - Each with <15 tools
   - Example: Split "exploration" and "execution" into separate agents

**Example Issue:**
Scout had 28 tools (~10k tokens). When also receiving full conversation history from Atlas (3-4k tokens), total context exceeded model's practical limits, causing empty responses despite being under 200k technical limit.

---

*Document Version: 5.1*  
*Last Updated: December 2024*  
*Changelog: Added memory management section, context overload troubleshooting, delegation clean-slate behavior*
