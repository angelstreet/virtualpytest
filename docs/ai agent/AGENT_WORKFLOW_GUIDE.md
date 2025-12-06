# Multi-Agent Platform - Complete Workflow Guide

## 📋 Overview

This guide explains how the multi-agent platform works, how to configure agents, link them to YAML templates, and assign skills.

---

## 🎯 Available Agents

### 1. **QA Web Manager** (`qa-web-manager`)
- **Platform**: Web browsers
- **Purpose**: Monitor and validate web-based userinterfaces
- **Triggers**: 
  - `alert.blackscreen` (web)
  - `alert.page_load_timeout`
  - `build.deployed` (web)
  - `schedule.web_regression`
- **Skills**: Web navigation, browser automation, responsive design validation
- **Parallel Tasks**: 5 (can test multiple browsers simultaneously)

### 2. **QA Mobile Manager** (`qa-mobile-manager`)
- **Platform**: Android/iOS mobile devices
- **Purpose**: Validate mobile applications and UX
- **Triggers**:
  - `alert.blackscreen` (mobile)
  - `alert.app_crash`
  - `alert.device_offline` (mobile)
  - `build.deployed` (mobile)
  - `schedule.mobile_regression`
- **Skills**: Touch gestures, orientation changes, mobile performance
- **Parallel Tasks**: 3

### 3. **QA STB Manager** (`qa-stb-manager`)
- **Platform**: Set-Top Boxes, Android TV
- **Purpose**: Validate STB interfaces and video playback
- **Triggers**:
  - `alert.blackscreen` (stb)
  - `alert.video_playback_failed`
  - `alert.channel_change_failed`
  - `build.deployed` (stb)
  - `schedule.stb_regression`
- **Skills**: Remote control navigation, video validation, channel switching
- **Parallel Tasks**: 2

### 4. **Monitoring Manager** (`monitoring-manager`)
- **Platform**: All (infrastructure monitoring)
- **Purpose**: Monitor device health, detect incidents, system monitoring
- **Triggers**:
  - `schedule.health_check` (every 5 minutes)
  - `alert.device_offline`
  - `alert.service_down`
  - `alert.high_cpu` (>= 90%)
  - `alert.high_memory` (>= 85%)
  - `alert.disk_space_low` (<= 10%)
- **Skills**: Health checks, service monitoring, log analysis, alerting
- **Parallel Tasks**: 10 (monitors many devices simultaneously)

### 5. **QA Manager** (`qa-manager`) - General Purpose
- **Platform**: All platforms (coordinator)
- **Purpose**: General QA coordination, delegates to specialized agents
- **Sub-agents**: Explorer, Builder, Executor, Analyst, Maintainer

### 6. **Explorer** (`explorer`)
- **Type**: On-demand specialist
- **Purpose**: UI discovery and navigation tree building

### 7. **Executor** (`executor`)
- **Type**: On-demand specialist
- **Purpose**: Execute testcases and campaigns

---

## 🔧 How YAML Configuration Works

### YAML Structure

Each agent is defined by a YAML file with this structure:

```yaml
metadata:
  id: agent-unique-id           # Unique identifier
  name: Human Readable Name      # Display name
  version: 1.0.0                 # Semantic version
  author: system                 # Creator
  description: Brief description
  tags: [qa, automation]         # Categorization

goal:
  type: continuous               # 'continuous' or 'on-demand'
  description: What the agent does

triggers:                        # Events that activate this agent
  - type: alert.blackscreen
    priority: critical
    filters:                     # Optional event filtering
      platform: web

event_pools:                     # Event channels to subscribe to
  - shared.alerts
  - own.agent-tasks

subagents:                       # Delegate tasks to specialists
  - id: explorer
    version: ">=1.0.0"
    delegate_for:
      - ui_discovery

skills:                          # Functions the agent can call
  - list_userinterfaces
  - take_control
  - execute_testcase

permissions:                     # Access control
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

## 🔗 How Agents Link to Skills

### Skill Mapping

Skills in YAML map to **MCP tools** in `/backend_server/src/mcp/`:

#### Example Skill Mappings:

| YAML Skill | MCP Tool | File Location |
|------------|----------|---------------|
| `list_userinterfaces` | `list_userinterfaces()` | `mcp/tool_definitions/navigation_definitions.py` |
| `take_control` | `take_control_of_device()` | `mcp/tool_definitions/device_definitions.py` |
| `execute_testcase` | `execute_testcase()` | `mcp/tool_definitions/execution_definitions.py` |
| `list_requirements` | `list_requirements()` | `mcp/tool_definitions/requirements_definitions.py` |
| `get_device_info` | `get_device_info()` | `mcp/tool_definitions/device_definitions.py` |
| `view_logs` | `view_logs()` | `mcp/tool_definitions/monitoring_definitions.py` |

### How Skills Work:

1. **YAML Configuration**: Agent's `skills` list defines what it can do
2. **Agent Registry**: Validates skills against available MCP tools
3. **Agent Runtime**: When agent runs, only listed skills are accessible
4. **MCP Server**: Executes the actual tool function
5. **Permissions**: Cross-checked against `permissions` section

---

## 📦 Complete Workflow: From YAML to Execution

### Step 1: Import Agent from YAML

```bash
# Import QA Web Manager
curl -X POST http://localhost:5109/api/agents/import \
  -H "Content-Type: text/yaml" \
  --data-binary @backend_server/src/agent/registry/templates/qa-web-manager.yaml
```

**What happens:**
1. YAML is validated against `AgentDefinition` schema
2. Agent stored in `agent_registry` table
3. Event triggers stored in `agent_event_triggers` table
4. Status set to `draft`

### Step 2: Publish Agent

```bash
# Publish to make it active
curl -X POST http://localhost:5109/api/agents/qa-web-manager/publish \
  -H "Content-Type: application/json" \
  -d '{"version": "1.0.0"}'
```

**What happens:**
1. Agent status changed from `draft` to `published`
2. Agent now eligible to handle events

### Step 3: Event Triggers Agent

**Automatic (when event occurs):**
```bash
# Event published (e.g., from monitoring system)
curl -X POST http://localhost:5109/api/events/publish \
  -H "Content-Type: application/json" \
  -d '{
    "type": "alert.blackscreen",
    "payload": {
      "device_id": "web-chrome-001",
      "platform": "web",
      "severity": "critical"
    },
    "priority": "critical"
  }'
```

**What happens:**
1. Event published to Event Bus (Redis)
2. Event logged to `event_log` table
3. Event Router queries `agent_event_triggers`
4. Finds `qa-web-manager` matches `alert.blackscreen` + `platform: web`
5. Checks filters match
6. Starts agent instance

### Step 4: Agent Instance Runs

```bash
# Start agent manually (on-demand agents)
curl -X POST http://localhost:5109/api/runtime/instances \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "qa-web-manager",
    "version": "1.0.0"
  }'
```

**What happens:**
1. Agent Runtime Manager creates instance
2. Record added to `agent_instances` table
3. Resource locks acquired if needed (device access)
4. Agent execution begins
5. Skills are callable via MCP server
6. Execution tracked in `agent_execution_history`

### Step 5: Monitor Agent Status

```bash
# Get instance status
curl http://localhost:5109/api/runtime/instances/{instance_id}
```

**Response:**
```json
{
  "instance_id": "inst_abc123",
  "agent_id": "qa-web-manager",
  "version": "1.0.0",
  "state": "running",
  "current_task": {
    "task_id": "task_xyz",
    "description": "Investigating blackscreen on web-chrome-001",
    "status": "running",
    "progress": "2/5 steps"
  },
  "last_heartbeat": "2025-12-06T10:30:00Z"
}
```

---

## 🎨 How to Create a New Agent

### Example: Create "Performance Monitor" Agent

1. **Create YAML file** (`performance-monitor.yaml`):

```yaml
metadata:
  id: performance-monitor
  name: Performance Monitor
  version: 1.0.0
  author: your-team
  description: Monitors application performance metrics

goal:
  type: continuous
  description: Track performance KPIs and alert on degradation

triggers:
  - type: schedule.performance_check
    priority: normal
  - type: alert.slow_response
    priority: high

skills:
  - get_execution_results
  - query_metrics
  - analyze_performance
  - create_alert

permissions:
  database: [read]
  external: [slack]

config:
  max_parallel_tasks: 1
  timeout_seconds: 600
  budget_limit_usd: 10.00
```

2. **Import to Registry:**
```bash
curl -X POST http://localhost:5109/api/agents/import \
  -H "Content-Type: text/yaml" \
  --data-binary @performance-monitor.yaml
```

3. **Publish:**
```bash
curl -X POST http://localhost:5109/api/agents/performance-monitor/publish \
  -d '{"version": "1.0.0"}'
```

4. **Test Manually:**
```bash
curl -X POST http://localhost:5109/api/runtime/instances \
  -d '{"agent_id": "performance-monitor", "version": "1.0.0"}'
```

---

## 🔍 Available Skills Reference

### Device & Navigation
- `list_devices` - Get all devices
- `get_device_info` - Device details
- `take_control` - Lock device for exclusive use
- `navigate_to_node` - Navigate to UI node
- `send_remote_key` - Send remote control command (STB)
- `execute_gesture` - Touch gesture (mobile)

### User Interfaces
- `list_userinterfaces` - List all UIs
- `get_userinterface_complete` - Full UI details
- `list_nodes` - UI navigation nodes
- `list_edges` - UI navigation edges
- `preview_userinterface` - UI preview

### Test Execution
- `list_testcases` - All testcases
- `load_testcase` - Load testcase details
- `execute_testcase` - Run a testcase
- `execute_campaign` - Run campaign
- `get_execution_status` - Execution status
- `get_execution_results` - Execution results

### Requirements
- `list_requirements` - All requirements
- `get_requirement` - Requirement details
- `get_coverage_summary` - Coverage stats
- `get_uncovered_requirements` - Gaps in coverage

### Monitoring & Logs
- `view_logs` - View system logs
- `get_service_status` - Service health
- `check_device_health` - Device health check
- `get_system_metrics` - System metrics
- `create_alert` - Create alert
- `list_alerts` - View alerts

### Verifications
- `list_verifications` - Available verifications
- `verify_element_visible` - Check visibility
- `verify_video_playing` - Video playback (STB)
- `capture_screenshot` - Take screenshot

---

## 🎯 Event Types & Triggers

### System Events
- `alert.blackscreen` - Black screen detected
- `alert.device_offline` - Device unreachable
- `alert.service_down` - Service failure
- `alert.high_cpu` - High CPU usage
- `alert.high_memory` - High memory usage

### Application Events
- `alert.app_crash` - Application crash
- `alert.page_load_timeout` - Page load failed
- `alert.video_playback_failed` - Video error
- `alert.channel_change_failed` - Channel switch failed

### Build/Deployment Events
- `build.deployed` - New build deployed
- `build.failed` - Build failure

### Scheduled Events
- `schedule.regression` - Run regression tests
- `schedule.health_check` - System health check
- `schedule.web_regression` - Web tests
- `schedule.mobile_regression` - Mobile tests
- `schedule.stb_regression` - STB tests
- `schedule.nightly_sanity` - Nightly sanity

### Task Events (for on-demand agents)
- `task.explore_ui` - Trigger explorer
- `task.execute_test` - Trigger executor
- `task.execute_campaign` - Campaign execution

---

## 📊 Monitoring & Analytics

### View Agent Metrics
```bash
# Get performance metrics for an agent
curl http://localhost:5109/api/agents/qa-web-manager/metrics
```

**Response:**
```json
{
  "total_executions": 150,
  "successful_executions": 142,
  "failed_executions": 8,
  "success_rate_percent": 94.67,
  "avg_duration_seconds": 45.2,
  "avg_token_usage": 1250,
  "total_cost_usd": 18.75,
  "avg_cost_per_task_usd": 0.125,
  "avg_user_rating": 4.5
}
```

### List All Running Instances
```bash
curl http://localhost:5109/api/runtime/instances
```

### View Event Log
```bash
# Query database
SELECT * FROM event_log 
WHERE event_type LIKE 'alert.%' 
ORDER BY timestamp DESC 
LIMIT 10;
```

---

## 🚀 Quick Start Checklist

1. ✅ **Database schemas applied** (020, 021)
2. ✅ **Redis running** (`brew services start redis`)
3. ✅ **Backend server running**
4. ✅ **Import agents**:
   ```bash
   curl -X POST http://localhost:5109/api/agents/import \
     --data-binary @qa-web-manager.yaml
   ```
5. ✅ **Publish agents**
6. ✅ **Configure scheduled events** (in `scheduled_events` table)
7. ✅ **Publish test events** to verify routing
8. ✅ **Monitor in UI** (AgentStatus component)

---

## 🎓 Summary

- **YAML files** = Agent configuration templates
- **Skills** = MCP tools the agent can call
- **Triggers** = Events that activate the agent
- **Event Router** = Matches events to agents
- **Agent Registry** = Stores agent definitions
- **Agent Runtime** = Manages running instances
- **Resource Locks** = Prevents device conflicts

The system is **fully event-driven** and **autonomous** - agents respond to events automatically without human intervention!

