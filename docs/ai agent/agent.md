# AI Agent Architecture

YAML-driven agent system. Flat hierarchy with specialized managers.

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              ATLAS                                          │
│                         (Main Orchestrator)                                 │
│                                                                             │
│   Skills: READ-ONLY tools + navigate_to_page (browser only)                │
│   Delegates to: Platform-specific MANAGER agents                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│   │   Scout    │  │  Sherlock  │  │  Watcher   │  │  Guardian  │          │
│   │  (Mobile)  │  │   (Web)    │  │   (STB)    │  │ (Monitor)  │          │
│   │     🔍     │  │     🧪     │  │     📺     │  │     🛡️     │          │
│   └────────────┘  └────────────┘  └────────────┘  └────────────┘          │
│                                                                             │
│   Each manager has ALL skills for its platform:                            │
│   - take_control                                                           │
│   - navigate_to_node                                                       │
│   - execute_testcase                                                       │
│   - create_node, create_edge (autonomous exploration)                      │
│   - etc.                                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

**Key Principle:** No sub-agents. Each manager is self-sufficient with all needed skills.

---

## 2. Available Agents

All agents are user-selectable (`selectable: true`):

| Agent ID | Nickname | Icon | Platform | Specialty |
|----------|----------|------|----------|-----------|
| `ai-assistant` | **Atlas** | 🤖 | All | Orchestrator, delegates to specialists |
| `qa-mobile-manager` | **Scout** | 🔍 | Mobile | Android/iOS device control & testing |
| `qa-web-manager` | **Sherlock** | 🧪 | Web | Browser testing, DOM, web automation |
| `qa-stb-manager` | **Watcher** | 📺 | STB/TV | Remote control, EPG, D-pad navigation |
| `monitoring-manager` | **Guardian** | 🛡️ | All | Alerts, health checks, incidents |

**No internal/hidden sub-agents.** Each selectable agent = one chat bubble.

---

## 3. Two Separate Domains

### Domain A: Browser Navigation (Atlas)

```
Tool: navigate_to_page
Purpose: Navigate within VirtualPyTest web UI
Agent: Atlas handles directly

User: "go to incidents page"
  ↓
Atlas calls: navigate_to_page("incidents")
  ↓
Frontend navigates to /monitoring/incidents
```

### Domain B: Device Navigation (Managers)

```
Tool: take_control + navigate_to_node
Purpose: Control physical/virtual devices
Agent: Platform manager (Scout/Sherlock/Watcher)

User: "go to home on horizon_android_mobile"
  ↓
Atlas: "DELEGATE TO qa-mobile-manager"
  ↓
Scout calls: take_control(userinterface="horizon_android_mobile")
Scout calls: navigate_to_node(node="home")
  ↓
Device navigates to home screen
```

**These domains are completely separate. Never mix them.**

---

## 4. Delegation Flow

```
User: "go to home on horizon_android_mobile"
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Atlas checks:                                                    │
│ - Platform? Mobile (android_mobile)                             │
│ - Do I have navigate_to_node? NO                                │
│ - Who handles mobile? Scout (qa-mobile-manager)                 │
│                                                                  │
│ Atlas responds: "DELEGATE TO qa-mobile-manager"                 │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Scout (qa-mobile-manager) receives request                       │
│                                                                  │
│ Scout has these skills (from YAML):                             │
│ - take_control ✓                                                │
│ - navigate_to_node ✓                                            │
│                                                                  │
│ Scout executes:                                                  │
│ 1. take_control(userinterface="horizon_android_mobile")         │
│ 2. navigate_to_node(node="home")                                │
│                                                                  │
│ Done. Two tool calls. No extra prep work.                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Tool Simplicity

**`navigate_to_node` is self-sufficient:**

```
❌ WRONG (what agent was doing):
   1. get_compatible_hosts
   2. preview_userinterface
   3. capture_screenshot
   4. dump_ui_elements
   5. list_navigation_nodes
   6. take_control
   7. navigate_to_node

✅ CORRECT (what agent should do):
   1. take_control(userinterface="...")
   2. navigate_to_node(node="...")

That's it. The tools handle everything internally.
```

---

## 6. Platform-Specific Skills

### Scout (Mobile)

```yaml
skills:
  # Navigation
  - take_control
  - navigate_to_node
  
  # Screen Analysis (ADB)
  - dump_ui_elements
  - analyze_screen_for_action
  - analyze_screen_for_verification
  - capture_screenshot
  
  # Autonomous Exploration (NO human approval)
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
```

### Sherlock (Web)

```yaml
skills:
  # Navigation
  - take_control
  - navigate_to_node
  
  # Screen Analysis (DOM)
  - dump_ui_elements
  - analyze_screen_for_action
  - analyze_screen_for_verification
  - capture_screenshot
  
  # Autonomous Exploration
  - create_node
  - update_node
  - delete_node
  - create_edge
  - update_edge
  - delete_edge
  - execute_edge
  - save_node_screenshot
  
  # Execution
  - execute_testcase
  - execute_device_action
```

### Watcher (STB/TV)

```yaml
skills:
  # Navigation
  - take_control
  - navigate_to_node
  
  # Screen Analysis (AI Vision - NO dump_ui_elements)
  - capture_screenshot
  - get_transcript
  
  # Autonomous Exploration
  - create_node
  - update_node
  - delete_node
  - create_edge
  - update_edge
  - delete_edge
  - execute_edge
  - save_node_screenshot
  
  # Execution
  - execute_device_action    # D-pad, remote keys
  - execute_testcase
```

### Guardian (Monitoring)

```yaml
skills:
  - get_alerts
  - list_incidents
  - get_device_health
  - list_hosts
```

---

## 7. Chat Bubble Rules

| Agent | Chat Bubble |
|-------|-------------|
| Atlas | ✅ Own bubble |
| Scout | ✅ Own bubble (when delegated to) |
| Sherlock | ✅ Own bubble (when delegated to) |
| Watcher | ✅ Own bubble (when delegated to) |
| Guardian | ✅ Own bubble (when delegated to) |

**Rule:** One selectable YAML agent = one chat bubble.

---

## 8. YAML Structure

### Atlas (Orchestrator)

```yaml
# ai-assistant.yaml
metadata:
  id: ai-assistant
  nickname: Atlas
  selectable: true

skills:
  # READ-ONLY tools
  - list_testcases
  - list_userinterfaces
  - list_requirements
  - get_coverage_summary
  # Browser navigation only
  - navigate_to_page
  # NO device tools

subagents:
  - id: qa-mobile-manager
    delegate_for: [mobile_navigation, android_testing]
  - id: qa-web-manager
    delegate_for: [web_navigation, browser_testing]
  - id: qa-stb-manager
    delegate_for: [stb_navigation, tv_testing]
  - id: monitoring-manager
    delegate_for: [alert_investigation, incident_response]
```

### Scout (Mobile Manager)

```yaml
# qa-mobile-manager.yaml
metadata:
  id: qa-mobile-manager
  nickname: Scout
  selectable: true

skills:
  - take_control
  - navigate_to_node
  - dump_ui_elements
  - analyze_screen_for_action
  - analyze_screen_for_verification
  - capture_screenshot
  - create_node
  - update_node
  - delete_node
  - create_edge
  - update_edge
  - delete_edge
  - execute_edge
  - save_node_screenshot
  - execute_device_action
  - execute_testcase
  - get_compatible_hosts
  - list_navigation_nodes

subagents: []  # No sub-agents - all skills included
```

---

## 9. File Structure

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
└── config.py                   # Model config only
```

**Note:** Python agent classes (explorer.py, builder.py, etc.) have been removed.
YAML is the single source of truth for all agent definitions.

---

*Document Version: 5.0*  
*Last Updated: December 2024*  
*Changelog: Removed human-approval exploration tools, added autonomous CRUD tools, deleted dead Python agent code*
