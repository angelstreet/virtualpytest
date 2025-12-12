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
        Take exclusive control of a device
        
        Locks the device for exclusive use and returns a session_id.
        Required before any device operations.
        
        Automatically handles lock conflicts:
        - Tries to take control normally
        - If device is locked by another session, forces unlock and retries
        - Ensures agent can always take control when needed
        
        Args:
            params: {
                'host_name': str (REQUIRED - host where device is connected),
                'device_id': str (OPTIONAL - defaults to 'device1'),
                'team_id': str (OPTIONAL - uses default if not provided)
            }
            
        Returns:
            MCP-formatted response with session_id
        """
        host_name = params.get('host_name')
        device_id = params.get('device_id')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        userinterface_name = params.get('userinterface_name')
        
        # Build request - include userinterface_name for cache population
        data = {
            'host_name': host_name,
            'device_id': device_id,
            'userinterface_name': userinterface_name
        }
        
        # STEP 1: Try normal take_control
        result = self.api.post('/server/control/takeControl', data=data, params={'team_id': team_id})
        
        # STEP 2: If device locked by another session, force unlock and retry
        if not result.get('success') and result.get('errorType') == 'device_locked':
            print(f"[@mcp:take_control] Device {host_name} locked by another session, forcing unlock and retrying...")
            
            # Force unlock the device
            force_unlock_result = self.api.post('/server/control/forceUnlock', data={'host_name': host_name})
            
            if force_unlock_result.get('success'):
                print(f"[@mcp:take_control] Force unlock successful, retrying take_control...")
                # Retry take_control after force unlock
                result = self.api.post('/server/control/takeControl', data=data, params={'team_id': team_id})
            else:
                print(f"[@mcp:take_control] Force unlock failed: {force_unlock_result.get('error', 'Unknown error')}")
        
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



