# AI Agent Platform

VirtualPyTest AI Agent - YAML-driven multi-agent platform for automated QA testing.

---

## 1. Overview

### System Architecture

```
User Message → Manager loads YAML → Claude uses tools OR delegates → Response
```

**Key Principle: No hardcoded logic in manager. Everything from YAML.**

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI ASSISTANT (Atlas)                          │
│                     Default Generic Agent                        │
│            Claude decides when to delegate based on tools        │
└──────────────────────────┬───────────────────────────────────────┘
                           │ DELEGATE TO [agent_id]
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 🧭 Pathfinder   │ │ ⚡ Runner       │ │ Other sub-agents│
│    (explorer)   │ │   (executor)   │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Pre-configured Agents

**User-Selectable** (`selectable: true` in YAML):

| Agent | Nickname | Icon | Platform |
|-------|----------|------|----------|
| `ai-assistant` | Atlas | 🤖 | All |
| `qa-web-manager` | Sherlock | 🧪 | Web |
| `qa-mobile-manager` | Scout | 🔍 | Mobile |
| `qa-stb-manager` | Watcher | 📺 | STB/TV |
| `monitoring-manager` | Guardian | 🛡️ | All |

**Internal Sub-Agents** (`selectable: false`):

| Agent | Nickname | Icon | Role |
|-------|----------|------|------|
| `explorer` | Pathfinder | 🧭 | UI discovery |
| `executor` | Runner | ⚡ | Test execution |

---

## 2. YAML-Driven Architecture

### No Hardcoded Mode Detection

**OLD (removed):**
```python
# ❌ REMOVED - No more hardcoded keywords
def detect_mode(self, message):
    if "automate" in message: return Mode.CREATE
    if "run test" in message: return Mode.VALIDATE
```

**NEW (YAML-driven):**
```python
# ✅ Claude decides based on available tools
prompt = "Use your tools. If you lack the tool, say: DELEGATE TO [agent_id]"
```

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Load YAML Config                                              │
│    skills: [list_testcases, navigate_to_page, ...]              │
│    subagents: [explorer, executor]                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Build System Prompt                                           │
│    "Your tools: list_testcases, navigate_to_page..."            │
│    "Sub-agents: explorer (has navigate_to_node), executor..."   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Claude Decides                                                │
│    - Has the tool? → Use it                                      │
│    - Lacks the tool? → "DELEGATE TO explorer"                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Manager Validates & Delegates                                 │
│    - Is "explorer" in YAML subagents? → Yes                     │
│    - Lazy-load ExplorerAgent                                    │
│    - Run with original message                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. YAML Configuration

### Agent YAML Structure

```yaml
metadata:
  id: ai-assistant
  name: AI Assistant
  nickname: Atlas
  icon: "🤖"
  selectable: true          # Shown in UI dropdown
  description: General AI assistant

skills:                     # Tools this agent can use
  - list_testcases
  - list_userinterfaces
  - navigate_to_page        # Browser navigation
  - get_device_info
  # NO navigate_to_node     # Must delegate for device nav

subagents:                  # Who this agent can delegate to
  - id: explorer
    delegate_for:
      - ui_discovery
      - navigation_exploration
  - id: executor
    delegate_for:
      - test_execution

config:
  timeout_seconds: 300
```

### Skills → MCP Tools

| Category | Tools |
|----------|-------|
| **control** | `take_control` |
| **device** | `get_device_info`, `list_hosts` |
| **navigation** | `navigate_to_node`, `navigate_to_page` |
| **testcase** | `list_testcases`, `execute_testcase` |
| **userinterface** | `list_userinterfaces`, `get_userinterface_complete` |

### Platform-Specific Skills

| Platform | UI Inspection | Why |
|----------|---------------|-----|
| **Web** | `dump_ui_elements` ✅ | DOM available |
| **Mobile** | `dump_ui_elements` ✅ | ADB hierarchy |
| **STB/TV** | `capture_screenshot` only | No UI hierarchy |

---

## 4. Interactive Navigation

### Browser Navigation (navigate_to_page)

Atlas has this tool - navigates within VirtualPyTest web UI:

```
User: "go to incidents"
    ↓
Atlas calls: navigate_to_page("incidents")
    ↓
Frontend navigates to /monitoring/incidents
```

### Device Navigation (navigate_to_node)

Atlas does NOT have this - delegates to Explorer:

```
User: "go to home on device s21x"
    ↓
Atlas: "I don't have navigate_to_node"
Atlas: "DELEGATE TO explorer"
    ↓
Explorer calls: take_control(), navigate_to_node()
```

### Page Mapping (for navigate_to_page)

| Alias | Path |
|-------|------|
| `dashboard`, `home` | `/` |
| `devices` | `/device-control` |
| `incidents`, `alerts` | `/monitoring/incidents` |
| `reports` | `/test-results/reports` |
| `test cases` | `/test-plan/test-cases` |

---

## 5. API Reference

### Agent Registry

```bash
# List all agents
GET /server/agents

# List selectable only
GET /server/agents?selectable=true

# Get specific agent
GET /server/agents/<agent_id>

# Reload from YAML
POST /server/agents/reload
```

### Chat

```bash
# Create session
POST /server/agent/sessions

# SocketIO: send_message
{
  "session_id": "uuid",
  "message": "go to home on device s21x",
  "agent_id": "ai-assistant",
  "allow_auto_navigation": true,
  "current_page": "/ai-agent"
}
```

---

## 6. Frontend Integration

### AgentChat Component

```tsx
// Loads agents from API
const agents = await fetch('/server/agents?selectable=true');

// Filters for dropdown
agents.filter(a => a.metadata.selectable);

// Shows nickname everywhere
<AgentSelector agents={agents} />
```

### Agent Activity Badges

Shows real-time agent status across all pages.

---

## 7. File Structure

```
backend_server/src/agent/
├── agents/                      # Sub-agent implementations
│   ├── explorer.py             # Pathfinder (lazy-loaded)
│   ├── executor.py             # Runner (lazy-loaded)
│   └── ...
├── core/
│   ├── manager.py              # YAML-driven orchestrator
│   ├── session.py
│   └── tool_bridge.py
├── registry/
│   ├── templates/              # YAML configs (Source of Truth)
│   │   ├── ai-assistant.yaml
│   │   ├── explorer.yaml
│   │   └── ...
│   └── registry.py
└── config.py                   # Model config only

frontend/src/
├── pages/
│   ├── AgentChat.tsx
│   └── AgentDashboard.tsx
└── contexts/
    └── AIContext.tsx
```

---

## 8. Quick Start

### Start Backend

```bash
./setup/local/launch_server.sh
```

### Start Frontend

```bash
./setup/local/launch_frontend.sh
```

### Test

```bash
# Reload agents from YAML
curl -X POST http://localhost:5109/server/agents/reload

# List agents
curl http://localhost:5109/server/agents
```

---

## 9. Troubleshooting

### "Cannot delegate to X"

Check YAML subagents list:
```yaml
subagents:
  - id: explorer  # Must be listed here
```

### Agent not in dropdown

Check `selectable: true` in YAML metadata.

### Tool not found

Check agent's `skills` list in YAML.

---

*Document Version: 3.0*  
*Last Updated: December 2024*  
*Changelog: Removed hardcoded mode detection - now fully YAML-driven*
