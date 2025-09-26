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
        team_id = request.args.get('team_id')
        host_name = request.args.get('host_name')
        
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'team_id is required'
            }), 400
            
        if not host_name:
            return jsonify({
                'success': False,
                'message': 'host_name is required'
            }), 400
        
        # Use the same cache population pattern as navigation execution
        from backend_server.src.routes.server_control_routes import populate_navigation_cache_for_control
        
        print(f"[@route:get_validation_preview] Ensuring cache for tree {tree_id} on host {host_name}")
        cache_populated = populate_navigation_cache_for_control(tree_id, team_id, host_name)
        
        if not cache_populated:
            return jsonify({
                'success': False,
                'error': 'Failed to populate unified navigation cache. Tree may need to be loaded first.'
            }), 400
        
        # Use optimal edge validation sequence with unified cache
        from  backend_server.src.lib.utils.route_utils import proxy_to_host
        
        proxy_result, _ = proxy_to_host('/host/navigation/validation_sequence', 'POST', {
            'tree_id': tree_id,
            'team_id': team_id
        })
        validation_sequence = proxy_result.get('sequence') if proxy_result and proxy_result.get('success') else None
        
        if not validation_sequence:
            return jsonify({
                'success': False,
                'error': 'No validation sequence found - tree may be empty or have no traversable edges'
            }), 400
        
        # Convert validation sequence to preview format - include cross-tree navigation details
        edges = []
        step_counter = 1
        
        for validation_step in validation_sequence:
            step_type = validation_step.get('step_type', 'unknown')
            
            # Include all validation steps EXCEPT forced transitions
            # This includes transitional_return steps which contain cross-tree navigation details
            if step_type != 'forced_transition':
                edge_info = {
                    'step_number': step_counter,
                    'from_node': validation_step['from_node_id'],
                    'to_node': validation_step['to_node_id'],
                    'from_name': validation_step['from_node_label'],
                    'to_name': validation_step['to_node_label'],
                    'selected': True,
                    'actions': validation_step.get('actions', []),
                    'has_verifications': validation_step.get('total_verifications', 0) > 0,
                    'step_type': step_type,
                    'transition_type': validation_step.get('transition_type', 'NORMAL'),
                    'is_cross_tree': validation_step.get('tree_context_change', False)
                }
                edges.append(edge_info)
                step_counter += 1
        
        print(f"[@route:get_validation_preview] Filtered {len(validation_sequence)} total steps to {len(edges)} optimized validation steps (including cross-tree navigation)")
        
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

# Removed legacy cache population functions - now using populate_navigation_cache_for_control

# Removed /status/<task_id> route - no longer needed since validation uses useScript directly

# Removed /run/<tree_id> route - validation now uses existing useScript infrastructure
# The frontend calls the validation script directly through RunTests.tsx + useScript.ts
