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
from src.lib.supabase.navigation_trees_db import (
    get_all_trees as get_all_navigation_trees_util,
    delete_tree as delete_navigation_tree,
    get_tree_metadata,
    save_tree_metadata,
    save_node,
    save_edge
)
from src.lib.supabase.userinterface_db import (
    get_all_userinterfaces, 
    get_userinterface,
    get_userinterface_by_name
)
from src.lib.utils.app_utils import check_supabase, get_team_id

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
        team_id = get_team_id()
        
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
        home_node_id = 'home-node'
        home_node_data = {
            'node_id': home_node_id,
            'label': 'Home',
            'node_type': 'screen',
            'position_x': 300,
            'position_y': 200,
            'data': {
                'type': 'screen',
                'label': 'Home',
                'description': 'Home screen - main landing page',
                'is_root': False
            },
            'verifications': []
        }
        
        home_result = save_node(tree_id, home_node_data, team_id)
        if not home_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to create home node: {home_result.get('error', 'Unknown error')}"
            }), 500
        
        print(f"[@route:create_empty_navigation_config] Created home node: {home_node_id}")
        
        # Create edge connecting entry to home
        edge_id = f"edge-{entry_node_id}-to-{home_node_id}"
        timestamp = int(datetime.now().timestamp() * 1000)
        action_set_id = f'actionset-{timestamp}'
        
        # Create properly initialized action_sets with default action set
        edge_data = {
            'edge_id': edge_id,
            'source_node_id': entry_node_id,
            'target_node_id': home_node_id,
            'label': 'Entry→Home',
            'action_sets': [
                {
                    'id': action_set_id,
                    'label': 'Entry→Home_1',
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

@server_navigation_bp.route('/cache/refresh', methods=['POST'])
def refresh_navigation_cache():
    """Proxy cache refresh request to pathfinding service"""
    try:
        print("[@route:server_navigation:refresh_navigation_cache] Proxying cache refresh request")
        
        data = request.get_json() or {}
        tree_id = data.get('tree_id')
        team_id = get_team_id()
        
        if not tree_id:
            return jsonify({
                'success': False,
                'error': 'tree_id is required for cache refresh'
            }), 400
        
        try:
            from src.lib.utils.navigation_cache import force_refresh_cache
            
            refresh_success = force_refresh_cache(tree_id, team_id)
            
            if refresh_success:
                message = f"Navigation cache refreshed for tree {tree_id}"
                return jsonify({
                    'success': True,
                    'message': message
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed to refresh navigation cache for tree {tree_id}'
                }), 500
            
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
        
