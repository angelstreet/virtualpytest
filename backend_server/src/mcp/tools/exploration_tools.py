"""AI Exploration Tools - Automated tree building via screen analysis"""

from typing import Dict, Any
from ..utils.mcp_formatter import MCPFormatter, ErrorCategory
from ..utils.api_client import MCPAPIClient

DEFAULT_TEAM_ID = '7fdeb4bb-3639-4ec3-959f-b54769a219ce'


class ExplorationTools:
    """AI exploration tools for automated tree building"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api_client = api_client
        self.formatter = MCPFormatter()
    
    def auto_discover_screen(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-discover elements and create nodes/edges"""
        tree_id = params.get('tree_id')
        host_name = params.get('host_name')
        userinterface_name = params.get('userinterface_name')
        device_id = params.get('device_id', 'device1')
        parent_node_id = params.get('parent_node_id', 'home')
        team_id = params.get('team_id', DEFAULT_TEAM_ID)
        
        if not all([tree_id, host_name, userinterface_name]):
            return self.formatter.format_error("tree_id, host_name and userinterface_name are required")
        
        try:
            response = self.api_client.post(
                '/server/ai-generation/auto-discover-screen',
                data={
                    'tree_id': tree_id,
                    'userinterface_name': userinterface_name,
                    'device_id': device_id,
                    'parent_node_id': parent_node_id
                },
                params={'host_name': host_name, 'team_id': team_id}
            )
            
            if not response.get('success'):
                return self.formatter.format_error(
                    f"Auto-discover failed: {response.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            nodes_created = response.get('nodes_created', 0)
            edges_created = response.get('edges_created', 0)
            elements_found = response.get('elements_found', [])
            
            result_text = f"✅ Auto-Discovery Complete\n\n"
            result_text += f"Elements: {len(elements_found)} | Nodes: {nodes_created} | Edges: {edges_created}\n\n"
            
            if elements_found:
                result_text += f"Elements: {', '.join(elements_found[:10])}"
                if len(elements_found) > 10:
                    result_text += f" (+{len(elements_found) - 10} more)"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Auto-discover failed: {str(e)}", ErrorCategory.BACKEND)
