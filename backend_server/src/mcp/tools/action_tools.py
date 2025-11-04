"""
Action Tools - Device action execution

Execute remote commands, ADB commands, web actions, and desktop actions.
"""

import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class ActionTools:
    """Device action execution tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def execute_device_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute batch of actions on a device
        
        Supports: remote commands (IR, CEC, etc.), ADB commands, web actions, desktop automation.
        
        REUSES existing /server/action/executeBatch endpoint (same as frontend)
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'host_name': str (OPTIONAL),
                'team_id': str (REQUIRED),
                'actions': List[Dict] (REQUIRED) - [{
                    'command': str,
                    'params': dict,
                    'delay': int (ms, optional)
                }],
                'retry_actions': List[Dict] (OPTIONAL),
                'failure_actions': List[Dict] (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with execution results
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        actions = params.get('actions', [])
        retry_actions = params.get('retry_actions', [])
        failure_actions = params.get('failure_actions', [])
        
        # Validate required parameters
        if not actions:
            return {"content": [{"type": "text", "text": "Error: actions array is required"}], "isError": True}
        
        # Build request - SAME format as frontend (useAction.ts line 166-172)
        data = {
            'device_id': device_id,
            'host_name': host_name,
            'actions': actions,
            'retry_actions': retry_actions,
            'failure_actions': failure_actions
        }
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (useAction.ts line 163)
        print(f"[@MCP:execute_device_action] Calling /server/action/executeBatch")
        result = self.api.post('/server/action/executeBatch', data=data, params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Action execution failed')
            return {"content": [{"type": "text", "text": f"Action execution failed: {error_msg}"}], "isError": True}
        
        # Check if async (returns execution_id) - SAME as frontend (useAction.ts line 188)
        if result.get('execution_id'):
            execution_id = result['execution_id']
            print(f"[@MCP:execute_device_action] Async execution started: {execution_id}")
            
            # POLL for completion - SAME pattern as frontend (useAction.ts line 200-246)
            return self._poll_action_completion(execution_id, device_id, host_name, team_id)
        
        # Sync result - return directly
        print(f"[@MCP:execute_device_action] Sync execution completed")
        return self.formatter.format_api_response(result)
    
    def _poll_action_completion(self, execution_id: str, device_id: str, host_name: str, team_id: str, max_wait: int = 180) -> Dict[str, Any]:
        """
        Poll action execution until complete
        
        REUSES existing /server/action/execution/<id>/status API (same as frontend)
        Pattern from useAction.ts lines 200-246
        """
        poll_interval = 1  # 1 second (same as frontend line 206)
        elapsed = 0
        
        print(f"[@MCP:poll_action] Polling for execution {execution_id} (max {max_wait}s)")
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            # Poll status endpoint - SAME as frontend (useAction.ts line 195)
            status = self.api.get(
                f'/server/action/execution/{execution_id}/status',
                params={'device_id': device_id, 'host_name': host_name, 'team_id': team_id}
            )
            
            current_status = status.get('status')
            
            if current_status == 'completed':
                print(f"[@MCP:poll_action] Action execution completed successfully after {elapsed}s")
                result = status.get('result', {})
                passed = result.get('passed_count', 0)
                total = result.get('total_count', 0)
                message = f"Action execution completed: {passed}/{total} passed"
                return {"content": [{"type": "text", "text": f"✅ {message}"}], "isError": False}
            
            elif current_status == 'error':
                print(f"[@MCP:poll_action] Action execution failed after {elapsed}s")
                error = status.get('error', 'Action execution failed')
                return {"content": [{"type": "text", "text": f"❌ Action execution failed: {error}"}], "isError": True}
            
            elif current_status in ['pending', 'running']:
                print(f"[@MCP:poll_action] Status: {current_status} - {elapsed}s elapsed")
        
        print(f"[@MCP:poll_action] Action execution timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Action execution timed out after {max_wait}s"}], "isError": True}
