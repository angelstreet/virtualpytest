# RESULT ANALYSIS SYSTEM v2.3

## 🎯 CORE OBJECTIVE
Analyze script/testcase execution results to detect false positives, classify failures, and determine result reliability.

## 🏗️ ARCHITECTURE

### Two Operating Modes

| Mode | Trigger | Processing | Response |
|------|---------|------------|----------|
| **Chat Mode** | User selects analyzer in chat | Immediate (separate thread) | Interactive |
| **Event Mode** | Script/testcase completes | Background queue | Async |

### Flow Diagram
```
┌─────────────────────────────────────────────────────────────────┐
│                         USER CHAT                                │
│  "Analyze this report: http://..."                              │
└────────────────────────────┬────────────────────────────────────┘
                             │ IMMEDIATE (bypasses queue)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ANALYZER (Sherlock)                         │
│                     selectable: true                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ fetch_report    │  │ fetch_logs      │  │ get_queue_status│  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             ▲
                             │ QUEUED (background worker)
┌────────────────────────────┴────────────────────────────────────┐
│                      ANALYSIS QUEUE                              │
│  ┌──────┐ ┌──────┐ ┌──────┐                                     │
│  │task 1│ │task 2│ │task 3│ ← Events from executions            │
│  └──────┘ └──────┘ └──────┘                                     │
└─────────────────────────────────────────────────────────────────┘
                             ▲
                             │ publish event
┌────────────────────────────┴────────────────────────────────────┐
│                        EVENT BUS                                 │
│  ExecutionEvent { script_name, report_url, logs_url, ... }      │
└─────────────────────────────────────────────────────────────────┘
                             ▲
                             │ script completes
┌────────────────────────────┴────────────────────────────────────┐
│                     SCRIPT TOOLS                                 │
│  execute_script() → polls → completion → publish event          │
└─────────────────────────────────────────────────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Event Bus | `agent/core/event_bus.py` | Pub/sub for execution events |
| Analysis Queue | `agent/core/event_bus.py` | Background queue + worker thread |
| ExecutionEvent | `agent/core/event_bus.py` | Event data with URLs |
| Script Hook | `mcp/tools/script_tools.py` | Publishes event on completion |
| Analysis Tools | `mcp/tools/analysis_tools.py` | Fetch & parse reports |
| Analyzer Agent | `agent/registry/templates/analyzer.yaml` | Agent configuration |

## 💬 CHAT MODE

### How to Use
1. Select **Sherlock** (Result Analyzer) in chat
2. Provide a report URL:
   - "Analyze this report: http://host/reports/123/report.html"
   - "Check the last execution for false positives"
   - "Validate the result at http://..."

### Key Points
- **Always responsive** - Chat requests bypass the queue
- **Immediate processing** - No waiting for background tasks
- **Interactive** - Can ask follow-up questions

### Example Chat
```
User: Analyze this report: http://192.168.1.100/reports/exec_123/report.html

Sherlock: 📊 Report Analysis:
- Total steps: 15
- Passed: 12
- Failed: 3

❌ Errors found:
  - Element "login-btn" not found after 10s timeout

Classification: SCRIPT_ISSUE
Confidence: MEDIUM
Recommendation: REVIEW - Selector may need updating
```

## ⚡ EVENT MODE

### How It Works
1. Script/testcase completes
2. `script_tools` publishes `ExecutionEvent` to event bus
3. Event is queued in `AnalysisQueue`
4. Background worker processes queue (FIFO)
5. Results stored for retrieval

### Key Points
- **Non-blocking** - Doesn't slow down script execution
- **Ordered processing** - Queue ensures FIFO order
- **Doesn't block chat** - Separate thread from chat requests

### Queue Status Tool
```
User: What's in the analysis queue?

Sherlock: 📊 Analysis Queue Status:
- Pending tasks: 2
- Currently processing: Yes
- Current task: validation.py
- Worker running: Yes
- Completed analyses: 15

💡 Note: Chat requests bypass the queue and are processed immediately.
```

## 🔧 TOOLS

| Tool | Description |
|------|-------------|
| `fetch_execution_report` | Curl & parse HTML report from URL |
| `fetch_execution_logs` | Curl logs file (50KB limit) |
| `get_last_execution_event` | Get most recent execution context |
| `get_execution_status` | Get status by task ID |
| `get_analysis_queue_status` | Check background queue status |

## 📊 ExecutionEvent Data

```python
@dataclass
class ExecutionEvent:
    trigger_type: TriggerType       # SCRIPT_COMPLETED | TESTCASE_COMPLETED
    execution_id: str               # Task ID
    script_name: str                # Script filename
    success: bool                   # Pass/fail
    exit_code: int                  # Process exit code
    execution_time_ms: int          # Duration in ms
    report_url: str                 # Full URL to HTML report
    logs_url: str                   # Full URL to logs file
    host_name: str                  # Host where executed
    device_id: str                  # Device identifier
    timestamp: datetime
```

## 🔍 VALIDATION RULES

### RELIABLE if:
- Initial state OK (no black screen, no signal issues)
- Final state OK (no errors, device responsive)
- For PASS: Result coherent with test goal

### UNRELIABLE if:
- Any validation check fails
- Missing critical data

## 🎯 FAILURE CLASSIFICATION

| Classification | Rule | Confidence |
|---------------|------|------------|
| **BUG** | Element visible but "not found" error | HIGH |
| **SCRIPT_ISSUE** | Selector/timing/expectation error | MEDIUM |
| **SYSTEM_ISSUE** | Black screen/no signal/disconnect | HIGH |
| **UNKNOWN** | Unclear or conflicting evidence | LOW |

## 🛠️ CONFIGURATIONS

### analyzer.yaml (v2.3.0)
```yaml
metadata:
  id: analyzer
  name: Result Analyzer
  nickname: Sherlock
  selectable: true  # Users CAN select in chat
  version: 2.3.0

triggers:
  - type: chat.message
    priority: high  # Chat always takes priority
  - type: script.completed
    priority: normal  # Queued for background
  - type: testcase.completed
    priority: normal

suggestions:
  - "Analyze this report: http://..."
  - "Check the last execution for false positives"
  - "Validate the result at http://..."
  - "What's in the analysis queue?"

skills:
  - get_execution_status
  - get_last_execution_event
  - fetch_execution_report
  - fetch_execution_logs
  - get_analysis_queue_status
```

### AnalysisQueue
```python
class AnalysisQueue:
    """
    Background queue for event-triggered analysis.
    
    - Event bus → Queue (non-blocking)
    - Background worker processes queue
    - Chat requests bypass queue (immediate response)
    """
    
    def enqueue(event) → str           # Add to queue
    def get_status() → Dict            # Queue status
    def get_result(execution_id) → Dict # Get analysis result
```

## 🎯 KEY BENEFITS

✅ **Chat always responsive** - Never blocked by background tasks
✅ **Event-triggered analysis** - Automatic after execution
✅ **Queue-based** - Ordered, non-blocking background processing
✅ **URL-based** - Works across hosts via HTTP
✅ **Self-contained** - Uses only report/logs data
✅ **Selectable** - Users can chat with analyzer directly

## 📁 FILES

| File | Purpose |
|------|---------|
| `agent/core/event_bus.py` | Event bus + AnalysisQueue |
| `mcp/tools/analysis_tools.py` | Report/logs fetching + queue status |
| `mcp/tools/script_tools.py` | Publishes events on completion |
| `mcp/tool_definitions/analysis_definitions.py` | Tool schemas |
| `agent/skills/definitions/validate.yaml` | Validation skill |
| `agent/skills/definitions/analyze.yaml` | Analysis skill |
| `agent/registry/templates/analyzer.yaml` | Agent config |

## 🧪 TESTING

### Chat Mode
1. Select Sherlock in chat
2. Ask: "Analyze this report: http://..."
3. Verify immediate response

### Event Mode
1. Execute a script via assistant
2. Check queue status: "What's in the analysis queue?"
3. Verify event was queued
4. Verify background processing

### Concurrent Test
1. Start a script execution (queues analysis)
2. Immediately ask Sherlock to analyze different report
3. Verify chat response is immediate (not blocked)
