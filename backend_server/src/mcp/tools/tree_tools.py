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
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            self.logger.info(f"Deleting node {node_id} from tree {tree_id}")
            
            # Call backend
            result = self.api_client.delete(
                f'/server/navigationTrees/{tree_id}/nodes/{node_id}',
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                return self.formatter.format_success(
                    f"✅ Node deleted: {node_id}"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to delete node: {error_msg}",
                    ErrorCategory.BACKEND
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
            label: Edge label (optional - auto-generated if omitted)
        
        Returns:
            Created edge object
        """
        try:
            tree_id = params['tree_id']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            # Build edge payload - backend expects: edge_id, source_node_id, target_node_id, action_sets, default_action_set_id
            action_sets = params.get('action_sets', [])
            
            # Determine default_action_set_id (first action set by default)
            default_action_set_id = action_sets[0]['id'] if action_sets else 'forward'
            
            # Generate label from action set labels if not provided
            # Format: "source→target" (matches frontend format in useNavigationEditor.ts line 307)
            label = params.get('label')
            if not label and action_sets and len(action_sets) > 0:
                # Extract labels from first action set: "source → target" → "source→target"
                action_set_label = action_sets[0].get('label', '')
                label = action_set_label.replace(' → ', '→').replace(' ', '')
            
            edge_data = {
                'source_node_id': params['source_node_id'],
                'target_node_id': params['target_node_id'],
                'action_sets': action_sets,
                'default_action_set_id': default_action_set_id,
                'label': label or '',  # ✅ TOP-LEVEL label field (matches frontend)
                'final_wait_time': params.get('final_wait_time', 2000),  # ✅ TOP-LEVEL final_wait_time (matches frontend line 326)
                'data': {
                    # ✅ ACCEPT handle params or default to simple vertical (matches frontend lines 336-341)
                    # Available handles: bottom-source, top-target, left-source, left-target, right-source, right-target,
                    #                    top-left-menu-source, top-right-menu-target, bottom-left-menu-target, bottom-right-menu-source
                    'sourceHandle': params.get('sourceHandle', 'bottom-source'),  # Default: simple vertical from bottom
                    'targetHandle': params.get('targetHandle', 'top-target'),     # Default: simple vertical to top
                    'priority': params.get('priority', 'p3'),  # Default priority p3
                    'is_conditional': params.get('is_conditional', False),  # ✅ Matches frontend line 327
                    'is_conditional_primary': params.get('is_conditional_primary', False)
                }
            }
            
            # Add edge_id if provided
            if 'edge_id' in params:
                edge_data['edge_id'] = params['edge_id']
            
            self.logger.info(
                f"Creating edge in tree {tree_id}: "
                f"{params['source_node_id']} → {params['target_node_id']}"
            )
            
            # Call backend
            result = self.api_client.post(
                f'/server/navigationTrees/{tree_id}/edges',
                data=edge_data,
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                edge = result.get('edge', {})
                
                return self.formatter.format_success(
                    f"✅ Edge created: {edge.get('source_node_id')} → {edge.get('target_node_id')}"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to create edge: {error_msg}",
                    ErrorCategory.BACKEND
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
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            self.logger.info(f"Updating edge {edge_id} in tree {tree_id}")
            
            # STEP 1: Fetch existing edge to avoid overwriting data
            existing_result = self.api_client.get(
                f'/server/navigationTrees/{tree_id}/edges/{edge_id}',
                params={'team_id': team_id}
            )
            
            if not existing_result.get('success'):
                return self.formatter.format_error(
                    f"Failed to fetch existing edge: {existing_result.get('error')}",
                    ErrorCategory.BACKEND
                )
            
            existing_edge = existing_result.get('edge', {})
            
            # STEP 2: Merge updates with existing edge data
            action_sets = params['action_sets']
            default_action_set_id = action_sets[0]['id'] if action_sets else existing_edge.get('default_action_set_id', 'forward')
            
            # Generate label from action_sets if not provided (same logic as create_edge)
            label = params.get('label')
            if not label and action_sets and len(action_sets) > 0:
                action_set_label = action_sets[0].get('label', '')
                label = action_set_label.replace(' → ', '→').replace(' ', '')
            if not label:
                label = existing_edge.get('label', '')
            
            # Merge existing data with updates
            existing_data = existing_edge.get('data', {})
            
            merged_data = {
                'edge_id': edge_id,
                'source_node_id': existing_edge.get('source_node_id'),
                'target_node_id': existing_edge.get('target_node_id'),
                'action_sets': action_sets,
                'default_action_set_id': default_action_set_id,
                'label': label,  # ✅ Use generated or provided label
                'data': {
                    # Allow overriding metadata or preserve existing
                    'sourceHandle': params.get('sourceHandle', existing_data.get('sourceHandle', 'bottom-source')),
                    'targetHandle': params.get('targetHandle', existing_data.get('targetHandle', 'top-target')),
                    'priority': params.get('priority', existing_data.get('priority', 'p3')),
                    'is_conditional': params.get('is_conditional', existing_data.get('is_conditional', False)),
                    'is_conditional_primary': params.get('is_conditional_primary', existing_data.get('is_conditional_primary', False))
                },
                'final_wait_time': params.get('final_wait_time', existing_edge.get('final_wait_time') or 2000)  # ✅ Allow override, default to 2000 if missing
            }
            
            # STEP 3: Call backend with merged data
            result = self.api_client.put(
                f'/server/navigationTrees/{tree_id}/edges/{edge_id}',
                data=merged_data,
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                edge = result.get('edge', {})
                
                return self.formatter.format_success(
                    f"✅ Edge updated: {edge.get('edge_id')}"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to update edge: {error_msg}",
                    ErrorCategory.BACKEND
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
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            self.logger.info(f"Deleting edge {edge_id} from tree {tree_id}")
            
            # Call backend
            result = self.api_client.delete(
                f'/server/navigationTrees/{tree_id}/edges/{edge_id}',
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                return self.formatter.format_success(
                    f"✅ Edge deleted: {edge_id}"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to delete edge: {error_msg}",
                    ErrorCategory.BACKEND
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
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            self.logger.info(
                f"Creating subtree '{subtree_name}' for node {parent_node_id} "
                f"in tree {parent_tree_id}"
            )
            
            # Build subtree payload
            subtree_data = {
                'name': subtree_name
            }
            
            # Call backend
            result = self.api_client.post(
                f'/server/navigationTrees/{parent_tree_id}/nodes/{parent_node_id}/subtrees',
                data=subtree_data,
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                subtree = result.get('tree', {})
                subtree_id = subtree.get('id')
                
                return self.formatter.format_success(
                    f"✅ Subtree created: {subtree_name} (ID: {subtree_id})"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to create subtree: {error_msg}",
                    ErrorCategory.BACKEND
                )
        
        except Exception as e:
            self.logger.error(f"Error creating subtree: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)

