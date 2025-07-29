"""
Navigation Trees Database Operations - Normalized Architecture

This module provides functions for managing navigation trees using the new normalized structure:
- navigation_trees: Tree metadata containers
- navigation_nodes: Individual nodes with embedded verifications
- navigation_edges: Edges with embedded actions

No more monolithic JSONB - clean, scalable, individual record operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from shared.lib.utils.supabase_utils import get_supabase_client
from shared.lib.utils.app_utils import DEFAULT_TEAM_ID

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()

# ============================================================================
# TREE METADATA OPERATIONS
# ============================================================================

def get_all_trees(team_id: str) -> List[Dict]:
    """Retrieve all navigation trees metadata for a team."""
    supabase = get_supabase()
    result = supabase.table('navigation_trees').select(
        'id, name, userinterface_id, team_id, root_node_id, description, created_at, updated_at, '
        'userinterfaces(id, name, models)'
    ).eq('team_id', team_id).order('created_at', desc=False).execute()
    
    trees = []
    for tree in result.data:
        trees.append({
            'id': tree['id'],
            'name': tree['name'],
            'userinterface_id': tree['userinterface_id'],
            'userinterface': tree['userinterfaces'],
            'team_id': tree['team_id'],
            'root_node_id': tree['root_node_id'],
            'description': tree['description'] or '',
            'created_at': tree['created_at'],
            'updated_at': tree['updated_at']
        })
    
    return trees

def get_root_tree_for_interface(userinterface_id: str, team_id: str) -> Optional[Dict]:
    """Get the root navigation tree for a specific user interface."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select(
            'id, name, userinterface_id, team_id, root_node_id, description, created_at, updated_at'
        ).eq('userinterface_id', userinterface_id).eq('team_id', team_id).limit(1).execute()
        
        if result.data:
            tree = result.data[0]
            return {
                'id': tree['id'],
                'name': tree['name'],
                'userinterface_id': tree['userinterface_id'],
                'team_id': tree['team_id'],
                'root_node_id': tree['root_node_id'],
                'description': tree['description'],
                'created_at': tree['created_at'],
                'updated_at': tree['updated_at']
            }
        
        return None
        
    except Exception as e:
        print(f"[@db:navigation_trees:get_root_tree_for_interface] Error: {str(e)}")
        return None

def get_tree_metadata(tree_id: str, team_id: str) -> Dict:
    """Get tree basic metadata information."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select('*').eq('id', tree_id).eq('team_id', team_id).single().execute()
        
        if result.data:
            return {'success': True, 'tree': result.data}
        else:
            return {'success': False, 'error': 'Tree not found'}
    except Exception as e:
        print(f"[@db:navigation_trees:get_tree_metadata] Error: {e}")
        return {'success': False, 'error': str(e)}

def save_tree_metadata(tree_data: Dict, team_id: str) -> Dict:
    """Save tree metadata (create or update)."""
    try:
        supabase = get_supabase()
        tree_data['team_id'] = team_id
        tree_data['updated_at'] = datetime.now().isoformat()
        
        if 'id' in tree_data and tree_data['id']:
            # Update existing tree
            result = supabase.table('navigation_trees').update(tree_data).eq('id', tree_data['id']).eq('team_id', team_id).execute()
            print(f"[@db:navigation_trees:save_tree_metadata] Updated tree: {tree_data['id']}")
        else:
            # Create new tree
            tree_data['id'] = str(uuid4())
            tree_data['created_at'] = datetime.now().isoformat()
            result = supabase.table('navigation_trees').insert(tree_data).execute()
            print(f"[@db:navigation_trees:save_tree_metadata] Created new tree: {tree_data['id']}")
        
        return {'success': True, 'tree': result.data[0]}
    except Exception as e:
        print(f"[@db:navigation_trees:save_tree_metadata] Error: {e}")
        return {'success': False, 'error': str(e)}

def delete_tree(tree_id: str, team_id: str) -> Dict:
    """Delete a tree and all its nodes/edges (CASCADE)."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').delete().eq('id', tree_id).eq('team_id', team_id).execute()
        print(f"[@db:navigation_trees:delete_tree] Deleted tree: {tree_id}")
        return {'success': True}
    except Exception as e:
        print(f"[@db:navigation_trees:delete_tree] Error: {e}")
        return {'success': False, 'error': str(e)}

# ============================================================================
# NODE OPERATIONS
# ============================================================================

def get_tree_nodes(tree_id: str, team_id: str, page: int = 0, limit: int = 100) -> Dict:
    """Get nodes for a tree with pagination."""
    try:
        supabase = get_supabase()
        offset = page * limit
        
        result = supabase.table('navigation_nodes').select('*')\
            .eq('tree_id', tree_id)\
            .eq('team_id', team_id)\
            .range(offset, offset + limit - 1)\
            .order('created_at')\
            .execute()
        
        print(f"[@db:navigation_trees:get_tree_nodes] Found {len(result.data)} nodes for tree {tree_id}")
        return {'success': True, 'nodes': result.data}
    except Exception as e:
        print(f"[@db:navigation_trees:get_tree_nodes] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_node_by_id(tree_id: str, node_id: str, team_id: str) -> Dict:
    """Get a single node by its node_id."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_nodes').select('*')\
            .eq('tree_id', tree_id)\
            .eq('node_id', node_id)\
            .eq('team_id', team_id)\
            .single()\
            .execute()
        
        if result.data:
            return {'success': True, 'node': result.data}
        else:
            return {'success': False, 'error': 'Node not found'}
    except Exception as e:
        print(f"[@db:navigation_trees:get_node_by_id] Error: {e}")
        return {'success': False, 'error': str(e)}

def save_node(tree_id: str, node_data: Dict, team_id: str) -> Dict:
    """Save a single node (create or update)."""
    try:
        supabase = get_supabase()
        node_data['tree_id'] = tree_id
        node_data['team_id'] = team_id
        node_data['updated_at'] = datetime.now().isoformat()
        
        # Check if node exists
        existing = supabase.table('navigation_nodes').select('id')\
            .eq('tree_id', tree_id)\
            .eq('node_id', node_data['node_id'])\
            .eq('team_id', team_id)\
            .execute()
        
        if existing.data:
            # Update existing node
            result = supabase.table('navigation_nodes').update(node_data)\
                .eq('tree_id', tree_id)\
                .eq('node_id', node_data['node_id'])\
                .eq('team_id', team_id)\
            .execute()
            print(f"[@db:navigation_trees:save_node] Updated node: {node_data['node_id']}")
        else:
            # Insert new node
            node_data['created_at'] = datetime.now().isoformat()
            result = supabase.table('navigation_nodes').insert(node_data).execute()
            print(f"[@db:navigation_trees:save_node] Created new node: {node_data['node_id']}")
        
        return {'success': True, 'node': result.data[0]}
    except Exception as e:
        print(f"[@db:navigation_trees:save_node] Error: {e}")
        return {'success': False, 'error': str(e)}

def delete_node(tree_id: str, node_id: str, team_id: str) -> Dict:
    """Delete a node and all connected edges."""
    try:
        supabase = get_supabase()
        
        # Delete connected edges first (foreign key constraints will handle this, but let's be explicit)
        supabase.table('navigation_edges').delete()\
            .eq('tree_id', tree_id)\
            .eq('team_id', team_id)\
            .or_(f'source_node_id.eq.{node_id},target_node_id.eq.{node_id}')\
            .execute()
        
        # Delete the node
        result = supabase.table('navigation_nodes').delete()\
            .eq('tree_id', tree_id)\
            .eq('node_id', node_id)\
            .eq('team_id', team_id)\
            .execute()
        
        print(f"[@db:navigation_trees:delete_node] Deleted node: {node_id}")
        return {'success': True}
    except Exception as e:
        print(f"[@db:navigation_trees:delete_node] Error: {e}")
        return {'success': False, 'error': str(e)}

# ============================================================================
# EDGE OPERATIONS
# ============================================================================

def get_tree_edges(tree_id: str, team_id: str, node_ids: List[str] = None) -> Dict:
    """Get edges for a tree, optionally filtered by node IDs."""
    try:
        supabase = get_supabase()
        query = supabase.table('navigation_edges').select('*')\
            .eq('tree_id', tree_id)\
            .eq('team_id', team_id)
        
        if node_ids:
            # Get edges that connect to any of the specified nodes
            node_filter = ','.join(node_ids)
            query = query.or_(f'source_node_id.in.({node_filter}),target_node_id.in.({node_filter})')
        
        result = query.order('created_at').execute()
        
        print(f"[@db:navigation_trees:get_tree_edges] Found {len(result.data)} edges for tree {tree_id}")
        return {'success': True, 'edges': result.data}
    except Exception as e:
        print(f"[@db:navigation_trees:get_tree_edges] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_edge_by_id(tree_id: str, edge_id: str, team_id: str) -> Dict:
    """Get a single edge by its edge_id."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_edges').select('*')\
            .eq('tree_id', tree_id)\
            .eq('edge_id', edge_id)\
            .eq('team_id', team_id)\
            .single()\
            .execute()
        
        if result.data:
            return {'success': True, 'edge': result.data}
        else:
            return {'success': False, 'error': 'Edge not found'}
    except Exception as e:
        print(f"[@db:navigation_trees:get_edge_by_id] Error: {e}")
        return {'success': False, 'error': str(e)}

def save_edge(tree_id: str, edge_data: Dict, team_id: str) -> Dict:
    """Save a single edge (create or update)."""
    try:
        supabase = get_supabase()
        edge_data['tree_id'] = tree_id
        edge_data['team_id'] = team_id
        edge_data['updated_at'] = datetime.now().isoformat()
        
        # Check if edge exists
        existing = supabase.table('navigation_edges').select('id')\
            .eq('tree_id', tree_id)\
            .eq('edge_id', edge_data['edge_id'])\
            .eq('team_id', team_id)\
            .execute()
        
        if existing.data:
            # Update existing edge
            result = supabase.table('navigation_edges').update(edge_data)\
                .eq('tree_id', tree_id)\
                .eq('edge_id', edge_data['edge_id'])\
                .eq('team_id', team_id)\
                .execute()
            print(f"[@db:navigation_trees:save_edge] Updated edge: {edge_data['edge_id']}")
        else:
            # Insert new edge
            edge_data['created_at'] = datetime.now().isoformat()
            result = supabase.table('navigation_edges').insert(edge_data).execute()
            print(f"[@db:navigation_trees:save_edge] Created new edge: {edge_data['edge_id']}")
        
        return {'success': True, 'edge': result.data[0]}
    except Exception as e:
        print(f"[@db:navigation_trees:save_edge] Error: {e}")
        return {'success': False, 'error': str(e)}

def delete_edge(tree_id: str, edge_id: str, team_id: str) -> Dict:
    """Delete an edge."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_edges').delete()\
            .eq('tree_id', tree_id)\
            .eq('edge_id', edge_id)\
            .eq('team_id', team_id)\
            .execute()
        
        print(f"[@db:navigation_trees:delete_edge] Deleted edge: {edge_id}")
        return {'success': True}
    except Exception as e:
        print(f"[@db:navigation_trees:delete_edge] Error: {e}")
        return {'success': False, 'error': str(e)}

# ============================================================================
# BATCH OPERATIONS
# ============================================================================

def save_tree_data(tree_id: str, nodes: List[Dict], edges: List[Dict], team_id: str) -> Dict:
    """Save complete tree data (nodes + edges) in batch."""
    try:
        saved_nodes = []
        saved_edges = []
        
        # Save all nodes first
        for node_data in nodes:
            result = save_node(tree_id, node_data, team_id)
            if result['success']:
                saved_nodes.append(result['node'])
            else:
                return {'success': False, 'error': f"Failed to save node {node_data.get('node_id')}: {result['error']}"}
        
        # Save all edges
        for edge_data in edges:
            result = save_edge(tree_id, edge_data, team_id)
            if result['success']:
                saved_edges.append(result['edge'])
            else:
                return {'success': False, 'error': f"Failed to save edge {edge_data.get('edge_id')}: {result['error']}"}
        
        print(f"[@db:navigation_trees:save_tree_data] Saved {len(saved_nodes)} nodes and {len(saved_edges)} edges for tree {tree_id}")
        return {
            'success': True,
            'nodes': saved_nodes,
            'edges': saved_edges
        }
    except Exception as e:
        print(f"[@db:navigation_trees:save_tree_data] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_full_tree(tree_id: str, team_id: str) -> Dict:
    """Get complete tree data (metadata + nodes + edges)."""
    try:
        # Get tree metadata
        tree_result = get_tree_metadata(tree_id, team_id)
        if not tree_result['success']:
            return tree_result
        
        # Get all nodes
        nodes_result = get_tree_nodes(tree_id, team_id, page=0, limit=1000)  # Large limit for complete tree
        if not nodes_result['success']:
            return nodes_result
        
        # Get all edges
        edges_result = get_tree_edges(tree_id, team_id)
        if not edges_result['success']:
            return edges_result
        
        return {
            'success': True,
            'tree': tree_result['tree'],
            'nodes': nodes_result['nodes'],
            'edges': edges_result['edges']
        }
    except Exception as e:
        print(f"[@db:navigation_trees:get_full_tree] Error: {e}")
        return {'success': False, 'error': str(e)}

 