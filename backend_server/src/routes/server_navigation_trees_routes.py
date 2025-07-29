"""
Navigation Trees API Routes - Normalized Architecture

New API structure for normalized navigation tables:
- Tree metadata operations
- Individual node operations  
- Individual edge operations
- Batch operations

Clean, scalable REST endpoints without monolithic JSONB operations.
"""

from flask import Blueprint, request, jsonify
from shared.lib.supabase.navigation_trees_db import (
    # Tree metadata operations
    get_all_trees, get_tree_metadata, save_tree_metadata, delete_tree,
    # Node operations
    get_tree_nodes, get_node_by_id, save_node, delete_node,
    # Edge operations
    get_tree_edges, get_edge_by_id, save_edge, delete_edge,
    # Batch operations
    save_tree_data, get_full_tree
)
from shared.lib.supabase.userinterface_db import get_all_userinterfaces
from shared.lib.utils.app_utils import DEFAULT_TEAM_ID, DEFAULT_USER_ID, check_supabase, get_team_id

server_navigation_trees_bp = Blueprint('server_navigation_trees', __name__, url_prefix='/server')

# ============================================================================
# TREE METADATA ENDPOINTS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees', methods=['GET'])
def get_all_navigation_trees():
    """Get all navigation trees metadata for a team."""
    try:
        team_id = get_team_id()
        trees = get_all_trees(team_id)
        
        return jsonify({
            'success': True,
            'trees': trees
        })
    except Exception as e:
        print(f'[@route:navigation_trees:get_all] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/metadata', methods=['GET'])
def get_tree_metadata_api(tree_id):
    """Get tree basic metadata information."""
    try:
        team_id = get_team_id()
        result = get_tree_metadata(tree_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        print(f'[@route:navigation_trees:get_metadata] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/metadata', methods=['POST', 'PUT'])
def save_tree_metadata_api(tree_id):
    """Save tree metadata (create or update)."""
    try:
        team_id = get_team_id()
        tree_data = request.get_json()
        
        if not tree_data:
            return jsonify({
                'success': False,
                'message': 'No tree data provided'
            }), 400
        
        # Ensure tree_id matches URL parameter
        tree_data['id'] = tree_id
        
        result = save_tree_metadata(tree_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:save_metadata] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>', methods=['DELETE'])
def delete_tree_api(tree_id):
    """Delete a tree and all its nodes/edges."""
    try:
        team_id = get_team_id()
        result = delete_tree(tree_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:delete_tree] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# NODE ENDPOINTS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/nodes', methods=['GET'])
def get_tree_nodes_api(tree_id):
    """Get nodes for a tree with pagination."""
    try:
        team_id = get_team_id()
        page = int(request.args.get('page', 0))
        limit = int(request.args.get('limit', 100))
        
        result = get_tree_nodes(tree_id, team_id, page, limit)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:get_nodes] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/nodes/<node_id>', methods=['GET'])
def get_node_api(tree_id, node_id):
    """Get a single node by its node_id."""
    try:
        team_id = get_team_id()
        result = get_node_by_id(tree_id, node_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        print(f'[@route:navigation_trees:get_node] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/nodes', methods=['POST'])
def save_node_api(tree_id):
    """Save a single node (create or update)."""
    try:
        team_id = get_team_id()
        node_data = request.get_json()
        
        if not node_data:
            return jsonify({
                'success': False,
                'message': 'No node data provided'
            }), 400
        
        result = save_node(tree_id, node_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:save_node] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/nodes/<node_id>', methods=['PUT'])
def update_node_api(tree_id, node_id):
    """Update a specific node."""
    try:
        team_id = get_team_id()
        node_data = request.get_json()
        
        if not node_data:
            return jsonify({
                'success': False,
                'message': 'No node data provided'
            }), 400
        
        # Ensure node_id matches URL parameter
        node_data['node_id'] = node_id
        
        result = save_node(tree_id, node_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:update_node] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/nodes/<node_id>', methods=['DELETE'])
def delete_node_api(tree_id, node_id):
    """Delete a node and all connected edges."""
    try:
        team_id = get_team_id()
        result = delete_node(tree_id, node_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:delete_node] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# EDGE ENDPOINTS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/edges', methods=['GET'])
def get_tree_edges_api(tree_id):
    """Get edges for a tree, optionally filtered by nodes."""
    try:
        team_id = get_team_id()
        node_ids = request.args.getlist('node_ids')
        
        result = get_tree_edges(tree_id, team_id, node_ids if node_ids else None)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:get_edges] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/edges/<edge_id>', methods=['GET'])
def get_edge_api(tree_id, edge_id):
    """Get a single edge by its edge_id."""
    try:
        team_id = get_team_id()
        result = get_edge_by_id(tree_id, edge_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        print(f'[@route:navigation_trees:get_edge] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/edges', methods=['POST'])
def save_edge_api(tree_id):
    """Save a single edge (create or update)."""
    try:
        team_id = get_team_id()
        edge_data = request.get_json()
        
        if not edge_data:
            return jsonify({
                'success': False,
                'message': 'No edge data provided'
            }), 400
        
        result = save_edge(tree_id, edge_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:save_edge] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/edges/<edge_id>', methods=['PUT'])
def update_edge_api(tree_id, edge_id):
    """Update a specific edge."""
    try:
        team_id = get_team_id()
        edge_data = request.get_json()
        
        if not edge_data:
            return jsonify({
                'success': False,
                'message': 'No edge data provided'
            }), 400
        
        # Ensure edge_id matches URL parameter
        edge_data['edge_id'] = edge_id
        
        result = save_edge(tree_id, edge_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:update_edge] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/edges/<edge_id>', methods=['DELETE'])
def delete_edge_api(tree_id, edge_id):
    """Delete an edge."""
    try:
        team_id = get_team_id()
        result = delete_edge(tree_id, edge_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:delete_edge] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/full', methods=['GET'])
def get_full_tree_api(tree_id):
    """Get complete tree data (metadata + nodes + edges)."""
    try:
        team_id = get_team_id()
        result = get_full_tree(tree_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        print(f'[@route:navigation_trees:get_full_tree] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/batch', methods=['POST'])
def save_tree_data_api(tree_id):
    """Save complete tree data (nodes + edges) in batch."""
    try:
        team_id = get_team_id()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        nodes = data.get('nodes', [])
        edges = data.get('edges', [])
        
        result = save_tree_data(tree_id, nodes, edges, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:save_batch] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees/userinterfaces', methods=['GET'])
def get_userinterfaces():
    """Get all user interfaces for tree creation."""
    try:
        team_id = get_team_id()
        userinterfaces = get_all_userinterfaces(team_id)
        
        return jsonify({
            'success': True,
            'userinterfaces': userinterfaces
        })
    except Exception as e:
        print(f'[@route:navigation_trees:get_userinterfaces] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/lockStatus', methods=['GET'])
def check_lock_status():
    """Check lock status for a navigation tree (placeholder for future locking)."""
    try:
        userinterface_id = request.args.get('userinterface_id')
        
        if not userinterface_id:
            return jsonify({
                'success': False,
                'message': 'Missing required parameter: userinterface_id'
            }), 400
        
        # For now, always return not locked (implement actual locking later)
        return jsonify({
            'success': True,
            'lock': None
        })
    except Exception as e:
        print(f'[@route:navigation_trees:check_lock_status] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500 