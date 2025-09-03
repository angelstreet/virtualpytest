"""
Metrics API Routes

This module contains the metrics API endpoints for:
- Navigation tree metrics (node and edge confidence data)
- Performance metrics aggregation
"""

from flask import Blueprint, jsonify, request

# Import database functions
from shared.lib.supabase.execution_results_db import get_raw_tree_metrics
from shared.lib.supabase.navigation_trees_db import get_tree_nodes, get_tree_edges
from shared.lib.utils.app_utils import check_supabase, get_team_id

# Create blueprint
server_metrics_bp = Blueprint('server_metrics', __name__, url_prefix='/server/metrics')

# =====================================================
# METRICS ENDPOINTS
# =====================================================

@server_metrics_bp.route('/tree/<tree_id>', methods=['GET'])
@server_metrics_bp.route('/getTreeMetrics/<tree_id>', methods=['GET'])
def get_tree_metrics_api(tree_id):
    """Get aggregated metrics for a navigation tree"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        print(f"[@route:metrics:get_tree_metrics] Fetching metrics for tree: {tree_id}, team: {team_id}")
        
        # Get all nodes and edges for the tree to build the metrics request
        nodes_result = get_tree_nodes(tree_id, team_id)
        edges_result = get_tree_edges(tree_id, team_id)
        
        if not nodes_result.get('success', False):
            return jsonify({
                'success': False,
                'error': f'Failed to fetch tree nodes: {nodes_result.get("error", "Unknown error")}'
            }), 400
            
        if not edges_result.get('success', False):
            return jsonify({
                'success': False,
                'error': f'Failed to fetch tree edges: {edges_result.get("error", "Unknown error")}'
            }), 400
        
        nodes = nodes_result.get('nodes', [])
        edges = edges_result.get('edges', [])
        
        # Extract node and edge IDs
        node_ids = [node['node_id'] for node in nodes]
        edge_ids = [edge['edge_id'] for edge in edges]
        
        print(f"[@route:metrics:get_tree_metrics] Found {len(node_ids)} nodes and {len(edge_ids)} edges")
        
        # Get raw metrics for all nodes and edges
        metrics_result = get_raw_tree_metrics(team_id, tree_id, node_ids, edge_ids)
        
        if not metrics_result.get('success', False):
            return jsonify({
                'success': False,
                'error': f'Failed to fetch metrics: {metrics_result.get("error", "Unknown error")}'
            }), 500
        
        node_metrics_list = metrics_result.get('node_metrics', [])
        edge_metrics_list = metrics_result.get('edge_metrics', [])
        
        # Calculate global confidence from raw metrics
        all_metrics = []
        
        # Process node metrics for confidence calculation
        for metric in node_metrics_list:
            if metric['total_executions'] > 0:
                confidence = calculate_confidence(metric['total_executions'], metric['success_rate'])
                all_metrics.append({'confidence': confidence, 'volume': metric['total_executions']})
        
        # Process edge metrics for confidence calculation
        for metric in edge_metrics_list:
            if metric['total_executions'] > 0:
                confidence = calculate_confidence(metric['total_executions'], metric['success_rate'])
                all_metrics.append({'confidence': confidence, 'volume': metric['total_executions']})
        
        # Calculate global confidence (weighted by volume)
        global_confidence = 0.0
        if all_metrics:
            total_weighted_confidence = sum(m['confidence'] * max(m['volume'], 1) for m in all_metrics)
            total_weight = sum(max(m['volume'], 1) for m in all_metrics)
            global_confidence = total_weighted_confidence / total_weight if total_weight > 0 else 0.0
        
        # Build confidence distribution
        high_count = sum(1 for m in all_metrics if m['confidence'] >= 0.95)
        medium_count = sum(1 for m in all_metrics if 0.90 <= m['confidence'] < 0.95)
        low_count = sum(1 for m in all_metrics if m['confidence'] < 0.90)
        untested_count = (len(node_ids) + len(edge_ids)) - len(all_metrics)
        
        # Build tree metrics summary
        tree_metrics = {
            'tree_id': tree_id,
            'total_nodes': len(node_ids),
            'total_edges': len(edge_ids),
            'nodes_with_metrics': len([m for m in node_metrics_list if m['total_executions'] > 0]),
            'edges_with_metrics': len([m for m in edge_metrics_list if m['total_executions'] > 0]),
            'global_confidence': global_confidence,
            'confidence_distribution': {
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
                'untested': untested_count,
            }
        }
        
        print(f"[@route:metrics:get_tree_metrics] Global confidence: {global_confidence:.3f}, Distribution: {tree_metrics['confidence_distribution']}")
        
        return jsonify({
            'success': True,
            'tree_metrics': tree_metrics,
            'node_metrics': node_metrics_list,
            'edge_metrics': edge_metrics_list,
        })
        
    except Exception as e:
        print(f"[@route:metrics:get_tree_metrics] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@server_metrics_bp.route('/getNodeMetrics/<node_id>/<tree_id>', methods=['GET'])
def get_node_metrics_api(node_id, tree_id):
    """Get metrics for a specific node"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        print(f"[@route:metrics:get_node_metrics] Fetching metrics for node: {node_id}, tree: {tree_id}")
        
        metrics_result = get_raw_tree_metrics(team_id, tree_id, [node_id], [])
        
        if not metrics_result.get('success', False):
            return jsonify({
                'success': False,
                'error': f'Failed to fetch node metrics: {metrics_result.get("error", "Unknown error")}'
            }), 500
        
        node_metrics = metrics_result.get('node_metrics', [])
        node_metric = node_metrics[0] if node_metrics else None
        
        return jsonify({
            'success': True,
            'node_metric': node_metric
        })
        
    except Exception as e:
        print(f"[@route:metrics:get_node_metrics] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@server_metrics_bp.route('/getEdgeMetrics/<edge_id>/<tree_id>', methods=['GET'])
def get_edge_metrics_api(edge_id, tree_id):
    """Get metrics for a specific edge"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        print(f"[@route:metrics:get_edge_metrics] Fetching metrics for edge: {edge_id}, tree: {tree_id}")
        
        metrics_result = get_raw_tree_metrics(team_id, tree_id, [], [edge_id])
        
        if not metrics_result.get('success', False):
            return jsonify({
                'success': False,
                'error': f'Failed to fetch edge metrics: {metrics_result.get("error", "Unknown error")}'
            }), 500
        
        edge_metrics = metrics_result.get('edge_metrics', [])
        edge_metric = edge_metrics[0] if edge_metrics else None
        
        return jsonify({
            'success': True,
            'edge_metric': edge_metric
        })
        
    except Exception as e:
        print(f"[@route:metrics:get_edge_metrics] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@server_metrics_bp.route('/getActionHistory/<edge_id>/<tree_id>', methods=['GET'])
def get_action_history_api(edge_id, tree_id):
    """Get execution history for actions in an edge"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        from shared.lib.supabase.execution_results_db import get_action_execution_history
        
        limit = request.args.get('limit', 100, type=int)
        
        print(f"[@route:metrics:get_action_history] Fetching history for edge: {edge_id}, tree: {tree_id}")
        
        history_result = get_action_execution_history(team_id, edge_id, tree_id, limit)
        
        return jsonify(history_result)
        
    except Exception as e:
        print(f"[@route:metrics:get_action_history] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@server_metrics_bp.route('/getVerificationHistory/<node_id>/<tree_id>', methods=['GET'])
def get_verification_history_api(node_id, tree_id):
    """Get execution history for verifications in a node"""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        from shared.lib.supabase.execution_results_db import get_verification_execution_history
        
        limit = request.args.get('limit', 100, type=int)
        
        print(f"[@route:metrics:get_verification_history] Fetching history for node: {node_id}, tree: {tree_id}")
        
        history_result = get_verification_execution_history(team_id, node_id, tree_id, limit)
        
        return jsonify(history_result)
        
    except Exception as e:
        print(f"[@route:metrics:get_verification_history] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


def calculate_confidence(total_executions: int, success_rate: float) -> float:
    """
    Calculate confidence based on volume and success rate
    Matches the frontend calculation in metricsCalculations.ts
    """
    # Volume weight: reaches 1.0 at 10 executions, caps at 1.0
    volume_weight = min(total_executions / 10.0, 1.0)
    
    # Success rate weight: direct mapping 0.0-1.0
    success_weight = success_rate
    
    # Combined confidence: 30% volume importance, 70% success importance
    confidence = (volume_weight * 0.3) + (success_weight * 0.7)
    
    return min(confidence, 1.0)  # Cap at 1.0
