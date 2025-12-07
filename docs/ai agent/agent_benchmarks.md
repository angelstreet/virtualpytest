# Agent Benchmarking System

## Overview

The Agent Benchmarking System evaluates AI agents through standardized tests, user feedback, and execution metrics to produce comparable scores across agents.

**Test definitions are file-based (YAML)** for easy editing and version control.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BENCHMARK EVALUATION FLOW                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │  YAML Tests  │───▶│   Execute    │───▶│   Record     │          │
│   │  (files)     │    │   Agent      │    │   Results    │          │
│   └──────────────┘    └──────────────┘    └──────────────┘          │
│          │                                       │                   │
│          ▼                                       ▼                   │
│   ┌──────────────┐                       ┌──────────────┐           │
│   │    User      │                       │   Calculate  │           │
│   │   Feedback   │──────────────────────▶│    Score     │           │
│   └──────────────┘                       └──────────────┘           │
│                                                 │                    │
│                                                 ▼                    │
│                                          ┌──────────────┐           │
│                                          │  Leaderboard │           │
│                                          └──────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### File-Based Test Definitions

```
backend_server/src/agent/benchmarks/
├── __init__.py              # YAML loader
├── tests/                   # Built-in tests
│   ├── navigation.yaml
│   ├── detection.yaml
│   ├── execution.yaml
│   ├── analysis.yaml
│   └── recovery.yaml
└── custom/                  # Your custom tests
    └── my_tests.yaml
```

### Database (Runtime Data Only)

```
agent_benchmark_runs      # Execution tracking
       │
       ▼
agent_benchmark_results   # Individual test results
       │
       ▼
agent_scores              # Aggregated scores (leaderboard)
       │
       ▼
agent_feedback            # User ratings (1-5 stars)
```

---

## Benchmark Categories

| Category | Description | Test Examples |
|----------|-------------|---------------|
| `navigation` | UI navigation capabilities | List interfaces, navigate to node |
| `detection` | System monitoring & detection | Device status, health checks |
| `execution` | Test case execution | List/load/run test cases |
| `analysis` | Coverage and requirement analysis | Coverage summary, requirements |
| `recovery` | Error handling & recovery | Invalid input, timeout handling |

---

## Default Benchmark Tests

Built-in tests are defined in `backend_server/src/agent/benchmarks/tests/`:

| File | Category | Tests |
|------|----------|-------|
| `navigation.yaml` | Navigation | List interfaces, Navigate to node, Get tree |
| `detection.yaml` | Detection | Device status, Health check, Host discovery |
| `execution.yaml` | Execution | List/Load/Execute test cases, Get results |
| `analysis.yaml` | Analysis | Coverage summary, Requirements, Gap analysis |
| `recovery.yaml` | Recovery | Invalid input, Timeout, Missing resource |

### Example: navigation.yaml

```yaml
category: navigation
description: UI navigation capabilities

tests:
  - id: bench_nav_001
    name: List User Interfaces
    prompt: "List all available user interfaces in the system"
    expected:
      contains: ["userinterface", "list"]
    validation: contains
    timeout: 30
    points: 1.0
    agents:
      - qa-web-manager
      - qa-mobile-manager
      - qa-stb-manager
      - ai-assistant
```

---

## Scoring System

### Overall Score Calculation

```
┌─────────────────────────────────────────────────────────────┐
│           OVERALL_SCORE = Weighted Average                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐                                       │
│   │ Benchmark Score │ × 40%                                 │
│   │  (0-100%)       │                                       │
│   └─────────────────┘                                       │
│          +                                                  │
│   ┌─────────────────┐                                       │
│   │ User Rating     │ × 30%   (1-5 stars → 0-100%)         │
│   │  Score          │                                       │
│   └─────────────────┘                                       │
│          +                                                  │
│   ┌─────────────────┐                                       │
│   │ Success Rate    │ × 20%   (from execution history)     │
│   │  Score          │                                       │
│   └─────────────────┘                                       │
│          +                                                  │
│   ┌─────────────────┐                                       │
│   │ Cost Efficiency │ × 10%   (TBD)                        │
│   │  Score          │                                       │
│   └─────────────────┘                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Scores

| Component | Weight | Source | Calculation |
|-----------|--------|--------|-------------|
| Benchmark | 40% | `agent_benchmark_runs` | (passed / total) × 100 |
| User Rating | 30% | `agent_feedback` | (avg_rating - 1) × 25 |
| Success Rate | 20% | `agent_execution_history` | (successful / total) × 100 |
| Cost Efficiency | 10% | TBD | tokens/complexity ratio |

---

## API Reference

### Base URL
```
/api/benchmarks
```

### Endpoints

#### List Benchmark Tests
```http
GET /api/benchmarks/tests?category=navigation
```

**Response:**
```json
{
  "tests": [
    {
      "test_id": "bench_nav_001",
      "name": "List User Interfaces",
      "category": "navigation",
      "input_prompt": "List all available user interfaces in the system",
      "expected_output": {"contains": ["userinterface", "list"]},
      "validation_type": "contains",
      "timeout_seconds": 30,
      "points": 1.0,
      "applicable_agent_types": ["qa-web-manager", "qa-mobile-manager"]
    }
  ],
  "count": 17
}
```

---

#### Create Benchmark Run
```http
POST /api/benchmarks/run?team_id=<team_id>
Content-Type: application/json

{
  "agent_id": "qa-web-manager",
  "version": "1.0.0"
}
```

**Response:**
```json
{
  "run_id": "5e06f7d4-f474-4fa8-a834-b447442a7da2",
  "agent_id": "qa-web-manager",
  "version": "1.0.0",
  "total_tests": 10,
  "status": "pending",
  "message": "Benchmark run created. Execute /api/benchmarks/run/{run_id}/execute to start."
}
```

---

#### Execute Benchmark Run
```http
POST /api/benchmarks/run/{run_id}/execute?team_id=<team_id>
```

**Response:**
```json
{
  "run_id": "5e06f7d4-f474-4fa8-a834-b447442a7da2",
  "status": "completed",
  "passed": 10,
  "failed": 0,
  "score_percent": 100.0
}
```

---

#### List Benchmark Runs
```http
GET /api/benchmarks/runs?team_id=<team_id>&agent_id=qa-web-manager&limit=20
```

**Response:**
```json
{
  "runs": [
    {
      "id": "uuid",
      "agent_id": "qa-web-manager",
      "agent_version": "1.0.0",
      "status": "completed",
      "total_tests": 10,
      "passed_tests": 10,
      "failed_tests": 0,
      "score_percent": 100.0,
      "started_at": "2025-12-06T23:58:10Z",
      "completed_at": "2025-12-06T23:58:12Z"
    }
  ],
  "count": 1
}
```

---

#### Get Run Details
```http
GET /api/benchmarks/runs/{run_id}
```

**Response:**
```json
{
  "run": { ... },
  "results": [
    {
      "test_id": "bench_nav_001",
      "passed": true,
      "points_earned": 1.0,
      "duration_seconds": 1.5
    }
  ]
}
```

---

#### Submit User Feedback
```http
POST /api/benchmarks/feedback?team_id=<team_id>
Content-Type: application/json

{
  "agent_id": "qa-web-manager",
  "version": "1.0.0",
  "rating": 5,
  "comment": "Excellent navigation capabilities",
  "task_description": "Navigate to settings"
}
```

**Response:**
```json
{
  "feedback_id": "uuid",
  "message": "Feedback submitted successfully"
}
```

---

#### Get Leaderboard
```http
GET /api/benchmarks/leaderboard?team_id=<team_id>&limit=20
```

**Response:**
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "agent_id": "qa-web-manager",
      "agent_version": "1.0.0",
      "overall_score": 85.5,
      "benchmark_score": 100.0,
      "user_rating_score": 75.0,
      "success_rate_score": 80.0,
      "avg_user_rating": 4.0
    }
  ],
  "count": 1
}
```

---

#### Compare Agents
```http
GET /api/benchmarks/compare?agents=qa-web-manager:1.0.0,qa-mobile-manager:1.0.0&team_id=<team_id>
```

**Response:**
```json
{
  "comparison": [
    {"agent_id": "qa-web-manager", "overall_score": 85.5},
    {"agent_id": "qa-mobile-manager", "overall_score": 78.2}
  ],
  "winner": "qa-web-manager"
}
```

---

## Usage Examples

### Run a Benchmark (CLI)

```bash
# Step 1: Create benchmark run
RUN_ID=$(curl -s -X POST "http://localhost:5109/api/benchmarks/run?team_id=YOUR_TEAM_ID" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "qa-web-manager", "version": "1.0.0"}' \
  | jq -r '.run_id')

echo "Created run: $RUN_ID"

# Step 2: Execute benchmark
curl -X POST "http://localhost:5109/api/benchmarks/run/$RUN_ID/execute?team_id=YOUR_TEAM_ID"

# Step 3: Check results
curl "http://localhost:5109/api/benchmarks/runs/$RUN_ID"
```

### Run a Benchmark (Frontend)

1. Navigate to **Agent Dashboard** (`/agent-dashboard`)
2. Select **Agents** tab
3. Click the ⚡ **Benchmark** icon on any agent card
4. View results in the **Benchmarks** tab

### Submit Feedback (Frontend)

1. Navigate to **Agent Dashboard**
2. Click the ⭐ **Rate** icon on any agent card
3. Select 1-5 star rating
4. Add optional comment
5. Submit

---

## Database Schema Details

> **Note**: Test definitions are now in YAML files, not in the database.
> Only runtime/execution data is stored in the database.

### agent_benchmark_runs (Execution Tracking)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `agent_id` | VARCHAR(100) | Agent being tested |
| `agent_version` | VARCHAR(20) | Version tested |
| `status` | VARCHAR(20) | pending/running/completed/failed |
| `total_tests` | INTEGER | Total tests to run |
| `completed_tests` | INTEGER | Tests completed |
| `passed_tests` | INTEGER | Tests passed |
| `failed_tests` | INTEGER | Tests failed |
| `score_percent` | DECIMAL | Final score 0-100 |
| `team_id` | VARCHAR(100) | Team identifier |

### agent_benchmark_results (Individual Results)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `run_id` | UUID | Parent benchmark run |
| `benchmark_id` | UUID | Optional (null for file-based tests) |
| `test_id` | VARCHAR(50) | Test identifier from YAML |
| `passed` | BOOLEAN | Pass/fail status |
| `points_earned` | DECIMAL | Points scored |
| `actual_output` | JSONB | Agent's response |
| `failure_reason` | TEXT | Why test failed |
| `duration_seconds` | DECIMAL | Execution time |

### agent_scores (Aggregated Scores)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `agent_id` | VARCHAR(100) | Agent identifier |
| `agent_version` | VARCHAR(20) | Version |
| `benchmark_score` | DECIMAL | 0-100 from tests |
| `user_rating_score` | DECIMAL | 0-100 from feedback |
| `success_rate_score` | DECIMAL | 0-100 from history |
| `overall_score` | DECIMAL | Weighted composite |
| `rank_overall` | INTEGER | Leaderboard position |
| `team_id` | VARCHAR(100) | Team identifier |

### agent_feedback (User Ratings)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `agent_id` | VARCHAR(100) | Agent identifier |
| `agent_version` | VARCHAR(20) | Version |
| `rating` | INTEGER | 1-5 stars |
| `comment` | TEXT | Optional feedback text |
| `execution_id` | UUID | Task reference |
| `team_id` | VARCHAR(100) | Team identifier |

---

## Adding Custom Benchmark Tests

### Step 1: Create a YAML File

Create a new file in `backend_server/src/agent/benchmarks/custom/`:

```yaml
# backend_server/src/agent/benchmarks/custom/my_tests.yaml

category: custom
description: My custom benchmark tests

tests:
  - id: bench_custom_001
    name: Custom Test Name
    description: Description of what this test validates
    prompt: "The prompt given to the agent"
    expected:
      contains: ["expected", "keywords"]
    validation: contains
    timeout: 60
    points: 1.0
    agents:
      - qa-web-manager
      - qa-mobile-manager

  - id: bench_custom_002
    name: Another Custom Test
    description: Tests another capability
    prompt: "Another prompt for the agent"
    expected:
      contains: ["response", "keywords"]
    validation: contains
    timeout: 30
    points: 1.5
    agents:
      - ai-assistant
```

### Step 2: Restart Server

Tests are loaded at server startup. Restart to pick up new tests.

### Step 3: Verify

```bash
curl http://localhost:5109/api/benchmarks/tests
# Should show your new tests
```

---

### YAML Test Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique test ID (e.g., `bench_custom_001`) |
| `name` | string | ✅ | Human-readable name |
| `description` | string | | What the test validates |
| `prompt` | string | ✅ | Prompt given to the agent |
| `expected` | object | ✅ | Expected output pattern |
| `validation` | string | | Validation type (default: `contains`) |
| `timeout` | int | | Max seconds (default: 30) |
| `points` | float | | Points if passed (default: 1.0) |
| `agents` | list | | Applicable agent IDs (null = all) |
| `active` | bool | | Is test active (default: true) |

### Validation Types

| Type | Description | Expected Format |
|------|-------------|-----------------|
| `exact` | Exact match required | `{value: "exact string"}` |
| `contains` | Output must contain ALL keywords | `{contains: ["keyword1", "keyword2"]}` |
| `contains_any` | Output must contain ANY keyword | `{contains: ["error", "not found"]}` |
| `regex` | Regex pattern match | `{pattern: "regex.*pattern"}` |

---

## Triggering Score Recalculation

The `recalculate_agent_score` database function updates aggregate scores:

```sql
SELECT recalculate_agent_score(
    'qa-web-manager',  -- agent_id
    '1.0.0',           -- version
    'your-team-id'     -- team_id
);
```

This recalculates:
- Latest benchmark score
- Average user rating
- Success rate from execution history
- Overall weighted score

---

## Frontend Integration

### AgentDashboard Component

The dashboard provides three tabs:

1. **Agents Tab** - Agent cards with benchmark/rate actions
2. **Benchmarks Tab** - Benchmark run history table
3. **Leaderboard Tab** - Ranked agent comparison

### Key State Variables

```typescript
const [benchmarkRuns, setBenchmarkRuns] = useState<BenchmarkRun[]>([]);
const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
const [runningBenchmark, setRunningBenchmark] = useState(false);
```

### Triggering Benchmarks

```typescript
const handleRunBenchmark = async (agentId: string, version: string) => {
  // 1. Create run
  const createResponse = await fetch(buildServerUrl('/api/benchmarks/run'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: agentId, version })
  });
  const { run_id } = await createResponse.json();
  
  // 2. Execute
  const executeResponse = await fetch(
    buildServerUrl(`/api/benchmarks/run/${run_id}/execute`),
    { method: 'POST' }
  );
  
  // 3. Refresh list
  await loadBenchmarkRuns();
};
```

---

## Important Notes

### Team ID Requirement

All benchmark operations are **team-scoped**. The frontend automatically appends `team_id` via `buildServerUrl()`:

```typescript
// Frontend sends team_id from APP_CONFIG.DEFAULT_TEAM_ID
const response = await fetch(buildServerUrl('/api/benchmarks/runs'));
// URL becomes: /api/benchmarks/runs?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce
```

### Current Limitations

1. **Test Execution**: Uses placeholder simulation; real agent execution requires `QAManagerAgent` integration
2. **Cost Efficiency**: The 10% cost efficiency component is not yet implemented
3. **Hot Reload**: Server restart required after adding/editing YAML tests

