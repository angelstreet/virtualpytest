"""
Server AI Interface Generation Routes

Routes for AI-driven interface exploration and automated navigation tree generation.
Handles step-by-step exploration, image analysis, and node/edge generation.
"""

from flask import Blueprint, request, jsonify
from src.lib.utils.route_utils import proxy_to_host
from src.lib.supabase.navigation_trees_db import save_node, save_edge
from src.lib.utils.app_utils import DEFAULT_TEAM_ID
import uuid
import time

# Create blueprint
server_ai_generation_bp = Blueprint('server_ai_generation', __name__, url_prefix='/server/ai-generation')

@server_ai_generation_bp.route('/start-exploration', methods=['POST'])
def start_exploration():
    """
    Start AI interface exploration
    
    Request body:
    {
        "tree_id": "uuid",
        "host_ip": "192.168.1.100",
        "device_id": "device_uuid",
        "exploration_depth": 5,
        "start_node_id": "home_node_id"  # Optional, defaults to finding home
    }
    
    Response:
    {
        "success": true,
        "exploration_id": "uuid",
        "message": "Exploration started"
    }
    """
    try:
        print("[@route:server_ai_generation:start_exploration] Starting AI interface exploration")
        
        # Get request data
        request_data = request.get_json() or {}
        tree_id = request_data.get('tree_id')
        host_ip = request_data.get('host_ip')
        device_id = request_data.get('device_id')
        exploration_depth = request_data.get('exploration_depth', 5)
        start_node_id = request_data.get('start_node_id')
        
        # Validate required fields
        if not tree_id or not host_ip or not device_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: tree_id, host_ip, device_id'
            }), 400
        
        # Generate exploration ID
        exploration_id = str(uuid.uuid4())
        
        # Prepare host request
        host_request = {
            'exploration_id': exploration_id,
            'tree_id': tree_id,
            'device_id': device_id,
            'exploration_depth': exploration_depth,
            'start_node_id': start_node_id
        }
        
        # Proxy to host AI agent
        response_data, status_code = proxy_to_host(
            '/host/ai-generation/start-exploration', 
            'POST', 
            host_request,
            host_ip=host_ip
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_ai_generation:start_exploration] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_ai_generation_bp.route('/exploration-status/<exploration_id>', methods=['GET'])
def get_exploration_status(exploration_id):
    """
    Get current exploration status and progress
    
    Response:
    {
        "success": true,
        "exploration_id": "uuid",
        "status": "exploring|completed|failed",
        "current_step": "Analyzing home screen...",
        "progress": {
            "total_screens_found": 15,
            "screens_analyzed": 8,
            "nodes_proposed": 12,
            "edges_proposed": 15
        },
        "current_analysis": {
            "screen_name": "home",
            "elements_found": ["Live", "VOD", "Settings", "Guide"],
            "reasoning": "Found 4 main menu items on home screen"
        }
    }
    """
    try:
        print(f"[@route:server_ai_generation:get_exploration_status] Getting status for exploration {exploration_id}")
        
        # Get host IP from request args
        host_ip = request.args.get('host_ip')
        if not host_ip:
            return jsonify({
                'success': False,
                'error': 'Missing host_ip parameter'
            }), 400
        
        # Proxy to host
        response_data, status_code = proxy_to_host(
            f'/host/ai-generation/exploration-status/{exploration_id}',
            'GET',
            {},
            host_ip=host_ip
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_ai_generation:get_exploration_status] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@server_ai_generation_bp.route('/approve-generation', methods=['POST'])
def approve_generation():
    """
    Approve and generate nodes/edges in database
    
    Request body:
    {
        "exploration_id": "uuid",
        "tree_id": "uuid",
        "approved_nodes": ["node_id1", "node_id2"],
        "approved_edges": ["edge_id1", "edge_id2"]
    }
    
    Response:
    {
        "success": true,
        "nodes_created": 5,
        "edges_created": 8,
        "message": "Navigation tree updated successfully"
    }
    """
    try:
        print("[@route:server_ai_generation:approve_generation] Approving AI generated nodes/edges")
        
        # Get request data
        request_data = request.get_json() or {}
        exploration_id = request_data.get('exploration_id')
        tree_id = request_data.get('tree_id')
        approved_nodes = request_data.get('approved_nodes', [])
        approved_edges = request_data.get('approved_edges', [])
        host_ip = request_data.get('host_ip')
        
        # Validate required fields
        if not exploration_id or not tree_id or not host_ip:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: exploration_id, tree_id, host_ip'
            }), 400
        
        # Get proposed changes from host exploration status
        changes_response, changes_status = proxy_to_host(
            f'/host/ai-generation/exploration-status/{exploration_id}',
            'GET',
            {},
            host_ip=host_ip
        )
        
        if changes_status != 200 or not changes_response.get('success'):
            return jsonify({
                'success': False,
                'error': 'Failed to get exploration status from host'
            }), 400
        
        proposed_nodes = changes_response.get('proposed_nodes', [])
        proposed_edges = changes_response.get('proposed_edges', [])
        
        nodes_created = 0
        edges_created = 0
        
        # Create approved nodes using existing save_node function
        for node_data in proposed_nodes:
            if node_data['id'] in approved_nodes:
                try:
                    # Use existing save_node function from navigation_trees_db
                    result = save_node(tree_id, node_data, DEFAULT_TEAM_ID)
                    if result.get('success'):
                        nodes_created += 1
                        print(f"[@route:server_ai_generation:approve_generation] Created node: {node_data['id']}")
                    else:
                        print(f"[@route:server_ai_generation:approve_generation] Failed to create node {node_data['id']}: {result.get('error')}")
                        
                except Exception as e:
                    print(f"[@route:server_ai_generation:approve_generation] Error creating node {node_data['id']}: {str(e)}")
        
        # Create approved edges using existing save_edge function
        for edge_data in proposed_edges:
            if edge_data['id'] in approved_edges:
                try:
                    # Use existing save_edge function from navigation_trees_db
                    result = save_edge(tree_id, edge_data, DEFAULT_TEAM_ID)
                    if result.get('success'):
                        edges_created += 1
                        print(f"[@route:server_ai_generation:approve_generation] Created edge: {edge_data['id']}")
                    else:
                        print(f"[@route:server_ai_generation:approve_generation] Failed to create edge {edge_data['id']}: {result.get('error')}")
                        
                except Exception as e:
                    print(f"[@route:server_ai_generation:approve_generation] Error creating edge {edge_data['id']}: {str(e)}")
        
        return jsonify({
            'success': True,
            'nodes_created': nodes_created,
            'edges_created': edges_created,
            'message': f'Successfully created {nodes_created} nodes and {edges_created} edges'
        }), 200
        
    except Exception as e:
        print(f"[@route:server_ai_generation:approve_generation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server_ai_generation_bp.route('/cancel-exploration', methods=['POST'])
def cancel_exploration():
    """
    Cancel ongoing exploration
    
    Request body:
    {
        "exploration_id": "uuid",
        "host_ip": "192.168.1.100"
    }
    """
    try:
        print("[@route:server_ai_generation:cancel_exploration] Cancelling AI exploration")
        
        # Get request data
        request_data = request.get_json() or {}
        exploration_id = request_data.get('exploration_id')
        host_ip = request_data.get('host_ip')
        
        if not exploration_id or not host_ip:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: exploration_id, host_ip'
            }), 400
        
        # Proxy to host
        response_data, status_code = proxy_to_host(
            '/host/ai-generation/cancel-exploration',
            'POST',
            {'exploration_id': exploration_id},
            host_ip=host_ip
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        print(f"[@route:server_ai_generation:cancel_exploration] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
