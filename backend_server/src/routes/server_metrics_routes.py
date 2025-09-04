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
        
        # Add confidence calculation to each metric (backend responsibility)
        def calculate_confidence(volume: int, success_rate: float) -> float:
            """Calculate confidence as specified in architecture"""
            # Volume weight: reaches 1.0 at 10 executions, caps at 1.0
            volume_weight = min(volume / 10.0, 1.0)
            # Success rate weight: direct mapping 0.0-1.0
            success_weight = success_rate
            # Combined confidence: 30% volume importance, 70% success importance
            confidence = (volume_weight * 0.3) + (success_weight * 0.7)
            return min(confidence, 1.0)
        
        # Process nodes with confidence
        processed_nodes = {}
        for node_id, node_metric in metrics['nodes'].items():
            confidence = calculate_confidence(node_metric['volume'], node_metric['success_rate'])
            processed_nodes[node_id] = {
                'volume': node_metric['volume'],
                'success_rate': node_metric['success_rate'],
                'avg_execution_time': node_metric['avg_execution_time'],
                'confidence': confidence
            }
        
        # Process edges with confidence  
        processed_edges = {}
        for edge_id, edge_metric in metrics['edges'].items():
            confidence = calculate_confidence(edge_metric['volume'], edge_metric['success_rate'])
            processed_edges[edge_id] = {
                'volume': edge_metric['volume'],
                'success_rate': edge_metric['success_rate'],
                'avg_execution_time': edge_metric['avg_execution_time'],
                'confidence': confidence
            }
        
        # Calculate global confidence for toast system
        all_confidences = []
        all_volumes = []
        
        for node_metric in processed_nodes.values():
            if node_metric['volume'] > 0:
                all_confidences.append(node_metric['confidence'])
                all_volumes.append(node_metric['volume'])
        
        for edge_metric in processed_edges.values():
            if edge_metric['volume'] > 0:
                all_confidences.append(edge_metric['confidence'])
                all_volumes.append(edge_metric['volume'])
        
        # Calculate weighted global confidence
        global_confidence = 0.0
        if all_confidences:
            total_weighted = sum(conf * max(vol, 1) for conf, vol in zip(all_confidences, all_volumes))
            total_weight = sum(max(vol, 1) for vol in all_volumes)
            global_confidence = total_weighted / total_weight if total_weight > 0 else 0.0
        
        # Count confidence distribution for toast system
        high_count = sum(1 for conf in all_confidences if conf >= 0.7)
        medium_count = sum(1 for conf in all_confidences if 0.49 <= conf < 0.7)
        low_count = sum(1 for conf in all_confidences if conf < 0.49)
        untested_count = (len(node_ids) + len(edge_ids)) - len(all_confidences)
        
        return jsonify({
            'success': True,
            'nodes': processed_nodes,
            'edges': processed_edges,
            'global_confidence': global_confidence,
            'confidence_distribution': {
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
                'untested': untested_count
            }
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
