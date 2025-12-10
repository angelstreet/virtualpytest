# VirtualPyTest Agent Architecture

## Overview

VirtualPyTest uses a **skill-based agent architecture** where 3 purpose-driven agents dynamically load specialized skills based on user requests and system events.

```
┌──────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER                               │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
│  │  Assistant   │   │   Monitor    │   │   Analyzer   │         │
│  │  Atlas       │   │  Guardian    │   │  Sherlock    │         │
│  │              │   │              │   │              │         │
│  │  Trigger:    │   │  Trigger:    │   │  Trigger:    │         │
│  │  User Chat   │   │  Events      │   │  Script Done │         │
│  │              │   │              │   │              │         │
│  │  Mode:       │   │  Mode:       │   │  Mode:       │         │
│  │  Interactive │   │  Autonomous  │   │  Autonomous  │         │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘         │
│         │                  │                  │                  │
│         ▼                  ▼                  ▼                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     SKILL LAYER                          │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  exploration-mobile │ incident-response │ result-validation│  │
│  │  exploration-web    │ health-check      │ false-positive   │  │
│  │  exploration-stb    │ alert-triage      │ report-generation│  │
│  │  execution          │                   │                  │  │
│  │  design             │                   │                  │  │
│  │  monitoring-read    │                   │                  │  │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     TOOL LAYER (MCP)                     │   │
│  │  70+ tools: take_control, create_node, execute_testcase  │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## The 3 Agents

### 1. Assistant (Atlas)

**Purpose:** Interactive QA assistant for human-driven tasks

| Property | Value |
|----------|-------|
| ID | `assistant` |
| Nickname | Atlas |
| Selectable | Yes (default in UI) |
| Trigger | User chat messages |
| Mode | Interactive |

**Available Skills:**
- `exploration-mobile` - Build navigation trees for Android apps
- `exploration-web` - Build navigation trees for web apps
- `exploration-stb` - Build navigation trees for STB/TV apps
- `execution` - Run testcases and scripts
- `design` - Create testcases and manage requirements
- `monitoring-read` - Check device status (read-only)

**Example Interactions:**
```
User: "Explore the sauce-demo web app"
Atlas: Loading skill: exploration-web
       [OK] Loaded skill: exploration-web
       [Proceeds with web exploration workflow]

User: "Run testcase TC_AUTH_01"
Atlas: Loading skill: execution
       [OK] Loaded skill: execution
       [Executes the testcase]
```

---

### 2. Monitor (Guardian)

**Purpose:** Autonomous monitor that responds to system events

| Property | Value |
|----------|-------|
| ID | `monitor` |
| Nickname | Guardian |
| Selectable | No (event-driven only) |
| Trigger | Alerts, webhooks, schedules |
| Mode | Autonomous |

**Event Triggers:**
- `alert.blackscreen` (critical)
- `alert.app_crash` (critical)
- `alert.anr` (critical)
- `alert.no_signal` (critical)
- `webhook.ci_failure` (high)
- `schedule.health_check` (normal)

**Available Skills:**
- `incident-response` - Handle critical incidents
- `health-check` - Perform scheduled system checks
- `alert-triage` - Classify and route alerts

---

### 3. Analyzer (Sherlock)

**Purpose:** Analyzes execution results and detects false positives

| Property | Value |
|----------|-------|
| ID | `analyzer` |
| Nickname | Sherlock |
| Selectable | No (trigger-driven only) |
| Trigger | Script/test completion |
| Mode | Autonomous |

**Event Triggers:**
- `script.completed` (normal)
- `testcase.completed` (normal)
- `deployment.execution_done` (normal)

**Available Skills:**
- `result-validation` - Validate execution results
- `false-positive-detection` - Identify flaky tests
- `report-generation` - Generate execution reports

---

## How Skill Loading Works

### Router Mode vs Skill Mode

Each agent operates in one of two modes:

#### Router Mode (Default)
- Agent has minimal tools for quick queries
- Analyzes user request to determine which skill to load
- Responds with `LOAD SKILL [skill-name]` when specialized work is needed

#### Skill Mode (After Loading)
- Agent has full tool access from the loaded skill
- Follows the skill's workflow instructions
- Can unload skill with `UNLOAD SKILL` command

### Skill Loading Flow

```
┌─────────────────┐
│  User Message   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Router Mode    │◄─────────────────────┐
│  (minimal tools)│                      │
└────────┬────────┘                      │
         │                               │
         ▼                               │
┌─────────────────┐     No skill needed  │
│ Quick query?    │──────────────────────┤
│ (list, status)  │                      │
└────────┬────────┘                      │
         │ Yes, complex task             │
         ▼                               │
┌─────────────────┐                      │
│ LOAD SKILL      │                      │
│ [skill-name]    │                      │
└────────┬────────┘                      │
         │                               │
         ▼                               │
┌─────────────────┐                      │
│  Skill Mode     │                      │
│  (full tools)   │                      │
└────────┬────────┘                      │
         │                               │
         ▼                               │
┌─────────────────┐                      │
│ Task complete   │──────────────────────┘
│ UNLOAD SKILL    │
└─────────────────┘
```

### Example: Web Exploration

```
1. User: "Explore the sauce-demo app"

2. Atlas (Router Mode):
   - Has tools: list_userinterfaces, get_device_info, list_testcases
   - Matches "explore" + "web app" to exploration-web skill
   - Response: "Loading skill: exploration-web"

3. Atlas loads exploration-web skill

4. Atlas (Skill Mode):
   - Has tools: take_control, dump_ui_elements, create_node, create_edge, etc.
   - Follows exploration workflow from skill's system_prompt
   - Executes web exploration

5. Task complete -> UNLOAD SKILL -> Back to Router Mode
```

---

## Skill Definitions

Skills are defined in YAML files at `backend_server/src/agent/skills/definitions/`.

### Skill YAML Structure

```yaml
name: skill-name                    # Unique identifier
version: 1.0.0                      # Semantic version
description: |                      # Agent uses this to decide
  Short description of what this skill does.

triggers:                           # Keywords for auto-matching
  - keyword phrase 1
  - keyword phrase 2

system_prompt: |                    # Workflow instructions for LLM
  You are doing X.
  
  ## WORKFLOW
  1. Step one
  2. Step two
  
  ## RULES
  - Important rule

tools:                              # MCP tools to expose
  - tool_name_1
  - tool_name_2

platform: null                      # mobile, web, stb, or null
requires_device: false              # Needs device control?
timeout_seconds: 1800               # Default timeout
```

### Available Skills

#### Assistant Skills

| Skill | Platform | Device Required | Description |
|-------|----------|-----------------|-------------|
| `exploration-mobile` | mobile | Yes | Build Android navigation trees using ADB |
| `exploration-web` | web | Yes | Build web app navigation trees using DOM |
| `exploration-stb` | stb | Yes | Build TV navigation trees using D-pad |
| `execution` | all | Yes | Run testcases and scripts |
| `design` | all | No | Create testcases, manage requirements |
| `monitoring-read` | all | No | Check device status (read-only) |

#### Monitor Skills

| Skill | Platform | Device Required | Description |
|-------|----------|-----------------|-------------|
| `incident-response` | all | Yes | Handle critical system incidents |
| `health-check` | all | No | Scheduled system health verification |
| `alert-triage` | all | No | Classify alerts and determine response |

#### Analyzer Skills

| Skill | Platform | Device Required | Description |
|-------|----------|-----------------|-------------|
| `result-validation` | all | No | Validate execution results |
| `false-positive-detection` | all | No | Detect flaky tests |
| `report-generation` | all | No | Generate execution reports |

---

## Agent Definitions

Agents are defined in YAML files at `backend_server/src/agent/registry/templates/`.

### Agent YAML Structure

```yaml
metadata:
  id: assistant
  name: QA Assistant
  nickname: Atlas
  selectable: true          # Appears in UI dropdown
  default: true             # Default selection
  version: 2.0.0
  author: system
  description: "Interactive QA assistant"
  tags: [qa, assistant]
  suggestions:              # Example prompts in chat UI
    - "Explore the sauce-demo web app"
    - "Run testcase TC_AUTH_01"

triggers:
  - type: chat.message
    priority: normal

event_pools:
  - own.assistant-tasks

available_skills:           # Skills this agent can load
  - exploration-mobile
  - exploration-web
  - exploration-stb
  - execution
  - design
  - monitoring-read

skills:                     # Router mode tools (minimal)
  - list_userinterfaces
  - get_device_info
  - list_testcases
  - list_hosts

permissions:
  devices:
    - read
    - take_control
  database:
    - read
    - write.testcases

config:
  enabled: true
  max_parallel_tasks: 1
  timeout_seconds: 3600
```

---

## File Structure

```
backend_server/src/agent/
├── skills/
│   ├── __init__.py
│   ├── skill_schema.py         # Pydantic model for skills
│   ├── skill_loader.py         # YAML loader
│   ├── skill_registry.py       # Tool validation
│   └── definitions/            # Skill YAML files
│       ├── exploration-mobile.yaml
│       ├── exploration-web.yaml
│       ├── exploration-stb.yaml
│       ├── execution.yaml
│       ├── design.yaml
│       ├── monitoring-read.yaml
│       ├── incident-response.yaml
│       ├── health-check.yaml
│       ├── alert-triage.yaml
│       ├── result-validation.yaml
│       ├── false-positive-detection.yaml
│       └── report-generation.yaml
├── registry/
│   ├── config_schema.py        # Agent Pydantic model
│   ├── registry.py             # Agent loading
│   └── templates/              # Agent YAML files
│       ├── assistant.yaml
│       ├── monitor.yaml
│       └── analyzer.yaml
├── core/
│   ├── manager.py              # QAManagerAgent (main orchestrator)
│   ├── session.py              # Chat session management
│   ├── tool_bridge.py          # MCP tool execution
│   └── message_types.py        # Event types
└── runtime/
    └── runtime.py              # Event handling
```

---

## Adding a New Skill

### Step 1: Create Skill YAML

Create `skills/definitions/my-new-skill.yaml`:

```yaml
name: my-new-skill
version: 1.0.0
description: |
  What this skill does in one sentence.

triggers:
  - keyword 1
  - keyword 2

system_prompt: |
  You perform [task description].
  
  ## WORKFLOW
  1. First step
  2. Second step
  
  ## RULES
  - Important rule

tools:
  - tool_1
  - tool_2
  - tool_3

platform: null
requires_device: false
timeout_seconds: 1800
```

### Step 2: Add to Agent

Edit the agent's YAML file and add to `available_skills`:

```yaml
available_skills:
  - existing-skill
  - my-new-skill    # Add here
```

### Step 3: Restart Server

The skill will be loaded automatically on server startup.

---

## Event Types

The agent system emits these events via WebSocket:

| Event | Description |
|-------|-------------|
| `thinking` | Agent is reasoning |
| `tool_call` | Tool being called |
| `tool_result` | Tool execution result |
| `message` | Agent message to user |
| `skill_loaded` | Skill dynamically loaded |
| `skill_unloaded` | Skill unloaded |
| `session_ended` | Chat session complete |
| `error` | Error occurred |

---

## API Endpoints

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/server/agent/health` | Health check |
| POST | `/server/agent/api-key` | Save Anthropic API key |
| POST | `/server/agent/sessions` | Create chat session |
| GET | `/server/agent/sessions` | List sessions |
| GET | `/server/agent/sessions/<id>` | Get session |
| DELETE | `/server/agent/sessions/<id>` | Delete session |

### WebSocket Events (namespace: `/agent`)

| Event | Direction | Description |
|-------|-----------|-------------|
| `join_session` | Client -> Server | Join session room |
| `send_message` | Client -> Server | Send chat message |
| `stop_generation` | Client -> Server | Stop agent |
| `agent_event` | Server -> Client | Agent response events |

### Send Message Payload

```json
{
  "session_id": "uuid",
  "message": "User message",
  "team_id": "team-uuid",
  "agent_id": "assistant",
  "allow_auto_navigation": false,
  "current_page": "/dashboard"
}
```

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (or set per-user) |
| `DEFAULT_MODEL` | Claude model to use (default: claude-sonnet-4-20250514) |
| `LANGFUSE_ENABLED` | Enable observability (default: false) |

### Agent Config Options

```yaml
config:
  enabled: true              # Auto-start on server startup
  max_parallel_tasks: 1      # Concurrent task limit
  approval_required_for: []  # Actions needing approval
  auto_retry: true           # Retry failed tasks
  timeout_seconds: 3600      # Task timeout
```

---

## Skill Matching Logic

When a user sends a message, the assistant uses this logic to select a skill:

1. **Trigger Matching:** Each skill has `triggers` (keyword phrases)
2. **Score Calculation:** For each trigger found in the message, score += trigger length
3. **Best Match:** Skill with highest score wins
4. **No Match:** Use router tools for simple queries

```python
# Example matching
message = "explore the sauce-demo web application"

# exploration-web triggers: ["explore web", "map web app", "web tree"]
# Score: "explore web" not found, "map web app" not found
# -> Score = 0

# But "web" is in multiple triggers, so partial matching helps
# The LLM uses the skill descriptions to make the final decision
```

---

## Best Practices

### For Users

1. **Be Specific:** "Explore the sauce-demo web app" is better than "explore"
2. **One Task at a Time:** Complete current task before switching
3. **Use Suggestions:** Click the example prompts in the chat UI
4. **Check Status:** "Show device status" before running tests

### For Developers

1. **Keep Skills Focused:** Each skill should do one thing well
2. **Document Workflows:** Clear system_prompt with step-by-step instructions
3. **Minimal Tools:** Only include tools the skill actually needs
4. **Test Triggers:** Ensure triggers match expected user phrases

---

## Troubleshooting

### "Skill not loading"

- Check skill name is in agent's `available_skills`
- Verify skill YAML exists in `skills/definitions/`
- Check server logs for YAML parsing errors

### "Tool not found"

- Verify tool name in skill's `tools` list
- Check tool exists in MCP tool definitions
- Restart server to reload tools

### "Empty response from agent"

- Too many tools can overwhelm the model
- Check `max_tokens` setting
- Review server logs for API errors

### "Skill stuck in loop"

- Add clear completion criteria to system_prompt
- Use `UNLOAD SKILL` to return to router mode
- Clear session with "clear session" command

