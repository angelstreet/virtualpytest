# VirtualPyTest Skills Architecture Migration Plan

## Executive Summary

Migrate from **7 platform-based agents** to **3 purpose-based agents** that dynamically load skills.

---

## Part 1: Architecture Overview

### 3 Independent Agents

```
┌──────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
│  │  Assistant   │   │   Monitor    │   │   Analyzer   │         │
│  │              │   │              │   │              │         │
│  │  Trigger:    │   │  Trigger:    │   │  Trigger:    │         │
│  │  User Chat   │   │  Events      │   │  Script Done │         │
│  │              │   │  (alerts,    │   │              │         │
│  │  Mode:       │   │  webhooks)   │   │  Mode:       │         │
│  │  Interactive │   │              │   │  Autonomous  │         │
│  │              │   │  Mode:       │   │              │         │
│  │              │   │  Autonomous  │   │              │         │
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
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     TOOL LAYER (MCP)                     │   │
│  │  70+ tools: take_control, create_node, execute_testcase  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Agent Summary

| Agent | Trigger | Mode | Skills | Purpose |
|-------|---------|------|--------|---------|
| **Assistant** | User chat | Interactive | exploration-*, execution, design | Human-driven QA tasks |
| **Monitor** | Events (alerts, webhooks, CI/CD) | Autonomous | incident-response, health-check, alert-triage | React to system events |
| **Analyzer** | Script/test completion | Autonomous | result-validation, false-positive-detection, report-generation | Validate execution results |

### Current vs Target

| Current (7 agents) | Target (3 agents) |
|--------------------|-------------------|
| ai-assistant | → **assistant** |
| qa-mobile-manager | → assistant + exploration-mobile skill |
| qa-web-manager | → assistant + exploration-web skill |
| qa-stb-manager | → assistant + exploration-stb skill |
| qa-execution-manager | → assistant + execution skill |
| qa-design-manager | → assistant + design skill |
| monitoring-manager | → **monitor** |
| *(new)* | → **analyzer** |

---

## Part 2: Skill Definition Schema

### Skill YAML Structure

```yaml
# skills/definitions/{skill-name}.yaml
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

### Skill Pydantic Schema

```python
# skills/skill_schema.py
from pydantic import BaseModel, Field
from typing import List, Optional

class SkillDefinition(BaseModel):
    name: str = Field(..., pattern="^[a-z0-9-]+$")
    version: str = Field(default="1.0.0")
    description: str = Field(..., min_length=10)
    triggers: List[str] = Field(default_factory=list)
    system_prompt: str = Field(..., min_length=50)
    tools: List[str] = Field(..., min_items=1)
    platform: Optional[str] = Field(default=None)
    requires_device: bool = Field(default=False)
    timeout_seconds: int = Field(default=1800)
```

---

## Part 3: Agent Definitions

### 3.1 Assistant Agent

```yaml
# registry/templates/assistant.yaml
metadata:
  id: assistant
  name: QA Assistant
  nickname: Atlas
  selectable: true
  default: true
  version: 2.0.0
  author: system
  description: "Interactive QA assistant for human-driven tasks"
  tags:
    - qa
    - assistant
    - interactive
  suggestions:
    - "Explore the sauce-demo web app"
    - "Run testcase TC_AUTH_01"
    - "Create a testcase for login"
    - "Show me device status"

triggers:
  - type: chat.message
    priority: normal

available_skills:
  - exploration-mobile
  - exploration-web
  - exploration-stb
  - execution
  - design
  - monitoring-read  # Read-only status checks

# Minimal tools for router mode (before skill loads)
tools:
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
    - write.results

config:
  enabled: true
  max_parallel_tasks: 1
  auto_retry: true
  timeout_seconds: 3600
```

### 3.2 Monitor Agent

```yaml
# registry/templates/monitor.yaml
metadata:
  id: monitor
  name: QA Monitor
  nickname: Guardian
  selectable: false  # Not user-selectable, event-driven only
  version: 2.0.0
  author: system
  description: "Autonomous monitor that responds to system events"
  tags:
    - monitoring
    - autonomous
    - events

triggers:
  - type: alert.blackscreen
    priority: critical
  - type: alert.app_crash
    priority: critical
  - type: alert.anr
    priority: critical
  - type: alert.no_signal
    priority: critical
  - type: webhook.ci_failure
    priority: high
  - type: schedule.health_check
    priority: normal

event_pools:
  - shared.alerts
  - shared.builds
  - shared.ci

available_skills:
  - incident-response
  - health-check
  - alert-triage

tools:
  - get_device_info
  - list_hosts
  - get_alerts
  - capture_screenshot

permissions:
  devices:
    - read
    - take_control
  database:
    - read
    - write.incidents
  external:
    - slack
    - jira

config:
  enabled: true
  max_parallel_tasks: 3  # Can handle multiple incidents
  auto_retry: true
  timeout_seconds: 600
```

### 3.3 Analyzer Agent

```yaml
# registry/templates/analyzer.yaml
metadata:
  id: analyzer
  name: Result Analyzer
  nickname: Sherlock
  selectable: false  # Not user-selectable, trigger-driven only
  version: 2.0.0
  author: system
  description: "Analyzes script and test results to detect false positives"
  tags:
    - analysis
    - autonomous
    - validation

triggers:
  - type: script.completed
    priority: normal
  - type: testcase.completed
    priority: normal
  - type: deployment.execution_done
    priority: normal

event_pools:
  - shared.executions
  - shared.results

available_skills:
  - result-validation
  - false-positive-detection
  - report-generation

tools:
  - get_execution_status
  - list_testcases
  - load_testcase
  - capture_screenshot
  - get_deployment_history

permissions:
  devices:
    - read
  database:
    - read
    - write.analysis_results
  external:
    - slack

config:
  enabled: true
  max_parallel_tasks: 5  # Can analyze multiple results
  auto_retry: true
  timeout_seconds: 300
```

---

## Part 4: Skill Definitions

### 4.1 Assistant Skills

#### exploration-mobile.yaml

```yaml
name: exploration-mobile
version: 1.0.0
description: |
  Explore Android mobile applications and build navigation trees.
  Uses ADB to dump UI elements and extract resource-id selectors.

triggers:
  - explore mobile
  - explore android
  - build mobile navigation
  - map mobile app
  - dump ui mobile

system_prompt: |
  You explore Android mobile apps to build navigation models.
  
  ## WORKFLOW
  1. get_compatible_hosts(userinterface_name) → find device
  2. take_control(host_name, device_id, tree_id) → lock device
  3. For each screen:
     - dump_ui_elements(platform='mobile')
     - analyze_screen_for_action(elements, platform='mobile')
     - analyze_screen_for_verification(elements, platform='mobile')
     - create_node with verifications
     - save_node_screenshot
     - create_edge with selectors from analyze_screen_for_action
  4. release_control when done
  
  ## SELECTOR PRIORITY (Mobile)
  1. resource-id (most stable)
  2. content-desc
  3. text
  4. xpath (last resort)
  
  ## RULES
  - ALWAYS take_control before device operations
  - ALWAYS release_control when finished
  - ALWAYS save screenshots for nodes

tools:
  - get_compatible_hosts
  - take_control
  - release_control
  - dump_ui_elements
  - analyze_screen_for_action
  - analyze_screen_for_verification
  - create_node
  - update_node
  - create_edge
  - update_edge
  - save_node_screenshot
  - navigate_to_node
  - list_nodes
  - list_edges
  - capture_screenshot
  - get_node
  - get_edge
  - create_subtree

platform: mobile
requires_device: true
timeout_seconds: 1800
```

#### exploration-web.yaml

```yaml
name: exploration-web
version: 1.0.0
description: |
  Explore web applications and build navigation trees.
  Uses DOM inspection to extract CSS/XPath selectors.

triggers:
  - explore web
  - build web navigation
  - map web app
  - map website

system_prompt: |
  You explore web applications to build navigation models.
  
  ## WORKFLOW
  1. get_compatible_hosts(userinterface_name) → find browser device
  2. take_control(host_name, device_id, tree_id) → lock device
  3. For each screen:
     - dump_ui_elements(platform='web')
     - analyze_screen_for_action(elements, platform='web')
     - analyze_screen_for_verification(elements, platform='web')
     - create_node with verifications
     - save_node_screenshot
     - create_edge with selectors
  4. release_control when done
  
  ## SELECTOR PRIORITY (Web)
  1. #id (CSS ID - most stable)
  2. [data-testid] (test attributes)
  3. .class (CSS class)
  4. xpath (last resort)
  
  ## WEB-SPECIFIC
  - Use click_element_by_id when element has ID
  - Use CSS selectors over XPath when possible
  - Handle dynamic content with appropriate waits

tools:
  - get_compatible_hosts
  - take_control
  - release_control
  - dump_ui_elements
  - analyze_screen_for_action
  - analyze_screen_for_verification
  - create_node
  - update_node
  - create_edge
  - update_edge
  - save_node_screenshot
  - navigate_to_node
  - list_nodes
  - list_edges
  - capture_screenshot
  - get_node
  - get_edge
  - create_subtree

platform: web
requires_device: true
timeout_seconds: 1800
```

#### exploration-stb.yaml

```yaml
name: exploration-stb
version: 1.0.0
description: |
  Explore set-top box and TV applications using D-pad navigation.
  Uses screenshot + AI vision (no UI dump available on STB).

triggers:
  - explore stb
  - explore tv
  - build tv navigation
  - map stb app
  - map tv app

system_prompt: |
  You explore STB/TV apps to build navigation models.
  
  ## IMPORTANT: STB HAS NO UI DUMP
  - STB devices cannot dump UI hierarchy
  - Use capture_screenshot + AI vision to analyze screens
  - Navigation is D-pad based (UP, DOWN, LEFT, RIGHT, OK, BACK)
  
  ## WORKFLOW
  1. get_compatible_hosts(userinterface_name) → find STB device
  2. take_control(host_name, device_id, tree_id) → lock device
  3. For each screen:
     - capture_screenshot → get current screen
     - Analyze screenshot visually for navigation options
     - create_node (verifications based on visual elements)
     - save_node_screenshot
     - create_edge with D-pad actions (press_key)
  4. release_control when done
  
  ## D-PAD NAVIGATION
  - Commands: press_key with key: UP, DOWN, LEFT, RIGHT, OK, BACK
  - Include action_type: 'remote' for all actions
  - Add wait_time in params for timing
  
  ## EDGE FORMAT (STB)
  action_sets: [
    {
      id: "home_to_settings",
      actions: [{
        command: "press_key",
        action_type: "remote",
        params: { key: "RIGHT", wait_time: 1500 }
      }]
    }
  ]

tools:
  - get_compatible_hosts
  - take_control
  - release_control
  - capture_screenshot
  - create_node
  - update_node
  - create_edge
  - update_edge
  - save_node_screenshot
  - navigate_to_node
  - list_nodes
  - list_edges
  - get_node
  - get_edge
  - create_subtree
  - execute_device_action

platform: stb
requires_device: true
timeout_seconds: 2400
```

#### execution.yaml

```yaml
name: execution
version: 1.0.0
description: |
  Execute testcases and scripts on any platform.
  Manages deployments and scheduled test runs.

triggers:
  - run testcase
  - execute test
  - run script
  - execute script
  - create deployment
  - schedule test
  - run regression

system_prompt: |
  You execute testcases and scripts across all platforms.
  
  ## TESTCASE EXECUTION
  1. get_compatible_hosts(userinterface_name) → find device
  2. take_control(host_name, device_id, tree_id)
  3. execute_testcase(testcase_id, host_name, device_id)
     - Tool polls automatically until completion
  4. capture_screenshot → evidence
  5. release_control
  
  ## SCRIPT EXECUTION
  1. list_scripts → find available scripts
  2. get_compatible_hosts(userinterface_name)
  3. execute_script(script_name, host_name, device_id, parameters)
     - Tool polls automatically until completion
  4. release_control
  
  ## DEPLOYMENTS (Scheduled Execution)
  - create_deployment → schedule recurring execution
  - list_deployments → see all scheduled
  - pause_deployment / resume_deployment
  - get_deployment_history → past executions
  
  ## RULES
  - Always release_control after execution
  - Capture screenshot for evidence on failures
  - Report execution status clearly

tools:
  - get_compatible_hosts
  - take_control
  - release_control
  - list_testcases
  - load_testcase
  - execute_testcase
  - get_execution_status
  - list_scripts
  - execute_script
  - create_deployment
  - list_deployments
  - pause_deployment
  - resume_deployment
  - update_deployment
  - delete_deployment
  - get_deployment_history
  - capture_screenshot
  - get_device_info

platform: null
requires_device: true
timeout_seconds: 3600
```

#### design.yaml

```yaml
name: design
version: 1.0.0
description: |
  Create testcases, manage requirements, and track coverage.
  Design test strategies without device interaction.

triggers:
  - create testcase
  - generate test
  - create requirement
  - link testcase
  - coverage report
  - design tests

system_prompt: |
  You design testcases and manage requirements.
  
  ## TESTCASE CREATION
  - generate_and_save_testcase → AI-generated from navigation
  - save_testcase → manual testcase creation
  - list_testcases → see existing tests
  - load_testcase → view testcase details
  
  ## REQUIREMENT MANAGEMENT
  - create_requirement → define what to test
  - list_requirements → see all requirements
  - get_requirement → requirement details
  - update_requirement → modify requirement
  
  ## COVERAGE TRACKING
  - link_testcase_to_requirement → connect test to requirement
  - unlink_testcase_from_requirement → remove connection
  - get_requirement_coverage → see which tests cover requirement
  - get_coverage_summary → overall coverage stats
  - get_uncovered_requirements → gaps to fill
  
  ## BEST PRACTICES
  - Link every testcase to at least one requirement
  - Review coverage summary regularly
  - Prioritize uncovered requirements

tools:
  - generate_and_save_testcase
  - save_testcase
  - list_testcases
  - load_testcase
  - rename_testcase
  - create_requirement
  - list_requirements
  - get_requirement
  - update_requirement
  - link_testcase_to_requirement
  - unlink_testcase_from_requirement
  - get_testcase_requirements
  - get_requirement_coverage
  - get_coverage_summary
  - get_uncovered_requirements
  - list_userinterfaces
  - preview_userinterface
  - get_userinterface_complete

platform: null
requires_device: false
timeout_seconds: 600
```

#### monitoring-read.yaml

```yaml
name: monitoring-read
version: 1.0.0
description: |
  Check system status, device health, and view alerts.
  Read-only monitoring for the assistant.

triggers:
  - check status
  - device status
  - list devices
  - system health
  - show alerts

system_prompt: |
  You check system status and device health.
  
  ## DEVICE STATUS
  - list_hosts → see all registered hosts
  - get_device_info → device details and status
  - get_compatible_hosts → find devices for userinterface
  
  ## ALERTS
  - get_alerts → fetch current alerts
  
  ## RESOURCES
  - list_userinterfaces → available apps
  - list_testcases → available tests
  - list_scripts → available scripts
  - list_deployments → scheduled executions
  
  ## RULES
  - This skill is READ-ONLY
  - Do not take device control
  - Report status clearly and concisely

tools:
  - list_hosts
  - get_device_info
  - get_compatible_hosts
  - get_alerts
  - list_userinterfaces
  - list_testcases
  - list_scripts
  - list_deployments

platform: null
requires_device: false
timeout_seconds: 300
```

### 4.2 Monitor Skills

#### incident-response.yaml

```yaml
name: incident-response
version: 1.0.0
description: |
  Respond to critical incidents like blackscreen, crashes, and ANRs.
  Captures evidence and creates tickets.

triggers:
  - alert.blackscreen
  - alert.app_crash
  - alert.anr
  - alert.no_signal

system_prompt: |
  You respond to critical system incidents.
  
  ## INCIDENT WORKFLOW
  1. Acknowledge incident
  2. take_control of affected device
  3. capture_screenshot → evidence
  4. Analyze current state
  5. Attempt recovery if possible
  6. Create incident report
  7. Notify via Slack if critical
  8. release_control
  
  ## EVIDENCE COLLECTION
  - Always capture screenshot immediately
  - Note device state and any error messages
  - Record timestamp and incident type
  
  ## ESCALATION
  - Blackscreen > 5 min → Critical, notify immediately
  - App crash → High, create Jira ticket
  - ANR → Medium, log and monitor

tools:
  - take_control
  - release_control
  - capture_screenshot
  - get_device_info
  - execute_device_action
  - get_alerts

platform: null
requires_device: true
timeout_seconds: 600
```

#### health-check.yaml

```yaml
name: health-check
version: 1.0.0
description: |
  Perform scheduled health checks on devices and services.
  Verify system is operating normally.

triggers:
  - schedule.health_check
  - check health

system_prompt: |
  You perform system health checks.
  
  ## HEALTH CHECK WORKFLOW
  1. list_hosts → get all hosts
  2. For each host:
     - get_device_info → check device status
     - Verify device is responsive
     - Check for any alerts
  3. Report summary
  
  ## CHECKS TO PERFORM
  - Device online/offline status
  - Last heartbeat time
  - Any pending alerts
  - Resource availability
  
  ## REPORTING
  - All healthy → Brief summary
  - Issues found → Detailed report with recommendations

tools:
  - list_hosts
  - get_device_info
  - get_compatible_hosts
  - get_alerts

platform: null
requires_device: false
timeout_seconds: 300
```

#### alert-triage.yaml

```yaml
name: alert-triage
version: 1.0.0
description: |
  Triage incoming alerts and determine priority and response.
  Filter noise and identify real issues.

triggers:
  - new alert
  - triage alert

system_prompt: |
  You triage incoming alerts to determine appropriate response.
  
  ## TRIAGE WORKFLOW
  1. Receive alert details
  2. Check alert history (is this recurring?)
  3. Assess severity:
     - Critical: Immediate response needed
     - High: Response within 15 min
     - Medium: Response within 1 hour
     - Low: Log and monitor
  4. Determine if false positive
  5. Route to appropriate response
  
  ## FALSE POSITIVE INDICATORS
  - Alert cleared within seconds
  - Known maintenance window
  - Recurring pattern with no impact
  - Test environment alert
  
  ## ACTIONS
  - Critical → Trigger incident-response skill
  - High → Create ticket, notify team
  - Medium → Log, schedule investigation
  - Low/False positive → Log and dismiss

tools:
  - get_alerts
  - get_device_info
  - list_hosts

platform: null
requires_device: false
timeout_seconds: 120
```

### 4.3 Analyzer Skills

#### result-validation.yaml

```yaml
name: result-validation
version: 1.0.0
description: |
  Validate script and testcase execution results.
  Check if results are accurate and complete.

triggers:
  - script.completed
  - testcase.completed
  - validate results

system_prompt: |
  You validate execution results for accuracy.
  
  ## VALIDATION WORKFLOW
  1. Get execution details (get_execution_status)
  2. Load testcase/script definition
  3. Compare expected vs actual results
  4. Check for:
     - Missing steps
     - Unexpected failures
     - Timeout issues
     - Incomplete execution
  5. Generate validation report
  
  ## VALIDATION CHECKS
  - All steps executed?
  - Expected assertions passed?
  - Screenshots captured?
  - Execution time within bounds?
  
  ## OUTPUT
  - VALID: Results match expectations
  - INVALID: Specific issues found
  - NEEDS_REVIEW: Ambiguous results

tools:
  - get_execution_status
  - list_testcases
  - load_testcase
  - get_deployment_history

platform: null
requires_device: false
timeout_seconds: 300
```

#### false-positive-detection.yaml

```yaml
name: false-positive-detection
version: 1.0.0
description: |
  Detect false positive test failures.
  Identify flaky tests and environmental issues.

triggers:
  - check false positive
  - analyze failure
  - flaky test

system_prompt: |
  You analyze test failures to detect false positives.
  
  ## FALSE POSITIVE INDICATORS
  1. **Timing issues**
     - Element not found but visible in screenshot
     - Timeout on slow network
     
  2. **Environmental**
     - Device was locked/asleep
     - Network connectivity issue
     - Resource contention
     
  3. **Flaky patterns**
     - Same test passes/fails randomly
     - Failure only on specific device
     - Time-of-day correlation
     
  4. **Test issues**
     - Selector changed (UI update)
     - Incorrect expected value
     - Missing wait/sync
  
  ## ANALYSIS WORKFLOW
  1. Get failure details
  2. Check execution screenshot
  3. Compare with previous runs
  4. Look for patterns
  5. Classify: TRUE_FAILURE or FALSE_POSITIVE
  6. If false positive, identify root cause
  
  ## OUTPUT
  - TRUE_FAILURE: Real bug, needs fix
  - FALSE_POSITIVE: Environmental/flaky, needs investigation
  - INCONCLUSIVE: Need more data

tools:
  - get_execution_status
  - load_testcase
  - get_deployment_history
  - capture_screenshot

platform: null
requires_device: false
timeout_seconds: 300
```

#### report-generation.yaml

```yaml
name: report-generation
version: 1.0.0
description: |
  Generate execution reports and summaries.
  Create human-readable analysis of test runs.

triggers:
  - generate report
  - execution summary
  - test report

system_prompt: |
  You generate reports from execution data.
  
  ## REPORT TYPES
  
  ### Execution Summary
  - Total tests run
  - Pass/fail/skip counts
  - Duration
  - Device coverage
  
  ### Failure Analysis
  - List of failures
  - Grouped by type
  - Root cause indicators
  - Recommendations
  
  ### Trend Report
  - Pass rate over time
  - Flaky test identification
  - Performance trends
  
  ## REPORT FORMAT
  - Clear sections with headers
  - Key metrics highlighted
  - Actionable recommendations
  - Links to detailed logs

tools:
  - get_execution_status
  - list_testcases
  - get_deployment_history
  - get_coverage_summary

platform: null
requires_device: false
timeout_seconds: 300
```

---

## Part 5: Code Changes

### 5.1 New File Structure

```
backend_server/src/agent/
├── __init__.py
├── config.py
├── core/
│   ├── __init__.py
│   ├── manager.py              # Updated: skill loading
│   ├── session.py
│   ├── tool_bridge.py
│   └── message_types.py
├── skills/
│   ├── __init__.py             # Updated: exports
│   ├── skill_schema.py         # NEW: Pydantic model
│   ├── skill_loader.py         # NEW: YAML loader
│   ├── skill_registry.py       # Existing: validates tools
│   └── definitions/            # NEW: Skill YAML files
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
│   ├── __init__.py
│   ├── config_schema.py        # Updated: available_skills field
│   ├── validator.py
│   ├── registry.py
│   └── templates/
│       ├── assistant.yaml      # NEW
│       ├── monitor.yaml        # NEW
│       ├── analyzer.yaml       # NEW
│       └── _deprecated/        # Move old agents here
│           ├── ai-assistant.yaml
│           ├── qa-mobile-manager.yaml
│           ├── qa-web-manager.yaml
│           ├── qa-stb-manager.yaml
│           ├── qa-execution-manager.yaml
│           ├── qa-design-manager.yaml
│           └── monitoring-manager.yaml
└── runtime/
    └── runtime.py              # Existing: event handling
```

### 5.2 Key Code Changes

#### config_schema.py - Add available_skills

```python
class AgentDefinition(BaseModel):
    # ... existing fields ...
    
    available_skills: List[str] = Field(
        default_factory=list,
        description="Skills this agent can load"
    )
    
    # Rename 'skills' to 'tools' for clarity
    tools: List[str] = Field(
        default_factory=list,
        description="Default tools (before skill loads)"
    )
```

#### manager.py - Skill Loading

```python
from ..skills import SkillLoader, SkillDefinition

class QAManagerAgent:
    def __init__(self, ...):
        # ... existing ...
        self._active_skill: Optional[SkillDefinition] = None
        SkillLoader.load_all_skills()
    
    def get_system_prompt(self, context: Dict[str, Any] = None) -> str:
        if self._active_skill:
            return self._build_skill_prompt(self._active_skill, context)
        return self._build_router_prompt(context)
    
    def _build_router_prompt(self, ctx: Dict[str, Any]) -> str:
        available = self.agent_config.get('available_skills', [])
        skill_descriptions = SkillLoader.get_skill_descriptions(available)
        
        return f"""You are {self.agent_config['nickname']}.

## Available Skills
{skill_descriptions}

## Instructions
1. Read the user's request
2. Decide which skill matches best
3. Respond with: LOAD SKILL [skill-name]

If no skill matches, help with what you can."""
    
    def _build_skill_prompt(self, skill: SkillDefinition, ctx: Dict[str, Any]) -> str:
        return f"""You are executing the **{skill.name}** skill.

{skill.system_prompt}

Available tools: {', '.join(skill.tools)}"""
    
    @property
    def tool_names(self) -> List[str]:
        if self._active_skill:
            return self._active_skill.tools
        return self.agent_config.get('tools', [])
```

---

## Part 6: Migration Steps

### Phase 1: Skill Infrastructure (Week 1)

| Step | Task | Owner |
|------|------|-------|
| 1.1 | Create `skills/skill_schema.py` | Dev |
| 1.2 | Create `skills/skill_loader.py` | Dev |
| 1.3 | Create `skills/definitions/` folder | Dev |
| 1.4 | Update `skills/__init__.py` | Dev |
| 1.5 | Write unit tests | Dev |

### Phase 2: Skill Definitions (Week 1-2)

| Step | Task | Owner |
|------|------|-------|
| 2.1 | Create exploration-mobile.yaml | Dev |
| 2.2 | Create exploration-web.yaml | Dev |
| 2.3 | Create exploration-stb.yaml | Dev |
| 2.4 | Create execution.yaml | Dev |
| 2.5 | Create design.yaml | Dev |
| 2.6 | Create monitoring-read.yaml | Dev |
| 2.7 | Create incident-response.yaml | Dev |
| 2.8 | Create health-check.yaml | Dev |
| 2.9 | Create alert-triage.yaml | Dev |
| 2.10 | Create result-validation.yaml | Dev |
| 2.11 | Create false-positive-detection.yaml | Dev |
| 2.12 | Create report-generation.yaml | Dev |

### Phase 3: Agent & Manager Updates (Week 2)

| Step | Task | Owner |
|------|------|-------|
| 3.1 | Update config_schema.py | Dev |
| 3.2 | Update manager.py with skill loading | Dev |
| 3.3 | Create assistant.yaml | Dev |
| 3.4 | Create monitor.yaml | Dev |
| 3.5 | Create analyzer.yaml | Dev |

### Phase 4: Testing & Validation (Week 3)

| Step | Task | Owner |
|------|------|-------|
| 4.1 | Test assistant + all skills | QA |
| 4.2 | Test monitor + event triggers | QA |
| 4.3 | Test analyzer + script completion | QA |
| 4.4 | Update benchmarks | Dev |
| 4.5 | Performance testing | Dev |

### Phase 5: Cleanup & Documentation (Week 3)

| Step | Task | Owner |
|------|------|-------|
| 5.1 | Move old agents to _deprecated/ | Dev |
| 5.2 | Update documentation | Dev |
| 5.3 | Create migration guide | Dev |
| 5.4 | Remove deprecated agents (after 2 weeks) | Dev |

---

## Part 7: Success Criteria

### Functional

- [ ] Assistant loads correct skill based on user message
- [ ] Monitor triggers on events and loads appropriate skill
- [ ] Analyzer processes script completion and validates results
- [ ] All existing workflows still work
- [ ] Skill switching works correctly

### Architecture

- [ ] 3 agents replace 7 agents
- [ ] 12 skills cover all use cases
- [ ] No code duplication between skills
- [ ] Adding new skill = just add YAML file

### Performance

| Metric | Current | Target |
|--------|---------|--------|
| Agents to maintain | 7 | 3 |
| Skill files | 0 | 12 |
| Lines of prompt code | ~500 | ~50 |
| Time to add new workflow | Hours | Minutes |

---

## Part 8: Rollback Plan

1. **Keep deprecated agents** in `_deprecated/` folder for 2 weeks
2. **Feature flag**: `USE_SKILL_SYSTEM=true/false` in config
3. **Quick revert**: Move agents back from `_deprecated/`, set flag to false
4. **Gradual rollout**: Test with assistant first, then monitor, then analyzer

---

## Appendix A: Quick Reference

### Adding a New Skill

1. Create `skills/definitions/my-skill.yaml`
2. Add skill name to agent's `available_skills` list
3. Restart server
4. Test with: "Load skill my-skill"

### Skill YAML Template

```yaml
name: my-skill-name
version: 1.0.0
description: |
  One-line description.

triggers:
  - keyword 1
  - keyword 2

system_prompt: |
  Instructions here.

tools:
  - tool1
  - tool2

platform: null
requires_device: false
timeout_seconds: 1800
```

### Agent → Skills Mapping

| Agent | Skills |
|-------|--------|
| Assistant | exploration-mobile, exploration-web, exploration-stb, execution, design, monitoring-read |
| Monitor | incident-response, health-check, alert-triage |
| Analyzer | result-validation, false-positive-detection, report-generation |