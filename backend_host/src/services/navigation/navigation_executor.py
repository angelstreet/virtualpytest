"""
Navigation Execution System

Unified navigation executor with complete tree management, pathfinding, and execution capabilities.
Consolidates all navigation functionality without external dependencies.
"""

import time
from typing import Dict, List, Optional, Any, Tuple

# Core imports
from  backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path
from  backend_host.src.lib.utils.navigation_exceptions import NavigationTreeError, UnifiedCacheError, PathfindingError, DatabaseError
from  backend_host.src.lib.utils.navigation_cache import populate_unified_cache


class NavigationExecutor:
    """
    Standardized navigation executor that orchestrates action and verification execution
    to provide complete navigation functionality.
    """
    
    def __init__(self, device):
        """Initialize NavigationExecutor"""
        # Validate required parameters - fail fast if missing
        if not device:
            raise ValueError("Device instance is required")
        if not device.host_name:
            raise ValueError("Device must have host_name")
        if not device.device_id:
            raise ValueError("Device must have device_id")
        
        # Store instances directly
        self.device = device
        self.host_name = device.host_name
        self.device_id = device.device_id
        self.device_model = device.device_model
        
        # Navigation state tracking
        self.current_node_id = None
        self.current_node_label = None
        self.current_tree_id = None
        
        print(f"[@navigation_executor] Initialized for device: {self.device_id}, model: {self.device_model}")
    
    def get_available_context(self, userinterface_name: str, team_id: str) -> Dict[str, Any]:
        """Get available navigation context using cache when possible"""
        # First check if we have a cached unified graph for this interface
        from shared.src.lib.supabase.userinterface_db import get_userinterface_by_name
        from shared.src.lib.supabase.navigation_trees_db import get_root_tree_for_interface
        from  backend_host.src.lib.utils.navigation_cache import get_cached_unified_graph
        
        # Get interface and root tree ID
        interface_info = get_userinterface_by_name(userinterface_name, team_id)
        if not interface_info:
            raise ValueError(f"Interface '{userinterface_name}' not found")
            
        root_tree_info = get_root_tree_for_interface(interface_info['id'], team_id)
        if not root_tree_info:
            raise ValueError(f"No root tree found for interface '{userinterface_name}'")
            
        tree_id = root_tree_info['id']
        
        # Check cache first - avoid reloading if already cached
        cached_graph = get_cached_unified_graph(tree_id, team_id)
        if cached_graph:
            print(f"[@navigation_executor] Using cached unified graph for '{userinterface_name}' (tree: {tree_id})")
            # Extract available nodes from cached graph - use labels, not node IDs
            available_nodes = []
            for node_id, node_data in cached_graph.nodes(data=True):
                if node_id != 'root':  # Skip root node
                    label = node_data.get('label', node_id)  # Use label if available, fallback to node_id
                    if label:  # Only add non-empty labels
                        available_nodes.append(label)
            
            print(f"[@navigation_executor] Extracted {len(available_nodes)} node labels: {available_nodes}")
            
            return {
                'service_type': 'navigation',
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,
                'tree_id': tree_id,
                'available_nodes': available_nodes,
                'cross_tree_capabilities': len(cached_graph.nodes()) > 10,  # Estimate based on graph size
                'unified_graph_nodes': len(cached_graph.nodes()),
                'unified_graph_edges': len(cached_graph.edges())
            }
        
        # Cache miss - load tree hierarchy and populate cache
        print(f"[@navigation_executor] Cache miss for '{userinterface_name}' - loading tree hierarchy")
        tree_result = self.load_navigation_tree_with_hierarchy(userinterface_name, team_id, "navigation_executor")
        
        # Fail fast - no fallback
        if not tree_result['success']:
            raise ValueError(f"Failed to load navigation tree: {tree_result['error']}")
        
        root_tree = tree_result['root_tree']
        nodes = root_tree['nodes']
        # Extract node labels (not node_name) for consistency with cached path
        available_nodes = []
        for node in nodes:
            label = node.get('label') or node.get('node_name')  # Try label first, fallback to node_name
            if label:
                available_nodes.append(label)
        
        print(f"[@navigation_executor] Extracted {len(available_nodes)} node labels from tree result: {available_nodes}")
        
        return {
            'service_type': 'navigation',
            'device_id': self.device_id,
            'device_model': self.device_model,
            'userinterface_name': userinterface_name,
            'tree_id': tree_id,
            'available_nodes': available_nodes,
            'cross_tree_capabilities': tree_result.get('cross_tree_capabilities', False),
            'unified_graph_nodes': tree_result.get('unified_graph_nodes', 0),
            'unified_graph_edges': tree_result.get('unified_graph_edges', 0)
        }
    
    def _build_result(self, success: bool, message: str, tree_id: str, target_node_id: str, 
                     current_node_id: Optional[str], start_time: float, **kwargs) -> Dict[str, Any]:
        """Build standardized result dictionary"""
        result = {
            'success': success,
            'tree_id': tree_id,
            'target_node_id': target_node_id,
            'current_node_id': current_node_id,
            'execution_time': time.time() - start_time,
            'transitions_executed': 0,
            'total_transitions': 0,
            'actions_executed': 0,
            'total_actions': 0
        }
        
        if success:
            result['message'] = message
        else:
            result['error'] = message
            
        result.update(kwargs)
        return result
    
    
    def execute_navigation(self, 
                          tree_id: str, 
                          target_node_id: str, 
                          current_node_id: Optional[str] = None,
                          image_source_url: Optional[str] = None,
                          team_id: str = None) -> Dict[str, Any]:
        """Execute navigation to target node"""
        start_time = time.time()
        
        # Get preview first (includes pathfinding)
        preview = self.get_navigation_preview(tree_id, target_node_id, current_node_id, team_id)
        if not preview['success']:
            return self._build_result(False, preview['error'], tree_id, target_node_id, current_node_id, start_time)
        
        # Execute using preview data
        transitions = preview['transitions']
        
        try:
            # Execute transitions
            transitions_executed = 0
            actions_executed = 0
            total_actions = preview['total_actions']
            success = True
            error_message = ""
            
            for i, transition in enumerate(transitions):
                actions = transition.get('actions', [])
                if not actions:
                    transitions_executed += 1
                    continue
                
                # Execute actions using device's existing executor
                # Update context for this navigation
                self.device.action_executor.tree_id = tree_id
                self.device.action_executor.edge_id = transition.get('edge_id')
                # Pass script context if available
                if hasattr(self, 'script_result_id'):
                    self.device.action_executor.script_result_id = self.script_result_id
                
                result = self.device.action_executor.execute_actions(
                    actions=actions,
                    retry_actions=transition.get('retryActions', []),
                    team_id=team_id
                )
                
                if not result.get('success'):
                    success = False
                    error_message = f'Action failed: {result.get("error", "Unknown error")}'
                    break
                
                actions_executed += result.get('passed_count', 0)
                transitions_executed += 1
            
            # Execute target verifications if actions succeeded
            if success and transitions:
                target_verifications = transitions[-1].get('target_verifications', [])
                if target_verifications:
                    # Execute verifications using device's existing executor
                    # Update context for this navigation
                    self.device.verification_executor.tree_id = tree_id
                    self.device.verification_executor.node_id = target_node_id
                    # Pass script context if available
                    if hasattr(self, 'script_result_id'):
                        self.device.verification_executor.script_result_id = self.script_result_id
                    
                    result = self.device.verification_executor.execute_verifications(
                        verifications=target_verifications,
                        image_source_url=image_source_url,
                        team_id=team_id
                    )
                    
                    if not result.get('success'):
                        success = False
                        error_message = f'Verification failed: {result.get("error", "Unknown error")}'
            
            # Update position if navigation succeeded
            if success:
                self.update_current_position(target_node_id, tree_id)
            
            # Build result once
            message = f'Navigation to {target_node_id} completed' if success else error_message
            extra_kwargs = {'final_position_node_id': target_node_id} if success else {}
            
            return self._build_result(
                success, message, tree_id, target_node_id, current_node_id, start_time,
                transitions_executed=transitions_executed,
                total_transitions=preview['total_transitions'],
                actions_executed=actions_executed,
                total_actions=total_actions,
                **extra_kwargs
            )
            
        except Exception as e:
            return self._build_result(
                False,
                f'Navigation error: {str(e)}',
                tree_id, target_node_id, current_node_id, start_time
            )
    
    def get_navigation_preview(self, tree_id: str, target_node_id: str, 
                             current_node_id: Optional[str] = None, team_id: str = None) -> Dict[str, Any]:
        """Get navigation preview without executing"""
        
        transitions = find_shortest_path(tree_id, target_node_id, team_id, current_node_id)
        
        success = bool(transitions)
        error_message = 'No navigation path found' if not success else ''
        
        return {
            'success': success,
            'error': error_message if not success else None,
            'tree_id': tree_id,
            'target_node_id': target_node_id,
            'current_node_id': current_node_id,
            'transitions': transitions or [],
            'total_transitions': len(transitions) if transitions else 0,
            'total_actions': sum(len(t.get('actions', [])) for t in transitions) if transitions else 0
        }
    
    # ========================================
    # NAVIGATION TREE MANAGEMENT METHODS
    # ========================================
    
    def load_navigation_tree(self, userinterface_name: str, team_id: str, script_name: str = "navigation_executor") -> Dict[str, Any]:
        """
        Load navigation tree using direct database access (no HTTP requests).
        This populates the cache and is required before calling pathfinding functions.
        
        Args:
            userinterface_name: Interface name (e.g., 'horizon_android_mobile')
            team_id: Team ID (required)
            script_name: Name of the script for logging
            
        Returns:
            Dictionary with success status and tree data or error
        """
        try:
            from shared.src.lib.supabase.userinterface_db import get_userinterface_by_name
            userinterface = get_userinterface_by_name(userinterface_name, team_id)
            if not userinterface:
                return {'success': False, 'error': f"User interface '{userinterface_name}' not found"}
            
            userinterface_id = userinterface['id']
            
            # Use the same approach as NavigationEditor - call the working API endpoint
            from shared.src.lib.supabase.navigation_trees_db import get_root_tree_for_interface, get_full_tree
            
            # Get the root tree for this user interface (same as navigation page)
            tree = get_root_tree_for_interface(userinterface_id, team_id)
            
            if not tree:
                return {'success': False, 'error': f"No root tree found for interface: {userinterface_id}"}
            
            # Get full tree data with nodes and edges (same as navigation page)
            tree_data = get_full_tree(tree['id'], team_id)
            
            if not tree_data['success']:
                return {'success': False, 'error': f"Failed to load tree data: {tree_data.get('error', 'Unknown error')}"}
            
            tree_id = tree['id']
            nodes = tree_data['nodes']
            edges = tree_data['edges']
            
            return {
                'success': True,
                'tree': {
                    'id': tree_id,
                    'name': tree.get('name', ''),
                    'metadata': {
                        'nodes': nodes,
                        'edges': edges
                    }
                },
                'tree_id': tree_id,
                'userinterface_id': userinterface_id,
                'nodes': nodes,
                'edges': edges
            }
            
        except Exception as e:
            return {'success': False, 'error': f"Error loading navigation tree: {str(e)}"}

    def load_navigation_tree_with_hierarchy(self, userinterface_name: str, team_id: str, script_name: str = "navigation_executor") -> Dict[str, Any]:
        """Load navigation tree - exactly like main branch."""
        # Just load main tree and populate cache
        root_tree_result = self.load_navigation_tree(userinterface_name, team_id, script_name)
        if not root_tree_result['success']:
            return root_tree_result
        
        # Populate cache with main tree only
        from backend_host.src.lib.utils.navigation_cache import populate_cache
        populate_cache(root_tree_result['tree_id'], team_id, root_tree_result['nodes'], root_tree_result['edges'])
        
        return {
            'success': True,
            'tree_id': root_tree_result['tree_id'],
            'root_tree': root_tree_result
        }


    # ========================================
    # NODE AND EDGE FINDING METHODS
    # ========================================

    def find_node_by_label(self, nodes: List[Dict], label: str) -> Dict:
        """
        Find node by its label in a generic way.
        
        Args:
            nodes: List of node dictionaries
            label: Node label to search for
            
        Returns:
            Node dictionary with the matching label, or None if not found
        """
        for node in nodes:
            if node.get('label') == label:
                return node
        return None

    def find_edges_from_node(self, source_node_id: str, edges: List[Dict]) -> List[Dict]:
        """
        Find all edges originating from a specific node (generic version).
        
        Args:
            source_node_id: Source node ID
            edges: List of edge dictionaries
            
        Returns:
            List of edges originating from the specified node
        """
        return [edge for edge in edges if edge.get('source_node_id') == source_node_id]

    def find_edge_by_target_label(self, source_node_id: str, edges: List[Dict], nodes: List[Dict], target_label: str) -> Dict:
        """
        Find edge from source node to a target node with specific label.
        This is the proper generic way to find action edges.
        
        Args:
            source_node_id: Source node ID
            edges: List of edge dictionaries
            nodes: List of node dictionaries  
            target_label: Label of target node to find
            
        Returns:
            Edge dictionary going to target node with specified label, or None if not found
        """
        # First find the target node by label
        target_node = self.find_node_by_label(nodes, target_label)
        if not target_node:
            return None
        
        target_node_id = target_node.get('node_id')
        if not target_node_id:
            return None
        
        # Find edge from source to target
        source_edges = self.find_edges_from_node(source_node_id, edges)
        for edge in source_edges:
            if edge.get('target_node_id') == target_node_id:
                return edge
        
        return None

    def find_edge_with_action_command(self, node_id: str, edges: List[Dict], action_command: str) -> Dict:
        """
        Find edge from node_id that contains the specified action command in its action sets.
        
        Args:
            node_id: Source node ID
            edges: List of edge dictionaries 
            action_command: Action command to search for (e.g., 'tap_coordinates', 'press_key')
            
        Returns:
            Edge dictionary containing the action, or None if not found
        """
        source_edges = self.find_edges_from_node(node_id, edges)
        
        for edge in source_edges:
            action_sets = edge.get('action_sets', [])
            for action_set in action_sets:
                actions = action_set.get('actions', [])
                for action in actions:
                    if action.get('command') == action_command:
                        return edge
        
        return None

    def get_node_sub_trees_with_actions(self, node_id: str, tree_id: str, team_id: str) -> Dict:
        """Get all sub-trees for a node and return their nodes and edges for action checking."""
        from shared.src.lib.supabase.navigation_trees_db import get_node_sub_trees, get_full_tree
        
        # Get sub-trees for this node
        sub_trees_result = get_node_sub_trees(tree_id, node_id, team_id)
        if not sub_trees_result.get('success'):
            return {'success': False, 'error': sub_trees_result.get('error'), 'sub_trees': [], 'all_nodes': [], 'all_edges': []}
        
        sub_trees = sub_trees_result.get('sub_trees', [])
        all_nodes = []
        all_edges = []
        
        # Load nodes and edges from all sub-trees
        for sub_tree in sub_trees:
            sub_tree_id = sub_tree.get('id')
            if sub_tree_id:
                tree_data = get_full_tree(sub_tree_id, team_id)
                if tree_data.get('success'):
                    all_nodes.extend(tree_data.get('nodes', []))
                    all_edges.extend(tree_data.get('edges', []))
        
        return {
            'success': True,
            'sub_trees': sub_trees,
            'all_nodes': all_nodes,
            'all_edges': all_edges
        }

    def find_action_in_nested_trees(self, source_node_id: str, tree_id: str, nodes: List[Dict], edges: List[Dict], action_command: str, team_id: str) -> Dict:
        """Find action in main tree and sub-trees of the specific source node only."""
        
        # First check in the main tree
        action_edge = self.find_edge_by_target_label(source_node_id, edges, nodes, action_command)
        if action_edge:
            return {'success': True, 'edge': action_edge, 'tree_type': 'main', 'tree_id': tree_id}
        
        action_edge = self.find_edge_with_action_command(source_node_id, edges, action_command)
        if action_edge:
            return {'success': True, 'edge': action_edge, 'tree_type': 'main', 'tree_id': tree_id}
        
        # Check sub-trees for this specific node only
        print(f"🔍 [navigation_executor] Checking sub-trees for node: {source_node_id}")
        sub_trees_data = self.get_node_sub_trees_with_actions(source_node_id, tree_id, team_id)
        
        if not sub_trees_data.get('success') or not sub_trees_data.get('sub_trees'):
            print(f"🔍 [navigation_executor] Node {source_node_id} has no sub-trees")
            return {'success': False, 'error': f"Action '{action_command}' not found in main tree and node has no sub-trees"}
        
        sub_nodes = sub_trees_data.get('all_nodes', [])
        sub_edges = sub_trees_data.get('all_edges', [])
        sub_trees = sub_trees_data.get('sub_trees', [])
        
        print(f"🔍 [navigation_executor] Found {len(sub_trees)} sub-trees with {len(sub_nodes)} nodes and {len(sub_edges)} edges")
        
        # Simple search: try to find action in any sub-tree node
        for node in sub_nodes:
            node_id = node.get('node_id')
            if node_id:
                # Check by target label
                sub_action_edge = self.find_edge_by_target_label(node_id, sub_edges, sub_nodes, action_command)
                if sub_action_edge:
                    return {'success': True, 'edge': sub_action_edge, 'tree_type': 'sub', 'tree_id': sub_trees[0].get('id'), 'source_node_id': node_id}
                
                # Check by action command
                sub_action_edge = self.find_edge_with_action_command(node_id, sub_edges, action_command)
                if sub_action_edge:
                    return {'success': True, 'edge': sub_action_edge, 'tree_type': 'sub', 'tree_id': sub_trees[0].get('id'), 'source_node_id': node_id}
        
        return {'success': False, 'error': f"Action '{action_command}' not found in main tree or sub-trees"}

    # ========================================
    # POSITION TRACKING METHODS
    # ========================================
    
    def get_current_position(self) -> Dict[str, Any]:
        """Get current navigation position for this device"""
        return {
            'success': True,
            'device_id': self.device_id,
            'current_node_id': self.current_node_id,
            'current_node_label': self.current_node_label,
            'current_tree_id': self.current_tree_id
        }
    
    def update_current_position(self, node_id: str, tree_id: str = None, node_label: str = None) -> Dict[str, Any]:
        """Update current navigation position for this device"""
        self.current_node_id = node_id
        self.current_tree_id = tree_id or self.current_tree_id
        self.current_node_label = node_label or node_id
        
        print(f"[@navigation_executor] Updated position for {self.device_id}: {node_id} (tree: {self.current_tree_id})")
        
        return {
            'success': True,
            'device_id': self.device_id,
            'current_node_id': self.current_node_id,
            'current_node_label': self.current_node_label,
            'current_tree_id': self.current_tree_id
        }
    
    def clear_current_position(self) -> Dict[str, Any]:
        """Clear current navigation position (e.g., when switching interfaces)"""
        old_position = {
            'node_id': self.current_node_id,
            'tree_id': self.current_tree_id,
            'node_label': self.current_node_label
        }
        
        self.current_node_id = None
        self.current_tree_id = None
        self.current_node_label = None
        
        print(f"[@navigation_executor] Cleared position for {self.device_id} (was: {old_position['node_id']})")
        
        return {
            'success': True,
            'device_id': self.device_id,
            'previous_position': old_position,
            'current_position': None
        }
