# AI Agent Architecture

Focused documentation on agent workflow, skills, sub-agents, and registry.

---

## 1. Agent Selection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│                                                                              │
│   User selects agent: [Atlas ▼] → Sherlock (Web)                            │
│   User types: "Run login test on Chrome"                                     │
│                                                                              │
│   AIContext sends:                                                           │
│   {                                                                          │
│     session_id: "...",                                                       │
│     message: "Run login test on Chrome",                                     │
│     agent_id: "qa-web-manager"  ← Selected agent                            │
│   }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
│                                                                              │
│   server_agent_routes.py:                                                    │
│   ├── Extract agent_id from request                                         │
│   ├── Load agent config from YAML cache (memory)                            │
│   ├── Create QAManagerAgent with agent_id                                   │
│   └── Process message with agent-specific system prompt                      │
│                                                                              │
│   QAManagerAgent:                                                            │
│   ├── Detect mode (CREATE/VALIDATE/ANALYZE/MAINTAIN)                        │
│   ├── Use agent-specific system prompt                                       │
│   └── Delegate to sub-agents based on mode                                  │
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
| `explorer` | **Pathfinder** | 🧭 | UI discovery specialist |
| `executor` | **Runner** | ⚡ | Test execution specialist |

---

## 3. Sub-Agent Architecture

Each manager agent can delegate to specialized sub-agents:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MANAGER AGENTS                                        │
│                                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │  Sherlock   │  │   Scout     │  │  Watcher    │  │  Guardian   │        │
│   │    (Web)    │  │  (Mobile)   │  │   (STB)     │  │(Monitoring) │        │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│          │                │                │                │               │
│          └────────────────┴────────────────┴────────────────┘               │
│                                    │                                         │
│                           DELEGATE TO                                        │
│                                    │                                         │
│          ┌─────────────────────────┼─────────────────────────┐              │
│          ▼                         ▼                         ▼              │
│   ┌─────────────┐           ┌─────────────┐           ┌─────────────┐       │
│   │  Explorer   │           │  Executor   │           │  Analyst    │       │
│   │ (Pathfinder)│           │  (Runner)   │           │             │       │
│   └─────────────┘           └─────────────┘           └─────────────┘       │
│          │                         │                         │              │
│          ▼                         ▼                         ▼              │
│   ┌─────────────┐           ┌─────────────┐                                 │
│   │  Builder    │           │ Maintainer  │                                 │
│   └─────────────┘           └─────────────┘                                 │
│                                                                              │
│                          SUB-AGENTS                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Sub-Agent Roles

| Sub-Agent | Nickname | Role | When Used |
|-----------|----------|------|-----------|
| **Explorer** | Pathfinder | UI discovery, navigation tree building | CREATE mode |
| **Builder** | - | Test case & requirements creation | CREATE mode |
| **Executor** | Runner | Test execution, device control | VALIDATE mode |
| **Analyst** | - | Results analysis, metrics, coverage | VALIDATE/ANALYZE mode |
| **Maintainer** | - | Fix broken selectors, self-healing | MAINTAIN mode |

---

## 4. Platform-Specific Skills

Each agent has skills tailored to its platform:

### Web Agent Skills (Sherlock)

```python
# Web CAN use UI dump (DOM hierarchy)
- dump_ui_elements           # ✅ Works on web
- analyze_screen_for_action  # ✅ Selector scoring
- analyze_screen_for_verification
- capture_screenshot         # ✅ Always available
```

### Mobile Agent Skills (Scout)

```python
# Mobile CAN use UI dump (ADB hierarchy)
- dump_ui_elements           # ✅ Works via ADB
- analyze_screen_for_action  # ✅ Selector scoring
- analyze_screen_for_verification
- capture_screenshot         # ✅ Always available
- execute_device_action      # swipe, tap, gestures
```

### STB/TV Agent Skills (Watcher)

```python
# STB CANNOT use UI dump - use AI vision instead
- capture_screenshot         # ✅ Required for STB
- get_transcript            # ✅ Audio analysis
- execute_device_action      # D-pad, remote keys
# ❌ dump_ui_elements NOT available on STB!
```

---

## 5. Operating Modes

The QA Manager detects the user's intent and routes to appropriate sub-agents:

| Mode | Keywords | Sub-Agents Used | Flow |
|------|----------|-----------------|------|
| **CREATE** | "automate", "create", "build", "set up" | Explorer → Builder | Discover UI → Generate tests |
| **VALIDATE** | "run", "test", "validate", "regression" | Executor → Analyst | Run tests → Analyze results |
| **ANALYZE** | "analyze", "investigate", "why did" | Analyst | Deep analysis |
| **MAINTAIN** | "fix", "repair", "broken", "selector" | Maintainer | Self-healing |

---

## 6. Agent Registry

System agents are loaded from YAML templates on startup.

### Architecture: YAML → Memory (No Database)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. YAML Templates (Source of Truth)                             │
│    backend_server/src/agent/registry/templates/*.yaml           │
│    - Defines: id, name, nickname, icon, selectable, skills      │
└────────────────────────┬─────────────────────────────────────────┘
                         │ loaded on startup
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Memory Cache (AgentRegistry._system_agents)                  │
│    - All agents loaded into memory                              │
│    - No database for system agents                              │
│    - Reloadable via /server/agents/reload                       │
└────────────────────────┬─────────────────────────────────────────┘
                         │ exposed via
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. REST API                                                      │
│    GET /server/agents → Returns all agents                      │
│    No team_id - agents are global system resources              │
└────────────────────────┬─────────────────────────────────────────┘
                         │ consumed by
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Frontend                                                      │
│    - AgentChat.tsx loads agents from API                        │
│    - Filters by selectable: true for dropdown                   │
│    - Uses nickname for display everywhere                       │
└─────────────────────────────────────────────────────────────────┘
```

### YAML Templates Location

```
backend_server/src/agent/registry/templates/
├── ai-assistant.yaml        # Atlas (main entrance, selectable: true)
├── qa-web-manager.yaml      # Sherlock (selectable: true)
├── qa-mobile-manager.yaml   # Scout (selectable: true)
├── qa-stb-manager.yaml      # Watcher (selectable: true)
├── monitoring-manager.yaml  # Guardian (selectable: true)
├── explorer.yaml            # Pathfinder (selectable: false, internal)
└── executor.yaml            # Runner (selectable: false, internal)
```

### YAML Configuration Structure

```yaml
# qa-web-manager.yaml (Sherlock)
metadata:
  id: qa-web-manager
  name: QA Web Manager
  nickname: Sherlock
  icon: "🧪"
  selectable: true          # Shown in UI dropdown (false = internal sub-agent)
  version: 1.0.0
  description: Web testing specialist

goal:
  type: continuous
  description: Monitor and validate web-based userinterfaces

triggers:
  - type: alert.blackscreen
    priority: critical
    filters:
      platform: web

subagents:
  - id: explorer
    delegate_for: [ui_discovery, web_navigation_mapping]

skills:
  # WEB-SPECIFIC: UI dump works
  - dump_ui_elements
  - analyze_screen_for_action
  - capture_screenshot

config:
  platform_filter: web
```

### Registry API

```bash
# List all agents
GET /server/agents

# List selectable agents only
GET /server/agents?selectable=true
GET /server/agents/selectable

# Get agent by ID
GET /server/agents/<agent_id>

# Reload from YAML (development)
POST /server/agents/reload

# Export to YAML
GET /server/agents/<agent_id>/export
```

---

## 7. File Structure

```
backend_server/src/agent/
├── agents/                      # Sub-agent implementations
│   ├── base_agent.py           # Base class
│   ├── explorer.py             # UI discovery
│   ├── builder.py              # Test creation
│   ├── executor.py             # Test execution
│   ├── analyst.py              # Analysis
│   └── maintainer.py           # Self-healing
├── core/
│   ├── manager.py              # QAManagerAgent orchestrator
│   ├── session.py              # Session management
│   ├── tool_bridge.py          # MCP ↔ Agent bridge
│   └── message_types.py        # Event types
├── registry/
│   ├── templates/              # YAML agent configs (Source of Truth)
│   │   ├── ai-assistant.yaml
│   │   ├── qa-web-manager.yaml
│   │   └── ...
│   ├── registry.py             # YAML loading + memory cache
│   └── config_schema.py        # Pydantic models
├── skills/
│   ├── explorer_skills.py      # Explorer's MCP tools
│   ├── builder_skills.py       # Builder's MCP tools
│   └── executor_skills.py      # Executor's MCP tools
└── runtime/
    ├── runtime.py              # Instance lifecycle
    └── state.py                # State management
```

---

*Document Version: 2.0*  
*Last Updated: December 2024*
