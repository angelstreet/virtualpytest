"""
Validation Routes - Reuses NavigationExecutor API for sequential edge testing
"""

from typing import List
from flask import Blueprint, request, jsonify


# Create blueprint
server_validation_bp = Blueprint('server_validation', __name__, url_prefix='/server/validation')

@server_validation_bp.route('/preview/<tree_id>', methods=['GET'])
def get_validation_preview(tree_id: str):
    """
    Get validation preview - shows which edges will be validated using optimal depth-first sequence
    Uses unified cache system - requires proper cache population
    """
    try:
        team_id = request.args.get('team_id') or (request.get_json() or {}).get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        
        # Check if unified cache is populated for this tree via host API
        from src.lib.utils.route_utils import proxy_to_host
        cache_check_result = proxy_to_host('/host/navigation/cache/check_unified', 'POST', {
            'tree_id': tree_id,
            'team_id': team_id
        })
        unified_graph_exists = cache_check_result.get('exists', False) if cache_check_result and cache_check_result.get('success') else False
        
        if not unified_graph_exists:
            print(f"[@route:get_validation_preview] No unified cache found for tree {tree_id}, populating...")
            
            # Populate unified cache for this tree using the new architecture
            success = ensure_unified_cache_populated(tree_id, team_id)
            if not success:
                return jsonify({
                    'success': False,
                    'error': 'Failed to populate unified navigation cache. Tree may need to be loaded first.'
                }), 400
        
        # Use optimal edge validation sequence with unified cache
        from src.lib.utils.route_utils import proxy_to_host
        
        proxy_result = proxy_to_host('/host/navigation/validation_sequence', 'POST', {
            'tree_id': tree_id,
            'team_id': team_id
        })
        validation_sequence = proxy_result.get('sequence') if proxy_result and proxy_result.get('success') else None
        
        if not validation_sequence:
            return jsonify({
                'success': False,
                'error': 'No validation sequence found - tree may be empty or have no traversable edges'
            }), 400
        
        # Convert validation sequence to preview format
        edges = []
        for validation_step in validation_sequence:
            edge_info = {
                'step_number': validation_step['step_number'],
                'from_node': validation_step['from_node_id'],
                'to_node': validation_step['to_node_id'],
                'from_name': validation_step['from_node_label'],
                'to_name': validation_step['to_node_label'],
                'selected': True,
                'actions': validation_step.get('actions', []),
                'has_verifications': validation_step.get('total_verifications', 0) > 0,
                'step_type': validation_step.get('step_type', 'unknown')
            }
            edges.append(edge_info)
        
        return jsonify({
            'success': True,
            'tree_id': tree_id,
            'total_edges': len(edges),
            'edges': edges,
            'algorithm': 'unified_depth_first_traversal'
        })
        
    except Exception as e:
        print(f"[@route:get_validation_preview] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to get validation preview: {str(e)}'
        }), 500


def ensure_unified_cache_populated(tree_id: str, team_id: str) -> bool:
    """
    Ensure unified cache is populated for the given tree
    Uses the new normalized database architecture
    """
    try:
        print(f"[@route:ensure_unified_cache_populated] Populating unified cache for tree {tree_id}")
        
        # Get complete tree hierarchy from new normalized tables
        from shared.src.lib.supabase.navigation_trees_db import get_complete_tree_hierarchy
        hierarchy_result = get_complete_tree_hierarchy(tree_id, team_id)
        
        if not hierarchy_result.get('success'):
            print(f"[@route:ensure_unified_cache_populated] get_complete_tree_hierarchy failed: {hierarchy_result.get('error')}")
            
            # Fallback: Try to load single tree if hierarchy fails
            print(f"[@route:ensure_unified_cache_populated] Attempting single tree load as fallback...")
            return ensure_single_tree_cache_populated(tree_id, team_id)
        
        all_trees_data = hierarchy_result.get('all_trees_data', [])
        if not all_trees_data:
            print(f"[@route:ensure_unified_cache_populated] No tree data found, attempting single tree load...")
            return ensure_single_tree_cache_populated(tree_id, team_id)
        
        # Populate unified cache via host API
        from src.lib.utils.route_utils import proxy_to_host
        populate_result = proxy_to_host('/host/navigation/cache/populate_unified', 'POST', {
            'tree_id': tree_id,
            'team_id': team_id,
            'all_trees_data': all_trees_data
        })
        unified_graph_created = populate_result.get('success', False) if populate_result else False
        
        if unified_graph_created:
            print(f"[@route:ensure_unified_cache_populated] Successfully populated unified cache via host API")
            return True
        else:
            print(f"[@route:ensure_unified_cache_populated] Failed to create unified graph, trying single tree...")
            return ensure_single_tree_cache_populated(tree_id, team_id)
        
    except Exception as e:
        print(f"[@route:ensure_unified_cache_populated] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"[@route:ensure_unified_cache_populated] Falling back to single tree cache...")
        return ensure_single_tree_cache_populated(tree_id, team_id)


def ensure_single_tree_cache_populated(tree_id: str, team_id: str) -> bool:
    """
    Populate unified cache with single tree data (for trees without nested structure)
    """
    try:
        print(f"[@route:ensure_single_tree_cache_populated] Loading single tree for unified cache: {tree_id}")
        
        # Get single tree data
        from shared.src.lib.supabase.navigation_trees_db import get_full_tree
        tree_result = get_full_tree(tree_id, team_id)
        
        if not tree_result.get('success'):
            print(f"[@route:ensure_single_tree_cache_populated] Failed to load tree: {tree_result.get('error')}")
            return False
        
        # Format as single-tree hierarchy for unified cache
        single_tree_data = [{
            'tree_id': tree_id,
            'tree_info': {
                'name': tree_result['tree'].get('name', 'Unknown'),
                'is_root_tree': True,
                'tree_depth': 0,
                'parent_tree_id': None,
                'parent_node_id': None
            },
            'nodes': tree_result['nodes'],
            'edges': tree_result['edges']
        }]
        
        # Populate unified cache with single tree via host API
        from src.lib.utils.route_utils import proxy_to_host
        populate_result = proxy_to_host('/host/navigation/cache/populate_unified', 'POST', {
            'tree_id': tree_id,
            'team_id': team_id,
            'all_trees_data': single_tree_data
        })
        unified_graph_created = populate_result.get('success', False) if populate_result else False
        
        if unified_graph_created:
            print(f"[@route:ensure_single_tree_cache_populated] Successfully populated single-tree unified cache via host API")
            return True
        else:
            print(f"[@route:ensure_single_tree_cache_populated] Failed to create single-tree unified graph")
            return False
            
    except Exception as e:
        print(f"[@route:ensure_single_tree_cache_populated] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Removed /status/<task_id> route - no longer needed since validation uses useScript directly

# Removed /run/<tree_id> route - validation now uses existing useScript infrastructure
# The frontend calls the validation script directly through RunTests.tsx + useScript.ts
