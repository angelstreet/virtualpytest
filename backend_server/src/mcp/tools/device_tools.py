"""
Device Tools - Device information and status

Get device information, capabilities, and execution status.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class DeviceTools:
    """Device information and status tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def get_device_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get device information and capabilities
        
        Returns device list with capabilities, controllers, and status.
        
        Args:
            params: {
                'device_id': str (OPTIONAL) - Specific device, or omit for all devices,
                'host_name': str (OPTIONAL) - Filter by host
            }
            
        Returns:
            MCP-formatted response with device information
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        
        # Build request
        query_params = {}
        if device_id:
            query_params['device_id'] = device_id
        if host_name:
            query_params['host_name'] = host_name
        
        # Call API
        result = self.api.get('/host/devices', params=query_params)
        
        return result
    
    def get_execution_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Poll execution status for async operations
        
        Check status of actions, testcases, or other async operations.
        
        Args:
            params: {
                'execution_id': str (REQUIRED) - Execution ID from async operation,
                'operation_type': str (OPTIONAL) - 'action', 'testcase', 'ai' for specific endpoints
            }
            
        Returns:
            MCP-formatted response with execution status and results
        """
        execution_id = params.get('execution_id')
        operation_type = params.get('operation_type', 'action')
        
        # Validate required parameters
        if not execution_id:
            return {"content": [{"type": "text", "text": "Error: execution_id is required"}], "isError": True}
        
        # Call appropriate endpoint based on operation type
        if operation_type == 'action':
            endpoint = f'/host/action/getStatus/{execution_id}'
        elif operation_type == 'testcase':
            endpoint = f'/host/testcase/getStatus/{execution_id}'
        elif operation_type == 'ai':
            endpoint = f'/host/ai/getExecutionStatus/{execution_id}'
        else:
            return format_tool_result({'success': False, 'error': f'Unknown operation_type: {operation_type}'})
        
        # Call API
        result = self.api.get(endpoint)
        
        return result

