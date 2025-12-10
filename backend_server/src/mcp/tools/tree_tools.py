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
        Create a node in navigation tree
        
        ⚠️ REMINDER: Add verifications and test them
        
        After creating a node, consider:
        1. Add verifications to the node (unique stable elements)
        2. Test them: verify_node(node_id='...', tree_id='...')
        3. Create edges to/from this node
        4. Test each edge: get_edge() then execute_device_action()
        
        **Tools for validation:**
        - verify_node(node_id, tree_id) - Test node verifications
        - get_edge(edge_id, tree_id) - Get edge details
        - execute_device_action(actions=[...]) - Test edge actions
        
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
        Update an existing node
        
        Args:
            tree_id: Navigation tree ID
            node_id: Node identifier to update
            updates: Dict with fields to update (label, position, type, data)
        
        Returns:
            Updated node object
            
        ⚠️ VERIFICATION VALIDATION:
        If updates contain 'data' with 'verifications', they will be validated
        against available device controllers before saving.
        
        To see valid verification commands, call:
            list_verifications(device_id='device_id', host_name='host_name')
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
            
            # STEP 1.5: VALIDATE VERIFICATIONS if provided
            verifications_to_validate = updates.get('data', {}).get('verifications')
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
            
            # STEP 2: Merge updates with existing node data
            merged_data = {
                'node_id': node_id,
                'label': updates.get('label', existing_node.get('label')),
                'node_type': updates.get('type', existing_node.get('node_type')),
                'data': existing_node.get('data', {}),  # Start with existing data
                'style': existing_node.get('style', {}),
                'verifications': updates.get('verifications', existing_node.get('verifications', []))  # ✅ FIX: Accept verifications from updates
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
        
        ⚠️ CRITICAL: INCREMENTAL VALIDATION REQUIRED
        
        After creating an edge, you MUST test it before creating the next one.
        
        **Workflow (AI must follow):**
          1. create_edge(...)  
          2. get_edge(edge_id='...', tree_id='...')  ← GET EDGE DETAILS
          3. execute_device_action(actions=edge['action_sets'][0]['actions'], ...)  ← TEST IT
          4. If fails: update_edge() with correct selectors, test again
          5. If success: Create next edge
        
        **Why this matters:**
        - Catches selector errors immediately
        - Prevents cascading failures (10 broken edges)
        - Easier to debug when tested incrementally
        - Ensures each transition works before building on it
        
        **Tools for validation:**
        - get_edge(edge_id, tree_id) - Get edge details
        - execute_device_action(actions=[...]) - Test edge actions
        - navigate_to_node(target_node_label, tree_id) - Test full path
        - verify_node(node_id, tree_id) - Test node verifications
        
        Args:
            tree_id: Navigation tree ID (REQUIRED)
            source_node_id: Source node_id string (REQUIRED) - USE 'node_id' field from list_navigation_nodes
                           Example: "home" (NOT the UUID from 'id' field!)
            target_node_id: Target node_id string (REQUIRED) - USE 'node_id' field from list_navigation_nodes
                           Example: "tv_guide" (NOT the UUID from 'id' field!)
            source_label: Source node label (REQUIRED) - same as source_node_id for simple nodes
            target_label: Target node label (REQUIRED) - same as target_node_id for simple nodes
            action_sets: Array of action sets (REQUIRED) - MUST contain bidirectional actions
                         
                         ⚠️ CRITICAL FORMAT RULES:
                         1. Web/Remote: MUST include "action_type" field in EACH action
                         2. Mobile/ADB: NO "action_type" field needed (controller routes by device model)
                         3. Web/Remote: Include "wait_time" in params for timing control
                         4. Mobile/ADB: NO "wait_time" needed (ADB handles timing automatically)
                         5. Each action_set needs "id", "label", "actions", "retry_actions", "failure_actions"
                         6. Bidirectional edges need 2 action_sets (forward + backward)
                         
                         ⛔ COMMAND VALIDATION - MUST READ:
                         - ONLY use commands from list_actions() for your device model
                         - Invalid commands will FAIL with clear error messages
                         - For android_mobile/tv: Use "click_element" with text parameter
                         - NEVER use "click_element_by_index" - this command DOES NOT EXIST
                         - Example: {"command": "click_element", "params": {"element_id": "Home Tab"}}
                         - If unsure, call list_actions(device_id='...', host_name='...') first
                         
                         📋 COMPLETE EXAMPLES (COPY THESE EXACTLY):
                         
                         🔴 REMOTE/INFRARED (STB, TV):
                         [
                           {
                             "id": "home_to_settings",
                             "label": "home → settings",
                             "actions": [
                               {
                                 "command": "press_key",
                                 "action_type": "remote",
                                 "params": {
                                   "key": "RIGHT",
                                   "wait_time": 1500
                                 }
                               }
                             ],
                             "retry_actions": [],
                             "failure_actions": []
                           },
                           {
                             "id": "settings_to_home",
                             "label": "settings → home",
                             "actions": [
                               {
                                 "command": "press_key",
                                 "action_type": "remote",
                                 "params": {
                                   "key": "LEFT",
                                   "wait_time": 1500
                                 }
                               }
                             ],
                             "retry_actions": [],
                             "failure_actions": []
                           }
                         ]
                         
                         🌐 WEB (Playwright/Browser):
                         [
                           {
                             "id": "welcome_to_admin",
                             "label": "welcome → admin",
                             "actions": [
                               {
                                 "command": "click_element",
                                 "action_type": "web",
                                 "params": {
                                   "element_id": "Admin",
                                   "wait_time": 1000
                                 }
                               }
                             ],
                             "retry_actions": [],
                             "failure_actions": []
                           },
                           {
                             "id": "admin_to_welcome",
                             "label": "admin → welcome",
                             "actions": [
                               {
                                 "command": "click_element",
                                 "action_type": "web",
                                 "params": {
                                   "element_id": "Home",
                                   "wait_time": 1000
                                 }
                               }
                             ],
                             "retry_actions": [],
                             "failure_actions": []
                           }
                         ]
                         
                         📱 MOBILE/ADB (Android):
                         [
                           {
                             "id": "home_to_home_movies_series",
                             "label": "home → home_movies_series",
                             "actions": [
                               {
                                 "command": "click_element",
                                 "params": {
                                   "element_id": "Movies & Series Tab"
                                 }
                               }
                             ],
                             "retry_actions": [],
                             "failure_actions": []
                           },
                           {
                             "id": "home_movies_series_to_home",
                             "label": "home_movies_series → home",
                             "actions": [
                               {
                                 "command": "click_element",
                                 "params": {
                                   "element_id": "Home Tab"
                                 }
                               }
                             ],
                             "retry_actions": [],
                             "failure_actions": []
                           }
                         ]
                         
                         📊 MULTIPLE ACTIONS IN SEQUENCE (Web example):
                         [
                           {
                             "id": "home_to_settings",
                             "label": "home → settings",
                             "actions": [
                               {
                                 "command": "press_key",
                                 "action_type": "web",
                                 "params": {
                                   "key": "OK",
                                   "wait_time": 200
                                 }
                               },
                               {
                                 "command": "tap_x_y",
                                 "action_type": "web",
                                 "params": {
                                   "x": 226,
                                   "y": 847,
                                   "wait_time": 500
                                 }
                               }
                             ],
                             "retry_actions": [],
                             "failure_actions": []
                           },
                           {
                             "id": "settings_to_home",
                             "label": "settings → home",
                             "actions": [],
                             "retry_actions": [],
                             "failure_actions": []
                           }
                         ]
                         
                         ❌ COMMON MISTAKES TO AVOID:
                         1. Web/Remote: Missing "action_type" field → ALWAYS include it
                         2. Mobile/ADB: Including "action_type" → DO NOT include it
                         3. Mobile/ADB: Including "wait_time" → DO NOT include it (ADB handles timing)
                         4. Using "delay" at action level → Never use "delay", use "wait_time" in params (web/remote only)
                         5. Only one action_set → Need 2 for bidirectional navigation
                         6. Wrong param names: 
                            - Remote: use "key" (e.g., "RIGHT", "OK", "BACK")
                            - Web/Mobile: use "element_id" (e.g., "Admin", "Movies & Series Tab")
            
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
        Update an existing edge's actions
        
        Args:
            tree_id: Navigation tree ID (REQUIRED)
            edge_id: Edge identifier to update (REQUIRED)
            action_sets: New action sets to replace existing (REQUIRED)
                         
                         ⚠️ MUST USE SAME FORMAT AS create_edge:
                         - Web/Remote: Include "action_type" in each action
                         - Mobile/ADB: NO "action_type" field
                         - Web/Remote: Include "wait_time" in params
                         - Mobile/ADB: NO "wait_time" field
                         - Include "id", "label", "actions", "retry_actions", "failure_actions"
                         
                         See create_edge() docstring for complete examples.
                         
                         Quick Reference:
                         - Remote: {"command": "press_key", "action_type": "remote", "params": {"key": "RIGHT", "wait_time": 1500}}
                         - Web: {"command": "click_element", "action_type": "web", "params": {"element_id": "Admin", "wait_time": 1000}}
                         - Mobile: {"command": "click_element", "params": {"element_id": "Movies & Series Tab"}}
        
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
        Take screenshot and save it to a specific node (frontend: useNode.ts takeAndSaveScreenshot)
        
        This wraps the screenshot capture and node update into a single operation:
        1. Takes screenshot from device
        2. Saves it to userinterface-specific path
        3. Updates node with screenshot URL
        
        Frontend equivalent: useNode.ts line 99-160
        
        Args:
            tree_id: Navigation tree ID (REQUIRED)
            node_id: Node identifier to attach screenshot to (REQUIRED)
            label: Node label used as filename (REQUIRED)
            host_name: Host where device is connected (REQUIRED)
            device_id: Device identifier (REQUIRED)
            userinterface_name: User interface name for organizing screenshots (REQUIRED)
            team_id: Team ID (optional - defaults to default)
        
        Returns:
            {
                "success": true,
                "screenshot_url": "/screenshots/netflix_mobile/home_screen.png",
                "node_id": "home"
            }
        
        Example:
            save_node_screenshot({
                "tree_id": "ae9147a0-07eb-44d9-be71-aeffa3549ee0",
                "node_id": "home",
                "label": "Home Screen",
                "host_name": "sunri-pi1",
                "device_id": "device1",
                "userinterface_name": "netflix_mobile"
            })
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

