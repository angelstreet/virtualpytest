"""
Node Generator - Naming convention + _temp suffix
Generates node and edge structures following user's naming rules
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4


class NodeGenerator:
    """Generate node/edge names following naming convention + _temp suffix"""
    
    def __init__(self, tree_id: str, team_id: str):
        self.tree_id = tree_id
        self.team_id = team_id
        self.node_counter = 0
        self.edge_counter = 0
        
    def generate_node_name(
        self,
        ai_suggestion: str,
        parent_node: Optional[str],
        context_visible: bool
    ) -> str:
        """
        Generate node name following convention + _temp
        
        Rules:
        1. If context_visible (horizontal nav): keep prefix
           Example: "home" + "settings" → "home_settings_temp"
           
        2. If new screen (entered): drop prefix  
           Example: "settings" → "settings_temp"
           
        3. If in subtree: use parent prefix
           Example: parent="settings", child="audio" → "settings_audio_temp"
        
        Args:
            ai_suggestion: AI-suggested name (e.g., "settings")
            parent_node: Parent node name (e.g., "home_temp")
            context_visible: True if previous menu still visible
            
        Returns:
            Final node name with _temp suffix
        """
        # Clean AI suggestion (remove spaces, lowercase, sanitize)
        clean_name = ai_suggestion.lower().replace(' ', '_').replace('-', '_')
        clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '_')
        
        # If no parent, this is root-level node
        if not parent_node:
            return f"{clean_name}_temp"
        
        # Remove _temp from parent to get base name
        parent_base = parent_node.replace('_temp', '')
        
        # If context visible (horizontal nav), keep parent prefix
        if context_visible:
            # Check if parent has underscore (is already prefixed)
            if '_' in parent_base:
                # Parent is like "home_settings", keep same level
                return f"{parent_base}_{clean_name}_temp"
            else:
                # Parent is like "home", add as child
                return f"{parent_base}_{clean_name}_temp"
        
        # New screen (entered) - drop prefix
        return f"{clean_name}_temp"
    
    def should_create_subtree(self, node_name: str, depth: int) -> bool:
        """
        Determine if this node should have a subtree
        
        Rules:
        - Node entered via OK (new screen) → create subtree
        - Node name has no underscore prefix → likely a main screen
        - Depth 1 from root → create subtree
        
        Args:
            node_name: Node name (with _temp)
            depth: Current depth in exploration
            
        Returns:
            True if subtree should be created
        """
        # Remove _temp to analyze base name
        base_name = node_name.replace('_temp', '')
        
        # If depth 1, create subtree for organization
        if depth == 1:
            return True
        
        # If name has no underscore, it's likely a main screen
        # Example: "settings_temp" (not "home_settings_temp")
        if '_' not in base_name:
            return True
        
        return False
    
    def create_node_data(
        self,
        node_name: str,
        position: Dict[str, int],
        ai_analysis: Dict,
        node_type: str = 'screen'
    ) -> Dict:
        """
        Create node data structure for save_node()
        
        Args:
            node_name: Node name (with _temp)
            position: {'x': 250, 'y': 250}
            ai_analysis: AI analysis result
            node_type: 'screen', 'menu', etc.
            
        Returns:
            Node data dict ready for save_node()
        """
        return {
            'node_id': node_name,
            'label': node_name,
            'type': node_type,
            'position_x': position['x'],
            'position_y': position['y'],
            'data': {
                'type': node_type,
                'ai_generated': True,
                'ai_suggestion': ai_analysis.get('suggested_name', ''),
                'screen_type': ai_analysis.get('screen_type', 'screen'),
                'discovered_at': datetime.now(timezone.utc).isoformat(),
                'reasoning': ai_analysis.get('reasoning', '')
            },
            'style': {}
        }
    
    def create_edge_data(
        self,
        source: str,
        target: str,
        actions: List[Dict],
        label: str = ''
    ) -> Dict:
        """
        Create edge data structure for save_edge()
        
        Args:
            source: Source node_id (with _temp)
            target: Target node_id (with _temp)
            actions: List of actions taken
            label: Optional custom label
            
        Returns:
            Edge data dict ready for save_edge()
        """
        edge_id = f"edge_{source}_to_{target}_temp"
        action_set_id = f"ai_forward_{self.edge_counter}"
        self.edge_counter += 1
        
        return {
            'edge_id': edge_id,
            'source_node_id': source,
            'target_node_id': target,
            'action_sets': [{
                'id': action_set_id,
                'direction': 'forward',
                'actions': actions
            }],
            'default_action_set_id': action_set_id,
            'final_wait_time': 1000,
            'label': label,  # Empty = auto-generated by DB trigger
            'data': {
                'ai_generated': True,
                'discovered_at': datetime.now(timezone.utc).isoformat()
            }
        }
    
    def rename_node(self, node_data: Dict) -> Dict:
        """
        Remove _temp suffix from node data (for approval)
        
        Args:
            node_data: Original node data with _temp
            
        Returns:
            Node data with _temp removed
        """
        renamed = node_data.copy()
        renamed['node_id'] = renamed['node_id'].replace('_temp', '')
        renamed['label'] = renamed['label'].replace('_temp', '')
        return renamed
    
    def rename_edge(self, edge_data: Dict) -> Dict:
        """
        Remove _temp suffix from edge data (for approval)
        
        Args:
            edge_data: Original edge data with _temp
            
        Returns:
            Edge data with _temp removed
        """
        renamed = edge_data.copy()
        renamed['edge_id'] = renamed['edge_id'].replace('_temp', '')
        renamed['source_node_id'] = renamed['source_node_id'].replace('_temp', '')
        renamed['target_node_id'] = renamed['target_node_id'].replace('_temp', '')
        return renamed

