"""
AI Generation Routes - HTTP endpoints for AI-driven tree exploration
Auto-proxied from /server/ai-generation/* to /host/ai-generation/*
"""

from flask import Blueprint, request, jsonify
import threading
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict

from services.ai_exploration import ExplorationEngine
from shared.src.lib.database.navigation_trees_db import (
    save_node,
    save_edge,
    get_node_by_id,
    get_edge_by_id,
    delete_node,
    delete_tree_cascade,
    get_tree_nodes,
    get_tree_edges
)

ai_generation_bp = Blueprint('ai_generation', __name__, url_prefix='/host/ai-generation')

# In-memory exploration state (minimalist!)
_exploration_sessions: Dict[str, Dict] = {}
_exploration_locks = {}


@ai_generation_bp.route('/start-exploration', methods=['POST'])
def start_exploration():
    """
    Start AI exploration in background thread
    
    Request body:
    {
        'tree_id': 'uuid',
        'host_ip': '192.168.1.100',  # or 'host_name': 'sunri-pi1'
        'device_id': 'device1',
        'exploration_depth': 5,
        'userinterface_name': 'horizon_android_mobile'
    }
    Query params (auto-added by buildServerUrl):
        'team_id': 'team_1'
    
    Response:
    {
        'success': True,
        'exploration_id': 'uuid',
        'message': 'Exploration started'
    }
    """
    try:
        from flask import current_app
        
        data = request.get_json() or {}
        team_id = request.args.get('team_id')  # Auto-added by buildServerUrl
        
        # Extract parameters from body
        tree_id = data.get('tree_id')
        device_id = data.get('device_id', 'device1')
        host_name = data.get('host_name') or data.get('host_ip')  # Support both
        userinterface_name = data.get('userinterface_name')
        exploration_depth = data.get('exploration_depth', 5)
        
        # Validate required params
        if not team_id:
            return jsonify({'success': False, 'error': 'team_id required in query parameters'}), 400
        if not tree_id:
            return jsonify({'success': False, 'error': 'tree_id is required'}), 400
        if not host_name:
            return jsonify({'success': False, 'error': 'host_name or host_ip is required'}), 400
        if not userinterface_name:
            return jsonify({'success': False, 'error': 'userinterface_name is required'}), 400
        
        # Get device info from registry (like testcase routes do)
        if not hasattr(current_app, 'host_devices') or device_id not in current_app.host_devices:
            return jsonify({'success': False, 'error': f'Device {device_id} not found in registry'}), 404
        
        device = current_app.host_devices[device_id]
        device_name = device.device_name
        device_model_name = device.device_model
        
        # Generate exploration ID
        exploration_id = str(uuid4())
        
        print(f"[@route:ai_generation:start_exploration] Starting exploration {exploration_id}")
        print(f"  Tree: {tree_id}")
        print(f"  Device: {device_model_name} ({device_id})")
        print(f"  Host: {host_name}")
        print(f"  UI: {userinterface_name}")
        print(f"  Depth: {exploration_depth}")
        
        # Initialize exploration state
        _exploration_sessions[exploration_id] = {
            'exploration_id': exploration_id,
            'tree_id': tree_id,
            'team_id': team_id,
            'device_id': device_id,
            'device_model_name': device_model_name,
            'userinterface_name': userinterface_name,
            'status': 'starting',
            'current_step': 'Initializing exploration...',
            'progress': {
                'total_screens_found': 0,
                'screens_analyzed': 0,
                'nodes_proposed': 0,
                'edges_proposed': 0
            },
            'current_analysis': {
                'screen_name': '',
                'elements_found': [],
                'reasoning': ''
            },
            'created_nodes': [],
            'created_edges': [],
            'created_subtrees': [],
            'proposed_nodes': [],
            'proposed_edges': [],
            'started_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': None,
            'error': None
        }
        
        # Start exploration in background thread
        def run_exploration():
            try:
                # Update status
                _exploration_sessions[exploration_id]['status'] = 'exploring'
                _exploration_sessions[exploration_id]['current_step'] = 'Capturing initial screenshot...'
                
                # Create exploration engine
                engine = ExplorationEngine(
                    tree_id=tree_id,
                    device_id=device_id,
                    host_name=host_name,
                    device_model_name=device_model_name,
                    team_id=team_id,
                    userinterface_name=userinterface_name,
                    depth_limit=exploration_depth
                )
                
                # Run exploration
                result = engine.start_exploration()
                
                # Update state with results
                if result['success']:
                    _exploration_sessions[exploration_id]['status'] = 'completed'
                    _exploration_sessions[exploration_id]['current_step'] = f"Exploration completed. Found {result['nodes_created']} nodes."
                    _exploration_sessions[exploration_id]['progress'] = {
                        'total_screens_found': result['nodes_created'],
                        'screens_analyzed': result['nodes_created'],
                        'nodes_proposed': result['nodes_created'],
                        'edges_proposed': result['edges_created']
                    }
                    _exploration_sessions[exploration_id]['created_nodes'] = result['created_node_ids']
                    _exploration_sessions[exploration_id]['created_edges'] = result['created_edge_ids']
                    _exploration_sessions[exploration_id]['created_subtrees'] = result['created_subtree_ids']
                    
                    # Build proposed nodes/edges for frontend
                    proposed_nodes = []
                    for node_id in result['created_node_ids']:
                        node_result = get_node_by_id(tree_id, node_id, team_id)
                        if node_result['success']:
                            node = node_result['node']
                            proposed_nodes.append({
                                'id': node_id,
                                'name': node.get('label', node_id),
                                'screen_type': node.get('data', {}).get('screen_type', 'screen'),
                                'reasoning': node.get('data', {}).get('reasoning', '')
                            })
                    
                    proposed_edges = []
                    for edge_id in result['created_edge_ids']:
                        edge_result = get_edge_by_id(tree_id, edge_id, team_id)
                        if edge_result['success']:
                            edge = edge_result['edge']
                            proposed_edges.append({
                                'id': edge_id,
                                'source': edge.get('source_node_id', ''),
                                'target': edge.get('target_node_id', ''),
                                'reasoning': f"Navigation from {edge.get('source_node_id', '')} to {edge.get('target_node_id', '')}"
                            })
                    
                    _exploration_sessions[exploration_id]['proposed_nodes'] = proposed_nodes
                    _exploration_sessions[exploration_id]['proposed_edges'] = proposed_edges
                else:
                    _exploration_sessions[exploration_id]['status'] = 'failed'
                    _exploration_sessions[exploration_id]['error'] = result.get('error', 'Unknown error')
                    _exploration_sessions[exploration_id]['current_step'] = f"Exploration failed: {result.get('error')}"
                
                _exploration_sessions[exploration_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
                
            except Exception as e:
                print(f"[@route:ai_generation:run_exploration] Error: {e}")
                _exploration_sessions[exploration_id]['status'] = 'failed'
                _exploration_sessions[exploration_id]['error'] = str(e)
                _exploration_sessions[exploration_id]['current_step'] = f"Error: {str(e)}"
                _exploration_sessions[exploration_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Start thread
        thread = threading.Thread(target=run_exploration, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'exploration_id': exploration_id,
            'message': 'Exploration started'
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:start_exploration] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_generation_bp.route('/exploration-status/<exploration_id>', methods=['GET'])
def exploration_status(exploration_id):
    """
    Get current exploration status (polling endpoint)
    
    Response:
    {
        'success': True,
        'exploration_id': 'uuid',
        'status': 'exploring',
        'current_step': '...',
        'progress': {...},
        'proposed_nodes': [...],  # Only when completed
        'proposed_edges': [...]   # Only when completed
    }
    """
    try:
        if exploration_id not in _exploration_sessions:
            return jsonify({
                'success': False,
                'error': 'Exploration session not found'
            }), 404
        
        session = _exploration_sessions[exploration_id]
        
        response = {
            'success': True,
            'exploration_id': exploration_id,
            'status': session['status'],
            'current_step': session['current_step'],
            'progress': session['progress'],
            'current_analysis': session['current_analysis']
        }
        
        # Include proposed nodes/edges when completed
        if session['status'] == 'completed':
            response['proposed_nodes'] = session['proposed_nodes']
            response['proposed_edges'] = session['proposed_edges']
        
        # Include error if failed
        if session['status'] == 'failed':
            response['error'] = session['error']
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[@route:ai_generation:exploration_status] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_generation_bp.route('/approve-generation', methods=['POST'])
def approve_generation():
    """
    Approve generation - rename all _temp nodes/edges
    
    Request:
    {
        'exploration_id': 'uuid',
        'tree_id': 'uuid',
        'approved_nodes': ['home_temp', 'settings_temp'],
        'approved_edges': ['edge_home_to_settings_temp'],
        'team_id': 'team_1'
    }
    
    Response:
    {
        'success': True,
        'nodes_created': 2,
        'edges_created': 1
    }
    """
    try:
        data = request.get_json()
        
        exploration_id = data.get('exploration_id')
        tree_id = data.get('tree_id')
        approved_nodes = data.get('approved_nodes', [])
        approved_edges = data.get('approved_edges', [])
        team_id = data.get('team_id', 'team_1')
        
        if exploration_id not in _exploration_sessions:
            return jsonify({
                'success': False,
                'error': 'Exploration session not found'
            }), 404
        
        print(f"[@route:ai_generation:approve_generation] Approving {len(approved_nodes)} nodes, {len(approved_edges)} edges")
        
        from services.ai_exploration.node_generator import NodeGenerator
        node_generator = NodeGenerator(tree_id, team_id)
        
        nodes_created = 0
        edges_created = 0
        
        # Rename approved nodes (remove _temp)
        for node_id in approved_nodes:
            node_result = get_node_by_id(tree_id, node_id, team_id)
            if node_result['success']:
                node_data = node_result['node']
                renamed_data = node_generator.rename_node(node_data)
                
                # Delete old node
                delete_node(tree_id, node_id, team_id)
                
                # Save renamed node
                save_result = save_node(tree_id, renamed_data, team_id)
                if save_result['success']:
                    nodes_created += 1
                    print(f"  ✅ Renamed: {node_id} → {renamed_data['node_id']}")
        
        # Rename approved edges (remove _temp)
        for edge_id in approved_edges:
            edge_result = get_edge_by_id(tree_id, edge_id, team_id)
            if edge_result['success']:
                edge_data = edge_result['edge']
                renamed_data = node_generator.rename_edge(edge_data)
                
                # Delete old edge (will be handled by save_edge upsert)
                # save_edge handles update if exists
                save_result = save_edge(tree_id, renamed_data, team_id)
                if save_result['success']:
                    edges_created += 1
                    print(f"  ✅ Renamed: {edge_id} → {renamed_data['edge_id']}")
        
        # Clean up session
        del _exploration_sessions[exploration_id]
        
        print(f"[@route:ai_generation:approve_generation] ✅ Complete: {nodes_created} nodes, {edges_created} edges")
        
        return jsonify({
            'success': True,
            'nodes_created': nodes_created,
            'edges_created': edges_created,
            'message': f'Successfully created {nodes_created} nodes and {edges_created} edges'
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:approve_generation] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_generation_bp.route('/cancel-exploration', methods=['POST'])
def cancel_exploration():
    """
    Cancel exploration - delete all _temp nodes/edges
    
    Request:
    {
        'exploration_id': 'uuid',
        'host_ip': '...',
        'team_id': 'team_1'
    }
    
    Response:
    {
        'success': True,
        'message': 'Exploration cancelled'
    }
    """
    try:
        data = request.get_json()
        
        exploration_id = data.get('exploration_id')
        team_id = data.get('team_id', 'team_1')
        
        if exploration_id not in _exploration_sessions:
            return jsonify({
                'success': False,
                'error': 'Exploration session not found'
            }), 404
        
        session = _exploration_sessions[exploration_id]
        tree_id = session['tree_id']
        
        print(f"[@route:ai_generation:cancel_exploration] Cancelling exploration {exploration_id}")
        
        # Delete all created _temp nodes (cascade will delete edges)
        for node_id in session['created_nodes']:
            delete_node(tree_id, node_id, team_id)
            print(f"  🗑️  Deleted node: {node_id}")
        
        # Delete any created _temp subtrees
        for subtree_id in session['created_subtrees']:
            delete_tree_cascade(subtree_id, team_id)
            print(f"  🗑️  Deleted subtree: {subtree_id}")
        
        # Clean up session
        del _exploration_sessions[exploration_id]
        
        print(f"[@route:ai_generation:cancel_exploration] ✅ Exploration cancelled")
        
        return jsonify({
            'success': True,
            'message': 'Exploration cancelled, temporary nodes deleted'
        })
        
    except Exception as e:
        print(f"[@route:ai_generation:cancel_exploration] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

