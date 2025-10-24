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

---

## Architecture

### High-Level Flow

```
┌──────────────────────────────────────────────┐
│        TestCase Builder Page                 │
│  ┌────────────┬──────────────────────────┐   │
│  │ Visual Mode│  AI Prompt Mode          │   │
│  │ (drag-drop)│  (natural language)      │   │
│  └──────┬─────┴──────────┬───────────────┘   │
│         │                │                   │
│         │                │ AI generates      │
│         │                │ graph directly    │
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
- Graph validation updated
- Unified documentation
- Migration applied

### 🚧 Phase 2: Frontend Integration (In Progress)
- API service layer created
- Save/Load UI implemented
- Execute functionality added
- Navigation tree fetching (pending)
- AI Prompt Mode UI (pending)

### 📋 Phase 3: Future Enhancements
- Advanced loop configurations
- Conditional branching
- Parallel execution paths
- Test case versioning
- A/B test comparison
- Campaign integration
