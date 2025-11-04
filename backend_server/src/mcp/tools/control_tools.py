"""
Control Tools - Device control and session management

Provides take_control and release_control for device locking and cache generation.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.response_formatter import format_tool_result


class ControlTools:
    """Device control and session management tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
    
    def take_control(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take control of a device (REQUIRED before any operations)
        
        This locks the device, generates navigation cache, and returns a session_id.
        Must be called before: actions, navigation, verification, testcases, AI graph.
        
        Args:
            params: {
                'host_name': str (REQUIRED),
                'device_id': str (REQUIRED),
                'tree_id': str (OPTIONAL - triggers cache generation),
                'team_id': str (REQUIRED)
            }
            
        Returns:
            MCP-formatted response with session_id and cache status
        """
        host_name = params.get('host_name')
        device_id = params.get('device_id')
        tree_id = params.get('tree_id')
        team_id = params.get('team_id')
        
        # Validate required parameters
        if not host_name:
            return format_tool_result({'success': False, 'error': 'host_name is required'})
        if not device_id:
            return format_tool_result({'success': False, 'error': 'device_id is required'})
        if not team_id:
            return format_tool_result({'success': False, 'error': 'team_id is required'})
        
        # Build request
        data = {
            'host_name': host_name,
            'device_id': device_id
        }
        
        if tree_id:
            data['tree_id'] = tree_id
        
        query_params = {'team_id': team_id}
        
        # Call API
        result = self.api.post('/server/control/takeControl', data=data, params=query_params)
        
        return format_tool_result(result)
    
    def release_control(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Release control of a device
        
        Unlocks the device and releases the session.
        Should be called when done with device operations.
        
        Args:
            params: {
                'host_name': str (REQUIRED),
                'device_id': str (REQUIRED),
                'team_id': str (REQUIRED)
            }
            
        Returns:
            MCP-formatted response
        """
        host_name = params.get('host_name')
        device_id = params.get('device_id')
        team_id = params.get('team_id')
        
        # Validate required parameters
        if not host_name:
            return format_tool_result({'success': False, 'error': 'host_name is required'})
        if not device_id:
            return format_tool_result({'success': False, 'error': 'device_id is required'})
        if not team_id:
            return format_tool_result({'success': False, 'error': 'team_id is required'})
        
        # Build request
        data = {
            'host_name': host_name,
            'device_id': device_id
        }
        
        query_params = {'team_id': team_id}
        
        # Call API
        result = self.api.post('/server/control/releaseControl', data=data, params=query_params)
        
        return format_tool_result(result)

