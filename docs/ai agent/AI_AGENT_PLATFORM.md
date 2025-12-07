# AI Agent Platform

VirtualPyTest AI Agent is a multi-agent platform for automated QA testing, powered by Claude.

**Implementation Status: ~90% Complete**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Agent Types & Configuration](#3-agent-types--configuration)
4. [2-Step Workflow](#4-2-step-workflow)
5. [Interactive Navigation](#5-interactive-navigation)
6. [Global Badge System](#6-global-badge-system)
7. [API Reference](#7-api-reference)
8. [Frontend Integration](#8-frontend-integration)
9. [Scoring & Feedback](#9-scoring--feedback)
10. [Quick Start](#10-quick-start)
11. [File Structure](#11-file-structure)

---

## 1. Overview

### System Architecture

The platform operates in two modes:

**Chat Mode (Reactive)**
```
User Message → QA Manager → Mode Detection → Agent Delegation → Response
```

**Autonomous Mode (Event-Driven)**
```
Event Sources → Event Bus → Agent Runtime → Parallel Agents → Actions → Feedback
```

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI ASSISTANT (Atlas)                          │
│                     Default Generic Agent                        │
│                 Routes to specialists when needed                │
└──────────────────────────┬───────────────────────────────────────┘
                           │ delegates to
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 🧪 Sherlock     │ │ 🔍 Scout        │ │ 📺 Watcher      │
│ QA Web Manager  │ │ QA Mobile Mgr   │ │ QA STB Manager  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                │                │
          ▼                ▼                ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │ 🧭 Pathfinder│  │ ⚡ Runner  │   │ 🛡️ Guardian │
   │  Explorer   │   │  Executor  │   │ Monitoring  │
   └────────────┘   └────────────┘   └────────────┘
```

### Pre-configured Agents

| Agent | Nickname | Icon | Platform | Purpose |
|-------|----------|------|----------|---------|
| `ai-assistant` | Atlas | 🤖 | All | General purpose, routes to specialists |
| `qa-web-manager` | Sherlock | 🧪 | Web | Browser testing specialist |
| `qa-mobile-manager` | Scout | 🔍 | Mobile | Android/iOS testing |
| `qa-stb-manager` | Watcher | 📺 | STB/TV | Set-top box validation |
| `monitoring-manager` | Guardian | 🛡️ | All | System health monitoring |
| `qa-manager` | Captain | 🎖️ | All | Coordinator with sub-agents |
| `explorer` | Pathfinder | 🧭 | All | UI discovery specialist |
| `executor` | Runner | ⚡ | All | Test execution specialist |

---

## 2. Architecture

### Core Components

```
backend_server/src/
├── agent/
│   ├── agents/              # Specialist agents (Explorer, Builder, etc.)
│   ├── core/
│   │   ├── manager.py       # QA Manager orchestrator
│   │   ├── session.py       # Chat session management
│   │   └── tool_bridge.py   # MCP ↔ Agent bridge
│   ├── registry/
│   │   ├── config_schema.py # Pydantic models
│   │   ├── registry.py      # Agent CRUD & versioning
│   │   └── templates/       # Pre-defined YAML agents
│   ├── runtime/
│   │   ├── runtime.py       # Instance lifecycle
│   │   └── state.py         # State management
│   └── skills/
│       └── skill_registry.py # MCP tool validation
├── events/
│   ├── event_bus.py         # Redis pub/sub + DB logging
│   └── event_router.py      # Event → Agent routing
├── resources/
│   └── lock_manager.py      # Device locking
└── routes/
    ├── server_agent_routes.py     # Chat & sessions
    ├── agent_registry_routes.py   # Agent CRUD
    ├── agent_runtime_routes.py    # Instance management
    ├── agent_benchmark_routes.py  # Benchmarks & feedback
    └── event_routes.py            # Event publishing
```

### Event-Driven System

**Event Sources:**
- Chat/Slack messages
- Alert system (blackscreen, device offline)
- CI/CD webhooks
- Scheduler (cron)
- Database watchers
- Device monitors

**Event Priority Levels:**
| Priority | Examples | Behavior |
|----------|----------|----------|
| Critical | Blackscreen, crash | Immediate action |
| High | Build deployed, test failure | Next in queue |
| Normal | Scheduled regression | Standard processing |
| Low | Metrics collection | Background |

### Resource Lock Manager

Prevents device conflicts during parallel execution:
```
Mobile1: [Task A] → [Task B] → ...
Mobile2: [Task C] → ...
TV1:     [Task D] → ...
```

---

## 3. Agent Types & Configuration

### Operating Modes

| Mode | Keywords | Agents Used |
|------|----------|-------------|
| **CREATE** | "automate", "create", "build" | Explorer → Builder |
| **VALIDATE** | "run", "test", "regression" | Executor → Analyst |
| **ANALYZE** | "analyze", "investigate" | Analyst |
| **MAINTAIN** | "fix", "repair", "broken" | Maintainer |
| **DIRECT** | "list", "count", "show" | QA Manager (no delegation) |

### YAML Configuration

```yaml
metadata:
  id: qa-web-manager
  name: QA Web Manager
  nickname: Sherlock        # Fun name for badges
  icon: "🧪"                # Emoji icon
  version: 1.0.0
  author: system
  description: Web testing specialist

goal:
  type: continuous          # or "on-demand"
  description: Monitor web-based userinterfaces

triggers:
  - type: alert.blackscreen
    priority: critical
    filters:
      platform: web
  - type: build.deployed
    priority: high
  - type: schedule.web_regression
    priority: normal

event_pools:
  - shared.alerts
  - own.qa-web-tasks

subagents:
  - id: explorer
    version: ">=1.0.0"
    delegate_for: [ui_discovery]
  - id: executor
    version: ">=1.0.0"
    delegate_for: [test_execution]

skills:                     # Must be valid MCP tools!
  - list_userinterfaces
  - take_control
  - execute_testcase
  - navigate_to_page

permissions:
  devices: [read, take_control]
  database: [read, write.results]
  external: [jira, slack]

config:
  max_parallel_tasks: 5
  approval_required_for: [create_jira_ticket]
  auto_retry: true
  feedback_collection: true
  timeout_seconds: 1800
  budget_limit_usd: 30.00
```

### Skills → MCP Tools Mapping

| Category | Tools |
|----------|-------|
| **control** | `take_control`, `release_control` |
| **device** | `get_device_info`, `list_hosts` |
| **navigation** | `navigate_to_node`, `list_nodes`, `navigate_to_page` |
| **testcase** | `list_testcases`, `execute_testcase` |
| **verification** | `list_verifications`, `verify_element` |
| **userinterface** | `list_userinterfaces`, `get_userinterface_complete` |

---

## 4. 2-Step Workflow

The AI agent follows a mandatory 2-step workflow for all requests, separating **navigation** (visual context) from **task execution** (actual work).

### Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: NAVIGATION (Optional - for visual context)              │
├─────────────────────────────────────────────────────────────────┤
│ Skip if:                                                         │
│   • Auto-navigation toggle is OFF                               │
│   • User is already on target page                              │
│   • Request has no relevant page                                │
│                                                                  │
│ Execute if: Toggle ON + Not on page + Page exists               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: TASK EXECUTION (Required unless navigation-only)        │
├─────────────────────────────────────────────────────────────────┤
│ Skip if: Request is purely navigation ("go to X")               │
│                                                                  │
│ Execute: Use tools to provide ACTUAL DATA                       │
└─────────────────────────────────────────────────────────────────┘
```

### Request Classification

| Request Type | Step 1 (Navigate) | Step 2 (Execute) |
|--------------|-------------------|------------------|
| "go to incidents" | ✅ Navigate | ❌ Skip |
| "how many alerts?" | ✅ Navigate (if enabled) | ✅ Fetch data |
| "list test cases" | ✅ Navigate (if enabled) | ✅ Fetch data |
| "run regression" | ❌ Skip | ✅ Execute |

### Auto-Navigation Toggle

Users can control whether the AI navigates their browser:

- **Toggle ON**: AI navigates to relevant page, then executes task
- **Toggle OFF**: AI skips navigation, directly executes task

The toggle is available in the AgentChat UI (top bar).

### Context Passed to Backend

Frontend sends navigation context with every message:

```typescript
socketRef.current.emit('send_message', {
  session_id: sessionId,
  message: message,
  team_id: teamId,
  agent_id: agentId,
  allow_auto_navigation: true,    // Toggle state
  current_page: '/ai-agent',      // User's current location
});
```

### Page Mapping

| Keywords | Target Page |
|----------|-------------|
| alerts, incidents | `/monitoring/incidents` |
| devices, device control | `/device-control` |
| reports, test reports | `/test-results/reports` |
| heatmap | `/monitoring/heatmap` |
| test cases | `/test-plan/test-cases` |
| dashboard | `/` |

### Example Flow

**User asks**: "How many alerts are there?"

```
1. AI receives context:
   - allow_auto_navigation: true
   - current_page: /ai-agent

2. Step 1 (Navigation):
   - Check: Is navigation enabled? → YES
   - Check: Is user on /monitoring/incidents? → NO
   - Action: navigate_to_page("incidents")

3. Step 2 (Task Execution):
   - Use available tools to fetch alert data
   - Return: "There are 5 active alerts and 12 closed alerts."
```

---

## 5. Interactive Navigation

The AI can control the user's browser within the React application.

### Capabilities

- Navigate to any page
- Interact with UI elements (click, filter, select)
- Highlight elements to draw attention
- Show toast notifications

### Event Flow

```
User: "go to incidents"
    ↓
AI calls: navigate_to_page("incidents")
    ↓
Backend emits WebSocket: { action: "navigate", path: "/monitoring/incidents" }
    ↓
AIContext receives → calls React Router navigate()
    ↓
Page renders → AI can continue with interact_with_element()
```

### Page Schema

```typescript
// frontend/src/lib/ai/pageSchema.ts
interface PageSchema {
  path: string;           // Route path
  name: string;           // Display name
  elements: PageElement[];// Controllable elements
}

interface PageElement {
  id: string;             // Unique element ID
  type: string;           // button, table, dropdown, etc.
  actions: string[];      // click, select, filter...
}
```

### Navigation Aliases

| Alias | Path |
|-------|------|
| `dashboard`, `home` | `/` |
| `device control`, `devices` | `/device-control` |
| `run tests` | `/test-execution/run-tests` |
| `incidents`, `alerts` | `/monitoring/incidents` |
| `heatmap` | `/monitoring/heatmap` |
| `reports` | `/test-results/reports` |
| `test builder` | `/builder/test-builder` |
| `ai agent`, `chat` | `/ai-agent` |

### useAIControllable Hook

```tsx
import { useAIControllable } from '../hooks/ai';

const RunButton = () => {
  const buttonRef = useRef<HTMLButtonElement>(null);
  
  useAIControllable({
    elementId: 'run-btn',
    ref: buttonRef,
    onAction: (action, params) => {
      if (action === 'click') handleRunClick();
    }
  });
  
  return <button ref={buttonRef}>Run Test</button>;
};
```

---

## 6. Global Badge System

Floating badges show real-time agent activity across all pages.

### Badge Behavior

```
┌─────────────────────────────────────────────────────────────────┐
│                         ANY PAGE                                 │
│                                                                  │
│                                                                  │
│                                       ┌────────────────────────┐│
│                                       │ 🧪 Sherlock        (2) ││ ← Manual on TOP
│                                       │    Checking incidents  ││
│                                       │    ●●○ processing      ││
│                                       └────────────────────────┘│
│                                       ┌────────────────────────┐│
│                                       │ 🛡️ Guardian            ││ ← Auto below
│                                       │    Health check        ││
│                                       │    ●○○ processing      ││
│                                       └────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Stacking Rules

1. **Manual triggers** → Always on TOP (user initiated = priority)
2. **Auto triggers** → Stack BELOW manual ones
3. **One badge per agent** (with task count if multiple)

### Badge States

| State | Visual | Duration |
|-------|--------|----------|
| Processing | `●●○` dots | Until complete |
| Complete (manual) | `✓` + summary | Until user dismisses |
| Complete (auto) | `✓` flash | 10 seconds then fade |
| Error | `⚠` red | Until acknowledged |

### On Completion (Manual Tasks)

```
┌────────────────────────────────────────┐
│ 🧪 Sherlock                        ✓   │
│ ──────────────────────────────────────│
│ Found 3 open incidents                 │
│                                        │
│ Was this helpful?  [👍] [👎]           │
│ [↩ Back to Chat]  [✕ Dismiss]         │
└────────────────────────────────────────┘
```

---

## 7. API Reference

### Chat & Sessions

```bash
# Health check
GET /server/agent/health

# Create session
POST /server/agent/sessions

# List sessions
GET /server/agent/sessions

# Get/Delete session
GET/DELETE /server/agent/sessions/<id>
```

### Agent Registry

```bash
# List agents
GET /server/agents?team_id=<team_id>

# Get agent
GET /server/agents/<agent_id>?team_id=<team_id>

# Import from YAML
POST /server/agents/import
Content-Type: text/yaml

# Export to YAML
GET /server/agents/<agent_id>/export
```

### Agent Runtime

```bash
# List instances
GET /server/runtime/instances

# Start agent
POST /server/runtime/instances/start
Body: {"agent_id": "qa-web-manager", "version": "1.0.0"}

# Stop/Pause/Resume
POST /server/runtime/instances/<instance_id>/stop
POST /server/runtime/instances/<instance_id>/pause
POST /server/runtime/instances/<instance_id>/resume
```

### Events

```bash
# Publish event
POST /api/events/publish
Body: {
  "type": "alert.blackscreen",
  "payload": {"device_id": "device1"},
  "priority": "critical"
}

# Get stats
GET /api/events/stats
```

### Benchmarks & Feedback

```bash
# Run benchmark
POST /server/benchmarks/run
Body: {"agent_id": "qa-web-manager", "version": "1.0.0"}

# Submit feedback
POST /server/benchmarks/feedback
Body: {"agent_id": "...", "rating": 5, "comment": "Great!"}

# Get leaderboard
GET /server/benchmarks/leaderboard

# Compare agents
GET /server/benchmarks/compare?ids=agent1:1.0.0,agent2:1.0.0
```

### SocketIO Events

| Event | Direction | Data |
|-------|-----------|------|
| `join_session` | Client → Server | `{session_id}` |
| `send_message` | Client → Server | `{session_id, message, agent_id, allow_auto_navigation, current_page}` |
| `agent_event` | Server → Client | Thinking, tool_call, message, etc. |
| `ui_action` | Server → Client | navigate, interact, highlight, toast |

**`send_message` payload:**
```json
{
  "session_id": "uuid",
  "message": "how many alerts?",
  "team_id": "default",
  "agent_id": "ai-assistant",
  "allow_auto_navigation": true,
  "current_page": "/ai-agent"
}
```

---

## 8. Frontend Integration

### AI Context

Global state provider wrapping the application:

```tsx
// App.tsx
<AIProvider>
  <AgentActivityProvider>
    <AIOmniOverlay />
    <GlobalAgentBadges />
    <AgentActivityBridge />
    {/* App content */}
  </AgentActivityProvider>
</AIProvider>
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `AICommandBar` | Global (Cmd+K) | Quick command input |
| `AgentPilotPanel` | Right sidebar | Agent steps & status |
| `GlobalAgentBadges` | Bottom-right | Real-time activity badges |
| `AgentDashboard` | `/agent-dashboard` | Manage all agents |
| `AgentChat` | `/ai-agent` | Chat with agents |

### Agent Dashboard Features

- **Three tabs**: Agents | Benchmarks | Leaderboard
- **Dark theme** with gold accents
- **Auto-start** enabled agents on load
- **Per-agent controls**: Start, Stop, Export, Rate, Benchmark, Enable/Disable
- **Activity Log**: Expandable panel with all actions

### Agent Chat Features

- **Agent selector** dropdown with nicknames
- **Conversation history** sidebar
- **Real-time streaming** of agent responses
- **Tool call visualization** (collapsible)
- **Approval requests** when needed

---

## 9. Scoring & Feedback

### Score Formula

```
Overall = (Benchmark × 40%) + (UserRating × 30%) + (SuccessRate × 20%) + (Cost × 10%)
```

| Component | Weight | Source |
|-----------|--------|--------|
| Benchmark Score | 40% | Automated tests (0-100) |
| User Rating | 30% | 1-5 stars → 0-100 |
| Success Rate | 20% | Execution history |
| Cost Efficiency | 10% | Tokens per task |

### Benchmark Categories

| Category | Tests | Description |
|----------|-------|-------------|
| navigation | 2 | List UIs, navigate to nodes |
| detection | 2 | Device status, health checks |
| execution | 2 | List test cases, load details |
| analysis | 2 | Coverage summary, requirements |
| recovery | 2 | Handle invalid input, timeouts |

### Feedback Collection

- **Per task** rating (👍/👎 or 1-5 stars)
- **Optional comment** for detailed feedback
- **Automatic collection** after task completion

---

## 10. Quick Start

### Prerequisites

```bash
# Start Redis (required for Event Bus)
sudo systemctl start redis-server   # Linux
brew services start redis           # macOS
```

### Start Backend

```bash
./setup/local/launch_server.sh
# Or
./backend_server/scripts/launch_virtualserver.sh
```

### Start Frontend

```bash
./setup/local/launch_frontend.sh
```

### Access URLs

| URL | Description |
|-----|-------------|
| `http://localhost:5073/ai-agent` | Agent Chat |
| `http://localhost:5073/agent-dashboard` | Agent Dashboard |
| `http://localhost:5109/api/...` | Backend API |

### Quick Test

```bash
# Import custom agent
curl -X POST http://localhost:5109/server/agents/import \
  -H "Content-Type: text/yaml" \
  --data-binary @my-agent.yaml

# Publish test event
curl -X POST http://localhost:5109/api/events/publish \
  -H "Content-Type: application/json" \
  -d '{"type": "alert.blackscreen", "payload": {"device_id": "test"}, "priority": "high"}'
```

---

## 11. File Structure

```
backend_server/src/
├── agent/
│   ├── agents/                    # Specialist agents
│   │   ├── base_agent.py
│   │   ├── explorer.py
│   │   ├── builder.py
│   │   ├── executor.py
│   │   ├── analyst.py
│   │   └── maintainer.py
│   ├── core/
│   │   ├── manager.py             # QA Manager orchestrator
│   │   ├── session.py
│   │   └── tool_bridge.py
│   ├── registry/
│   │   ├── config_schema.py       # Pydantic models
│   │   ├── registry.py            # CRUD operations
│   │   ├── validator.py           # YAML validation
│   │   └── templates/             # Agent YAMLs
│   │       ├── qa-web-manager.yaml
│   │       ├── qa-mobile-manager.yaml
│   │       ├── qa-stb-manager.yaml
│   │       ├── monitoring-manager.yaml
│   │       ├── qa-manager.yaml
│   │       ├── explorer.yaml
│   │       └── executor.yaml
│   ├── runtime/
│   │   ├── runtime.py
│   │   └── state.py
│   ├── skills/
│   │   └── skill_registry.py
│   └── async_utils.py
├── events/
│   ├── event_bus.py
│   └── event_router.py
├── resources/
│   └── lock_manager.py
├── database/
│   └── async_client.py
└── routes/
    ├── server_agent_routes.py
    ├── agent_registry_routes.py
    ├── agent_runtime_routes.py
    ├── agent_benchmark_routes.py
    └── event_routes.py

frontend/src/
├── pages/
│   ├── AgentChat.tsx
│   └── AgentDashboard.tsx
├── components/
│   ├── agent/
│   │   ├── AgentSelector.tsx
│   │   ├── AgentStatus.tsx
│   │   ├── GlobalAgentBadges.tsx
│   │   └── AgentActivityBridge.tsx
│   └── ai/
│       ├── AICommandBar.tsx
│       ├── AIOmniOverlay.tsx
│       └── panels/
│           ├── AgentPilotPanel.tsx
│           └── LogTerminalPanel.tsx
├── contexts/
│   ├── AIContext.tsx
│   └── AgentActivityContext.tsx
├── hooks/
│   └── ai/
│       └── useAIControllable.ts
└── lib/
    └── ai/
        └── pageSchema.ts

setup/db/schema/
├── 020_event_system.sql
├── 021_agent_registry.sql
└── 022_agent_feedback_benchmarks.sql
```

---

## Implementation Status

### ✅ Implemented

| Component | Status |
|-----------|--------|
| Event Bus (Redis + PostgreSQL) | ✅ |
| Resource Lock Manager | ✅ |
| Agent Registry (CRUD, versioning) | ✅ |
| Agent Runtime (start/stop/pause/resume) | ✅ |
| Agent Templates (7 YAML files) | ✅ |
| Database Schemas | ✅ |
| REST API Routes | ✅ |
| Agent Dashboard | ✅ |
| Agent Chat with selector | ✅ |
| Skill Registry & Validation | ✅ |
| Auto-start Agents | ✅ |
| Interactive Navigation | ✅ |
| **2-Step Workflow (Navigate → Execute)** | ✅ |
| **Auto-Navigation Toggle** | ✅ |
| **Page Context Awareness** | ✅ |
| Global Badge System | ✅ |
| User Feedback (1-5 stars) | ✅ |
| Benchmark Tests | ✅ |
| Agent Scoring System | ✅ |
| Leaderboard & Comparison | ✅ |
| Agent Nicknames & Icons | ✅ |

### 🚧 Not Yet Implemented

| Component | Priority |
|-----------|----------|
| Cost Controls (Langfuse) | Medium |
| Preemption Logic | Low |
| Marketplace UI | Low |
| A/B Testing | Low |

---

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
SUPABASE_DB_URI=postgresql://...
REDIS_URL=redis://localhost:6379

# Optional
AGENT_MODEL=claude-sonnet-4-20250514
AGENT_MAX_TOKENS=8192
```

---

## Troubleshooting

### AI says "Cannot navigate to X"
- Check alias in `NAVIGATION_ALIASES` (backend)
- Check path in `PAGE_SCHEMAS` (frontend)

### Element doesn't respond to AI
- Ensure `useAIControllable` hook is added
- Verify `elementId` matches schema
- Check console for `ai-interact` events

### Badge not appearing
- Verify `AgentActivityProvider` wraps app
- Check `GlobalAgentBadges` is rendered
- Confirm `AgentActivityBridge` is connecting events

### Redis connection failed
- Run `redis-cli ping` to verify Redis is running
- Check `REDIS_URL` in environment

---

*Document Version: 2.1*  
*Last Updated: December 2024*  
*Changelog: Added 2-Step Workflow documentation*

