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
from shared.src.lib.database.navigation_trees_db import (
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
from shared.src.lib.database.userinterface_db import get_all_userinterfaces
from shared.src.lib.utils.app_utils import DEFAULT_USER_ID, check_supabase
from shared.src.lib.config.constants import CACHE_CONFIG
import time
import threading

server_navigation_trees_bp = Blueprint('server_navigation_trees', __name__, url_prefix='/server')

# ============================================================================
# IN-MEMORY CACHE FOR NAVIGATION TREES (reduces DB queries from 3 to 0)
# ============================================================================

_tree_cache = {}  # {tree_id: {'data': {...}, 'timestamp': time.time()}}
_cache_lock = threading.Lock()

def get_cached_tree(tree_id: str, team_id: str):
    """Get tree from cache if available and not expired."""
    with _cache_lock:
        cache_key = f"{team_id}:{tree_id}"
        if cache_key in _tree_cache:
            cached = _tree_cache[cache_key]
            age = time.time() - cached['timestamp']
            if age < CACHE_CONFIG['MEDIUM_TTL']:
                print(f"[@cache] HIT: Tree {tree_id} (age: {age:.1f}s)")
                return cached['data']
            else:
                # Expired
                print(f"[@cache] EXPIRED: Tree {tree_id} (age: {age:.1f}s)")
                del _tree_cache[cache_key]
        return None

def set_cached_tree(tree_id: str, team_id: str, data):
    """Store tree in cache."""
    with _cache_lock:
        cache_key = f"{team_id}:{tree_id}"
        _tree_cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        print(f"[@cache] SET: Tree {tree_id} (total cached: {len(_tree_cache)})")

def invalidate_cached_tree(tree_id: str, team_id: str):
    """Invalidate cached tree when it's modified (SERVER + HOST)."""
    # Clear SERVER cache
    with _cache_lock:
        cache_key = f"{team_id}:{tree_id}"
        if cache_key in _tree_cache:
            del _tree_cache[cache_key]
            print(f"[@cache] INVALIDATE: Tree {tree_id}")
    
    # Clear HOST cache
    from shared.src.lib.database.navigation_trees_db import invalidate_navigation_cache_for_tree
    invalidate_navigation_cache_for_tree(tree_id, team_id)
    
    # Also invalidate preview cache on all host devices
    try:
        from flask import current_app
        host_devices = getattr(current_app, 'host_devices', {})
        for device_id, device in host_devices.items():
            if hasattr(device, 'navigation_executor') and device.navigation_executor:
                device.navigation_executor.clear_preview_cache(tree_id)
    except Exception as e:
        print(f"[@cache] Warning: Could not clear preview cache: {e}")

def _fetch_tree_metrics(tree_id: str, team_id: str):
    """
    Internal helper to fetch metrics for a tree (used by combined endpoint).
    Uses optimized Supabase function that reads from pre-aggregated metrics tables.
    Returns metrics data or None on error.
    
    Performance: ~5ms (reads from node_metrics and edge_metrics tables)
    """
    try:
        from shared.src.lib.utils.supabase_utils import get_supabase_client
        
        supabase = get_supabase_client()
        
        # Call optimized Supabase function (reads from pre-aggregated metrics tables)
        # This is MUCH faster than computing from execution_results
        result = supabase.rpc(
            'get_tree_metrics_optimized',
            {'p_tree_id': tree_id, 'p_team_id': team_id}
        ).execute()
        
        if result.data:
            metrics_data = result.data
            print(f"[@metrics] ⚡ Fetched pre-aggregated metrics for tree {tree_id}")
            
            return {
                'nodes': metrics_data.get('nodes', {}),
                'edges': metrics_data.get('edges', {}),
                'global_confidence': metrics_data.get('global_confidence', 0.0),
                'confidence_distribution': metrics_data.get('confidence_distribution', {
                    'high': 0, 'medium': 0, 'low': 0, 'untested': 0
                }),
                'hierarchy_info': {
                    'total_trees': 1,
                    'max_depth': 0,
                    'has_nested_trees': False,
                    'trees': [{
                        'tree_id': tree_id,
                        'name': 'Navigation Tree',
                        'depth': 0,
                        'is_root': True
                    }]
                }
            }
        else:
            print(f"[@metrics] No metrics data returned for tree {tree_id}")
            return None
            
    except Exception as e:
        print(f"[@metrics] Error fetching metrics: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# TREE METADATA ENDPOINTS
# ============================================================================

@server_navigation_trees_bp.route('/navigationTrees', methods=['GET'])
def get_all_navigation_trees():
    """Get all navigation trees metadata for a team."""
    try:
        # Extract HTTP request data
        team_id = request.args.get('team_id')
        user_agent = request.headers.get('User-Agent', 'Unknown')
        referer = request.headers.get('Referer', 'Unknown')
        
        # Delegate to service layer (business logic moved out of route)
        from services.navigation_service import navigation_service
        result = navigation_service.get_all_navigation_trees(team_id, user_agent, referer)
        
        # Return HTTP response
        if result['success']:
            return jsonify({
                'success': True,
                'trees': result['trees']
            })
        else:
            status_code = result.get('status_code', 500)
            return jsonify({
                'success': False,
                'message': result['error']
            }), status_code
            
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        
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
        tree_data = request.get_json()
        
        if not tree_data:
            return jsonify({
                'success': False,
                'message': 'No tree data provided'
            }), 400
        
        team_id = tree_request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
    """
    Create a new node.
    
    Node Structure:
    {
        "node_id": "string",
        "label": "string", 
        "node_type": "screen|entry|...",
        "position_x": number,
        "position_y": number,
        "verifications": [...]  # ⚠️ TOP-LEVEL FIELD - verifications go HERE, not in data.verifications
        "data": {...}           # Metadata only - don't put verifications here
    }
    
    Note: The backend will auto-migrate verifications from data.verifications to root level
    as a safety measure, but always put them at the top level in your requests.
    """
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        node_data = request.get_json()
        
        if not node_data:
            return jsonify({
                'success': False,
                'message': 'No node data provided'
            }), 400
        
        result = save_node(tree_id, node_data, team_id)
        
        if result['success']:
            # Invalidate tree cache when node is created
            invalidate_cached_tree(tree_id, team_id)
            
            # Invalidate user interfaces cache (first node creation makes tree visible)
            from backend_server.src.routes.server_userinterface_routes import _invalidate_interfaces_cache
            _invalidate_interfaces_cache(team_id)
            
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
    """
    Update a node.
    
    Updates Structure:
    {
        "verifications": [...]  # ⚠️ TOP-LEVEL FIELD - verifications go HERE, not in data.verifications
        "data": {...}           # Metadata only - don't put verifications here
        ... other fields ...
    }
    
    Note: The backend will auto-migrate verifications from data.verifications to root level
    as a safety measure, but always put them at the top level in your requests.
    """
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        node_data = request.get_json()
        
        if not node_data:
            return jsonify({
                'success': False,
                'message': 'No node data provided'
            }), 400
        
        # ✅ VALIDATION: Check verifications if provided
        verifications = node_data.get('verifications', [])
        if verifications:
            # Get userinterface to determine device_model
            from shared.src.lib.database.navigation_trees_db import get_tree_metadata
            tree_metadata = get_tree_metadata(tree_id, team_id)
            
            if tree_metadata and tree_metadata.get('success'):
                userinterface_id = tree_metadata.get('tree', {}).get('userinterface_id')
                
                if userinterface_id:
                    from shared.src.lib.database.userinterface_db import get_userinterface
                    ui_result = get_userinterface(userinterface_id, team_id)
                    
                    if ui_result and ui_result.get('success'):
                        device_model = ui_result.get('userinterface', {}).get('device_model', 'unknown')
                        
                        # Import validator
                        from backend_server.src.mcp.utils.api_client import MCPAPIClient
                        from backend_server.src.mcp.utils.verification_validator import VerificationValidator
                        from shared.src.lib.config.constants import APP_CONFIG
                        
                        api_client = MCPAPIClient(
                            APP_CONFIG.get('BACKEND_SERVER_URL', 'http://localhost:5000')
                        )
                        validator = VerificationValidator(api_client)
                        
                        is_valid, errors, warnings = validator.validate_verifications(
                            verifications,
                            device_model
                        )
                        
                        if not is_valid:
                            error_msg = "❌ Invalid verification command(s):\n\n"
                            error_msg += "\n".join(errors)
                            error_msg += "\n\n" + validator.get_valid_commands_for_display(device_model)
                            
                            return jsonify({
                                'success': False,
                                'message': error_msg,
                                'errors': errors
                            }), 400
                        
                        # Log warnings but allow save
                        if warnings:
                            print(f"[@route:navigation_trees:update_node] ⚠️ Verification warnings:")
                            for warning in warnings:
                                print(f"  {warning}")
        
        node_data['node_id'] = node_id
        result = save_node(tree_id, node_data, team_id)
        
        if result['success']:
            # Invalidate tree cache when node is updated
            invalidate_cached_tree(tree_id, team_id)
            
            # No need to invalidate interfaces cache for node updates (doesn't affect visibility)
            
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        result = delete_node(tree_id, node_id, team_id)
        
        if result['success']:
            # Invalidate tree cache when node is deleted
            invalidate_cached_tree(tree_id, team_id)
            
            # Invalidate user interfaces cache (deleting all nodes makes tree invisible)
            from backend_server.src.routes.server_userinterface_routes import _invalidate_interfaces_cache
            _invalidate_interfaces_cache(team_id)
            
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        edge_data = request.get_json()
        
        if not edge_data:
            return jsonify({
                'success': False,
                'message': 'No edge data provided'
            }), 400
        
        # ✅ VALIDATION: Check action commands if provided
        action_sets = edge_data.get('action_sets', [])
        if action_sets:
            # Get userinterface to determine device_model
            from shared.src.lib.database.navigation_trees_db import get_tree_metadata
            tree_metadata = get_tree_metadata(tree_id, team_id)
            
            if tree_metadata and tree_metadata.get('success'):
                userinterface_id = tree_metadata.get('tree', {}).get('userinterface_id')
                
                if userinterface_id:
                    from shared.src.lib.database.userinterface_db import get_userinterface
                    ui_result = get_userinterface(userinterface_id, team_id)
                    
                    if ui_result and ui_result.get('success'):
                        device_model = ui_result.get('userinterface', {}).get('device_model', 'unknown')
                        
                        # Import validator
                        from backend_server.src.mcp.utils.api_client import MCPAPIClient
                        from backend_server.src.mcp.utils.action_validator import ActionValidator
                        from shared.src.lib.config.constants import APP_CONFIG
                        
                        api_client = MCPAPIClient(
                            APP_CONFIG.get('BACKEND_SERVER_URL', 'http://localhost:5000')
                        )
                        validator = ActionValidator(api_client)
                        
                        is_valid, errors, warnings = validator.validate_action_sets(
                            action_sets,
                            device_model
                        )
                        
                        if not is_valid:
                            error_msg = "❌ Invalid action command(s):\n\n"
                            error_msg += "\n".join(errors)
                            error_msg += "\n\n" + validator.get_valid_commands_for_display(device_model)
                            
                            return jsonify({
                                'success': False,
                                'message': error_msg,
                                'errors': errors
                            }), 400
                        
                        # Log warnings but allow save
                        if warnings:
                            print(f"[@route:navigation_trees:create_edge] ⚠️ Action warnings:")
                            for warning in warnings:
                                print(f"  {warning}")
        
        result = save_edge(tree_id, edge_data, team_id)
        
        if result['success']:
            # Invalidate cache when edge is created
            invalidate_cached_tree(tree_id, team_id)
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        edge_data = request.get_json()
        
        if not edge_data:
            return jsonify({
                'success': False,
                'message': 'No edge data provided'
            }), 400
        
        # ✅ VALIDATION: Check action commands if provided
        action_sets = edge_data.get('action_sets', [])
        if action_sets:
            # Get userinterface to determine device_model
            from shared.src.lib.database.navigation_trees_db import get_tree_metadata
            tree_metadata = get_tree_metadata(tree_id, team_id)
            
            if tree_metadata and tree_metadata.get('success'):
                userinterface_id = tree_metadata.get('tree', {}).get('userinterface_id')
                
                if userinterface_id:
                    from shared.src.lib.database.userinterface_db import get_userinterface
                    ui_result = get_userinterface(userinterface_id, team_id)
                    
                    if ui_result and ui_result.get('success'):
                        device_model = ui_result.get('userinterface', {}).get('device_model', 'unknown')
                        
                        # Import validator
                        from backend_server.src.mcp.utils.api_client import MCPAPIClient
                        from backend_server.src.mcp.utils.action_validator import ActionValidator
                        from shared.src.lib.config.constants import APP_CONFIG
                        
                        api_client = MCPAPIClient(
                            APP_CONFIG.get('BACKEND_SERVER_URL', 'http://localhost:5000')
                        )
                        validator = ActionValidator(api_client)
                        
                        is_valid, errors, warnings = validator.validate_action_sets(
                            action_sets,
                            device_model
                        )
                        
                        if not is_valid:
                            error_msg = "❌ Invalid action command(s):\n\n"
                            error_msg += "\n".join(errors)
                            error_msg += "\n\n" + validator.get_valid_commands_for_display(device_model)
                            
                            return jsonify({
                                'success': False,
                                'message': error_msg,
                                'errors': errors
                            }), 400
                        
                        # Log warnings but allow save
                        if warnings:
                            print(f"[@route:navigation_trees:update_edge] ⚠️ Action warnings:")
                            for warning in warnings:
                                print(f"  {warning}")
        
        edge_data['edge_id'] = edge_id
        result = save_edge(tree_id, edge_data, team_id)
        
        if result['success']:
            # Invalidate cache when edge is updated
            invalidate_cached_tree(tree_id, team_id)
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        result = delete_edge(tree_id, edge_id, team_id)
        
        if result['success']:
            # Invalidate cache when edge is deleted
            invalidate_cached_tree(tree_id, team_id)
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        result = get_full_tree(tree_id, team_id)
        
        if result['success']:
            # Cache population moved to "Take Control" flow - no longer done during tree loading
            
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
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
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
            # Invalidate tree cache when tree is modified
            invalidate_cached_tree(tree_id, team_id)
            
            # Invalidate user interfaces cache so getAllUserInterfaces refreshes root_tree status
            from backend_server.src.routes.server_userinterface_routes import _invalidate_interfaces_cache
            _invalidate_interfaces_cache(team_id)
            print(f"[@route:navigation_trees:save_batch] Invalidated interfaces cache for team {team_id}")
            
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
    """
    Get navigation tree for a specific user interface (with 5-min cache).
    
    Query parameters:
        include_metrics: boolean (default: false) - Include metrics data with tree data
                        Set to true to get tree + metrics in a single call (reduces 2 calls to 1)
        include_nested: boolean (default: false) - Include all nested subtrees
                        Set to true to get complete hierarchy (root + all nested trees)
    """
    try:
        team_id = request.args.get('team_id') 
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
        
        # Check if we should include metrics (defaults to false for backward compatibility)
        include_metrics = request.args.get('include_metrics', 'false').lower() == 'true'
        
        # Check if we should include nested trees (defaults to false for backward compatibility)
        include_nested = request.args.get('include_nested', 'false').lower() == 'true'
        
        # Get the root tree for this user interface
        tree = get_root_tree_for_interface(userinterface_id, team_id)
        
        if tree:
            tree_id = tree['id']
            
            # If nested trees requested, load complete hierarchy (no cache for now)
            if include_nested:
                print(f"[@route:navigation_trees] Loading complete hierarchy for tree {tree_id}")
                from shared.src.lib.database.navigation_trees_db import get_complete_tree_hierarchy
                
                hierarchy_result = get_complete_tree_hierarchy(tree_id, team_id)
                
                if hierarchy_result.get('success'):
                    all_trees_data = hierarchy_result.get('all_trees_data', [])
                    
                    # Flatten all nodes from all trees, but exclude duplicate nodes from nested trees
                    # Duplicates occur when a parent node (with has_subtree=true) also exists as entry in the subtree
                    all_nodes = []
                    all_edges = []
                    
                    # Track seen node IDs and labels to avoid duplicates
                    seen_node_ids = set()
                    seen_labels = set()
                    
                    for tree_data in all_trees_data:
                        tree_info = tree_data.get('tree_info', {})
                        is_root_tree = tree_info.get('is_root_tree', False)
                        
                        nodes = tree_data.get('nodes', [])
                        edges = tree_data.get('edges', [])
                        
                        if is_root_tree:
                            # For root tree, include all nodes and track them
                            for node in nodes:
                                all_nodes.append(node)
                                seen_node_ids.add(node.get('node_id'))
                                seen_labels.add(node.get('label'))
                            print(f"[@route:navigation_trees] Root tree: added {len(nodes)} nodes")
                        else:
                            # For nested trees, skip nodes that already exist in parent
                            unique_nodes = []
                            skipped_count = 0
                            for node in nodes:
                                node_id = node.get('node_id')
                                label = node.get('label')
                                
                                # Skip if we've already seen this node_id or label
                                if node_id in seen_node_ids or label in seen_labels:
                                    print(f"[@route:navigation_trees] Skipping duplicate node: {label} (already in parent tree)")
                                    skipped_count += 1
                                    continue
                                
                                unique_nodes.append(node)
                                seen_node_ids.add(node_id)
                                seen_labels.add(label)
                            
                            all_nodes.extend(unique_nodes)
                            print(f"[@route:navigation_trees] Nested tree '{tree_info.get('name', 'unknown')}': added {len(unique_nodes)} nodes (skipped {skipped_count} duplicates)")
                        
                        # Include all edges from all trees
                        all_edges.extend(edges)
                    
                    response_data = {
                        'success': True,
                        'tree': {
                            'id': tree['id'],
                            'name': tree['name'],
                            'viewport_x': tree.get('viewport_x', 0),
                            'viewport_y': tree.get('viewport_y', 0),
                            'viewport_zoom': tree.get('viewport_zoom', 1),
                            'metadata': {
                                'nodes': all_nodes,
                                'edges': all_edges
                            }
                        },
                        'nested_trees_count': len(all_trees_data)
                    }
                    
                    print(f"[@route:navigation_trees] Loaded {len(all_trees_data)} trees with {len(all_nodes)} total unique nodes")
                    return jsonify(response_data)
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to load tree hierarchy: {hierarchy_result.get("error", "Unknown error")}'
                    })
            
            # Try cache first (avoids 3 DB queries!) - only for non-nested requests
            cached_result = get_cached_tree(tree_id, team_id)
            if cached_result:
                # If metrics requested and not in cache, fetch and add them
                if include_metrics and 'metrics' not in cached_result:
                    print(f"[@cache] HIT: Tree {tree_id}, fetching metrics...")
                    metrics_data = _fetch_tree_metrics(tree_id, team_id)
                    if metrics_data:
                        cached_result['metrics'] = metrics_data
                return jsonify(cached_result)
            
            # Cache miss - fetch from database
            print(f"[@cache] MISS: Tree {tree_id} - fetching from DB")
            result = get_full_tree(tree_id, team_id)
            
            if result['success']:
                # Build response
                response_data = {
                    'success': True,
                    'tree': {
                        'id': tree['id'],
                        'name': tree['name'],
                        'viewport_x': tree.get('viewport_x', 0),
                        'viewport_y': tree.get('viewport_y', 0),
                        'viewport_zoom': tree.get('viewport_zoom', 1),
                        'metadata': {
                            'nodes': result.get('nodes', []),
                            'edges': result.get('edges', [])
                        }
                    }
                }
                
                # Fetch metrics if requested (combines 2 API calls into 1)
                if include_metrics:
                    print(f"[@cache] Including metrics for tree {tree_id}")
                    metrics_data = _fetch_tree_metrics(tree_id, team_id)
                    if metrics_data:
                        response_data['metrics'] = metrics_data
                
                # Cache for next time (note: we cache WITH metrics if requested)
                set_cached_tree(tree_id, team_id, response_data)
                
                # Prevent browser caching - always fetch fresh from server
                response = jsonify(response_data)
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed to load tree data: {result.get("error", "Unknown error")}'
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