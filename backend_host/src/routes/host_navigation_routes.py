"""
Host Navigation Routes - Device Navigation Execution

This module receives navigation execution requests from the server and routes them
to the appropriate device's NavigationExecutor.
"""

from flask import Blueprint, request, jsonify, current_app

# Create blueprint
host_navigation_bp = Blueprint('host_navigation', __name__, url_prefix='/host/navigation')

@host_navigation_bp.route('/execute/<tree_id>/<target_node_id>', methods=['POST'])
def navigation_execute(tree_id, target_node_id):
    """Execute navigation using device's NavigationExecutor"""
    try:
        print(f"[@route:host_navigation:navigation_execute] Starting navigation to {target_node_id}")
        
        # Get request data
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        current_node_id = data.get('current_node_id')
        image_source_url = data.get('image_source_url')
        
        print(f"[@route:host_navigation:navigation_execute] Device: {device_id}, Tree: {tree_id}, Team: {team_id}")
        
        # Validate
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
            
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False, 
                'error': f'Device {device_id} not found in host'
            }), 404
        
        device = host_devices[device_id]
        
        # Check if device has navigation_executor
        if not hasattr(device, 'navigation_executor') or not device.navigation_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have NavigationExecutor initialized'
            }), 500
        
        # Execute navigation using device's NavigationExecutor
        result = device.navigation_executor.execute_navigation(
            tree_id=tree_id,
            target_node_id=target_node_id,
            current_node_id=current_node_id,
            image_source_url=image_source_url,
            team_id=team_id
        )
        
        print(f"[@route:host_navigation:navigation_execute] Execution completed: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_navigation:navigation_execute] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host navigation execution failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/preview/<tree_id>/<target_node_id>', methods=['GET'])
def navigation_preview(tree_id, target_node_id):
    """Get navigation preview using device's NavigationExecutor"""
    try:
        print(f"[@route:host_navigation:navigation_preview] Getting preview for {target_node_id}")
        
        # Get query parameters
        device_id = request.args.get('device_id', 'device1')
        current_node_id = request.args.get('current_node_id')
        team_id = request.args.get('team_id')
        
        print(f"[@route:host_navigation:navigation_preview] Device: {device_id}, Tree: {tree_id}, Team: {team_id}")
        
        # Validate team_id for auto-loading capability
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id query parameter is required for navigation preview'
            }), 400
        
        # Get host device registry from app context
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False, 
                'error': f'Device {device_id} not found in host'
            }), 404
        
        device = host_devices[device_id]
        
        # Check if device has navigation_executor
        if not hasattr(device, 'navigation_executor') or not device.navigation_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have NavigationExecutor initialized'
            }), 500
        
        # Get navigation preview using device's NavigationExecutor with team_id for auto-loading
        result = device.navigation_executor.get_navigation_preview(
            tree_id=tree_id,
            target_node_id=target_node_id,
            current_node_id=current_node_id,
            team_id=team_id
        )
        
        print(f"[@route:host_navigation:navigation_preview] Preview completed: success={result.get('success')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:host_navigation:navigation_preview] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host navigation preview failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/cache/check/<tree_id>', methods=['GET'])
def check_navigation_cache(tree_id):
    """Check if unified navigation cache exists for tree"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        # Check if cache exists
        from backend_host.src.lib.utils.navigation_cache import get_cached_unified_graph
        cached_graph = get_cached_unified_graph(tree_id, team_id)
        
        exists = cached_graph is not None
        nodes_count = len(cached_graph.nodes) if cached_graph else 0
        edges_count = len(cached_graph.edges) if cached_graph else 0
        
        print(f"[@route:host_navigation:check_navigation_cache] Cache exists for tree {tree_id}: {exists}")
        
        return jsonify({
            'success': True,
            'exists': exists,
            'nodes_count': nodes_count,
            'edges_count': edges_count
        })
        
    except Exception as e:
        print(f"[@route:host_navigation:check_navigation_cache] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Cache check failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/cache/populate/<tree_id>', methods=['POST'])
def populate_navigation_cache(tree_id):
    """Populate unified navigation cache in host process (with duplicate protection)"""
    try:
        print(f"[@route:host_navigation:populate_navigation_cache] Populating cache for tree: {tree_id}")
        
        # Get request data
        data = request.get_json() or {}
        team_id = request.args.get('team_id') or data.get('team_id')
        all_trees_data = data.get('all_trees_data', [])
        force_repopulate = data.get('force_repopulate', False)
        
        # Validate required parameters
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
            
        if not all_trees_data:
            return jsonify({
                'success': False,
                'error': 'all_trees_data is required'
            }), 400
        
        # Check if cache already exists (protection against re-population)
        from backend_host.src.lib.utils.navigation_cache import get_cached_unified_graph, populate_unified_cache
        existing_cache = get_cached_unified_graph(tree_id, team_id)
        
        if existing_cache and not force_repopulate:
            print(f"[@route:host_navigation:populate_navigation_cache] Cache already exists for tree {tree_id}, skipping re-population")
            return jsonify({
                'success': True,
                'nodes_count': len(existing_cache.nodes),
                'edges_count': len(existing_cache.edges),
                'message': f'Cache already exists for tree {tree_id}',
                'already_cached': True
            })
        
        # Populate unified cache in host process
        unified_graph = populate_unified_cache(tree_id, team_id, all_trees_data)
        
        if unified_graph:
            action = 'Re-populated' if force_repopulate else 'Populated'
            print(f"[@route:host_navigation:populate_navigation_cache] {action} cache: {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
            return jsonify({
                'success': True,
                'nodes_count': len(unified_graph.nodes),
                'edges_count': len(unified_graph.edges),
                'message': f'Cache {action.lower()} for tree {tree_id}',
                'repopulated': force_repopulate
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to populate unified cache'
            }), 500
            
    except Exception as e:
        print(f"[@route:host_navigation:populate_navigation_cache] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Cache population failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for host navigation service"""
    return jsonify({
        'success': True,
        'message': 'Host navigation service is running'
    })
