# AI Graph Builder Documentation

**Clean, single-file AI graph generation system**

NO legacy code, NO backward compatibility - Pure, efficient implementation.

---

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Context Loading (24h cache) | ✅ **Implemented** | In-memory cache per device |
| **Graph Caching (mandatory)** | ✅ **Implemented** | Database-backed, fingerprint-based |
| AI Generation | ✅ **Implemented** | OpenRouter API integration |
| Post-processing (labels) | ✅ **Implemented** | Enforces naming conventions |
| Pre-fetch Transitions | ✅ **Implemented** | Embeds navigation paths |
| Frontend UI | ✅ **Implemented** | Result panel + reopen button |
| **Preprocessing (exact match)** | ✅ **Implemented** | Skip AI for simple prompts |
| **Disambiguation** | ✅ **Implemented** | Interactive modal + auto-learning |
| **Learned Mappings** | ✅ **Implemented** | Auto-apply user choices |
| Advanced Validation | ❌ **TODO** | Pre-execution checks |

---

## Architecture Overview

```
Frontend → Server (proxy) → Host → AIGraphBuilder → OpenRouter AI → Graph
                                         ↓
                                   Device Services
                                   (navigation, testcase)
```

**Components:**
- `backend_host/src/services/ai/ai_builder.py` - Main AIGraphBuilder class
- `backend_host/src/lib/utils/graph_utils.py` - Pure graph utilities
- `backend_host/src/routes/host_ai_routes.py` - HTTP routes

---

## Complete Pipeline Flow

### 1. **User Input**
```
Frontend: User enters "Navigate to home" in AI Test Generator
```

### 2. **Request Flow**
```
POST /server/ai/generatePlan
  ↓ (proxy)
POST /host/ai/generatePlan
  ↓
AIGraphBuilder.generate_graph()
```

### 3. **Context Loading** (with 24h cache)
```
Load from device services:
- Available navigation nodes (from navigation_executor)
- Available actions (from testcase_executor)
- Available verifications (from testcase_executor)

Cached per: device_id + userinterface_name + team_id
TTL: 24 hours
```

### 4. **Graph Cache Check** (MANDATORY - Skip AI if HIT)
```
Generate fingerprint = MD5(normalized_prompt + context)

Query database:
  SELECT * FROM ai_graph_cache 
  WHERE fingerprint = ? AND team_id = ?

CACHE HIT?
  ✅ Return cached graph immediately (500ms)
  ✅ Skip AI call entirely
  ✅ Increment use_count
  
CACHE MISS?
  → Continue to AI generation (step 5)
```

### 5. **AI Generation** (only if cache miss)
```
Build AI prompt with:
- Task description
- Available nodes/actions/verifications
- Output format + examples
- Label naming rules

Call OpenRouter API:
- Model: microsoft/phi-3-mini-128k-instruct
- Max tokens: 2000
- Temperature: 0.0

Parse JSON response:
- Handle markdown blocks
- Handle trailing content
- Extract usage stats (tokens)
```

### 6. **Post-Processing**
```
Validate feasibility
  ↓
Enforce labels:
  navigation_N:target
  action_N:command
  verification_N:type
  ↓
Pre-fetch navigation transitions:
  Resolve target nodes
  Get paths from unified graph
  Embed in node data
  ↓
Calculate stats:
  Block counts
  Token usage
```

### 7. **Store in Cache** (for next time)
```
INSERT INTO ai_graph_cache (
  fingerprint,
  original_prompt,
  device_model,
  userinterface_name,
  available_nodes,
  graph,
  analysis,
  team_id,
  use_count,
  created_at,
  last_used
)

Next identical request → CACHE HIT (instant)
```

### 8. **Response**
```json
{
  "success": true,
  "graph": {
    "nodes": [
      {"id": "start", "type": "start", "data": {"label": "START"}},
      {"id": "nav1", "type": "navigation", "data": {
        "label": "navigation_1:home",
        "target_node": "home",
        "transitions": [...]
      }},
      {"id": "success", "type": "success", "data": {"label": "SUCCESS"}}
    ],
    "edges": [...]
  },
  "analysis": "Goal: Navigate to home\nThinking: 'home' exists → direct navigation",
  "execution_time": 4.51,
  "generation_stats": {
    "prompt_tokens": 8609,
    "completion_tokens": 983,
    "total_tokens": 9592,
    "block_counts": {
      "navigation": 1,
      "action": 0,
      "verification": 0,
      "total": 3
    }
  }
}
```

---

## API Reference

### `AIGraphBuilder.generate_graph()`

**Main entry point for graph generation**

```python
result = ai_builder.generate_graph(
    prompt="Navigate to home and check audio",
    userinterface_name="horizon_android_mobile",
    team_id="7fdeb4bb-3639-4ec3-959f-b54769a219ce",
    current_node_id=None  # Optional
)
```

**Returns:**
```python
{
    'success': bool,
    'graph': {
        'nodes': List[Dict],  # ReactFlow nodes
        'edges': List[Dict]   # ReactFlow edges
    },
    'analysis': str,  # AI reasoning (Goal + Thinking)
    'execution_time': float,  # Seconds
    'generation_stats': {
        'prompt_tokens': int,
        'completion_tokens': int,
        'total_tokens': int,
        'block_counts': {
            'navigation': int,
            'action': int,
            'verification': int,
            'other': int,
            'total': int
        },
        'blocks_generated': List[Dict]  # All blocks with type, label, id
    }
}
```

---

## Graph Format

### Node Structure

**All nodes:**
```python
{
    'id': str,  # Unique identifier
    'type': str,  # start, navigation, action, verification, success, failure
    'position': {'x': int, 'y': int},
    'data': {...}  # Type-specific data
}
```

**Navigation node data:**
```python
{
    'label': 'navigation_1:home',  # Enforced format
    'target_node': 'home',
    'target_node_id': 'home',
    'action_type': 'navigation',
    'transitions': [...]  # Pre-fetched path
}
```

**Action node data:**
```python
{
    'label': 'action_1:click_element',  # Enforced format
    'command': 'click_element',
    'element_id': 'replay',
    'action_type': 'remote'
}
```

**Verification node data:**
```python
{
    'label': 'verification_1:check_audio',  # Enforced format
    'verification_type': 'check_audio',
    'expected': {...}
}
```

### Edge Structure

```python
{
    'id': str,  # Unique identifier
    'source': str,  # Source node ID
    'target': str,  # Target node ID
    'sourceHandle': str,  # 'success' or 'failure'
    'type': str  # 'success' or 'failure'
}
```

---

## Label Naming Conventions

**Enforced by post-processing** (not AI):

| Type | Format | Example |
|------|--------|---------|
| start | `START` | `START` |
| success | `SUCCESS` | `SUCCESS` |
| failure | `FAILURE` | `FAILURE` |
| navigation | `navigation_N:target` | `navigation_1:home` |
| action | `action_N:command` | `action_1:click_element` |
| verification | `verification_N:type` | `verification_1:check_audio` |

**Why enforce?**
- Consistent UI display
- Predictable parsing
- AI is unreliable for formatting

---

## Context Caching

**Context loaded once per 24h per device/interface/team:**

```python
cache_key = f"{device_id}_{userinterface_name}_{team_id}"
cache_ttl = 86400  # 24 hours
```

**Cached data:**
- Available navigation nodes
- Available actions
- Available verifications
- Device model

**Cache cleared on:**
- Device restart
- Manual clear: `ai_builder.clear_context_cache()`

---

## Error Handling

### Common Errors

**1. Empty prompt:**
```json
{"success": false, "error": "Prompt is required"}
```

**2. Task not feasible:**
```json
{
  "success": false,
  "error": "Task not feasible",
  "analysis": "Goal: Go to settings\nThinking: No 'settings' node exists"
}
```

**3. AI returned invalid JSON:**
```json
{
  "success": false,
  "error": "AI returned invalid JSON: Expecting value: line 1 column 1 (char 0)"
}
```

**4. AI service unavailable:**
```json
{
  "success": false,
  "error": "AI call failed: OpenRouter API timeout"
}
```

---

## Performance

### Typical Timings

| Step | Time | Notes |
|------|------|-------|
| Context loading (first time) | 200-500ms | Database queries |
| Context loading (cached) | <5ms | In-memory cache |
| **Graph cache HIT** | **500ms** | **Instant response** |
| **Graph cache MISS** | **4-7s** | **Full AI generation** |
| AI API call | 3-6s | OpenRouter latency |
| JSON parsing | <10ms | |
| Post-processing | 50-200ms | Label enforcement + transitions |

### Cache Hit Rates

**Expected performance:**
- First request: 4-7s (cache miss, full AI)
- Identical requests: 500ms (cache hit, no AI)
- **Cost savings**: ~90% reduction in API calls

### Optimization Strategies

**1. Context caching (24h TTL):**
- Reduces repeated DB queries
- Balances freshness vs performance
- Clears on device restart

**2. Graph caching (permanent until deleted):**
- **CRITICAL**: Skips AI entirely for identical prompts
- Fingerprint-based (prompt + context hash)
- Tracks use_count for popularity metrics
- Cleanup: 90 days since last_used

**3. Pre-fetching transitions:**
- Embeds navigation paths in graph
- Frontend doesn't need additional API calls
- Faster test execution

---

## Graph Caching (Implemented)

### How It Works

**Fingerprint Generation:**
```python
# Normalize prompt
prompt_normalized = "navigate to home"  # lowercase, trimmed

# Create context signature
context_sig = {
    'device_model': 'android_mobile',
    'userinterface_name': 'horizon_android_mobile',
    'available_nodes': ['home', 'live', 'settings', ...]  # sorted
}

# Generate MD5 fingerprint
fingerprint = MD5(prompt_normalized + json.dumps(context_sig))
# Result: "a3f5e8d9c2b1..."
```

**Cache Lookup:**
```python
# Step 1: Check database
cached = get_graph_by_fingerprint(fingerprint, team_id)

if cached:
    # HIT - return immediately
    return cached['graph']
else:
    # MISS - generate with AI
    graph = generate_with_ai(...)
    store_graph(fingerprint, graph, ...)
    return graph
```

### Database Schema

```sql
CREATE TABLE ai_graph_cache (
    id SERIAL PRIMARY KEY,
    fingerprint TEXT NOT NULL,           -- MD5 hash (unique per team)
    original_prompt TEXT NOT NULL,       -- "Navigate to home"
    device_model TEXT NOT NULL,          -- "android_mobile"
    userinterface_name TEXT NOT NULL,    -- "horizon_android_mobile"
    available_nodes JSONB,               -- ["home", "live", ...]
    graph JSONB NOT NULL,                -- {nodes: [...], edges: [...]}
    analysis TEXT,                       -- "Goal: ... Thinking: ..."
    team_id UUID NOT NULL,
    use_count INTEGER DEFAULT 1,         -- Popularity tracking
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    UNIQUE(fingerprint, team_id)         -- One per fingerprint+team
);

CREATE INDEX idx_ai_graph_cache_fingerprint_team 
  ON ai_graph_cache(fingerprint, team_id);

CREATE INDEX idx_ai_graph_cache_last_used 
  ON ai_graph_cache(team_id, last_used);
```

### Cache Invalidation

**Automatic cleanup:**
```python
# Remove graphs unused for 90+ days
cleanup_old_graphs(team_id, days_old=90)
```

**Manual deletion:**
```python
# Delete specific graph
delete_graph(fingerprint, team_id)
```

**When cache invalidates:**
- Navigation nodes change (new fingerprint)
- Device model changes (new fingerprint)
- Interface changes (new fingerprint)
- Manual deletion
- 90 days since last_used

### Cache Metrics

**Track usage:**
- `use_count` - How many times this graph was reused
- `created_at` - When first generated
- `last_used` - Last cache hit

**Monitoring:**
```sql
-- Most popular graphs
SELECT original_prompt, use_count, last_used
FROM ai_graph_cache
WHERE team_id = ?
ORDER BY use_count DESC
LIMIT 10;

-- Cache hit rate (requires logging)
-- hits / (hits + misses) * 100
```

---

## Future Enhancements

### Planned (Not Yet Implemented)

**1. Advanced Validation**
   - Pre-execution validation:
     - Check all target nodes exist in navigation graph
     - Validate action commands are available on device
     - Detect impossible verification types
   - Return warnings before graph display

**2. Multi-step Flow Generation**
   - Handle complex prompts: "Go to home, then live, verify audio, then go to settings"
   - Parse into multiple sequential blocks
   - Generate longer, more complex graphs

**3. Context-aware Generation**
   - Use current device state as context
   - If already on "home", don't navigate there again
   - Optimize paths based on current position

**4. Smart Caching Invalidation**
   - Detect when navigation graph changes
   - Auto-invalidate affected cached graphs
   - Notify users of outdated graphs

---

## Preprocessing & Disambiguation (IMPLEMENTED)

### Complete Flow

```
User enters: "Navigate to live"
  ↓
Step 1: Exact Match Check
  → Is "live" exactly in available_nodes? 
     ✅ YES → Generate simple graph (100ms, no AI)
     ❌ NO → Continue to Step 2
  ↓
Step 2: Learned Mappings (Database)
  → Check: Has team mapped "live" before?
     ✅ YES → Auto-apply mapping: "live" → "live_tv" (200ms)
     ❌ NO → Continue to Step 3
  ↓
Step 3: Fuzzy Matching
  → Find similar nodes for "live":
     - 1 match → Auto-correct to that node (300ms)
     - 2+ matches → Show disambiguation dialog
     - 0 matches → Pass to AI (let AI handle it)
  ↓
Step 4: AI Generation (only if no match found)
  → Full AI call (4-7s)
```

### Disambiguation Dialog Flow

**When preprocessing finds ambiguity:**

```typescript
// Backend returns:
{
  "success": false,
  "needs_disambiguation": true,
  "ambiguities": [
    {
      "original": "live",
      "suggestions": ["live_tv", "live_radio", "live_streams"]
    }
  ],
  "original_prompt": "Navigate to live"
}
```

**Frontend shows modal:**

```
┌─────────────────────────────────────────┐
│ 🤔 Clarify Navigation Nodes             │
├─────────────────────────────────────────┤
│                                         │
│ We found: "live"                        │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ ✓ live_tv               ⭐ default  │ │ ← Pre-selected
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │   live_radio                        │ │ ← Click to select
│ └─────────────────────────────────────┘ │
│                                         │
├─────────────────────────────────────────┤
│ ✏️ Edit Prompt    [Cancel] [Confirm]   │
└─────────────────────────────────────────┘
```

**User clicks "Confirm":**
- Frontend sends selection to backend
- Backend saves to database: `"live" → "live_tv"` for this team
- Backend regenerates graph with corrected prompt
- **Next time**: "Navigate to live" → auto-corrects to "live_tv" (no dialog!)

### Learned Mappings (Database)

**Schema:**
```sql
CREATE TABLE ai_prompt_disambiguation (
    id UUID PRIMARY KEY,
    team_id UUID NOT NULL,
    userinterface_name TEXT NOT NULL,
    user_phrase TEXT NOT NULL,        -- "live"
    resolved_node TEXT NOT NULL,      -- "live_tv"
    usage_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, userinterface_name, user_phrase)
);
```

**How it works:**

1. **First time**: User sees disambiguation dialog
2. **User selects**: "live" → "live_tv"
3. **Saved to DB**: Mapping stored for team
4. **Next time**: 
   ```python
   learned = get_learned_mapping(team_id, userinterface_name, "live")
   # Returns: "live_tv"
   # Auto-apply → no dialog needed!
   ```

### Code Files

**Backend:**
- `backend_host/src/services/ai/ai_preprocessing.py` - Preprocessing logic
  - `check_exact_match()` - Direct node matching
  - `preprocess_prompt()` - Full preprocessing pipeline
  - `find_fuzzy_matches()` - Similarity matching
  - `extract_potential_node_phrases()` - Parse prompt for node refs

**Frontend:**
- `frontend/src/components/ai/PromptDisambiguation.tsx` - Disambiguation modal
- `frontend/src/types/aiagent/AIDisambiguation_Types.ts` - Type definitions

**Database:**
- `shared/src/lib/database/ai_prompt_disambiguation_db.py` - CRUD operations
  - `get_learned_mapping()` - Single mapping lookup
  - `get_learned_mappings_batch()` - Batch lookup (efficient)
  - `save_disambiguation()` - Store user selection

### Example Scenarios

**Scenario 1: Exact Match (Fastest)**
```
Input: "home"
→ Check: "home" exists? YES
→ Generate: START → navigation_1:home → SUCCESS
→ Time: 100ms, Cost: $0
```

**Scenario 2: Learned Mapping (Fast)**
```
Input: "Navigate to live"
→ Extract: "live"
→ Database: "live" → "live_tv" (learned)
→ Auto-apply: "Navigate to live_tv"
→ AI call with corrected prompt
→ Time: 4.2s (AI) + 200ms (DB), Cost: $0.01
→ Next time: Auto-corrected, same cost
```

**Scenario 3: Disambiguation (Interactive)**
```
Input: "Go to live"
→ Extract: "live"
→ Database: No mapping found
→ Fuzzy match: ["live_tv", "live_radio"]
→ Show dialog → User selects "live_tv"
→ Save to DB: "live" → "live_tv"
→ AI call with corrected prompt
→ Time: 4.2s (AI) + user interaction
→ Next time: Becomes Scenario 2 (automatic!)
```

**Scenario 4: Single Fuzzy Match (Auto-correct)**
```
Input: "Navigate to hom"  (typo)
→ Extract: "hom"
→ Fuzzy match: ["home"] (only 1 match, high confidence)
→ Auto-correct: "hom" → "home"
→ Generate: START → navigation_1:home → SUCCESS
→ Time: 300ms, Cost: $0
```

### API Response Examples

**Clear (no issues):**
```json
{
  "status": "clear",
  "prompt": "Navigate to home"
}
```

**Auto-corrected:**
```json
{
  "status": "auto_corrected",
  "original_prompt": "Go to hom",
  "corrected_prompt": "Go to home",
  "corrections": [
    {"from": "hom", "to": "home", "source": "fuzzy"}
  ]
}
```

**Needs disambiguation:**
```json
{
  "status": "needs_disambiguation",
  "original_prompt": "Navigate to live",
  "ambiguities": [
    {
      "original": "live",
      "suggestions": ["live_tv", "live_radio"]
    }
  ]
}
```

---

## Device Integration

### Device Setup

**Device must have:**
1. `navigation_executor` - For node resolution, path finding
2. `testcase_executor` - For actions, verifications
3. `ai_builder` - AIGraphBuilder instance

**Initialization:**
```python
from backend_host.src.services.ai import AIGraphBuilder

device.ai_builder = AIGraphBuilder(device)
```

---

## Troubleshooting

### "Device does not have AIGraphBuilder initialized"

**Check:**
1. Device registered in `current_app.host_devices`
2. Device has `ai_builder` attribute
3. `ai_builder` is not None

**Fix:**
```python
# In device initialization
device.ai_builder = AIGraphBuilder(device)
```

### Labels not following convention

**This is expected!**
- Labels are enforced in post-processing
- AI might return wrong format initially
- `_enforce_labels()` corrects all labels

### Transitions not embedded

**Check:**
1. Navigation executor available
2. Unified graph loaded
3. Target nodes exist in navigation list

**Debug:**
```python
# Check navigation executor
device.navigation_executor.get_available_nodes(...)

# Check path resolution
device.navigation_executor.get_navigation_path(target_node_id=...)
```

---

## Code Examples

### Generate Simple Graph

```python
# In route handler
device = current_app.host_devices['device1']

result = device.ai_builder.generate_graph(
    prompt="Go to live TV",
    userinterface_name="horizon_android_mobile",
    team_id="abc123"
)

if result['success']:
    graph = result['graph']
    print(f"Generated {len(graph['nodes'])} nodes")
```

### Custom Context

```python
# Pre-load and cache context
ai_builder._load_context(
    userinterface_name="horizon_android_mobile",
    current_node_id=None,
    team_id="abc123"
)

# Now generate (uses cached context)
result = ai_builder.generate_graph(...)
```

### Clear Cache

```python
# Clear context cache (force reload)
device.ai_builder.clear_context_cache()
```

---

## Related Files

**Core Implementation:**
- `backend_host/src/services/ai/ai_builder.py` - Main AIGraphBuilder class (~600 lines)
- `backend_host/src/lib/utils/graph_utils.py` - Pure graph utilities (~200 lines)

**HTTP Routes:**
- `backend_host/src/routes/host_ai_routes.py` - `/host/ai/generatePlan` endpoint
- `backend_server/src/routes/server_ai_routes.py` - Proxy to host

**Frontend:**
- `frontend/src/hooks/testcase/useTestCaseAI.ts` - API client
- `frontend/src/hooks/pages/useTestCaseBuilderPage.ts` - State management
- `frontend/src/components/testcase/builder/AIGenerationResultPanel.tsx` - Results UI
- `frontend/src/components/testcase/ai/AIModePanel.tsx` - Input panel

**Database (Implemented):**
- `shared/src/lib/database/ai_graph_cache_db.py` - **Graph caching (MANDATORY)**
  - `create_ai_graph_cache_table()` - Schema creation
  - `get_graph_by_fingerprint()` - Cache lookup
  - `store_graph()` - Cache storage
  - `cleanup_old_graphs()` - 90-day cleanup

**Database (TODO - Not Used Yet):**
- `shared/src/lib/database/ai_prompt_disambiguation_db.py` - Learned mappings
  - For future preprocessing/disambiguation
  - Schema exists, integration pending

---

## Database Files

### `ai_graph_cache_db.py` (Implemented)

**Purpose:** Store and retrieve generated graphs to avoid redundant AI calls.

**Key Functions:**
```python
# Cache lookup (step 1)
cached = get_graph_by_fingerprint(fingerprint, team_id)
if cached:
    return cached  # Instant response

# Cache storage (after generation)
store_graph(
    fingerprint=fingerprint,
    original_prompt=prompt,
    device_model=device.model,
    userinterface_name=userinterface_name,
    available_nodes=context['nodes'],
    graph=graph,
    analysis=analysis,
    team_id=team_id
)

# Periodic cleanup (cron job)
cleanup_old_graphs(team_id, days_old=90)
```

**Performance Impact:**
- Cache HIT: 500ms (no AI call)
- Cache MISS: 4-7s (full generation)
- **90% cost savings** for repeated prompts

### `ai_prompt_disambiguation_db.py` (TODO)

**Purpose:** Store user disambiguation choices for future automatic mapping.

**Key Functions (not implemented yet):**
```python
# Check for learned mapping
mapping = get_disambiguation(team_id, "live")
if mapping:
    prompt = prompt.replace("live", mapping['resolved_value'])

# Store new mapping after user selection
store_disambiguation(team_id, "live", "live_tv")

# Auto-apply next time
```

**Integration Points (pending):**
1. In `_preprocess_prompt()` - Apply learned mappings
2. After user disambiguation - Store choice
3. Cleanup - Remove stale mappings

---

## Clean Architecture Principles

✅ **Single Responsibility:**
- `AIGraphBuilder` - Orchestration only
- `graph_utils.py` - Pure functions only
- Routes - HTTP handling only

✅ **No Legacy Code:**
- No plan-based logic
- No backward compatibility
- Clean slate implementation

✅ **Separation of Concerns:**
- Business logic in `services/`
- Utilities in `lib/utils/`
- Database in `shared/database/`

✅ **Testability:**
- Pure functions easy to test
- Clear inputs/outputs
- No hidden state

---

**Last Updated:** 2025-10-26
**Version:** 1.0.0
**Status:** Production Ready

