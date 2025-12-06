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
│     agent_id: "qa-web-manager",  ← Selected agent                           │
│     team_id: "team_1"                                                        │
│   }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
│                                                                              │
│   server_agent_routes.py:                                                    │
│   ├── Extract agent_id from request                                         │
│   ├── Load agent config (AGENT_CONFIGS[agent_id])                           │
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

| Agent ID | Nickname | Icon | Platform | Specialty |
|----------|----------|------|----------|-----------|
| `ai-assistant` | **Atlas** | 🤖 | All | General purpose, routes to specialists |
| `qa-web-manager` | **Sherlock** | 🧪 | Web | Browser testing, DOM, web performance |
| `qa-mobile-manager` | **Scout** | 🔍 | Mobile | Android/iOS, Appium, touch gestures |
| `qa-stb-manager` | **Watcher** | 📺 | STB/TV | Remote control, EPG, D-pad navigation |
| `monitoring-manager` | **Guardian** | 🛡️ | All | Alerts, health checks, incidents |

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

## 4. Skills (MCP Tools)

Each agent/sub-agent has access to specific MCP tools.

### Explorer Skills (`skills/explorer_skills.py`)

```python
EXPLORER_TOOLS = [
    # Host/Device discovery
    "get_compatible_hosts",
    "get_device_info",
    
    # Screen analysis
    "dump_ui_elements",
    "analyze_screen_for_action",
    "analyze_screen_for_verification",
    "capture_screenshot",
    
    # AI Exploration (automated tree building)
    "start_ai_exploration",
    "approve_exploration_plan",
    "validate_exploration_edges",
    "get_node_verification_suggestions",
    "finalize_exploration",
    
    # Navigation
    "preview_userinterface",
    "list_navigation_nodes",
    "create_userinterface",
    "list_userinterfaces",
]
```

### Builder Skills (`skills/builder_skills.py`)

```python
BUILDER_TOOLS = [
    # Requirements
    "create_requirement",
    "list_requirements",
    "get_requirement",
    "update_requirement",
    
    # Test cases
    "save_testcase",
    "generate_and_save_testcase",
    "list_testcases",
    "load_testcase",
    
    # Coverage
    "get_coverage_summary",
    "get_uncovered_requirements",
]
```

### Executor Skills (`skills/executor_skills.py`)

```python
EXECUTOR_TOOLS = [
    # Device control
    "take_control",
    "get_device_info",
    "get_execution_status",
    
    # Test execution
    "execute_testcase",
    "execute_testcase_by_id",
    
    # Navigation
    "navigate_to_node",
    "list_navigation_nodes",
]
```

### Manager Skills (All agents have access)

```python
MANAGER_TOOLS = [
    # Data queries
    "list_testcases",
    "list_userinterfaces",
    "list_requirements",
    "get_coverage_summary",
    
    # UI Navigation (browser control)
    "get_available_pages",
    "navigate_to_page",
    "interact_with_element",
    "highlight_element",
    "show_toast",
]
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

### Mode Detection Logic

```python
def detect_mode(self, message: str) -> str:
    message_lower = message.lower()
    
    # CREATE mode
    if any(kw in message_lower for kw in ["automate", "create", "build", "explore"]):
        return Mode.CREATE
    
    # MAINTAIN mode
    if any(kw in message_lower for kw in ["fix", "repair", "broken"]):
        return Mode.MAINTAIN
    
    # VALIDATE mode
    if any(kw in message_lower for kw in ["run", "test", "validate", "execute"]):
        return Mode.VALIDATE
    
    # Default: ANALYZE (direct answer)
    return Mode.ANALYZE
```

---

## 6. Agent Registry

Agent configurations are stored in YAML files and the database.

### YAML Templates Location

```
backend_server/src/agent/registry/templates/
├── qa-web-manager.yaml      # Sherlock
├── qa-mobile-manager.yaml   # Scout
├── qa-stb-manager.yaml      # Watcher
├── monitoring-manager.yaml  # Guardian
├── qa-manager.yaml          # Captain (orchestrator)
├── explorer.yaml            # Pathfinder
└── executor.yaml            # Runner
```

### YAML Configuration Structure

```yaml
# qa-web-manager.yaml (Sherlock)
metadata:
  id: qa-web-manager
  name: QA Web Manager
  nickname: Sherlock
  icon: "🧪"
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
  - type: build.deployed
    priority: high

subagents:
  - id: explorer
    delegate_for: [ui_discovery, web_navigation_mapping]
  - id: executor
    delegate_for: [web_test_execution, browser_automation]

skills:
  - list_testcases
  - execute_testcase
  - take_control
  - verify_element_visible
  - navigate_to_node

permissions:
  devices: [read, take_control]
  database: [read, write.testcases, write.results]

config:
  max_parallel_tasks: 5
  timeout_seconds: 1800
  platform_filter: web
```

### Registry API

```bash
# List all agents
GET /api/agents?team_id=<team_id>

# Get agent details
GET /api/agents/<agent_id>?team_id=<team_id>

# Import from YAML
POST /api/agents/import
Content-Type: text/yaml

# Export to YAML
GET /api/agents/<agent_id>/export
```

---

## 7. Agent Configuration (Runtime)

Agents are configured in `manager.py`:

```python
AGENT_CONFIGS = {
    'ai-assistant': {
        'name': 'Atlas',
        'nickname': 'Atlas',
        'specialty': 'General purpose AI assistant',
        'platform': 'all',
        'focus_areas': ['navigation', 'data queries', 'general assistance'],
    },
    'qa-web-manager': {
        'name': 'Sherlock',
        'nickname': 'Sherlock',
        'specialty': 'Web testing specialist - browser automation, DOM analysis',
        'platform': 'web',
        'focus_areas': ['web automation', 'browser testing', 'responsive design'],
        'preferred_subagents': ['explorer', 'executor'],
    },
    'qa-mobile-manager': {
        'name': 'Scout',
        'nickname': 'Scout',
        'specialty': 'Mobile testing specialist - Android/iOS, Appium',
        'platform': 'mobile',
        'focus_areas': ['mobile automation', 'touch gestures', 'app testing'],
        'preferred_subagents': ['explorer', 'executor'],
    },
    # ... more agents
}
```

---

## 8. End-to-End Example

### User: "Run smoke test on Pixel 5" (Selected: Scout)

```
1. Frontend sends:
   { agent_id: "qa-mobile-manager", message: "Run smoke test on Pixel 5" }

2. Backend creates QAManagerAgent with agent_id="qa-mobile-manager"

3. System prompt includes:
   "You are Scout, Mobile testing specialist - Android/iOS, Appium..."

4. Mode detection: "run" + "test" → VALIDATE mode

5. Manager delegates to Executor:
   - Executor.run("Run smoke test on Pixel 5")
   - Executor uses: take_control, execute_testcase, get_execution_status

6. Executor returns results

7. Manager delegates to Analyst:
   - Analyst analyzes results
   - Returns summary

8. Response to user:
   "✅ Smoke test passed! 15/15 steps completed on Pixel 5."
```

---

## 9. File Structure

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
│   ├── templates/              # YAML agent configs
│   │   ├── qa-web-manager.yaml
│   │   ├── qa-mobile-manager.yaml
│   │   └── ...
│   ├── registry.py             # CRUD operations
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

*Document Version: 1.0*  
*Last Updated: December 2024*

