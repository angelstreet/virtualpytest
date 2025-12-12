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
from typing import Dict, Any, List
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter, ErrorCategory
from ..utils.verification_validator import VerificationValidator
from ..utils.action_validator import ActionValidator


class TreeTools:
    """Navigation tree CRUD operations"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api_client = api_client
        self.formatter = MCPFormatter()
        self.logger = logging.getLogger(__name__)
        self.verification_validator = VerificationValidator(api_client)
        self.action_validator = ActionValidator(api_client)
    
    def _normalize_action_params(self, action_sets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize action parameter names to canonical format before saving to DB.
        
        Conversions:
        - click_element: text/selector → element_id
        - hover_element: text/element_id → selector
        - find_element: text/element_id → selector
        - input_text: element_id → selector
        
        This ensures DB only stores canonical parameter names.
        """
        if not action_sets:
            return action_sets
        
        normalized = []
        for action_set in action_sets:
            normalized_set = action_set.copy()
            
            # Normalize actions
            if 'actions' in normalized_set:
                normalized_set['actions'] = self._normalize_action_list(normalized_set['actions'])
            
            # Normalize retry_actions
            if 'retry_actions' in normalized_set:
                normalized_set['retry_actions'] = self._normalize_action_list(normalized_set['retry_actions'])
            
            # Normalize failure_actions
            if 'failure_actions' in normalized_set:
                normalized_set['failure_actions'] = self._normalize_action_list(normalized_set['failure_actions'])
            
            normalized.append(normalized_set)
        
        return normalized
    
    def _normalize_action_list(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize parameter names in an action list"""
        normalized = []
        for action in actions:
            # Deep copy to avoid modifying original
            import copy
            normalized_action = copy.deepcopy(action)
            command = normalized_action.get('command')
            params = normalized_action.get('params', {})
            
            # Normalize based on command
            if command == 'click_element':
                # Standardize to element_id
                if 'text' in params or 'selector' in params:
                    element_id = params.get('element_id') or params.get('selector') or params.get('text')
                    # Remove old keys
                    params.pop('text', None)
                    params.pop('selector', None)
                    params['element_id'] = element_id
            
            elif command in ['hover_element', 'find_element']:
                # Standardize to selector
                if 'text' in params or 'element_id' in params:
                    selector = params.get('selector') or params.get('element_id') or params.get('text')
                    # Remove old keys
                    params.pop('text', None)
                    params.pop('element_id', None)
                    params['selector'] = selector
            
            elif command == 'input_text':
                # Standardize to selector (text param is for input content, not selector)
                if 'element_id' in params:
                    selector = params.get('selector') or params.get('element_id')
                    # Remove old key
                    params.pop('element_id', None)
                    params['selector'] = selector
            
            normalized_action['params'] = params
            normalized.append(normalized_action)
        
        return normalized
    
    def create_node(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a node in navigation tree. Remember to add verifications and test them after creation.
        
        Example: create_node(tree_id='abc', node_id='home', label='Home Screen')
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'node_id': str (OPTIONAL - node identifier auto-generated if omitted),
                'label': str (REQUIRED - node label or name),
                'type': str (OPTIONAL - node type default screen),
                'position': dict (OPTIONAL - x y coordinates),
                'data': dict (OPTIONAL - custom metadata)
            }
        
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
                node_id_str = node.get('node_id') or node_data.get('node_id')
                return {"content": [{"type": "text", "text": f"created node:{node_id_str}"}], "isError": False}
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
        Update an existing node. Verifications in updates will be validated against available device controllers.
        
        Example: update_node(tree_id='abc', node_id='home', updates={'label': 'Home Screen New'})
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'node_id': str (REQUIRED - node identifier to update),
                'updates': dict (REQUIRED - fields to update like label position type or data)
            }
        
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
            
            # STEP 1.5: VALIDATE VERIFICATIONS if provided (check both locations)
            verifications_to_validate = updates.get('verifications') or updates.get('data', {}).get('verifications')
            if verifications_to_validate:
                # Get userinterface to determine device_model
                userinterface_result = self.api_client.get(
                    f'/server/navigationTrees/{tree_id}',
                    params={'team_id': team_id}
                )
                
                if userinterface_result.get('success'):
                    tree_data = userinterface_result.get('tree', {})
                    userinterface_id = tree_data.get('userinterface_id')
                    
                    if userinterface_id:
                        ui_result = self.api_client.get(
                            f'/server/userinterfaces/{userinterface_id}',
                            params={'team_id': team_id}
                        )
                        
                        if ui_result.get('success'):
                            device_model = ui_result.get('userinterface', {}).get('device_model', 'unknown')
                            
                            # Validate verifications
                            is_valid, errors, warnings = self.verification_validator.validate_verifications(
                                verifications_to_validate,
                                device_model
                            )
                            
                            if not is_valid:
                                # Build error message with helpful info
                                error_msg = "❌ Invalid verification command(s):\n\n"
                                error_msg += "\n".join(errors)
                                error_msg += "\n\n" + self.verification_validator.get_valid_commands_for_display(device_model)
                                
                                return self.formatter.format_error(
                                    error_msg,
                                    ErrorCategory.VALIDATION
                                )
                            
                            # Show warnings if any
                            if warnings:
                                self.logger.warning(f"Verification warnings for node {node_id}:")
                                for warning in warnings:
                                    self.logger.warning(f"  {warning}")
            
            existing_node = existing_result.get('node', {})
            
            # STEP 2: Extract verifications - can be in updates.verifications OR updates.data.verifications
            # Backend expects verifications at root level, not in data
            verifications = updates.get('verifications')
            if verifications is None:
                verifications = updates.get('data', {}).get('verifications')
            if verifications is None:
                verifications = existing_node.get('verifications', [])
            
            # STEP 3: Merge updates with existing node data
            merged_data = {
                'node_id': node_id,
                'label': updates.get('label', existing_node.get('label')),
                'node_type': updates.get('type', existing_node.get('node_type')),
                'data': existing_node.get('data', {}),  # Start with existing data
                'style': existing_node.get('style', {}),
                'verifications': verifications  # Root level verifications
            }
            
            # Merge data field if provided (excluding verifications - they go at root level)
            if 'data' in updates:
                data_to_merge = {k: v for k, v in updates['data'].items() if k != 'verifications'}
                merged_data['data'].update(data_to_merge)
            
            # Clean up any verifications that may exist in data (backend expects root level only)
            merged_data['data'].pop('verifications', None)
            
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
                return {"content": [{"type": "text", "text": f"updated node:{node_id}"}], "isError": False}
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
        Delete a node from navigation tree.
        
        Example: delete_node(tree_id='abc', node_id='home')
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'node_id': str (REQUIRED - node identifier to delete)
            }
        
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
                return {"content": [{"type": "text", "text": f"deleted node:{node_id}"}], "isError": False}
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
        
        Example: create_edge(tree_id='abc', source_node_id='home', target_node_id='settings', source_label='home', target_label='settings', action_sets=[...])
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'source_node_id': str (REQUIRED - source node ID),
                'target_node_id': str (REQUIRED - target node ID),
                'source_label': str (REQUIRED - source node label),
                'target_label': str (REQUIRED - target node label),
                'action_sets': list (REQUIRED - array of action sets with bidirectional actions)
            }
        
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
            
            # ✅ NORMALIZE: Convert parameter names to canonical format before saving
            action_sets = self._normalize_action_params(action_sets)
            
            # ✅ VALIDATION: Validate action commands if action_sets provided
            if action_sets:
                # Get userinterface to determine device_model
                userinterface_result = self.api_client.get(
                    f'/server/navigationTrees/{tree_id}',
                    params={'team_id': team_id}
                )
                
                if userinterface_result.get('success'):
                    tree_data = userinterface_result.get('tree', {})
                    userinterface_id = tree_data.get('userinterface_id')
                    
                    if userinterface_id:
                        ui_result = self.api_client.get(
                            f'/server/userinterfaces/{userinterface_id}',
                            params={'team_id': team_id}
                        )
                        
                        if ui_result.get('success'):
                            device_model = ui_result.get('userinterface', {}).get('device_model', 'unknown')
                            
                            # Validate action commands
                            is_valid, errors, warnings = self.action_validator.validate_action_sets(
                                action_sets,
                                device_model
                            )
                            
                            if not is_valid:
                                # Build error message with helpful info
                                error_msg = "❌ Invalid action command(s):\n\n"
                                error_msg += "\n".join(errors)
                                error_msg += "\n\n" + self.action_validator.get_valid_commands_for_display(device_model)
                                
                                return self.formatter.format_error(
                                    error_msg,
                                    ErrorCategory.VALIDATION
                                )
                            
                            # Show warnings if any
                            if warnings:
                                self.logger.warning(f"Action warnings for edge {source_node_id} → {target_node_id}:")
                                for warning in warnings:
                                    self.logger.warning(f"  {warning}")
            
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
                    'is_conditional_primary': params.get('is_conditional_primary', False),
                    'enable_sibling_shortcuts': params.get('enable_sibling_shortcuts', False)  # Sibling shortcuts for bottom nav/tab bars
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
                
                return {"content": [{"type": "text", "text": f"created edge:{permanent_edge_id} {edge.get('source_node_id')}→{edge.get('target_node_id')}"}], "isError": False}
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
        Update an existing edge's actions. Must use same format as create_edge.
        
        Example: update_edge(tree_id='abc', edge_id='edge1', action_sets=[...])
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'edge_id': str (REQUIRED - edge identifier to update),
                'action_sets': list (REQUIRED - new action sets to replace existing)
            }
        
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
            
            # STEP 2: Validate action commands if provided
            action_sets = params['action_sets']
            
            # ✅ NORMALIZE: Convert parameter names to canonical format before saving
            action_sets = self._normalize_action_params(action_sets)
            
            # ✅ VALIDATION: Validate action commands before updating
            if action_sets:
                # Get userinterface to determine device_model
                userinterface_result = self.api_client.get(
                    f'/server/navigationTrees/{tree_id}',
                    params={'team_id': team_id}
                )
                
                if userinterface_result.get('success'):
                    tree_data = userinterface_result.get('tree', {})
                    userinterface_id = tree_data.get('userinterface_id')
                    
                    if userinterface_id:
                        ui_result = self.api_client.get(
                            f'/server/userinterfaces/{userinterface_id}',
                            params={'team_id': team_id}
                        )
                        
                        if ui_result.get('success'):
                            device_model = ui_result.get('userinterface', {}).get('device_model', 'unknown')
                            
                            # Validate action commands
                            is_valid, errors, warnings = self.action_validator.validate_action_sets(
                                action_sets,
                                device_model
                            )
                            
                            if not is_valid:
                                # Build error message with helpful info
                                error_msg = "❌ Invalid action command(s):\n\n"
                                error_msg += "\n".join(errors)
                                error_msg += "\n\n" + self.action_validator.get_valid_commands_for_display(device_model)
                                
                                return self.formatter.format_error(
                                    error_msg,
                                    ErrorCategory.VALIDATION
                                )
                            
                            # Show warnings if any
                            if warnings:
                                self.logger.warning(f"Action warnings for edge {edge_id}:")
                                for warning in warnings:
                                    self.logger.warning(f"  {warning}")
            
            # STEP 3: Merge updates with existing edge data
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
                    'is_conditional_primary': params.get('is_conditional_primary', existing_data.get('is_conditional_primary', False)),
                    'enable_sibling_shortcuts': params.get('enable_sibling_shortcuts', existing_data.get('enable_sibling_shortcuts', False))  # Sibling shortcuts for bottom nav/tab bars
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
                return {"content": [{"type": "text", "text": f"updated edge:{edge.get('edge_id')}"}], "isError": False}
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
        Delete an edge from navigation tree.
        
        Example: delete_edge(tree_id='abc', edge_id='edge1')
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'edge_id': str (REQUIRED - edge identifier to delete)
            }
        
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
                return {"content": [{"type": "text", "text": f"deleted edge:{edge_id}"}], "isError": False}
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
        Create a subtree for a parent node.
        
        Example: create_subtree(parent_tree_id='abc', parent_node_id='menu', subtree_name='Menu Options')
        
        Args:
            params: {
                'parent_tree_id': str (REQUIRED - parent tree ID),
                'parent_node_id': str (REQUIRED - parent node ID to attach subtree),
                'subtree_name': str (REQUIRED - name for the subtree)
            }
        
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
                return {"content": [{"type": "text", "text": f"created subtree:{subtree_id}"}], "isError": False}
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
        Get a specific node by ID.
        
        Example: get_node(tree_id='abc', node_id='home')
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'node_id': str (REQUIRED - node identifier)
            }
        
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
                return {
                    "content": [{"type": "text", "text": f"node:{node.get('node_id')}"}],
                    "isError": False,
                    "node": {
                        'node_id': node.get('node_id'),
                        'label': node.get('label'),
                        'type': node.get('node_type'),
                        'data': node.get('data', {}),
                        'verifications': node.get('verifications', [])
                    }
                }
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
        Get a specific edge by ID.
        
        Example: get_edge(tree_id='abc', edge_id='edge1')
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'edge_id': str (REQUIRED - edge identifier)
            }
        
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
                return {
                    "content": [{"type": "text", "text": f"edge:{edge.get('source_node_id')}→{edge.get('target_node_id')}"}],
                    "isError": False,
                    "edge": {
                        'edge_id': edge.get('edge_id'),
                        'source_node_id': edge.get('source_node_id'),
                        'target_node_id': edge.get('target_node_id'),
                        'action_sets': edge.get('action_sets', [])
                    }
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Failed to get edge: {error_msg}",
                    ErrorCategory.BACKEND
                )
        
        except Exception as e:
            self.logger.error(f"Error getting edge: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)
    
    def save_node_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take screenshot and save it to a specific node. Wraps screenshot capture and node update into single operation.
        
        Example: save_node_screenshot(tree_id='abc', node_id='home', label='Home Screen', host_name='sunri-pi1', device_id='device1', userinterface_name='google_tv')
        
        Args:
            params: {
                'tree_id': str (REQUIRED - navigation tree ID),
                'node_id': str (REQUIRED - node identifier to attach screenshot),
                'label': str (REQUIRED - node label used as filename),
                'host_name': str (REQUIRED - host where device is connected),
                'device_id': str (REQUIRED - device identifier),
                'userinterface_name': str (REQUIRED - interface name for organizing screenshots)
            }
        
        Returns:
            Success with screenshot URL and node ID
        """
        try:
            import re
            import time
            
            tree_id = params['tree_id']
            node_id = params['node_id']
            label = params['label']
            host_name = params['host_name']
            device_id = params['device_id']
            userinterface_name = params['userinterface_name']
            team_id = params.get('team_id', '7fdeb4bb-3639-4ec3-959f-b54769a219ce')
            
            self.logger.info(f"Saving screenshot for node {node_id} ({label}) in tree {tree_id}")
            
            # STEP 1: Sanitize filename (same as frontend - useNode.ts line 124)
            # Remove spaces and special characters
            sanitized_filename = re.sub(r'\s+', '_', label)
            sanitized_filename = re.sub(r'[^a-zA-Z0-9_-]', '', sanitized_filename)
            
            # STEP 2: Take and save screenshot (same as frontend - useNode.ts line 126-137)
            screenshot_result = self.api_client.post(
                '/server/av/saveScreenshot',
                data={
                    'host_name': host_name,
                    'device_id': device_id,
                    'filename': sanitized_filename,
                    'userinterface_name': userinterface_name
                }
            )
            
            if not screenshot_result.get('success'):
                error_msg = screenshot_result.get('message', 'Failed to save screenshot')
                return self.formatter.format_error(
                    f"Screenshot capture failed: {error_msg}",
                    ErrorCategory.BACKEND
                )
            
            screenshot_url = screenshot_result.get('screenshot_url')
            if not screenshot_url:
                return self.formatter.format_error(
                    "Screenshot saved but no URL returned",
                    ErrorCategory.BACKEND
                )
            
            # STEP 3: Read current node to get existing data (avoid overwriting other fields)
            node_result = self.api_client.get(
                f'/server/navigationTrees/{tree_id}/nodes/{node_id}',
                params={'team_id': team_id}
            )
            
            if not node_result.get('success'):
                return self.formatter.format_error(
                    f"Screenshot saved but failed to read node for update: {node_result.get('error', 'Unknown error')}\n"
                    f"Screenshot URL: {screenshot_url}\n"
                    f"You may need to manually update the node.",
                    ErrorCategory.BACKEND
                )
            
            # STEP 4: Merge screenshot into existing data and update node
            # Screenshot must be in data object, not top-level (database schema: data jsonb column)
            current_data = node_result.get('node', {}).get('data', {})
            current_data['screenshot'] = screenshot_url
            current_data['screenshot_timestamp'] = int(time.time() * 1000)  # Force cache bust
            
            update_result = self.api_client.put(
                f'/server/navigationTrees/{tree_id}/nodes/{node_id}',
                data={
                    'data': current_data
                },
                params={'team_id': team_id}
            )
            
            if update_result.get('success'):
                return {"content": [{"type": "text", "text": f"screenshot saved:{node_id}"}], "isError": False}
            else:
                error_msg = update_result.get('error', 'Unknown error')
                return self.formatter.format_error(
                    f"Screenshot saved but node update failed: {error_msg}\n"
                    f"Screenshot URL: {screenshot_url}\n"
                    f"You may need to manually update the node.",
                    ErrorCategory.BACKEND
                )
        
        except Exception as e:
            self.logger.error(f"Error saving node screenshot: {e}", exc_info=True)
            return self.formatter.format_error(str(e), ErrorCategory.BACKEND)

