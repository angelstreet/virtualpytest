Sure! Here's how the routes are architected in this codebase:

## Routes Architecture

```
backend_server/src/routes/
├── server_integrations_routes.py    # /server/integrations/* (JIRA, Slack)
├── server_agent_routes.py           # WebSocket + /server/agent/*
├── server_control_routes.py         # /server/control/*
├── server_device_routes.py          # /server/device/*
└── ... other server_* routes
```

---

## Pattern: 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Routes (Flask Blueprints)                         │
│  backend_server/src/routes/*.py                             │
│  - HTTP endpoints only                                       │
│  - Request parsing, validation                               │
│  - Response formatting                                       │
│  - NO business logic                                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Database Layer (Shared)                           │
│  shared/src/lib/database/*_db.py                            │
│  - Pure database operations                                  │
│  - Supabase client calls                                     │
│  - Returns dicts/lists                                       │
│  - NO Flask, NO HTTP                                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Supabase (Database)                               │
│  shared/src/lib/utils/supabase_utils.py                     │
│  - Connection management                                     │
│  - Single client instance                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Example: Benchmark Routes

**Route file** (`agent_benchmark_routes.py`):
```python
# Thin layer - just HTTP handling
@server_agent_benchmark_bp.route('/runs', methods=['GET'])
def route_list_benchmark_runs():
    agent_id = request.args.get('agent_id')  # Parse request
    team_id = get_team_id()
    
    runs = list_benchmark_runs(team_id, agent_id)  # Call DB layer
    
    return jsonify({'runs': runs}), 200  # Format response
```

**DB layer** (`agent_benchmarks_db.py`):
```python
# Pure database logic - no Flask
def list_benchmark_runs(team_id, agent_id=None):
    supabase = get_supabase()
    query = supabase.table('agent_benchmark_runs').select('*').eq('team_id', team_id)
    if agent_id:
        query = query.eq('agent_id', agent_id)
    return query.execute().data
```

---

## Blueprint Registration

In `backend_server/src/server.py`:
```python
from routes.agent_benchmark_routes import server_agent_benchmark_bp
from routes.agent_registry_routes import server_agent_registry_bp

app.register_blueprint(server_agent_benchmark_bp)  # → /api/benchmarks/*
app.register_blueprint(server_agent_registry_bp)   # → /api/agents/*
```

---

## Key Principles

| Rule | Why |
|------|-----|
| Routes = thin HTTP layer | Easy to test, swap frameworks |
| DB layer in `shared/` | Reusable across server & scripts |
| No async in routes | Flask is sync; use `run_async()` only for Redis |
| `get_team_id()` helper | Extracts from query params or headers |

---

## File-Based vs DB-Based

| Data Type | Location |
|-----------|----------|
| **Benchmark tests** | YAML files (version controlled) |
| **Benchmark results** | Database (runtime data) |
| **Agent configs** | YAML templates + DB registry |
| **Execution history** | Database |