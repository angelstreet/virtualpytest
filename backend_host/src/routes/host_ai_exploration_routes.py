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
    delete_edge
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
        
        # Get all nodes and edges
        nodes_result = get_tree_nodes(tree_id, team_id)
        edges_result = get_tree_edges(tree_id, team_id)
        
        nodes_deleted = 0
        edges_deleted = 0
        
        # Delete edges with _temp
        if edges_result.get('success') and edges_result.get('edges'):
            for edge in edges_result['edges']:
                edge_id = edge.get('edge_id', '')
                if '_temp' in edge_id:
                    delete_result = delete_edge(tree_id, edge_id, team_id)
                    if delete_result.get('success'):
                        edges_deleted += 1
                        print(f"  🗑️  Deleted edge: {edge_id}")
        
        # Delete nodes ending with _temp
        if nodes_result.get('success') and nodes_result.get('nodes'):
            for node in nodes_result['nodes']:
                node_id = node.get('node_id', '')
                if node_id.endswith('_temp'):
                    delete_result = delete_node(tree_id, node_id, team_id)
                    if delete_result.get('success'):
                        nodes_deleted += 1
                        print(f"  🗑️  Deleted node: {node_id}")
        
        print(f"[@route:ai_generation:cleanup_temp] Complete: {nodes_deleted} nodes, {edges_deleted} edges deleted")
        
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
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        if not tree_id:
            return jsonify({'success': False, 'error': 'tree_id required'}), 400
        if not userinterface_name:
            return jsonify({'success': False, 'error': 'userinterface_name required'}), 400
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor (depth is fixed at 2 levels)
        result = device.exploration_executor.start_exploration(
            tree_id=tree_id,
            userinterface_name=userinterface_name,
            team_id=team_id,
            original_prompt=original_prompt
        )
        
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
        device_id = request.args.get('device_id', 'device1')
        
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor
        result = device.exploration_executor.get_exploration_status()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[@route:ai_generation:exploration_status] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_exploration_bp.route('/continue-exploration', methods=['POST'])
def continue_exploration():
    """
    Phase 2a: Create all nodes and edges structure - delegates to device.exploration_executor
    
    Body: {'exploration_id': 'abc123'}
    Query params: team_id
    """
    try:
        data = request.get_json() or {}
        team_id = request.args.get('team_id')
        device_id = data.get('device_id', 'device1')
        
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required'}), 400
        
        # Get device
        if device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        device = current_app.host_devices[device_id]
        
        # Delegate to exploration executor
        result = device.exploration_executor.continue_exploration(team_id=team_id)
        
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


@host_ai_exploration_bp.route('/finalize-structure', methods=['POST'])
def finalize_structure():
    """
    Finalize structure: Rename all _temp nodes/edges to permanent
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
        
        print(f"[@route:ai_generation:finalize_structure] Renaming _temp nodes/edges for tree: {tree_id}")
        
        # Get all nodes and edges from tree
        from shared.src.lib.database.navigation_trees_db import get_tree_nodes, get_tree_edges, save_node, save_edge, delete_node, delete_edge
        
        nodes_result = get_tree_nodes(tree_id, team_id)
        edges_result = get_tree_edges(tree_id, team_id)
        
        if not nodes_result.get('success') or not edges_result.get('success'):
            return jsonify({'success': False, 'error': 'Failed to get tree data'}), 400
        
        nodes = nodes_result.get('nodes', [])
        edges = edges_result.get('edges', [])
        
        nodes_renamed = 0
        edges_renamed = 0
        
        # Rename nodes: delete old, create new without _temp suffix
        for node in nodes:
            node_id = node.get('node_id', '')
            if node_id.endswith('_temp'):
                new_node_id = node_id.replace('_temp', '')
                
                # Update node_id in the data
                node['node_id'] = new_node_id
                
                # Create new node with updated id
                result = save_node(tree_id, node, team_id)
                if result.get('success'):
                    # Delete old _temp node
                    delete_node(tree_id, node_id, team_id)
                    nodes_renamed += 1
                    print(f"  ✅ Renamed node: {node_id} → {new_node_id}")
                else:
                    print(f"  ❌ Failed to rename node: {node_id}")
        
        # Rename edges: delete old, create new without _temp suffix
        for edge in edges:
            edge_id = edge.get('edge_id', '')
            source = edge.get('source_node_id', '')
            target = edge.get('target_node_id', '')
            
            if '_temp' in edge_id or '_temp' in source or '_temp' in target:
                new_edge_id = edge_id.replace('_temp', '')
                new_source = source.replace('_temp', '')
                new_target = target.replace('_temp', '')
                
                # Update edge data
                edge['edge_id'] = new_edge_id
                edge['source_node_id'] = new_source
                edge['target_node_id'] = new_target
                
                # Create new edge with updated ids
                result = save_edge(tree_id, edge, team_id)
                if result.get('success'):
                    # Delete old _temp edge
                    delete_edge(tree_id, edge_id, team_id)
                    edges_renamed += 1
                    print(f"  ✅ Renamed edge: {edge_id} → {new_edge_id}")
                else:
                    print(f"  ❌ Failed to rename edge: {edge_id}")
        
        print(f"[@route:ai_generation:finalize_structure] Complete: {nodes_renamed} nodes, {edges_renamed} edges renamed")
        
        return jsonify({
            'success': True,
            'nodes_renamed': nodes_renamed,
            'edges_renamed': edges_renamed,
            'message': f'Finalized: {nodes_renamed} nodes and {edges_renamed} edges renamed'
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
