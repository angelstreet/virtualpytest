# AI Agent System Documentation

VirtualPyTest AI Agent is a multi-agent architecture for automated QA testing, powered by Claude.

---

## Overview

The AI Agent system uses a **QA Manager** orchestrator that delegates tasks to **5 specialist agents**, each with specific skills and tools.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              QA MANAGER                                      │
│                         (Orchestrator - No Tools)                           │
│                                                                             │
│  • Understands user requests                                                │
│  • Detects operating mode                                                   │
│  • Delegates to specialist agents                                           │
│  • Handles approvals                                                        │
│  • Reports results                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
       ┌──────────┬─────────┬───────┴───────┬──────────┬──────────┐
       ▼          ▼         ▼               ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ EXPLORER │ │ BUILDER  │ │ EXECUTOR │ │ ANALYST  │ │MAINTAINER│
│          │ │          │ │          │ │          │ │          │
│ Discovery│ │ Tests &  │ │ Strategy │ │ Analysis │ │ Fix &    │
│ & Trees  │ │ Reqs     │ │ & Run    │ │ & Triage │ │ Heal     │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

## Operating Modes

| Mode | Keywords | Agents Used | Description |
|------|----------|-------------|-------------|
| **CREATE** | "automate", "create", "build" | Explorer → Builder | Build navigation tree + create tests |
| **VALIDATE** | "run", "test", "regression" | Executor → Analyst | Run tests + analyze results |
| **ANALYZE** | "analyze", "why did", "investigate" | Analyst | Review existing results |
| **MAINTAIN** | "fix", "repair", "broken" | Maintainer | Fix broken selectors |

---

## Agent Responsibilities

### QA Manager (Orchestrator)
- **Role**: Senior QA Lead
- **Tools**: None (delegates only)
- **Skills**: Intent parsing, mode detection, delegation, human communication

### Explorer Agent
- **Role**: UI Discovery Specialist
- **Focus**: Discover UI elements, build navigation trees
- **Key Tools**: `start_ai_exploration`, `approve_exploration_plan`, `validate_exploration_edges`, `dump_ui_elements`

### Builder Agent
- **Role**: Test Case Creator
- **Focus**: Create requirements, generate test cases, ensure coverage
- **Key Tools**: `create_requirement`, `save_testcase`, `generate_and_save_testcase`, `link_testcase_to_requirement`

### Executor Agent
- **Role**: Execution Strategist
- **Focus**: HOW to run tests efficiently (devices, parallelization, retries)
- **Key Tools**: `take_control`, `execute_testcase`, `execute_edge`, `capture_screenshot`

### Analyst Agent
- **Role**: Result Analyst
- **Focus**: WHAT results mean (bug vs UI change, Jira lookup, root cause)
- **Key Tools**: `get_coverage_summary`, `list_verifications`, `verify_node`

### Maintainer Agent
- **Role**: Self-Healing Specialist
- **Focus**: Fix broken selectors, update edges
- **Key Tools**: `update_edge`, `analyze_screen_for_action`, `execute_edge`

---

## Backend Architecture

### File Structure

```
backend_server/src/
├── routes/
│   └── server_agent_routes.py     # REST + SocketIO handlers
│
└── agent/                         # Agent system
    ├── __init__.py
    ├── config.py                  # Configuration & mode definitions
    │
    ├── agents/                    # Agent definitions
    │   ├── __init__.py
    │   ├── base_agent.py          # Base class with tool execution loop
    │   ├── explorer.py            # Explorer Agent
    │   ├── builder.py             # Builder Agent
    │   ├── executor.py            # Executor Agent
    │   ├── analyst.py             # Analyst Agent
    │   └── maintainer.py          # Maintainer Agent
    │
    ├── skills/                    # Tool mappings per agent
    │   ├── __init__.py
    │   ├── explorer_skills.py
    │   ├── builder_skills.py
    │   ├── executor_skills.py
    │   ├── analyst_skills.py
    │   └── maintainer_skills.py
    │
    └── core/                      # Core components
        ├── __init__.py
        ├── manager.py             # QA Manager orchestrator
        ├── session.py             # Chat session management
        ├── message_types.py       # Event types for streaming
        └── tool_bridge.py         # MCP ↔ Agent bridge
```

### Key Components

#### Routes (`routes/server_agent_routes.py`)

Follows standard routes architecture with:
- Blueprint: `server_agent_bp` (prefix: `/server/agent`)
- SocketIO namespace: `/agent`

#### Tool Bridge (`agent/core/tool_bridge.py`)
Connects Claude Agent SDK to existing MCP tools:

```python
class ToolBridge:
    def __init__(self):
        self.mcp_server = VirtualPyTestMCPServer()
    
    def get_tool_definitions(self, tool_names: list) -> list:
        # Returns tools in Claude format
        
    def execute(self, tool_name: str, params: dict) -> dict:
        # Executes MCP tool
```

#### Base Agent (`agent/agents/base_agent.py`)
Common functionality for all specialist agents:

```python
class BaseAgent:
    @property
    def name(self) -> str: ...
    @property
    def system_prompt(self) -> str: ...
    @property
    def tool_names(self) -> List[str]: ...
    
    async def run(self, task: str, context: dict) -> AsyncGenerator:
        # Agent loop: Claude → tool calls → results → repeat
```

#### QA Manager (`agent/core/manager.py`)
Orchestrates the entire system:

```python
class QAManagerAgent:
    def detect_mode(self, message: str) -> str:
        # CREATE, VALIDATE, ANALYZE, MAINTAIN
    
    async def process_message(self, message: str, session: Session):
        # 1. Detect mode
        # 2. Delegate to agents in order
        # 3. Stream events to frontend
```

### API Endpoints

#### REST Endpoints (prefix: `/server/agent`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/server/agent/health` | GET | Health check + API key status |
| `/server/agent/sessions` | POST | Create new chat session |
| `/server/agent/sessions` | GET | List all sessions |
| `/server/agent/sessions/<id>` | GET | Get session details |
| `/server/agent/sessions/<id>` | DELETE | Delete session |
| `/server/agent/sessions/<id>/approve` | POST | Approve/reject action |

#### SocketIO Events (namespace: `/agent`)

| Event | Direction | Data |
|-------|-----------|------|
| `join_session` | Client → Server | `{session_id}` |
| `send_message` | Client → Server | `{session_id, message}` |
| `approve` | Client → Server | `{session_id, approved, modifications}` |
| `agent_event` | Server → Client | Event with type, agent, content |

### Event Types

```python
class EventType(str, Enum):
    THINKING = "thinking"           # Agent reasoning
    TOOL_CALL = "tool_call"         # Tool being called
    TOOL_RESULT = "tool_result"     # Tool result
    MESSAGE = "message"             # Agent message to user
    MODE_DETECTED = "mode_detected"
    AGENT_DELEGATED = "agent_delegated"
    AGENT_COMPLETED = "agent_completed"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RECEIVED = "approval_received"
    PROGRESS = "progress"
    ERROR = "error"
```

---

## Frontend Architecture

### File Structure

```
frontend/src/
├── pages/
│   └── AgentChat.tsx              # Main chat page
│
└── components/
    └── common/
        └── Navigation_Bar.tsx     # AI Agent button in nav
```

### AgentChat Page Features

1. **API Key Management**
   - Auto-detects backend `ANTHROPIC_API_KEY` from `.env`
   - Falls back to user-provided key (stored in localStorage)
   - Shows API key input only when needed

2. **Session Persistence**
   - Messages saved to localStorage
   - Survives page refresh/navigation

3. **Status Indicator**
   - Single colored dot (green/yellow/red)
   - Green = Ready, Yellow = Checking/Setup, Red = Error

4. **Clean Chat UI**
   - Message bubbles with agent colors
   - Collapsible tool call details
   - Processing spinner during agent work
   - Approval buttons when required

### UI States

| State | What You See |
|-------|--------------|
| **Checking** | Spinner + "Connecting..." |
| **Needs Key** | 🔑 API key input form |
| **Ready** | ● Green dot + chat messages |
| **Error** | ● Red dot + retry button |

### SocketIO Integration

```typescript
// Connect to agent namespace
const socket = io(`${serverUrl}/agent`, {
  path: '/server/socket.io',
  transports: ['websocket', 'polling'],
});

// Join session
socket.emit('join_session', { session_id: sessionId });

// Send message
socket.emit('send_message', { session_id, message });

// Receive events
socket.on('agent_event', (event: AgentEvent) => {
  // Handle thinking, tool_call, message, etc.
});
```

### Color Coding

**Modes:**
| Mode | Color |
|------|-------|
| CREATE | Green (#4caf50) |
| VALIDATE | Blue (#2196f3) |
| ANALYZE | Orange (#ff9800) |
| MAINTAIN | Purple (#9c27b0) |

**Agents:**
| Agent | Color |
|-------|-------|
| QA Manager | Blue (#1976d2) |
| Explorer | Green (#4caf50) |
| Builder | Orange (#ff9800) |
| Executor | Red (#f44336) |
| Analyst | Purple (#9c27b0) |
| Maintainer | Cyan (#00bcd4) |

---

## Usage Examples

### CREATE Mode
```
User: "Automate sauce-demo.com with login and cart flows"

QA Manager: Mode detected: CREATE
  → Delegating to Explorer...
  
Explorer: 
  → get_compatible_hosts()
  → start_ai_exploration()
  → approve_exploration_plan()
  → validate_exploration_edges()
  ← Created 5 nodes, 8 edges

QA Manager: Delegating to Builder...

Builder:
  → create_requirement() x 3
  → generate_and_save_testcase() x 3
  → link_testcase_to_requirement()
  ← Created 3 requirements, 3 test cases

QA Manager: ✅ Complete! Created navigation tree + test cases.
```

### VALIDATE Mode
```
User: "Run regression tests for sauce-demo"

QA Manager: Mode detected: VALIDATE
  → Delegating to Executor...

Executor:
  → get_compatible_hosts()
  → take_control()
  → execute_testcase() x 3
  ← Results: 2 passed, 1 failed

QA Manager: Delegating to Analyst...

Analyst:
  → Analyzing TC_CART_01 failure...
  → Classification: UI CHANGE (selector #add-to-cart moved)
  ← Recommend: Flag for Maintainer

QA Manager: ✅ 2/3 passed. 1 failure needs selector update.
```

### MAINTAIN Mode
```
User: "Fix the broken cart button selector"

QA Manager: Mode detected: MAINTAIN
  → Delegating to Maintainer...

Maintainer:
  → get_edge() - Get current selector
  → dump_ui_elements() - Analyze screen
  → analyze_screen_for_action() - Find new selector
  → update_edge() - Apply fix
  → execute_edge() - Verify fix
  ← Fixed! New selector: [data-testid="add-to-cart"]

QA Manager: ✅ Edge fixed and verified.
```

---

## Configuration

### Environment Variables

```bash
# Required for AI Agent
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Optional
AGENT_MODEL=claude-sonnet-4-20250514
AGENT_MAX_TOKENS=8192
```

### Dependencies

**Backend:**
```
anthropic>=0.40.0
```

**Frontend:**
```
socket.io-client
```

---

## Approval Points

The system pauses for human approval at:

| Scenario | Reason |
|----------|--------|
| First-time site exploration | Verify AI understood correctly |
| New test case creation | Review before saving |
| Creating Jira tickets | Confirm it's a real bug |
| Major tree changes | Prevent accidental data loss |

---

## Error Handling

### Agent Errors
- Tool failures are caught and reported
- Agent can retry with different approach
- Persistent failures escalate to QA Manager

### Session Management
- Sessions timeout after 24 hours
- Cleanup runs automatically
- State persisted in memory (DB integration planned)

---

## Future Enhancements

1. **Jira Integration**: Auto-create tickets for bugs
2. **Slack Alerts**: Notify on failures below threshold
3. **Parallel Execution**: Multiple Executor instances
4. **Session Persistence**: Database-backed sessions
5. **Sub-agent Memory**: Remember past fixes
