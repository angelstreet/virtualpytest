# Agent Benchmarking System

## Overview

The Agent Benchmarking System evaluates AI agents through a **3-tier pyramid strategy** to quickly identify broken agents and validate production readiness.

```
                    ┌─────────────┐
                    │   TIER 3    │  ← "Is agent PRODUCTION READY?"
                    │   E2E (3)   │     Full scenario: ~5 mins
                    └──────┬──────┘
                           │
                ┌──────────┴──────────┐
                │      TIER 2         │  ← "Can agent DO tasks?"
                │  SKILLS (5 tests)   │     Per-skill: ~3 mins
                └──────────┬──────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │              TIER 1                  │  ← "Is agent BROKEN?"
        │      TOOL SELECTION (10 tests)       │     Quick check: ~1 min
        └──────────────────────────────────────┘
```

---

## Quick Status Check

| Status | Tier 1 | Tier 2 | Tier 3 | Meaning |
|--------|--------|--------|--------|---------|
| 🟢 **HEALTHY** | ✅ 100% | ✅ 80%+ | ✅ Pass | Production ready |
| 🟡 **DEGRADED** | ✅ 100% | ⚠️ 50-80% | ❌ Fail | Some skills broken |
| 🔴 **BROKEN** | ❌ <100% | - | - | Agent can't select tools |

---

## Benchmark Files

```
backend_server/src/agent/benchmarks/
├── __init__.py
├── tests/
│   ├── tier1_tool_selection.yaml   # 10 tests - Quick health check
│   ├── tier2_skill_workflows.yaml  # 5 tests - Capability validation
│   ├── tier3_e2e_integration.yaml  # 3 tests - Full sauce-demo flow
│   ├── navigation.yaml             # Basic navigation
│   ├── detection.yaml              # Device detection
│   ├── execution.yaml              # Test execution
│   ├── analysis.yaml               # Coverage analysis
│   └── recovery.yaml               # Error handling
└── custom/
    └── exploration.yaml            # Autonomous exploration benchmarks
```

---

## Tier 1: Tool Selection (Quick Health Check)

**Purpose**: Verify agent selects the RIGHT tool for each task  
**Time**: ~1 minute (10 tests × 5s)  
**Pass Criteria**: 100% = Agent is NOT broken

| Test ID | Tool | Prompt |
|---------|------|--------|
| `ts_001` | `list_userinterfaces` | "List all userinterfaces" |
| `ts_002` | `get_device_info` | "Get device info for my device" |
| `ts_003` | `get_compatible_hosts` | "What hosts are compatible?" |
| `ts_004` | `list_navigation_nodes` | "List all navigation nodes" |
| `ts_005` | `dump_ui_elements` | "Dump all UI elements" |
| `ts_006` | `list_requirements` | "List all requirements" |
| `ts_007` | `list_testcases` | "List all test cases" |
| `ts_008` | `get_coverage_summary` | "What is the test coverage?" |
| `ts_009` | `take_control` | "Take control of the device" |
| `ts_010` | `execute_testcase` | "Run test case TC_001" |

---

## Tier 2: Skill Workflows (Capability Check)

**Purpose**: Verify agent completes multi-step skill workflows  
**Time**: ~3 minutes (5 tests × 30s)  
**Pass Criteria**: 80%+ = Agent skills are FUNCTIONAL

| Test ID | Skill | Description |
|---------|-------|-------------|
| `sw_001` | **EXPLORE** | Analyze screen, identify interactive elements |
| `sw_002` | **BUILD** (Req) | Create requirement with acceptance criteria |
| `sw_003` | **BUILD** (TC) | Create test case with steps |
| `sw_004` | **EXECUTE** | Execute test and report results |
| `sw_005` | **NAVIGATE** | Create node and edge in navigation tree |

---

## Tier 3: E2E Integration (Full Validation)

**Purpose**: Verify agent completes the sauce-demo gold standard  
**Time**: ~5 minutes  
**Pass Criteria**: Pass = Agent is PRODUCTION READY

| Test ID | Name | Description |
|---------|------|-------------|
| `e2e_001` | **Sauce Demo Full Automation** | Complete workflow: hosts → exploration → validate → requirement → testcase → coverage |
| `e2e_002` | **Navigation Tree Validation** | Verify tree has: home, login, signup, cart nodes |
| `e2e_003` | **Coverage Validation** | Verify 100% coverage for created requirements |

### Sauce Demo Expected Deliverables

- **7 nodes**: home, signup, login, logout, product_detail, cart, search_results
- **6 requirements**: signup, login, logout, search, add to cart, verify cart
- **6 test cases**: linked to requirements
- **100% coverage**: all requirements covered

---

## Autonomous Exploration Benchmarks

Custom benchmarks for testing autonomous navigation tree building.

**Location:** `benchmarks/custom/exploration.yaml`

| Test ID | Name | Points | Description |
|---------|------|--------|-------------|
| `mobile_explore_001` | Basic Exploration | 10 | Creates nodes + edges |
| `mobile_explore_002` | With Edge Testing | 10 | Tests all edges bidirectionally |
| `mobile_explore_003` | Optimal Selectors | 10 | Uses IDs over text |
| `mobile_explore_004` | Add Verifications | 12 | Adds node detection |
| `mobile_explore_005` | Full Autonomous | 25 | Everything + screenshots |
| `mobile_explore_006` | Reference Model Match | 30 | Matches expected structure |
| `mobile_explore_007` | Fix Failed Edges | 15 | Error recovery |
| `mobile_explore_008` | Simple Natural Prompt | 8 | Understands human prompts |

### Reference Model (mobile_explore_006)

```yaml
expected:
  reference_model:
    userinterface: google_tv
    platform: android_mobile
    expected_nodes:
      - label: home
        has_verification: true
      - label: search
        has_verification: true
      - label: library
        has_verification: true
      - label: settings
        has_verification: true
    expected_edges:
      - source: home
        target: search
        bidirectional: true
      - source: home
        target: library
        bidirectional: true
      - source: home
        target: settings
        bidirectional: true
    min_match_percentage: 75
```

---

## Scoring System

### Overall Score Calculation

```
┌─────────────────────────────────────────────────────────┐
│   OVERALL_SCORE = Weighted Average                       │
├─────────────────────────────────────────────────────────┤
│   Benchmark Score  × 40%   (from tier tests)            │
│   User Rating      × 30%   (1-5 stars → 0-100%)         │
│   Success Rate     × 20%   (from execution history)     │
│   Cost Efficiency  × 10%   (TBD)                        │
└─────────────────────────────────────────────────────────┘
```

### Version Comparison

```
┌─────────────────────────────────────────────────────────┐
│ Agent: Sherlock (qa-web-manager)                        │
├─────────────────────────────────────────────────────────┤
│ Version │ Tier 1 │ Tier 2 │ Tier 3 │ Overall │ Status  │
├─────────┼────────┼────────┼────────┼─────────┼─────────┤
│ v1.0.0  │ 100%   │ 60%    │ ❌      │ 72%     │ 🟡      │
│ v1.1.0  │ 100%   │ 80%    │ ✅      │ 88%     │ 🟢      │
│ v1.2.0  │ 90%    │ 40%    │ ❌      │ 58%     │ 🔴 REGR │
└─────────────────────────────────────────────────────────┘
```

---

## API Reference

### Run Benchmarks

```bash
# Quick health check (Tier 1 only)
curl -X POST "http://localhost:5109/server/benchmarks/run?team_id=<team_id>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "qa-mobile-manager", "version": "1.0.0", "category": "tool_selection"}'

# Full benchmark (all tiers)
curl -X POST "http://localhost:5109/server/benchmarks/run?team_id=<team_id>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "qa-mobile-manager", "version": "1.0.0"}'

# Run exploration benchmarks
curl -X POST "http://localhost:5109/server/benchmarks/run?team_id=<team_id>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "qa-mobile-manager", "version": "1.0.0", "category": "exploration_mobile"}'

# Execute the run
curl -X POST "http://localhost:5109/server/benchmarks/run/<run_id>/execute?team_id=<team_id>"
```

### Get Results

```bash
# List runs
GET /server/benchmarks/runs?team_id=<team_id>&agent_id=qa-mobile-manager

# Get run details
GET /server/benchmarks/runs/<run_id>

# Get leaderboard
GET /server/benchmarks/leaderboard?team_id=<team_id>

# Compare agents
GET /server/benchmarks/compare?agents=qa-web-manager:1.0.0,qa-mobile-manager:1.0.0
```

### Submit Feedback

```bash
POST /server/benchmarks/feedback?team_id=<team_id>
Content-Type: application/json

{
  "agent_id": "qa-mobile-manager",
  "version": "1.0.0",
  "rating": 5,
  "comment": "Excellent autonomous exploration"
}
```

---

## YAML Test Schema

```yaml
category: exploration_mobile
description: Autonomous mobile exploration benchmarks

tests:
  - id: mobile_explore_001       # Unique test ID
    name: Basic Mobile Exploration
    description: Agent explores and creates navigation structure
    prompt: "Explore google_tv and map all screens reachable from home."
    expected:
      contains: ["node", "edge", "created"]
      tools_called:
        - get_compatible_hosts
        - dump_ui_elements
        - create_node
        - create_edge
        - get_edge
        - execute_device_action
      min_nodes: 3
      min_edges: 2
    validation: exploration_result
    timeout: 300
    points: 10.0
    agents:
      - qa-mobile-manager
```

### Validation Types

| Type | Description | Expected Format |
|------|-------------|-----------------|
| `contains` | Output must contain ALL keywords | `{contains: ["keyword1", "keyword2"]}` |
| `contains_any` | Output must contain ANY keyword | `{contains: ["error", "not found"]}` |
| `exact` | Exact match required | `{value: "exact string"}` |
| `regex` | Regex pattern match | `{pattern: "regex.*pattern"}` |
| `exploration_result` | Validates exploration output | `{min_nodes, min_edges, tools_called}` |
| `reference_model` | Compares to expected structure | `{reference_model: {...}}` |
| `selector_analysis` | Checks selector quality | `{selector_quality: {...}}` |

---

## Adding Custom Benchmarks

### Step 1: Create YAML File

```yaml
# backend_server/src/agent/benchmarks/custom/my_tests.yaml

category: custom
description: My custom benchmark tests

tests:
  - id: bench_custom_001
    name: Custom Test Name
    prompt: "Your test prompt here"
    expected:
      contains: ["expected", "keywords"]
    validation: contains
    timeout: 60
    points: 1.0
    agents:
      - qa-mobile-manager
```

### Step 2: Restart Server

Tests are loaded at server startup.

### Step 3: Verify

```bash
curl http://localhost:5109/server/benchmarks/tests?category=custom
```

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `agent_benchmark_runs` | Execution tracking (status, scores) |
| `agent_benchmark_results` | Individual test results |
| `agent_scores` | Aggregated scores for leaderboard |
| `agent_feedback` | User ratings (1-5 stars) |

---

## Best Practices

### When to Run Each Tier

| Scenario | Run |
|----------|-----|
| Quick sanity check | Tier 1 only |
| After code changes | Tier 1 + Tier 2 |
| Before release | All tiers |
| CI/CD pipeline | Tier 1 (fast), Tier 3 (nightly) |
| Testing exploration | `exploration_mobile` category |

### Regression Detection

1. Run same tests across versions
2. Compare scores: drop = regression
3. Investigate failing tests
4. Fix and re-run

### Adding Tests for New Skills

When adding a new MCP tool:
1. Add Tier 1 test (tool selection)
2. Add Tier 2 test if it's part of a workflow
3. Update Tier 3 if it's critical to E2E flow

---

## Limitations

1. **Test Execution**: Currently uses simulation; real execution requires live agent
2. **Cost Efficiency**: 10% score component not yet implemented
3. **Hot Reload**: Server restart required after adding/editing YAML tests

---

*Document Version: 2.0*  
*Last Updated: December 2024*  
*Changelog: Added autonomous exploration benchmarks, updated test categories*
