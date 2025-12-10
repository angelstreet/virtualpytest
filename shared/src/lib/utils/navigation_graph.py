"""
NetworkX Graph Management for Navigation Trees
Handles building and managing NetworkX graphs from navigation data
"""

import networkx as nx
from typing import Dict, List, Optional

def create_networkx_graph(nodes: List[Dict], edges: List[Dict]) -> nx.DiGraph:
    """
    Create NetworkX directed graph from navigation nodes and edges
    
    Args:
        nodes: List of navigation nodes from database
        edges: List of navigation edges from database
        
    Returns:
        NetworkX directed graph
    """
    print(f"[@navigation:graph:create_networkx_graph] Creating graph with {len(nodes)} nodes and {len(edges)} edges")
    
    # Create directed graph for navigation flow
    G = nx.DiGraph()
    
    # Add nodes with their data - NEW NORMALIZED FORMAT ONLY
    for node in nodes:
        node_id = node.get('node_id')
        if not node_id:
            print(f"[@navigation:graph:create_networkx_graph] Warning: Node without node_id found, skipping")
            continue
            
        # NEW NORMALIZED FORMAT - direct database fields
        node_data = node.get('data', {})
        label = node.get('label', '')
        
        # Entry point detection - node_type='entry' OR label='ENTRY'
        node_type_value = node.get('node_type', 'screen')
        is_entry_point = (
            node_type_value == 'entry' or
            label.upper() == 'ENTRY'
        )
        
        print(f"[@navigation:graph:create_networkx_graph] Adding node: {label} ({node_id})")
        
        verifications = node.get('verifications', [])
        
        G.add_node(node_id, **{
            'label': label,
            'node_type': node_type_value,  # Use top-level node_type column
            'description': node_data.get('description', ''),
            'screenshot_url': node_data.get('screenshot', ''),
            'is_entry_point': is_entry_point,
            'is_exit_point': node_data.get('is_exit_point', False),
            'has_children': node_data.get('has_children', False),
            'child_tree_id': node_data.get('child_tree_id'),
            'metadata': node_data,
            'verifications': verifications,  # Embedded verifications
            'verification_pass_condition': node.get('verification_pass_condition') or node_data.get('verification_pass_condition', 'all')  # ✅ FIX: Add as top-level attribute
        })
    
    print(f"[@navigation:graph:create_networkx_graph] Added {len(G.nodes)} nodes to graph")
    
    # Add edges with actions as attributes
    edges_added = 0
    edges_skipped = 0
    
    print(f"[@navigation:graph:create_networkx_graph] ===== ADDING EDGES WITH ACTIONS =====")
    
    for edge in edges:
        # NEW NORMALIZED FORMAT ONLY
        source_id = edge.get('source_node_id')
        target_id = edge.get('target_node_id')
        
        if not source_id or not target_id:
            print(f"[@navigation:graph:create_networkx_graph] Warning: Edge without source/target found, skipping. Available keys: {list(edge.keys())}")
            edges_skipped += 1
            continue
            
        # Check if nodes exist
        if source_id not in G.nodes or target_id not in G.nodes:
            print(f"[@navigation:graph:create_networkx_graph] Warning: Edge references non-existent nodes {source_id} -> {target_id}, skipping")
            edges_skipped += 1
            continue
        
        # NEW ONLY: action_sets structure
        edge_data = edge.get('data', {})
        action_sets = edge.get('action_sets')
        if action_sets is None:
            raise ValueError(f"Edge {edge.get('edge_id')} missing action_sets")
        
        default_action_set_id = edge.get('default_action_set_id')
        if not default_action_set_id:
            raise ValueError(f"Edge {edge.get('edge_id')} missing default_action_set_id")
        
        # Handle empty action_sets for initial setup
        if not action_sets:
            # Empty navigation config - create placeholder edge for initial setup
            actions_list = []
            retry_actions_list = []
            failure_actions_list = []
            default_set = None
            print(f"[@navigation:graph:create_networkx_graph] Adding EMPTY edge {source_id} → {target_id}: Initial setup (no actions yet)")
        else:
            # Find default action set
            default_set = next(
                (s for s in action_sets if s['id'] == default_action_set_id),
                None
            )
            
            if not default_set:
                raise ValueError(f"Edge {edge.get('edge_id')} default action set '{default_action_set_id}' not found")
            
            # Extract actions from default set for pathfinding
            actions_list = default_set.get('actions', [])
            retry_actions_list = default_set.get('retry_actions') or []
            failure_actions_list = default_set.get('failure_actions') or []
            
            # Check if this edge has any valid actions (forward or reverse)
            has_forward_actions = bool(actions_list)
            has_reverse_actions = False
            
            # Check if reverse action set (index 1) has actions
            if len(action_sets) >= 2:
                reverse_set = action_sets[1]
                reverse_actions = reverse_set.get('actions', [])
                has_reverse_actions = bool(reverse_actions)
            
            # Check if this is a conditional edge (shares action_set_id with siblings from same source)
            # Conditional edges might not have actions populated but should be in graph for pathfinding
            is_conditional_edge = False
            if default_action_set_id:
                # Check if other edges from same source share this action_set_id
                for other_edge in edges:
                    other_source = other_edge.get('source_node_id')
                    other_target = other_edge.get('target_node_id')
                    if other_source == source_id and other_target != target_id:
                        other_action_sets = other_edge.get('action_sets', [])
                        if other_action_sets:
                            other_default_id = other_edge.get('default_action_set_id')
                            if other_default_id == default_action_set_id:
                                is_conditional_edge = True
                                break
            
            # Skip edges only if no actions AND not conditional
            # Conditional edges need graph representation even without actions (siblings have the actions)
            if not has_forward_actions and not has_reverse_actions and not is_conditional_edge:
                print(f"[@navigation:graph:create_networkx_graph] SKIPPING edge {source_id} → {target_id}: No actions defined")
                edges_skipped += 1
                continue
            elif not has_forward_actions and not has_reverse_actions and is_conditional_edge:
                print(f"[@navigation:graph:create_networkx_graph] Including CONDITIONAL edge {source_id} → {target_id}: Shares action_set_id with siblings")
        
        # Get node labels for logging
        source_node_data = G.nodes[source_id]
        target_node_data = G.nodes[target_id]
        source_label = source_node_data.get('label', source_id)
        target_label = target_node_data.get('label', target_id)
        
        # Log detailed edge information with action_sets
        print(f"[@navigation:graph:create_networkx_graph] Adding Edge: {source_label} → {target_label}")
        print(f"[@navigation:graph:create_networkx_graph]   Source ID: {source_id}")
        print(f"[@navigation:graph:create_networkx_graph]   Target ID: {target_id}")
        print(f"[@navigation:graph:create_networkx_graph]   Action Sets ({len(action_sets)}):")
        
        for i, action_set in enumerate(action_sets):
            set_id = action_set.get('id', 'unknown')
            set_label = action_set.get('id', 'Unknown')
            is_default = set_id == default_action_set_id
            default_marker = ' [DEFAULT]' if is_default else ''
            print(f"[@navigation:graph:create_networkx_graph]     {i+1}. {set_label} ({set_id}){default_marker}")
            
            set_actions = action_set.get('actions', [])
            for j, action in enumerate(set_actions):
                command = action.get('command', 'unknown')
                params = action.get('params', {})
                params_str = ', '.join([f"{k}={v}" for k, v in params.items()]) if params else 'no params'
                print(f"[@navigation:graph:create_networkx_graph]       - {j+1}. {command}({params_str})")
        
        print(f"[@navigation:graph:create_networkx_graph]   Default Actions ({len(actions_list)}): {[a.get('command') for a in actions_list]}")
        print(f"[@navigation:graph:create_networkx_graph]   Default Retry Actions ({len(retry_actions_list)}): {[a.get('command') for a in retry_actions_list]}")
        print(f"[@navigation:graph:create_networkx_graph]   Default Failure Actions ({len(failure_actions_list)}): {[a.get('command') for a in failure_actions_list]}")
        
        # Create forward edge if it has actions OR if it's a conditional edge
        # Conditional edges need graph representation for pathfinding (multiple destinations, same action)
        if has_forward_actions or is_conditional_edge:
            # ✅ CONDITIONAL EDGE: Populate actions from sibling if this edge has none
            actual_action_sets = action_sets if action_sets else []
            if is_conditional_edge and not has_forward_actions:
                print(f"[@navigation:graph:create_networkx_graph] Conditional edge detected - looking up sibling actions")
                
                # Find sibling edge with same action_set_id that HAS actions
                for other_edge in edges:
                    other_source = other_edge.get('source_node_id')
                    other_target = other_edge.get('target_node_id')
                    
                    if other_source == source_id and other_target != target_id:
                        other_action_sets = other_edge.get('action_sets', [])
                        if other_action_sets and len(other_action_sets) > 0:
                            other_default_id = other_edge.get('default_action_set_id')
                            if other_default_id == default_action_set_id:
                                # Found sibling with actions - use them
                                forward_set = other_action_sets[0]
                                if forward_set.get('actions'):
                                    actual_action_sets = [forward_set]
                                    actions_list = forward_set.get('actions', [])
                                    retry_actions_list = forward_set.get('retry_actions', [])
                                    failure_actions_list = forward_set.get('failure_actions', [])
                                    
                                    # Get sibling label for logging
                                    other_target_data = G.nodes.get(other_target, {})
                                    other_target_label = other_target_data.get('label', other_target)
                                    print(f"[@navigation:graph:create_networkx_graph] ✅ Using actions from sibling: {source_label} → {other_target_label}")
                                    print(f"[@navigation:graph:create_networkx_graph] Sibling has {len(actions_list)} main actions")
                                    break
                
                if not actual_action_sets:
                    print(f"[@navigation:graph:create_networkx_graph] ⚠️ No sibling actions found - conditional edge may be incomplete")
            
            if is_conditional_edge and not has_forward_actions:
                print(f"[@navigation:graph:create_networkx_graph] Creating FORWARD edge (conditional): {source_label} → {target_label} [action_set_id: {default_action_set_id}]")
            else:
                print(f"[@navigation:graph:create_networkx_graph] Creating FORWARD edge: {source_label} → {target_label}")
            
            G.add_edge(source_id, target_id, **{
                'edge_id': edge.get('edge_id'),
                'action_sets': actual_action_sets,  # Use populated action_sets (from sibling if conditional)
                'default_action_set_id': default_action_set_id,
                'edge_type': edge.get('edge_type', 'navigation'),
                'final_wait_time': edge.get('final_wait_time', 2000),
                'weight': 1,
                'is_forward_edge': True,
                'is_conditional': is_conditional_edge  # Mark conditional edges for executor
            })
            edges_added += 1
        else:
            print(f"[@navigation:graph:create_networkx_graph] SKIPPING forward edge {source_label} → {target_label}: No forward actions and not conditional")
        
        # Create reverse edge if action set index 1 has valid actions
        if has_reverse_actions:
            reverse_set = action_sets[1]
            reverse_actions = reverse_set.get('actions', [])
            reverse_edge_id = f"{edge.get('edge_id')}_reverse"
            print(f"[@navigation:graph:create_networkx_graph] Creating REVERSE edge: {target_label} → {source_label}")
            print(f"[@navigation:graph:create_networkx_graph]   Reverse Actions ({len(reverse_actions)}): {[a.get('command') for a in reverse_actions]}")
            
            G.add_edge(target_id, source_id, **{
                'edge_id': reverse_edge_id,
                'action_sets': [reverse_set],  # Only include the reverse action set
                'default_action_set_id': reverse_set.get('id'),
                'edge_type': edge.get('edge_type', 'navigation'),
                'final_wait_time': edge.get('final_wait_time', 2000),
                'weight': 1,
                'is_reverse_edge': True  # Mark as reverse for debugging
            })
            edges_added += 1
        else:
            print(f"[@navigation:graph:create_networkx_graph] No reverse edge created for {target_label} → {source_label}: No reverse actions")
        
        print(f"[@navigation:graph:create_networkx_graph] -----")
    
    print(f"[@navigation:graph:create_networkx_graph] ===== GRAPH CONSTRUCTION COMPLETE =====")
    print(f"[@navigation:graph:create_networkx_graph] Successfully created graph with {len(G.nodes)} nodes and {len(G.edges)} edges")
    print(f"[@navigation:graph:create_networkx_graph] Edge processing summary: {edges_added} added, {edges_skipped} skipped")
    
    # ✅ PRE-COMPUTE SIBLING RELATIONSHIPS for conditional edges
    print(f"[@navigation:graph:create_networkx_graph] ===== COMPUTING SIBLING RELATIONSHIPS =====")
    sibling_count = 0
    
    for source_id, target_id, edge_data in G.edges(data=True):
        # Only process conditional edges (they need sibling lookup)
        if not edge_data.get('is_conditional'):
            continue
        
        # Get this edge's action_set_id
        action_sets = edge_data.get('action_sets', [])
        if not action_sets:
            continue
        
        action_set_id = action_sets[0].get('id')
        if not action_set_id:
            continue
        
        # Find all sibling edges (same source, same action_set_id, different target)
        sibling_node_ids = []
        for _, other_target, other_edge_data in G.edges(source_id, data=True):
            # Skip self
            if other_target == target_id:
                continue
            
            # Check if shares same action_set_id
            other_action_sets = other_edge_data.get('action_sets', [])
            if other_action_sets:
                other_action_set_id = other_action_sets[0].get('id')
                if other_action_set_id == action_set_id:
                    sibling_node_ids.append(other_target)
        
        # Store sibling list on the edge
        if sibling_node_ids:
            edge_data['sibling_node_ids'] = sibling_node_ids
            sibling_count += 1
            source_label = G.nodes[source_id].get('label', source_id)
            target_label = G.nodes[target_id].get('label', target_id)
            sibling_labels = [G.nodes[sid].get('label', sid) for sid in sibling_node_ids]
            print(f"[@navigation:graph:create_networkx_graph] Edge {source_label} → {target_label} has {len(sibling_node_ids)} sibling(s): {sibling_labels}")
    
    print(f"[@navigation:graph:create_networkx_graph] Pre-computed siblings for {sibling_count} conditional edges")
    
    # Log all possible transitions summary
    print(f"[@navigation:graph:create_networkx_graph] ===== ALL POSSIBLE TRANSITIONS SUMMARY =====")
    for i, (from_node, to_node, edge_data) in enumerate(G.edges(data=True), 1):
        from_info = G.nodes[from_node]
        to_info = G.nodes[to_node]
        from_label = from_info.get('label', from_node)
        to_label = to_info.get('label', to_node)
        actions = edge_data.get('actions', [])
        action_summary = f"{len(actions)} actions" if actions else "no actions"
        primary_action = edge_data.get('go_action', 'none')
        
        print(f"[@navigation:graph:create_networkx_graph] Transition {i:2d}: {from_label} → {to_label} (primary: {primary_action}, {action_summary})")
    
    print(f"[@navigation:graph:create_networkx_graph] ===== END TRANSITIONS SUMMARY =====")
    
    return G

# NEW: Unified graph creation for nested trees

def create_unified_networkx_graph(all_trees_data: List[Dict]) -> nx.DiGraph:
    """
    Create unified NetworkX graph from multiple navigation trees with cross-tree edges
    
    Args:
        all_trees_data: List of tree data dicts containing tree_info, nodes, and edges
        
    Returns:
        Unified NetworkX directed graph with cross-tree connections
    """
    print(f"[@navigation:graph:create_unified_networkx_graph] Creating unified graph with {len(all_trees_data)} trees")
    
    # Create unified directed graph
    unified_graph = nx.DiGraph()
    
    # Track tree relationships for cross-tree edges
    tree_hierarchy = {}
    parent_child_map = {}  # parent_node_id -> child_tree_id
    
    # Phase 1: Add all nodes and edges from individual trees
    total_nodes = 0
    total_edges = 0
    
    for tree_data in all_trees_data:
        tree_id = tree_data.get('tree_id')
        tree_info = tree_data.get('tree_info', {})
        nodes = tree_data.get('nodes', [])
        edges = tree_data.get('edges', [])
        
        if not tree_id:
            print(f"[@navigation:graph:create_unified_networkx_graph] Warning: Tree data missing tree_id, skipping")
            continue
        
        print(f"[@navigation:graph:create_unified_networkx_graph] Processing tree: {tree_info.get('name', tree_id)} ({len(nodes)} nodes, {len(edges)} edges)")
        
        # Store tree hierarchy info
        tree_hierarchy[tree_id] = {
            'tree_id': tree_id,
            'name': tree_info.get('name', ''),
            'parent_tree_id': tree_info.get('parent_tree_id'),
            'parent_node_id': tree_info.get('parent_node_id'),
            'tree_depth': tree_info.get('tree_depth', 0),
            'is_root_tree': tree_info.get('is_root_tree', False)
        }
        
        # Map parent node to child tree
        if tree_info.get('parent_node_id'):
            parent_child_map[tree_info.get('parent_node_id')] = tree_id
        
        # Create individual tree graph
        tree_graph = create_networkx_graph(nodes, edges)
        
        # Add tree context to all nodes
        for node_id, node_data in tree_graph.nodes(data=True):
            node_data['tree_id'] = tree_id
            node_data['tree_name'] = tree_info.get('name', '')
            node_data['tree_depth'] = tree_info.get('tree_depth', 0)
            unified_graph.add_node(node_id, **node_data)
        
        # Add tree context to all edges  
        for from_node, to_node, edge_data in tree_graph.edges(data=True):
            edge_data['tree_id'] = tree_id
            edge_data['tree_name'] = tree_info.get('name', '')
            unified_graph.add_edge(from_node, to_node, **edge_data)
        
        total_nodes += len(tree_graph.nodes)
        total_edges += len(tree_graph.edges)
    
    print(f"[@navigation:graph:create_unified_networkx_graph] Added {total_nodes} nodes and {total_edges} edges from individual trees")
    
    # Phase 1.5: Create sibling shortcuts for web/mobile DOM navigation
    sibling_shortcuts_created = _create_sibling_shortcuts(unified_graph)
    if sibling_shortcuts_created > 0:
        print(f"[@navigation:graph:create_unified_networkx_graph] ✅ Created {sibling_shortcuts_created} sibling shortcut edges for DOM navigation")
    
    # Phase 2: Add cross-tree edges for nested tree navigation
    cross_tree_edges_added = 0
    
    for parent_node_id, child_tree_id in parent_child_map.items():
        # Find entry point of child tree
        child_entry_points = []
        for node_id, node_data in unified_graph.nodes(data=True):
            if (node_data.get('tree_id') == child_tree_id and 
                node_data.get('is_entry_point', False)):
                child_entry_points.append(node_id)
        
        if not child_entry_points:
            # No explicit entry point, use first node of child tree
            for node_id, node_data in unified_graph.nodes(data=True):
                if node_data.get('tree_id') == child_tree_id:
                    child_entry_points.append(node_id)
                    break
        
        if child_entry_points and parent_node_id in unified_graph.nodes:
            child_entry_id = child_entry_points[0]
            parent_tree_id = unified_graph.nodes[parent_node_id].get('tree_id')
            
            print(f"[@navigation:graph:create_unified_networkx_graph] Adding cross-tree edge: {parent_node_id} (tree: {parent_tree_id}) -> {child_entry_id} (tree: {child_tree_id})")
            
            # Add ENTER_SUBTREE edge with action_sets format
            enter_action_set = {
                'id': f'enter-{child_tree_id}',
                'label': 'Enter Subtree',
                'actions': [{'command': 'enter_subtree', 'params': {'tree_id': child_tree_id}}],
                'retry_actions': [],
            'failure_actions': []
            }
            unified_graph.add_edge(parent_node_id, child_entry_id, **{
                'edge_type': 'ENTER_SUBTREE',
                'source_tree_id': parent_tree_id,
                'target_tree_id': child_tree_id,
                'action_sets': [enter_action_set],
                'default_action_set_id': enter_action_set['id'],
                'is_virtual': True,
                'weight': 1,
                'tree_context_change': True
            })
            
            # Add EXIT_SUBTREE edge with action_sets format
            exit_action_set = {
                'id': f'exit-{parent_tree_id}',
                'label': 'Exit Subtree',
                'actions': [{'command': 'exit_subtree', 'params': {'tree_id': parent_tree_id}}],
                'retry_actions': [],
            'failure_actions': []
            }
            unified_graph.add_edge(child_entry_id, parent_node_id, **{
                'edge_type': 'EXIT_SUBTREE', 
                'source_tree_id': child_tree_id,
                'target_tree_id': parent_tree_id,
                'action_sets': [exit_action_set],
                'default_action_set_id': exit_action_set['id'],
                'is_virtual': True,
                'weight': 1,
                'tree_context_change': True
            })
            
            cross_tree_edges_added += 2
    
    print(f"[@navigation:graph:create_unified_networkx_graph] Added {cross_tree_edges_added} cross-tree edges")
    
    # Log unified graph statistics
    print(f"[@navigation:graph:create_unified_networkx_graph] ===== UNIFIED GRAPH COMPLETE =====")
    print(f"[@navigation:graph:create_unified_networkx_graph] Total nodes: {len(unified_graph.nodes)}")
    print(f"[@navigation:graph:create_unified_networkx_graph] Total edges: {len(unified_graph.edges)}")
    print(f"[@navigation:graph:create_unified_networkx_graph] Trees included: {len(tree_hierarchy)}")
    
    # Log tree distribution
    tree_node_counts = {}
    for node_id, node_data in unified_graph.nodes(data=True):
        tree_id = node_data.get('tree_id', 'unknown')
        tree_node_counts[tree_id] = tree_node_counts.get(tree_id, 0) + 1
    
    for tree_id, node_count in tree_node_counts.items():
        tree_name = tree_hierarchy.get(tree_id, {}).get('name', tree_id)
        print(f"[@navigation:graph:create_unified_networkx_graph] Tree '{tree_name}': {node_count} nodes")
    
    return unified_graph

def get_node_info(graph: nx.DiGraph, node_id: str) -> Optional[Dict]:
    """
    Get node information from NetworkX graph
    
    Args:
        graph: NetworkX directed graph
        node_id: Node identifier
        
    Returns:
        Node information dictionary or None if not found
    """
    if node_id not in graph.nodes:
        return None
        
    return dict(graph.nodes[node_id])

def get_edge_action(graph: nx.DiGraph, from_node: str, to_node: str) -> Optional[str]:
    """
    Get navigation action between two nodes
    
    Args:
        graph: NetworkX directed graph
        from_node: Source node ID
        to_node: Target node ID
        
    Returns:
        Primary action command string or None if edge doesn't exist
    """
    if not graph.has_edge(from_node, to_node):
        return None
        
    edge_data = graph.edges[from_node, to_node]
    action_sets = edge_data.get('action_sets', [])
    default_action_set_id = edge_data.get('default_action_set_id')
    
    if action_sets and default_action_set_id:
        default_set = next((s for s in action_sets if s['id'] == default_action_set_id), None)
        if default_set:
            actions = default_set.get('actions', [])
            if actions:
                return actions[0].get('command')
    
    return None

def get_entry_points(graph: nx.DiGraph) -> List[str]:
    """
    Get all entry point nodes from the graph
    
    Args:
        graph: NetworkX directed graph
        
    Returns:
        List of entry point node IDs
    """
    entry_points = []
    for node_id, node_data in graph.nodes(data=True):
        if node_data.get('is_entry_point', False):
            entry_points.append(node_id)
    
    return entry_points

def get_exit_points(graph: nx.DiGraph) -> List[str]:
    """
    Get all exit point nodes from the graph
    
    Args:
        graph: NetworkX directed graph
        
    Returns:
        List of exit point node IDs
    """
    exit_points = []
    for node_id, node_data in graph.nodes(data=True):
        if node_data.get('is_exit_point', False):
            exit_points.append(node_id)
    
    return exit_points

def validate_graph(graph: nx.DiGraph) -> Dict:
    """
    Validate the navigation graph for potential issues
    
    Args:
        graph: NetworkX directed graph
        
    Returns:
        Validation results dictionary
    """
    issues = []
    warnings = []
    
    # Check for isolated nodes
    isolated = list(nx.isolates(graph))
    if isolated:
        warnings.append(f"Found {len(isolated)} isolated nodes: {isolated}")
    
    # Check for entry points
    entry_points = get_entry_points(graph)
    if not entry_points:
        issues.append("No entry point nodes found")
    elif len(entry_points) > 1:
        warnings.append(f"Multiple entry points found: {entry_points}")
    
    # Check for unreachable nodes
    if entry_points:
        reachable = nx.descendants(graph, entry_points[0])
        reachable.add(entry_points[0])
        unreachable = set(graph.nodes) - reachable
        if unreachable:
            warnings.append(f"Found {len(unreachable)} unreachable nodes: {list(unreachable)}")
    
    # Check for missing action sets
    missing_action_sets = []
    for from_node, to_node, edge_data in graph.edges(data=True):
        action_sets = edge_data.get('action_sets', [])
        if not action_sets:
            missing_action_sets.append(f"{from_node} -> {to_node}")
    
    if missing_action_sets:
        warnings.append(f"Found {len(missing_action_sets)} edges without action_sets")
    
    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'stats': {
            'nodes': len(graph.nodes),
            'edges': len(graph.edges),
            'entry_points': len(entry_points),
            'exit_points': len(get_exit_points(graph)),
            'isolated_nodes': len(isolated)
        }
    }


def _create_sibling_shortcuts(G: nx.DiGraph) -> int:
    """
    Create shortcut edges between sibling nodes (nodes sharing same parent)
    ONLY for edges marked with enable_sibling_shortcuts=True
    
    For web/mobile DOM navigation: Nav bars/tab bars are shared across sibling screens,
    so siblings are directly reachable using the same actions as parent → target.
    
    Example:
        home → home_tvguide [enable_sibling_shortcuts: True]
        home → home_replay [enable_sibling_shortcuts: True]
        home → home_saved [enable_sibling_shortcuts: True]
        
    Creates shortcuts:
        home_tvguide ↔ home_replay (using same action as home → home_replay)
        home_tvguide ↔ home_saved (using same action as home → home_saved)
        home_replay ↔ home_saved (using same action as home → home_saved)
    
    Args:
        G: NetworkX directed graph
        
    Returns:
        Number of sibling shortcut edges created
    """
    shortcuts_created = 0
    
    # Find all parent→child edges that opt-in to sibling sharing
    parent_children_map = {}  # parent_id → [(child_id, edge_data), ...]
    
    for from_node, to_node, edge_data in G.edges(data=True):
        # Check if this edge enables sibling shortcuts
        # Look in both edge_data directly and in action_sets
        enable_shortcuts = edge_data.get('enable_sibling_shortcuts', False)
        
        # Also check in action_sets if present (for backward compatibility)
        if not enable_shortcuts:
            action_sets = edge_data.get('action_sets', [])
            if action_sets and len(action_sets) > 0:
                # Check first action set
                enable_shortcuts = action_sets[0].get('enable_sibling_shortcuts', False)
        
        if enable_shortcuts:
            if from_node not in parent_children_map:
                parent_children_map[from_node] = []
            parent_children_map[from_node].append((to_node, edge_data))
    
    # Create shortcuts between siblings
    for parent_node, children in parent_children_map.items():
        if len(children) < 2:
            continue  # Need at least 2 children to create shortcuts
        
        parent_info = get_node_info(G, parent_node) or {}
        parent_label = parent_info.get('label', parent_node)
        
        print(f"[@navigation:graph:sibling_shortcuts] Parent '{parent_label}' has {len(children)} siblings with shortcuts enabled")
        
        # Create bidirectional shortcuts between all sibling pairs
        for i, (sibling_a, _) in enumerate(children):
            for sibling_b, edge_data_b in children[i+1:]:
                # Skip if shortcut already exists
                if G.has_edge(sibling_a, sibling_b):
                    continue
                
                sibling_a_info = get_node_info(G, sibling_a) or {}
                sibling_b_info = get_node_info(G, sibling_b) or {}
                sibling_a_label = sibling_a_info.get('label', sibling_a)
                sibling_b_label = sibling_b_info.get('label', sibling_b)
                
                # Create shortcut: sibling_a → sibling_b (reusing parent → sibling_b actions)
                shortcut_edge_data = {
                    **edge_data_b,  # Copy all edge properties from parent → sibling_b
                    'edge_id': f'sibling_shortcut_{sibling_a}_{sibling_b}',
                    'edge_type': 'SIBLING_SHORTCUT',
                    'is_sibling_shortcut': True,
                    'original_parent': parent_node,
                    'shortcut_info': f"Shortcut from {sibling_a_label} to {sibling_b_label} via shared parent {parent_label}"
                }
                
                G.add_edge(sibling_a, sibling_b, **shortcut_edge_data)
                print(f"[@navigation:graph:sibling_shortcuts]   ✅ {sibling_a_label} → {sibling_b_label}")
                shortcuts_created += 1
                
                # Create reverse shortcut: sibling_b → sibling_a
                # Find parent → sibling_a edge data
                if G.has_edge(parent_node, sibling_a):
                    edge_data_a = G.edges[parent_node, sibling_a]
                    
                    reverse_shortcut_edge_data = {
                        **edge_data_a,  # Copy all edge properties from parent → sibling_a
                        'edge_id': f'sibling_shortcut_{sibling_b}_{sibling_a}',
                        'edge_type': 'SIBLING_SHORTCUT',
                        'is_sibling_shortcut': True,
                        'original_parent': parent_node,
                        'shortcut_info': f"Shortcut from {sibling_b_label} to {sibling_a_label} via shared parent {parent_label}"
                    }
                    
                    G.add_edge(sibling_b, sibling_a, **reverse_shortcut_edge_data)
                    print(f"[@navigation:graph:sibling_shortcuts]   ✅ {sibling_b_label} → {sibling_a_label}")
                    shortcuts_created += 1
    
    return shortcuts_created 