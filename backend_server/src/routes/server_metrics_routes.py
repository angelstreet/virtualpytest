"""
Navigation Metrics API Routes

This module implements the metrics API endpoints as specified in:
docs/architecture/navigation_metrics.md

Provides clean, architecture-compliant endpoints for:
- Tree metrics (aggregated node and edge metrics)
- Individual node metrics
- Individual edge metrics  
- Action execution history
- Verification execution history

No legacy code or backward compatibility - follows the clean embedded architecture.
"""

from flask import Blueprint, jsonify, request
from shared.lib.supabase.navigation_metrics_db import (
    get_tree_metrics,
    get_action_execution_history,
    get_verification_execution_history
)
from shared.lib.supabase.navigation_trees_db import get_tree_nodes, get_tree_edges
from shared.lib.utils.app_utils import check_supabase, get_team_id

# Create blueprint
server_metrics_bp = Blueprint('server_metrics', __name__, url_prefix='/server/metrics')

# =====================================================
# TREE METRICS ENDPOINTS
# =====================================================

@server_metrics_bp.route('/tree/<tree_id>', methods=['GET'])
def get_tree_metrics_api(tree_id):
    """
    Get aggregated metrics for all nodes and edges in a navigation tree.
    
    Returns metrics in the format expected by the frontend:
    {
        success: true,
        nodes: {node_id: {volume, success_rate, avg_execution_time}},
        edges: {edge_id: {volume, success_rate, avg_execution_time}}
    }
    """
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        print(f"[@route:metrics:get_tree_metrics] Fetching metrics for tree: {tree_id}, team: {team_id}")
        
        # Get all nodes and edges for the tree
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
        
        # Get metrics using the proper navigation metrics function
        metrics = get_tree_metrics(team_id, node_ids, edge_ids)
        
        return jsonify({
            'success': True,
            'nodes': metrics['nodes'],
            'edges': metrics['edges']
        })
        
    except Exception as e:
        print(f"[@route:metrics:get_tree_metrics] ERROR: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


# =====================================================
# INDIVIDUAL METRICS ENDPOINTS
# =====================================================

@server_metrics_bp.route('/node/<node_id>/<tree_id>', methods=['GET'])
def get_node_metrics_api(node_id, tree_id):
    """Get metrics for a specific node."""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        print(f"[@route:metrics:get_node_metrics] Fetching metrics for node: {node_id}, tree: {tree_id}")
        
        # Get metrics for single node
        metrics = get_tree_metrics(team_id, [node_id], [])
        node_metric = metrics['nodes'].get(node_id)
        
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


@server_metrics_bp.route('/edge/<edge_id>/<tree_id>', methods=['GET'])
def get_edge_metrics_api(edge_id, tree_id):
    """Get metrics for a specific edge."""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
        print(f"[@route:metrics:get_edge_metrics] Fetching metrics for edge: {edge_id}, tree: {tree_id}")
        
        # Get metrics for single edge
        metrics = get_tree_metrics(team_id, [], [edge_id])
        edge_metric = metrics['edges'].get(edge_id)
        
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


# =====================================================
# EXECUTION HISTORY ENDPOINTS
# =====================================================

@server_metrics_bp.route('/history/actions/<edge_id>/<tree_id>', methods=['GET'])
def get_action_history_api(edge_id, tree_id):
    """Get execution history for actions in an edge."""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
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


@server_metrics_bp.route('/history/verifications/<node_id>/<tree_id>', methods=['GET'])
def get_verification_history_api(node_id, tree_id):
    """Get execution history for verifications in a node."""
    error = check_supabase()
    if error:
        return error
        
    team_id = get_team_id()
    
    try:
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
