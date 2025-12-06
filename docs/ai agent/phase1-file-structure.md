# Phase 1 File Structure
## New Files & Directories for Event-Driven Multi-Agent Platform

```
virtualpytest/
│
├── backend_server/
│   ├── requirements.txt                           # [MODIFY] Add asyncpg, apscheduler
│   │
│   └── src/
│       │
│       ├── events/                                # [NEW] Event Bus System
│       │   ├── __init__.py
│       │   ├── event_bus.py                       # Core Event Bus (Redis pub/sub)
│       │   ├── event_router.py                    # Route events to agents
│       │   ├── event_types.py                     # Event type definitions
│       │   │
│       │   └── sources/                           # [NEW] Event Sources
│       │       ├── __init__.py
│       │       ├── alert_source.py                # Alert events (blackscreen, offline)
│       │       ├── scheduler_source.py            # Cron/scheduled events
│       │       └── webhook_source.py              # [FUTURE] CI/CD webhooks
│       │
│       ├── resources/                             # [NEW] Resource Management
│       │   ├── __init__.py
│       │   ├── lock_manager.py                    # Resource lock management
│       │   └── device_pool.py                     # [FUTURE] Device pool management
│       │
│       ├── agent/
│       │   ├── config.py                          # [EXISTS] Current agent config
│       │   │
│       │   ├── registry/                          # [NEW] Agent Registry
│       │   │   ├── __init__.py
│       │   │   ├── config_schema.py               # Pydantic models for agent definition
│       │   │   ├── registry.py                    # Agent storage/retrieval
│       │   │   ├── validator.py                   # YAML validation
│       │   │   └── templates/                     # [NEW] Agent YAML templates
│       │   │       ├── qa-manager-template.yaml
│       │   │       ├── explorer-template.yaml
│       │   │       └── executor-template.yaml
│       │   │
│       │   ├── runtime/                           # [NEW] Agent Runtime
│       │   │   ├── __init__.py
│       │   │   ├── runtime.py                     # Agent instance management
│       │   │   ├── executor.py                    # Task execution logic
│       │   │   └── state.py                       # Agent state tracking
│       │   │
│       │   ├── core/                              # [EXISTS] Current QA Manager
│       │   │   ├── manager.py
│       │   │   ├── session.py
│       │   │   └── tool_bridge.py
│       │   │
│       │   └── agents/                            # [EXISTS] Specialist agents
│       │       ├── base_agent.py
│       │       ├── explorer.py
│       │       ├── executor.py
│       │       └── analyst.py
│       │
│       ├── routes/
│       │   ├── server_agent_routes.py             # [EXISTS] Current chat routes
│       │   ├── agent_registry_routes.py           # [NEW] Agent CRUD operations
│       │   ├── agent_runtime_routes.py            # [NEW] Agent instance control
│       │   └── event_routes.py                    # [NEW] Manual event triggering
│       │
│       └── database/                              # [NEW] Database utilities
│           ├── __init__.py
│           └── async_client.py                    # Async PostgreSQL client

├── setup/
│   └── db/
│       └── schema/
│           ├── 020_event_system.sql               # [NEW] Event & Resource Lock tables
│           └── 021_agent_registry.sql             # [NEW] Agent Registry tables
│
├── shared/
│   └── src/
│       └── lib/
│           └── database/
│               ├── event_log_db.py                # [NEW] Event log operations
│               └── agent_registry_db.py           # [NEW] Agent registry operations
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   └── AgentChat.tsx                      # [MODIFY] Add agent selector
│       │
│       └── components/
│           └── agent/                             # [NEW] Agent UI components
│               ├── AgentSelector.tsx              # Agent dropdown selector
│               ├── AgentStatus.tsx                # Real-time status display
│               └── AgentControls.tsx              # Start/stop/pause controls
│
├── tests/                                         # [NEW] Phase 1 tests
│   └── backend_server/
│       └── events/
│           ├── test_event_bus.py
│           ├── test_lock_manager.py
│           ├── test_agent_registry.py
│           └── test_agent_runtime.py
│
└── docs/
    └── ai agent/
        ├── autonomous-agent-architecture.md       # [EXISTS] Architecture doc
        ├── implementation-roadmap.md              # [EXISTS] This roadmap
        ├── phase1-file-structure.md               # [NEW] This file
        └── agent-yaml-schema.md                   # [NEW] Agent config spec
```

---

## File Count Summary

### New Files: **29 files**
- Backend Python: 18 files
- Database Schema: 2 files (020, 021)
- Frontend TypeScript: 3 files
- Tests: 4 files
- Documentation: 2 files

### Modified Files: **2 files**
- `backend_server/requirements.txt` - Add dependencies
- `frontend/src/pages/AgentChat.tsx` - Add agent selector UI

---

## Key Dependencies to Add

### requirements.txt additions:
```python
# Async PostgreSQL
asyncpg>=0.29.0

# Task scheduling
apscheduler>=3.10.0

# FastAPI (optional for new async routes)
fastapi>=0.104.0
uvicorn>=0.24.0

# WebSocket support (already have redis, just ensure version)
redis>=4.5.0  # Already present, just verify
```

### System dependencies:
```bash
# Redis server (macOS)
brew install redis

# Start Redis
brew services start redis
```

---

## Database Schema Overview

### Tables to Create:

1. **event_log** (Step 1.1)
   - Stores all events published to the bus
   - Fields: id, event_id, event_type, payload, priority, timestamp

2. **resource_locks** (Step 1.2)
   - Tracks device/resource locks
   - Fields: id, resource_id, owner_id, acquired_at, expires_at

3. **agent_registry** (Step 1.3)
   - Stores agent definitions and versions
   - Fields: id, agent_id, version, definition (JSONB)

4. **agent_event_triggers** (Step 1.3)
   - Maps which events trigger which agents
   - Fields: id, agent_id, event_type, priority

5. **scheduled_events** (Step 4.2)
   - Cron-based scheduled events
   - Fields: id, event_type, cron_expression, payload

---

## Implementation Order

### Week 1: Core Infrastructure
1. Create directory structure
2. Add dependencies to requirements.txt
3. Install Redis
4. Create database migrations
5. Implement Event Bus (event_bus.py)
6. Implement Resource Lock Manager (lock_manager.py)
7. Write tests

### Week 2: Agent Foundation
8. Create agent config schema (config_schema.py)
9. Implement agent registry (registry.py)
10. Create YAML templates
11. Add registry routes
12. Write tests

### Week 3: Runtime
13. Implement agent runtime (runtime.py)
14. Create event router (event_router.py)
15. Add runtime routes
16. Write tests

### Week 4: UI Integration
17. Add agent selector UI (AgentSelector.tsx)
18. Add status display (AgentStatus.tsx)
19. WebSocket for real-time updates
20. Test end-to-end

---

## Existing vs New Architecture

### What Stays (No Changes):
- ✅ Current QA Manager agent system
- ✅ Specialist agents (Explorer, Builder, etc.)
- ✅ Existing chat interface
- ✅ MCP tools and routes
- ✅ Supabase database operations
- ✅ All existing routes

### What Gets Added (New):
- ➕ Event Bus for async events
- ➕ Resource Lock Manager
- ➕ Agent Registry for versioning
- ➕ Agent Runtime for parallel execution
- ➕ Multi-agent UI selector
- ➕ Event sources (alerts, scheduler)

### Integration Points:
1. Current chat → Can trigger events → Event Bus
2. Current agents → Can be wrapped as versioned agents → Agent Registry
3. Existing device control → Uses Resource Lock Manager
4. Current routes → Coexist with new agent routes

---

## Migration Strategy

**No Breaking Changes!**

1. **Phase 1-2**: Build new system alongside old
2. **Phase 3**: Connect new UI to new system
3. **Phase 4**: Add event sources
4. **Phase 5**: Migrate QA Manager to use new runtime (optional)
5. **Phase 6**: Deprecate old chat-only mode (if desired)

Users can use BOTH systems simultaneously:
- Old: Chat with QA Manager (existing)
- New: Event-driven multi-agent (new)

---

## Next Steps

Would you like me to:
1. ✅ Create all directory structure
2. ✅ Add dependencies to requirements.txt
3. ✅ Create database migration files
4. ✅ Implement Event Bus (Step 1.1)
5. ✅ Implement Resource Lock Manager (Step 1.2)

Or would you prefer to review the structure first?

