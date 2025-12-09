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
        
        Uses AV controller for all devices (unified screenshot endpoint).
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'team_id': str (REQUIRED),
                'include_ui_dump': bool (OPTIONAL, default: False) - Include UI hierarchy,
                'host_name': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with screenshot URL
        """
        device_id = params.get('device_id')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        include_ui_dump = params.get('include_ui_dump', False)
        host_name = params.get('host_name')
        
        # Build request
        data = {
            'device_id': device_id
        }
        
        if host_name:
            data['host_name'] = host_name
        
        query_params = {'team_id': team_id}
        
        # Use AV endpoint for all devices (unified screenshot)
        result = self.api.post('/server/av/takeScreenshot', data=data, params=query_params)
        
        if not result.get('success'):
            return self.formatter.format_api_response(result)
        
        # AV endpoint returns screenshot_url
        screenshot_url = result.get('screenshot_url', '')
        device_id_result = result.get('device_id', device_id)
        
        response_text = f"✅ Screenshot captured successfully.\n\n"
        response_text += f"Device: {device_id_result}\n"
        response_text += f"Screenshot URL: {screenshot_url}\n"
        
        if include_ui_dump:
            response_text += "\nNote: UI dump not supported via AV endpoint. Use dump_ui_elements tool separately if needed."
        
        return self.formatter.format_success(response_text)

