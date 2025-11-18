"""
Screenshot Tools - Capture device screenshots

Capture screenshots for AI vision analysis.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class ScreenshotTools:
    """Device screenshot capture tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
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
            MCP-formatted response with base64 screenshot for AI vision analysis
        """
        device_id = params.get('device_id')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        include_ui_dump = params.get('include_ui_dump', False)
        host_name = params.get('host_name')
        
        # Validate required parameters
        
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
        
        # Check if successful
        if not result.get('success'):
            return self.formatter.format_api_response(result)
        
        # Extract screenshot data
        screenshot_data = result.get('screenshot', '')
        
        # Format as image response for AI vision analysis
        return self.formatter.format_image_response(screenshot_data, mime_type="image/png")

