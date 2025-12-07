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
- No sub-agents (Explorer/Executor deleted)
- Each manager has ALL skills for its platform
- One selectable agent = one chat bubble

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

## 5. YAML Configuration

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
  - take_control
  - navigate_to_node
  - dump_ui_elements
  - capture_screenshot
  - execute_device_action
  - execute_testcase
  - start_ai_exploration
  - get_compatible_hosts
  - list_navigation_nodes

subagents: []  # No sub-agents
```

---

## 6. Chat Bubbles

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

## 7. Delegation Flow

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

## 8. API Reference

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

## 9. File Structure

```
backend_server/src/agent/
├── core/
│   ├── manager.py              # YAML-driven orchestrator
│   ├── session.py
│   └── tool_bridge.py
├── registry/
│   ├── templates/
│   │   ├── ai-assistant.yaml       # Atlas
│   │   ├── qa-mobile-manager.yaml  # Scout
│   │   ├── qa-web-manager.yaml     # Sherlock
│   │   ├── qa-stb-manager.yaml     # Watcher
│   │   └── monitoring-manager.yaml # Guardian
│   └── registry.py
└── config.py
```

---

## 10. Troubleshooting

### "Cannot delegate to X"

Check Atlas's `subagents` list in YAML includes the target agent.

### Agent not in dropdown

Check `selectable: true` in agent's YAML metadata.

### Tool not found

Check agent's `skills` list in YAML.

### Agent doing too much prep work

Update system prompt to emphasize: "Just use take_control + navigate_to_node. No screenshots or dumps needed first."

---

*Document Version: 4.0*  
*Last Updated: December 2024*  
*Changelog: Simplified architecture - flat hierarchy, no Explorer/Executor*
