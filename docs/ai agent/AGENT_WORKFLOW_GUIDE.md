# Multi-Agent Platform - Complete Workflow Guide

## 📋 Overview

This guide explains how the multi-agent platform works, how to configure agents, link them to YAML templates, and assign skills.

**Implementation Status: ~85% Complete**

---

## 🎯 Pre-configured Agents

The following agents are **pre-loaded** in the Agent Dashboard and **auto-start** when enabled:

### 1. **QA Web Manager** (`qa-web-manager`)
- **Platform**: Web browsers
- **Purpose**: Monitor and validate web-based userinterfaces
- **Triggers**: `alert.blackscreen`, `alert.page_load_timeout`, `build.deployed`, `schedule.web_regression`
- **Parallel Tasks**: 5

### 2. **QA Mobile Manager** (`qa-mobile-manager`)
- **Platform**: Android/iOS mobile devices
- **Purpose**: Validate mobile applications and UX
- **Triggers**: `alert.blackscreen`, `alert.app_crash`, `alert.device_offline`, `build.deployed`
- **Parallel Tasks**: 3

### 3. **QA STB Manager** (`qa-stb-manager`)
- **Platform**: Set-Top Boxes, Android TV
- **Purpose**: Validate STB interfaces and video playback
- **Triggers**: `alert.blackscreen`, `alert.video_playback_failed`, `alert.channel_change_failed`
- **Parallel Tasks**: 2

### 4. **Monitoring Manager** (`monitoring-manager`)
- **Platform**: All (infrastructure monitoring)
- **Purpose**: Monitor device health, detect incidents
- **Triggers**: `schedule.health_check`, `alert.device_offline`, `alert.service_down`
- **Parallel Tasks**: 10

### 5. **QA Manager** (`qa-manager`) - General Purpose
- **Platform**: All platforms (coordinator)
- **Sub-agents**: Explorer, Builder, Executor, Analyst, Maintainer

### 6. **Explorer** (`explorer`) - On-demand specialist
### 7. **Executor** (`executor`) - On-demand specialist

---

## 🖥️ Agent Dashboard UI

Access: **http://localhost:5073/agent-dashboard**

### Features:
- **Dark theme** with gold accents (professional look)
- **Auto-start**: All enabled agents start automatically on load
- **Three tabs**: Agents | Benchmarks | Leaderboard
- **Controls per agent**:
  - ▶️ Start / ⏹️ Stop
  - ⬇️ Export YAML
  - ⭐ Rate agent (1-5 stars)
  - ⚡ Run benchmark
  - 🔘 Enable/Disable toggle
- **Activity Log**: Expandable panel showing all agent actions
- **Import**: Upload YAML files to add new agents
- **Benchmarks Tab**: Run tests and view results
- **Leaderboard Tab**: Compare agents by score

---

## 🔧 YAML Configuration Structure

```yaml
metadata:
  id: agent-unique-id           # Unique identifier (lowercase, hyphens)
  name: Human Readable Name
  version: 1.0.0                # Semantic version
  author: system
  description: Brief description
  tags: [qa, automation]

goal:
  type: continuous              # 'continuous' or 'on-demand'
  description: What the agent does

triggers:
  - type: alert.blackscreen
    priority: critical
    filters:
      platform: web

event_pools:
  - shared.alerts
  - own.agent-tasks

subagents:
  - id: explorer
    version: ">=1.0.0"
    delegate_for:
      - ui_discovery

skills:                         # Must be valid MCP tool names!
  - list_userinterfaces
  - take_control
  - execute_testcase

permissions:
  devices: [read, take_control]
  database: [read, write.results]
  external: [jira, slack]

config:
  max_parallel_tasks: 3
  approval_required_for: []
  auto_retry: true
  timeout_seconds: 3600
  budget_limit_usd: 50.00
```

---

## 🔗 Skills → MCP Tools Mapping

Skills in YAML are **validated** against available MCP tools at import time.

### Skill Categories:

| Category | Tools | Location |
|----------|-------|----------|
| **control** | `take_control`, `release_control` | `control_definitions.py` |
| **device** | `get_device_info`, `list_hosts` | `device_definitions.py` |
| **navigation** | `navigate_to_node`, `list_nodes`, `list_edges` | `navigation_definitions.py` |
| **testcase** | `list_testcases`, `load_testcase`, `execute_testcase` | `testcase_definitions.py` |
| **requirements** | `list_requirements`, `get_coverage_summary` | `requirements_definitions.py` |
| **verification** | `list_verifications`, `verify_element` | `verification_definitions.py` |
| **userinterface** | `list_userinterfaces`, `get_userinterface_complete` | `userinterface_definitions.py` |
| **logs** | `view_logs`, `get_error_logs` | `logs_definitions.py` |
| **tree** | `list_navigation_nodes`, `build_navigation_tree` | `tree_definitions.py` |
| **screenshot** | `capture_screenshot`, `get_screenshot` | `screenshot_definitions.py` |
| **exploration** | `explore_ui`, `discover_elements` | `exploration_definitions.py` |

### Skill Validation:
```python
# When importing, unknown skills trigger a warning:
[@agent_validator] ⚠️ Unknown skills: fake_skill, nonexistent_tool
```

---

## 📦 API Endpoints

### Agent Registry

```bash
# List all agents
GET http://localhost:5109/api/agents?team_id=<team_id>

# Get agent details
GET http://localhost:5109/api/agents/<agent_id>?team_id=<team_id>

# Import agent from YAML
POST http://localhost:5109/api/agents/import
Content-Type: text/yaml
Body: <yaml content>

# Export agent to YAML
GET http://localhost:5109/api/agents/<agent_id>/export?team_id=<team_id>
```

### Agent Runtime

```bash
# List running instances
GET http://localhost:5109/api/runtime/instances?team_id=<team_id>

# Start agent
POST http://localhost:5109/api/runtime/instances/start
Body: {"agent_id": "qa-web-manager", "version": "1.0.0"}

# Stop agent
POST http://localhost:5109/api/runtime/instances/<instance_id>/stop

# Pause agent
POST http://localhost:5109/api/runtime/instances/<instance_id>/pause

# Resume agent
POST http://localhost:5109/api/runtime/instances/<instance_id>/resume

# Get runtime status
GET http://localhost:5109/api/runtime/status
```

### Events

```bash
# Publish event
POST http://localhost:5109/api/events/publish
Body: {
  "type": "alert.blackscreen",
  "payload": {"device_id": "device1"},
  "priority": "critical"
}

# Get event stats
GET http://localhost:5109/api/events/stats?team_id=<team_id>
```

### Benchmarks & Feedback

```bash
# List benchmark tests
GET http://localhost:5109/api/benchmarks/tests

# Run benchmark for an agent
POST http://localhost:5109/api/benchmarks/run
Body: {"agent_id": "qa-web-manager", "version": "1.0.0"}

# Execute pending benchmark run
POST http://localhost:5109/api/benchmarks/run/<run_id>/execute

# List benchmark runs
GET http://localhost:5109/api/benchmarks/runs?team_id=<team_id>

# Get benchmark run details
GET http://localhost:5109/api/benchmarks/runs/<run_id>

# Submit user feedback (1-5 stars)
POST http://localhost:5109/api/benchmarks/feedback
Body: {
  "agent_id": "qa-web-manager",
  "version": "1.0.0",
  "rating": 5,
  "comment": "Great agent!"
}

# List feedback for agent
GET http://localhost:5109/api/benchmarks/feedback?agent_id=<agent_id>

# Get agent scores
GET http://localhost:5109/api/benchmarks/scores?team_id=<team_id>

# Get leaderboard
GET http://localhost:5109/api/benchmarks/leaderboard?team_id=<team_id>

# Compare agents side-by-side
GET http://localhost:5109/api/benchmarks/compare?ids=qa-web-manager:1.0.0,qa-stb-manager:1.0.0
```

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Start Redis (required for Event Bus)
sudo systemctl start redis-server

# Or on macOS:
brew services start redis
```

### 2. Start Backend Server

```bash
./setup/local/launch_server.sh
```

### 3. Start Frontend

```bash
./setup/local/launch_frontend.sh
```

### 4. Open Agent Dashboard

Navigate to: **http://localhost:5073/agent-dashboard**

- Agents auto-load from predefined templates
- Enabled agents auto-start
- Use controls to manage each agent

### 5. Import Custom Agent

```bash
curl -X POST http://localhost:5109/api/agents/import \
  -H "Content-Type: text/yaml" \
  --data-binary @my-custom-agent.yaml
```

---

## 📂 File Structure

```
backend_server/src/
├── agent/
│   ├── registry/
│   │   ├── config_schema.py    # Pydantic models
│   │   ├── registry.py         # CRUD operations
│   │   ├── validator.py        # YAML validation + skill validation
│   │   └── templates/          # Pre-defined agent YAMLs
│   │       ├── qa-web-manager.yaml
│   │       ├── qa-mobile-manager.yaml
│   │       ├── qa-stb-manager.yaml
│   │       ├── monitoring-manager.yaml
│   │       ├── qa-manager.yaml
│   │       ├── explorer.yaml
│   │       └── executor.yaml
│   ├── runtime/
│   │   ├── runtime.py          # Instance lifecycle
│   │   └── state.py            # State management
│   ├── skills/
│   │   └── skill_registry.py   # Skill validation
│   └── async_utils.py          # Flask/async bridge
├── events/
│   ├── event_bus.py            # Redis pub/sub + DB logging
│   └── event_router.py         # Event → Agent routing
├── resources/
│   └── lock_manager.py         # Device locking
├── routes/
│   ├── agent_registry_routes.py
│   ├── agent_runtime_routes.py
│   ├── agent_benchmark_routes.py  # Benchmarks & feedback
│   └── event_routes.py
└── database/
    └── async_client.py         # asyncpg (pgbouncer-compatible)

frontend/src/
├── pages/
│   └── AgentDashboard.tsx      # Main dashboard (dark theme)
└── components/agent/
    ├── AgentSelector.tsx
    └── AgentStatus.tsx

setup/db/schema/
├── 020_event_system.sql          # event_log, resource_locks, scheduled_events
├── 021_agent_registry.sql        # agent_registry, agent_instances, execution_history
└── 022_agent_feedback_benchmarks.sql  # feedback, benchmarks, scores, leaderboard
```

---

## 🎯 Event Types

### Alert Events
- `alert.blackscreen` - Black screen detected
- `alert.device_offline` - Device unreachable
- `alert.service_down` - Service failure
- `alert.app_crash` - Application crash
- `alert.video_playback_failed` - Video error
- `alert.high_cpu` / `alert.high_memory` - Resource alerts

### Build Events
- `build.deployed` - New build deployed
- `build.failed` - Build failure

### Scheduled Events
- `schedule.health_check` - Periodic health check
- `schedule.regression` - Regression tests
- `schedule.web_regression` / `schedule.mobile_regression` / `schedule.stb_regression`

### Task Events
- `task.explore_ui` - Trigger explorer
- `task.execute_test` - Execute test
- `task.execute_campaign` - Run campaign

---

## 🔄 Agent Lifecycle

```
YAML Template → Import → Registry (draft)
                            ↓
                      Publish → (published)
                            ↓
Event occurs → Event Router → Match Agent
                            ↓
                   Start Instance → (running)
                            ↓
                   Execute Skills via MCP
                            ↓
                   Complete / Error → Stop
```

### Agent States:
- `active` - Ready to start
- `running` - Currently executing
- `paused` - Temporarily suspended
- `disabled` - Won't auto-start
- `error` - Failed state

---

## ⚙️ Configuration

### Environment Variables

```bash
# .env file
SUPABASE_DB_URI=postgresql://...  # Required for database
REDIS_URL=redis://localhost:6379   # Required for Event Bus
```

### Database Schemas

Apply in Supabase SQL Editor:
1. `setup/db/schema/020_event_system.sql`
2. `setup/db/schema/021_agent_registry.sql`

---

## 📊 What's Implemented

| Component | Status |
|-----------|--------|
| Event Bus (Redis + PostgreSQL) | ✅ |
| Resource Lock Manager | ✅ |
| Agent Registry (CRUD, versioning) | ✅ |
| Agent Runtime (start/stop/pause/resume) | ✅ |
| Agent Templates (7 YAML files) | ✅ |
| Database Schemas | ✅ |
| REST API Routes | ✅ |
| Frontend Dashboard | ✅ |
| Skill Registry & Validation | ✅ |
| Auto-start Agents | ✅ |
| pgbouncer Compatibility | ✅ |
| **User Feedback (1-5 stars)** | ✅ |
| **Benchmark Tests (10 default)** | ✅ |
| **Agent Scoring System** | ✅ |
| **Leaderboard & Comparison** | ✅ |

## 📊 What's NOT Implemented Yet

| Component | Priority |
|-----------|----------|
| Cost Controls (Langfuse) | Medium |
| Preemption Logic | Low |
| Marketplace UI | Low |
| A/B Testing | Low |

---

## 📈 Scoring System

### How Scores are Calculated

| Component | Weight | Source |
|-----------|--------|--------|
| Benchmark Score | 40% | Automated tests (0-100) |
| User Rating | 30% | User feedback 1-5 stars → 0-100 |
| Success Rate | 20% | Execution history |
| Cost Efficiency | 10% | Tokens per task (TBD) |

**Formula**: `Overall = (Benchmark × 0.4) + (UserRating × 0.3) + (SuccessRate × 0.2) + (Cost × 0.1)`

### Benchmark Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| navigation | 2 | List UIs, navigate to nodes |
| detection | 2 | Device status, health checks |
| execution | 2 | List test cases, load details |
| analysis | 2 | Coverage summary, requirements |
| recovery | 2 | Handle invalid input, timeouts |

### Comparing Agents

Use the compare endpoint to compare:
- **Same agent, different versions**: `qa-web-manager:1.0.0,qa-web-manager:2.0.0`
- **Different agents, same goal**: `qa-web-manager:1.0.0,qa-stb-manager:1.0.0`
- **Leaderboard**: Global ranking by overall score

---

## 🎓 Summary

- **YAML files** = Agent configuration templates
- **Skills** = MCP tools the agent can call (validated at import)
- **Triggers** = Events that activate the agent
- **Event Router** = Matches events to agents
- **Agent Registry** = Stores agent definitions
- **Agent Runtime** = Manages running instances
- **Resource Locks** = Prevents device conflicts
- **Dashboard** = Dark UI at `/agent-dashboard`

The system is **event-driven** and **autonomous** - agents auto-start and respond to events automatically!
