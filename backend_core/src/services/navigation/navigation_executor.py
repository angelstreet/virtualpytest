"""
Navigation Execution System

Unified navigation executor with complete tree management, pathfinding, and execution capabilities.
Consolidates all navigation functionality without external dependencies.
"""

import time
from typing import Dict, List, Optional, Any, Tuple

# Core imports
from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path
from shared.lib.utils.app_utils import get_team_id
from shared.lib.utils.navigation_exceptions import NavigationTreeError, UnifiedCacheError, PathfindingError, DatabaseError
from shared.lib.utils.navigation_cache import populate_unified_cache


class NavigationExecutor:
    """
    Standardized navigation executor that orchestrates action and verification execution
    to provide complete navigation functionality.
    """
    
    def __init__(self, host: Dict[str, Any], device, device_id: str = None, team_id: Optional[str] = None):
        """Initialize NavigationExecutor"""
        # Validate required parameters - fail fast if missing
        if not device:
            raise ValueError("Device instance is required")
        if not host or not host.get('host_name'):
            raise ValueError("Host configuration with host_name is required")
        
        # Store instances directly
        self.host = host
        self.device = device
        self.host_name = host['host_name']
        self.device_id = device_id or device.device_id
        self.device_model = device.device_model
        self.team_id = team_id or get_team_id()
        
        # Navigation state tracking
        self.current_node_id = None
        self.current_node_label = None
        self.current_tree_id = None
        
        print(f"[@navigation_executor] Initialized for device: {self.device_id}, model: {self.device_model}")
    
    def get_available_context(self, userinterface_name: str) -> Dict[str, Any]:
        """Get available navigation context with enhanced hierarchy support"""
        tree_result = self.load_navigation_tree_with_hierarchy(userinterface_name, "navigation_executor")
        
        # Fail fast - no fallback
        if not tree_result['success']:
            raise ValueError(f"Failed to load navigation tree: {tree_result['error']}")
        
        tree_id = tree_result['tree_id']
        root_tree = tree_result['root_tree']
        nodes = root_tree['nodes']
        available_nodes = [node.get('node_name') for node in nodes if node.get('node_name')]
        
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
                          image_source_url: Optional[str] = None) -> Dict[str, Any]:
        """Execute navigation to target node"""
        start_time = time.time()
        
        # Get preview first (includes pathfinding)
        preview = self.get_navigation_preview(tree_id, target_node_id, current_node_id)
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
                
                result = self.device.action_executor.execute_actions(
                    actions=actions,
                    retry_actions=transition.get('retryActions', [])
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
                    
                    result = self.device.verification_executor.execute_verifications(
                        verifications=target_verifications,
                        image_source_url=image_source_url
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
                             current_node_id: Optional[str] = None) -> Dict[str, Any]:
        """Get navigation preview without executing"""
        transitions = find_shortest_path(tree_id, target_node_id, self.team_id, current_node_id)
        
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
    
    def load_navigation_tree(self, userinterface_name: str, script_name: str = "navigation_executor") -> Dict[str, Any]:
        """
        Load navigation tree using direct database access (no HTTP requests).
        This populates the cache and is required before calling pathfinding functions.
        
        Args:
            userinterface_name: Interface name (e.g., 'horizon_android_mobile')
            script_name: Name of the script for logging
            
        Returns:
            Dictionary with success status and tree data or error
        """
        try:
            from shared.lib.supabase.userinterface_db import get_all_userinterfaces
            
            userinterfaces = get_all_userinterfaces(self.team_id)
            if not userinterfaces:
                return {'success': False, 'error': "No userinterfaces found"}
            
            userinterface = next((ui for ui in userinterfaces if ui['name'] == userinterface_name), None)
            if not userinterface:
                return {'success': False, 'error': f"User interface '{userinterface_name}' not found"}
            
            userinterface_id = userinterface['id']
            
            # Use the same approach as NavigationEditor - call the working API endpoint
            from shared.lib.supabase.navigation_trees_db import get_root_tree_for_interface, get_full_tree
            
            # Get the root tree for this user interface (same as navigation page)
            tree = get_root_tree_for_interface(userinterface_id, self.team_id)
            
            if not tree:
                return {'success': False, 'error': f"No root tree found for interface: {userinterface_id}"}
            
            # Get full tree data with nodes and edges (same as navigation page)
            tree_data = get_full_tree(tree['id'], self.team_id)
            
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

    def load_navigation_tree_with_hierarchy(self, userinterface_name: str, script_name: str = "navigation_executor") -> Dict[str, Any]:
        """
        Load complete navigation tree hierarchy and populate unified cache.
        FAIL EARLY: No fallback to single-tree loading.
        
        Args:
            userinterface_name: Interface name (e.g., 'horizon_android_mobile')
            script_name: Name of the script for logging
            
        Returns:
            Dictionary with success status and complete hierarchy data
            
        Raises:
            NavigationTreeError: If any part of the hierarchy loading fails
        """
        try:
            print(f"🗺️ [{script_name}] Loading complete navigation tree hierarchy for '{userinterface_name}'")
            
            # 1. Load root tree (using existing logic)
            root_tree_result = self.load_navigation_tree(userinterface_name, script_name)
            if not root_tree_result['success']:
                raise NavigationTreeError(f"Root tree loading failed: {root_tree_result['error']}")
            
            root_tree_id = root_tree_result['tree_id']
            
            print(f"✅ [{script_name}] Root tree loaded: {root_tree_id}")
            
            # 2. Discover complete tree hierarchy
            hierarchy_data = self.discover_complete_hierarchy(root_tree_id, self.team_id, script_name)
            if not hierarchy_data:
                # If no nested trees, create single-tree hierarchy
                hierarchy_data = [self.format_tree_for_hierarchy(root_tree_result, is_root=True)]
                print(f"📋 [{script_name}] No nested trees found, using single root tree")
            else:
                print(f"📋 [{script_name}] Found {len(hierarchy_data)} trees in hierarchy")
            
            # 3. Build unified tree data structure
            all_trees_data = self.build_unified_tree_data(hierarchy_data, script_name)
            if not all_trees_data:
                raise NavigationTreeError("Failed to build unified tree data structure")
            
            # 4. Populate unified cache (MANDATORY)
            print(f"🔄 [{script_name}] Populating unified cache...")
            unified_graph = populate_unified_cache(root_tree_id, self.team_id, all_trees_data)
            if not unified_graph:
                raise UnifiedCacheError("Failed to populate unified cache - navigation will not work")
            
            print(f"✅ [{script_name}] Unified cache populated: {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
            
            # 5. Return enhanced result with hierarchy info
            return {
                'success': True,
                'tree_id': root_tree_id,
                'root_tree': root_tree_result,
                'hierarchy': hierarchy_data,
                'unified_graph_nodes': len(unified_graph.nodes),
                'unified_graph_edges': len(unified_graph.edges),
                'cross_tree_capabilities': len(hierarchy_data) > 1,
                'team_id': self.team_id
            }
            
        except (NavigationTreeError, UnifiedCacheError) as e:
            # Re-raise navigation-specific errors
            raise e
        except Exception as e:
            # FAIL EARLY - no fallback
            raise NavigationTreeError(f"Unified tree loading failed: {str(e)}")

    def discover_complete_hierarchy(self, root_tree_id: str, team_id: str, script_name: str = "navigation_executor") -> List[Dict]:
        """
        Discover all nested trees in hierarchy using enhanced database functions.
        
        Args:
            root_tree_id: Root tree ID
            team_id: Team ID
            script_name: Script name for logging
            
        Returns:
            List of tree data dictionaries for the complete hierarchy
        """
        try:
            from shared.lib.supabase.navigation_trees_db import get_complete_tree_hierarchy
            
            print(f"🔍 [{script_name}] Discovering complete tree hierarchy using enhanced database function...")
            
            # Use the new enhanced database function
            hierarchy_result = get_complete_tree_hierarchy(root_tree_id, team_id)
            if not hierarchy_result['success']:
                print(f"⚠️ [{script_name}] Failed to get complete hierarchy: {hierarchy_result.get('error', 'Unknown error')}")
                return []
            
            hierarchy_data = hierarchy_result['hierarchy']
            if not hierarchy_data:
                print(f"📋 [{script_name}] Empty hierarchy returned from database")
                return []
            
            total_trees = hierarchy_result.get('total_trees', len(hierarchy_data))
            max_depth = hierarchy_result.get('max_depth', 0)
            has_nested = hierarchy_result.get('has_nested_trees', False)
            
            print(f"✅ [{script_name}] Complete hierarchy discovered:")
            print(f"   • Total trees: {total_trees}")
            print(f"   • Maximum depth: {max_depth}")
            print(f"   • Has nested trees: {has_nested}")
            
            # The data is already in the correct format from the database function
            return hierarchy_data
            
        except Exception as e:
            print(f"❌ [{script_name}] Error discovering hierarchy: {str(e)}")
            return []

    def format_tree_for_hierarchy(self, tree_data: Dict, tree_info: Dict = None, is_root: bool = False) -> Dict:
        """
        Format tree data for unified hierarchy structure.
        
        Args:
            tree_data: Tree data from database
            tree_info: Optional hierarchy metadata
            is_root: Whether this is the root tree
            
        Returns:
            Formatted tree data for unified processing
        """
        if is_root:
            # Root tree from load_navigation_tree
            return {
                'tree_id': tree_data['tree_id'],
                'tree_info': {
                    'name': tree_data['tree']['name'],
                    'is_root_tree': True,
                    'tree_depth': 0,
                    'parent_tree_id': None,
                    'parent_node_id': None
                },
                'nodes': tree_data['nodes'],
                'edges': tree_data['edges']
            }
        else:
            # Nested tree from hierarchy
            return {
                'tree_id': tree_info['tree_id'],
                'tree_info': {
                    'name': tree_info.get('tree_name', ''),
                    'is_root_tree': tree_info.get('depth', 0) == 0,
                    'tree_depth': tree_info.get('depth', 0),
                    'parent_tree_id': tree_info.get('parent_tree_id'),
                    'parent_node_id': tree_info.get('parent_node_id')
                },
                'nodes': tree_data['nodes'],
                'edges': tree_data['edges']
            }

    def build_unified_tree_data(self, hierarchy_data: List[Dict], script_name: str = "navigation_executor") -> List[Dict]:
        """
        Build unified data structure for cache population.
        
        Args:
            hierarchy_data: List of formatted tree data
            script_name: Script name for logging
            
        Returns:
            Data structure ready for create_unified_networkx_graph()
        """
        try:
            if not hierarchy_data:
                print(f"⚠️ [{script_name}] No hierarchy data to build unified structure")
                return []
            
            print(f"🔧 [{script_name}] Building unified data structure from {len(hierarchy_data)} trees")
            
            # The hierarchy_data is already in the correct format for create_unified_networkx_graph
            # Just validate and return
            for tree_data in hierarchy_data:
                required_keys = ['tree_id', 'tree_info', 'nodes', 'edges']
                for key in required_keys:
                    if key not in tree_data:
                        raise NavigationTreeError(f"Missing required key '{key}' in tree data")
            
            print(f"✅ [{script_name}] Unified data structure validated")
            return hierarchy_data
            
        except Exception as e:
            print(f"❌ [{script_name}] Error building unified data: {str(e)}")
            return []

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
        from shared.lib.supabase.navigation_trees_db import get_node_sub_trees, get_full_tree
        
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

    