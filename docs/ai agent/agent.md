# VirtualPyTest Agent Architecture v2.1

## Overview

VirtualPyTest uses a **token-optimized skill-based agent architecture** where 3 purpose-driven agents dynamically load micro-skills (2-8 tools each) with prompt caching for 90% cost reduction.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           AGENT LAYER                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                      │
│  │  Assistant   │   │   Monitor    │   │   Analyzer   │                      │
│  │  Atlas       │   │  Guardian    │   │  Sherlock    │                      │
│  │              │   │              │   │              │                      │
│  │  Interactive │   │  Autonomous  │   │  Autonomous  │                      │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                      │
│         │                  │                  │                              │
│         ▼                  ▼                  ▼                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      MICRO-SKILL LAYER (2-8 tools each)              │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │ run-script  │ │run-testcase │ │list-resources│ │device-status│    │   │
│  │  │  2 tools    │ │   2 tools   │ │   4 tools   │ │   2 tools   │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │explore-web  │ │explore-mobile│ │ explore-stb │ │create-testcase│  │   │
│  │  │  8 tools    │ │   8 tools   │ │   7 tools   │ │   4 tools   │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    PROMPT CACHE LAYER                                │   │
│  │  ┌────────────────────────────────────────────────────────────┐     │   │
│  │  │  Cached: System Prompt + Tool Definitions (5 min TTL)      │     │   │
│  │  │  First call: Full price | Subsequent: 90% discount         │     │   │
│  │  └────────────────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       TOOL LAYER (MCP)                               │   │
│  │  70+ tools available, only loaded when skill requests them           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## The 3 Agents

### 1. Assistant (Atlas)

**Purpose:** Interactive QA assistant for human-driven tasks

**Architecture Note:** Unlike Monitor and Analyzer agents, Atlas has no router tools and operates purely in skill-based mode for simplicity and predictability.

| Property | Value |
|----------|-------|
| ID | `assistant` |
| Nickname | Atlas |
| Selectable | Yes (default in UI) |
| Trigger | User chat messages |
| Mode | Interactive (skill-based only) |

**Available Skills (9 micro-skills):**

| Skill | Tools | Purpose |
|-------|-------|---------|
| `run-script` | 2 | Execute Python scripts |
| `run-testcase` | 2 | Execute testcases |
| `list-resources` | 4 | List scripts/testcases/devices |
| `device-status` | 2 | Check device health |
| `explore-mobile` | 8 | Build Android navigation trees |
| `explore-web` | 8 | Build web navigation trees |
| `explore-stb` | 7 | Build STB navigation trees |
| `create-testcase` | 4 | Create testcases |
| `manage-requirements` | 5 | Track requirements/coverage |

**Example Interactions:**
```
User: "Run goto script on google_tv"
Atlas: LOAD SKILL run-script
Atlas: [Now in run-script skill mode - 2 tools]
       Calling: get_compatible_hosts
       Calling: execute_script
       **goto** on device1: PASSED (7.5s)
       [Report](url) | [Logs](url)
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

**Available Skills (3 micro-skills):**

| Skill | Tools | Purpose |
|-------|-------|---------|
| `incident-response` | 4 | Handle critical incidents |
| `health-check` | 2 | System health verification |
| `alert-triage` | 2 | Classify and route alerts |

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

**Available Skills (3 micro-skills):**

| Skill | Tools | Purpose |
|-------|-------|---------|
| `validate-result` | 2 | Validate execution results |
| `detect-false-positive` | 2 | Identify flaky tests |
| `generate-report` | 3 | Generate execution reports |

---

## Prompt Caching

The agent uses Anthropic's prompt caching to reduce costs by up to 90%.

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    API CALL #1 (First)                      │
├─────────────────────────────────────────────────────────────┤
│  System Prompt     [cache_control: ephemeral]  -> CACHED    │
│  Tool Definitions  [cache_control: ephemeral]  -> CACHED    │
│  User Message                                               │
│  ───────────────────────────────────────────────────────    │
│  Cost: Full price (creates cache)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API CALL #2 (Cached)                     │
├─────────────────────────────────────────────────────────────┤
│  System Prompt     <- READ FROM CACHE (90% cheaper)         │
│  Tool Definitions  <- READ FROM CACHE (90% cheaper)         │
│  User Message                                               │
│  Tool Result #1                                             │
│  ───────────────────────────────────────────────────────    │
│  Cost: 90% discount on cached portions                      │
└─────────────────────────────────────────────────────────────┘
```

### Cache Metrics

The system logs cache performance:
```
[CACHE] Created cache with 1200 tokens
[CACHE] Read 1200 tokens from cache (90% cheaper)
```

### Cache TTL

- **Duration:** 5 minutes (ephemeral)
- **Scope:** Per skill (system prompt + tools)
- **Requirement:** Minimum 1024 tokens to cache

---

## Token Optimization

### Before vs After

| Scenario | Before (Broad Skills) | After (Micro-Skills + Cache) | Savings |
|----------|----------------------|------------------------------|---------|
| Run script | ~18,000 tokens | ~1,600 tokens | **91%** |
| Run testcase | ~18,000 tokens | ~1,600 tokens | **91%** |
| List resources | ~5,000 tokens | ~1,400 tokens | **72%** |

### Why Micro-Skills Save Tokens

| Factor | Broad Skill | Micro-Skill |
|--------|-------------|-------------|
| Tools per skill | 13-21 | 2-8 |
| Tool definition tokens | ~3,000 | ~600 |
| Sent on every API call | Yes | Yes |
| With caching | 10% of 3,000 = 300 | 10% of 600 = 60 |

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

system_prompt: |                    # Workflow instructions (keep concise!)
  Execute X on devices.
  
  WORKFLOW:
  1. get_compatible_hosts(userinterface_name)
  2. execute_X(params)
  
  RESPONSE FORMAT:
  **{name}** on {device}: {PASSED|FAILED} ({time}s)

tools:                              # MCP tools (2-8 max for token efficiency)
  - tool_name_1
  - tool_name_2

platform: null                      # mobile, web, stb, or null
requires_device: false              # Needs device control?
timeout_seconds: 1800               # Default timeout
```

### All 15 Micro-Skills

#### Execution Skills (4)

| Skill | Tools | Triggers |
|-------|-------|----------|
| `run-script` | get_compatible_hosts, execute_script | "run script", "execute script" |
| `run-testcase` | get_compatible_hosts, execute_testcase | "run testcase", "execute test" |
| `list-resources` | list_scripts, list_testcases, list_hosts, list_userinterfaces | "list scripts", "list testcases" |
| `device-status` | get_device_info, get_compatible_hosts | "device status", "check device" |

#### Exploration Skills (3)

| Skill | Tools | Triggers |
|-------|-------|----------|
| `explore-mobile` | 8 tools (take_control, dump_ui_elements, create_node, etc.) | "explore mobile", "android" |
| `explore-web` | 8 tools (take_control, dump_ui_elements, create_node, etc.) | "explore web", "website" |
| `explore-stb` | 7 tools (take_control, capture_screenshot, create_node, etc.) | "explore stb", "tv" |

#### Design Skills (2)

| Skill | Tools | Triggers |
|-------|-------|----------|
| `create-testcase` | list_userinterfaces, generate_and_save_testcase, save_testcase, list_testcases | "create testcase" |
| `manage-requirements` | create_requirement, list_requirements, link_testcase_to_requirement, get_coverage_summary, get_uncovered_requirements | "requirements", "coverage" |

#### Monitor Skills (3)

| Skill | Tools | Triggers |
|-------|-------|----------|
| `incident-response` | take_control, release_control, capture_screenshot, get_device_info | "alert.blackscreen" |
| `health-check` | list_hosts, get_device_info | "health check" |
| `alert-triage` | get_device_info, capture_screenshot | "triage alert" |

#### Analyzer Skills (3)

| Skill | Tools | Triggers |
|-------|-------|----------|
| `validate-result` | get_execution_status, load_testcase | "validate results" |
| `detect-false-positive` | get_execution_status, load_testcase | "false positive", "flaky" |
| `generate-report` | get_execution_status, list_testcases, get_coverage_summary | "generate report" |

---

## How Skill Loading Works

### Skill-Based Operation

The assistant operates in a single skill-based mode:

| Mode | Tools | Purpose |
|------|-------|---------|
| Skill Mode | 2-8 (from loaded skill) | Analyze request → load skill → execute task |

**No Router Tools:** Unlike other agents, Atlas has no router tools. It always analyzes the user's request and loads the most appropriate skill directly.

### Skill Loading Flow

```
User: "Run goto script on google_tv"
         │
         ▼
┌─────────────────────────────────────┐
│  Analyze Request                     │
│  Matches "run script" -> run-script  │
│  Response: LOAD SKILL run-script     │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Load run-script (2 tools)          │
│  - get_compatible_hosts             │
│  - execute_script                   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Execute with cached tools          │
│  1. get_compatible_hosts            │
│  2. execute_script                  │
│  3. Return result                   │
└─────────────────────────────────────┘
```

**Note:** Atlas has no intermediate router mode. It analyzes the request and loads the skill directly.

---

## File Structure

```
backend_server/src/agent/
├── skills/
│   ├── __init__.py
│   ├── skill_schema.py         # Pydantic model
│   ├── skill_loader.py         # YAML loader
│   ├── skill_registry.py       # Tool validation
│   └── definitions/            # 15 micro-skill YAML files
│       ├── run-script.yaml
│       ├── run-testcase.yaml
│       ├── list-resources.yaml
│       ├── device-status.yaml
│       ├── explore-mobile.yaml
│       ├── explore-web.yaml
│       ├── explore-stb.yaml
│       ├── create-testcase.yaml
│       ├── manage-requirements.yaml
│       ├── incident-response.yaml
│       ├── health-check.yaml
│       ├── alert-triage.yaml
│       ├── validate-result.yaml
│       ├── detect-false-positive.yaml
│       └── generate-report.yaml
├── registry/
│   ├── config_schema.py        # Agent Pydantic model
│   ├── registry.py             # Agent loading
│   └── templates/              # 3 agent YAML files
│       ├── assistant.yaml      # 9 available skills
│       ├── monitor.yaml        # 3 available skills
│       └── analyzer.yaml       # 3 available skills
├── core/
│   ├── manager.py              # With prompt caching
│   ├── session.py              # Chat session
│   ├── tool_bridge.py          # MCP execution
│   └── message_types.py        # Event types
└── runtime/
    └── runtime.py              # Event handling
```

---

## Adding a New Micro-Skill

### Step 1: Create Skill YAML (2-8 tools max)

```yaml
# skills/definitions/my-skill.yaml
name: my-skill
version: 1.0.0
description: Short description

triggers:
  - keyword 1
  - keyword 2

system_prompt: |
  Execute task.
  1. tool_1(param)
  2. tool_2(param)

tools:
  - tool_1
  - tool_2

platform: null
requires_device: false
timeout_seconds: 600
```

### Step 2: Add to Agent

```yaml
# registry/templates/assistant.yaml
available_skills:
  - existing-skill
  - my-skill    # Add here
```

### Step 3: Restart Server

---

## Event Types

| Event | Description |
|-------|-------------|
| `thinking` | Agent reasoning |
| `tool_call` | Tool being called |
| `tool_result` | Tool result |
| `message` | Agent response |
| `skill_loaded` | Skill loaded |
| `session_ended` | Session complete |
| `error` | Error occurred |

---

## API Endpoints

### REST

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/server/agent/health` | Health check |
| POST | `/server/agent/api-key` | Save API key |
| POST | `/server/agent/sessions` | Create session |
| GET | `/server/agent/sessions/<id>` | Get session |

### WebSocket (namespace: `/agent`)

| Event | Direction | Description |
|-------|-----------|-------------|
| `send_message` | Client -> Server | Send message |
| `agent_event` | Server -> Client | Agent events |

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key |
| `DEFAULT_MODEL` | Claude model |

### Agent Config

```yaml
config:
  enabled: true
  max_parallel_tasks: 1
  timeout_seconds: 3600
```

---

## Best Practices

### For Token Efficiency

1. **Keep skills focused:** 2-8 tools per skill
2. **Short system prompts:** No verbose examples
3. **Use prompt caching:** Enabled by default
4. **Match triggers precisely:** Better skill selection

### For Users

1. **Be specific:** "Run goto script on google_tv"
2. **One task at a time:** Complete before switching skills
3. **Use suggestions:** Click example prompts
4. **Skill-based:** Atlas always loads a skill - be clear about what you want to accomplish

---

## Troubleshooting

### "High token usage"

- Check skill has 2-8 tools (not 13+)
- Verify prompt caching is working (check logs for `[CACHE]`)
- Review system_prompt length

### "Skill not loading"

- Check skill name in `available_skills` (Atlas has no router tools)
- Verify YAML exists in `skills/definitions/`
- Be specific in requests - Atlas analyzes and loads skills directly

### "Cache not working"

- Minimum 1024 tokens required
- Cache TTL is 5 minutes
- Check `anthropic-beta` header
