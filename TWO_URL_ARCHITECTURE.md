# Two-URL Architecture Implementation

## Overview

This document explains the two-URL architecture implemented to eliminate SSL certificate verification issues (`verify=False`) across the codebase while supporting both same-network and cross-network deployments.

## Problem Statement

Previously, the system had SSL certificate verification issues because:
- All communication used HTTPS URLs through nginx
- Local network hosts used self-signed certificates
- Required `verify=False` in 50+ locations across the codebase
- Created maintenance burden and security concerns

## Solution: Two-URL Approach

Each host now registers with **two URLs** serving different purposes:

### 1. `host_url` - For Browser/Frontend Access (via nginx)
- **Purpose**: Static files (images, videos, streams)
- **Protocol**: HTTPS (via nginx proxy with SSL termination)
- **Used by**: Frontend/Browser
- **Example**: `https://dev.virtualpytest.com/pi4-server`

### 2. `host_api_url` - For Server-to-Server API Calls (direct)
- **Purpose**: Backend API calls between services
- **Protocol**: HTTP (direct connection, no SSL)
- **Used by**: Backend servers calling host APIs
- **Example**: `http://192.168.1.34:6109`

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│ Browser                                         │
│ Uses: host_url (HTTPS via nginx)               │
└────────────────┬────────────────────────────────┘
                 │ HTTPS
                 ▼
┌─────────────────────────────────────────────────┐
│ sunri-pi1 nginx (192.168.1.150)                │
│ SSL Termination                                 │
│ ├─ /pi4/ → http://192.168.1.34 (proxy)         │
│ └─ SSL handled here                             │
└─────────────────────────────────────────────────┘
                 │ HTTP (internal)
                 ▼
┌─────────────────────────────────────────────────┐
│ Backend Server (pi1)                            │
│ Uses: host_api_url (HTTP direct)               │
└────────────────┬────────────────────────────────┘
                 │ HTTP (direct, no nginx)
                 ▼
┌─────────────────────────────────────────────────┐
│ Backend Host (pi4)                              │
│ http://192.168.1.34:6109                        │
└─────────────────────────────────────────────────┘
```

## Environment Variables

### Frontend (sunri-pi1)
```bash
# frontend/.env
VITE_SERVER_URL=https://dev.virtualpytest.com
VITE_SLAVE_SERVER_URL=["https://dev.virtualpytest.com/pi4/server"]
```

### Backend Server (sunri-pi1)
```bash
# backend_server/.env
SERVER_URL=http://192.168.1.150:5109
# or
SERVER_URL=http://127.0.0.1:5109
```

### Backend Host (sunri-pi1)
```bash
# backend_host/.env
SERVER_URL=http://192.168.1.150:5109        # Talk to server directly (HTTP)
HOST_URL=https://dev.virtualpytest.com      # For browser static files (HTTPS)
HOST_API_URL=http://192.168.1.150:6109      # For server API calls (HTTP)
```

### Backend Server (sunri-pi4)
```bash
# backend_server/.env
SERVER_URL=http://192.168.1.34:5109
# or
SERVER_URL=http://127.0.0.1:5109
```

### Backend Host (sunri-pi4)
```bash
# backend_host/.env
SERVER_URL=http://192.168.1.150:5109                      # Talk to pi1 server (HTTP)
HOST_URL=https://dev.virtualpytest.com/pi4-server         # For browser (HTTPS via nginx)
HOST_API_URL=http://192.168.1.34:6109                     # For server API calls (HTTP)
```

## Key Changes

### 1. Host Registration (`backend_host/src/lib/utils/host_utils.py`)

```python
registration_data = {
    'host_name': host.host_name,
    'host_url': os.getenv('HOST_URL'),           # For browser
    'host_api_url': os.getenv('HOST_API_URL'),   # For server-to-server
    'host_ip': host.host_ip,
    'host_port': host.host_port,
    ...
}
```

### 2. URL Building (`shared/src/lib/utils/build_url_utils.py`)

**For Server-to-Server API Calls:**
```python
def buildHostUrl(host_info: dict, endpoint: str) -> str:
    """Uses host_api_url for direct server-to-server (HTTP)"""
    host_base_url = host_info.get('host_api_url') or host_info.get('host_url')
    return f"{host_base_url}/{endpoint}"
```

**For Browser Access to Static Files:**
```python
def buildHostImageUrl(host_info: dict, image_path: str) -> str:
    """Uses host_url for browser access via nginx (HTTPS)"""
    host_url = _get_nginx_host_url(host_info)
    return f"{host_url}/host/{image_path}"
```

### 3. Routes Cleanup

**Removed `verify=False` from all routes:**
- ✅ All `backend_server/src/routes/` files (6 files)
- ✅ All `backend_host/src/routes/` files (4 files)
- ✅ `backend_host/src/lib/utils/host_utils.py`
- ✅ `backend_host/src/controllers/verification/` files (2 files)

## Benefits

### ✅ Security
- No more `verify=False` scattered across codebase
- HTTP used only for trusted local network
- HTTPS properly verified for internet traffic

### ✅ Performance
- Direct server-to-server communication bypasses nginx
- Faster API calls (no SSL overhead for local network)
- Reduced load on nginx reverse proxy

### ✅ Maintainability
- Single centralized URL building logic
- Clear separation of concerns (browser vs server)
- Easy to understand and debug

### ✅ Flexibility
- Works for same-network deployments (current setup)
- Works for cross-network deployments (set `host_api_url` to HTTPS)
- Easy to adapt for different network topologies

## Usage Examples

### Server Calling Host API
```python
# server_control_routes.py
host_url = buildHostUrl(host_data, '/host/av/takeScreenshot')
# Returns: http://192.168.1.34:6109/host/av/takeScreenshot
response = requests.post(host_url, json=data, timeout=30)
# No verify=False needed - it's HTTP!
```

### Frontend Fetching Image
```typescript
// Frontend code
const imageUrl = buildHostImageUrl(host, '/stream/captures/image.jpg');
// Returns: https://dev.virtualpytest.com/pi4-server/host/stream/captures/image.jpg
// Browser fetches via nginx (HTTPS)
```

## Cross-Network Deployment

For hosts in different networks (internet communication):

```bash
# Remote host .env
SERVER_URL=https://main-server.virtualpytest.com/server
HOST_URL=https://remote-host.virtualpytest.com/host
HOST_API_URL=https://remote-host.virtualpytest.com/host  # Use HTTPS for internet
```

System automatically handles SSL verification based on protocol:
- `http://` URLs: No SSL verification needed
- `https://` URLs: Uses proper SSL verification with real certificates

## Migration Notes

### Backward Compatibility
- Falls back to `host_url` if `host_api_url` not provided
- Existing deployments continue working during migration
- No breaking changes to external APIs

### Testing
- Test same-network setup: Both URLs should be HTTP
- Test cross-network setup: `host_api_url` should be HTTPS
- Verify no SSL errors in logs

### Rollout Strategy
1. Update environment variables on all hosts
2. Restart host services to register with new URLs
3. Verify server-to-server communication uses HTTP
4. Verify browser access still uses HTTPS

## Troubleshooting

### SSL Certificate Errors
- Check that `host_api_url` uses HTTP for local network
- Verify `HOST_API_URL` environment variable is set correctly

### Slow API Calls
- Ensure server-to-server calls use `host_api_url` (direct)
- Check if requests are going through nginx unnecessarily

### Image Loading Issues
- Verify `host_url` points to nginx proxy URL
- Check nginx configuration for static file serving

## Files Modified

### Core Files
- `backend_host/src/lib/utils/host_utils.py` - Registration
- `shared/src/lib/utils/build_url_utils.py` - URL building

### Backend Server Routes (6 files)
- `backend_server/src/routes/server_control_routes.py`
- `backend_server/src/routes/server_stream_proxy_routes.py`
- `backend_server/src/routes/server_translation_routes.py`
- `backend_server/src/routes/server_script_routes.py`
- `backend_server/src/routes/server_remote_routes.py`
- `backend_server/src/routes/server_campaign_execution_routes.py`

### Backend Host Routes (4 files)
- `backend_host/src/routes/host_web_routes.py`
- `backend_host/src/routes/host_verification_video_routes.py`
- `backend_host/src/routes/host_script_routes.py`
- `backend_host/src/routes/host_campaign_routes.py`

### Controllers (2 files)
- `backend_host/src/controllers/verification/text_helpers.py`
- `backend_host/src/controllers/verification/image_helpers.py`

**Total: 13 files modified, 50+ `verify=False` removed!**

## Conclusion

The two-URL architecture provides a clean, maintainable solution for handling both local and remote deployments while eliminating SSL certificate issues. The system now automatically uses the appropriate protocol and verification strategy based on network topology.
