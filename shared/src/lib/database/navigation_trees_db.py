"""
Navigation Trees Database Operations - Normalized Architecture

This module provides functions for managing navigation trees using the new normalized structure:
- navigation_trees: Tree metadata containers with nested tree support
- navigation_nodes: Individual nodes with embedded verifications
- navigation_edges: Edges with embedded actions

Clean, scalable, individual record operations with nested tree functionality.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from shared.src.lib.utils.supabase_utils import get_supabase_client

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()

def _get_root_tree_id(tree_id: str, team_id: str) -> Optional[str]:
    """
    Get root tree ID for a given tree (could be a subtree)
    
    Args:
        tree_id: Current tree ID (may be a subtree)
        team_id: Team ID
        
    Returns:
        Root tree ID or None
    """
    try:
        supabase = get_supabase()
        
        # Get tree info
        tree_result = supabase.table('navigation_trees').select('id, is_root_tree, parent_tree_id, userinterface_id')\
            .eq('id', tree_id)\
            .eq('team_id', team_id)\
            .limit(1)\
            .execute()
        
        if not tree_result.data:
            return None
        
        tree_info = tree_result.data[0]
        
        # If already root, return it
        if tree_info.get('is_root_tree'):
            return tree_id
        
        # If has parent_tree_id, traverse up
        if tree_info.get('parent_tree_id'):
            return _get_root_tree_id(tree_info['parent_tree_id'], team_id)
        
        # Fallback: Find root by userinterface_id
        if tree_info.get('userinterface_id'):
            root_result = supabase.table('navigation_trees').select('id')\
                .eq('userinterface_id', tree_info['userinterface_id'])\
                .eq('team_id', team_id)\
                .eq('is_root_tree', True)\
                .limit(1)\
                .execute()
            
            if root_result.data:
                return root_result.data[0]['id']
        
        return None
        
    except Exception as e:
        print(f"[@db:_get_root_tree_id] Error: {e}")
        return None

def invalidate_navigation_cache_for_tree(tree_id: str, team_id: str):
    """
    Clear cache when tree is modified (on ANY save: edge, node, tree)
    Cache will be rebuilt automatically on next navigation/take-control
    
    SIMPLE: Just clear local cache (works for direct HOST usage)
    """
    try:
        print(f"[@cache_invalidation] 🔄 Clearing LOCAL cache for tree: {tree_id} (will rebuild on next take-control)")
        
        # Clear local cache directly (works when running in backend_host)
        from shared.src.lib.utils.navigation_cache import clear_unified_cache
        clear_unified_cache(tree_id, team_id)
        
        print(f"[@cache_invalidation] ✅ Cache cleared for tree: {tree_id}")
        
        # NOTE: Materialized view (mv_full_navigation_trees) is automatically refreshed by database triggers
        # on navigation_nodes, navigation_edges, and navigation_trees tables - no manual refresh needed
    except Exception as e:
        print(f"[@cache_invalidation] Error: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# TREE METADATA OPERATIONS
# ============================================================================

def get_all_trees(team_id: str) -> Dict:
    """Get all navigation trees metadata for a team."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select('*').eq('team_id', team_id).order('created_at').execute()
        
        print(f"[@db:navigation_trees:get_all_trees] Retrieved {len(result.data)} trees")
        return {'success': True, 'trees': result.data}
    except Exception as e:
        print(f"[@db:navigation_trees:get_all_trees] Error: {e}")
        return {'success': False, 'error': str(e), 'trees': []}

def get_tree_metadata(tree_id: str, team_id: str) -> Dict:
    """Get tree basic information."""
    try:
        supabase = get_supabase()
        result = supabase.table('navigation_trees').select('*').eq('id', tree_id).eq('team_id', team_id).execute()
        
        if result.data:
            return {'success': True, 'tree': result.data[0]}
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
        tree_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        if 'id' in tree_data and tree_data['id']:
            # Update existing tree
            result = supabase.table('navigation_trees').update(tree_data).eq('id', tree_data['id']).eq('team_id', team_id).execute()
            print(f"[@db:navigation_trees:save_tree_metadata] Updated tree: {tree_data['id']}")
        else:
            # Create new tree
            tree_data['id'] = str(uuid4())
            tree_data['created_at'] = datetime.now(timezone.utc).isoformat()
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

def duplicate_tree(source_tree_id: str, target_userinterface_id: str, target_userinterface_name: str, team_id: str) -> Dict:
    """Duplicate entire navigation tree (optimized with batch inserts)."""
    try:
        supabase = get_supabase()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Get source tree and data
        source_tree = supabase.table('navigation_trees').select('*').eq('id', source_tree_id).eq('team_id', team_id).single().execute()
        if not source_tree.data:
            return {'success': False, 'error': 'Source tree not found'}
        
        full_tree = get_full_tree(source_tree_id, team_id)
        if not full_tree['success']:
            return {'success': False, 'error': f"Failed to get tree data: {full_tree.get('error')}"}
        
        # Create new tree
        new_tree_id = str(uuid4())
        supabase.table('navigation_trees').insert({
            'id': new_tree_id,
            'name': source_tree.data.get('name', target_userinterface_name),
            'userinterface_id': target_userinterface_id,
            'is_root_tree': source_tree.data.get('is_root_tree', True),
            'tree_depth': source_tree.data.get('tree_depth', 0),
            'viewport_x': source_tree.data.get('viewport_x', 0),
            'viewport_y': source_tree.data.get('viewport_y', 0),
            'viewport_zoom': source_tree.data.get('viewport_zoom', 1),
            'team_id': team_id,
            'created_at': timestamp,
            'updated_at': timestamp
        }).execute()
        
        # Batch insert nodes (db triggers will refresh materialized view)
        if full_tree.get('nodes'):
            nodes = [{
                'tree_id': new_tree_id,
                'node_id': n['node_id'],
                'label': n.get('label', ''),
                'node_type': n.get('node_type', 'screen'),
                'position_x': n.get('position_x', 0),
                'position_y': n.get('position_y', 0),
                'data': n.get('data', {}),
                'style': n.get('style', {}),
                'verifications': n.get('verifications', []),
                'team_id': team_id,
                'created_at': timestamp,
                'updated_at': timestamp
            } for n in full_tree['nodes']]
            supabase.table('navigation_nodes').insert(nodes).execute()
        
        # Batch insert edges (db triggers will refresh materialized view)
        if full_tree.get('edges'):
            edges = [{
                'tree_id': new_tree_id,
                'edge_id': e['edge_id'],
                'source_node_id': e['source_node_id'],
                'target_node_id': e['target_node_id'],
                'action_sets': e.get('action_sets', []),
                'default_action_set_id': e.get('default_action_set_id', ''),
                'final_wait_time': e.get('final_wait_time', 2000),
                'label': e.get('label', ''),
                'data': e.get('data', {}),
                'team_id': team_id,
                'created_at': timestamp,
                'updated_at': timestamp
            } for e in full_tree['edges']]
            supabase.table('navigation_edges').insert(edges).execute()
        
        # Verify data was inserted correctly by reading it back
        verify_result = get_full_tree(new_tree_id, team_id)
        if not verify_result['success']:
            print(f"[@db:navigation_trees:duplicate_tree] Warning: Could not verify duplicated tree immediately (materialized view may be refreshing)")
        else:
            actual_nodes = len(verify_result.get('nodes', []))
            actual_edges = len(verify_result.get('edges', []))
            if actual_nodes != len(full_tree.get('nodes', [])) or actual_edges != len(full_tree.get('edges', [])):
                print(f"[@db:navigation_trees:duplicate_tree] Warning: Verification mismatch - expected {len(full_tree.get('nodes', []))} nodes, got {actual_nodes}")
        
        # Invalidate cache for new tree
        invalidate_navigation_cache_for_tree(new_tree_id, team_id)
        
        nodes_count = len(full_tree.get('nodes', []))
        edges_count = len(full_tree.get('edges', []))
        print(f"[@db:navigation_trees:duplicate_tree] Duplicated tree {source_tree_id} -> {new_tree_id} ({nodes_count} nodes, {edges_count} edges)")
        
        return {'success': True, 'tree_id': new_tree_id, 'nodes_count': nodes_count, 'edges_count': edges_count}
        
    except Exception as e:
        print(f"[@db:navigation_trees:duplicate_tree] Error: {e}")
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

def get_nodes_batch(tree_id: str, node_ids: list, team_id: str) -> Dict:
    """Get multiple nodes by their node_ids in a single query (optimized for N+1 prevention)."""
    try:
        if not node_ids:
            return {'success': True, 'nodes': {}}
        
        supabase = get_supabase()
        result = supabase.table('navigation_nodes').select('*')\
            .eq('tree_id', tree_id)\
            .in_('node_id', node_ids)\
            .eq('team_id', team_id)\
            .execute()
        
        # Create a dict for fast lookup: node_id -> node_data
        nodes_dict = {node['node_id']: node for node in result.data} if result.data else {}
        
        print(f"[@db:navigation_trees:get_nodes_batch] Retrieved {len(nodes_dict)}/{len(node_ids)} nodes in single query")
        return {'success': True, 'nodes': nodes_dict}
    except Exception as e:
        print(f"[@db:navigation_trees:get_nodes_batch] Error: {e}")
        return {'success': False, 'error': str(e)}

def save_node(tree_id: str, node_data: Dict, team_id: str) -> Dict:
    """Save a single node (create or update)."""
    try:
        supabase = get_supabase()
        node_data['tree_id'] = tree_id
        node_data['team_id'] = team_id
        node_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Ensure data field is never null - database constraint requires it
        if 'data' not in node_data or node_data['data'] is None:
            node_data['data'] = {}
        
        # Sync data.type with node_type for frontend compatibility
        if 'node_type' in node_data:
            node_data['data']['type'] = node_data['node_type']
        
        # Log what we're about to save
        print(f"[@db:navigation_trees:save_node] Saving node {node_data['node_id']}")
        print(f"[@db:navigation_trees:save_node] data.is_root = {node_data.get('data', {}).get('is_root')}")
        print(f"[@db:navigation_trees:save_node] Full data field: {node_data.get('data')}")
        
        # Ensure style field is never null - database constraint requires it
        if 'style' not in node_data or node_data['style'] is None:
            node_data['style'] = {}
        
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
            print(f"[@db:navigation_trees:save_node] Updated node: {node_data['node_id']}, position: ({node_data.get('position_x', 'missing')}, {node_data.get('position_y', 'missing')})")
        else:
            # Insert new node
            node_data['created_at'] = datetime.now(timezone.utc).isoformat()
            result = supabase.table('navigation_nodes').insert(node_data).execute()
            print(f"[@db:navigation_trees:save_node] Created new node: {node_data['node_id']}, position: ({node_data.get('position_x', 'missing')}, {node_data.get('position_y', 'missing')})")
        
        # NOTE: Cache updates are handled by frontend calling /server/navigation/cache/update-node
        # which proxies to all hosts for incremental NetworkX graph updates (graph.nodes[id].update())
        # This is O(1) incremental update - no full graph rebuild needed
        
        return {'success': True, 'node': result.data[0]}
    except Exception as e:
        print(f"[@db:navigation_trees:save_node] Error: {e}")
        return {'success': False, 'error': str(e)}

def delete_node(tree_id: str, node_id: str, team_id: str) -> Dict:
    """Delete a node, all connected edges, and cascade delete any nested trees."""
    try:
        supabase = get_supabase()
        
        # First, find and delete any nested trees linked to this node
        subtrees_result = get_node_sub_trees(tree_id, node_id, team_id)
        if subtrees_result['success']:
            subtrees = subtrees_result['sub_trees']
            for subtree in subtrees:
                # Use cascade delete to remove the entire subtree hierarchy
                cascade_result = delete_tree_cascade(subtree['id'], team_id)
                if cascade_result['success']:
                    print(f"[@db:navigation_trees:delete_node] Cascade deleted subtree: {subtree['id']} for node: {node_id}")
                else:
                    print(f"[@db:navigation_trees:delete_node] Warning: Failed to delete subtree {subtree['id']}: {cascade_result['error']}")
        
        # Delete connected edges
        supabase.table('navigation_edges').delete()\
            .eq('tree_id', tree_id)\
            .eq('team_id', team_id)\
            .or_(f'source_node_id.eq.{node_id},target_node_id.eq.{node_id}')\
            .execute()
        
        # Delete the node itself
        result = supabase.table('navigation_nodes').delete()\
            .eq('tree_id', tree_id)\
            .eq('node_id', node_id)\
            .eq('team_id', team_id)\
            .execute()
        
        print(f"[@db:navigation_trees:delete_node] Deleted node: {node_id}")
        
        # Invalidate cache after successful delete
        invalidate_navigation_cache_for_tree(tree_id, team_id)
        
        return {'success': True}
    except Exception as e:
        print(f"[@db:navigation_trees:delete_node] Error: {e}")
        return {'success': False, 'error': str(e)}

# ============================================================================
# EDGE OPERATIONS
# ============================================================================

def get_tree_edges(tree_id: str, team_id: str, node_ids: List[str] = None) -> Dict:
    """Get edges with action_sets structure ONLY - NO LEGACY SUPPORT."""
    try:
        supabase = get_supabase()
        
        # Select only new structure fields
        query = supabase.table('navigation_edges')\
            .select('edge_id', 'source_node_id', 'target_node_id', 'action_sets', 'default_action_set_id', 'final_wait_time', 'label', 'data')\
            .eq('tree_id', tree_id)\
            .eq('team_id', team_id)
        
        if node_ids:
            # Get edges that connect to any of the specified nodes
            node_filter = ','.join(node_ids)
            query = query.or_(f'source_node_id.in.({node_filter}),target_node_id.in.({node_filter})')
        
        result = query.order('created_at').execute()
        
        # STRICT: All edges must have action_sets field (can be empty array for initial setup)
        for edge in result.data:
            if 'action_sets' not in edge:
                raise ValueError(f"Edge {edge.get('edge_id')} missing action_sets - migration incomplete")
            if not edge.get('default_action_set_id'):
                raise ValueError(f"Edge {edge.get('edge_id')} missing default_action_set_id - migration incomplete")
        
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
    """Save edge with action_sets structure ONLY - NO LEGACY SUPPORT.
    
    Note: If 'label' is not provided or is empty, the database trigger 
    will automatically generate it in format 'source_label→target_label'.
    """
    try:
        supabase = get_supabase()
        
        # STRICT: Only accept new action_sets format
        if 'action_sets' not in edge_data:
            raise ValueError("action_sets is required")
        
        if not edge_data.get('default_action_set_id'):
            raise ValueError("default_action_set_id is required")
        
        # Validate action_sets constraints
        action_sets = edge_data['action_sets']
        default_id = edge_data['default_action_set_id']
        
        # Validate maximum action sets limit (2 for bidirectional, 1 for unidirectional)
        if len(action_sets) > 2:
            raise ValueError(f"Maximum 2 action sets allowed per edge, got {len(action_sets)}")
        
        # Validate default_action_set_id exists in action_sets (skip if action_sets is empty for initial setup)
        if action_sets and not any(action_set.get('id') == default_id for action_set in action_sets):
            raise ValueError(f"default_action_set_id '{default_id}' not found in action_sets")
        
        edge_data['tree_id'] = tree_id
        edge_data['team_id'] = team_id
        edge_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
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
            edge_data['created_at'] = datetime.now(timezone.utc).isoformat()
            result = supabase.table('navigation_edges').insert(edge_data).execute()
            print(f"[@db:navigation_trees:save_edge] Created new edge: {edge_data['edge_id']}")
        
        # NOTE: Cache updates are handled by frontend calling /server/navigation/cache/update-edge
        # which proxies to all hosts for incremental NetworkX graph updates (graph.remove_edge + graph.add_edge)
        # This is O(1) incremental update - no full graph rebuild needed
        
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
        
        # Invalidate cache after successful delete
        invalidate_navigation_cache_for_tree(tree_id, team_id)
        
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
        
        # Get parent tree depth and userinterface_id
        parent_result = supabase.table('navigation_trees').select('tree_depth, userinterface_id')\
            .eq('id', parent_tree_id)\
            .eq('team_id', team_id)\
            .execute()
        
        if not parent_result.data:
            return {'success': False, 'error': 'Parent tree not found'}
        
        parent_depth = parent_result.data[0]['tree_depth']
        parent_userinterface_id = parent_result.data[0].get('userinterface_id')
        
        # Validate depth limit
        if parent_depth >= 5:
            return {'success': False, 'error': 'Maximum nesting depth reached (5 levels)'}
        
        # Inherit userinterface_id from parent if not provided
        if 'userinterface_id' not in tree_data or tree_data['userinterface_id'] is None:
            tree_data['userinterface_id'] = parent_userinterface_id
        
        # Set nested tree properties
        tree_data.update({
            'parent_tree_id': parent_tree_id,
            'parent_node_id': parent_node_id,
            'tree_depth': parent_depth + 1,
            'is_root_tree': False,
            'team_id': team_id,
            'id': str(uuid4()),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
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


def get_complete_tree_hierarchy(root_tree_id: str, team_id: str) -> Dict[str, Any]:
    """
    Get complete tree hierarchy for unified pathfinding
    FAIL EARLY: Returns error if hierarchy cannot be built
    
    Args:
        root_tree_id: Root navigation tree ID
        team_id: Team ID for security
        
    Returns:
        Dictionary with complete hierarchy data ready for unified pathfinding
    """
    try:
        from shared.src.lib.utils.navigation_exceptions import DatabaseError
        
        # Get root tree
        root_tree = get_full_tree(root_tree_id, team_id)
        if not root_tree['success']:
            raise DatabaseError(f"Failed to load root tree: {root_tree.get('error')}")
        
        # Validate root tree structure
        if not root_tree.get('tree'):
            raise DatabaseError(f"Root tree {root_tree_id} has no tree metadata")
        
        # Get all descendant trees using existing function
        descendant_trees = get_descendant_trees_data(root_tree_id, team_id)
        
        # Build complete hierarchy data
        hierarchy_data = []
        total_nodes = len(root_tree['nodes'])
        total_edges = len(root_tree['edges'])
        
        # Add root tree
        hierarchy_data.append({
            'tree_id': root_tree_id,
            'tree_info': {
                'name': root_tree['tree'].get('name', root_tree_id),
                'is_root_tree': True,
                'tree_depth': 0,
                'parent_tree_id': None,
                'parent_node_id': None
            },
            'nodes': root_tree['nodes'],
            'edges': root_tree['edges']
        })
        
        # Add nested trees
        for nested_tree_info in descendant_trees:
            nested_tree_id = nested_tree_info['tree_id']
            
            nested_data = get_full_tree(nested_tree_id, team_id)
            if nested_data['success']:
                # Validate nested tree structure
                if not nested_data.get('tree'):
                    print(f"[@db:navigation_trees:get_complete_tree_hierarchy] ⚠️ Skipping tree {nested_tree_id} - no tree metadata")
                    continue
                
                hierarchy_data.append({
                    'tree_id': nested_tree_id,
                    'tree_info': {
                        'name': nested_tree_info.get('tree_name', nested_tree_id),
                        'is_root_tree': False,
                        'tree_depth': nested_tree_info.get('depth', 0),
                        'parent_tree_id': nested_tree_info.get('parent_tree_id'),
                        'parent_node_id': nested_tree_info.get('parent_node_id')
                    },
                    'nodes': nested_data['nodes'],
                    'edges': nested_data['edges']
                })
                total_nodes += len(nested_data['nodes'])
                total_edges += len(nested_data['edges'])
        
        max_depth = max([t['tree_info']['tree_depth'] for t in hierarchy_data]) if hierarchy_data else 0
        
        # Single summary log with essential information
        print(f"[@db:navigation_trees:get_complete_tree_hierarchy] Complete hierarchy: {len(hierarchy_data)} trees, {total_nodes} nodes, {total_edges} edges, max depth: {max_depth}")
        
        return {
            'success': True,
            'all_trees_data': hierarchy_data,  # This is the format expected by populate_unified_cache
            'hierarchy': hierarchy_data,       # Keep for backward compatibility
            'total_trees': len(hierarchy_data),
            'max_depth': max_depth,
            'has_nested_trees': len(hierarchy_data) > 1
        }
        
    except Exception as e:
        print(f"[@db:navigation_trees:get_complete_tree_hierarchy] Error: {e}")
        return {
            'success': False,
            'error': f"Failed to build tree hierarchy: {str(e)}"
        }


def get_descendant_trees_data(root_tree_id: str, team_id: str) -> List[Dict]:
    """
    Get all descendant trees with full metadata for hierarchy building
    
    Args:
        root_tree_id: Root tree ID
        team_id: Team ID for security
        
    Returns:
        List of descendant tree metadata dictionaries
    """
    try:
        # Use existing get_tree_hierarchy function
        hierarchy_result = get_tree_hierarchy(root_tree_id, team_id)
        
        if not hierarchy_result['success']:
            return []
        
        hierarchy_trees = hierarchy_result['hierarchy']
        
        # Filter out the root tree (depth 0) to get only descendants
        descendant_trees = [tree for tree in hierarchy_trees if tree.get('depth', 0) > 0]
        
        return descendant_trees
        
    except Exception as e:
        print(f"[@db:navigation_trees:get_descendant_trees_data] Error: {e}")
        return []

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
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', subtree_id).eq('team_id', team_id).execute()
        
        print(f"[@db:navigation_trees:move_subtree] Moved subtree: {subtree_id} to node: {new_parent_node_id}")
        return {'success': True, 'tree': result.data[0]}
        
    except Exception as e:
        print(f"[@db:navigation_trees:move_subtree] Error: {e}")
        return {'success': False, 'error': str(e)}

# ============================================================================
# BATCH OPERATIONS
# ============================================================================

def save_tree_data(tree_id: str, nodes: List[Dict], edges: List[Dict], team_id: str, deleted_node_ids: List[str] = None, deleted_edge_ids: List[str] = None, viewport: Dict = None) -> Dict:
    """Save complete tree data (nodes + edges) in batch with deletions."""
    try:
        # Handle deletions first
        if deleted_node_ids:
            for node_id in deleted_node_ids:
                delete_result = delete_node(tree_id, node_id, team_id)
                if not delete_result['success']:
                    return {'success': False, 'error': f"Failed to delete node {node_id}: {delete_result['error']}"}
        
        if deleted_edge_ids:
            for edge_id in deleted_edge_ids:
                delete_result = delete_edge(tree_id, edge_id, team_id)
                if not delete_result['success']:
                    return {'success': False, 'error': f"Failed to delete edge {edge_id}: {delete_result['error']}"}
        
        # Update tree viewport if provided
        if viewport:
            supabase = get_supabase()
            supabase.table('navigation_trees').update({
                'viewport_x': viewport.get('x', 0),
                'viewport_y': viewport.get('y', 0), 
                'viewport_zoom': viewport.get('zoom', 1)
            }).eq('id', tree_id).eq('team_id', team_id).execute()

        # Save/update current nodes and edges
        saved_nodes = []
        saved_edges = []
        
        # Save all nodes
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
        
        deleted_count = len(deleted_node_ids or []) + len(deleted_edge_ids or [])
        print(f"[@db:navigation_trees:save_tree_data] Deleted {deleted_count} items, saved {len(saved_nodes)} nodes and {len(saved_edges)} edges for tree {tree_id}")
        
        # Invalidate cache after successful save
        invalidate_navigation_cache_for_tree(tree_id, team_id)
        
        return {
            'success': True,
            'nodes': saved_nodes,
            'edges': saved_edges
        }
    except Exception as e:
        print(f"[@db:navigation_trees:save_tree_data] Error: {e}")
        return {'success': False, 'error': str(e)}

def get_full_tree(tree_id: str, team_id: str) -> Dict:
    """
    Get complete tree data (metadata + nodes + edges) from materialized view.
    
    Uses materialized view for instant reads (~10ms) with automatic refresh on writes.
    Database function returns SETOF JSON (array), so we extract first element.
    
    Performance: ~10ms reads (50x faster than function calls)
    """
    supabase = get_supabase()
    
    # RPC call - PostgreSQL function returns SETOF JSON (array with one element)
    result = supabase.rpc(
        'get_full_tree_from_mv',
        {'p_tree_id': tree_id, 'p_team_id': team_id}
    ).execute()
    
    # Extract first element from array
    if result.data and len(result.data) > 0:
        tree_data = result.data[0]
        print(f"[@db:navigation_trees:get_full_tree] ⚡ Retrieved tree {tree_id} from materialized view")
        
        return {
            'success': tree_data.get('success', True),
            'tree': tree_data.get('tree'),
            'nodes': tree_data.get('nodes', []),
            'edges': tree_data.get('edges', [])
        }
    else:
        print(f"[@db:navigation_trees:get_full_tree] ERROR: Tree {tree_id} not found in materialized view")
        return {'success': False, 'error': 'Tree not found'}

 