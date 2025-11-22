"""
Host AI Exploration Routes - Thin HTTP layer for AI-driven tree exploration

Architecture:
- Thin routes that delegate to device.exploration_executor
- No business logic in routes
- No global session dict (state is device-bound)
- Consistent with host_*_routes.py naming convention
"""

from flask import Blueprint, request, jsonify, current_app
from shared.src.lib.database.navigation_trees_db import (
    get_tree_nodes,
    get_tree_edges,
    delete_node,
    delete_edge,
    save_nodes_batch,
    save_edges_batch,
    get_supabase
)

host_ai_exploration_bp = Blueprint('host_ai_exploration', __name__, url_prefix='/host/ai-generation')


@host_ai_exploration_bp.route('/cleanup-temp', methods=['POST'])
def cleanup_temp():
    """
    Clean up all _temp nodes and edges before starting new exploration
    
    Request body: {'tree_id': 'uuid'}
    Query params: 'team_id'
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        tree_id = data.get('tree_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        if not tree_id:
            return jsonify({'success': False, 'error': 'tree_id required'}), 400
        
        print(f"[@route:ai_generation:cleanup_temp] Cleaning up _temp for tree: {tree_id}")
        
        # ✅ SIMPLE: Delete ALL edges except entry-to-home, then delete all non-home nodes
        edges_result = get_tree_edges(tree_id, team_id)
        
        print(f"[@route:ai_generation:cleanup_temp] Edges query result: success={edges_result.get('success')}, count={len(edges_result.get('edges', []))}")
        
        edges_deleted = 0
        
        if edges_result.get('success') and edges_result.get('edges'):
            print(f"[@route:ai_generation:cleanup_temp] Processing {len(edges_result['edges'])} edges...")
            for edge in edges_result['edges']:
                edge_id = edge.get('edge_id', '')
                source = edge.get('source_node_id', '')
                target = edge.get('target_node_id', '')
                
                # Keep ONLY the entry-to-home edge, delete everything else
                is_entry_to_home = (
                    'entry' in edge_id.lower() and 
                    target.lower() == 'home'
                )
                
                if not is_entry_to_home:
                    print(f"  🗑️  Deleting edge: {edge_id} ({source} → {target})")
                    delete_result = delete_edge(tree_id, edge_id, team_id)
                    if delete_result.get('success'):
                        edges_deleted += 1
                        print(f"  ✅ Deleted edge: {edge_id}")
                    else:
                        print(f"  ❌ Failed to delete edge: {edge_id}, error: {delete_result.get('error')}")
                else:
                    print(f"  ⏭️  Keeping entry edge: {edge_id}")
        else:
            print(f"[@route:ai_generation:cleanup_temp] No edges found or query failed")
        
        # Now get nodes
        nodes_result = get_tree_nodes(tree_id, team_id)
        
        print(f"[@route:ai_generation:cleanup_temp] Found {len(nodes_result.get('nodes', []))} nodes")
        
        nodes_deleted = 0
        
        # Delete ALL nodes except entry-node and home
        if nodes_result.get('success') and nodes_result.get('nodes'):
            for node in nodes_result['nodes']:
                node_id = node.get('node_id', '')
                if node_id.lower() not in ['entry-node', 'home']:
                    delete_result = delete_node(tree_id, node_id, team_id)
                    if delete_result.get('success'):
                        nodes_deleted += 1
                        print(f"  🗑️  Deleted node: {node_id}")
                else:
                    print(f"  ⏭️  Keeping protected node: {node_id}")
        
        print(f"[@route:ai_generation:cleanup_temp] Complete: {nodes_deleted} nodes, {edges_deleted} edges deleted")
        
        # ✅ Clear and REBUILD cache after cleanup (don't wait for next take-control)
        # This ensures start-exploration works immediately after cleanup
        from shared.src.lib.database.navigation_trees_db import invalidate_navigation_cache_for_tree, get_complete_tree_hierarchy
        from shared.src.lib.utils.navigation_cache import populate_unified_cache
        
        # 1. Clear old cache
        invalidate_navigation_cache_for_tree(tree_id, team_id)
        print(f"[@route:ai_generation:cleanup_temp] ✅ Cache invalidated for tree {tree_id}")
        
        # 2. Rebuild cache immediately
        hierarchy_result = get_complete_tree_hierarchy(tree_id, team_id)
        if hierarchy_result and hierarchy_result.get('all_trees_data'):
            unified_graph = populate_unified_cache(tree_id, team_id, hierarchy_result['all_trees_data'])
            if unified_graph:
                print(f"[@route:ai_generation:cleanup_temp] ✅ Cache rebuilt: {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
                
                # 3. Update all NavigationExecutor instances
                from flask import current_app
                host_devices = getattr(current_app, 'host_devices', {})
                for device_id, device in host_devices.items():
                    if hasattr(device, 'navigation_executor') and device.navigation_executor:
                        device.navigation_executor.unified_graph = unified_graph
                        print(f"[@route:ai_generation:cleanup_temp] Updated NavigationExecutor for device {device_id}")
            else:
                print(f"[@route:ai_generation:cleanup_temp] ⚠️ Failed to rebuild cache (empty graph)")
        else:
            print(f"[@route:ai_generation:cleanup_temp] ⚠️ No hierarchy data to rebuild cache")
        
        return jsonify({
            'success': True,
            'nodes_deleted': nodes_deleted,
            'edges_deleted': edges_deleted
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:cleanup_temp] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/start-exploration', methods=['POST'])
def start_exploration():
    """
    Start AI exploration - delegates to device.exploration_executor
    
    Note: Exploration depth is FIXED at 2 levels (main items + sub-items)
    
    Request body:
    {
        'tree_id': 'uuid',
        'device_id': 'device1',
        'userinterface_name': 'horizon_android_mobile',
        'original_prompt': 'Automate sauce demo' (optional, for v2.0 context)
    }
    Query params: team_id (auto-added)
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        
        # Validate params
        tree_id = data.get('tree_id')
        device_id = data.get('device_id', 'device1')
        userinterface_name = data.get('userinterface_name')
        original_prompt = data.get('original_prompt', '')
        start_node = data.get('start_node', 'home')  # NEW: Defaults to 'home'
        
        # 🔍 DEBUG LOG: Show what's being started
        print(f"[@route:ai_generation:start_exploration] Starting exploration:")
        print(f"  tree_id: {tree_id}")
        print(f"  device_id: {device_id}")
        print(f"  userinterface_name: {userinterface_name}")
        print(f"  start_node: {start_node}")
        print(f"  available devices: {list(current_app.host_devices.keys())}")
        
        if not team_id:
            print(f"[@route:ai_generation:start_exploration] ❌ Missing team_id")
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        if not tree_id:
            print(f"[@route:ai_generation:start_exploration] ❌ Missing tree_id")
            return jsonify({'success': False, 'error': 'tree_id required'}), 400
        if not userinterface_name:
            print(f"[@route:ai_generation:start_exploration] ❌ Missing userinterface_name")
            return jsonify({'success': False, 'error': 'userinterface_name required'}), 400
        
        # Get device
        if device_id not in current_app.host_devices:
            print(f"[@route:ai_generation:start_exploration] ❌ Device '{device_id}' not found")
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        print(f"[@route:ai_generation:start_exploration] ✅ Starting exploration on device '{device_id}'")
        
        # Delegate to exploration executor
        result = device.exploration_executor.start_exploration(
            tree_id=tree_id,
            userinterface_name=userinterface_name,
            team_id=team_id,
            original_prompt=original_prompt,
            start_node=start_node  # NEW: Pass start_node
        )
        
        print(f"[@route:ai_generation:start_exploration] Result: success={result.get('success', False)}, exploration_id={result.get('exploration_id', 'N/A')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:start_exploration] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/init', methods=['POST'])
def init_exploration():
    """
    Phase 0: Detect device strategy (dump_ui available? click vs DPAD?)
    
    Request body:
    {
        'device_id': 'device1'
    }
    """
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor
        result = device.exploration_executor.execute_phase0()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:init] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/next', methods=['POST'])
def next_item():
    """
    Phase 2: Create and test ONE edge incrementally
    
    Request body:
    {
        'device_id': 'device1'
    }
    
    Returns:
    {
        'success': bool,
        'item': str,
        'has_more_items': bool,
        'progress': {'current_item': int, 'total_items': int}
    }
    """
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor
        result = device.exploration_executor.execute_phase2_next_item()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:next] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/exploration-status/<exploration_id>', methods=['GET'])
def exploration_status(exploration_id):
    """
    Get current exploration status - delegates to device.exploration_executor
    
    Note: exploration_id is currently ignored (device has only one active exploration)
    """
    try:
        # Get device_id from query params (frontend should send this)
        device_id_requested = request.args.get('device_id')
        device_id = device_id_requested or 'device1'
        
        # 🔍 DEBUG LOG: Show what's being checked
        print(f"[@route:ai_generation:exploration_status] Checking exploration status:")
        print(f"  exploration_id: {exploration_id}")
        print(f"  device_id requested: {device_id_requested}")
        print(f"  device_id used: {device_id}")
        print(f"  available devices: {list(current_app.host_devices.keys())}")
        
        if device_id not in current_app.host_devices:
            print(f"[@route:ai_generation:exploration_status] ❌ Device '{device_id}' not found")
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # 🔍 DEBUG LOG: Show if device has active exploration
        has_exploration = device.exploration_executor.current_exploration_id is not None
        print(f"[@route:ai_generation:exploration_status] Device '{device_id}' has active exploration: {has_exploration}")
        if has_exploration:
            print(f"  Active exploration ID: {device.exploration_executor.current_exploration_id}")
        
        # Delegate to exploration executor
        result = device.exploration_executor.get_exploration_status()
        
        # 🔍 DEBUG LOG: Show result
        print(f"[@route:ai_generation:exploration_status] Result: {result.get('status', 'unknown')} (success={result.get('success', False)})")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:exploration_status] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/continue-exploration', methods=['POST'])
def continue_exploration():
    """
    Phase 2a: Create nodes and edges structure for selected items - delegates to device.exploration_executor
    
    Body: {
        'exploration_id': 'abc123',
        'selected_items': ['item1', 'item2'] (optional - if omitted, creates all)
    }
    Query params: team_id
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        device_id = data.get('device_id', 'device1')
        selected_items = data.get('selected_items')  # ✅ Get user selection
        
        print(f"[@route:ai_generation:continue_exploration] Received selected_items: {selected_items}")
        print(f"[@route:ai_generation:continue_exploration] Type: {type(selected_items)}, Length: {len(selected_items) if selected_items else 0}")
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor with selected items
        result = device.exploration_executor.continue_exploration(
            team_id=team_id,
            selected_items=selected_items
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:continue_exploration] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/start-validation', methods=['POST'])
def start_validation():
    """
    Phase 2b: Start validation process - delegates to device.exploration_executor
    
    Body: {'exploration_id': 'abc123'}
    """
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor
        result = device.exploration_executor.start_validation()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:start_validation] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/validate-next-item', methods=['POST'])
def validate_next_item():
    """
    Phase 2b: Validate ONE edge - delegates to device.exploration_executor
    
    Body: {'exploration_id': 'abc123'}
    Query params: team_id
    """
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor
        result = device.exploration_executor.validate_next_item()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:validate_next_item] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/start-node-verification', methods=['POST'])
def start_node_verification():
    """
    Phase 2c: Analyze dumps and suggest node verifications
    
    Request body:
    {
        'device_id': 'device1'
    }
    """
    try:
        print(f"[@route:ai_generation:start_node_verification] START")
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        
        print(f"[@route:ai_generation:start_node_verification] device_id: {device_id}")
        print(f"[@route:ai_generation:start_node_verification] Available devices: {list(current_app.host_devices.keys())}")
        
        if device_id not in current_app.host_devices:
            print(f"[@route:ai_generation:start_node_verification] Device {device_id} not found!")
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        print(f"[@route:ai_generation:start_node_verification] Calling device.exploration_executor.start_node_verification()")
        result = device.exploration_executor.start_node_verification()
        
        print(f"[@route:ai_generation:start_node_verification] Result: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:start_node_verification] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/approve-node-verifications', methods=['POST'])
def approve_node_verifications():
    """
    Phase 2c: Approve and save node verifications
    
    Request body:
    {
        'device_id': 'device1',
        'approved_verifications': [
            {
                'node_id': 'search',
                'verification': {...},
                'screenshot_url': '...'
            }
        ]
    }
    Query params: team_id
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        device_id = data.get('device_id', 'device1')
        approved_verifications = data.get('approved_verifications', [])
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        result = device.exploration_executor.approve_node_verifications(
            approved_verifications=approved_verifications,
            team_id=team_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:approve_node_verifications] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/finalize-structure', methods=['POST'])
def finalize_structure():
    """
    Finalize structure: Remove _temp from labels only (non-destructive)
    Node IDs and edge IDs are already clean - only labels have _temp for visual distinction.
    Works standalone without active exploration session.
    
    Body: {'tree_id': 'uuid'} (optional: 'device_id' for backwards compatibility)
    Query params: team_id
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        tree_id = data.get('tree_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        if not tree_id:
            return jsonify({'success': False, 'error': 'tree_id required'}), 400
        
        print(f"[@route:ai_generation:finalize_structure] Removing _temp from labels for tree: {tree_id}")
        
        # Get all nodes and edges from tree
        from shared.src.lib.database.navigation_trees_db import (
            get_tree_nodes, 
            get_tree_edges,
            get_supabase
        )
        
        nodes_result = get_tree_nodes(tree_id, team_id)
        edges_result = get_tree_edges(tree_id, team_id)
        
        if not nodes_result.get('success') or not edges_result.get('success'):
            return jsonify({'success': False, 'error': 'Failed to get tree data'}), 400
        
        nodes = nodes_result.get('nodes', [])
        edges = edges_result.get('edges', [])
        
        nodes_updated = 0
        edges_updated = 0
        
        # Prepare Batch Updates
        nodes_to_update = []
        edges_to_update = []

        # Update node labels: remove _temp suffix
        for node in nodes:
            label = node.get('label', '')
            if label.endswith('_temp'):
                new_label = label.replace('_temp', '')
                node['label'] = new_label
                nodes_to_update.append(node)
                print(f"  Queueing node label update: {label} → {new_label}")

        # Update edge labels: remove _temp suffix
        for edge in edges:
            label = edge.get('label', '')
            if label and '_temp' in label:
                new_label = label.replace('_temp', '')
                edge['label'] = new_label
                edges_to_update.append(edge)
                print(f"  Queueing edge label update: {label} → {new_label}")
        
        # Execute Batch Updates
        if nodes_to_update:
            print(f"[@route:ai_generation:finalize_structure] Batch updating {len(nodes_to_update)} nodes...")
            res = save_nodes_batch(tree_id, nodes_to_update, team_id)
            if res['success']:
                nodes_updated = len(nodes_to_update)
                print(f"  ✅ Successfully updated {nodes_updated} nodes")
            else:
                print(f"  ❌ Failed to update nodes: {res.get('error')}")
                return jsonify({'success': False, 'error': f"Node update failed: {res.get('error')}"}), 500

        if edges_to_update:
            print(f"[@route:ai_generation:finalize_structure] Batch updating {len(edges_to_update)} edges...")
            res = save_edges_batch(tree_id, edges_to_update, team_id)
            if res['success']:
                edges_updated = len(edges_to_update)
                print(f"  ✅ Successfully updated {edges_updated} edges")
            else:
                print(f"  ❌ Failed to update edges: {res.get('error')}")
                return jsonify({'success': False, 'error': f"Edge update failed: {res.get('error')}"}), 500
        
        # Invalidate cache after all changes
        from shared.src.lib.database.navigation_trees_db import invalidate_navigation_cache_for_tree
        invalidate_navigation_cache_for_tree(tree_id, team_id)
        
        print(f"[@route:ai_generation:finalize_structure] Complete: {nodes_updated} nodes, {edges_updated} edges updated")
        
        return jsonify({
            'success': True,
            'nodes_renamed': nodes_updated,  # Keep old key name for frontend compatibility
            'edges_renamed': edges_updated,  # Keep old key name for frontend compatibility
            'message': f'Finalized: {nodes_updated} node labels and {edges_updated} edge labels updated'
        })
            
    except Exception as e:
        print(f"[@route:ai_generation:finalize_structure] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/approve-generation', methods=['POST'])
def approve_generation():
    """
    Approve generation - rename all _temp nodes/edges - delegates to device.exploration_executor
    
    Body:
    {
        'exploration_id': 'uuid',
        'tree_id': 'uuid',
        'approved_nodes': ['home_temp', 'settings_temp'],
        'approved_edges': ['edge_home_to_settings_temp']
    }
    Query params: team_id
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        device_id = data.get('device_id', 'device1')
        
        tree_id = data.get('tree_id')
        approved_nodes = data.get('approved_nodes', [])
        approved_edges = data.get('approved_edges', [])
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor
        result = device.exploration_executor.approve_generation(
            tree_id=tree_id,
            approved_nodes=approved_nodes,
            approved_edges=approved_edges,
            team_id=team_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:approve_generation] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/cancel-exploration', methods=['POST'])
def cancel_exploration():
    """
    Cancel exploration - delete all _temp nodes/edges - delegates to device.exploration_executor
    
    Body: {'exploration_id': 'uuid'}
    Query params: team_id
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        device_id = data.get('device_id', 'device1')
        
        tree_id = data.get('tree_id')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor
        result = device.exploration_executor.cancel_exploration(
            tree_id=tree_id,
            team_id=team_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:cancel_exploration] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
