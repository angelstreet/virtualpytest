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
        
        # Proxy to host navigation execution endpoint
        execution_payload = {
            'device_id': device_id,
            'current_node_id': current_node_id,
            'image_source_url': image_source_url,
            'host_name': host_name
        }
        
        response_data, status_code = proxy_to_host(f'/host/navigation/execute/{tree_id}/{node_id}', 'POST', execution_payload, timeout=120)
        
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
            'current_node_id': current_node_id
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
                proxy_result = proxy_to_host('/host/navigation/execute', 'POST', {
                    'device_id': device_id,
                    'tree_id': tree_id,
                    'target_node_id': target_node_id,
                    'current_node_id': current_node_id,
                    'team_id': request.args.get('team_id')
                })
                
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