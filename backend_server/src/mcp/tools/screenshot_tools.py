"""
Screenshot Tools - Capture device screenshots

Capture screenshots for AI vision analysis.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.response_formatter import format_tool_result


class ScreenshotTools:
    """Device screenshot capture tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
    
    def capture_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture screenshot from device
        
        Returns base64-encoded image for AI vision analysis.
        Optionally includes UI dump for element detection.
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'team_id': str (REQUIRED),
                'include_ui_dump': bool (OPTIONAL, default: False) - Include UI hierarchy,
                'host_name': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with base64 screenshot and optional UI dump
        """
        device_id = params.get('device_id', 'device1')
        team_id = params.get('team_id')
        include_ui_dump = params.get('include_ui_dump', False)
        host_name = params.get('host_name')
        
        # Validate required parameters
        if not team_id:
            return format_tool_result({'success': False, 'error': 'team_id is required'})
        
        # Build request
        data = {
            'device_id': device_id
        }
        
        if host_name:
            data['host_name'] = host_name
        
        query_params = {'team_id': team_id}
        
        # Call appropriate endpoint
        if include_ui_dump:
            # Screenshot + UI dump
            result = self.api.post('/server/remote/screenshotAndDump', data=data, params=query_params)
        else:
            # Screenshot only
            result = self.api.post('/server/remote/takeScreenshot', data=data, params=query_params)
        
        return format_tool_result(result)

