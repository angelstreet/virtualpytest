"""
Navigation Tools - UI navigation execution

Navigate through UI trees using pathfinding and action execution.
"""

import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class NavigationTools:
    """UI navigation execution tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def navigate_to_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigate to a target node in UI tree
        
        Uses pathfinding to find optimal path and executes navigation.
        Requires take_control to be called first (cache must be ready).
        
        REUSES existing /server/navigation/execute/{tree_id} endpoint (same as frontend)
        
        Args:
            params: {
                'tree_id': str (REQUIRED),
                'userinterface_name': str (REQUIRED - for reference resolution),
                'target_node_id': str (REQUIRED if no target_node_label),
                'target_node_label': str (REQUIRED if no target_node_id),
                'device_id': str (REQUIRED),
                'team_id': str (REQUIRED),
                'current_node_id': str (OPTIONAL - starting position),
                'host_name': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with navigation path and results
        """
        tree_id = params.get('tree_id')
        userinterface_name = params.get('userinterface_name')
        target_node_id = params.get('target_node_id')
        target_node_label = params.get('target_node_label')
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        current_node_id = params.get('current_node_id')
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        
        # Validate required parameters
        if not tree_id:
            return {"content": [{"type": "text", "text": "Error: tree_id is required"}], "isError": True}
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "Error: userinterface_name is required for reference resolution"}], "isError": True}
        if not target_node_id and not target_node_label:
            return {"content": [{"type": "text", "text": "Error: Either target_node_id or target_node_label is required"}], "isError": True}
        
        # Build request - SAME format as frontend (navigationExecutionUtils.ts line 58-65)
        data = {
            'userinterface_name': userinterface_name,
            'device_id': device_id,
            'host_name': host_name
        }
        
        if target_node_id:
            data['target_node_id'] = target_node_id
        if target_node_label:
            data['target_node_label'] = target_node_label
        if current_node_id:
            data['current_node_id'] = current_node_id
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (navigationExecutionUtils.ts line 53)
        print(f"[@MCP:navigate_to_node] Calling /server/navigation/execute/{tree_id}")
        result = self.api.post(
            f'/server/navigation/execute/{tree_id}',
            data=data,
            params=query_params
        )
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Navigation failed')
            return {"content": [{"type": "text", "text": f"Navigation failed: {error_msg}"}], "isError": True}
        
        # Check if async (returns execution_id) - SAME as frontend (navigationExecutionUtils.ts line 75)
        if result.get('execution_id'):
            execution_id = result['execution_id']
            print(f"[@MCP:navigate_to_node] Async execution started: {execution_id}")
            
            # POLL for completion - SAME pattern as frontend (navigationExecutionUtils.ts line 84-142)
            return self._poll_navigation_completion(execution_id, device_id, host_name, team_id, target_node_label or target_node_id)
        
        # Sync result - return directly
        print(f"[@MCP:navigate_to_node] Sync execution completed")
        return self.formatter.format_api_response(result)
    
    def _poll_navigation_completion(self, execution_id: str, device_id: str, host_name: str, team_id: str, target_label: str, max_wait: int = 60) -> Dict[str, Any]:
        """
        Poll navigation execution until complete
        
        REUSES existing /server/navigation/execution/<id>/status API (same as frontend)
        Pattern from navigationExecutionUtils.ts lines 84-142
        """
        poll_interval = 1  # 1 second (same as frontend line 93)
        elapsed = 0
        
        print(f"[@MCP:poll_navigation] Polling for execution {execution_id} (max {max_wait}s)")
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            # Poll status endpoint - SAME as frontend (navigationExecutionUtils.ts line 85-86)
            status = self.api.get(
                f'/server/navigation/execution/{execution_id}/status',
                params={'device_id': device_id, 'host_name': host_name, 'team_id': team_id}
            )
            
            current_status = status.get('status')
            
            if current_status == 'completed':
                print(f"[@MCP:poll_navigation] Navigation completed successfully after {elapsed}s")
                result = status.get('result', {})
                message = result.get('message', f'Navigation to {target_label} completed')
                return {"content": [{"type": "text", "text": f"✅ {message}"}], "isError": False}
            
            elif current_status == 'error':
                print(f"[@MCP:poll_navigation] Navigation failed after {elapsed}s")
                error = status.get('error', 'Navigation failed')
                return {"content": [{"type": "text", "text": f"❌ Navigation failed: {error}"}], "isError": True}
            
            elif current_status == 'running':
                progress = status.get('progress', 0)
                message = status.get('message', 'Running...')
                print(f"[@MCP:poll_navigation] Status: {message} ({progress}%) - {elapsed}s elapsed")
        
        print(f"[@MCP:poll_navigation] Navigation timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Navigation timed out after {max_wait}s"}], "isError": True}

