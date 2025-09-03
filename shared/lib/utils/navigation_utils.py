"""
Navigation utilities for VirtualPyTest

This module contains all navigation-related functions including:
- Navigation tree loading and management
- Node and edge finding functions
- Path finding and navigation execution
- Action validation and execution
"""

import os
import sys
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.dirname(current_dir)
shared_dir = os.path.dirname(lib_dir)
project_root = os.path.dirname(shared_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .host_utils import get_controller
from .action_utils import execute_navigation_with_verifications, capture_validation_screenshot
from .navigation_exceptions import NavigationTreeError, UnifiedCacheError, PathfindingError, DatabaseError
from .navigation_cache import populate_unified_cache


def load_navigation_tree(userinterface_name: str, script_name: str = "script") -> Dict[str, Any]:
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
        team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
        
        from shared.lib.supabase.userinterface_db import get_all_userinterfaces
        
        userinterfaces = get_all_userinterfaces(team_id)
        if not userinterfaces:
            return {'success': False, 'error': "No userinterfaces found"}
        
        userinterface = next((ui for ui in userinterfaces if ui['name'] == userinterface_name), None)
        if not userinterface:
            return {'success': False, 'error': f"User interface '{userinterface_name}' not found"}
        
        userinterface_id = userinterface['id']
        
        # Use the same approach as NavigationEditor - call the working API endpoint
        from shared.lib.supabase.navigation_trees_db import get_root_tree_for_interface, get_full_tree
        
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


def load_navigation_tree_with_hierarchy(userinterface_name: str, script_name: str = "script") -> Dict[str, Any]:
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
        root_tree_result = load_navigation_tree(userinterface_name, script_name)
        if not root_tree_result['success']:
            raise NavigationTreeError(f"Root tree loading failed: {root_tree_result['error']}")
        
        team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
        root_tree_id = root_tree_result['tree_id']
        
        print(f"✅ [{script_name}] Root tree loaded: {root_tree_id}")
        
        # 2. Discover complete tree hierarchy
        hierarchy_data = discover_complete_hierarchy(root_tree_id, team_id, script_name)
        if not hierarchy_data:
            # If no nested trees, create single-tree hierarchy
            hierarchy_data = [format_tree_for_hierarchy(root_tree_result, is_root=True)]
            print(f"📋 [{script_name}] No nested trees found, using single root tree")
        else:
            print(f"📋 [{script_name}] Found {len(hierarchy_data)} trees in hierarchy")
        
        # 3. Build unified tree data structure
        all_trees_data = build_unified_tree_data(hierarchy_data, script_name)
        if not all_trees_data:
            raise NavigationTreeError("Failed to build unified tree data structure")
        
        # 4. Populate unified cache (MANDATORY)
        print(f"🔄 [{script_name}] Populating unified cache...")
        unified_graph = populate_unified_cache(root_tree_id, team_id, all_trees_data)
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
            'team_id': team_id
        }
        
    except (NavigationTreeError, UnifiedCacheError) as e:
        # Re-raise navigation-specific errors
        raise e
    except Exception as e:
        # FAIL EARLY - no fallback
        raise NavigationTreeError(f"Unified tree loading failed: {str(e)}")


def discover_complete_hierarchy(root_tree_id: str, team_id: str, script_name: str = "script") -> List[Dict]:
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


def format_tree_for_hierarchy(tree_data: Dict, tree_info: Dict = None, is_root: bool = False) -> Dict:
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


def build_unified_tree_data(hierarchy_data: List[Dict], script_name: str = "script") -> List[Dict]:
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


def find_node_by_label(nodes: List[Dict], label: str) -> Dict:
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


def find_edges_from_node(source_node_id: str, edges: List[Dict]) -> List[Dict]:
    """
    Find all edges originating from a specific node (generic version).
    
    Args:
        source_node_id: Source node ID
        edges: List of edge dictionaries
        
    Returns:
        List of edges originating from the specified node
    """
    return [edge for edge in edges if edge.get('source_node_id') == source_node_id]


def find_edge_by_target_label(source_node_id: str, edges: List[Dict], nodes: List[Dict], target_label: str) -> Dict:
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
    target_node = find_node_by_label(nodes, target_label)
    if not target_node:
        return None
    
    target_node_id = target_node.get('node_id')
    if not target_node_id:
        return None
    
    # Find edge from source to target
    source_edges = find_edges_from_node(source_node_id, edges)
    for edge in source_edges:
        if edge.get('target_node_id') == target_node_id:
            return edge
    
    return None


def find_edge_with_action_command(node_id: str, edges: List[Dict], action_command: str) -> Dict:
    """
    Find edge from node_id that contains the specified action command in its action sets.
    
    Args:
        node_id: Source node ID
        edges: List of edge dictionaries 
        action_command: Action command to search for (e.g., 'tap_coordinates', 'press_key')
        
    Returns:
        Edge dictionary containing the action, or None if not found
    """
    source_edges = find_edges_from_node(node_id, edges)
    
    for edge in source_edges:
        action_sets = edge.get('action_sets', [])
        for action_set in action_sets:
            actions = action_set.get('actions', [])
            for action in actions:
                if action.get('command') == action_command:
                    return edge
    
    return None


def get_node_sub_trees_with_actions(node_id: str, tree_id: str, team_id: str) -> Dict:
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


def find_action_in_nested_trees(source_node_id: str, tree_id: str, nodes: List[Dict], edges: List[Dict], action_command: str, team_id: str) -> Dict:
    """Find action in main tree and sub-trees of the specific source node only."""
    
    # First check in the main tree
    action_edge = find_edge_by_target_label(source_node_id, edges, nodes, action_command)
    if action_edge:
        return {'success': True, 'edge': action_edge, 'tree_type': 'main', 'tree_id': tree_id}
    
    action_edge = find_edge_with_action_command(source_node_id, edges, action_command)
    if action_edge:
        return {'success': True, 'edge': action_edge, 'tree_type': 'main', 'tree_id': tree_id}
    
    # Check sub-trees for this specific node only
    print(f"🔍 [navigation_utils] Checking sub-trees for node: {source_node_id}")
    sub_trees_data = get_node_sub_trees_with_actions(source_node_id, tree_id, team_id)
    
    if not sub_trees_data.get('success') or not sub_trees_data.get('sub_trees'):
        print(f"🔍 [navigation_utils] Node {source_node_id} has no sub-trees")
        return {'success': False, 'error': f"Action '{action_command}' not found in main tree and node has no sub-trees"}
    
    sub_nodes = sub_trees_data.get('all_nodes', [])
    sub_edges = sub_trees_data.get('all_edges', [])
    sub_trees = sub_trees_data.get('sub_trees', [])
    
    print(f"🔍 [navigation_utils] Found {len(sub_trees)} sub-trees with {len(sub_nodes)} nodes and {len(sub_edges)} edges")
    
    # Simple search: try to find action in any sub-tree node
    for node in sub_nodes:
        node_id = node.get('node_id')
        if node_id:
            # Check by target label
            sub_action_edge = find_edge_by_target_label(node_id, sub_edges, sub_nodes, action_command)
            if sub_action_edge:
                return {'success': True, 'edge': sub_action_edge, 'tree_type': 'sub', 'tree_id': sub_trees[0].get('id'), 'source_node_id': node_id}
            
            # Check by action command
            sub_action_edge = find_edge_with_action_command(node_id, sub_edges, action_command)
            if sub_action_edge:
                return {'success': True, 'edge': sub_action_edge, 'tree_type': 'sub', 'tree_id': sub_trees[0].get('id'), 'source_node_id': node_id}
    
    return {'success': False, 'error': f"Action '{action_command}' not found in main tree or sub-trees"}


def validate_action_availability(nodes: List[Dict], edges: List[Dict], action_command: str, 
                                tree_id: str, team_id: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Validate that an action exists and return the action edge.
    
    Args:
        nodes: List of navigation nodes
        edges: List of navigation edges  
        action_command: Action command to validate
        tree_id: Navigation tree ID
        team_id: Team ID
        
    Returns:
        Tuple of (action_edge, error_message). If successful, error_message is None.
    """
    try:
        # Find the live node
        live_node = find_node_by_label(nodes, "live")
        if not live_node:
            return None, "Live node not found in navigation tree"
        
        live_node_id = live_node.get('node_id')
        print(f"[@navigation_utils:validate_action] Found live node with ID: '{live_node_id}'")
        
        # Validate action edge exists (including nested sub-trees)
        action_result = find_action_in_nested_trees(
            live_node_id, tree_id, nodes, edges, action_command, team_id
        )
        
        if not action_result.get('success'):
            # Provide helpful error with available actions
            live_edges = find_edges_from_node(live_node_id, edges)
            available_actions = [
                next((n.get('label') for n in nodes if n.get('node_id') == e.get('target_node_id')), 'unknown') 
                for e in live_edges
            ]
            return None, f"Action '{action_command}' not found from live node. Available actions: {available_actions}"
        
        action_edge = action_result.get('edge')
        tree_type = action_result.get('tree_type')
        action_tree_id = action_result.get('tree_id')
        
        if tree_type == 'main':
            print(f"[@navigation_utils:validate_action] Action '{action_command}' found in main tree - edge: {action_edge.get('edge_id')}")
        else:
            source_node_id = action_result.get('source_node_id')
            print(f"[@navigation_utils:validate_action] Action '{action_command}' found in sub-tree {action_tree_id} - edge: {action_edge.get('edge_id')} (from node: {source_node_id})")
        
        return action_edge, None
        
    except Exception as e:
        return None, f"Action validation error: {str(e)}"


def goto_node(host, device, target_node_label: str, tree_id: str, team_id: str, context=None) -> Dict[str, Any]:
    """
    Navigate to target node using ONLY unified pathfinding
    
    Args:
        host: Host instance
        device: Device instance  
        target_node_label: Label of the target node (e.g., 'home', 'live', 'settings')
        tree_id: Navigation tree ID
        team_id: Team ID
        context: Optional ScriptExecutionContext for tracking step results
        
    Returns:
        Dict with success status and details
    """
    try:
        from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path
        from shared.lib.utils.navigation_exceptions import UnifiedCacheError, PathfindingError
        
        # Determine starting node from context
        start_node_id = None
        if context and hasattr(context, 'current_node_id') and context.current_node_id:
            start_node_id = context.current_node_id
            print(f"[@navigation_utils:goto_node] Starting from current location: {start_node_id}")
        else:
            print(f"[@navigation_utils:goto_node] Starting from default entry point (no current location)")
        
        print(f"[@navigation_utils:goto_node] Navigating to '{target_node_label}' using unified pathfinding")
        
        # Use unified pathfinding with current location as starting point
        navigation_path = find_shortest_path(tree_id, target_node_label, team_id, start_node_id)
        
        if not navigation_path:
            return {
                'success': False,
                'error': f"No unified path found to '{target_node_label}'",
                'unified_pathfinding_used': True
            }
        
        print(f"[@navigation_utils:goto_node] Found path with {len(navigation_path)} steps")
        
        # Execute navigation sequence with early stopping for goto functions
        for i, step in enumerate(navigation_path):
            step_num = i + 1
            from_node = step.get('from_node_label', 'unknown')
            to_node = step.get('to_node_label', 'unknown')
            
            print(f"[@navigation_utils:goto_node] Step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
            
            # Step start screenshot - capture BEFORE action execution (like zap controller)
            step_start_screenshot_path = ""
            if context:
                from .report_utils import capture_and_upload_screenshot
                step_name = f"step_{step_num}_{from_node}_{to_node}"
                step_start_screenshot_result = capture_and_upload_screenshot(host, device, f"{step_name}_start", "navigation")
                step_start_screenshot_path = step_start_screenshot_result.get('screenshot_path', '')
                
                if step_start_screenshot_path:
                    print(f"📸 [@navigation_utils:goto_node] Step-start screenshot captured: {step_start_screenshot_path}")
                    context.add_screenshot(step_start_screenshot_path)
            
            step_start_time = time.time()
            result = execute_navigation_with_verifications(host, device, step, team_id, tree_id)
            step_execution_time = int((time.time() - step_start_time) * 1000)
            
            # Main action screenshot (existing)
            main_screenshot_path = ""
            if context:
                step_screenshot = capture_validation_screenshot(host, device, f"goto_step_{step_num}", "goto")
                main_screenshot_path = step_screenshot
                context.add_screenshot(step_screenshot)
            
            # Step end screenshot - capture AFTER action execution (like zap controller)
            step_end_screenshot_path = ""
            if context:
                step_end_screenshot_result = capture_and_upload_screenshot(host, device, f"{step_name}_end", "navigation")
                step_end_screenshot_path = step_end_screenshot_result.get('screenshot_path', '')
                
                if step_end_screenshot_path:
                    print(f"📸 [@navigation_utils:goto_node] Step-end screenshot captured: {step_end_screenshot_path}")
                    context.add_screenshot(step_end_screenshot_path)
            
            # If context is provided, record the step result
            if context:
                step_start_timestamp = datetime.fromtimestamp(step_start_time).strftime('%H:%M:%S')
                step_end_timestamp = datetime.now().strftime('%H:%M:%S')
                
                step_result = {
                    'success': result.get('success', False),
                    'screenshot_path': main_screenshot_path,
                    'screenshot_url': result.get('screenshot_url'),
                    'step_start_screenshot_path': step_start_screenshot_path,
                    'step_end_screenshot_path': step_end_screenshot_path,
                    'message': f"Navigation step: {from_node} → {to_node}",  # Will be updated with step number
                    'execution_time_ms': step_execution_time,
                    'start_time': step_start_timestamp,
                    'end_time': step_end_timestamp,
                    'from_node': from_node,
                    'to_node': to_node,
                    'actions': step.get('actions', []),
                    'verifications': step.get('verifications', []),
                    'verification_results': result.get('verification_results', []),
                    'error': result.get('error'),  # Store actual error message from action execution
                    'step_category': 'navigation'
                }
                
                # Record step immediately - step number shown in table
                context.record_step_immediately(step_result)
                # Simple message without redundant step number
                step_result['message'] = f"{from_node} → {to_node}"
            
            if not result.get('success', False):
                error_msg = result.get('error', 'Unknown error')
                error_details = result.get('error_details', {})
                
                print(f"[@navigation_utils:goto_node] NAVIGATION STEP FAILED:")
                print(f"[@navigation_utils:goto_node]   Step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
                print(f"[@navigation_utils:goto_node]   Error: {error_msg}")
                print(f"[@navigation_utils:goto_node]   Execution time: {step_execution_time}ms")
                
                # Log additional error details if available
                if error_details:
                    if error_details.get('edge_id'):
                        print(f"[@navigation_utils:goto_node]   Edge ID: {error_details.get('edge_id')}")
                    if error_details.get('actions_count'):
                        print(f"[@navigation_utils:goto_node]   Actions attempted: {error_details.get('actions_count')}")
                    if error_details.get('retry_actions_count'):
                        print(f"[@navigation_utils:goto_node]   Retry actions attempted: {error_details.get('retry_actions_count')}")
                    if error_details.get('failure_actions_count'):
                        print(f"[@navigation_utils:goto_node]   Failure actions attempted: {error_details.get('failure_actions_count')}")
                    
                    # Log specific actions that failed
                    failed_actions = error_details.get('actions', [])
                    if failed_actions:
                        print(f"[@navigation_utils:goto_node]   Failed actions:")
                        for i, action in enumerate(failed_actions):
                            cmd = action.get('command', 'unknown')
                            params = action.get('params', {})
                            print(f"[@navigation_utils:goto_node]     {i+1}. {cmd}: {params}")
                
                # GOTO FUNCTIONS: Stop immediately on ANY step failure (no recovery attempts)
                print(f"🛑 [@navigation_utils:goto_node] STOPPING navigation - goto functions do not recover from failures")
                detailed_error_msg = f"Navigation failed at step {step_num} ({from_node} → {to_node}): {error_msg}"
                return {
                    'success': False, 
                    'error': detailed_error_msg,
                    'error_details': {
                        'step_number': step_num,
                        'total_steps': len(navigation_path),
                        'from_node': from_node,
                        'to_node': to_node,
                        'execution_time_ms': step_execution_time,
                        'original_error': error_msg,
                        'action_details': error_details
                    }
                }
            
            print(f"[@navigation_utils:goto_node] Step {step_num} completed successfully in {step_execution_time}ms")
        
        print(f"[@navigation_utils:goto_node] Successfully navigated to '{target_node_label}'!")
        
        # Update current location in context after successful navigation
        if context and hasattr(context, 'current_node_id') and navigation_path:
            # Get the final destination node ID from the last step
            final_step = navigation_path[-1]
            target_node_id = final_step.get('to_node_id')
            if target_node_id:
                context.current_node_id = target_node_id
                print(f"[@navigation_utils:goto_node] Updated current location to: {target_node_id}")
        
        # Count cross-tree transitions
        cross_tree_transitions = len([step for step in navigation_path if step.get('tree_context_change')])
        
        return {
            'success': True,
            'message': f"Successfully navigated to '{target_node_label}' in {len(navigation_path)} steps",
            'path_length': len(navigation_path),
            'cross_tree_transitions': cross_tree_transitions,
            'unified_pathfinding_used': True
        }
        
    except (UnifiedCacheError, PathfindingError) as e:
        print(f"❌ [@navigation_utils:goto_node] Unified navigation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'unified_pathfinding_required': True
        }
    except Exception as e:
        error_msg = f"Unexpected navigation error to '{target_node_label}': {str(e)}"
        print(f"❌ [@navigation_utils:goto_node] ERROR: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'unified_pathfinding_used': True
        }


