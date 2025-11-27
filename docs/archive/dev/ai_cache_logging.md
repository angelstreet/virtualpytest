# AI Plan Cache Logging - Explicit Messages

## Overview

Updated cache logging to make it **crystal clear** that cache misses are **normal behavior**, not errors. The "0 rows" message from Supabase is now properly contextualized.

---

## New Log Output Examples

### ✅ **Cache HIT (Exact Match)**

```
[@ai_plan_cache] Checking cache for fingerprint: a3f5c9d2... (prompt: 'go to live TV...')
[@ai_plan_generation_db] ✓ Cache MISS for fingerprint a3f5c9d2... (normal - no cached plan exists yet)
[@ai_plan_cache] No exact match found. Trying compatible plans...
[@ai_plan_cache] ✓ Cache HIT (exact match)! Using cached plan: a3f5c9d2...
[@ai_executor] ✓ Using cached plan (no AI call needed): a3f5c9d2...
```

**What this means:** Found an exact match! No AI call needed, immediate execution.

---

### ✅ **Cache HIT (Compatible Plan)**

```
[@ai_plan_cache] Checking cache for fingerprint: b4e6a8c1... (prompt: 'navigate to live TV...')
[@ai_plan_generation_db] ✓ Cache MISS for fingerprint b4e6a8c1... (normal - no cached plan exists yet)
[@ai_plan_cache] No exact match found. Trying compatible plans...
[@ai_plan_cache] ✓ Cache HIT (compatible plan)! Fingerprint: a3f5c9d2... (success rate: 0.95)
[@ai_executor] ✓ Using cached plan (no AI call needed): a3f5c9d2...
```

**What this means:** Exact fingerprint didn't match, but found a compatible plan with similar prompt/context. Uses the compatible plan instead.

---

### ✅ **Cache MISS (Normal - First Execution)**

```
[@ai_plan_cache] Checking cache for fingerprint: c5f7b9d3... (prompt: 'go to replay section...')
[@ai_plan_generation_db] ✓ Cache MISS for fingerprint c5f7b9d3... (normal - no cached plan exists yet)
[@ai_plan_cache] No exact match found. Trying compatible plans...
[@ai_plan_cache] ✓ Cache MISS (normal) - No cached plan exists for this prompt+context combination.
[@ai_plan_cache]   → Will generate NEW plan with AI and cache it after successful execution
[@ai_executor] ✓ Cache miss (normal) - Will generate new plan with AI
[@ai_executor] 🤖 Generating new plan with AI (will be cached after successful execution for future reuse)
[AI generates plan and executes]
[@ai_plan_cache] ✓ Stored successful plan in cache: c5f7b9d3... (will be reused for future identical requests)
```

**What this means:** First time running this prompt+context combo. Generates new plan, executes it, and caches it for future reuse.

---

### ✅ **Cache MISS with Caching Disabled**

```
[@ai_plan_cache] Checking cache for fingerprint: d6g8c0e4... (prompt: 'test one-time action...')
[@ai_plan_generation_db] ✓ Cache MISS for fingerprint d6g8c0e4... (normal - no cached plan exists yet)
[@ai_plan_cache] No exact match found. Trying compatible plans...
[@ai_plan_cache] ✓ Cache MISS (normal) - No cached plan exists for this prompt+context combination.
[@ai_plan_cache]   → Will generate NEW plan with AI and cache it after successful execution
[@ai_executor] ✓ Cache miss (normal) - Will generate new plan with AI
[@ai_executor] 🤖 Generating new plan with AI (caching disabled - plan will NOT be saved)
[AI generates plan and executes]
[No storage message - plan not cached]
```

**What this means:** `use_cache=False` was set, so plan is generated fresh and NOT stored.

---

### ❌ **Actual Database Error**

```
[@ai_plan_cache] Checking cache for fingerprint: e7h9d1f5... (prompt: 'some action...')
[@ai_plan_generation_db] ❌ Database error getting plan: Connection timeout after 30s
[@ai_plan_cache] Error finding cached plan: Connection timeout after 30s
[@ai_executor] ✓ Cache miss (normal) - Will generate new plan with AI
```

**What this means:** Real error (connection, permission, etc.). System falls back to generating new plan.

---

## Key Message Indicators

### ✓ Symbols Meaning:
- **✓ Cache HIT** = Found and using cached plan (good!)
- **✓ Cache MISS (normal)** = No cache, will generate (expected!)
- **✓** prefix = Normal operation, everything working as designed

### ❌ Symbols Meaning:
- **❌ Database error** = Real problem (connection, permissions, etc.)
- **❌ Failed to store** = Couldn't save plan to cache

### 🤖 Emoji Meaning:
- **🤖** = AI is being called to generate a plan

---

## Understanding Fingerprints

### Full vs Abbreviated Fingerprints

**Full:** `a3f5c9d2e8b4f7a1c3e5d9b2f4a6c8e0` (32 characters - MD5 hash)  
**Abbreviated:** `a3f5c9d2...` (first 8 characters for readability)

Abbreviated fingerprints are used in logs to reduce noise while still being traceable.

---

## Cache Miss Reasons (All Normal)

A cache miss with "0 rows" is **EXPECTED** when:

1. **First Execution:** Never run this exact prompt+context before
2. **New Available Nodes:** Navigation tree changed (added/removed nodes)
3. **Different Device/UI:** Different device_model or userinterface_name
4. **Prompt Variation:** Phrase doesn't normalize to existing cached prompts
5. **Fresh Database:** Cache table was recently cleared/migrated
6. **Different Team:** Caches are isolated per team_id

**All of these are normal operations, not errors!**

---

## Troubleshooting

### If You See Many Cache Misses:

1. **Check if prompt varies slightly each time:**
   - ❌ `"go to live"`, `"go to the live TV"`, `"navigate to live"`
   - ✅ Use consistent phrasing for better cache hits

2. **Check if available_nodes list changes:**
   - Navigation tree modifications affect fingerprint
   - Use `journalctl` to see what nodes are available in each request

3. **Check team_id is consistent:**
   - Each team has isolated cache
   - Verify requests use same team_id

### If You See Actual Errors:

Look for **❌** symbols without "(normal)" qualifier:
- `❌ Database error getting plan:` = Database connection/permission issue
- `❌ Failed to store plan in cache:` = Database write issue

---

## Performance Impact

### Cache HIT:
- ⚡ **~50-200ms** - No AI call, immediate execution
- 💰 **$0** - No AI API costs
- 🎯 **Consistent** - Uses proven successful plans

### Cache MISS (First Time):
- 🐢 **~2-5 seconds** - AI generation + execution
- 💰 **~$0.01-0.05** - AI API costs
- 🎯 **Then cached** - Subsequent runs will hit cache

---

## Configuration

Cache behavior controlled by `use_cache` parameter:

```python
# Enable caching (recommended for production)
result = ai_executor.execute(
    prompt="go to live TV",
    use_cache=True  # Default
)

# Disable caching (for testing/debugging)
result = ai_executor.execute(
    prompt="test temporary action",
    use_cache=False
)
```

---

## Related Files

- `shared/src/lib/database/ai_plan_generation_db.py` - Database operations
- `shared/src/lib/executors/ai_plan_cache.py` - Cache logic
- `shared/src/lib/executors/ai_executor.py` - Execution orchestration
- `setup/db/schema/009_ai_plan_generation.sql` - Database schema

