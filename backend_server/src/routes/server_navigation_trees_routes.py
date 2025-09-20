"""
Navigation Trees API Routes - Normalized Architecture

New API structure for normalized navigation tables:
- Tree metadata operations
- Individual node operations  
- Individual edge operations
- Batch operations
- Nested tree operations

Clean, scalable REST endpoints without monolithic JSONB operations.
"""

from flask import Blueprint, request, jsonify
from shared.src.lib.config.supabase.navigation_trees_db import (
    # Tree metadata operations
    get_all_trees, get_tree_metadata, save_tree_metadata, delete_tree,
    # Node operations
    get_tree_nodes, get_node_by_id, save_node, delete_node,
    # Edge operations
    get_tree_edges, get_edge_by_id, save_edge, delete_edge,
    # Batch operations
    save_tree_data, get_full_tree,
    # Interface operations
    get_root_tree_for_interface,
    # Nested tree operations
    get_node_sub_trees, create_sub_tree, get_tree_hierarchy, 
    get_tree_breadcrumb, delete_tree_cascade, move_subtree
)
from shared.src.lib.config.supabase.userinterface_db import get_all_userinterfaces
from shared.src.lib.utils.app_utils import DEFAULT_TEAM_ID, DEFAULT_USER_ID, check_supabase, get_team_id

server_navigation_trees_bp = Blueprint('server_navigation_trees', __name__, url_prefix='/server')

# ============================================================================
# TREE METADATA ENDPOINTS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees', methods=['GET'])
def get_all_navigation_trees():
    """Get all navigation trees metadata for a team."""
    # Log caller information to identify source
    user_agent = request.headers.get('User-Agent', 'Unknown')
    referer = request.headers.get('Referer', 'Unknown')
    x_requested_with = request.headers.get('X-Requested-With', 'Unknown')
    print(f"[@server_navigation_trees_routes:navigationTrees] 🔍 CALLER INFO:")
    print(f"  - User-Agent: {user_agent}")
    print(f"  - Referer: {referer}")
    print(f"  - X-Requested-With: {x_requested_with}")
    print(f"  - Remote Address: {request.remote_addr}")
    
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

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>', methods=['GET'])
def get_tree_metadata_api(tree_id):
    """Get tree metadata."""
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

@server_navigation_trees_bp.route('/navigationTrees', methods=['POST'])
def create_tree_api():
    """Create a new navigation tree."""
    try:
        team_id = get_team_id()
        tree_data = request.get_json()
        
        if not tree_data:
            return jsonify({
                'success': False,
                'message': 'No tree data provided'
            }), 400
        
        result = save_tree_metadata(tree_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:create] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>', methods=['PUT'])
def update_tree_api(tree_id):
    """Update tree metadata."""
    try:
        team_id = get_team_id()
        tree_data = request.get_json()
        
        if not tree_data:
            return jsonify({
                'success': False,
                'message': 'No tree data provided'
            }), 400
        
        tree_data['id'] = tree_id
        result = save_tree_metadata(tree_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:update] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>', methods=['DELETE'])
def delete_tree_api(tree_id):
    """Delete a tree."""
    try:
        team_id = get_team_id()
        result = delete_tree(tree_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:delete] ERROR: {e}')
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
def create_node_api(tree_id):
    """Create a new node."""
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
        print(f'[@route:navigation_trees:create_node] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/nodes/<node_id>', methods=['PUT'])
def update_node_api(tree_id, node_id):
    """Update a node."""
    try:
        team_id = get_team_id()
        node_data = request.get_json()
        
        if not node_data:
            return jsonify({
                'success': False,
                'message': 'No node data provided'
            }), 400
        
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
    """Delete a node."""
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
    """Get edges, optionally filtered by nodes."""
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
def create_edge_api(tree_id):
    """Create a new edge."""
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
        print(f'[@route:navigation_trees:create_edge] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/edges/<edge_id>', methods=['PUT'])
def update_edge_api(tree_id, edge_id):
    """Update an edge."""
    try:
        team_id = get_team_id()
        edge_data = request.get_json()
        
        if not edge_data:
            return jsonify({
                'success': False,
                'message': 'No edge data provided'
            }), 400
        
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
# NESTED TREE ENDPOINTS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees/getNodeSubTrees/<tree_id>/<node_id>', methods=['GET'])
def get_node_sub_trees_api(tree_id, node_id):
    """Get all sub-trees for a specific node."""
    try:
        team_id = get_team_id()
        result = get_node_sub_trees(tree_id, node_id, team_id)
        return jsonify(result)
    except Exception as e:
        print(f'[@route:navigation_trees:get_node_sub_trees] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<parent_tree_id>/nodes/<parent_node_id>/subtrees', methods=['POST'])
def create_sub_tree_api(parent_tree_id, parent_node_id):
    """Create a new sub-tree for a specific node."""
    try:
        team_id = get_team_id()
        tree_data = request.get_json()
        
        if not tree_data:
            return jsonify({
                'success': False,
                'message': 'No tree data provided'
            }), 400
        
        result = create_sub_tree(parent_tree_id, parent_node_id, tree_data, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:create_sub_tree] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/hierarchy', methods=['GET'])
def get_tree_hierarchy_api(tree_id):
    """Get complete tree hierarchy starting from root."""
    try:
        team_id = get_team_id()
        result = get_tree_hierarchy(tree_id, team_id)
        return jsonify(result)
    except Exception as e:
        print(f'[@route:navigation_trees:get_hierarchy] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/breadcrumb', methods=['GET'])
def get_tree_breadcrumb_api(tree_id):
    """Get breadcrumb path for a tree."""
    try:
        team_id = get_team_id()
        result = get_tree_breadcrumb(tree_id, team_id)
        return jsonify(result)
    except Exception as e:
        print(f'[@route:navigation_trees:get_breadcrumb] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<tree_id>/cascade', methods=['DELETE'])
def delete_tree_cascade_api(tree_id):
    """Delete a tree and all its descendant trees."""
    try:
        team_id = get_team_id()
        result = delete_tree_cascade(tree_id, team_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:delete_cascade] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/<subtree_id>/move', methods=['PUT'])
def move_subtree_api(subtree_id):
    """Move a subtree to a different parent node."""
    try:
        team_id = get_team_id()
        data = request.get_json()
        
        if not data or 'new_parent_tree_id' not in data or 'new_parent_node_id' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing required fields: new_parent_tree_id, new_parent_node_id'
            }), 400
        
        result = move_subtree(
            subtree_id, 
            data['new_parent_tree_id'], 
            data['new_parent_node_id'], 
            team_id
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f'[@route:navigation_trees:move_subtree] ERROR: {e}')
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
            # Populate navigation cache - EXACT ORIGINAL FORMAT
            try:
                from shared.src.lib.utils.navigation_cache import populate_cache, populate_unified_cache
                nodes = result.get('nodes', [])
                edges = result.get('edges', [])
                
                # Pass nodes and edges exactly as they come from database
                # The graph builder will handle the format conversion
                populate_cache(tree_id, team_id, nodes, edges)
                print(f'[@route:navigation_trees:get_full_tree] Successfully populated navigation cache for tree: {tree_id}')
                
                # Also populate unified cache for single tree case (treat as root tree)
                tree_data_for_unified = [{
                    'tree_id': tree_id,
                    'tree_info': {
                        'name': result.get('name', tree_id),
                        'is_root_tree': True,
                        'tree_depth': 0,
                        'parent_tree_id': None,
                        'parent_node_id': None
                    },
                    'nodes': nodes,
                    'edges': edges
                }]
                
                populate_unified_cache(tree_id, team_id, tree_data_for_unified)
                print(f'[@route:navigation_trees:get_full_tree] Successfully populated unified cache for root tree: {tree_id}')
                
            except Exception as cache_error:
                print(f'[@route:navigation_trees:get_full_tree] Cache population failed: {cache_error}')
                # Don't fail the request if cache population fails
            
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
        deleted_node_ids = data.get('deleted_node_ids', [])
        deleted_edge_ids = data.get('deleted_edge_ids', [])
        
        viewport = data.get('viewport')
        result = save_tree_data(tree_id, nodes, edges, team_id, deleted_node_ids, deleted_edge_ids, viewport)
        
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
# INTERFACE OPERATIONS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees/getTreeByUserInterfaceId/<userinterface_id>', methods=['GET'])
def get_tree_by_userinterface_id(userinterface_id):
    """Get navigation tree for a specific user interface."""
    try:
        team_id = get_team_id()
        
        # Get the root tree for this user interface
        tree = get_root_tree_for_interface(userinterface_id, team_id)
        
        if tree:
            # SAME AS SCRIPT: Load complete hierarchy instead of single tree
            from shared.src.lib.config.supabase.userinterface_db import get_userinterface
            from shared.src.lib.utils.route_utils import proxy_to_host
            
            # Get interface name for hierarchy loading
            interface = get_userinterface(userinterface_id, team_id)
            if not interface:
                return jsonify({
                    'success': False,
                    'error': f'User interface not found: {userinterface_id}'
                })
            
            interface_name = interface.get('name')
            if not interface_name:
                return jsonify({
                    'success': False,
                    'error': f'Interface name not found for: {userinterface_id}'
                })
            
            # Proxy navigation hierarchy loading to host
            print(f'[@route:navigation_trees:get_tree_by_userinterface_id] Loading hierarchy for interface: {interface_name}')
            hierarchy_result = proxy_to_host('/host/navigation/load_hierarchy', 'POST', {
                'interface_name': interface_name,
                'context': 'frontend_navigation_editor',
                'team_id': team_id
            })
            
            if not hierarchy_result['success']:
                return jsonify({
                    'success': False,
                    'error': f'Failed to load hierarchy: {hierarchy_result.get("error", "Unknown error")}'
                })
            
            # Extract root tree data from hierarchy result
            root_tree_data = hierarchy_result['root_tree']
            
            print(f'[@route:navigation_trees:get_tree_by_userinterface_id] Successfully loaded hierarchy with {hierarchy_result["unified_graph_nodes"]} nodes')
            
            return jsonify({
                'success': True,
                'tree': {
                    'id': tree['id'],
                    'name': tree['name'],
                    'viewport_x': tree.get('viewport_x', 0),
                    'viewport_y': tree.get('viewport_y', 0),
                    'viewport_zoom': tree.get('viewport_zoom', 1),
                    'metadata': {
                        'nodes': root_tree_data['nodes'],
                        'edges': root_tree_data['edges']
                    }
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'No navigation tree found for user interface: {userinterface_id}'
            })
    except Exception as e:
        print(f'[@route:navigation_trees:get_tree_by_userinterface_id] ERROR: {e}')
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

@server_navigation_trees_bp.route('/navigationTrees/lockAcquire', methods=['POST'])
def acquire_lock():
    """Acquire lock for a navigation tree (placeholder for future locking)."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request body'
            }), 400
            
        userinterface_id = data.get('userinterface_id')
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        
        if not all([userinterface_id, session_id, user_id]):
            return jsonify({
                'success': False,
                'message': 'Missing required parameters: userinterface_id, session_id, user_id'
            }), 400
        
        # For now, always return successful lock acquisition
        return jsonify({
            'success': True,
            'lock': {
                'userinterface_id': userinterface_id,
                'session_id': session_id,
                'user_id': user_id,
                'locked_at': '2025-01-29T12:00:00Z'
            }
        })
    except Exception as e:
        print(f'[@route:navigation_trees:acquire_lock] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@server_navigation_trees_bp.route('/navigationTrees/lockRelease', methods=['POST'])
def release_lock():
    """Release lock for a navigation tree (placeholder for future locking)."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request body'
            }), 400
            
        userinterface_id = data.get('userinterface_id')
        session_id = data.get('session_id')
        
        if not all([userinterface_id, session_id]):
            return jsonify({
                'success': False,
                'message': 'Missing required parameters: userinterface_id, session_id'
            }), 400
        
        # For now, always return successful lock release
        return jsonify({
            'success': True,
            'message': 'Lock released successfully'
        })
    except Exception as e:
        print(f'[@route:navigation_trees:release_lock] ERROR: {e}')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500 