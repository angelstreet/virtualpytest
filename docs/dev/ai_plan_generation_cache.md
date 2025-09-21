# AI Plan Generation Cache System

## Overview

The AI Plan Generation Cache System is designed to intelligently store, reuse, and optimize AI-generated execution plans to reduce costs, improve performance, and learn from successful patterns over time.

## Table of Contents

- [System Architecture](#system-architecture)
- [Database Schema](#database-schema)
- [Prompt Normalization](#prompt-normalization)
- [Cache Strategy](#cache-strategy)
- [Implementation Plan](#implementation-plan)
- [API Reference](#api-reference)
- [Performance Metrics](#performance-metrics)
- [Maintenance](#maintenance)

## System Architecture

### Components

1. **Database Cache** (`ai_plan_generation` table)
   - Persistent storage for all generated plans
   - Tracks success rates and performance metrics
   - Shared across all users and sessions

2. **Server Cache** (In-memory)
   - Loaded at startup from database
   - Fast lookup for active plans
   - Indexed by normalized prompts

3. **Plan Matcher**
   - Finds compatible cached plans
   - Evaluates context compatibility
   - Ranks plans by success probability

4. **Prompt Normalizer**
   - Converts prompt variations into standard form
   - Enables plan reuse across different phrasings
   - Extracts intent and target information

### Flow Diagram

```
User Request → Check use_cache flag → Prompt Normalization → Cache Lookup
     ↓                    ↓                      ↓                ↓
     ↓              use_cache=false       Generate Fingerprint   Found Compatible?
     ↓                    ↓                      ↓                ↓
     ↓              Skip Cache Entirely   Check Server Cache     Reuse Plan
     ↓                    ↓                      ↓                ↓
     ↓              Generate New Plan     Cache Miss       Plan Execution
     ↓                    ↓                      ↓                ↓
     ↓              Execute Plan          Generate New Plan      Success?
     ↓                    ↓                      ↓                ↓
     ↓              DON'T STORE           Execute Plan           Update Metrics
     ↓                                          ↓                ↓
     ↓                                    Success + use_cache    Store ONLY if:
     ↓                                    + !debug_mode?         - Success = true
     ↓                                          ↓                - use_cache = true  
     ↓                                     Store in Database     - debug_mode = false
     ↓                                                           - All steps completed
     └─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation Logic

```python
def execute_prompt_with_cache(self, prompt: str, userinterface_name: str, team_id: str,
                             use_cache: bool = True, debug_mode: bool = False, **kwargs):
    """Enhanced execute_prompt with safety controls"""
    
    # 1. Early exit if caching disabled
    if not use_cache:
        print("[@ai_executor] Cache disabled by user - generating fresh plan")
        plan_dict = self.generate_plan(prompt, context, current_node_id)
        result = self._execute_plan_sync(plan_dict, context)
        # DON'T STORE - user explicitly disabled caching
        return result
    
    # 2. Try cache lookup (only if use_cache=True)
    context = self._load_context(userinterface_name, current_node_id, team_id)
    cached_plans = self.plan_cache.find_matching_plans(prompt, context)
    
    if cached_plans and self.plan_cache.should_reuse_plan(cached_plans[0], context):
        print("[@ai_executor] Using cached plan")
        cached_plan = cached_plans[0]
        result = self._execute_plan_sync(cached_plan.plan, context)
        
        # Update metrics for cached plan
        self.plan_cache.update_metrics(cached_plan.fingerprint, result.success, result.total_time_ms)
        return result
    
    # 3. Generate new plan
    print("[@ai_executor] Generating new plan")
    plan_dict = self.generate_plan(prompt, context, current_node_id)
    result = self._execute_plan_sync(plan_dict, context)
    
    # 4. CONDITIONAL STORAGE - only store if ALL conditions met
    should_store = (
        result.success and                    # Must be successful
        use_cache and                         # User allows caching
        not debug_mode and                    # Not in debug mode
        len(result.step_results) > 0 and      # Has actual steps
        all(r.get('success') for r in result.step_results)  # All steps succeeded
    )
    
    if should_store:
        fingerprint = generate_task_fingerprint(prompt, context)
        self.plan_cache.store_successful_plan(fingerprint, prompt, context, plan_dict, result)
        print("[@ai_executor] Stored successful plan in cache")
    else:
        reasons = []
        if not result.success: reasons.append("execution failed")
        if not use_cache: reasons.append("caching disabled")
        if debug_mode: reasons.append("debug mode active")
        print(f"[@ai_executor] NOT storing plan: {', '.join(reasons)}")
    
    return result
```

## Database Schema

### Table: `ai_plan_generation`

```sql
CREATE TABLE ai_plan_generation (
    -- Primary identification
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    fingerprint VARCHAR(32) UNIQUE NOT NULL, -- MD5 hash for fast lookups
    
    -- Prompt information
    original_prompt TEXT NOT NULL,
    normalized_prompt VARCHAR(255) NOT NULL, -- For indexing and grouping
    intent_type VARCHAR(50), -- 'navigation', 'action', 'search', etc.
    target_name VARCHAR(100), -- Extracted target like 'replay', 'home_replay'
    
    -- Context signature
    device_model VARCHAR(100) NOT NULL,
    userinterface_name VARCHAR(100) NOT NULL,
    available_nodes JSONB NOT NULL, -- Array of available navigation nodes
    context_signature JSONB NOT NULL, -- Full context hash for compatibility
    
    -- Plan data
    plan JSONB NOT NULL, -- The AI-generated plan with steps
    plan_complexity INTEGER DEFAULT 0, -- Number of steps
    requires_reassessment BOOLEAN DEFAULT FALSE, -- Has navigation_reassessment steps
    
    -- Performance metrics
    success_rate DECIMAL(5,4) DEFAULT 0.0000, -- 0.0000 to 1.0000
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_execution_time_ms INTEGER DEFAULT 0,
    
    -- Usage tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_success TIMESTAMP WITH TIME ZONE,
    last_failure TIMESTAMP WITH TIME ZONE,
    
    -- Failure analysis
    failure_reasons JSONB DEFAULT '[]'::jsonb, -- Array of failure reason strings
    
    -- Team/user context (for multi-tenancy)
    team_id UUID REFERENCES teams(id),
    created_by UUID REFERENCES users(id),
    
    -- Metadata
    version INTEGER DEFAULT 1, -- For plan versioning
    tags JSONB DEFAULT '[]'::jsonb, -- For categorization
    notes TEXT -- Optional human notes
);
```

### Indexes

```sql
-- Primary lookup indexes
CREATE INDEX idx_ai_plan_generation_fingerprint ON ai_plan_generation(fingerprint);
CREATE INDEX idx_ai_plan_generation_normalized_prompt ON ai_plan_generation(normalized_prompt);

-- Context-based lookups
CREATE INDEX idx_ai_plan_generation_device_interface ON ai_plan_generation(device_model, userinterface_name);
CREATE INDEX idx_ai_plan_generation_team ON ai_plan_generation(team_id);

-- Performance-based queries
CREATE INDEX idx_ai_plan_generation_success_rate ON ai_plan_generation(success_rate DESC, execution_count DESC);
CREATE INDEX idx_ai_plan_generation_last_used ON ai_plan_generation(last_used DESC);

-- Composite index for common queries
CREATE INDEX idx_ai_plan_generation_lookup ON ai_plan_generation(normalized_prompt, device_model, userinterface_name, success_rate DESC);

-- GIN index for JSONB searches
CREATE INDEX idx_ai_plan_generation_available_nodes ON ai_plan_generation USING GIN(available_nodes);
CREATE INDEX idx_ai_plan_generation_plan ON ai_plan_generation USING GIN(plan);
```

## Prompt Normalization

### Purpose
Convert different user inputs that represent the same task into a standardized form for cache matching.

### Examples

| Original Prompt | Normalized Prompt | Intent | Target |
|----------------|-------------------|---------|---------|
| "go to replay" | "navigation_replay" | navigation | replay |
| "navigate to replay" | "navigation_replay" | navigation | replay |
| "take me to the replay section" | "navigation_replay" | navigation | replay |
| "click on settings" | "action_settings" | action | settings |
| "press the OK button" | "action_ok" | action | ok |

### Normalization Process

```python
def normalize_prompt_advanced(prompt: str) -> str:
    """Advanced prompt normalization pipeline"""
    
    # 1. Basic cleanup
    normalized = prompt.lower().strip()
    
    # 2. Remove politeness words
    politeness_words = ['please', 'can you', 'could you', 'would you', 'i want to', 'i need to']
    for word in politeness_words:
        normalized = normalized.replace(word, '').strip()
    
    # 3. Classify intent
    intent = classify_intent(normalized)
    
    # 4. Extract target
    target = extract_target(normalized)
    
    # 5. Create standardized format
    return f"{intent}_{target}" if intent and target else normalized
```

### Intent Classification

- **navigation**: go, navigate, take me, show, open, goto
- **action**: click, tap, press, select, touch
- **search**: find, search, look for, locate
- **media**: play, start, stop, pause, resume
- **system**: back, home, exit, quit

## Cache Strategy

### Cache Levels

1. **Server Memory Cache**
   - Loaded at startup
   - Fast O(1) lookups
   - Limited size (top 1000 plans per team)

2. **Database Cache**
   - Persistent storage
   - All historical plans
   - Cleanup policies for maintenance

### Cache Storage Rules

**Plans are ONLY stored when:**
- ✅ Task execution completed fully (all steps executed)
- ✅ Final result shows `success: true`
- ✅ No execution errors or timeouts occurred
- ✅ Cache is enabled for this execution (not disabled by user)

**Plans are NEVER stored when:**
- ❌ Task failed or partially completed
- ❌ User explicitly disabled caching (`use_cache: false`)
- ❌ Execution was interrupted or timed out
- ❌ Testing/debug mode is active

### Cache Hit Decision Matrix

| Condition | Action | Confidence |
|-----------|--------|------------|
| Cache disabled by user | Generate new plan | N/A |
| Exact fingerprint match + success_rate > 80% | Reuse immediately | High |
| Normalized prompt match + context compatible + success_rate > 60% | Reuse with monitoring | Medium |
| Similar intent + partial context match + success_rate > 50% | Consider reuse | Low |
| No matches or success_rate < 50% | Generate new plan | None |

### Context Compatibility

Plans are considered compatible when:
- Device model matches exactly
- User interface matches exactly
- Available nodes have >80% overlap
- No recent failures with same context

## Implementation Plan

### Phase 1: Database Setup ✅
- [x] Create `ai_plan_generation` table
- [x] Add indexes for performance
- [x] Create stored procedures for metrics
- [x] Set up RLS policies

### Phase 2: Core Cache System
- [ ] Implement `DatabasePlanCache` class
- [ ] Implement `ServerPlanCache` class
- [ ] Create prompt normalization functions
- [ ] Add fingerprint generation logic

### Phase 3: AI Executor Integration
- [ ] Modify `execute_prompt()` to accept `use_cache` and `debug_mode` parameters
- [ ] Add cache lookup logic (only if `use_cache=True`)
- [ ] Implement conditional plan storage (only if successful AND `use_cache=True` AND `debug_mode=False`)
- [ ] Add metrics updating after execution
- [ ] Add cache hit/miss logging
- [ ] Add manual plan invalidation endpoints

### Phase 4: Advanced Features
- [ ] Implement semantic similarity matching
- [ ] Add plan versioning system
- [ ] Create cache analytics dashboard
- [ ] Add manual plan curation interface

### Phase 5: Optimization
- [ ] Add cache warming strategies
- [ ] Implement predictive pre-loading
- [ ] Add A/B testing for cache vs fresh generation
- [ ] Performance monitoring and alerting

## API Reference

### AI Executor Cache Integration

```python
def execute_prompt(self, 
                  prompt: str, 
                  userinterface_name: str,
                  team_id: str,
                  current_node_id: Optional[str] = None,
                  async_execution: bool = True,
                  use_cache: bool = True,  # NEW: Allow cache control
                  debug_mode: bool = False) -> Dict[str, Any]:
    """
    Execute AI prompt with optional caching
    
    Args:
        use_cache: If False, skip cache lookup and don't store results
        debug_mode: If True, don't store results even if successful
    """
```

### DatabasePlanCache

```python
class DatabasePlanCache:
    def store_successful_plan(self, fingerprint: str, prompt: str, context: Dict, 
                            plan: Dict, execution_result: ExecutionResult) -> bool:
        """Store plan ONLY if execution was fully successful"""
        
    def get_plan(self, fingerprint: str) -> Optional[CachedPlan]
    def find_compatible_plans(self, prompt: str, context: Dict) -> List[CachedPlan]
    def update_metrics(self, fingerprint: str, success: bool, execution_time: int) -> bool
    def cleanup_old_plans(self, days: int = 90) -> int
    def invalidate_plan(self, fingerprint: str) -> bool  # NEW: Manual plan removal
```

### ServerPlanCache

```python
class ServerPlanCache:
    def __init__(self)
    def load_from_database(self) -> int
    def find_by_normalized_prompt(self, prompt: str, context: Dict) -> List[CachedPlan]
    def is_context_compatible(self, cached_context: Dict, current_context: Dict) -> bool
    def should_reuse_plan(self, cached_plan: CachedPlan, context: Dict) -> bool
```

### Utility Functions

```python
def normalize_prompt_advanced(prompt: str) -> str
def generate_task_fingerprint(prompt: str, context: Dict) -> str
def classify_intent(prompt: str) -> str
def extract_target(prompt: str) -> str
```

## Performance Metrics

### Cache Performance

- **Cache Hit Rate**: Percentage of requests served from cache
- **Cache Miss Rate**: Percentage requiring new AI generation
- **Average Response Time**: Cache hit vs miss response times
- **Storage Efficiency**: Plans stored vs plans reused ratio

### Plan Quality Metrics

- **Success Rate Distribution**: Histogram of plan success rates
- **Execution Time Distribution**: Performance characteristics
- **Failure Pattern Analysis**: Common failure reasons
- **Context Compatibility Score**: How well contexts match

### Business Impact

- **AI Cost Savings**: Reduced API calls to AI providers
- **User Experience**: Faster response times
- **System Learning**: Improvement in success rates over time
- **Resource Utilization**: Database and memory usage

## Maintenance

### Automated Cleanup

```sql
-- Run daily via cron job
SELECT cleanup_plan_cache();
```

**Cleanup Rules:**
- Remove plans with success_rate < 30% and execution_count > 5
- Remove unused plans older than 90 days with success_rate < 70%
- Keep only top 1000 plans per team
- Archive high-value plans before deletion

### Manual Maintenance

**Weekly Tasks:**
- Review top failing plans
- Analyze new prompt patterns
- Update normalization rules
- Check cache hit rates

**Monthly Tasks:**
- Performance optimization review
- Database index maintenance
- Cache size optimization
- Success rate trend analysis

### Monitoring Alerts

- Cache hit rate drops below 40%
- Database storage exceeds 80% capacity
- Average plan success rate drops below 60%
- Unusual failure pattern detected

### Cache Control Examples

#### Frontend/API Usage

```javascript
// Normal execution with caching (default)
const result = await executeAIPrompt({
  prompt: "go to replay",
  userinterface_name: "horizon_android_mobile",
  team_id: "team_123"
  // use_cache: true (default)
});

// Testing/debugging - disable cache completely
const result = await executeAIPrompt({
  prompt: "go to replay",
  userinterface_name: "horizon_android_mobile", 
  team_id: "team_123",
  use_cache: false,  // Don't use or store cache
  debug_mode: true   // Extra safety - never store
});

// Use cache for lookup but don't store results (one-way)
const result = await executeAIPrompt({
  prompt: "go to replay",
  userinterface_name: "horizon_android_mobile",
  team_id: "team_123", 
  use_cache: true,
  debug_mode: true  // Will read cache but won't store new plans
});
```

#### Manual Cache Management

```python
# Invalidate a bad plan that was mistakenly cached
cache.invalidate_plan(fingerprint="abc123def456")

# Check plan before trusting it
cached_plan = cache.get_plan(fingerprint)
if cached_plan.success_rate < 0.7:
    # Don't use this plan, generate fresh
    pass
```

## Configuration

### Environment Variables

```bash
# Cache settings
AI_CACHE_ENABLED=true
AI_CACHE_MAX_MEMORY_PLANS=1000
AI_CACHE_MIN_SUCCESS_RATE=0.5
AI_CACHE_CLEANUP_INTERVAL_HOURS=24
AI_CACHE_STORE_ONLY_SUCCESSFUL=true  # NEW: Only store successful executions

# Performance thresholds
AI_CACHE_HIGH_CONFIDENCE_THRESHOLD=0.8
AI_CACHE_MEDIUM_CONFIDENCE_THRESHOLD=0.6
AI_CACHE_CONTEXT_COMPATIBILITY_THRESHOLD=0.8

# Safety settings
AI_CACHE_DEBUG_MODE_DEFAULT=false
AI_CACHE_ALLOW_MANUAL_INVALIDATION=true
```

### Feature Flags

- `enable_plan_caching`: Master switch for caching system
- `enable_semantic_matching`: Advanced similarity matching
- `enable_predictive_loading`: Pre-load likely plans
- `enable_cache_analytics`: Detailed metrics collection

## Security Considerations

### Data Privacy
- Plans are isolated by team_id using RLS
- No cross-team plan sharing
- Sensitive data in prompts is not logged

### Access Control
- Only team members can access team plans
- Plan creation requires valid team membership
- Metrics updates are authenticated

### Data Retention
- Plans older than 1 year are archived
- Failed plans are cleaned up more aggressively
- User data is anonymized in analytics

## Future Enhancements

### Planned Features
- **Semantic Search**: Find similar plans using embeddings
- **Plan Templates**: Create reusable plan patterns
- **Collaborative Curation**: Team-based plan improvement
- **Cross-Device Learning**: Share successful patterns across device types
- **Predictive Caching**: Pre-generate plans for common workflows

### Research Areas
- **Reinforcement Learning**: Improve plan selection over time
- **Federated Learning**: Learn from multiple deployments
- **Plan Synthesis**: Combine multiple cached plans
- **Context Prediction**: Anticipate context changes

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Status**: Implementation Phase 1 Complete
