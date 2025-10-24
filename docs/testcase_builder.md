# TestCase Builder - Unified Visual & AI Test Creation

## Overview

The **TestCase Builder** is a unified test creation tool that allows users to create automated test scripts visually (drag-drop) or via AI (natural language prompt). All test cases are stored as graphs and executed through the same engine.

**Key Features:**
- 🎨 Visual drag-drop interface (React Flow)
- 🤖 AI prompt-based generation
- 🔄 Edit AI-generated tests visually
- 💾 Unified execution tracking (script_results table)
- 📊 Automatic report generation
- 🔁 Loop support with nested flows
- 📱 Device-agnostic execution

**Creation Methods:**
- **Visual Mode**: Drag blocks from toolbox, connect with edges
- **AI Mode**: Describe test in natural language, AI generates graph

Both methods produce the same graph structure and execute identically.

**Live AI Modal vs TestCase Builder:**
- **Live AI Modal**: Generate graph → Convert to steps for display → Execute (no save)
- **TestCase Builder**: Generate/edit graph → Save → Execute (persistent)

Both use the same unified backend route with different flags.

---

## Architecture

### High-Level Flow

```
┌──────────────────────────────────────────────┐
│     Live AI Modal (Ephemeral)                │
│  Natural language prompt                     │
│         ↓                                    │
│    1. Pre-process prompt (validate nodes)    │
│    2. AI generates graph (nodes/edges)       │
│    3. Pre-fetch navigation transitions       │
│         ↓                                    │
│    Display in AIStepDisplay component        │
│         ↓                                    │
│    Execute graph (no save)                   │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│        TestCase Builder Page                 │
│  ┌────────────┬──────────────────────────┐   │
│  │ Visual Mode│  AI Prompt Mode          │   │
│  │ (drag-drop)│  (natural language)      │   │
│  └──────┬─────┴──────────┬───────────────┘   │
│         │                │                   │
│         │                │ 1. Pre-process    │
│         │                │ 2. AI → graph     │
│         │                │ 3. Pre-fetch      │
│         ↓                ↓                   │
│    React Flow Graph  React Flow Graph       │
│    (editable after generation)               │
└────────────────┬─────────────────────────────┘
                 │ Both save as graph
                 ↓
┌────────────────────────────────────────────┐
│    testcase_definitions (Database)         │
│    - graph_json: {nodes[], edges[]}        │
│    - creation_method: 'visual' | 'ai'      │
│    - ai_prompt (if AI-generated)           │
│    - ai_analysis (if AI-generated)         │
└────────────────┬───────────────────────────┘
                 │ Both execute same way
                 ↓
┌────────────────────────────────────────────┐
│    testcase_executor.py                    │
│    - Execute graph (nodes/edges)           │
│    - Delegate to action/verification exec  │
│    - Record steps to context               │
└────────────────┬───────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────┐
│    ScriptExecutionContext                  │
│    - Unified step recording                │
│    - Screenshots, timing, etc.             │
└────────────────┬───────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────┐
│    script_results (DB)                     │
│    - script_type='testcase'                │
│    - Unified result format                 │
└────────────────────────────────────────────┘
```

### AI Generation Pipeline

```
User Prompt: "Go to live TV"
         ↓
┌─────────────────────────────────────────────┐
│ 1. PRE-PROCESSING (ai_prompt_validation.py) │
│    - Extract navigation node phrases        │
│    - Check against available nodes          │
│    - Apply learned mappings from DB         │
│    - Auto-fix fuzzy matches                 │
│    - Return disambiguation if needed        │
└────────────────┬────────────────────────────┘
                 ↓ (validated prompt)
┌─────────────────────────────────────────────┐
│ 2. AI GENERATION (ai_executor.py)           │
│    - Call AI with validated context         │
│    - AI returns graph: {nodes[], edges[]}   │
│    - No post-validation needed              │
└────────────────┬────────────────────────────┘
                 ↓ (graph)
┌─────────────────────────────────────────────┐
│ 3. TRANSITION PRE-FETCH                     │
│    - For each navigation node in graph      │
│    - Fetch transitions from DB              │
│    - Embed in graph (no UI fetching later)  │
└────────────────┬────────────────────────────┘
                 ↓ (complete graph)
┌─────────────────────────────────────────────┐
│ 4. EXECUTION (testcase_executor.py)         │
│    - Traverse graph nodes/edges             │
│    - Execute actions/verifications          │
│    - Use pre-fetched transitions            │
└─────────────────────────────────────────────┘
```

---

## Database Schema

### Test Case Definitions

```sql
CREATE TABLE testcase_definitions (
    testcase_id UUID PRIMARY KEY,
    team_id UUID REFERENCES teams(id),
    testcase_name VARCHAR(255) UNIQUE,  -- Used as script_name
    description TEXT,
    userinterface_name VARCHAR(255),    -- Navigation tree
    graph_json JSONB,                   -- React Flow structure
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Creation metadata
    creation_method VARCHAR(10),  -- 'visual' or 'ai'
    ai_prompt TEXT,              -- Original prompt if AI-generated
    ai_analysis TEXT             -- AI reasoning if AI-generated
);
```

### Execution Results (REUSED)

```sql
-- Test case executions stored in existing table
-- No new table needed!
SELECT * FROM script_results 
WHERE script_type = 'testcase'  
  AND script_name = 'login_test';
```

---

## API Endpoints

### Routing Architecture

**Frontend → Server → Host**
```
Frontend calls:  /server/testcase/*  (public API)
Server proxies:  /host/testcase/*    (internal to host)
Host executes:   TestCaseExecutor    (actual execution)
```

**Benefits:**
- ✅ Unified frontend API endpoint
- ✅ Server handles routing to appropriate host
- ✅ Clean separation: Server (proxy) vs Host (execution)
- ✅ Follows same pattern as AI routes

### Test Case CRUD

```
POST   /server/testcase/save?team_id=xxx
  Proxies to: /host/testcase/save
  Request:
    {
      "testcase_name": "login_test",
      "graph_json": { nodes: [...], edges: [...] },
      "description": "Test login flow",
      "userinterface_name": "horizon_android_mobile",
      "created_by": "john@example.com",
      "creation_method": "visual" | "ai",  // NEW
      "ai_prompt": "...",                   // NEW (if AI)
      "ai_analysis": "..."                  // NEW (if AI)
    }
  Response:
    {
      "success": true,
      "testcase_id": "uuid",
      "action": "created" | "updated"
    }

GET    /server/testcase/list?team_id=xxx
  Proxies to: /host/testcase/list
  Response:
    {
      "success": true,
      "testcases": [
        {
          "testcase_id": "uuid",
          "testcase_name": "login_test",
          "description": "...",
          "creation_method": "ai",       // NEW
          "ai_prompt": "Go to live TV",  // NEW
          "created_at": "2024-10-24",
          "execution_count": 5,
          "last_execution_success": true
        }
      ]
    }

GET    /server/testcase/:id?team_id=xxx
  Proxies to: /host/testcase/:id
  Response:
    {
      "success": true,
      "testcase": {
        "testcase_id": "uuid",
        "testcase_name": "login_test",
        "graph_json": { nodes: [...], edges: [...] },
        "userinterface_name": "horizon_android_mobile",
        "creation_method": "visual",
        ...
      }
    }

DELETE /server/testcase/:id?team_id=xxx
  Proxies to: /host/testcase/:id (DELETE)
  Response:
    {"success": true}
```

### Execution & History

```
POST   /server/testcase/:id/execute?team_id=xxx
  Proxies to: /host/testcase/:id/execute
  Request:
    {"device_id": "device1"}
  Response:
    {
      "success": true,
      "result": {
        "success": true,
        "execution_time_ms": 5432,
        "step_count": 4,
        "script_result_id": "uuid",
        "report_url": "https://..."
      }
    }

GET    /server/testcase/:id/history?team_id=xxx
  Proxies to: /host/testcase/:id/history
  Response:
    {
      "success": true,
      "history": [
        {
          "script_result_id": "uuid",
          "started_at": "2024-10-24T10:00:00Z",
          "execution_time_ms": 5432,
          "success": true
        }
      ]
    }
```

---

## User Workflow

### **Workflow 1: Visual Creation**

```
1. User navigates to /test-plan/testcase-builder
2. Select "Visual Mode"
3. Drag START block from toolbox to canvas
4. Drag ACTION block, configure command (e.g., press_ok)
5. Connect START → ACTION via success edge
6. Drag VERIFICATION block, configure check
7. Connect ACTION → VERIFICATION
8. Drag SUCCESS block
9. Connect VERIFICATION → SUCCESS via success edge
10. Click "Save" → Enter name, description, UI name
11. Graph saved to database (creation_method='visual')
```

### **Workflow 2: AI Generation**

```
1. User navigates to /test-plan/testcase-builder
2. Select "AI Prompt Mode"
3. Enter natural language prompt: "Go to live TV and verify audio"
4. Click "Generate with AI"
5. AI generates graph directly with nodes and edges
6. Graph appears in React Flow (editable)
7. User can edit visually if needed
8. Click "Save" → Enter name (or auto-named "AI: [prompt]")
9. Graph saved to database (creation_method='ai', ai_prompt stored)
```

### **Workflow 3: Execution (Same for Both)**

```
1. User clicks "Execute" button
2. Frontend calls POST /server/testcase/{id}/execute
3. Server proxies to POST /host/testcase/{id}/execute
4. testcase_executor.py loads graph and traverses nodes/edges
5. Each node delegates to ActionExecutor/VerificationExecutor/NavigationExecutor
6. Steps recorded in script_results (script_type='testcase')
7. Report generated and URL returned
8. Frontend displays report
```

---

## Key Benefits

### For Users
- 🎨 **Visual Mode**: No coding required, intuitive drag-drop
- 🤖 **AI Mode**: Describe what you want in plain English
- ✏️ **Hybrid**: Edit AI-generated tests visually
- 🔍 Visual flow understanding
- ⚡ Fast iteration
- 🔄 Easy modifications
- 📊 Same reporting as scripts

### For System Architecture
- 🎯 Single test case system (no AI vs Visual split)
- 🔄 Unified execution engine (testcase_executor)
- 📊 Unified tracking (script_results)
- 💾 Single storage (testcase_definitions)
- 🎥 Same report generation
- 🔧 One codebase to maintain

---

## Implementation Status

### ✅ Phase 1 Complete
- Database schema with AI metadata columns
- AI executor generates graphs directly
- Clean implementation (no legacy validation)
- Unified documentation
- Migration applied

### ✅ Phase 2 Complete (October 2024)
- API service layer created
- Save/Load UI implemented
- Execute functionality added
- Navigation tree fetching working
- AI Prompt Mode integrated
- Bug fixes:
  - Fixed Supabase import in ai_plan_generation_db.py
  - Removed legacy validate_plan (graph validation now in pre-processing)
  - Fixed cache behavior: cache miss now falls through to generation (not abort)
  - Clean separation: pre-processing validation vs execution

### Cache Behavior

**`use_cache=True` (Recommended):**
- Try to find cached plan first
- If cache **hit**: Execute cached plan immediately (fast!)
- If cache **miss**: Generate new plan with AI, execute, then cache it for next time
- Best for repeated tasks - first run generates, subsequent runs use cache

**`use_cache=False`:**
- Always generate fresh plan with AI
- Never use cached plans
- Never store plans in cache
- Use for one-off tasks or when testing new prompts

**Understanding Cache Logs:**

The system now provides **explicit, clear logging** to distinguish between normal cache misses and actual errors:

- ✅ `✓ Cache HIT` - Found cached plan, no AI call needed (fast!)
- ✅ `✓ Cache MISS (normal)` - No cache exists yet, will generate with AI (expected behavior!)
- ❌ `❌ Database error` - Actual problem (connection, permissions, etc.)

When you see "0 rows returned" in logs, the system now clarifies this is **normal** for first executions. See `docs/dev/ai_cache_logging.md` for detailed log examples and troubleshooting.

### 📋 Phase 3: Future Enhancements
- Advanced loop configurations
- Conditional branching
- Parallel execution paths
- Test case versioning
- A/B test comparison
- Campaign integration

---

## Technical Implementation Details

### Graph Format (Modern)

AI generates graphs directly with React Flow compatible structure:

```json
{
  "graph": {
    "nodes": [
      {
        "id": "start",
        "type": "start",
        "position": {"x": 100, "y": 100},
        "data": {}
      },
      {
        "id": "step1",
        "type": "navigation",
        "position": {"x": 100, "y": 200},
        "data": {
          "target_node": "live_fullscreen",
          "target_node_id": "live_fullscreen",
          "transitions": [...]  // Pre-fetched
        }
      },
      {
        "id": "success",
        "type": "success",
        "position": {"x": 100, "y": 300},
        "data": {}
      }
    ],
    "edges": [
      {
        "id": "e1",
        "source": "start",
        "target": "step1",
        "sourceHandle": "success",
        "type": "success"
      },
      {
        "id": "e2",
        "source": "step1",
        "target": "success",
        "sourceHandle": "success",
        "type": "success"
      }
    ]
  }
}
```

### Validation Strategy

**Pre-Processing (Before AI):**
- Extract navigation phrases from prompt
- Validate against available nodes
- Apply learned mappings from database
- Auto-fix fuzzy matches (single match or 90%+ confidence)
- Return disambiguation modal if ambiguous

**During Generation:**
- AI only receives validated nodes
- AI generates graph with valid nodes only
- Transitions pre-fetched and embedded

**Post-Processing:**
- ❌ No validation needed (already done in pre-processing)
- ✅ Graph ready for execution

### Legacy Format Support

For backward compatibility with old cached plans:

```python
# Convert legacy 'steps' format to modern 'graph' format
if 'steps' in ai_response and 'graph' not in ai_response:
    ai_response['graph'] = self._convert_steps_to_graph(ai_response['steps'])
```

This ensures old cached plans can still be used without breaking the system.
