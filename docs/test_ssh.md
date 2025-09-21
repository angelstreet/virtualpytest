# SSH Testing Guide for MCP

## Quick SSH Testing Commands

### 1. Restart Server
```bash
sudo systemctl restart vpt_server_host
```

### 2. Check Server Status
```bash
systemctl is-active vpt_server_host
```

### 3. Find Server Port
```bash
sudo netstat -tlnp | grep python
```

### 4. Test AI Execution Endpoint
```bash
curl -s -X POST "http://localhost:5109/server/ai-execution/executeTask?team_id=7fdeb4bb-3639-4ec3-959f-b54769a219ce" \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "go to live",
    "userinterface_name": "horizon_android_mobile", 
    "host_name": "sunri-pi1",
    "device_id": "device1"
  }'
```

### 5. Check Recent Logs
```bash
journalctl -u vpt_server_host.service --since "2 minutes ago" | tail -20
```

### 6. Monitor Logs in Real-time
```bash
journalctl -u vpt_server_host.service -f
```

## Expected Success Response
```json
{
  "success": true,
  "execution_id": "uuid",
  "message": "Execution started",
  "plan_steps": 1
}
```

## Common Error Patterns
- `'userinterface_id'` - Fixed: Field name mismatch
- `'tree_id'` - Navigation context issue
- `Host not found` - Server still starting up
- `400 status` - Check logs for specific error

## MCP SSH Tool Usage
Use `mcp_ssh-mcp_exec` with command parameter to execute any bash command on the remote server.
