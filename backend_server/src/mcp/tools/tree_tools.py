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
            
            # Build node payload - backend expects: label, node_type, data, node_id
            node_data = {
                'label': params['label'],
                'node_id': params['label'],  # node_id is always the label
                'node_type': params.get('type', 'screen'),
                'data': params.get('data', {})
            }
            
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
                # Return the node_id string (NOT the database UUID!)
                node_id_str = node.get('node_id') or node_data.get('node_id')
                
                return self.formatter.format_success(
                    f"✅ Node created: {node.get('label')} (node_id: '{node_id_str}')\n"
                    f"   Use node_id='{node_id_str}' when creating edges (NOT the database UUID!)"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to create node: {error_msg}",
                    ErrorCategory.BACKEND
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
            tree_id: Navigation tree ID (REQUIRED)
            source_node_id: Source node_id string (REQUIRED) - USE 'node_id' field from list_navigation_nodes
                           Example: "home" (NOT the UUID from 'id' field!)
            target_node_id: Target node_id string (REQUIRED) - USE 'node_id' field from list_navigation_nodes
                           Example: "tv_guide" (NOT the UUID from 'id' field!)
            source_label: Source node label (REQUIRED) - same as source_node_id for simple nodes
            target_label: Target node label (REQUIRED) - same as target_node_id for simple nodes
            action_sets: Array of action sets with CORRECT FORMAT for each controller type:
                         
                         REMOTE (infrared):
                         {
                           "id": "home_to_settings",
                           "label": "home → settings",
                           "actions": [
                             {
                               "command": "press_key",
                               "action_type": "remote",
                               "params": {"key": "RIGHT"}
                             }
                           ],
                           "retry_actions": [],
                           "failure_actions": []
                         }
                         
                         WEB (playwright):
                         {
                           "id": "home_to_settings",
                           "label": "home → settings",
                           "actions": [
                             {
                               "command": "click_element",
                               "params": {"element_id": "Settings Button"}
                             }
                           ],
                           "retry_actions": [],
                           "failure_actions": []
                         }
                         
                         ADB/MOBILE:
                         {
                           "id": "home_to_settings",
                           "label": "home → settings",
                           "actions": [
                             {
                               "command": "click_element",
                               "params": {"text": "Settings Tab"}
                             }
                           ],
                           "retry_actions": [],
                           "failure_actions": []
                         }
                         
                         ⚠️ IMPORTANT: Do NOT use "delay" at action level or "wait_time" in params
                         unless specifically required by the controller command.
            
            edge_id: Edge identifier (optional - auto-generated if omitted)
            label: Edge label (optional - auto-generated from labels)
            priority: Edge priority p1/p2/p3 (optional - default p3)
        
        IMPORTANT: When calling list_navigation_nodes, the response contains TWO ID fields:
            - 'node_id': "home" ← USE THIS for source_node_id and target_node_id
            - 'id': "ce97c317-7394-466d-b20d-328a5d53e479" ← DO NOT USE THIS (database UUID)
        
        Example:
            list_navigation_nodes returns:
                • home (id: ce97c317-7394-466d-b20d-328a5d53e479, type: screen)
                           ↑ DO NOT USE                ↑ USE THIS
            
            Correct call:
                create_edge(
                    source_node_id="home",      ← Correct! Uses node_id string
                    target_node_id="tv_guide",  ← Correct! Uses node_id string
                    source_label="home",
                    target_label="tv_guide",
                    ...
                )
            
            WRONG call:
                create_edge(
                    source_node_id="ce97c317-7394-466d-b20d-328a5d53e479",  ← WRONG! This is the database UUID
                    target_node_id="3a90bcb0-cd5c-4c80-bd7a-4b7ef9869744",  ← WRONG! This is the database UUID
                    ...
                )
        
        Returns:
            Created edge object
        """
        try:
            import uuid
            import re
            tree_id = params['tree_id']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            source_label = params['source_label']  # REQUIRED - no fetch
            target_label = params['target_label']  # REQUIRED - no fetch
            
            # ✅ VALIDATION: Ensure source_node_id and target_node_id are node_id strings, not database UUIDs
            source_node_id = params['source_node_id']
            target_node_id = params['target_node_id']
            
            # Check if user provided UUID instead of node_id (UUID format: 8-4-4-4-12 hex digits)
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            
            if re.match(uuid_pattern, source_node_id):
                raise ValueError(
                    f"source_node_id must be the node_id string (e.g., 'home'), not database UUID '{source_node_id}'. "
                    f"Use the 'node_id' field from list_navigation_nodes, not the 'id' field."
                )
            
            if re.match(uuid_pattern, target_node_id):
                raise ValueError(
                    f"target_node_id must be the node_id string (e.g., 'tv_guide'), not database UUID '{target_node_id}'. "
                    f"Use the 'node_id' field from list_navigation_nodes, not the 'id' field."
                )
            
            # Build edge payload - backend expects: edge_id, source_node_id, target_node_id, action_sets, default_action_set_id
            action_sets = params.get('action_sets', [])
            
            # Clean labels for ID format (matches frontend useNavigationEditor.ts line 300-301)
            clean_source = re.sub(r'[^a-z0-9]', '_', source_label.lower())
            clean_target = re.sub(r'[^a-z0-9]', '_', target_label.lower())
            
            # Auto-generate action_set id, label, and empty arrays if missing (matches frontend useNavigationEditor.ts line 310-322)
            for i, action_set in enumerate(action_sets):
                if i == 0:
                    # Forward direction
                    if 'id' not in action_set or not action_set['id']:
                        action_set['id'] = f"{clean_source}_to_{clean_target}"
                    if 'label' not in action_set or not action_set['label']:
                        action_set['label'] = f"{source_label} → {target_label}"
                elif i == 1:
                    # Backward direction
                    if 'id' not in action_set or not action_set['id']:
                        action_set['id'] = f"{clean_target}_to_{clean_source}"
                    if 'label' not in action_set or not action_set['label']:
                        action_set['label'] = f"{target_label} → {source_label}"
                
                # Always ensure retry_actions and failure_actions exist (frontend always includes these)
                if 'retry_actions' not in action_set:
                    action_set['retry_actions'] = []
                if 'failure_actions' not in action_set:
                    action_set['failure_actions'] = []
            
            # Determine default_action_set_id (first action set by default)
            default_action_set_id = action_sets[0]['id'] if action_sets else 'forward'
            
            # Auto-generate top-level edge label (matches frontend useNavigationEditor.ts line 307)
            label = params.get('label') or f"{source_label}→{target_label}"
            
            edge_data = {
                'source_node_id': source_node_id,  # ✅ Use validated node_id
                'target_node_id': target_node_id,  # ✅ Use validated node_id
                'action_sets': action_sets,
                'default_action_set_id': default_action_set_id,
                'label': label or '',  # ✅ TOP-LEVEL label field (matches frontend)
                'final_wait_time': params.get('final_wait_time', 2000),  # ✅ TOP-LEVEL final_wait_time (matches frontend line 326)
                'data': {
                    # ✅ FIXED handles - only menu handles supported
                    'sourceHandle': 'bottom-right-menu-source',  # Fixed: menu handle from bottom-right
                    'targetHandle': 'top-right-menu-target',     # Fixed: menu handle to top-right
                    'priority': params.get('priority', 'p3'),  # Default priority p3
                    'is_conditional': params.get('is_conditional', False),
                    'is_conditional_primary': params.get('is_conditional_primary', False)
                }
            }
            
            # edge_id is required by database - generate UUID if not provided
            if 'edge_id' in params:
                edge_data['edge_id'] = params['edge_id']
            else:
                # Generate UUID for edge_id field
                edge_data['edge_id'] = str(uuid.uuid4())
            
            self.logger.info(
                f"Creating edge in tree {tree_id}: "
                f"{source_node_id} → {target_node_id}"
            )
            
            # Call backend
            result = self.api_client.post(
                f'/server/navigationTrees/{tree_id}/edges',
                data=edge_data,
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                edge = result.get('edge', {})
                # Return permanent database IDs for both source and target nodes
                permanent_edge_id = edge.get('edge_id') or edge.get('id')
                
                return self.formatter.format_success(
                    f"✅ Edge created: {edge.get('source_node_id')} → {edge.get('target_node_id')} (ID: {permanent_edge_id})"
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
                    'sourceHandle': params.get('sourceHandle', existing_data.get('sourceHandle', 'bottom-right-menu-source')),
                    'targetHandle': params.get('targetHandle', existing_data.get('targetHandle', 'top-right-menu-target')),
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
    
    def get_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a specific node by ID
        
        Args:
            tree_id: Navigation tree ID
            node_id: Node identifier
        
        Returns:
            Full node object with all fields
        """
        try:
            tree_id = params['tree_id']
            node_id = params['node_id']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            result = self.api_client.get(
                f'/server/navigationTrees/{tree_id}/nodes/{node_id}',
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                node = result.get('node', {})
                return self.formatter.format_success({
                    'node_id': node.get('node_id'),
                    'label': node.get('label'),
                    'type': node.get('node_type'),
                    'position': {'x': node.get('position_x'), 'y': node.get('position_y')},
                    'data': node.get('data', {}),
                    'verifications': node.get('verifications', [])
                })
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to get node: {error_msg}",
                    ErrorCategory.BACKEND
                )
        
        except Exception as e:
            self.logger.error(f"Error getting node: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def get_edge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a specific edge by ID
        
        Args:
            tree_id: Navigation tree ID
            edge_id: Edge identifier
        
        Returns:
            Full edge object with all fields
        """
        try:
            tree_id = params['tree_id']
            edge_id = params['edge_id']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            result = self.api_client.get(
                f'/server/navigationTrees/{tree_id}/edges/{edge_id}',
                params={'team_id': team_id}
            )
            
            if result.get('success'):
                edge = result.get('edge', {})
                return self.formatter.format_success({
                    'edge_id': edge.get('edge_id'),
                    'source_node_id': edge.get('source_node_id'),
                    'target_node_id': edge.get('target_node_id'),
                    'label': edge.get('label'),
                    'action_sets': edge.get('action_sets', []),
                    'default_action_set_id': edge.get('default_action_set_id'),
                    'final_wait_time': edge.get('final_wait_time'),
                    'data': edge.get('data', {})
                })
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to get edge: {error_msg}",
                    ErrorCategory.BACKEND
                )
        
        except Exception as e:
            self.logger.error(f"Error getting edge: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)

