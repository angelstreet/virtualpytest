# Host Name Pattern Documentation

## Overview

This document describes the standard pattern for handling `host_name` parameters in server routes after the refactoring to use centralized host management.

## Background

After refactoring, the frontend sends `host_name` (string identifier) instead of full `host` objects. The server then uses this `host_name` to look up the complete host information from the host manager and proxy requests to the appropriate host.

## Standard Pattern

### ✅ Correct Implementation

```python
@server_bp.route('/endpoint', methods=['POST'])
def endpoint_handler():
    """Proxy request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        device_id = request_data.get('device_id', 'device1')
        
        # Let proxy_to_host_with_params handle host lookup via get_host_from_request()
        query_params = {'device_id': device_id}

        response_data, status_code = proxy_to_host_with_params(
            '/host/endpoint',
            'POST',
            request_data,
            query_params
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### ❌ Incorrect Implementation (Bug Pattern)

```python
@server_bp.route('/endpoint', methods=['POST'])
def endpoint_handler():
    """Proxy request to selected host with device_id"""
    try:
        request_data = request.get_json() or {}
        host_name = request_data.get('host_name')  # ← Extract host_name
        device_id = request_data.get('device_id', 'device1')

        if not host:  # ← BUG: 'host' is not defined!
            return jsonify({'success': False, 'error': 'Host required'}), 400

        # ... rest of implementation
```

## How the Pattern Works

### 1. Frontend Request
Frontend sends request with `host_name`:
```typescript
const response = await fetch('/server/av/takeScreenshot', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    host_name: host.host_name,
    device_id: device?.device_id || 'device1',
  }),
});
```

### 2. Server Route Handler
Server route uses proxy utility functions:
```python
response_data, status_code = proxy_to_host_with_params(
    '/host/av/takeScreenshot',
    'POST',
    request_data,
    query_params
)
```

### 3. Proxy Utility Functions
The proxy functions handle host lookup automatically:

#### `get_host_from_request()`
```python
def get_host_from_request():
    """Get host information from request data using host_name lookup"""
    try:
        data = request.get_json() or {}
        host_name = data.get('host_name')
        
        if not host_name:
            return None, 'host_name required in request body'
            
        from  backend_host.src.lib.utils.server_utils import get_host_manager
        host_manager = get_host_manager()
        host_info = host_manager.get_host(host_name)
        
        if not host_info:
            return None, f'Host "{host_name}" not found'
            
        return host_info, None
    except Exception as e:
        return None, f'Error getting host from request: {str(e)}'
```

#### `proxy_to_host_with_params()`
```python
def proxy_to_host_with_params(endpoint, method='GET', data=None, query_params=None, timeout=30, headers=None):
    """Proxy a request to the specified host's endpoint with query parameters"""
    try:
        # Get host information from request
        host_info, error = get_host_from_request()
        if not host_info:
            return {
                'success': False,
                'error': error or 'Host information required'
            }, 400
        
        # Use centralized API URL builder to construct the proper URL
        from shared.src.lib.utils.build_url_utils import buildHostUrl
        full_url = buildHostUrl(host_info, endpoint)
        
        # ... make request to host
```

## Benefits of This Pattern

1. **Centralized Host Management**: All host lookups go through the host manager
2. **Consistent Error Handling**: Standardized error messages for missing/invalid hosts
3. **Reduced Code Duplication**: No need to manually validate hosts in each route
4. **Automatic Host Discovery**: Host manager handles host registration and cleanup
5. **Type Safety**: Host objects are validated and structured consistently

## Common Mistakes to Avoid

### 1. Manual Host Validation
❌ **Don't do this:**
```python
host_name = request_data.get('host_name')
if not host_name:
    return jsonify({'error': 'host_name required'}), 400
```

✅ **Let the proxy function handle it:**
```python
# proxy_to_host_with_params() handles validation automatically
```

### 2. Undefined Variable References
❌ **Don't do this:**
```python
host_name = request_data.get('host_name')
if not host:  # ← 'host' is not defined!
    return jsonify({'error': 'Host required'}), 400
```

✅ **Use the correct variable:**
```python
host_name = request_data.get('host_name')
if not host_name:  # ← Check the actual variable
    return jsonify({'error': 'host_name required'}), 400
```

### 3. Mixing Patterns
❌ **Don't mix old and new patterns:**
```python
# Don't manually extract host_name and then use proxy functions
host_name = request_data.get('host_name')
if not host_name:
    return jsonify({'error': 'host_name required'}), 400
    
# proxy_to_host_with_params will do this lookup again!
response_data, status_code = proxy_to_host_with_params(...)
```

## Special Cases

### Routes Expecting Full Host Objects
Some routes (like `server_actions_routes.py`) expect full host objects in the request:

```python
@server_actions_bp.route('/executeBatch', methods=['POST'])
def action_execute_batch():
    try:
        data = request.get_json() or {}
        host = data.get('host', {})  # ← Expects full host object
        
        if not host:
            return jsonify({'success': False, 'error': 'host is required'}), 400
```

This is correct for routes that receive embedded host objects rather than just `host_name` strings.

### Routes with Custom Host Handling
Some routes manually handle host lookup for specific reasons:

```python
@server_stream_proxy_bp.route('/av/streamUrl', methods=['POST'])
def proxy_stream_url():
    try:
        data = request.get_json()
        host_name = data.get('host_name')
        
        if not host_name:
            return jsonify({'error': 'host_name is required'}), 400
        
        # Manual host lookup for specific stream proxy logic
        host_manager = get_host_manager()
        host_data = host_manager.get_host(host_name)
        if not host_data:
            return jsonify({'error': f'Host {host_name} not found'}), 404
```

This is acceptable when routes need custom host handling logic.

## Migration Checklist

When updating routes to use the standard pattern:

- [ ] Remove manual `host_name` extraction
- [ ] Remove manual host validation (`if not host_name:`)
- [ ] Remove undefined variable checks (`if not host:` when `host` is not defined)
- [ ] Use `proxy_to_host()` or `proxy_to_host_with_params()` functions
- [ ] Let proxy functions handle host lookup and validation
- [ ] Test that the route works with frontend requests
- [ ] Verify error handling for missing/invalid hosts

## Files Using This Pattern

### ✅ Correctly Implemented
- `server_web_routes.py` - Uses `get_host_from_request()` and `proxy_to_host()`
- `server_control_routes.py` - Manual validation but checks correct variables
- `server_stream_proxy_routes.py` - Manual host lookup with proper validation

### ✅ Recently Fixed
- `server_av_routes.py` - All routes now use standard pattern
- `server_monitoring_routes.py` - All routes now use standard pattern  
- `server_restart_routes.py` - Fixed print statement variable reference

### ⚠️ Special Cases (Correct)
- `server_actions_routes.py` - Expects full `host` objects, not `host_name`

## Testing

To verify the pattern works correctly:

1. **Frontend Request**: Ensure frontend sends `host_name` parameter
2. **Server Response**: Verify server can look up host and proxy request
3. **Error Handling**: Test with invalid/missing `host_name` values
4. **Host Discovery**: Verify host manager can find registered hosts

Example test:
```bash
curl -X POST http://localhost:5000/server/av/takeScreenshot \
  -H "Content-Type: application/json" \
  -d '{"host_name": "test-host", "device_id": "device1"}'
```

Expected success response:
```json
{
  "success": true,
  "screenshot_url": "http://test-host:8080/host/stream/..."
}
```

Expected error response (invalid host):
```json
{
  "success": false,
  "error": "Host \"invalid-host\" not found"
}
```
