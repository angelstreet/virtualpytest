"""
AI Tools - AI-powered test generation

Generate test graphs from natural language using AI.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.response_formatter import format_tool_result


class AITools:
    """AI-powered test generation tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
    
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
        device_id = params.get('device_id', 'device1')
        team_id = params.get('team_id')
        userinterface_name = params.get('userinterface_name')
        current_node_id = params.get('current_node_id')
        
        # Validate required parameters
        if not prompt:
            return format_tool_result({'success': False, 'error': 'prompt is required'})
        if not team_id:
            return format_tool_result({'success': False, 'error': 'team_id is required'})
        if not userinterface_name:
            return format_tool_result({'success': False, 'error': 'userinterface_name is required'})
        
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
        
        return format_tool_result(result)

