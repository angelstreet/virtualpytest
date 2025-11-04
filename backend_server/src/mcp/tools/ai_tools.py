"""
AI Tools - AI-powered test generation

Generate test graphs from natural language using AI.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class AITools:
    """AI-powered test generation tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def generate_test_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate test case graph from natural language prompt
        
        Uses AI to convert natural language descriptions into executable test graphs.
        Requires device to have AIGraphBuilder initialized.
        
        Args:
            params: {
                'prompt': str (REQUIRED) - Natural language test description,
                'device_id': str (REQUIRED),
                'team_id': str (REQUIRED),
                'userinterface_name': str (REQUIRED),
                'current_node_id': str (OPTIONAL) - Starting node for context
            }
            
        Returns:
            MCP-formatted response with generated graph JSON and analysis
        """
        prompt = params.get('prompt')
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        userinterface_name = params.get('userinterface_name')
        current_node_id = params.get('current_node_id')
        
        # Validate required parameters
        if not prompt:
            return {"content": [{"type": "text", "text": "Error: prompt is required"}], "isError": True}
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "Error: userinterface_name is required"}], "isError": True}
        
        # Build request
        data = {
            'prompt': prompt,
            'device_id': device_id,
            'userinterface_name': userinterface_name
        }
        
        if current_node_id:
            data['current_node_id'] = current_node_id
        
        query_params = {'team_id': team_id}
        
        # Call API
        result = self.api.post('/host/ai/generatePlan', data=data, params=query_params)
        
        return result

