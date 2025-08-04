"""
Unified Pathfinding System for Navigation Trees
Uses NetworkX for cross-tree shortest path calculations with fail-early behavior
"""

import networkx as nx
from typing import List, Dict, Optional, Tuple
from shared.lib.utils.navigation_exceptions import UnifiedCacheError, PathfindingError


def find_shortest_path(tree_id: str, target_node_id: str, team_id: str, start_node_id: str = None) -> List[Dict]:
    """
    Find shortest path using ONLY unified graph - no fallback to single-tree
    FAIL EARLY: If unified cache missing, operation fails immediately
    
    Args:
        tree_id: Navigation tree ID (treated as root tree for unified pathfinding)
        target_node_id: Target node to navigate to (can be node ID or label)
        team_id: Team ID for security
        start_node_id: Starting node (if None, uses entry point; can be node ID or label)
        
    Returns:
        List of navigation steps
        
    Raises:
        UnifiedCacheError: If unified cache is not available
        PathfindingError: If no path can be found
    """
    print(f"[@navigation:pathfinding:unified_only] Finding path to '{target_node_id}' (unified pathfinding required)")
    
    # Use unified pathfinding ONLY - NO FALLBACK
    unified_result = find_shortest_path_unified(tree_id, target_node_id, team_id, start_node_id)
    if unified_result:
        print(f"[@navigation:pathfinding:unified_only] Found path using unified graph: {len(unified_result)} transitions")
        return unified_result
    
    # FAIL EARLY - no fallback available
    raise PathfindingError(f"No unified path found to '{target_node_id}'. Unified pathfinding is required - no single-tree fallback available.")


def find_shortest_path_unified(root_tree_id: str, target_node_id: str, team_id: str, start_node_id: str = None) -> Optional[List[Dict]]:
    """
    Find shortest path across nested trees using unified graph
    Enhanced with fail-early behavior and clear error messages
    
    Args:
        root_tree_id: Root navigation tree ID
        target_node_id: Target node to navigate to (can be node ID or label)
        team_id: Team ID for security
        start_node_id: Starting node (if None, uses entry point; can be node ID or label)
        
    Returns:
        List of navigation transitions with cross-tree context or None if no path found
    """
    print(f"[@navigation:pathfinding:find_shortest_path_unified] Finding unified path to node {target_node_id}")
    
    # Get unified cached graph - MANDATORY
    from shared.lib.utils.navigation_cache import get_cached_unified_graph, get_node_tree_location, get_tree_hierarchy_metadata
    from shared.lib.utils.navigation_graph import get_entry_points, get_node_info
    
    unified_graph = get_cached_unified_graph(root_tree_id, team_id)
    if not unified_graph:
        print(f"[@navigation:pathfinding:find_shortest_path_unified] No unified graph cached for root tree {root_tree_id}")
        raise UnifiedCacheError(f"No unified graph cached for root tree {root_tree_id}. Unified pathfinding is required - no fallback available.")
    
    print(f"[@navigation:pathfinding:find_shortest_path_unified] Using unified graph with {len(unified_graph.nodes)} nodes and {len(unified_graph.edges)} edges")
    
    # Check if target is an action node
    target_node_data = unified_graph.nodes.get(target_node_id, {})
    if target_node_data.get('node_type') == 'action':
        print(f"[@navigation:pathfinding:find_shortest_path_unified] Cannot navigate to action node {target_node_id}")
        raise PathfindingError(f"Cannot navigate to action node {target_node_id}")
    
    # Resolve target_node_id if it's a label instead of UUID
    actual_target_node = target_node_id
    if target_node_id not in unified_graph.nodes:
        print(f"[@navigation:pathfinding:find_shortest_path_unified] Target '{target_node_id}' not found as node ID, searching by label...")
        for node_id, node_data in unified_graph.nodes(data=True):
            if node_data.get('label', '') == target_node_id and node_data.get('node_type') != 'action':
                actual_target_node = node_id
                print(f"[@navigation:pathfinding:find_shortest_path_unified] Resolved label '{target_node_id}' to node ID '{node_id}'")
                break
        else:
            # Try case-insensitive search
            for node_id, node_data in unified_graph.nodes(data=True):
                if node_data.get('label', '').lower() == target_node_id.lower() and node_data.get('node_type') != 'action':
                    actual_target_node = node_id
                    print(f"[@navigation:pathfinding:find_shortest_path_unified] Resolved label '{target_node_id}' to node ID '{node_id}' (case-insensitive)")
                    break
    
    # Determine starting node
    actual_start_node = start_node_id
    if start_node_id:
        # Resolve start_node_id if it's a label instead of UUID
        if start_node_id not in unified_graph.nodes:
            print(f"[@navigation:pathfinding:find_shortest_path_unified] Start '{start_node_id}' not found as node ID, searching by label...")
            for node_id, node_data in unified_graph.nodes(data=True):
                if node_data.get('label', '') == start_node_id:
                    actual_start_node = node_id
                    print(f"[@navigation:pathfinding:find_shortest_path_unified] Resolved start label '{start_node_id}' to node ID '{node_id}'")
                    break
            else:
                # Try case-insensitive search
                for node_id, node_data in unified_graph.nodes(data=True):
                    if node_data.get('label', '').lower() == start_node_id.lower():
                        actual_start_node = node_id
                        print(f"[@navigation:pathfinding:find_shortest_path_unified] Resolved start label '{start_node_id}' to node ID '{node_id}' (case-insensitive)")
                        break
    
    if not actual_start_node:
        entry_points = get_entry_points(unified_graph)
        
        if not entry_points:
            print(f"[@navigation:pathfinding:find_shortest_path_unified] No entry points found, using first node")
            nodes = list(unified_graph.nodes())
            if not nodes:
                print(f"[@navigation:pathfinding:find_shortest_path_unified] No nodes in unified graph")
                raise PathfindingError("No nodes in unified graph")
            actual_start_node = nodes[0]
        else:
            # Prioritize dedicated entry node over home node
            dedicated_entry = None
            for entry_id in entry_points:
                entry_info = get_node_info(unified_graph, entry_id)
                if entry_info and entry_info.get('node_type') == 'entry':
                    dedicated_entry = entry_id
                    break
            
            actual_start_node = dedicated_entry if dedicated_entry else entry_points[0]
    
    # Validate nodes exist
    if actual_start_node not in unified_graph.nodes:
        raise PathfindingError(f"Start node {actual_start_node} not found in unified graph")
    
    if actual_target_node not in unified_graph.nodes:
        available_nodes = list(unified_graph.nodes())
        raise PathfindingError(f"Target node {actual_target_node} not found in unified graph. Available nodes: {available_nodes}")
    
    # Final check: ensure target is not an action node
    final_target_data = unified_graph.nodes.get(actual_target_node, {})
    if final_target_data.get('node_type') == 'action':
        raise PathfindingError(f"Cannot navigate to action node {actual_target_node}")
    
    # Check if we're already at the target
    if actual_start_node == actual_target_node:
        print(f"[@navigation:pathfinding:find_shortest_path_unified] Already at target node {actual_target_node}")
        return []
    
    try:
        # Use NetworkX shortest path algorithm on unified graph
        path = nx.shortest_path(unified_graph, actual_start_node, actual_target_node)
        print(f"[@navigation:pathfinding:find_shortest_path_unified] Found path with {len(path)} nodes")
        print(f"[@navigation:pathfinding:find_shortest_path_unified] Path nodes: {' → '.join(path)}")
        
        # Convert path to navigation transitions with cross-tree support
        navigation_transitions = []
        transition_number = 1
        
        for i in range(len(path) - 1):
            from_node = path[i]
            to_node = path[i + 1]
            
            # Get node information
            from_node_info = get_node_info(unified_graph, from_node) or {}
            to_node_info = get_node_info(unified_graph, to_node) or {}
            
            # Get edge data - check multiple possible action formats
            edge_data = unified_graph.edges[from_node, to_node] if unified_graph.has_edge(from_node, to_node) else {}
            
            # Extract actions - try multiple formats for backward compatibility
            actions_list = []
            if 'actions' in edge_data:
                actions_list = edge_data['actions']
            elif 'default_actions' in edge_data:
                actions_list = edge_data['default_actions']
            elif 'action_sets' in edge_data:
                # Try to get actions from action_sets structure
                action_sets = edge_data.get('action_sets', [])
                default_action_set_id = edge_data.get('default_action_set_id')
                if action_sets and default_action_set_id:
                    default_set = next((s for s in action_sets if s['id'] == default_action_set_id), None)
                    if default_set:
                        actions_list = default_set.get('actions', [])
            
            # Extract retry actions
            retry_actions_list = []
            if 'retry_actions' in edge_data:
                retry_actions_list = edge_data['retry_actions']
            elif 'retryActions' in edge_data:
                retry_actions_list = edge_data['retryActions']
            elif 'action_sets' in edge_data:
                # Try to get retry actions from action_sets structure
                action_sets = edge_data.get('action_sets', [])
                default_action_set_id = edge_data.get('default_action_set_id')
                if action_sets and default_action_set_id:
                    default_set = next((s for s in action_sets if s['id'] == default_action_set_id), None)
                    if default_set:
                        retry_actions_list = default_set.get('retry_actions', [])
            
            verifications_list = to_node_info.get('verifications', [])
            
            # Debug logging for action extraction
            print(f"[@navigation:pathfinding:find_shortest_path_unified]   Edge data keys: {list(edge_data.keys())}")
            print(f"[@navigation:pathfinding:find_shortest_path_unified]   Actions found: {len(actions_list)}")
            print(f"[@navigation:pathfinding:find_shortest_path_unified]   Retry actions found: {len(retry_actions_list)}")
            
            # Check for cross-tree transition
            transition_type = edge_data.get('edge_type', 'NORMAL')
            is_cross_tree = transition_type in ['ENTER_SUBTREE', 'EXIT_SUBTREE']
            
            # Get tree context
            from_tree_id = from_node_info.get('tree_id', '')
            to_tree_id = to_node_info.get('tree_id', '')
            tree_context_change = from_tree_id != to_tree_id
            
            print(f"[@navigation:pathfinding:find_shortest_path_unified] Transition {transition_number}: {from_node_info.get('label', from_node)} → {to_node_info.get('label', to_node)}")
            if is_cross_tree:
                print(f"[@navigation:pathfinding:find_shortest_path_unified]   Cross-tree transition: {transition_type}")
                print(f"[@navigation:pathfinding:find_shortest_path_unified]   From tree: {from_tree_id} → To tree: {to_tree_id}")
            
            # Create navigation transition with cross-tree metadata and proper action execution fields
            navigation_transition = {
                'transition_number': transition_number,
                'from_node_id': from_node,
                'to_node_id': to_node,
                'from_node_label': from_node_info.get('label', from_node),
                'to_node_label': to_node_info.get('label', to_node),
                'from_tree_id': from_tree_id,
                'to_tree_id': to_tree_id,
                'transition_type': transition_type,
                'tree_context_change': tree_context_change,
                'actions': actions_list,  # Primary field expected by action execution
                'retryActions': retry_actions_list,  # Primary field expected by action execution  
                'verifications': verifications_list,
                'total_actions': len(actions_list),
                'total_retry_actions': len(retry_actions_list),
                'total_verifications': len(verifications_list),
                'finalWaitTime': edge_data.get('finalWaitTime', edge_data.get('final_wait_time', 2000)),
                'edge_id': edge_data.get('edge_id', 'unknown'),
                'alternatives_count': edge_data.get('alternatives_count', 1),
                'is_virtual': edge_data.get('is_virtual', False),
                'description': f"Navigate from '{from_node_info.get('label', from_node)}' to '{to_node_info.get('label', to_node)}'",
                # Add legacy fields for compatibility
                'default_actions': actions_list,  # Backup field
                'action_sets': edge_data.get('action_sets', []),  # Original action_sets structure
                'default_action_set_id': edge_data.get('default_action_set_id')
            }
            
            # Add cross-tree metadata if applicable
            if is_cross_tree:
                navigation_transition['cross_tree_metadata'] = {
                    'source_tree_name': from_node_info.get('tree_name', ''),
                    'target_tree_name': to_node_info.get('tree_name', ''),
                    'tree_depth_change': to_node_info.get('tree_depth', 0) - from_node_info.get('tree_depth', 0)
                }
            
            navigation_transitions.append(navigation_transition)
            transition_number += 1
        
        print(f"[@navigation:pathfinding:find_shortest_path_unified] Generated {len(navigation_transitions)} navigation transitions")
        
        # Count cross-tree transitions
        cross_tree_count = len([t for t in navigation_transitions if t.get('tree_context_change')])
        if cross_tree_count > 0:
            print(f"[@navigation:pathfinding:find_shortest_path_unified] Cross-tree transitions: {cross_tree_count}")
        
        return navigation_transitions
        
    except nx.NetworkXNoPath:
        print(f"[@navigation:pathfinding:find_shortest_path_unified] No path found from {actual_start_node} to {actual_target_node}")
        raise PathfindingError(f"No path found from {actual_start_node} to {actual_target_node} in unified graph")
    except Exception as e:
        print(f"[@navigation:pathfinding:find_shortest_path_unified] Error finding path: {e}")
        raise PathfindingError(f"Error finding unified path: {str(e)}")


# Keep only essential helper functions - remove all legacy single-tree functions
def get_navigation_transitions(tree_id: str, target_node_id: str, team_id: str, current_node_id: str = None) -> List[Dict]:
    """
    Get step-by-step navigation instructions using unified pathfinding only
    """
    return find_shortest_path(tree_id, target_node_id, team_id, current_node_id)


def validate_action_availability(nodes: List[Dict], edges: List[Dict], action_command: str, tree_id: str, team_id: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Validate that an action is available in the navigation tree
    Uses unified pathfinding system
    """
    try:
        # This function needs to be updated to work with unified graphs
        # For now, return a simple validation
        print(f"[@navigation:pathfinding:validate_action_availability] Validating action '{action_command}' in unified system")
        
        # Find edges that contain the action command
        for edge in edges:
            actions = edge.get('actions', [])
            for action in actions:
                if action.get('command') == action_command:
                    print(f"[@navigation:pathfinding:validate_action_availability] Action '{action_command}' found in edge {edge.get('edge_id')}")
                    return edge, None
        
        return None, f"Action '{action_command}' not found in navigation tree"
        
    except Exception as e:
        return None, f"Error validating action: {str(e)}"


def find_optimal_edge_validation_sequence(tree_id: str, team_id: str) -> List[Dict]:
    """
    Find optimal sequence for validating all edges using unified pathfinding
    FAIL EARLY: No legacy fallback - requires unified cache
    
    Args:
        tree_id: Navigation tree ID (treated as root tree)
        team_id: Team ID for security
        
    Returns:
        List of validation steps ordered for optimal traversal
        
    Raises:
        UnifiedCacheError: If unified cache is not available
        PathfindingError: If validation sequence cannot be built
    """
    print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] Finding validation sequence for unified tree {tree_id}")
    
    try:
        from shared.lib.utils.navigation_cache import get_cached_unified_graph
        from shared.lib.utils.navigation_graph import get_entry_points, get_node_info
        
        # Get unified graph - MANDATORY
        unified_graph = get_cached_unified_graph(tree_id, team_id)
        if not unified_graph:
            raise UnifiedCacheError(f"No unified graph cached for tree {tree_id}. Validation requires unified pathfinding.")
        
        print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] Using unified graph with {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
        
        # Get all edges that need validation
        edges_to_validate = []
        for u, v, data in unified_graph.edges(data=True):
            # Skip virtual cross-tree edges for validation
            if not data.get('is_virtual', False):
                edges_to_validate.append((u, v, data))
        
        if not edges_to_validate:
            print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] No edges to validate")
            return []
        
        print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] Found {len(edges_to_validate)} edges to validate")
        
        # Create validation sequence using unified graph
        validation_sequence = []
        step_number = 1
        
        for u, v, edge_data in edges_to_validate:
            from_node_data = unified_graph.nodes.get(u, {})
            to_node_data = unified_graph.nodes.get(v, {})
            
            # Get actions from edge
            actions = edge_data.get('actions', [])
            retry_actions = edge_data.get('retry_actions', [])
            verifications = to_node_data.get('verifications', [])
            
            # Check for cross-tree transition
            from_tree_id = from_node_data.get('tree_id', '')
            to_tree_id = to_node_data.get('tree_id', '')
            is_cross_tree = from_tree_id != to_tree_id
            
            validation_step = {
                'step_number': step_number,
                'step_type': 'cross_tree_validation' if is_cross_tree else 'unified_validation',
                'from_node_id': u,
                'to_node_id': v,
                'from_node_label': from_node_data.get('label', u),
                'to_node_label': to_node_data.get('label', v),
                'from_tree_id': from_tree_id,
                'to_tree_id': to_tree_id,
                'tree_context_change': is_cross_tree,
                'actions': actions,
                'retryActions': retry_actions,
                'verifications': verifications,
                'total_actions': len(actions),
                'total_retry_actions': len(retry_actions),
                'total_verifications': len(verifications),
                'finalWaitTime': edge_data.get('final_wait_time', 2000),
                'is_virtual': edge_data.get('is_virtual', False),
                'description': f"Validate unified transition: {from_node_data.get('label', u)} → {to_node_data.get('label', v)}"
            }
            
            # Add cross-tree metadata if applicable
            if is_cross_tree:
                validation_step['cross_tree_metadata'] = {
                    'source_tree_name': from_node_data.get('tree_name', ''),
                    'target_tree_name': to_node_data.get('tree_name', ''),
                    'tree_depth_change': to_node_data.get('tree_depth', 0) - from_node_data.get('tree_depth', 0)
                }
            
            validation_sequence.append(validation_step)
            step_number += 1
        
        cross_tree_count = len([step for step in validation_sequence if step.get('tree_context_change')])
        
        print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] Generated {len(validation_sequence)} validation steps")
        print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] Cross-tree validations: {cross_tree_count}")
        
        return validation_sequence
        
    except (UnifiedCacheError, PathfindingError) as e:
        # Re-raise navigation-specific errors
        raise e
    except Exception as e:
        # FAIL EARLY - no fallback
        raise PathfindingError(f"Validation sequence generation failed: {str(e)}")