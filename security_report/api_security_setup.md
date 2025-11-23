# API Security Setup Guide

## 🔐 Clean Centralized Architecture

API Key authentication uses a **single source of truth** pattern - one place to validate (host), one place to inject (server).

### Architecture Pattern

**Host Side**: Decorator validates all incoming requests  
**Server Side**: Centralized `call_host()` injects API key on all outgoing requests  
**Result**: Zero duplication, single source of truth

---

## Quick Setup (3 Steps)

### 1️⃣ Generate API Key

Run this command to generate a secure random API key:

```bash
python3 -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"
```

**Example output:**
```
API_KEY=xK7mP3qN9vL2wR5tY8uJ1sA4bC6dE0fGhI-jKlMnOpQr
```

### 2️⃣ Add to `.env` File

Add the generated API key to your **project root `.env` file**:

```bash
# API Key for backend_host authentication
API_KEY=your-api-key
```

### 3️⃣ Restart Services

**For Raspberry Pi (systemd services):**
```bash
# Restart backend_host
sudo systemctl restart backend_host

# Restart backend_server
sudo systemctl restart backend_server
```

**For Hetzner/Docker deployment:**
```bash
# The setup.sh script automatically extracts API_KEY from .env
cd setup/docker/hetzner_custom
./setup.sh  # Re-run to regenerate host .env files with API_KEY
./launch.sh  # Restart containers
```

---

## What Was Protected?

### ✅ **All Backend_Host Routes** (`/host/*`)
- `/host/desktop/pyautogui` ⚠️ **HIGH RISK** - Now secured with PyAutoGUI command filtering
- `/host/desktop/bash` ⚠️ **HIGH RISK**
- `/host/remote/*` - Device control
- `/host/av/*` - Audio/video operations
- `/host/power/*` - Device power control
- `/host/verification/*` - All verification endpoints
- `/host/ai/*` - AI execution
- `/host/actions/*` - Action execution
- ...and 22 more routes

### ✅ **MCP Routes** (`/server/mcp/*`)
- Already protected with Bearer token (no changes needed)

---

## Security Features Implemented

### 1. **Global API Key Validation** (backend_host)
- Flask `@app.before_request` decorator validates all `/host/*` requests
- Invalid/missing keys return 401 Unauthorized
- Located: `backend_host/src/app.py → setup_api_authentication()`

### 2. **Centralized API Key Injection** (backend_server)
- Single `call_host()` function in `shared/src/lib/utils/build_url_utils.py`
- **Automatically injects `X-API-Key` header** on ALL server→host calls
- Eliminates duplicated `os.getenv('API_KEY')` across 50+ files

### 3. **How It Works**

**Server Side (Injection)**:
```python
# ONE place handles ALL host calls
from shared.src.lib.utils.build_url_utils import call_host

# API key injection is automatic - no manual headers needed
response_data, status = call_host(
    host_info,
    '/host/monitoring/latest-json',
    method='POST',
    data={'device_id': 'device1'}
)
```

**Host Side (Validation)**:
```python
# ONE decorator checks ALL /host/* routes
@app.before_request
def check_api_key():
    if request.path.startswith('/host/'):
        is_valid, error = validate_api_key()
        if not is_valid:
            return jsonify(error), 401
```

---

## Architecture Diagram

```
┌─────────────┐                  ┌─────────────────┐                  ┌──────────────┐
│   Frontend  │                  │  Backend_Server │                  │ Backend_Host │
│   (Browser) │                  │  (Main API)     │                  │  (Hardware)  │
└──────┬──────┘                  └────────┬────────┘                  └──────┬───────┘
       │                                  │                                   │
       │  Request                         │                                   │
       │─────────────────────────────────>│                                   │
       │                                  │                                   │
       │                                  │  call_host(host_info, endpoint)   │
       │                                  │  ↓ Automatic X-API-Key injection  │
       │                                  │──────────────────────────────────>│
       │                                  │                                   │
       │                                  │                                   │ @app.before_request
       │                                  │                                   │ ↓ Validate API Key
       │                                  │                                   │ ✓ Valid → Process
       │                                  │                                   │ ✗ Invalid → 401
       │                                  │                                   │
       │                                  │  Response                         │
       │                                  │<──────────────────────────────────│
       │  Response                        │                                   │
       │<─────────────────────────────────│                                   │
```

---

## Testing

### ✅ **Test 1: Valid API Key (Should Work)**
```bash
curl -X POST http://localhost:6109/host/desktop/pyautogui/executeCommand \
  -H "X-API-Key: xK7mP3qN9vL2wR5tY8uJ1sA4bC6dE0fGhI-jKlMnOpQr" \
  -H "Content-Type: application/json" \
  -d '{"command": "execute_pyautogui_click", "params": {"x": 100, "y": 100}}'
```

**Expected:** `{"success": true, ...}`

### ❌ **Test 2: No API Key (Should Fail)**
```bash
curl -X POST http://localhost:6109/host/desktop/pyautogui/executeCommand \
  -H "Content-Type: application/json" \
  -d '{"command": "execute_pyautogui_click", "params": {"x": 100, "y": 100}}'
```

**Expected:** `{"error": "Authentication required", "message": "X-API-Key header is required"}` (401)

### ❌ **Test 3: Dangerous Command (Should Fail)**
```bash
curl -X POST http://localhost:6109/host/desktop/pyautogui/executeCommand \
  -H "X-API-Key: xK7mP3qN9vL2wR5tY8uJ1sA4bC6dE0fGhI-jKlMnOpQr" \
  -H "Content-Type: application/json" \
  -d '{"command": "execute_pyautogui_type", "params": {"text": "cat .env"}}'
```

**Expected:** `{"success": false, "error": "SECURITY BLOCK: Text references blocked file pattern: ..."}` (200 but failed)

---

## Security Best Practices

### ✅ **DO:**
- Keep API key secret (never commit to git)
- Use different API keys for dev/staging/production
- Rotate API keys periodically (every 90 days)
- Monitor logs for failed authentication attempts

### ❌ **DON'T:**
- Share API key in code/documentation
- Use simple/guessable API keys
- Store API key in frontend code
- Disable security features

---

## Troubleshooting

### Problem: "Authentication required" error

**Cause:** API_KEY not set or not matching

**Solution:**
1. Check `.env` file has `API_KEY=...`
2. Restart services after adding API_KEY
3. Verify same API_KEY in both backend_host and backend_server

### Problem: "PyAutoGUI command execution error"

**Cause:** Security filters blocking legitimate commands

**Solution:**
1. Check logs: `journalctl -u backend_host -n 50`
2. Review blocked patterns in `backend_host/src/controllers/desktop/pyautogui.py`
3. Adjust patterns if needed (be careful!)

---

## Files Modified

### Core Architecture (Single Source of Truth)

1. **shared/src/lib/utils/build_url_utils.py** - NEW FUNCTION
   - Added `call_host()` - centralized server→host call handler
   - **Automatic API key injection** (line 84-86)
   - Handles URL building, timeouts, error handling

2. **backend_server/src/lib/utils/route_utils.py** - REFACTORED
   - All proxy functions now use `call_host()`
   - Eliminated duplicate API key logic (150+ lines removed)

3. **backend_host/src/app.py** - UNCHANGED
   - `setup_api_authentication()` decorator already in place
   - Validates all `/host/*` requests

### Files Using Centralized Architecture

4. **backend_server/src/routes/server_monitoring_routes.py**
   - Uses `proxy_to_host_with_params()` → automatic API key ✓

5. **backend_server/src/routes/auto_proxy.py**
   - Uses `proxy_to_host_with_params()` → automatic API key ✓

6. **All 45+ other server routes**
   - Inherit centralized behavior via `route_utils.py` ✓

### Migration Example

**Before** (duplicated in every file):
```python
api_key = os.getenv('API_KEY')
headers = {'X-API-Key': api_key} if api_key else {}
response = requests.post(host_url, json=data, headers=headers, timeout=30)
result = response.json()
```

**After** (centralized):
```python
from shared.src.lib.utils.build_url_utils import call_host
result, status = call_host(host_info, '/host/endpoint', data=data)
```

---

## Next Steps (Optional)

For even stronger security, consider:

1. **JWT Tokens** - User-level authentication with expiration
2. **Rate Limiting** - Prevent brute force attacks
3. **IP Whitelist** - Only allow specific IPs
4. **Audit Logging** - Track all API calls to database
5. **2FA** - Two-factor authentication for admin actions

---

## Support

If you have questions or issues:
1. Check logs: `journalctl -u backend_host` and `journalctl -u backend_server`
2. Review this guide
3. Contact your system administrator

