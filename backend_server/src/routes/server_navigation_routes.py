"""
Navigation API Routes

This module contains the API endpoints for:
- Navigation trees management
- Navigation nodes and edges management

NOTE: Navigation execution routes are now in server_navigation_execution_routes.py
NOTE: Navigation pathfinding and preview routes are in server_pathfinding_routes.py
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import uuid
import requests
import time

# Import from specific database modules (direct imports)
from shared.src.lib.database.navigation_trees_db import (
    get_all_trees as get_all_navigation_trees_util,
    delete_tree as delete_navigation_tree,
    get_tree_metadata,
    save_tree_metadata,
    save_node,
    save_edge
)
from shared.src.lib.database.userinterface_db import (
    get_all_userinterfaces, 
    get_userinterface,
    get_userinterface_by_name
)
from shared.src.lib.utils.app_utils import check_supabase, get_team_id

# Create blueprint with abstract server navigation prefix
server_navigation_bp = Blueprint('server_navigation', __name__, url_prefix='/server/navigation')

# =====================================================
# NAVIGATION TREE MANAGEMENT ENDPOINTS
# =====================================================

@server_navigation_bp.route('/goto', methods=['POST'])
def goto_navigation_node():
    """Navigate to a specific node using abstract navigation controller."""
    try:
        data = request.get_json()
        target_node = data.get('target_node')
        
        print(f"[@route:goto_navigation_node] Navigating to node: {target_node}")
        
        if not target_node:
            return jsonify({
                'success': False,
                'error': 'target_node is required'
            }), 400
        
        # Get the host device object with instantiated controllers
        host_device = getattr(current_app, 'my_host_device', None)
        if not host_device:
            return jsonify({
                'success': False,
                'error': 'Host device not initialized'
            }), 500
        
        # Get the abstract navigation controller
        navigation_controller = host_device.get('controller_objects', {}).get('navigation')
        if not navigation_controller:
            # Fallback to remote controller for basic navigation
            remote_controller = host_device.get('controller_objects', {}).get('remote')
            if not remote_controller:
                return jsonify({
                    'success': False,
                    'error': 'Navigation controller not available'
                }), 400
            
            # Use remote controller for basic navigation
            print(f"[@route:goto_navigation_node] Using remote controller for navigation to: {target_node}")
            result = remote_controller.navigate_to_node(target_node)
        else:
            # Use dedicated navigation controller
            print(f"[@route:goto_navigation_node] Using navigation controller for navigation to: {target_node}")
            result = navigation_controller.goto_node(target_node)
        
        print(f"[@route:goto_navigation_node] Navigation completed successfully")
        return jsonify({
            'success': True,
            'result': result,
            'message': f'Successfully navigated to node: {target_node}'
        })
        
    except Exception as e:
        print(f"[@route:goto_navigation_node] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Navigation error: {str(e)}'
        }), 500

# =====================================================
# NAVIGATION CONFIG MANAGEMENT ENDPOINTS
# =====================================================

@server_navigation_bp.route('/config/createEmpty/<interface_name>', methods=['POST'])
def create_empty_navigation_config(interface_name):
    """Create empty navigation config for a user interface with entry and home nodes."""
    try:
        from uuid import uuid4
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        
        print(f"[@route:create_empty_navigation_config] Creating navigation config for interface: {interface_name}")
        
        # Get user interface data from request or by name lookup
        userinterface_data = data.get('userinterface_data')
        if not userinterface_data:
            # Fallback: look up by name
            userinterface = get_userinterface_by_name(interface_name, team_id)
            if not userinterface:
                return jsonify({
                    'success': False,
                    'error': f'User interface "{interface_name}" not found'
                }), 404
            userinterface_data = userinterface
        
        # Create root navigation tree for this interface
        tree_data = {
            'name': f"{interface_name}_navigation",
            'description': f"Navigation tree for {interface_name}",
            'userinterface_id': userinterface_data.get('id'),
            'is_root_tree': True,
            'tree_depth': 0,
            'parent_tree_id': None,
            'parent_node_id': None,
            'viewport_x': 0,
            'viewport_y': 0,
            'viewport_zoom': 1
        }
        
        # Save the tree metadata
        tree_result = save_tree_metadata(tree_data, team_id)
        
        if not tree_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to create navigation tree: {tree_result.get('error', 'Unknown error')}"
            }), 500
        
        tree_id = tree_result['tree']['id']
        print(f"[@route:create_empty_navigation_config] Created navigation tree: {tree_id}")
        
        # Update user interface with root_tree_id
        from shared.src.lib.database.userinterface_db import update_userinterface
        update_result = update_userinterface(
            userinterface_data.get('id'),
            {'root_tree_id': tree_id},
            team_id
        )
        if update_result:
            print(f"[@route:create_empty_navigation_config] ✅ Updated userinterface with root_tree_id: {tree_id}")
        else:
            print(f"[@route:create_empty_navigation_config] ⚠️ WARNING: Failed to update userinterface with root_tree_id")
        
        # Node and edge save functions are imported at the top
        
        # Create entry node
        entry_node_id = 'entry-node'
        entry_node_data = {
            'node_id': entry_node_id,
            'label': 'Entry',
            'node_type': 'entry',
            'position_x': 100,
            'position_y': 200,
            'data': {
                'type': 'entry',
                'label': 'Entry',
                'description': 'Entry point for navigation',
                'is_root': True
            },
            'verifications': []
        }
        
        entry_result = save_node(tree_id, entry_node_data, team_id)
        if not entry_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to create entry node: {entry_result.get('error', 'Unknown error')}"
            }), 500
        
        print(f"[@route:create_empty_navigation_config] Created entry node: {entry_node_id}")
        
        # Create home node
        home_id = 'home'
        home_data = {
            'node_id': home_id,
            'label': 'home',
            'node_type': 'screen',
            'position_x': 300,
            'position_y': 200,
            'data': {
                'type': 'screen',
                'label': 'home',
                'description': 'Home screen - main landing page',
                'is_root': True
            },
            'verifications': []
        }
        
        home_result = save_node(tree_id, home_data, team_id)
        if not home_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to create home node: {home_result.get('error', 'Unknown error')}"
            }), 500
        
        print(f"[@route:create_empty_navigation_config] Created home node: {home_id}")
        
        # Create edge connecting entry to home
        edge_id = f"edge-{entry_node_id}-to-{home_id}"
        timestamp = int(datetime.now().timestamp() * 1000)
        action_set_id = f'actionset-{timestamp}'
        
        # Create properly initialized action_sets with default action set
        edge_data = {
            'edge_id': edge_id,
            'source_node_id': entry_node_id,
            'target_node_id': home_id,
            'label': 'Entry→home',
            'action_sets': [
                {
                    'id': action_set_id,
                    'label': 'Entry→home',
                    'actions': [],
                    'retry_actions': [],
                    'failure_actions': [],
                    'priority': 1
                }
            ],
            'default_action_set_id': action_set_id,
            'final_wait_time': 2000,
            'data': {
                'priority': 'p3',
                'sourceHandle': 'right-source',
                'targetHandle': 'left-target'
            }
        }
        
        # Debug: Print edge data before saving
        print(f"[@route:create_empty_navigation_config] Edge data: {edge_data}")
        print(f"[@route:create_empty_navigation_config] Action sets: {edge_data.get('action_sets')}")
        print(f"[@route:create_empty_navigation_config] Default action set ID: {edge_data.get('default_action_set_id')}")
        
        edge_result = save_edge(tree_id, edge_data, team_id)
        if not edge_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to create entry→home edge: {edge_result.get('error', 'Unknown error')}"
            }), 500
        
        print(f"[@route:create_empty_navigation_config] Created edge: {edge_id}")
        
        return jsonify({
            'success': True,
            'tree': tree_result['tree'],
            'nodes_created': 2,
            'edges_created': 1,
            'message': f'Navigation config created for {interface_name} with entry and home nodes'
        })
            
    except Exception as e:
        print(f"[@route:create_empty_navigation_config] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

# =====================================================
# CACHE MANAGEMENT ENDPOINTS
# =====================================================

@server_navigation_bp.route('/cache/update-edge', methods=['POST'])
def update_edge_in_cache():
    """Update a specific edge in cached graphs on all hosts (incremental - no rebuild)"""
    try:
        data = request.get_json() or {}
        edge_data = data.get('edge')
        tree_id = data.get('tree_id')
        team_id = request.args.get('team_id')
        
        if not edge_data or not tree_id or not team_id:
            return jsonify({
                'success': False,
                'error': 'edge, tree_id, and team_id are required'
            }), 400
        
        edge_id = edge_data.get('id') or edge_data.get('edge_id')
        print(f"\n{'='*80}")
        print(f"[@route:server_navigation:update_edge_in_cache] 🔄 CACHE UPDATE REQUEST")
        print(f"  → Edge ID: {edge_id}")
        print(f"  → Tree ID: {tree_id}")
        print(f"  → Team ID: {team_id}")
        print(f"  → Source: {edge_data.get('source_node_id')}")
        print(f"  → Target: {edge_data.get('target_node_id')}")
        
        # Get all hosts and update edge on each
        from backend_server.src.lib.utils.server_utils import get_host_manager
        from backend_server.src.lib.utils.route_utils import proxy_to_host_direct
        
        host_manager = get_host_manager()
        all_hosts_dict = host_manager.get_all_hosts()  # Returns dict: {host_name: host_info}
        
        # Convert dict to list of host_info dicts
        hosts = list(all_hosts_dict.values())
        host_names = [h.get('host_name') for h in hosts]
        print(f"  → Updating on {len(hosts)} host(s): {host_names}")
        
        results = []
        success_count = 0
        cache_exists_count = 0
        skip_count = 0
        error_count = 0
        
        for host_info in hosts:
            host_name = host_info.get('host_name')
            try:
                result, status_code = proxy_to_host_direct(
                    host_info,
                    f'/host/navigation/cache/update-edge?team_id={team_id}',  # Add query params to URL
                    'POST',
                    {'edge': edge_data, 'tree_id': tree_id}
                )
                
                # Debug: Log what we got back
                print(f"  [DEBUG] {host_name} response: result={result}, status={status_code}")
                
                if result:
                    cache_exists = result.get('cache_exists', False)
                    success = result.get('success', False)
                    message = result.get('message', '')
                    
                    print(f"  [DEBUG] {host_name} parsed: success={success}, cache_exists={cache_exists}, message={message}")
                    
                    if success and cache_exists:
                        print(f"  ✅ {host_name}: Cache updated")
                        success_count += 1
                        cache_exists_count += 1
                    elif success and not cache_exists:
                        print(f"  ℹ️  {host_name}: No cache (skipped - will rebuild on next take-control)")
                        skip_count += 1
                    else:
                        print(f"  ⚠️  {host_name}: Update failed - {message or 'unknown error'}")
                        error_count += 1
                    
                    results.append({
                        'host': host_name,
                        'success': success,
                        'cache_exists': cache_exists,
                        'message': message
                    })
                else:
                    print(f"  ❌ {host_name}: No response (status: {status_code})")
                    error_count += 1
                    results.append({
                        'host': host_name,
                        'success': False,
                        'error': f'No response (HTTP {status_code})'
                    })
                    
            except Exception as e:
                print(f"  ❌ {host_name}: Exception - {str(e)}")
                error_count += 1
                results.append({
                    'host': host_name,
                    'success': False,
                    'error': str(e)
                })
        
        # Summary
        print(f"\n📊 CACHE UPDATE SUMMARY:")
        print(f"  → Total hosts: {len(hosts)}")
        print(f"  → Successfully updated: {success_count}")
        print(f"  → Skipped (no cache): {skip_count}")
        print(f"  → Errors: {error_count}")
        print(f"{'='*80}\n")
        
        return jsonify({
            'success': True,
            'message': f'Edge update completed on {len(hosts)} host(s)',
            'summary': {
                'total_hosts': len(hosts),
                'updated': success_count,
                'skipped': skip_count,
                'errors': error_count
            },
            'results': results
        })
        
    except Exception as e:
        print(f"[@route:server_navigation:update_edge_in_cache] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Edge update failed: {str(e)}'
        }), 500

@server_navigation_bp.route('/cache/update-node', methods=['POST'])
def update_node_in_cache():
    """Update a specific node in cached graphs on all hosts (incremental - no rebuild)"""
    try:
        data = request.get_json() or {}
        node_data = data.get('node')
        tree_id = data.get('tree_id')
        team_id = request.args.get('team_id')
        
        if not node_data or not tree_id or not team_id:
            return jsonify({
                'success': False,
                'error': 'node, tree_id, and team_id are required'
            }), 400
        
        node_id = node_data.get('id')
        print(f"\n{'='*80}")
        print(f"[@route:server_navigation:update_node_in_cache] 🔄 CACHE UPDATE REQUEST")
        print(f"  → Node ID: {node_id}")
        print(f"  → Tree ID: {tree_id}")
        print(f"  → Team ID: {team_id}")
        
        # Get all hosts and update node on each
        from backend_server.src.lib.utils.server_utils import get_host_manager
        from backend_server.src.lib.utils.route_utils import proxy_to_host_direct
        
        host_manager = get_host_manager()
        all_hosts_dict = host_manager.get_all_hosts()  # Returns dict: {host_name: host_info}
        
        # Convert dict to list of host_info dicts
        hosts = list(all_hosts_dict.values())
        host_names = [h.get('host_name') for h in hosts]
        print(f"  → Updating on {len(hosts)} host(s): {host_names}")
        
        results = []
        success_count = 0
        cache_exists_count = 0
        skip_count = 0
        error_count = 0
        
        for host_info in hosts:
            host_name = host_info.get('host_name')
            try:
                result, status_code = proxy_to_host_direct(
                    host_info,
                    f'/host/navigation/cache/update-node?team_id={team_id}',  # Add query params to URL
                    'POST',
                    {'node': node_data, 'tree_id': tree_id}
                )
                
                # Debug: Log what we got back
                print(f"  [DEBUG] {host_name} response: result={result}, status={status_code}")
                
                if result:
                    cache_exists = result.get('cache_exists', False)
                    success = result.get('success', False)
                    message = result.get('message', '')
                    
                    print(f"  [DEBUG] {host_name} parsed: success={success}, cache_exists={cache_exists}, message={message}")
                    
                    if success and cache_exists:
                        print(f"  ✅ {host_name}: Cache updated")
                        success_count += 1
                        cache_exists_count += 1
                    elif success and not cache_exists:
                        print(f"  ℹ️  {host_name}: No cache (skipped - will rebuild on next take-control)")
                        skip_count += 1
                    else:
                        print(f"  ⚠️  {host_name}: Update failed - {message or 'unknown error'}")
                        error_count += 1
                    
                    results.append({
                        'host': host_name,
                        'success': success,
                        'cache_exists': cache_exists,
                        'message': message
                    })
                else:
                    print(f"  ❌ {host_name}: No response (status: {status_code})")
                    error_count += 1
                    results.append({
                        'host': host_name,
                        'success': False,
                        'error': f'No response (HTTP {status_code})'
                    })
                    
            except Exception as e:
                print(f"  ❌ {host_name}: Exception - {str(e)}")
                error_count += 1
                results.append({
                    'host': host_name,
                    'success': False,
                    'error': str(e)
                })
        
        print(f"\n📊 CACHE UPDATE SUMMARY:")
        print(f"  → Total hosts: {len(hosts)}")
        print(f"  → Successfully updated: {success_count}")
        print(f"  → Skipped (no cache): {skip_count}")
        print(f"  → Errors: {error_count}")
        print(f"{'='*80}\n")
        
        return jsonify({
            'success': True,
            'message': f'Node update requested for tree {tree_id}',
            'results': results
        })
        
    except Exception as e:
        print(f"[@route:server_navigation:update_node_in_cache] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Node update failed: {str(e)}'
        }), 500

@server_navigation_bp.route('/cache/invalidate/<tree_id>', methods=['POST'])
def invalidate_navigation_cache(tree_id):
    """Invalidate navigation cache on all hosts (full rebuild required - use for major changes)"""
    try:
        team_id = request.args.get('team_id')
        
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        print(f"[@route:server_navigation:invalidate_navigation_cache] Invalidating cache for tree {tree_id}")
        
        # Get all hosts and clear cache on each
        from backend_server.src.lib.utils.server_utils import get_host_manager
        from backend_server.src.lib.utils.route_utils import proxy_to_host_direct
        
        host_manager = get_host_manager()
        hosts = host_manager.get_all_hosts()
        
        results = []
        for host in hosts:
            try:
                result, _ = proxy_to_host_direct(
                    host,
                    f'/host/navigation/cache/clear/{tree_id}',
                    'POST',
                    None,
                    {'team_id': team_id}
                )
                results.append({
                    'host': host.get('host_name'),
                    'success': result.get('success', False) if result else False
                })
                print(f"[@route:server_navigation:invalidate_navigation_cache] Cache cleared on {host.get('host_name')}")
            except Exception as e:
                print(f"[@route:server_navigation:invalidate_navigation_cache] Failed for {host.get('host_name')}: {e}")
                results.append({
                    'host': host.get('host_name'),
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': f'Cache invalidation requested for tree {tree_id}',
            'results': results
        })
        
    except Exception as e:
        print(f"[@route:server_navigation:invalidate_navigation_cache] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Cache invalidation failed: {str(e)}'
        }), 500

@server_navigation_bp.route('/cache/refresh', methods=['POST'])
def refresh_navigation_cache():
    """Proxy cache refresh request to pathfinding service"""
    try:
        print("[@route:server_navigation:refresh_navigation_cache] Proxying cache refresh request")
        
        data = request.get_json() or {}
        tree_id = data.get('tree_id')
        team_id = request.args.get('team_id')
        
        if not tree_id:
            return jsonify({
                'success': False,
                'error': 'tree_id is required for cache refresh'
            }), 400
        
        try:
            from shared.src.lib.utils.navigation_cache import clear_unified_cache
            
            # Clear the cache for this tree to force a rebuild on next access
            clear_unified_cache(tree_id, team_id)
            
            message = f"Navigation cache cleared for tree {tree_id}"
            return jsonify({
                'success': True,
                'message': message
            })
        except ImportError as e:
            print(f"[@route:server_navigation:refresh_navigation_cache] Cache modules not available: {e}")
            return jsonify({
                'success': False,
                'error': 'Navigation cache modules not available'
            }), 503
        
    except Exception as e:
        print(f"[@route:server_navigation:refresh_navigation_cache] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
