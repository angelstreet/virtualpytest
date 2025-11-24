"""
Host Navigation Routes - Device Navigation Execution

This module receives navigation execution requests from the server and routes them
to the appropriate device's NavigationExecutor.
"""

import time
import threading
from flask import Blueprint, request, jsonify, current_app

# Create blueprint
host_navigation_bp = Blueprint('host_navigation', __name__, url_prefix='/host/navigation')

@host_navigation_bp.route('/execute/<tree_id>', methods=['POST'])
def navigation_execute(tree_id):
    """
    Execute navigation using device's NavigationExecutor - supports async execution
    
    Required body parameters (provide EXACTLY ONE of target_node_id or target_node_label):
    
    Option 1 - Navigate by UUID:
    {
        "target_node_id": "46854a27-57d2-43ee-bb8d-925b29b83843",
        "device_id": "device1",
        "current_node_id": "optional_uuid",
        "userinterface_name": "horizon_android_tv",
        "async_execution": true
    }
    
    Option 2 - Navigate by label:
    {
        "target_node_label": "home",
        "device_id": "device1",
        "current_node_id": "optional_uuid",
        "userinterface_name": "horizon_android_tv",
        "async_execution": true
    }
    """
    try:
        print(f"\n{'='*80}")
        print(f"[@route:host_navigation:navigation_execute] 🚀 NAVIGATION EXECUTION STARTED")
        print(f"{'='*80}")
        
        # Get request data
        data = request.get_json() or {}
        
        # Get explicit target parameters
        target_node_id = data.get('target_node_id')
        target_node_label = data.get('target_node_label')
        
        # Validate: Must provide exactly one
        if not target_node_id and not target_node_label:
            return jsonify({
                'success': False,
                'error': 'Either target_node_id or target_node_label is required in request body'
            }), 400
        
        if target_node_id and target_node_label:
            return jsonify({
                'success': False,
                'error': 'Cannot provide both target_node_id and target_node_label'
            }), 400
        
        device_id = data.get('device_id', 'device1')
        team_id = request.args.get('team_id')
        frontend_sent_position = 'current_node_id' in data
        current_node_id = data.get('current_node_id') if frontend_sent_position else None
        image_source_url = data.get('image_source_url')
        userinterface_name = data.get('userinterface_name')
        async_execution = data.get('async_execution', True)
        
        print(f"[@route:host_navigation:navigation_execute]   → Target Node ID: {target_node_id}")
        print(f"[@route:host_navigation:navigation_execute]   → Target Node Label: {target_node_label}")
        print(f"[@route:host_navigation:navigation_execute]   → Tree ID: {tree_id}")
        print(f"[@route:host_navigation:navigation_execute]   → Device ID: {device_id}")
        print(f"[@route:host_navigation:navigation_execute]   → Team ID: {team_id}")
        print(f"[@route:host_navigation:navigation_execute]   → UserInterface: {userinterface_name}")
        print(f"[@route:host_navigation:navigation_execute]   → Current Node ID: {current_node_id if frontend_sent_position else 'Not provided'}")
        print(f"[@route:host_navigation:navigation_execute]   → Frontend Sent Position: {frontend_sent_position}")
        print(f"[@route:host_navigation:navigation_execute]   → Async Execution: {async_execution}")
        print(f"{'='*80}\n")
        
        # Validate
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id is required'}), 400
            
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id is required'}), 400
        
        if not userinterface_name:
            return jsonify({'success': False, 'error': 'userinterface_name is required for reference resolution'}), 400
        
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
        
        # Always execute asynchronously to prevent HTTP timeouts
        # Generate execution ID
        import uuid
        execution_id = str(uuid.uuid4())
        
        # Store execution state
        if not hasattr(device.navigation_executor, '_executions'):
            device.navigation_executor._executions = {}
            device.navigation_executor._lock = threading.Lock()
        
        with device.navigation_executor._lock:
            device.navigation_executor._executions[execution_id] = {
                'execution_id': execution_id,
                'status': 'running',
                'tree_id': tree_id,
                'target_node_id': target_node_id,
                'target_node_label': target_node_label,
                'result': None,
                'error': None,
                'start_time': time.time(),
                'progress': 0,
                'message': 'Navigation starting...'
            }
        
        # Start execution in background thread using NavigationExecutor's own async management
        from backend_host.src.orchestrator import ExecutionOrchestrator
        
        def run_navigation():
            try:
                import asyncio
                result = asyncio.run(ExecutionOrchestrator.execute_navigation(
                    device=device,
                    tree_id=tree_id,
                    userinterface_name=userinterface_name,
                    target_node_id=target_node_id,
                    target_node_label=target_node_label,
                    current_node_id=current_node_id,
                    frontend_sent_position=frontend_sent_position,
                    image_source_url=image_source_url,
                    team_id=team_id,
                    context=None,
                ))
                
                # Update execution state with result
                with device.navigation_executor._lock:
                    device.navigation_executor._executions[execution_id]['status'] = 'completed'
                    device.navigation_executor._executions[execution_id]['result'] = result
                    device.navigation_executor._executions[execution_id]['progress'] = 100
                    device.navigation_executor._executions[execution_id]['message'] = result.get('message', 'Completed')
                    
            except Exception as e:
                print(f"[@route:host_navigation:navigation_execute] Execution error: {e}")
                import traceback
                traceback.print_exc()
                
                # Update execution state with error
                with device.navigation_executor._lock:
                    device.navigation_executor._executions[execution_id]['status'] = 'error'
                    device.navigation_executor._executions[execution_id]['error'] = str(e)
                    device.navigation_executor._executions[execution_id]['message'] = f'Navigation failed: {str(e)}'
        
        # Start thread
        thread = threading.Thread(target=run_navigation, daemon=True)
        thread.start()
        
        print(f"[@route:host_navigation:navigation_execute] Async execution started: {execution_id}")
            
        return jsonify({'success': True, 'execution_id': execution_id, 'message': 'Navigation started'})
        
    except Exception as e:
        print(f"[@route:host_navigation:navigation_execute] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Host navigation execution failed: {str(e)}'
        }), 500


@host_navigation_bp.route('/execution/<execution_id>/status', methods=['GET'])
def navigation_execution_status(execution_id):
    """Get status of async navigation execution"""
    try:
        # Get query parameters
        device_id = request.args.get('device_id', 'device1')
        
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
        
        # Get execution status from NavigationExecutor (not WebWorker)
        # Execution tracking is managed by NavigationExecutor
        status = device.navigation_executor.get_execution_status(execution_id)
        return jsonify(status)
        
    except Exception as e:
        print(f"[@route:host_navigation:execution_status] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get execution status: {str(e)}'
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
        from shared.src.lib.utils.navigation_cache import get_cached_unified_graph
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

@host_navigation_bp.route('/cache/update-edge', methods=['POST'])
def update_edge_in_cache():
    """Update a specific edge in the cached graph (incremental update - no rebuild)"""
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
        
        edge_id = edge_data.get('id')
        source_node = edge_data.get('source_node_id')
        target_node = edge_data.get('target_node_id')
        
        if not edge_id or not source_node or not target_node:
            return jsonify({
                'success': False,
                'error': 'edge must have id, source_node_id, and target_node_id'
            }), 400
        
        # Resolve to root tree (cache is always stored under root tree ID)
        from shared.src.lib.database.navigation_trees_db import _get_root_tree_id
        root_tree_id = _get_root_tree_id(tree_id, team_id)
        
        if not root_tree_id:
            root_tree_id = tree_id  # Fallback to original tree_id
        
        # Get the cached graph (silent=True to avoid logging cache misses)
        from shared.src.lib.utils.navigation_cache import get_cached_unified_graph, save_unified_cache, _unified_graphs_cache
        
        cached_graph = get_cached_unified_graph(root_tree_id, team_id, silent=True)
        
        # If no cache exists, silently skip (cache only created on take-control)
        if not cached_graph:
            return jsonify({
                'success': True,
                'message': f'No cache for tree {tree_id} - update skipped (will rebuild on next take-control)',
                'cache_exists': False
            })
        
        # Cache exists - log the update
        print(f"[@route:host_navigation:update_edge_in_cache] 🔧 Update Request:")
        print(f"  → Edge ID: {edge_id}")
        print(f"  → Tree ID (requested): {tree_id}")
        print(f"  → Team ID: {team_id}")
        print(f"  → Source: {source_node} → Target: {target_node}")
        if root_tree_id != tree_id:
            print(f"  🔗 Resolved to ROOT tree: {root_tree_id}")
        
        # Update edge in graph - COMPLETELY REPLACE attributes (not shallow merge)
        if cached_graph.has_edge(source_node, target_node):
            # Remove old edge and add with fresh data to ensure complete replacement
            cached_graph.remove_edge(source_node, target_node)
            cached_graph.add_edge(source_node, target_node, **edge_data)
            print(f"  ✅ REPLACED edge {source_node} -> {target_node} with fresh data")
        else:
            # Edge doesn't exist in graph - add it
            cached_graph.add_edge(source_node, target_node, **edge_data)
            print(f"  ✅ ADDED NEW edge {source_node} -> {target_node}")
        
        # Save updated graph to cache (use ROOT tree ID)
        save_unified_cache(root_tree_id, team_id, cached_graph)
        
        # Update in-memory graphs in all NavigationExecutor instances
        host_devices = getattr(current_app, 'host_devices', {})
        updated_devices = []
        for device_id, device in host_devices.items():
            if hasattr(device, 'navigation_executor') and device.navigation_executor:
                if device.navigation_executor.unified_graph:
                    # COMPLETELY REPLACE edge in in-memory graph
                    if device.navigation_executor.unified_graph.has_edge(source_node, target_node):
                        device.navigation_executor.unified_graph.remove_edge(source_node, target_node)
                        device.navigation_executor.unified_graph.add_edge(source_node, target_node, **edge_data)
                    else:
                        device.navigation_executor.unified_graph.add_edge(source_node, target_node, **edge_data)
                    updated_devices.append(device_id)
                    print(f"[@route:host_navigation:update_edge_in_cache] Updated edge in NavigationExecutor for device {device_id}")
                
                # Clear preview cache for this tree (previews may have changed)
                device.navigation_executor.clear_preview_cache(tree_id)
        
        print(f"[@route:host_navigation:update_edge_in_cache] ✅ Edge updated in cache (file + {len(updated_devices)} NavigationExecutor instances)")
        
        return jsonify({
            'success': True,
            'message': f'Edge {edge_id} updated in cache',
            'updated_devices': updated_devices,
            'cache_exists': True
        })
        
    except Exception as e:
        print(f"[@route:host_navigation:update_edge_in_cache] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Edge update failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/cache/update-node', methods=['POST'])
def update_node_in_cache():
    """Update a specific node in the cached graph (incremental update - no rebuild)"""
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
        if not node_id:
            return jsonify({
                'success': False,
                'error': 'node must have id'
            }), 400
        
        # Resolve to root tree (cache is always stored under root tree ID)
        from shared.src.lib.database.navigation_trees_db import _get_root_tree_id
        root_tree_id = _get_root_tree_id(tree_id, team_id)
        
        if not root_tree_id:
            root_tree_id = tree_id  # Fallback to original tree_id
        
        # Get the cached graph (silent=True to avoid logging cache misses)
        from shared.src.lib.utils.navigation_cache import get_cached_unified_graph, save_unified_cache, _unified_graphs_cache
        
        cached_graph = get_cached_unified_graph(root_tree_id, team_id, silent=True)
        
        # If no cache exists, silently skip (cache only created on take-control)
        if not cached_graph:
            return jsonify({
                'success': True,
                'message': f'No cache for tree {tree_id} - update skipped (will rebuild on next take-control)',
                'cache_exists': False
            })
        
        # Cache exists - log the update
        print(f"[@route:host_navigation:update_node_in_cache] 🔧 Update Request:")
        print(f"  → Node ID: {node_id}")
        print(f"  → Tree ID (requested): {tree_id}")
        print(f"  → Team ID: {team_id}")
        if root_tree_id != tree_id:
            print(f"  🔗 Resolved to ROOT tree: {root_tree_id}")
        
        # Update node in graph
        if cached_graph.has_node(node_id):
            # Update node data
            cached_graph.nodes[node_id].update(node_data)
            print(f"  ✅ UPDATED node {node_id}")
        else:
            # Node doesn't exist - add it
            cached_graph.add_node(node_id, **node_data)
            print(f"  ✅ ADDED NEW node {node_id}")
        
        # Save updated graph to cache (use ROOT tree ID)
        save_unified_cache(root_tree_id, team_id, cached_graph)
        
        # Update in-memory graphs in all NavigationExecutor instances
        host_devices = getattr(current_app, 'host_devices', {})
        updated_devices = []
        for device_id, device in host_devices.items():
            if hasattr(device, 'navigation_executor') and device.navigation_executor:
                if device.navigation_executor.unified_graph:
                    # Update the node in the in-memory graph
                    if device.navigation_executor.unified_graph.has_node(node_id):
                        device.navigation_executor.unified_graph.nodes[node_id].update(node_data)
                    else:
                        device.navigation_executor.unified_graph.add_node(node_id, **node_data)
                    updated_devices.append(device_id)
                    print(f"[@route:host_navigation:update_node_in_cache] Updated node in NavigationExecutor for device {device_id}")
                
                # Clear preview cache for this tree (previews may have changed)
                device.navigation_executor.clear_preview_cache(tree_id)
        
        print(f"[@route:host_navigation:update_node_in_cache] ✅ Node updated in cache (file + {len(updated_devices)} NavigationExecutor instances)")
        
        return jsonify({
            'success': True,
            'message': f'Node {node_id} updated in cache',
            'updated_devices': updated_devices,
            'cache_exists': True
        })
        
    except Exception as e:
        print(f"[@route:host_navigation:update_node_in_cache] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Node update failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/cache/clear/<tree_id>', methods=['POST'])
def clear_navigation_cache_for_tree(tree_id):
    """Clear navigation cache for a specific tree (full rebuild required)"""
    try:
        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        # 1. Clear file cache
        from shared.src.lib.utils.navigation_cache import clear_unified_cache
        clear_unified_cache(tree_id, team_id)
        
        # 2. Clear in-memory graph from all NavigationExecutor instances
        host_devices = getattr(current_app, 'host_devices', {})
        cleared_devices = []
        for device_id, device in host_devices.items():
            if hasattr(device, 'navigation_executor') and device.navigation_executor:
                # Clear the in-memory unified graph
                if device.navigation_executor.unified_graph:
                    device.navigation_executor.unified_graph = None
                    cleared_devices.append(device_id)
                    print(f"[@route:host_navigation:clear_navigation_cache_for_tree] Cleared unified_graph from NavigationExecutor for device {device_id}")
                
                # Clear preview cache for this tree
                device.navigation_executor.clear_preview_cache(tree_id)
        
        print(f"[@route:host_navigation:clear_navigation_cache_for_tree] ✅ Cache cleared for tree {tree_id} (file cache + {len(cleared_devices)} NavigationExecutor instances)")
        
        return jsonify({
            'success': True,
            'message': f'Cache cleared for tree {tree_id}',
            'cleared_devices': cleared_devices
        })
        
    except Exception as e:
        print(f"[@route:host_navigation:clear_navigation_cache_for_tree] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Cache clear failed: {str(e)}'
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
        from shared.src.lib.utils.navigation_cache import get_cached_unified_graph, populate_unified_cache, refresh_cache_timestamp
        existing_cache = get_cached_unified_graph(tree_id, team_id)
        
        if existing_cache and not force_repopulate:
            # Refresh timestamp to prevent TTL expiry between this check and next use
            refresh_cache_timestamp(tree_id, team_id)
            print(f"[@route:host_navigation:populate_navigation_cache] Cache already exists for tree {tree_id}, skipping re-population (timestamp refreshed)")
            
            # ✅ SYNC: Ensure all NavigationExecutor instances are synced with cache
            host_devices = getattr(current_app, 'host_devices', {})
            for device_id, device in host_devices.items():
                if hasattr(device, 'navigation_executor') and device.navigation_executor:
                    if not device.navigation_executor.unified_graph:
                        device.navigation_executor.unified_graph = existing_cache
                        print(f"[@route:host_navigation:populate_navigation_cache] Synced NavigationExecutor for device {device_id} with existing cache")
            
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
            
            # ✅ UPDATE: Sync all NavigationExecutor instances with the cached graph
            host_devices = getattr(current_app, 'host_devices', {})
            for device_id, device in host_devices.items():
                if hasattr(device, 'navigation_executor') and device.navigation_executor:
                    device.navigation_executor.unified_graph = unified_graph
                    print(f"[@route:host_navigation:populate_navigation_cache] Updated NavigationExecutor for device {device_id}")
            
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

@host_navigation_bp.route('/validation_sequence', methods=['POST'])
def get_validation_sequence():
    """Get optimal validation sequence for tree edges"""
    try:
        print(f"[@route:host_navigation:get_validation_sequence] Getting validation sequence")
        
        # Get request data
        data = request.get_json() or {}
        tree_id = data.get('tree_id')
        team_id = data.get('team_id')
        
        if not tree_id:
            return jsonify({
                'success': False,
                'error': 'tree_id is required'
            }), 400
            
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        print(f"[@route:host_navigation:get_validation_sequence] Tree: {tree_id}, Team: {team_id}")
        
        # Get validation sequence using pathfinding service
        from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
        
        validation_sequence = find_optimal_edge_validation_sequence(tree_id, team_id)
        
        if validation_sequence:
            print(f"[@route:host_navigation:get_validation_sequence] Generated {len(validation_sequence)} validation steps")
            return jsonify({
                'success': True,
                'sequence': validation_sequence,
                'total_steps': len(validation_sequence)
            })
        else:
            print(f"[@route:host_navigation:get_validation_sequence] No validation sequence found")
            return jsonify({
                'success': False,
                'error': 'No validation sequence found - tree may be empty or have no traversable edges'
            }), 400
            
    except Exception as e:
        print(f"[@route:host_navigation:get_validation_sequence] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'Validation sequence generation failed: {str(e)}'
        }), 500

@host_navigation_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for host navigation service"""
    return jsonify({
        'success': True,
        'message': 'Host navigation service is running'
    })

# ========================================
# BACKGROUND EXECUTION THREAD
# ========================================

def _execute_navigation_thread(
    device,
    execution_id: str,
    tree_id: str,
    userinterface_name: str,
    target_node_id: str,
    target_node_label: str,
    current_node_id: str,
    frontend_sent_position: bool,
    image_source_url: str,
    team_id: str
):
    """Execute navigation in background thread with progress tracking"""
    import sys
    import io
    import time
    
    # Capture logs for single navigation execution
    log_buffer = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    class Tee:
        def __init__(self, *streams):
            self.streams = streams
        def write(self, data):
            for stream in self.streams:
                stream.write(data)
                stream.flush()
        def flush(self):
            for stream in self.streams:
                stream.flush()
    
    try:
        # Redirect stdout/stderr to BOTH terminal and buffer
        sys.stdout = Tee(old_stdout, log_buffer)
        sys.stderr = Tee(old_stderr, log_buffer)
        
        # Update status
        with device.navigation_executor._lock:
            device.navigation_executor._executions[execution_id]['message'] = 'Executing navigation...'
            device.navigation_executor._executions[execution_id]['progress'] = 50
        
        # ✅ Execute navigation through ExecutionOrchestrator for consistent logging
        from backend_host.src.orchestrator import ExecutionOrchestrator
        import asyncio
        result = asyncio.run(ExecutionOrchestrator.execute_navigation(
            device=device,
            tree_id=tree_id,
            userinterface_name=userinterface_name,
            target_node_id=target_node_id,
            target_node_label=target_node_label,
            current_node_id=current_node_id,
            frontend_sent_position=frontend_sent_position,
            image_source_url=image_source_url,
            team_id=team_id,
            context=None,
        ))
        
        # Stop log capture and add logs to result
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        captured_logs = log_buffer.getvalue()
        if captured_logs:
            result['logs'] = captured_logs
        
        # Update with result
        with device.navigation_executor._lock:
            if result.get('success'):
                device.navigation_executor._executions[execution_id]['status'] = 'completed'
                device.navigation_executor._executions[execution_id]['result'] = result
                device.navigation_executor._executions[execution_id]['progress'] = 100
                device.navigation_executor._executions[execution_id]['message'] = 'Navigation completed'
            else:
                device.navigation_executor._executions[execution_id]['status'] = 'error'
                device.navigation_executor._executions[execution_id]['error'] = result.get('error', 'Navigation failed')
                device.navigation_executor._executions[execution_id]['result'] = result
                device.navigation_executor._executions[execution_id]['progress'] = 100
                device.navigation_executor._executions[execution_id]['message'] = 'Navigation failed'
    
    except Exception as e:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Update with error
        with device.navigation_executor._lock:
            device.navigation_executor._executions[execution_id]['status'] = 'error'
            device.navigation_executor._executions[execution_id]['error'] = str(e)
            device.navigation_executor._executions[execution_id]['progress'] = 100
            device.navigation_executor._executions[execution_id]['message'] = f'Navigation error: {str(e)}'
    finally:
        # Always restore stdout/stderr
        if sys.stdout != old_stdout:
            sys.stdout = old_stdout
        if sys.stderr != old_stderr:
            sys.stderr = old_stderr
