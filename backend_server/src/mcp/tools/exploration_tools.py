"""AI Exploration Tools - Automated tree building via screen analysis"""

import json
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
        """Auto-discover elements, create nodes/edges, and validate them."""
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
            validation_results = response.get('validation_results', [])
            
            # Format output - just show raw data, no extra processing
            result_text = f"🗺️ EXPLORATION + VALIDATION COMPLETE\n{'='*50}\n\n"
            result_text += f"📦 CREATED: {len(nodes)} nodes, {len(edges)} edges\n\n"
            
            if nodes:
                result_text += f"Nodes: {', '.join(nodes)}\n\n"
            
            # Show validation results (raw format from validate_next_item)
            result_text += f"🧪 VALIDATION: {len(validation_results)} items tested\n\n"
            
            for r in validation_results:
                item = r.get('item', '')
                # Mobile/Web format
                if 'click_result' in r:
                    fwd = r.get('click_result', '?')
                    bck = r.get('back_result', '?')
                    symbol = '✅' if fwd == 'success' and bck == 'success' else '❌'
                    result_text += f"{symbol} {item}: forward={fwd}, back={bck}\n"
                # TV format
                elif 'edges' in r:
                    for edge in r.get('edges', []):
                        et = edge.get('edge_type', '')
                        fwd = edge.get('action_sets', {}).get('forward', {}).get('result', '?')
                        bck = edge.get('action_sets', {}).get('reverse', {}).get('result', '?')
                        symbol = '✅' if fwd == 'success' and bck == 'success' else '❌'
                        result_text += f"{symbol} {item} ({et}): forward={fwd}, back={bck}\n"
            
            return {"content": [{"type": "text", "text": result_text}], "isError": False}
            
        except Exception as e:
            return self.formatter.format_error(f"Auto-discover failed: {str(e)}", ErrorCategory.BACKEND)
