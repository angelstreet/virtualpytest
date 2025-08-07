"""
Validation Routes - Reuses NavigationExecutor API for sequential edge testing
"""

from typing import List
from flask import Blueprint, request, jsonify

from shared.lib.utils.navigation_cache import get_cached_graph
from shared.lib.utils.app_utils import get_team_id


# Removed transform_script_results_to_validation_format since we now execute the script directly


# Create blueprint
server_validation_bp = Blueprint('server_validation', __name__, url_prefix='/server/validation')

@server_validation_bp.route('/preview/<tree_id>', methods=['GET'])
def get_validation_preview(tree_id: str):
    """
    Get validation preview - shows which edges will be validated using optimal depth-first sequence
    Uses unified cache system - requires proper cache population
    """
    try:
        team_id = get_team_id()
        
        # Ensure unified cache is populated for this tree
        from shared.lib.utils.navigation_cache import get_cached_unified_graph
        unified_graph = get_cached_unified_graph(tree_id, team_id)
        
        if not unified_graph:
            print(f"[@route:get_validation_preview] No unified cache found for tree {tree_id}, populating...")
            
            # Populate unified cache for this tree using the new architecture
            success = ensure_unified_cache_populated(tree_id, team_id)
            if not success:
                return jsonify({
                    'success': False,
                    'error': 'Failed to populate unified navigation cache. Tree may need to be loaded first.'
                }), 400
        
        # Use optimal edge validation sequence with unified cache
        from backend_core.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
        
        validation_sequence = find_optimal_edge_validation_sequence(tree_id, team_id)
        
        if not validation_sequence:
            return jsonify({
                'success': False,
                'error': 'No validation sequence found - tree may be empty or have no traversable edges'
            }), 400
        
        # Convert validation sequence to preview format
        edges = []
        for validation_step in validation_sequence:
            edge_info = {
                'step_number': validation_step['step_number'],
                'from_node': validation_step['from_node_id'],
                'to_node': validation_step['to_node_id'],
                'from_name': validation_step['from_node_label'],
                'to_name': validation_step['to_node_label'],
                'selected': True,
                'actions': validation_step.get('actions', []),
                'has_verifications': validation_step.get('total_verifications', 0) > 0,
                'step_type': validation_step.get('step_type', 'unknown')
            }
            edges.append(edge_info)
        
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


def ensure_unified_cache_populated(tree_id: str, team_id: str) -> bool:
    """
    Ensure unified cache is populated for the given tree
    Uses the new normalized database architecture
    """
    try:
        print(f"[@route:ensure_unified_cache_populated] Populating unified cache for tree {tree_id}")
        
        # Get complete tree hierarchy from new normalized tables
        from shared.lib.supabase.navigation_trees_db import get_complete_tree_hierarchy
        hierarchy_result = get_complete_tree_hierarchy(tree_id, team_id)
        
        if not hierarchy_result.get('success'):
            print(f"[@route:ensure_unified_cache_populated] get_complete_tree_hierarchy failed: {hierarchy_result.get('error')}")
            
            # Fallback: Try to load single tree if hierarchy fails
            print(f"[@route:ensure_unified_cache_populated] Attempting single tree load as fallback...")
            return ensure_single_tree_cache_populated(tree_id, team_id)
        
        all_trees_data = hierarchy_result.get('all_trees_data', [])
        if not all_trees_data:
            print(f"[@route:ensure_unified_cache_populated] No tree data found, attempting single tree load...")
            return ensure_single_tree_cache_populated(tree_id, team_id)
        
        # Populate unified cache
        from shared.lib.utils.navigation_cache import populate_unified_cache
        unified_graph = populate_unified_cache(tree_id, team_id, all_trees_data)
        
        if unified_graph:
            print(f"[@route:ensure_unified_cache_populated] Successfully populated unified cache: {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
            return True
        else:
            print(f"[@route:ensure_unified_cache_populated] Failed to create unified graph, trying single tree...")
            return ensure_single_tree_cache_populated(tree_id, team_id)
        
    except Exception as e:
        print(f"[@route:ensure_unified_cache_populated] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"[@route:ensure_unified_cache_populated] Falling back to single tree cache...")
        return ensure_single_tree_cache_populated(tree_id, team_id)


def ensure_single_tree_cache_populated(tree_id: str, team_id: str) -> bool:
    """
    Populate unified cache with single tree data (for trees without nested structure)
    """
    try:
        print(f"[@route:ensure_single_tree_cache_populated] Loading single tree for unified cache: {tree_id}")
        
        # Get single tree data
        from shared.lib.supabase.navigation_trees_db import get_full_tree
        tree_result = get_full_tree(tree_id, team_id)
        
        if not tree_result.get('success'):
            print(f"[@route:ensure_single_tree_cache_populated] Failed to load tree: {tree_result.get('error')}")
            return False
        
        # Format as single-tree hierarchy for unified cache
        single_tree_data = [{
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
        
        # Populate unified cache with single tree
        from shared.lib.utils.navigation_cache import populate_unified_cache
        unified_graph = populate_unified_cache(tree_id, team_id, single_tree_data)
        
        if unified_graph:
            print(f"[@route:ensure_single_tree_cache_populated] Successfully populated single-tree unified cache: {len(unified_graph.nodes)} nodes, {len(unified_graph.edges)} edges")
            return True
        else:
            print(f"[@route:ensure_single_tree_cache_populated] Failed to create single-tree unified graph")
            return False
            
    except Exception as e:
        print(f"[@route:ensure_single_tree_cache_populated] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@server_validation_bp.route('/status/<task_id>', methods=['GET'])
def get_validation_status(task_id):
    """Get status of an async validation task"""
    try:
        from shared.lib.utils.task_manager import task_manager
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        return jsonify({
            'success': True,
            'task': task
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_validation_bp.route('/run/<tree_id>', methods=['POST'])
def run_validation(tree_id: str):
    """Run validation asynchronously with progress tracking"""
    try:
        print(f"[@route:run_validation] Starting async validation for tree: {tree_id}")
        
        data = request.get_json() or {}
        host = data.get('host')
        device_id = data.get('device_id')
        edges_to_validate = data.get('edges_to_validate', [])
        
        if not host:
            return jsonify({
                'success': False,
                'error': 'Host configuration is required'
            }), 400
        
        if not edges_to_validate:
            return jsonify({
                'success': False,
                'error': 'No edges provided for validation'
            }), 400
        
        print(f"[@route:run_validation] Host: {host.get('host_name')}, Device: {device_id}")
        print(f"[@route:run_validation] Validating {len(edges_to_validate)} edges")
        
        # Create task for async validation
        from shared.lib.utils.task_manager import task_manager
        task_id = task_manager.create_task('validation', {
            'tree_id': tree_id,
            'host': host,
            'device_id': device_id,
            'edges_to_validate': edges_to_validate
        })
        
        # No progress tracking needed - simple execution
        
        # Get team_id BEFORE starting background thread (while in Flask context)
        team_id = get_team_id()
        
        # Execute validation script on HOST (exactly like RunTests does)
        import threading
        def execute_async():
            try:
                print(f"[@route:run_validation] Starting validation script execution for task {task_id}")
                
                # Get host info from registry (same as RunTests)
                from shared.lib.utils.host_utils import get_host_manager
                host_manager = get_host_manager()
                host_name = host.get('host_name')
                host_info = host_manager.get_host(host_name)
                
                if not host_info:
                    task_manager.complete_task(task_id, {}, error=f'Host not found: {host_name}')
                    return
                
                # Build parameters for validation script like RunTests does
                userinterface_name = f'tree_{tree_id}'
                parameters = f"{userinterface_name} --host {host_name} --device {device_id}"
                
                print(f"[@route:run_validation] Executing validation script with parameters: {parameters}")
                
                # Forward to HOST for execution (exactly like RunTests does)
                from shared.lib.utils.build_url_utils import buildHostUrl
                import requests
                
                # Prepare request payload (same as RunTests)
                payload = {
                    'script_name': 'validation',
                    'device_id': device_id,
                    'parameters': parameters,
                    'task_id': task_id
                }
                
                # Build host URL and make request
                host_url = buildHostUrl(host_info, '/host/script/execute')
                
                response = requests.post(
                    host_url,
                    json=payload,
                    timeout=300  # 5 minutes timeout for validation
                )
                
                result = response.json()
                
                if response.status_code in [200, 202] and result.get('success'):
                    print(f"[@route:run_validation] Validation script completed successfully")
                    
                    # Parse the script output to extract validation results
                    # The validation.py script generates its own report via ScriptExecutor
                    stdout = result.get('stdout', '')
                    
                    # Extract report URL from stdout if available
                    report_url = ""
                    for line in stdout.split('\n'):
                        if 'Report uploaded:' in line or 'report.html' in line:
                            # Extract URL from the line
                            parts = line.split()
                            for part in parts:
                                if 'report.html' in part:
                                    report_url = part
                                    break
                    
                    # Create simple validation results for frontend
                    # Since the script handles all the validation logic internally
                    validation_results = {
                        'treeId': tree_id,
                        'summary': {
                            'totalNodes': 1,
                            'totalEdges': 1,
                            'validNodes': 1 if result.get('success') else 0,
                            'errorNodes': 0 if not result.get('success') else 1,
                            'skippedEdges': 0,
                            'overallHealth': 'excellent' if result.get('success') else 'poor',
                            'executionTime': result.get('execution_time_ms', 0)
                        },
                        'nodeResults': [],
                        'edgeResults': [
                            {
                                'from': 'validation',
                                'to': 'complete',
                                'fromName': 'Validation Start',
                                'toName': 'Validation Complete',
                                'success': result.get('success', False),
                                'skipped': False,
                                'retryAttempts': 0,
                                'errors': [result.get('stderr', '')] if not result.get('success') else [],
                                'actionsExecuted': 1,
                                'totalActions': 1,
                                'executionTime': result.get('execution_time_ms', 0),
                                'verificationResults': []
                            }
                        ],
                        'reportUrl': report_url
                    }
                    
                    task_manager.complete_task(task_id, validation_results)
                    print(f"[@route:run_validation] Validation completed with report: {report_url}")
                    
                else:
                    error_msg = result.get('error') or result.get('stderr') or 'Host validation execution failed'
                    print(f"[@route:run_validation] Validation script failed: {error_msg}")
                    task_manager.complete_task(task_id, {}, error=error_msg)
                
            except Exception as e:
                print(f"[@route:run_validation] Background validation error for task {task_id}: {e}")
                import traceback
                traceback.print_exc()
                task_manager.complete_task(task_id, {}, error=str(e))
        
        threading.Thread(target=execute_async, daemon=True).start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': 'started',
            'message': f'Validation started for tree {tree_id}'
        }), 202
        
    except Exception as e:
        print(f"[@route:run_validation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Validation failed: {str(e)}'
        }), 500
