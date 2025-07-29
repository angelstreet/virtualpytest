"""
Navigation Trees Database Operations - Normalized Architecture

This module provides functions for managing navigation trees using the new normalized structure:
- navigation_trees: Tree metadata containers with nested tree support
- navigation_nodes: Individual nodes with embedded verifications
- navigation_edges: Edges with embedded actions

Clean, scalable, individual record operations with nested tree functionality.
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
    """Get all navigation trees metadata for a team."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select('*').eq('team_id', team_id).order('created_at').execute()
        
        print(f"[@db:navigation_trees:get_all_trees] Retrieved {len(result.data)} trees")
        return result.data
    except Exception as e:
        print(f"[@db:navigation_trees:get_all_trees] Error: {e}")
        return []

def get_tree_metadata(tree_id: str, team_id: str) -> Dict:
    """Get tree basic information."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select('*').eq('id', tree_id).eq('team_id', team_id).execute()
        
        if result.data:
            print(f"[@db:navigation_trees:get_tree_metadata] Retrieved tree: {tree_id}")
            return {'success': True, 'tree': result.data[0]}
        else:
            print(f"[@db:navigation_trees:get_tree_metadata] Tree not found: {tree_id}")
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
    """Delete a tree (cascade will handle nodes and edges)."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').delete().eq('id', tree_id).eq('team_id', team_id).execute()
        
        print(f"[@db:navigation_trees:delete_tree] Deleted tree: {tree_id}")
        return {'success': True}
    except Exception as e:
        print(f"[@db:navigation_trees:delete_tree] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_root_tree_for_interface(userinterface_id: str, team_id: str) -> Optional[Dict]:
    """Get the root tree for a specific user interface."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select('*')\
            .eq('userinterface_id', userinterface_id)\
            .eq('team_id', team_id)\
            .eq('is_root_tree', True)\
            .order('created_at')\
            .limit(1)\
            .execute()
        
        if result.data:
            print(f"[@db:navigation_trees:get_root_tree_for_interface] Found root tree for interface: {userinterface_id}")
            return result.data[0]
        else:
            print(f"[@db:navigation_trees:get_root_tree_for_interface] No root tree found for interface: {userinterface_id}")
            return None
    except Exception as e:
        print(f"[@db:navigation_trees:get_root_tree_for_interface] Error: {e}")
        return None

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
        
        print(f"[@db:navigation_trees:get_tree_nodes] Retrieved {len(result.data)} nodes for tree: {tree_id}")
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
            .execute()
        
        if result.data:
            print(f"[@db:navigation_trees:get_node_by_id] Retrieved node: {node_id}")
            return {'success': True, 'node': result.data[0]}
        else:
            print(f"[@db:navigation_trees:get_node_by_id] Node not found: {node_id}")
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
        
        # Delete connected edges first
        supabase.table('navigation_edges').delete()\
            .eq('tree_id', tree_id)\
            .eq('team_id', team_id)\
            .or_(f'source_node_id.eq.{node_id},target_node_id.eq.{node_id}')\
            .execute()
        
        # Delete node
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
        query = supabase.table('navigation_edges').select('*').eq('tree_id', tree_id).eq('team_id', team_id)
        
        if node_ids:
            # Get edges that connect to any of the specified nodes
            node_filter = ','.join(node_ids)
            query = query.or_(f'source_node_id.in.({node_filter}),target_node_id.in.({node_filter})')
        
        result = query.order('created_at').execute()
        
        print(f"[@db:navigation_trees:get_tree_edges] Retrieved {len(result.data)} edges for tree: {tree_id}")
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
            .execute()
        
        if result.data:
            print(f"[@db:navigation_trees:get_edge_by_id] Retrieved edge: {edge_id}")
            return {'success': True, 'edge': result.data[0]}
        else:
            print(f"[@db:navigation_trees:get_edge_by_id] Edge not found: {edge_id}")
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
# NESTED TREE OPERATIONS
# ============================================================================

def get_node_sub_trees(tree_id: str, node_id: str, team_id: str) -> Dict:
    """Get all sub-trees that belong to a specific node."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select('*')\
            .eq('parent_tree_id', tree_id)\
            .eq('parent_node_id', node_id)\
            .eq('team_id', team_id)\
            .order('created_at')\
            .execute()
        
        print(f"[@db:navigation_trees:get_node_sub_trees] Retrieved {len(result.data)} sub-trees for node: {node_id}")
        return {
            'success': True,
            'sub_trees': result.data
        }
    except Exception as e:
        print(f"[@db:navigation_trees:get_node_sub_trees] Error: {e}")
        return {'success': False, 'error': str(e)}

def create_sub_tree(parent_tree_id: str, parent_node_id: str, tree_data: Dict, team_id: str) -> Dict:
    """Create a new sub-tree linked to a parent node."""
    try:
        supabase = get_supabase()
        
        # Get parent tree depth
        parent_result = supabase.table('navigation_trees').select('tree_depth')\
            .eq('id', parent_tree_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if not parent_result.data:
            return {'success': False, 'error': 'Parent tree not found'}
        
        parent_depth = parent_result.data[0]['tree_depth']
        
        # Validate depth limit
        if parent_depth >= 5:
            return {'success': False, 'error': 'Maximum nesting depth reached (5 levels)'}
        
        # Set nested tree properties
        tree_data.update({
            'parent_tree_id': parent_tree_id,
            'parent_node_id': parent_node_id,
            'tree_depth': parent_depth + 1,
            'is_root_tree': False,
            'team_id': team_id,
            'id': str(uuid4()),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
        
        # Create the sub-tree
        result = supabase.table('navigation_trees').insert(tree_data).execute()
        
        print(f"[@db:navigation_trees:create_sub_tree] Created sub-tree: {tree_data['id']} for node: {parent_node_id}")
        return {'success': True, 'tree': result.data[0]}
        
    except Exception as e:
        print(f"[@db:navigation_trees:create_sub_tree] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_tree_hierarchy(root_tree_id: str, team_id: str) -> Dict:
    """Get complete tree hierarchy starting from root."""
    try:
        supabase = get_supabase()
        
        # Use the SQL function to get all descendant trees
        result = supabase.rpc('get_descendant_trees', {'root_tree_id': root_tree_id}).execute()
        
        print(f"[@db:navigation_trees:get_tree_hierarchy] Retrieved hierarchy for tree: {root_tree_id}")
        return {
            'success': True,
            'hierarchy': result.data
        }
    except Exception as e:
        print(f"[@db:navigation_trees:get_tree_hierarchy] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_tree_breadcrumb(tree_id: str, team_id: str) -> Dict:
    """Get breadcrumb path for a tree."""
    try:
        supabase = get_supabase()
        
        # Use the SQL function to get tree path
        result = supabase.rpc('get_tree_path', {'target_tree_id': tree_id}).execute()
        
        print(f"[@db:navigation_trees:get_tree_breadcrumb] Retrieved breadcrumb for tree: {tree_id}")
        return {
            'success': True,
            'breadcrumb': result.data
        }
    except Exception as e:
        print(f"[@db:navigation_trees:get_tree_breadcrumb] Error: {e}")
        return {'success': False, 'error': str(e)}

def delete_tree_cascade(tree_id: str, team_id: str) -> Dict:
    """Delete a tree and all its descendant trees."""
    try:
        supabase = get_supabase()
        
        # Get all descendant trees first
        hierarchy_result = get_tree_hierarchy(tree_id, team_id)
        if not hierarchy_result['success']:
            return hierarchy_result
        
        # Delete all trees in reverse depth order (deepest first)
        trees_to_delete = sorted(hierarchy_result['hierarchy'], key=lambda x: x['depth'], reverse=True)
        
        for tree in trees_to_delete:
            # Delete tree (cascade will handle nodes and edges)
            supabase.table('navigation_trees').delete().eq('id', tree['tree_id']).eq('team_id', team_id).execute()
            print(f"[@db:navigation_trees:delete_tree_cascade] Deleted tree: {tree['tree_id']}")
        
        return {'success': True, 'deleted_count': len(trees_to_delete)}
        
    except Exception as e:
        print(f"[@db:navigation_trees:delete_tree_cascade] Error: {e}")
        return {'success': False, 'error': str(e)}

def move_subtree(subtree_id: str, new_parent_tree_id: str, new_parent_node_id: str, team_id: str) -> Dict:
    """Move a subtree to a different parent node."""
    try:
        supabase = get_supabase()
        
        # Get new parent depth
        parent_result = supabase.table('navigation_trees').select('tree_depth')\
            .eq('id', new_parent_tree_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if not parent_result.data:
            return {'success': False, 'error': 'New parent tree not found'}
        
        new_parent_depth = parent_result.data[0]['tree_depth']
        
        # Get current subtree depth to check if move is valid
        subtree_result = supabase.table('navigation_trees').select('tree_depth')\
            .eq('id', subtree_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if not subtree_result.data:
            return {'success': False, 'error': 'Subtree not found'}
        
        # Calculate new depth and validate
        depth_difference = subtree_result.data[0]['tree_depth'] - new_parent_depth - 1
        if new_parent_depth + 1 + depth_difference > 5:
            return {'success': False, 'error': 'Move would exceed maximum nesting depth'}
        
        # Update subtree parent relationships
        result = supabase.table('navigation_trees').update({
            'parent_tree_id': new_parent_tree_id,
            'parent_node_id': new_parent_node_id,
            'tree_depth': new_parent_depth + 1,
            'updated_at': datetime.now().isoformat()
        }).eq('id', subtree_id).eq('team_id', team_id).execute()
        
        print(f"[@db:navigation_trees:move_subtree] Moved subtree: {subtree_id} to node: {new_parent_node_id}")
        return {'success': True, 'tree': result.data[0]}
        
    except Exception as e:
        print(f"[@db:navigation_trees:move_subtree] Error: {e}")
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

 