"""
Control Tools - Device control and session management

Provides take_control and release_control for device locking and cache generation.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class ControlTools:
    """Device control and session management tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def take_control(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take control of a device (REQUIRED before any operations)
        
        This locks the device, generates navigation cache, and returns a session_id.
        Must be called before: actions, navigation, verification, testcases, AI graph.
        
        Args:
            params: {
                'host_name': str (OPTIONAL - uses default 'sunri-pi1' if not provided),
                'device_id': str (OPTIONAL - uses default 'device_1' if not provided),
                'tree_id': str (OPTIONAL - triggers cache generation),
                'team_id': str (OPTIONAL - uses default if not provided)
            }
            
        Returns:
            MCP-formatted response with session_id and cache status
        """
        host_name = params.get('host_name')
        device_id = params.get('device_id')
        tree_id = params.get('tree_id')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        # Build request
        data = {'host_name': host_name, 'device_id': device_id}
        if tree_id:
            data['tree_id'] = tree_id
        
        # Call API and format response
        result = self.api.post('/server/control/takeControl', data=data, params={'team_id': team_id})
        return self.formatter.format_api_response(result)
    
    def release_control(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Release control of a device
        
        Unlocks the device and releases the session.
        Should be called when done with device operations.
        
        Args:
            params: {
                'host_name': str (OPTIONAL - uses default 'sunri-pi1' if not provided),
                'device_id': str (OPTIONAL - uses default 'device_1' if not provided),
                'team_id': str (OPTIONAL - uses default if not provided)
            }
            
        Returns:
            MCP-formatted response
        """
        host_name = params.get('host_name')
        device_id = params.get('device_id')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        # Build request
        data = {'host_name': host_name, 'device_id': device_id}
        
        # Call API and format response
        result = self.api.post('/server/control/releaseControl', data=data, params={'team_id': team_id})
        return self.formatter.format_api_response(result)



