"""
Action Tools - Device action execution

Execute remote commands, ADB commands, web actions, and desktop actions.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.response_formatter import format_tool_result


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
        device_id = params.get('device_id', 'device1')
        team_id = params.get('team_id')
        actions = params.get('actions', [])
        retry_actions = params.get('retry_actions', [])
        failure_actions = params.get('failure_actions', [])
        
        # Validate required parameters
        if not team_id:
            return format_tool_result({'success': False, 'error': 'team_id is required'})
        if not actions:
            return format_tool_result({'success': False, 'error': 'actions array is required'})
        
        # Build request
        data = {
            'device_id': device_id,
            'actions': actions,
            'retry_actions': retry_actions,
            'failure_actions': failure_actions
        }
        
        query_params = {'team_id': team_id}
        
        # Call API
        result = self.api.post('/host/action/executeBatch', data=data, params=query_params)
        
        return format_tool_result(result)

