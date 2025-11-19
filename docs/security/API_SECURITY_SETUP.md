# API Security Setup Guide

## 🔐 Security Implementation Complete

API Key authentication has been added to protect all `/host/*` routes.

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

```bash
# Restart backend_host
sudo systemctl restart backend_host

# Restart backend_server
sudo systemctl restart backend_server
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

### 1. **Global API Key Protection** (backend_host)
- All `/host/*` requests require `X-API-Key` header
- Invalid/missing keys return 401 Unauthorized
- Logged for security auditing

### 2. **PyAutoGUI Command Filtering** (backend_host)
- Blocks dangerous commands (`rm -rf`, `sudo`, `shutdown`)
- Blocks sensitive file access (`.env`, `/etc/passwd`, `.ssh`)
- Blocks malicious applications (`bash`, `rm`, `systemctl`)
- Blocks directory traversal (`../../../`)

### 3. **Automatic API Key Forwarding** (backend_server)
- All proxy functions include API key in requests
- `proxy_to_host()` - Updated ✓
- `proxy_to_host_with_params()` - Updated ✓
- `proxy_to_host_direct()` - Updated ✓

---

## How It Works

```
┌─────────────┐                  ┌─────────────────┐                  ┌──────────────┐
│   Frontend  │                  │  Backend_Server │                  │ Backend_Host │
│   (Browser) │                  │  (Main API)     │                  │  (Hardware)  │
└──────┬──────┘                  └────────┬────────┘                  └──────┬───────┘
       │                                  │                                   │
       │  Request                         │                                   │
       │─────────────────────────────────>│                                   │
       │                                  │                                   │
       │                                  │  Proxy + X-API-Key                │
       │                                  │──────────────────────────────────>│
       │                                  │                                   │
       │                                  │                                   │ Validate API Key
       │                                  │                                   │ ✓ Valid → Process
       │                                  │                                   │ ✗ Invalid → 401
       │                                  │                                   │
       │                                  │  Response                         │
       │                                  │<──────────────────────────────────│
       │  Response                        │                                   │
       │<─────────────────────────────────│                                   │
       │                                  │                                   │
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

1. **shared/src/lib/utils/auth_utils.py** - NEW
   - API key validation logic

2. **backend_host/src/app.py** - UPDATED
   - Added global `@app.before_request` for API key checking

3. **backend_host/src/controllers/desktop/pyautogui.py** - UPDATED
   - Added command/file/app whitelisting/blacklisting
   - Security validation methods

4. **backend_server/src/lib/utils/route_utils.py** - UPDATED
   - Added API key to all proxy functions

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

