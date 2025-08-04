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
    Simple one-line navigation function to go to any node.
    
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
        
        print(f"[@navigation_utils:goto_node] Finding path to '{target_node_label}'...")
        
        # Find path to target node
        navigation_path = find_shortest_path(tree_id, target_node_label, team_id)
        
        if not navigation_path:
            return {
                'success': False, 
                'error': f"No path found to node '{target_node_label}'"
            }
        
        print(f"[@navigation_utils:goto_node] Found path with {len(navigation_path)} steps")
        
        # Execute navigation sequence
        for i, step in enumerate(navigation_path):
            step_num = i + 1
            from_node = step.get('from_node_label', 'unknown')
            to_node = step.get('to_node_label', 'unknown')
            
            print(f"[@navigation_utils:goto_node] Step {step_num}/{len(navigation_path)}: {from_node} → {to_node}")
            
            step_start_time = time.time()
            result = execute_navigation_with_verifications(host, device, step, team_id, tree_id)
            step_execution_time = int((time.time() - step_start_time) * 1000)
            
            # If context is provided, record the step result
            if context:
                step_start_timestamp = datetime.fromtimestamp(step_start_time).strftime('%H:%M:%S')
                step_end_timestamp = datetime.now().strftime('%H:%M:%S')
                
                # Capture screenshot
                step_screenshot = capture_validation_screenshot(host, device, f"goto_step_{step_num}", "goto")
                context.add_screenshot(step_screenshot)
                
                step_result = {
                    'step_number': len(context.step_results) + 1,
                    'success': result.get('success', False),
                    'screenshot_path': step_screenshot,
                    'message': f"Navigation step {step_num}: {from_node} → {to_node}",
                    'execution_time_ms': step_execution_time,
                    'start_time': step_start_timestamp,
                    'end_time': step_end_timestamp,
                    'from_node': from_node,
                    'to_node': to_node,
                    'actions': step.get('actions', []),
                    'verifications': step.get('verifications', []),
                    'verification_results': result.get('verification_results', [])
                }
                context.step_results.append(step_result)
            
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
                    
                    # Log specific actions that failed
                    failed_actions = error_details.get('actions', [])
                    if failed_actions:
                        print(f"[@navigation_utils:goto_node]   Failed actions:")
                        for i, action in enumerate(failed_actions):
                            cmd = action.get('command', 'unknown')
                            params = action.get('params', {})
                            print(f"[@navigation_utils:goto_node]     {i+1}. {cmd}: {params}")
                
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
        return {
            'success': True, 
            'message': f"Successfully navigated to '{target_node_label}' in {len(navigation_path)} steps"
        }
        
    except Exception as e:
        error_msg = f"Navigation to '{target_node_label}' failed: {str(e)}"
        print(f"[@navigation_utils:goto_node] ERROR: {error_msg}")
        return {'success': False, 'error': error_msg}


