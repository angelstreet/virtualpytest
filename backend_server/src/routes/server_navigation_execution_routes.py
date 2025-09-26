"""
Server Navigation Execution Routes

This module provides API endpoints for navigation execution using the standardized
NavigationExecutor class. These endpoints can be used by:
- Frontend components (via fetch calls)
- Python scripts (via direct API calls)
- External integrations

The endpoints use the same NavigationExecutor that can be used directly in Python code.
"""

from flask import Blueprint, request, jsonify
from shared.src.lib.utils.app_utils import get_team_id
from  backend_server.src.lib.utils.route_utils import proxy_to_host, proxy_to_host_with_params

# Create blueprint
server_navigation_execution_bp = Blueprint('server_navigation_execution', __name__, url_prefix='/server/navigation')


@server_navigation_execution_bp.route('/execute/<tree_id>/<node_id>', methods=['POST'])
def execute_navigation(tree_id, node_id):
    """
    Execute navigation using standardized NavigationExecutor
    
    Expected JSON payload:
    {
        "host": {"host_name": "...", "device_model": "...", ...},
        "device_id": "optional_device_id",
        "team_id": "optional_team_id",
        "current_node_id": "optional_current_node",
        "image_source_url": "optional_image_source"
    }
    """
    try:
        print(f"[@route:navigation_execution:execute_navigation] Executing navigation to {node_id} in tree {tree_id}")
        
        data = request.get_json() or {}
        host_name = data.get('host_name')
        device_id = data.get('device_id')
        team_id = request.args.get('team_id')
        current_node_id = data.get('current_node_id')
        image_source_url = data.get('image_source_url')
        
        # Validate required parameters
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name is required'
            }), 400
        
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        # Ensure unified cache is populated before execution (same as preview/validation routes)
        print(f"[@route:navigation_execution:execute_navigation] Checking unified cache for tree {tree_id}, team_id {team_id}")
        print(f"[@route:navigation_execution:execute_navigation] About to call ensure_unified_cache_populated...")
        cache_populated = ensure_unified_cache_populated(tree_id, team_id, host_name)
        print(f"[@route:navigation_execution:execute_navigation] Cache population result: {cache_populated}")
        if not cache_populated:
            print(f"[@route:navigation_execution:execute_navigation] Cache population FAILED for tree {tree_id}")
            return jsonify({
                'success': False,
                'error': 'Failed to populate unified navigation cache. Tree may need to be loaded first.'
            }), 400
        print(f"[@route:navigation_execution:execute_navigation] Cache population SUCCESS, proceeding with execution")
        
        # Proxy to host navigation execution endpoint
        execution_payload = {
            'device_id': device_id,
            'current_node_id': current_node_id,
            'image_source_url': image_source_url,
            'host_name': host_name
        }
        
        # Pass team_id as query parameter to host
        query_params = {}
        if team_id:
            query_params['team_id'] = team_id
        
        response_data, status_code = proxy_to_host_with_params(f'/host/navigation/execute/{tree_id}/{node_id}', 'POST', execution_payload, query_params, timeout=120)
        
        print(f"[@route:navigation_execution:execute_navigation] Navigation result: success={response_data.get('success')}")
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:navigation_execution:execute_navigation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Navigation execution error: {str(e)}'
        }), 500


@server_navigation_execution_bp.route('/preview/<tree_id>/<node_id>', methods=['GET'])
def get_navigation_preview_with_executor(tree_id, node_id):
    """
    Get navigation preview using NavigationExecutor
    
    Query parameters:
    - current_node_id: optional current node for pathfinding
    - host_name: required host name for executor initialization
    - device_id: optional device ID
    - team_id: optional team ID
    """
    try:
        print(f"[@route:navigation_execution:get_navigation_preview_with_executor] Getting preview for navigation to {node_id} in tree {tree_id}")
        
        current_node_id = request.args.get('current_node_id')
        host_name = request.args.get('host_name')
        device_id = request.args.get('device_id')
        team_id = request.args.get('team_id')
        
        # Validate required parameters
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name query parameter is required'
            }), 400
        
        # Create minimal host configuration for preview
        host = {'host_name': host_name}
        
        # Proxy to host navigation preview endpoint
        query_params = {
            'device_id': device_id,
            'current_node_id': current_node_id,
            'team_id': team_id
        }
        
        # Remove None values
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response_data, status_code = proxy_to_host_with_params(f'/host/navigation/preview/{tree_id}/{node_id}', 'GET', None, query_params, timeout=60)
        
        print(f"[@route:navigation_execution:get_navigation_preview_with_executor] Preview result: success={response_data.get('success')}")
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:navigation_execution:get_navigation_preview_with_executor] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Navigation preview error: {str(e)}'
        }), 500


@server_navigation_execution_bp.route('/batch-execute', methods=['POST'])
def batch_execute_navigation():
    """
    Execute multiple navigation operations in sequence
    
    Expected JSON payload:
    {
        "host": {"host_name": "...", "device_model": "...", ...},
        "device_id": "optional_device_id",
        "team_id": "optional_team_id",
        "navigations": [
            {
                "tree_id": "tree1",
                "target_node_id": "node1",
                "current_node_id": "optional_current"
            },
            {
                "tree_id": "tree2", 
                "target_node_id": "node2"
            }
        ]
    }
    """
    try:
        print(f"[@route:navigation_execution:batch_execute_navigation] Starting batch navigation execution")
        
        data = request.get_json() or {}
        host_name = data.get('host_name')
        device_id = data.get('device_id')
        team_id = request.args.get('team_id')
        navigations = data.get('navigations', [])
        
        # Validate required parameters
        if not host_name:
            return jsonify({
                'success': False,
                'error': 'host_name is required'
            }), 400
        
        if not navigations:
            return jsonify({
                'success': False,
                'error': 'navigations array is required'
            }), 400
        
        if not team_id:
            return jsonify({
                'success': False,
                'error': 'team_id is required'
            }), 400
        
        # Ensure unified cache is populated for all trees in batch
        unique_tree_ids = list(set(nav.get('tree_id') for nav in navigations if nav.get('tree_id')))
        for tree_id in unique_tree_ids:
            print(f"[@route:navigation_execution:batch_execute_navigation] Ensuring cache for tree {tree_id}")
            cache_populated = ensure_unified_cache_populated(tree_id, team_id, host_name)
            if not cache_populated:
                return jsonify({
                    'success': False,
                    'error': f'Failed to populate unified navigation cache for tree {tree_id}. Tree may need to be loaded first.'
                }), 400
        
        # Proxy navigation execution to host
        from  backend_server.src.lib.utils.route_utils import proxy_to_host
        from shared.src.lib.utils.app_utils import get_team_id
        
        results = []
        successful_navigations = 0
        
        for i, navigation in enumerate(navigations):
            tree_id = navigation.get('tree_id')
            target_node_id = navigation.get('target_node_id')
            current_node_id = navigation.get('current_node_id')
            
            if not tree_id or not target_node_id:
                result = {
                    'success': False,
                    'error': 'tree_id and target_node_id are required for each navigation',
                    'navigation_index': i
                }
            else:
                print(f"[@route:navigation_execution:batch_execute_navigation] Executing navigation {i+1}/{len(navigations)}: {tree_id} -> {target_node_id}")
                
                # Proxy to host for actual navigation execution
                batch_payload = {
                    'device_id': device_id,
                    'current_node_id': current_node_id,
                    'host_name': host_name
                }
                
                # Pass team_id as query parameter to host
                batch_query_params = {}
                if team_id:
                    batch_query_params['team_id'] = team_id
                
                proxy_result, proxy_status = proxy_to_host_with_params(f'/host/navigation/execute/{tree_id}/{target_node_id}', 'POST', batch_payload, batch_query_params, timeout=120)
                
                result = proxy_result if proxy_result else {'success': False, 'error': 'Host proxy failed'}
                result['navigation_index'] = i
                
                if result.get('success'):
                    successful_navigations += 1
            
            results.append(result)
            
            # If navigation failed and we want to stop on first failure
            if not result.get('success'):
                print(f"[@route:navigation_execution:batch_execute_navigation] Navigation {i+1} failed, continuing with next...")
        
        overall_success = successful_navigations == len(navigations)
        
        print(f"[@route:navigation_execution:batch_execute_navigation] Batch completed: {successful_navigations}/{len(navigations)} successful")
        
        return jsonify({
            'success': overall_success,
            'total_navigations': len(navigations),
            'successful_navigations': successful_navigations,
            'failed_navigations': len(navigations) - successful_navigations,
            'results': results,
            'message': f'Batch navigation completed: {successful_navigations}/{len(navigations)} successful'
        })
        
    except Exception as e:
        print(f"[@route:navigation_execution:batch_execute_navigation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Batch navigation execution error: {str(e)}'
        }), 500


def ensure_unified_cache_populated(tree_id: str, team_id: str, host_name: str) -> bool:
    """
    Ensure unified cache is populated for the given tree on the specified host
    Uses the same pattern as validation routes
    """
    try:
        print(f"[@route:ensure_unified_cache_populated] Starting cache population for tree {tree_id} on host {host_name}, team_id {team_id}")
        
        # Check if cache already exists on host (avoid re-population)
        from  backend_server.src.lib.utils.route_utils import proxy_to_host_with_params
        print(f"[@route:ensure_unified_cache_populated] Checking if cache exists...")
        cache_check_result, check_status = proxy_to_host_with_params(f'/host/navigation/cache/check/{tree_id}', 'GET', None, {'team_id': team_id}, timeout=30)
        print(f"[@route:ensure_unified_cache_populated] Cache check result: {cache_check_result}, status: {check_status}")
        
        if cache_check_result and cache_check_result.get('success') and cache_check_result.get('exists'):
            print(f"[@route:ensure_unified_cache_populated] Cache already exists for tree {tree_id}, skipping population")
            return True
        
        # Get complete tree hierarchy from database
        from shared.src.lib.supabase.navigation_trees_db import get_complete_tree_hierarchy, get_full_tree
        
        # Try to load complete hierarchy first (for nested trees)
        hierarchy_result = get_complete_tree_hierarchy(tree_id, team_id)
        
        if hierarchy_result.get('success'):
            all_trees_data = hierarchy_result.get('all_trees_data', [])
            print(f"[@route:ensure_unified_cache_populated] Loaded tree hierarchy: {len(all_trees_data)} trees")
        else:
            print(f"[@route:ensure_unified_cache_populated] get_complete_tree_hierarchy failed: {hierarchy_result.get('error')}")
            
            # Fallback: Load single tree
            tree_result = get_full_tree(tree_id, team_id)
            if not tree_result.get('success'):
                print(f"[@route:ensure_unified_cache_populated] Failed to load tree {tree_id}: {tree_result.get('error', 'Unknown error')}")
                return False
            
            # Format as single-tree hierarchy for unified cache
            all_trees_data = [{
                'tree_id': tree_id,
                'tree_info': {
                    'name': tree_result['tree'].get('name', 'Unknown'),
                    'is_root_tree': True,
                    'tree_depth': 0,
                    'parent_tree_id': None,
                    'parent_node_id': None
                },
                'nodes': tree_result['nodes'],
                'edges': tree_result['edges']
            }]
            print(f"[@route:ensure_unified_cache_populated] Loaded single tree as fallback")
        
        if not all_trees_data:
            print(f"[@route:ensure_unified_cache_populated] ERROR: No tree data found for tree {tree_id}")
            return False
        
        # Populate cache on host
        print(f"[@route:ensure_unified_cache_populated] Calling host cache populate endpoint...")
        populate_result, populate_status = proxy_to_host_with_params(f'/host/navigation/cache/populate/{tree_id}', 'POST', {
            'team_id': team_id,
            'all_trees_data': all_trees_data,
            'force_repopulate': False
        }, {}, timeout=60)
        print(f"[@route:ensure_unified_cache_populated] Cache populate result: {populate_result}, status: {populate_status}")
        
        if populate_result and populate_result.get('success'):
            print(f"[@route:ensure_unified_cache_populated] Successfully populated cache: {populate_result.get('nodes_count', 0)} nodes")
            return True
        else:
            print(f"[@route:ensure_unified_cache_populated] Cache population failed: {populate_result.get('error', 'Unknown error') if populate_result else 'No response'}")
            return False
            
    except Exception as e:
        print(f"[@route:ensure_unified_cache_populated] Error: {str(e)}")
        return False 