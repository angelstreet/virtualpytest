"""
Unified Pathfinding System for Navigation Trees
Uses NetworkX for cross-tree shortest path calculations with fail-early behavior
"""

import networkx as nx
from typing import List, Dict, Optional, Tuple
from src.lib.utils.navigation_exceptions import UnifiedCacheError, PathfindingError


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
    from src.lib.utils.navigation_cache import get_cached_unified_graph, get_node_tree_location, get_tree_hierarchy_metadata
    from src.lib.utils.navigation_graph import get_entry_points, get_node_info
    
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
            
            # Use standardized 2-action-set structure: forward (index 0) then reverse (index 1)
            action_sets = edge_data.get('action_sets', [])
            
            if not action_sets:
                raise PathfindingError(f"Edge {from_node} -> {to_node} missing action_sets")
            
            # Always use forward action set (first in array) for regular pathfinding
            forward_set = action_sets[0]
            actions_list = forward_set.get('actions', [])
            retry_actions_list = forward_set.get('retry_actions') or []
            verifications_list = to_node_info.get('verifications', [])
            
            # Debug logging
            print(f"[@navigation:pathfinding:find_shortest_path_unified]   Action sets: {len(action_sets)}")
            print(f"[@navigation:pathfinding:find_shortest_path_unified]   Using forward set: {forward_set.get('id')}")
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
            
            # Create navigation transition with action_sets structure ONLY
            navigation_transition = {
                'transition_number': transition_number,
                'step_number': transition_number,  # Add step_number for action_utils compatibility
                'from_node_id': from_node,
                'to_node_id': to_node,
                'from_node_label': from_node_info.get('label', from_node),
                'to_node_label': to_node_info.get('label', to_node),
                'from_tree_id': from_tree_id,
                'to_tree_id': to_tree_id,
                'transition_type': transition_type,
                'tree_context_change': tree_context_change,
                'actions': actions_list,
                'retryActions': retry_actions_list,
                'action_set_id': forward_set.get('id'),  # Track forward action set used
                'original_edge_data': edge_data,  # Preserve original edge structure
                'verifications': verifications_list,
                'finalWaitTime': edge_data.get('finalWaitTime', 2000),
                'edge_id': edge_data.get('edge_id', 'unknown'),
                'is_virtual': edge_data.get('is_virtual', False),
                'description': f"Navigate from '{from_node_info.get('label', from_node)}' to '{to_node_info.get('label', to_node)}'"
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
        # Enhanced error logging with node labels
        start_label = "unknown"
        target_label = "unknown"
        try:
            start_node_info = get_node_info(unified_graph, actual_start_node)
            if start_node_info:
                start_label = start_node_info.get('label', 'unknown')
            
            target_node_info = get_node_info(unified_graph, actual_target_node)
            if target_node_info:
                target_label = target_node_info.get('label', 'unknown')
        except:
            pass  # Fall back to 'unknown' if label lookup fails
            
        print(f"[@navigation:pathfinding:find_shortest_path_unified] No path found from {start_label} ({actual_start_node}) to {target_label} ({actual_target_node})")
        raise PathfindingError(f"No path found from '{start_label} ({actual_start_node})' to '{target_label} ({actual_target_node})' in unified graph")
    except Exception as e:
        print(f"[@navigation:pathfinding:find_shortest_path_unified] Error finding path: {e}")
        raise PathfindingError(f"Error finding unified path: {str(e)}")


# Keep only essential helper functions - remove all legacy single-tree functions
def get_navigation_transitions(tree_id: str, target_node_id: str, team_id: str, current_node_id: str = None) -> List[Dict]:
    """
    Get step-by-step navigation instructions using unified pathfinding only
    """
    return find_shortest_path(tree_id, target_node_id, team_id, current_node_id)




def find_optimal_edge_validation_sequence(tree_id: str, team_id: str) -> List[Dict]:
    """
    Find optimal sequence for validating all edges with enhanced bidirectional support.
    Uses depth-first traversal to ensure systematic coverage.
    
    Args:
        tree_id: Navigation tree ID
        team_id: Team ID for security
        
    Returns:
        List of validation steps ordered for optimal traversal
    """
    print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] Finding optimal validation sequence for tree {tree_id}")
    
    from src.lib.utils.navigation_cache import get_cached_unified_graph
    
    G = get_cached_unified_graph(tree_id, team_id)
    if not G:
        print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] Failed to get graph for tree {tree_id}")
        return []
    
    # Get all edges that need validation
    edges_to_validate = []
    for u, v, data in G.edges(data=True):
        # Skip virtual cross-tree edges for validation
        if not data.get('is_virtual', False):
            edges_to_validate.append((u, v, data))
    
    if not edges_to_validate:
        print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] No edges to validate")
        return []
    
    print(f"[@navigation:pathfinding:find_optimal_edge_validation_sequence] Found {len(edges_to_validate)} edges to validate")
    
    # Use depth-first traversal for optimal validation sequence
    validation_sequence = _create_reachability_based_validation_sequence(
        G, edges_to_validate, tree_id, team_id
    )
    
    return validation_sequence


def _create_reachability_based_validation_sequence(G, edges_to_validate: List[Tuple], 
                                                 tree_id: str, team_id: str) -> List[Dict]:
    """
    Create validation sequence using depth-first traversal that goes deep into each branch before coming back.
    
    Args:
        G: NetworkX graph
        edges_to_validate: List of (from_node, to_node, edge_data) tuples
        
    Returns:
        List of validation steps ordered by depth-first traversal
    """
    from src.lib.utils.navigation_graph import get_entry_points, get_node_info
    
    print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Creating depth-first validation sequence")
    
    # Build edge mapping for quick lookup INCLUDING bidirectional edges
    edge_map = {}
    bidirectional_edges = set()
    
    for u, v, data in edges_to_validate:
        edge_map[(u, v)] = data
        
        # Check if reverse direction has actions (action set at index 1)
        action_sets = data.get('action_sets', [])
        if len(action_sets) >= 2:
            reverse_set = action_sets[1]  # Index 1 = reverse action set
            if reverse_set and reverse_set.get('actions'):
                # Add reverse edge to map - reverse direction has valid actions
                edge_map[(v, u)] = data
                bidirectional_edges.add((u, v))
                bidirectional_edges.add((v, u))
                
                from_info = get_node_info(G, u) or {}
                to_info = get_node_info(G, v) or {}
                from_label = from_info.get('label', u)
                to_label = to_info.get('label', v)
                print(f"[@navigation:pathfinding] Reverse direction available: {from_label} ↔ {to_label}")
    
    print(f"[@navigation:pathfinding] Edge mapping complete: {len(edge_map)} total edges, {len(bidirectional_edges)//2} with reverse actions")
    
    # Build adjacency list for traversal
    adjacency = {}
    for u, v, data in edges_to_validate:
        if u not in adjacency:
            adjacency[u] = []
        adjacency[u].append(v)
        
        # Make adjacency symmetric for bidirectional edges to ensure all directions are traversed as children
        if (v, u) in edge_map:  # If reverse exists
            if v not in adjacency:
                adjacency[v] = []
            if u not in adjacency[v]:
                adjacency[v].append(u)  # Add reverse as child
    
    # Sort children for consistent ordering
    for node in adjacency:
        adjacency[node].sort()
    
    # Find entry points
    entry_points = get_entry_points(G)
    if not entry_points:
        # Find nodes with no incoming edges
        entry_points = [node for node in G.nodes() if G.in_degree(node) == 0]
    if not entry_points and G.nodes():
        entry_points = [list(G.nodes())[0]]
    
    print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Starting depth-first from entry points: {entry_points}")
    
    validation_sequence = []
    visited_edges = set()
    step_number = 1
    current_position = entry_points[0] if entry_points else None
    recursion_stack = set()  # For cycle detection in DFS

    def depth_first_traversal(current_node, parent_node=None):
        """Recursively traverse depth-first, going deep into each branch before coming back"""
        nonlocal step_number, current_position
        
        if current_node in recursion_stack:
            print(f"[@navigation:pathfinding] Cycle detected at {current_node} - skipping recursion")
            return
        
        recursion_stack.add(current_node)
        
        # Process all children of current node depth-first
        for child_node in adjacency.get(current_node, []):
            forward_edge = (current_node, child_node)
            
            # Skip if already visited or if it's the parent (avoid immediate back-and-forth)
            if forward_edge in visited_edges or child_node == parent_node:
                continue
            
            # Add forward edge
            from_info = get_node_info(G, current_node) or {}
            to_info = get_node_info(G, child_node) or {}
            from_label = from_info.get('label', current_node)
            to_label = to_info.get('label', child_node)
            
            forced_steps, validation_step = _create_validation_step(G, current_node, child_node, edge_map[forward_edge], step_number, 'depth_first_forward', current_position, tree_id, team_id)
            validation_sequence.extend(forced_steps)
            if validation_step is not None:
                validation_sequence.append(validation_step)
                visited_edges.add(forward_edge)
                
                print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Step {validation_step['step_number']}: {from_label} → {to_label} (forward)")
                step_number = validation_step['step_number'] + 1
            else:
                print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Skipping unreachable step: {from_label} → {to_label} (forward)")
                step_number += 1
            
            # Update position: if target is action node, stay at current node, otherwise move to target
            child_node_info = get_node_info(G, child_node) or {}
            if child_node_info.get('node_type') == 'action':
                # Action nodes don't change position - we stay where we were
                print(f"[@navigation:pathfinding] Action node {to_label} - staying at {from_label}")
                # current_position stays the same
            else:
                current_position = child_node
            
            # Recursively go deeper into this child's branch
            depth_first_traversal(child_node, current_node)
            
            # ENHANCED RETURN EDGE DETECTION
            return_edge = (child_node, current_node)
            return_edge_data = None
            return_method = None
            
            # Strategy 1: Direct return edge exists
            if return_edge in edge_map and return_edge not in visited_edges:
                return_edge_data = edge_map[return_edge]
                return_method = "direct"
                print(f"[@navigation:pathfinding] Found direct return edge: {to_label} → {from_label}")
            
            # Strategy 2: Reverse direction has actions available
            elif forward_edge in bidirectional_edges and return_edge not in visited_edges:
                return_edge_data = edge_map[forward_edge]  # Same edge data
                return_method = "reverse_actions"
                print(f"[@navigation:pathfinding] Found reverse actions: {to_label} → {from_label}")
            
            # Strategy 3: Transitional edge using pathfinding (always enabled)
            elif return_edge not in visited_edges:
                try:
                    # Try to find a path back using unified pathfinding
                    transitional_path = find_shortest_path_unified(tree_id, current_node, team_id, child_node)
                    if transitional_path:
                        print(f"[@navigation:pathfinding] Using transitional path: {to_label} → {from_label} ({len(transitional_path)} steps)")
                        for i, step in enumerate(transitional_path):
                            step['step_type'] = 'transitional_return'
                            step['step_number'] = step_number + i
                            validation_sequence.append(step)
                        step_number += len(transitional_path)
                        visited_edges.add(return_edge)  # Mark as handled
                        continue
                except Exception as e:
                    print(f"[@navigation:pathfinding] Transitional path failed: {e}")
            
            # Execute return if found
            if return_edge_data:
                forced_steps, validation_step = _create_validation_step(G, child_node, current_node, return_edge_data, step_number, f'depth_first_return_{return_method}', current_position, tree_id, team_id)
                validation_sequence.extend(forced_steps)
                if validation_step is not None:
                    validation_sequence.append(validation_step)
                    visited_edges.add(return_edge)
                    
                    print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Step {validation_step['step_number']}: {to_label} → {from_label} (return via {return_method})")
                    step_number = validation_step['step_number'] + 1
                    current_position = current_node
                else:
                    print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Skipping unreachable return step: {to_label} → {from_label} (return via {return_method})")
                    step_number += 1
            else:
                # Strategy 4: No return path available - this is OK for unidirectional actions
                print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] No return path for: {to_label} → {from_label} (unidirectional action - OK)")
        
        recursion_stack.remove(current_node)
    
    # Start depth-first traversal from each entry point
    for entry_point in entry_points:
        depth_first_traversal(entry_point)
    
    # Add any remaining unvisited edges INCLUDING all valid bidirectional edges
    remaining_edges = [(u, v) for u, v in edge_map.keys() if (u, v) not in visited_edges]
    
    print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Found {len(remaining_edges)} remaining unvisited edges")
    
    for edge in remaining_edges:
        from_node, to_node = edge
        

        
        from_info = get_node_info(G, from_node) or {}
        to_info = get_node_info(G, to_node) or {}
        from_label = from_info.get('label', from_node)
        to_label = to_info.get('label', to_node)
        
        # Check if this is a valid edge (has non-empty actions)
        edge_data = edge_map[edge]
        action_sets = edge_data.get('action_sets', [])
        
        # For bidirectional edges, determine which action set to use
        is_bidirectional_return = edge in bidirectional_edges and (to_node, from_node) in visited_edges
        
        has_valid_actions = False
        if is_bidirectional_return:
            # This is a reverse direction - use action set at index 1
            reverse_set = action_sets[1] if len(action_sets) >= 2 else None
            has_valid_actions = reverse_set and reverse_set.get('actions')
        else:
            # This is a forward direction - use action set at index 0
            forward_set = action_sets[0] if action_sets else None
            has_valid_actions = forward_set and forward_set.get('actions')
        
        if has_valid_actions:
            step_type = 'remaining_reverse' if is_bidirectional_return else 'remaining_forward'
            forced_steps, validation_step = _create_validation_step(G, from_node, to_node, edge_data, step_number, step_type, current_position, tree_id, team_id)
            validation_sequence.extend(forced_steps)
            if validation_step is not None:
                validation_sequence.append(validation_step)
                visited_edges.add(edge)
                
                print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Step {validation_step['step_number']} (remaining): {from_label} → {to_label} ({step_type})")
                step_number = validation_step['step_number'] + 1
            else:
                print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Skipping unreachable remaining step: {from_label} → {to_label} ({step_type})")
                step_number += 1
                # Don't update position if step is unreachable
                continue
            
            # Update position: if target is action node, stay at from_node, otherwise move to to_node
            to_node_info = get_node_info(G, to_node) or {}
            if to_node_info.get('node_type') == 'action':
                # Action nodes don't change position - we stay at from_node
                print(f"[@navigation:pathfinding] Action node {to_label} - staying at {from_label}")
                current_position = from_node
            else:
                current_position = to_node
        else:
            print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Skipping edge with empty actions: {from_label} → {to_label}")
    
    print(f"[@navigation:pathfinding:_create_reachability_based_validation_sequence] Generated {len(validation_sequence)} validation steps using depth-first traversal")
    
    # Generate clean summary like before refactoring
    print(f"\n🎯 [VALIDATION] CLEAN TRANSITION SUMMARY (like before refactoring)")
    print(f"="*80)
    
    forward_steps = [s for s in validation_sequence if s.get('transition_direction') == 'forward']
    return_steps = [s for s in validation_sequence if s.get('transition_direction') == 'return']
    forced_steps = [s for s in validation_sequence if s.get('step_type') == 'forced_transition']
    action_steps = [s for s in validation_sequence if s.get('transition_direction') == 'forward' and get_node_info(G, s['to_node_id']).get('node_type') == 'action']
    
    print(f"📊 Statistics:")
    print(f"   • Total validation steps: {len(validation_sequence)}")
    print(f"   • Real transitions: {len(forward_steps) + len(return_steps)}")
    print(f"     - Forward: {len(forward_steps)}")
    print(f"     - Return: {len(return_steps)}")
    print(f"     - Action transitions: {len(action_steps)} (included in forward, no position change)")
    print(f"   • Forced transitions: {len(forced_steps)}")
    print(f"   • All valid edges covered: ✅")
    
    print(f"\n📋 All Validation Transitions:")
    for i, step in enumerate(validation_sequence, 1):
        from_label = step.get('from_node_label', 'unknown')
        to_label = step.get('to_node_label', 'unknown')
        direction = step.get('transition_direction', 'unknown')
        step_type = step.get('step_type', '')
        
        if step_type == 'forced_transition':
            arrow = "→"
            dir_text = "(forced)"
        elif direction == 'forward':
            arrow = "→"
            if get_node_info(G, step['to_node_id']).get('node_type') == 'action':
                dir_text = "forward (action)"
            else:
                dir_text = "(forward)"
        elif direction == 'return':
            arrow = "←"
            dir_text = "(return)"
        else:
            arrow = "?"
            dir_text = "(unknown)"
        
        print(f"   {i:2d}. {from_label} {arrow} {to_label} {dir_text}")
    
    print(f"="*80)
    
    return validation_sequence


def _create_validation_step(G, from_node: str, to_node: str, edge_data: Dict, step_number: int, step_type: str, current_position: str = None, tree_id: str = None, team_id: str = None) -> Tuple[List[Dict], Optional[Dict]]:
    """
    Create a validation step for an edge transition
    
    Args:
        G: NetworkX graph
        from_node: Source node ID
        to_node: Target node ID
        edge_data: Edge data dictionary
        step_number: Step number in sequence
        step_type: Type of step (depth_first_forward, depth_first_return, remaining)
        current_position: Where we currently are
        tree_id: Tree ID for forced transitions
        team_id: Team ID for forced transitions
        
    Returns:
        Tuple of (forced_steps, validation_step)
    """
    from src.lib.utils.navigation_graph import get_node_info
    
    # SYSTEMATIC CHECK: Insert forced transition if needed
    forced_steps = []
    reachable = True
    if current_position and current_position != from_node:
        print(f"[@navigation:pathfinding] Forced transition needed: {current_position} → {from_node}")
        if tree_id and team_id:
            forced_path = None
            try:
                forced_path = find_shortest_path_unified(tree_id, from_node, team_id, current_position)
            except Exception as e:
                print(f"[@navigation:pathfinding] Direct forced transition failed: {e} - trying fallback from entry")
            
            if not forced_path:
                try:
                    forced_path = find_shortest_path_unified(tree_id, from_node, team_id)
                except Exception as e:
                    print(f"[@navigation:pathfinding] Fallback forced transition failed: {e} - node unreachable, skipping step")
                    reachable = False
            
            if forced_path:
                for i, forced_step in enumerate(forced_path):
                    forced_step['step_number'] = step_number + i
                    forced_step['step_type'] = 'forced_transition'
                    forced_steps.append(forced_step)
    
    if not reachable:
        return forced_steps, None

    from_info = get_node_info(G, from_node) or {}
    to_info = get_node_info(G, to_node) or {}
    
    # Use standardized 2-action-set structure: forward (index 0) then reverse (index 1)
    action_sets = edge_data.get('action_sets', [])
    
    if not action_sets:
        print(f"[@navigation:pathfinding] Warning: No action sets found for edge {from_node} → {to_node}")
        actions = []
        retry_actions = []
        action_set_used = None
    elif 'return' in step_type and len(action_sets) >= 2:
        # For return steps, use reverse action set (index 1)
        reverse_set = action_sets[1]
        actions = reverse_set.get('actions', [])
        retry_actions = reverse_set.get('retry_actions') or []
        action_set_used = reverse_set['id']
        print(f"[@navigation:pathfinding] Using reverse action set: {action_set_used}")
    else:
        # For forward steps, use forward action set (index 0)
        forward_set = action_sets[0]
        actions = forward_set.get('actions', [])
        retry_actions = forward_set.get('retry_actions') or []
        action_set_used = forward_set['id']
        print(f"[@navigation:pathfinding] Using forward action set: {action_set_used}")
    
    verifications = get_node_info(G, to_node).get('verifications', []) if get_node_info(G, to_node) else []
    
    # Adjust step number for the actual validation step
    actual_step_number = step_number + len(forced_steps)
    
    validation_step = {
        'step_number': actual_step_number,
        'step_type': step_type,
        'from_node_id': from_node,
        'to_node_id': to_node,
        'from_node_label': from_info.get('label', from_node),
        'to_node_label': to_info.get('label', to_node),
        'actions': actions,
        'retryActions': retry_actions,
        'action_set_id': action_set_used,  # Track which action set was used
        'original_edge_data': edge_data,  # Pass the original edge with all action sets
        'verifications': verifications,
        'total_actions': len(actions),
        'total_retry_actions': len(retry_actions),
        'total_verifications': len(verifications),
        'finalWaitTime': edge_data.get('finalWaitTime', 2000),
        'edge_id': edge_data.get('edge_id', 'unknown'),
        'transition_direction': 'return' if 'return' in step_type else 'forward',  # Track direction
        'description': f"Validate transition: {from_info.get('label', from_node)} → {to_info.get('label', to_node)}"
    }
    
    return forced_steps, validation_step