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
            
            nodes = response.get('nodes', [])
            edges = response.get('edges', [])
            
            # Format output
            result_text = f"✅ Exploration Complete!\n\n"
            result_text += f"🗺️ Navigation Tree Structure:\n"
            result_text += f"  • {len(nodes)} nodes\n"
            result_text += f"  • {len(edges)} edges\n\n"
            
            # List nodes
            result_text += f"📱 Nodes:\n"
            for idx, node in enumerate(nodes, 1):
                result_text += f"  {idx}. {node}\n"
            
            # List edges (parse edge IDs to show connections)
            if edges:
                result_text += f"\n🔗 Edges:\n"
                for idx, edge in enumerate(edges, 1):
                    # Parse edge ID like "edge_home_search" to "home ↔ search"
                    edge_clean = edge.replace('edge_', '').replace('_temp', '')
                    parts = edge_clean.split('_', 1)
                    if len(parts) == 2:
                        connection = f"{parts[0]} ↔ {parts[1]}"
                    else:
                        connection = edge_clean
                    result_text += f"  {idx}. {connection}\n"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Auto-discover failed: {str(e)}", ErrorCategory.BACKEND)
