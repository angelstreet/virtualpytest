# AI Agent Architecture

YAML-driven agent system. No hardcoded logic in manager.

---

## 1. Agent Selection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│                                                                              │
│   User selects agent: [Atlas ▼] → Sherlock (Web)                            │
│   User types: "Go to home on device s21x"                                   │
│                                                                              │
│   AIContext sends:                                                           │
│   {                                                                          │
│     session_id: "...",                                                       │
│     message: "Go to home on device s21x",                                   │
│     agent_id: "qa-web-manager"  ← Selected agent                            │
│   }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
│                                                                              │
│   QAManagerAgent:                                                            │
│   ├── Load agent config from YAML (tools, sub-agents)                       │
│   ├── Build system prompt with available tools                              │
│   ├── Claude decides: use tools OR "DELEGATE TO [agent_id]"                 │
│   └── If delegation → run sub-agent with original message                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Available Agents

### User-Selectable Agents (shown in UI dropdown)

| Agent ID | Nickname | Icon | Platform | Specialty |
|----------|----------|------|----------|-----------|
| `ai-assistant` | **Atlas** | 🤖 | All | General purpose, main entrance |
| `qa-web-manager` | **Sherlock** | 🧪 | Web | Browser testing, DOM, web performance |
| `qa-mobile-manager` | **Scout** | 🔍 | Mobile | Android/iOS, Appium, touch gestures |
| `qa-stb-manager` | **Watcher** | 📺 | STB/TV | Remote control, EPG, D-pad navigation |
| `monitoring-manager` | **Guardian** | 🛡️ | All | Alerts, health checks, incidents |

### Internal Agents (sub-agents, not user-selectable)

| Agent ID | Nickname | Icon | Role |
|----------|----------|------|------|
| `explorer` | **Pathfinder** | 🧭 | UI discovery, navigation tree building |
| `executor` | **Runner** | ⚡ | Test execution, device control |

---

## 3. YAML-Driven Architecture

**No hardcoded mode detection. No hardcoded agent mapping.**

Everything comes from YAML:

```yaml
# ai-assistant.yaml
metadata:
  id: ai-assistant
  nickname: Atlas

skills:                    # Tools Atlas can use
  - list_testcases
  - list_userinterfaces
  - navigate_to_page       # Browser navigation only
  # NO navigate_to_node    # → Must delegate

subagents:                 # Who Atlas can delegate to
  - id: explorer
    delegate_for:
      - ui_discovery
      - navigation_exploration
  - id: executor
    delegate_for:
      - test_execution
```

### How Delegation Works

```
User: "Navigate to home on device s21x"
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Atlas checks its tools (from YAML skills):                       │
│ - list_testcases ✓                                              │
│ - navigate_to_page ✓ (browser)                                  │
│ - navigate_to_node ✗ (NOT in skills)                            │
│                                                                  │
│ Claude realizes: "I don't have navigate_to_node"                │
│ Claude responds: "DELEGATE TO explorer"                         │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Manager validates: "explorer" in self.agent_config['subagents'] │
│ Manager loads: ExplorerAgent (lazy, on demand)                  │
│ Manager runs: explorer.run(original_message, context)           │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Explorer (Pathfinder) has these tools (from explorer.yaml):     │
│ - navigate_to_node ✓                                            │
│ - take_control ✓                                                │
│ - start_ai_exploration ✓                                        │
│ - ...                                                           │
│                                                                  │
│ Explorer executes the navigation                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Sub-Agent Roles

| Sub-Agent | Nickname | When Delegated | Key Skills |
|-----------|----------|----------------|------------|
| **Explorer** | Pathfinder | UI discovery, device navigation | `navigate_to_node`, `take_control`, `start_ai_exploration` |
| **Executor** | Runner | Test execution | `execute_testcase`, `take_control`, `execute_device_action` |
| **Builder** | - | Test/requirement creation | `save_testcase`, `create_requirement` |
| **Analyst** | - | Results analysis | `get_coverage_summary`, `list_requirements` |
| **Maintainer** | - | Fix broken selectors | `update_edge`, `dump_ui_elements` |

---

## 5. Platform-Specific Skills

Each agent's YAML defines platform-appropriate skills:

### Web Agent Skills (Sherlock)

```yaml
skills:
  - dump_ui_elements           # ✅ DOM hierarchy
  - analyze_screen_for_action  # ✅ Selector scoring
  - capture_screenshot         # ✅ Always available
```

### Mobile Agent Skills (Scout)

```yaml
skills:
  - dump_ui_elements           # ✅ ADB hierarchy
  - execute_device_action      # ✅ Touch, swipe
  - capture_screenshot         # ✅ Always available
```

### STB/TV Agent Skills (Watcher)

```yaml
skills:
  - capture_screenshot         # ✅ Required - AI vision
  - get_transcript            # ✅ Audio analysis
  # NO dump_ui_elements        # ❌ Not available on STB
```

---

## 6. Agent Registry

### Architecture: YAML → Memory → API

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. YAML Templates (Source of Truth)                             │
│    backend_server/src/agent/registry/templates/*.yaml           │
└────────────────────────┬────────────────────────────────────────┘
                         │ loaded on startup
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Memory Cache (AgentRegistry._system_agents)                  │
│    - Reloadable via POST /server/agents/reload                  │
└────────────────────────┬────────────────────────────────────────┘
                         │ exposed via
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. REST API (GET /server/agents)                                │
│    - No team_id - agents are global                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ consumed by
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Frontend (AgentChat.tsx)                                     │
│    - Filters by selectable: true for dropdown                   │
└─────────────────────────────────────────────────────────────────┘
```

### YAML Templates Location

```
backend_server/src/agent/registry/templates/
├── ai-assistant.yaml        # Atlas (selectable: true)
├── qa-web-manager.yaml      # Sherlock (selectable: true)
├── qa-mobile-manager.yaml   # Scout (selectable: true)
├── qa-stb-manager.yaml      # Watcher (selectable: true)
├── monitoring-manager.yaml  # Guardian (selectable: true)
├── explorer.yaml            # Pathfinder (selectable: false)
└── executor.yaml            # Runner (selectable: false)
```

---

## 7. File Structure

```
backend_server/src/agent/
├── agents/                      # Sub-agent implementations
│   ├── base_agent.py
│   ├── explorer.py             # Pathfinder
│   ├── builder.py
│   ├── executor.py             # Runner
│   ├── analyst.py
│   └── maintainer.py
├── core/
│   ├── manager.py              # YAML-driven orchestrator
│   ├── session.py              # Session management
│   ├── tool_bridge.py          # MCP ↔ Agent bridge
│   └── message_types.py        # Event types
├── registry/
│   ├── templates/              # YAML agent configs (Source of Truth)
│   ├── registry.py             # YAML loading
│   └── config_schema.py        # Pydantic models
└── config.py                   # Model config only (no Mode/MODE_AGENTS)
```

---

*Document Version: 3.0*  
*Last Updated: December 2024*  
*Changelog: Removed hardcoded mode detection - now fully YAML-driven*
