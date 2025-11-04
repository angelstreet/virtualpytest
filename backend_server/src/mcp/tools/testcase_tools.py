"""
TestCase Tools - Test case execution

Execute complete test cases and scripts on devices.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class TestCaseTools:
    """Test case execution tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def execute_testcase(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a test case on a device
        
        Can execute from graph JSON (direct) or by testcase name (saved).
        Returns execution_id immediately for async polling.
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'team_id': str (REQUIRED),
                'host_name': str (REQUIRED),
                'graph_json': Dict (REQUIRED if no testcase_name) - Graph definition,
                'testcase_name': str (REQUIRED if no graph_json) - Saved testcase name,
                'userinterface_name': str (OPTIONAL),
                'async_execution': bool (OPTIONAL, default: True)
            }
            
        Returns:
            MCP-formatted response with execution_id for polling or immediate results
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        graph_json = params.get('graph_json')
        testcase_name = params.get('testcase_name')
        userinterface_name = params.get('userinterface_name', '')
        async_execution = params.get('async_execution', True)
        
        # Validate required parameters
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        if not graph_json and not testcase_name:
            return {"content": [{"type": "text", "text": "Error: Either graph_json or testcase_name is required"}], "isError": True}
        
        # Build request
        if graph_json:
            # Execute from graph (direct)
            data = {
                'device_id': device_id,
                'host_name': host_name,
                'graph_json': graph_json,
                'userinterface_name': userinterface_name,
                'testcase_name': testcase_name or 'mcp_testcase',
                'async_execution': async_execution
            }
            
            query_params = {'team_id': team_id}
            
            result = self.api.post('/host/testcase/execute', data=data, params=query_params)
        else:
            # Execute saved testcase by name
            # Note: Would need testcase_id lookup first
            return {"content": [{"type": "text", "text": "Error: Execute by testcase_name not yet implemented - use graph_json"}], "isError": True}
        
        return result

