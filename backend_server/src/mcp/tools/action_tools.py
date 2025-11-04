"""
Action Tools - Device action execution

Execute remote commands, ADB commands, web actions, and desktop actions.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from shared.src.lib.config.constants import APP_CONFIG


class ActionTools:
    """Device action execution tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
    
    def execute_device_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute batch of actions on a device
        
        Supports: remote commands (IR, CEC, etc.), ADB commands, web actions, desktop automation.
        Returns execution_id immediately for async polling.
        
        Args:
            params: {
                'device_id': str (REQUIRED),
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
            MCP-formatted response with execution_id for polling
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        actions = params.get('actions', [])
        retry_actions = params.get('retry_actions', [])
        failure_actions = params.get('failure_actions', [])
        
        # Validate required parameters
        if not actions:
            return {"content": [{"type": "text", "text": "Error: actions array is required"}], "isError": True}
        
        # Build request
        data = {
            'device_id': device_id,
            'actions': actions,
            'retry_actions': retry_actions,
            'failure_actions': failure_actions
        }
        
        query_params = {'team_id': team_id}
        
        # Call API - returns MCP format directly
        return self.api.post('/host/action/executeBatch', data=data, params=query_params)

