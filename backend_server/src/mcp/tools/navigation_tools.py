"""
Navigation Tools - UI navigation execution

Navigate through UI trees using pathfinding and action execution.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class NavigationTools:
    """UI navigation execution tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def navigate_to_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigate to a target node in UI tree
        
        Uses pathfinding to find optimal path and executes navigation.
        Requires take_control to be called first (cache must be ready).
        
        Args:
            params: {
                'tree_id': str (REQUIRED),
                'userinterface_name': str (REQUIRED - for reference resolution),
                'target_node_id': str (REQUIRED if no target_node_label),
                'target_node_label': str (REQUIRED if no target_node_id),
                'device_id': str (REQUIRED),
                'team_id': str (REQUIRED),
                'current_node_id': str (OPTIONAL - starting position),
                'host_name': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with navigation path and results
        """
        tree_id = params.get('tree_id')
        userinterface_name = params.get('userinterface_name')
        target_node_id = params.get('target_node_id')
        target_node_label = params.get('target_node_label')
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        current_node_id = params.get('current_node_id')
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        
        # Validate required parameters
        if not tree_id:
            return {"content": [{"type": "text", "text": "Error: tree_id is required"}], "isError": True}
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "Error: userinterface_name is required for reference resolution"}], "isError": True}
        if not target_node_id and not target_node_label:
            return {"content": [{"type": "text", "text": "Error: Either target_node_id or target_node_label is required"}], "isError": True}
        
        # Build request
        data = {
            'tree_id': tree_id,
            'userinterface_name': userinterface_name,
            'device_id': device_id
        }
        
        if target_node_id:
            data['target_node_id'] = target_node_id
        if target_node_label:
            data['target_node_label'] = target_node_label
        if current_node_id:
            data['current_node_id'] = current_node_id
        if host_name:
            data['host_name'] = host_name
        
        query_params = {'team_id': team_id}
        
        # Call API
        result = self.api.post('/server/navigation/executeNavigationToNode', data=data, params=query_params)
        
        return result

