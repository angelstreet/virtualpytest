from typing import Dict, Any, List
import time
from backend_host.src.services.ai_exploration.node_generator import NodeGenerator
from shared.src.lib.database.navigation_trees_db import (
    get_node_by_id,
    get_edge_by_id,
    delete_node,
    save_nodes_batch,
    save_edges_batch,
    get_tree_nodes,
    get_tree_edges
)

def finalize_structure(executor) -> Dict[str, Any]:
    """
    Finalize structure: Rename all _temp nodes/edges to permanent
    
    Returns:
        {
            'success': True,
            'nodes_renamed': 5,
            'edges_renamed': 4
        }
    """
    with executor._lock:
        if not executor.current_exploration_id:
            return {'success': False, 'error': 'No active exploration'}
        
        tree_id = executor.exploration_state['tree_id']
        team_id = executor.exploration_state['team_id']
        
        print(f"[@ExplorationExecutor:finalize_structure] Renaming _temp nodes/edges for {executor.current_exploration_id}")
        
        # Get all nodes and edges from tree
        nodes_result = get_tree_nodes(tree_id, team_id)
        edges_result = get_tree_edges(tree_id, team_id)
        
        if not nodes_result.get('success') or not edges_result.get('success'):
            return {'success': False, 'error': 'Failed to get tree data'}
        
        nodes = nodes_result.get('nodes', [])
        edges = edges_result.get('edges', [])
        
        nodes_renamed = 0
        edges_renamed = 0
        
        # Rename nodes: remove _temp suffix
        nodes_to_save = []
        for node in nodes:
            node_id = node.get('node_id', '')
            if node_id.endswith('_temp'):
                new_node_id = node_id.replace('_temp', '')
                node['node_id'] = new_node_id
                nodes_to_save.append(node)
                print(f"  ✅ Renamed node: {node_id} → {new_node_id}")
        
        if nodes_to_save:
            result = save_nodes_batch(tree_id, nodes_to_save, team_id)
            if result.get('success'):
                nodes_renamed = len(nodes_to_save)
            else:
                print(f"  ❌ Failed to save renamed nodes: {result.get('error')}")
        
        # Rename edges: remove _temp suffix from edge_id, source, target
        edges_to_save = []
        for edge in edges:
            edge_id = edge.get('edge_id', '')
            source = edge.get('source', '')
            target = edge.get('target', '')
            
            if '_temp' in edge_id or '_temp' in source or '_temp' in target:
                new_edge_id = edge_id.replace('_temp', '')
                new_source = source.replace('_temp', '')
                new_target = target.replace('_temp', '')
                
                edge['edge_id'] = new_edge_id
                edge['source'] = new_source
                edge['target'] = new_target
                edges_to_save.append(edge)
                print(f"  ✅ Renamed edge: {edge_id} → {new_edge_id}")
                
        if edges_to_save:
            result = save_edges_batch(tree_id, edges_to_save, team_id)
            if result.get('success'):
                edges_renamed = len(edges_to_save)
            else:
                print(f"  ❌ Failed to save renamed edges: {result.get('error')}")
        
        # Update state
        executor.exploration_state['status'] = 'finalized'
        executor.exploration_state['current_step'] = f'Finalized: {nodes_renamed} nodes and {edges_renamed} edges renamed'
        
        # DELAY: Wait 2s to let view refresh/propagate before frontend fetch
        time.sleep(2)
        
        return {
            'success': True,
            'nodes_renamed': nodes_renamed,
            'edges_renamed': edges_renamed,
            'message': 'Structure finalized successfully'
        }

def approve_generation(executor, tree_id: str, approved_nodes: list, approved_edges: list, team_id: str) -> Dict[str, Any]:
    """
    Approve generation - rename all _temp nodes/edges
    
    Returns:
        {
            'success': True,
            'nodes_created': 2,
            'edges_created': 1
        }
    """
    print(f"[@ExplorationExecutor:approve_generation] Approving {len(approved_nodes)} nodes, {len(approved_edges)} edges")
    
    node_generator = NodeGenerator(tree_id, team_id)
    nodes_created = 0
    edges_created = 0
    
    # Rename nodes
    nodes_to_save = []
    for node_id in approved_nodes:
        node_result = get_node_by_id(tree_id, node_id, team_id)
        if node_result['success']:
            node_data = node_result['node']
            renamed_data = node_generator.rename_node(node_data)
            
            delete_node(tree_id, node_id, team_id)
            nodes_to_save.append(renamed_data)
            print(f"  ✅ Renamed: {node_id} → {renamed_data['node_id']}")

    if nodes_to_save:
        save_result = save_nodes_batch(tree_id, nodes_to_save, team_id)
        if save_result['success']:
            nodes_created = len(nodes_to_save)
    
    # Rename edges
    edges_to_save = []
    for edge_id in approved_edges:
        edge_result = get_edge_by_id(tree_id, edge_id, team_id)
        if edge_result['success']:
            edge_data = edge_result['edge']
            renamed_data = node_generator.rename_edge(edge_data)
            
            edges_to_save.append(renamed_data)
            print(f"  ✅ Renamed: {edge_id} → {renamed_data['edge_id']}")

    if edges_to_save:
        save_result = save_edges_batch(tree_id, edges_to_save, team_id)
        if save_result['success']:
            edges_created = len(edges_to_save)
    
    # Clean up state
    with executor._lock:
        executor.current_exploration_id = None
        executor.exploration_engine = None
        executor.exploration_state['status'] = 'idle'
    
    print(f"[@ExplorationExecutor:approve_generation] ✅ Complete: {nodes_created} nodes, {edges_created} edges")
    
    # DELAY: Wait 2s to let view refresh/propagate before frontend fetch
    time.sleep(2)
    
    return {
        'success': True,
        'nodes_created': nodes_created,
        'edges_created': edges_created,
        'message': f'Successfully created {nodes_created} nodes and {edges_created} edges'
    }

def cancel_exploration(executor, tree_id: str, team_id: str) -> Dict[str, Any]:
    """
    Cancel exploration - delete all _temp nodes/edges
    
    Returns:
        {
            'success': True,
            'message': 'Exploration cancelled'
        }
    """
    with executor._lock:
        nodes_to_delete = executor.exploration_state.get('nodes_created', [])
        
        print(f"[@ExplorationExecutor:cancel_exploration] Cancelling exploration")
        
        for node_id in nodes_to_delete:
            delete_node(tree_id, node_id, team_id)
            print(f"  🗑️  Deleted node: {node_id}")
        
        # Reset state
        executor.current_exploration_id = None
        executor.exploration_engine = None
        executor.exploration_state['status'] = 'idle'
        
        print(f"[@ExplorationExecutor:cancel_exploration] ✅ Cancelled")
        
        return {
            'success': True,
            'message': 'Exploration cancelled, temporary nodes deleted'
        }

