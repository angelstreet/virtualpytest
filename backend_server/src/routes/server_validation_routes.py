"""
Validation Routes - Reuses NavigationExecutor API for sequential edge testing
"""

from typing import List
from flask import Blueprint, request, jsonify

from shared.lib.utils.navigation_cache import get_cached_graph
from shared.lib.utils.app_utils import get_team_id
from backend_core.src.services.navigation.navigation_execution import NavigationExecutor


def transform_script_results_to_validation_format(step_results, report_url, tree_id):
    """Transform ScriptExecutor step_results to frontend ValidationResults format"""
    
    # Calculate summary stats
    total_edges = len(step_results)
    successful_edges = sum(1 for step in step_results if step.get('success', False))
    failed_edges = total_edges - successful_edges
    
    # Calculate overall health
    health_percentage = (successful_edges / total_edges * 100) if total_edges > 0 else 0
    if health_percentage >= 90:
        overall_health = 'excellent'
    elif health_percentage >= 75:
        overall_health = 'good'
    elif health_percentage >= 50:
        overall_health = 'fair'
    else:
        overall_health = 'poor'
    
    # Transform each step to edgeResults format
    edge_results = []
    for step in step_results:
        edge_result = {
            'from': step.get('from_node', ''),
            'to': step.get('to_node', ''),
            'fromName': step.get('from_node', ''),
            'toName': step.get('to_node', ''),
            'success': step.get('success', False),
            'skipped': False,
            'retryAttempts': 0,
            'errors': [step.get('error', '')] if not step.get('success', False) and step.get('error') else [],
            'actionsExecuted': len(step.get('actions', [])),
            'totalActions': len(step.get('actions', [])),
            'executionTime': step.get('execution_time_ms', 0),
            'verificationResults': step.get('verification_results', [])
        }
        edge_results.append(edge_result)
    
    return {
        'treeId': tree_id,
        'summary': {
            'totalNodes': successful_edges,
            'totalEdges': total_edges,
            'validNodes': successful_edges,
            'errorNodes': failed_edges,
            'skippedEdges': 0,
            'overallHealth': overall_health,
            'executionTime': sum(step.get('execution_time_ms', 0) for step in step_results)
        },
        'nodeResults': [],
        'edgeResults': edge_results,
        'reportUrl': report_url
    }


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
        
        # Execute validation in background thread using ScriptExecutor
        import threading
        def execute_async():
            try:
                print(f"[@route:run_validation] Starting ScriptExecutor validation for task {task_id}")
                
                # Import ScriptExecutor and related functions
                import sys
                import os
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
                
                from shared.lib.utils.script_framework import ScriptExecutor
                from backend_core.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
                from shared.lib.utils.action_utils import execute_navigation_with_verifications
                from shared.lib.utils.report_utils import generate_and_upload_script_report
                
                # Create mock args for ScriptExecutor
                class MockArgs:
                    def __init__(self):
                        self.userinterface_name = f'tree_{tree_id}'
                        self.host = None
                        self.device = device_id
                
                # Setup ScriptExecutor
                executor = ScriptExecutor("validation", "Web interface validation")
                context = executor.setup_execution_context(MockArgs(), enable_db_tracking=True)
                
                # Manually set context values
                context.host = type('Host', (), host)()  # Convert dict to object
                context.team_id = team_id
                context.tree_id = tree_id
                
                # Load selected device
                from shared.lib.utils.host_utils import get_device_by_id
                context.selected_device = get_device_by_id(device_id)
                
                # Get validation sequence
                validation_sequence = find_optimal_edge_validation_sequence(tree_id, team_id)
                
                if not validation_sequence:
                    raise Exception("No validation sequence found")
                
                print(f"[@route:run_validation] Found {len(validation_sequence)} validation steps")
                
                # Custom step handler for validation
                def validation_step_handler(context, step, step_num):
                    try:
                        result = execute_navigation_with_verifications(
                            context.host, context.selected_device, step, context.team_id, 
                            context.tree_id, context.script_result_id, 'validation'
                        )
                        return result
                    except Exception as e:
                        print(f"⚠️ [validation] Step handler error: {e}")
                        return {
                            'success': False,
                            'error': f'Step handler exception: {str(e)}',
                            'verification_results': []
                        }
                
                # Execute validation sequence (no progress callbacks - simple execution)
                success = executor.execute_navigation_sequence(
                    context, validation_sequence, validation_step_handler
                )
                
                # Generate rich HTML report using existing infrastructure
                report_result = generate_and_upload_script_report(
                    script_name="validation",
                    device_info={
                        'device_name': context.selected_device.device_name if context.selected_device else 'Unknown Device',
                        'device_model': context.selected_device.device_model if context.selected_device else 'Unknown Model',
                        'device_id': device_id or 'web_interface'
                    },
                    host_info={
                        'host_name': host.get('host_name', 'Unknown Host')
                    },
                    execution_time=context.get_execution_time_ms(),
                    success=success,
                    step_results=context.step_results,
                    screenshot_paths=context.screenshot_paths,
                    error_message=context.error_message,
                    userinterface_name=f'tree_{tree_id}',
                    execution_summary=f"Web interface validation completed with {len(context.step_results)} steps"
                )
                
                report_url = report_result.get('report_url', '') if report_result.get('success') else ''
                
                # Transform ScriptExecutor results to frontend format
                validation_results = transform_script_results_to_validation_format(
                    context.step_results, report_url, tree_id
                )
                
                task_manager.complete_task(task_id, validation_results)
                print(f"[@route:run_validation] Validation completed successfully with report: {report_url}")
                
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
