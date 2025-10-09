# AI Test Case Analysis Host Selection Fix

## Problem

When calling `/server/ai-testcase/analyze`, the endpoint was failing with:
```json
{
    "error": "host_name required in request body or query parameters",
    "success": false
}
```

## Root Cause

### Architecture Issue

The system has this architecture:
- **Frontend** → calls → **Backend Server** → proxies to → **Backend Host** (which has AI executors)
- All AI operations require a **host** because AI executors live on host machines
- `proxy_to_host_with_params()` requires `host_name` to find the target host

### The Bug

In `backend_server/src/routes/server_ai_testcase_routes.py`:

**Before:**
```python
# Line 83-92 (and similar in lines 221-230, 421-430)
plan_response, _ = proxy_to_host_with_params(
    '/host/ai/generatePlan', 
    'POST', 
    {
        'prompt': prompt,
        'context': context,
        'team_id': team_id
        # ❌ NO host_name provided!
    },
    {}
)
```

The backend server was calling `proxy_to_host_with_params()` WITHOUT providing `host_name` in the request data, causing the proxy function to fail when trying to extract it.

## Solution

### Why This Approach is Correct

Test case analysis is a **GLOBAL operation** that analyzes compatibility across ALL userinterfaces. It doesn't matter which host performs this analysis - any available host with an AI executor can do it.

**After:**
```python
# Get first available host for AI analysis (global operation doesn't need specific host)
from backend_server.src.lib.utils.server_utils import get_host_manager
host_manager = get_host_manager()
all_hosts = host_manager.get_all_hosts()

if not all_hosts:
    return jsonify({
        'success': False,
        'error': 'No hosts available for AI analysis. Please ensure at least one host is running.'
    }), 503

# Pick first available host (doesn't matter which one for global analysis)
first_host_name = list(all_hosts.keys())[0]
print(f"[@server_ai_testcase] Using host '{first_host_name}' for AI analysis")

# Now include host_name in proxy calls
plan_response, _ = proxy_to_host_with_params(
    '/host/ai/generatePlan', 
    'POST', 
    {
        'prompt': prompt,
        'context': context,
        'team_id': team_id,
        'host_name': first_host_name  # ✅ NOW PROVIDED!
    },
    {}
)
```

## Files Changed

### Backend Server
- **`backend_server/src/routes/server_ai_testcase_routes.py`**
  - `/analyze` endpoint (line 58-105): Added host selection and `host_name` parameter
  - `/generate` endpoint (line 219-258): Added host selection and `host_name` parameter  
  - `/feasibilityCheck` endpoint (line 442-472): Added host selection and `host_name` parameter

### Frontend (Kept Existing Correct Code)
- **`frontend/src/components/testcase/AITestCaseGenerator.tsx`**: No changes needed - correctly calls `/server/ai-testcase/analyze` with just `{ prompt }`
- **`frontend/src/hooks/useAI.ts`**: Previously fixed to:
  - Use `/server/*` endpoints instead of `/host/*` (auto-proxy requirement)
  - Include `host_name` + `device_id` for device-specific AI operations

## Flow After Fix

```
1. User: "Go to live and check audio"
   ↓
2. Frontend: POST /server/ai-testcase/analyze
   Body: { prompt: "Go to live..." }
   ↓
3. Backend Server (server_ai_testcase_routes.py):
   - Gets all registered hosts from HostManager
   - Picks first available host (e.g., "rpi-capture-1")
   - For EACH userinterface:
   ↓
4. Backend Server calls AI analysis:
   proxy_to_host_with_params('/host/ai/generatePlan', ...)
   Body: { prompt, context, team_id, host_name: "rpi-capture-1" }
   ↓
5. proxy_to_host_with_params:
   - Extracts host_name from request body ✅
   - Looks up host info in HostManager ✅
   - Builds URL: https://rpi-capture-1.local:6109/host/ai/generatePlan
   ↓
6. Backend Host: Runs AI executor analysis
   ↓
7. Returns: Compatibility matrix to frontend
```

## Key Principles

1. **Global operations** (test case analysis) can use ANY available host
2. **Device-specific operations** (AI execution, plan generation for a specific device) must use the host that controls that device
3. ALL operations that call `proxy_to_host_with_params()` MUST provide `host_name` in the request data
4. Frontend calls `/server/*` endpoints (auto-proxy), NOT `/host/*` directly

## Testing

Test the fix by:
1. Ensure at least one host is running and registered with the server
2. Open Test Case Editor in frontend
3. Click "AI Generate" button
4. Enter prompt: "Go to live and check audio"
5. Should successfully analyze compatibility across all interfaces ✅

Error conditions:
- If NO hosts are available: Returns 503 with clear error message
- If AI analysis fails: Returns specific error per interface in compatibility matrix

