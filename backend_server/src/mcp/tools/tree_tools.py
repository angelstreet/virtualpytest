"""
Tree Management Tools for MCP

Provides CRUD operations for navigation tree nodes, edges, and subtrees.
These are atomic primitives that can be composed for any workflow:
- AI exploration
- Manual tree building
- Tree refactoring
- Quality assurance
"""

import logging
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter, ErrorCategory


class TreeTools:
    """Navigation tree CRUD operations"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api_client = api_client
        self.formatter = MCPFormatter()
        self.logger = logging.getLogger(__name__)
    
    def create_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a node in navigation tree
        
        Args:
            tree_id: Navigation tree ID
            node_id: Node identifier (optional - auto-generated if omitted)
            label: Node label/name
            type: Node type (default: "screen")
            position: {x, y} coordinates (optional)
            data: Custom metadata (optional)
        
        Returns:
            Created node object
        """
        try:
            tree_id = params['tree_id']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            # Build node payload - backend expects: node_id, label, node_type, data
            node_data = {
                'label': params['label'],
                'node_type': params.get('type', 'screen'),
                'data': params.get('data', {})
            }
            
            # Add node_id if provided
            if 'node_id' in params:
                node_data['node_id'] = params['node_id']
            
            # Add position to data if provided
            if 'position' in params:
                pos = params['position']
                node_data['data']['position'] = pos
                # Also set position_x and position_y for database columns
                node_data['position_x'] = pos.get('x', 0)
                node_data['position_y'] = pos.get('y', 0)
            
            self.logger.info(f"Creating node in tree {tree_id}: {node_data.get('label')}")
            
            # Call backend
            result = self.api_client.post(
                f'/server/navigationTrees/{tree_id}/nodes',
                data=node_data,
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                node = result.get('node', {})
                
                return self.formatter.format_success(
                    f"✅ Node created: {node.get('label')} (ID: {node.get('node_id')})"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to create node: {error_msg}",
                    ErrorCategory.BACKEND,
                    details=result
                )
        
        except Exception as e:
            self.logger.error(f"Error creating node: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def update_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing node
        
        Args:
            tree_id: Navigation tree ID
            node_id: Node identifier to update
            updates: Dict with fields to update (label, position, type, data)
        
        Returns:
            Updated node object
        """
        try:
            tree_id = params['tree_id']
            node_id = params['node_id']
            updates = params['updates']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            self.logger.info(f"Updating node {node_id} in tree {tree_id}")
            
            # STEP 1: Fetch existing node to avoid overwriting data
            existing_result = self.api_client.get(
                f'/server/navigationTrees/{tree_id}/nodes/{node_id}',
                params={'team_id': team_id}
            )
            
            if not existing_result.get('success'):
                return self.formatter.format_error(
                    f"Failed to fetch existing node: {existing_result.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            existing_node = existing_result.get('node', {})
            
            # STEP 2: Merge updates with existing node data
            merged_data = {
                'node_id': node_id,
                'label': updates.get('label', existing_node.get('label')),
                'node_type': updates.get('type', existing_node.get('node_type')),
                'data': existing_node.get('data', {}),  # Start with existing data
                'style': existing_node.get('style', {}),
                'verifications': existing_node.get('verifications', [])
            }
            
            # Merge data field if provided
            if 'data' in updates:
                merged_data['data'].update(updates['data'])
            
            # Handle position - merge into data.position
            if 'position' in updates:
                pos = updates['position']
                merged_data['data']['position'] = pos
                merged_data['position_x'] = pos.get('x', 0)
                merged_data['position_y'] = pos.get('y', 0)
            else:
                # Preserve existing position
                merged_data['position_x'] = existing_node.get('position_x', 0)
                merged_data['position_y'] = existing_node.get('position_y', 0)
            
            # STEP 3: Call backend with merged data
            result = self.api_client.put(
                f'/server/navigationTrees/{tree_id}/nodes/{node_id}',
                data=merged_data,
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                node = result.get('node', {})
                
                return self.formatter.format_success(
                    f"✅ Node updated: {node.get('label')}"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to update node: {error_msg}",
                    ErrorCategory.BACKEND
                )
        
        except Exception as e:
            self.logger.error(f"Error updating node: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def delete_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete a node from navigation tree
        
        Args:
            tree_id: Navigation tree ID
            node_id: Node identifier to delete
        
        Returns:
            Success confirmation
        """
        try:
            tree_id = params['tree_id']
            node_id = params['node_id']
            
            self.logger.info(f"Deleting node {node_id} from tree {tree_id}")
            
            # Call backend
            response = self.api_client.delete(
                f'/server/navigationTrees/{tree_id}/nodes/{node_id}'
            )
            
            if response.status_code == 200 or response.status_code == 204:
                return self.formatter.format_success(
                    f"✅ Node deleted: {node_id}",
                    data={"node_id": node_id}
                )
            else:
                error_data = response.json() if response.text else {}
                return self.formatter.format_error(
                    f"Failed to delete node: {error_data.get('error', response.text)}",
                    ErrorCategory.BACKEND,
                    details=error_data
                )
        
        except Exception as e:
            self.logger.error(f"Error deleting node: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def create_edge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an edge between two nodes
        
        Args:
            tree_id: Navigation tree ID
            source_node_id: Source node ID
            target_node_id: Target node ID
            action_sets: Array of action sets (forward/backward)
            edge_id: Edge identifier (optional - auto-generated if omitted)
        
        Returns:
            Created edge object
        """
        try:
            tree_id = params['tree_id']
            
            # Build edge payload
            edge_data = {
                'source': params['source_node_id'],
                'target': params['target_node_id'],
                'data': {
                    'action_sets': params.get('action_sets', [])
                }
            }
            
            if 'edge_id' in params:
                edge_data['id'] = params['edge_id']
            
            self.logger.info(
                f"Creating edge in tree {tree_id}: "
                f"{params['source_node_id']} → {params['target_node_id']}"
            )
            
            # Call backend
            response = self.api_client.post(
                f'/server/navigationTrees/{tree_id}/edges',
                json=edge_data
            )
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                edge = result.get('edge', result)
                
                return self.formatter.format_success(
                    f"✅ Edge created: {edge.get('source')} → {edge.get('target')}",
                    data={"edge": edge}
                )
            else:
                error_data = response.json() if response.text else {}
                return self.formatter.format_error(
                    f"Failed to create edge: {error_data.get('error', response.text)}",
                    ErrorCategory.BACKEND,
                    details=error_data
                )
        
        except Exception as e:
            self.logger.error(f"Error creating edge: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def update_edge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing edge's actions
        
        Args:
            tree_id: Navigation tree ID
            edge_id: Edge identifier to update
            action_sets: New action sets (replaces existing)
        
        Returns:
            Updated edge object
        """
        try:
            tree_id = params['tree_id']
            edge_id = params['edge_id']
            
            # Build update payload
            updates = {
                'data': {
                    'action_sets': params['action_sets']
                }
            }
            
            self.logger.info(f"Updating edge {edge_id} in tree {tree_id}")
            
            # Call backend
            response = self.api_client.patch(
                f'/server/navigationTrees/{tree_id}/edges/{edge_id}',
                json=updates
            )
            
            if response.status_code == 200:
                result = response.json()
                edge = result.get('edge', result)
                
                return self.formatter.format_success(
                    f"✅ Edge updated: {edge.get('id')}",
                    data={"edge": edge}
                )
            else:
                error_data = response.json() if response.text else {}
                return self.formatter.format_error(
                    f"Failed to update edge: {error_data.get('error', response.text)}",
                    ErrorCategory.BACKEND,
                    details=error_data
                )
        
        except Exception as e:
            self.logger.error(f"Error updating edge: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def delete_edge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete an edge from navigation tree
        
        Args:
            tree_id: Navigation tree ID
            edge_id: Edge identifier to delete
        
        Returns:
            Success confirmation
        """
        try:
            tree_id = params['tree_id']
            edge_id = params['edge_id']
            
            self.logger.info(f"Deleting edge {edge_id} from tree {tree_id}")
            
            # Call backend
            response = self.api_client.delete(
                f'/server/navigationTrees/{tree_id}/edges/{edge_id}'
            )
            
            if response.status_code == 200 or response.status_code == 204:
                return self.formatter.format_success(
                    f"✅ Edge deleted: {edge_id}",
                    data={"edge_id": edge_id}
                )
            else:
                error_data = response.json() if response.text else {}
                return self.formatter.format_error(
                    f"Failed to delete edge: {error_data.get('error', response.text)}",
                    ErrorCategory.BACKEND,
                    details=error_data
                )
        
        except Exception as e:
            self.logger.error(f"Error deleting edge: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def create_subtree(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a subtree for a parent node
        
        Args:
            parent_tree_id: Parent tree ID
            parent_node_id: Parent node ID to attach subtree to
            subtree_name: Name for the subtree
        
        Returns:
            Created subtree with new tree_id
        """
        try:
            parent_tree_id = params['parent_tree_id']
            parent_node_id = params['parent_node_id']
            subtree_name = params['subtree_name']
            
            self.logger.info(
                f"Creating subtree '{subtree_name}' for node {parent_node_id} "
                f"in tree {parent_tree_id}"
            )
            
            # Build subtree payload
            subtree_data = {
                'name': subtree_name
            }
            
            # Call backend
            response = self.api_client.post(
                f'/server/navigationTrees/{parent_tree_id}/nodes/{parent_node_id}/subtrees',
                json=subtree_data
            )
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                subtree = result.get('tree', result)
                
                return self.formatter.format_success(
                    f"✅ Subtree created: {subtree_name} (ID: {subtree.get('id')})",
                    data={"subtree": subtree, "subtree_tree_id": subtree.get('id')}
                )
            else:
                error_data = response.json() if response.text else {}
                return self.formatter.format_error(
                    f"Failed to create subtree: {error_data.get('error', response.text)}",
                    ErrorCategory.BACKEND,
                    details=error_data
                )
        
        except Exception as e:
            self.logger.error(f"Error creating subtree: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)

