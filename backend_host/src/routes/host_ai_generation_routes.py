"""
Host AI Interface Generation Routes

Host-side routes for AI-driven interface exploration and automated navigation tree generation.
Handles actual device control, image analysis, and step-by-step exploration logic.
"""

from flask import Blueprint, request, jsonify
import uuid
import time
import threading
from typing import Dict, List, Optional, Any
import json

# Create blueprint
host_ai_generation_bp = Blueprint('host_ai_generation', __name__, url_prefix='/host/ai-generation')

# Global storage for exploration sessions (in production, use Redis or database)
exploration_sessions: Dict[str, Dict] = {}
exploration_threads: Dict[str, threading.Thread] = {}

@host_ai_generation_bp.route('/start-exploration', methods=['POST'])
def start_exploration():
    """
    Start AI interface exploration on host
    
    Request body:
    {
        "exploration_id": "uuid",
        "tree_id": "uuid", 
        "device_id": "device_uuid",
        "exploration_depth": 5,
        "start_node_id": "home_node_id"
    }
    """
    try:
        print("[@host_ai_generation] Starting AI interface exploration")
        
        # Get request data
        request_data = request.get_json() or {}
        exploration_id = request_data.get('exploration_id')
        tree_id = request_data.get('tree_id')
        device_id = request_data.get('device_id')
        team_id = request.args.get('team_id')
        exploration_depth = request_data.get('exploration_depth', 5)
        start_node_id = request_data.get('start_node_id')
        
        # Validate required fields
        if not exploration_id or not tree_id or not device_id or not team_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: exploration_id, tree_id, device_id, team_id'
            }), 400
        
        # Initialize exploration session
        exploration_sessions[exploration_id] = {
            'exploration_id': exploration_id,
            'tree_id': tree_id,
            'device_id': device_id,
            'team_id': team_id,
            'exploration_depth': exploration_depth,
            'start_node_id': start_node_id,
            'status': 'initializing',
            'current_step': 'Initializing exploration...',
            'progress': {
                'total_screens_found': 0,
                'screens_analyzed': 0,
                'nodes_proposed': 0,
                'edges_proposed': 0
            },
            'current_analysis': {},
            'proposed_nodes': [],
            'proposed_edges': [],
            'created_at': time.time(),
            'error': None
        }
        
        # Start exploration in background thread
        exploration_thread = threading.Thread(
            target=run_exploration,
            args=(exploration_id,)
        )
        exploration_thread.daemon = True
        exploration_thread.start()
        
        exploration_threads[exploration_id] = exploration_thread
        
        return jsonify({
            'success': True,
            'exploration_id': exploration_id,
            'message': 'Exploration started successfully'
        }), 200
        
    except Exception as e:
        print(f"[@host_ai_generation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@host_ai_generation_bp.route('/exploration-status/<exploration_id>', methods=['GET'])
def get_exploration_status(exploration_id):
    """Get current exploration status and progress"""
    try:
        if exploration_id not in exploration_sessions:
            return jsonify({
                'success': False,
                'error': 'Exploration not found'
            }), 404
        
        session = exploration_sessions[exploration_id]
        
        response_data = {
            'success': True,
            'exploration_id': exploration_id,
            'status': session['status'],
            'current_step': session['current_step'],
            'progress': session['progress'],
            'current_analysis': session['current_analysis'],
            'error': session.get('error')
        }
        
        # Include proposed nodes and edges when exploration is completed
        if session['status'] == 'completed':
            response_data['proposed_nodes'] = session['proposed_nodes']
            response_data['proposed_edges'] = session['proposed_edges']
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"[@host_ai_generation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@host_ai_generation_bp.route('/cancel-exploration', methods=['POST'])
def cancel_exploration():
    """Cancel ongoing exploration"""
    try:
        request_data = request.get_json() or {}
        exploration_id = request_data.get('exploration_id')
        
        if not exploration_id:
            return jsonify({
                'success': False,
                'error': 'Missing exploration_id'
            }), 400
        
        if exploration_id in exploration_sessions:
            exploration_sessions[exploration_id]['status'] = 'cancelled'
            exploration_sessions[exploration_id]['current_step'] = 'Exploration cancelled by user'
        
        return jsonify({
            'success': True,
            'message': 'Exploration cancelled'
        }), 200
        
    except Exception as e:
        print(f"[@host_ai_generation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def run_exploration(exploration_id: str):
    """
    AI-driven interface exploration using clean architecture
    
    This function uses AI to systematically explore interfaces:
    1. AI analyzes current context and capabilities
    2. AI generates exploration plan (screenshot → analyze → navigate → repeat)
    3. Existing executors handle all device interaction
    4. AI learns from results and adapts exploration strategy
    """
    try:
        print(f"[@host_ai_generation] Starting AI-driven exploration {exploration_id}")
        
        session = exploration_sessions[exploration_id]
        session['status'] = 'exploring'
        
        # Import simplified AI architecture
        from backend_host.controllers.controller_manager import get_host
        
        # Get session parameters
        device_id = session['device_id']
        tree_id = session['tree_id']
        team_id = session['team_id']
        
        # Update progress
        update_progress(exploration_id, "Loading device context...")
        
        # Get host and device info dynamically (no hardcoding)
        host = get_host()
        device = host.get_device(device_id)
        if not device:
            raise Exception(f"Device {device_id} not found")
        
        # Get userinterface name from tree_id if available, otherwise use device-based name
        userinterface_name = None
        if tree_id:
            try:
                from shared.src.lib.supabase.navigation_trees_db import get_tree_info
                tree_info = get_tree_info(tree_id, team_id)
                if tree_info and tree_info.get('userinterface_name'):
                    userinterface_name = tree_info['userinterface_name']
            except Exception as e:
                print(f"[@run_exploration] Could not get userinterface from tree_id: {e}")
        
        # Fallback to device-based interface name if no tree interface found
        if not userinterface_name:
            userinterface_name = f"{device.device_model}_exploration"
        
        print(f"[@run_exploration] Using userinterface: {userinterface_name}")
        
        # Get device with existing AI executor for exploration
        update_progress(exploration_id, "Analyzing device capabilities...")
        device = get_device(device_id)
        if not device or not hasattr(device, 'ai_executor'):
            update_progress(exploration_id, "ERROR: Device or AI executor not found", is_error=True)
            return
        
        # AI-driven exploration loop
        exploration_steps = session['exploration_depth']
        for step in range(exploration_steps):
            if session['status'] == 'cancelled':
                break
                
            update_progress(exploration_id, f"AI exploration step {step + 1}/{exploration_steps}...")
            
            # AI generates exploration plan for this step
            exploration_prompt = f"""
            Explore this interface systematically. Step {step + 1} of {exploration_steps}.
            
            Tasks:
            1. Take a screenshot to see current state
            2. Analyze what interactive elements are visible
            3. Test one navigation action (press key or click element)
            4. Take another screenshot to see what changed
            5. Record findings for navigation mapping
            
            Focus on discovering new screens and navigation paths.
            Use available actions and verifications from the context.
            """
            
            try:
                # Execute AI exploration step
                result = device.ai_executor.execute_prompt(
                    exploration_prompt, 
                    userinterface_name,
                    async_execution=False,  # Synchronous for exploration
                    team_id=team_id
                )
                
                step_success = result.get('success', False)
                
                if step_success:
                    # AI successfully executed exploration step
                    # Extract findings from execution result
                    execution_result = result.get('result')
                    
                    # Create nodes and edges based on AI findings
                    create_exploration_results_from_ai_execution(session, execution_result, step)
                    
                    print(f"[@run_exploration] Step {step + 1} completed successfully")
                else:
                    print(f"[@run_exploration] Step {step + 1} failed, continuing...")
                    
            except Exception as step_error:
                print(f"[@run_exploration] Error in step {step + 1}: {step_error}")
                continue
        
        # Mark exploration as completed
        session['status'] = 'completed'
        session['current_step'] = f"AI exploration completed. Found {len(session['proposed_nodes'])} screens and {len(session['proposed_edges'])} navigation paths."
        
        print(f"[@host_ai_generation] AI-driven exploration {exploration_id} completed successfully")
        
    except Exception as e:
        print(f"[@host_ai_generation] Error in exploration {exploration_id}: {str(e)}")
        if exploration_id in exploration_sessions:
            exploration_sessions[exploration_id]['status'] = 'failed'
            exploration_sessions[exploration_id]['error'] = str(e)
            exploration_sessions[exploration_id]['current_step'] = f"Exploration failed: {str(e)}"

@host_ai_generation_bp.route('/generatePlan', methods=['POST'])
def generate_plan():
    """Generate AI execution plan using device AI executor."""
    try:
        from  backend_host.src.lib.utils.host_utils import get_device_by_id
        
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        prompt = data.get('prompt', '')
        
        print(f"[@host_ai_generation] Generating AI plan for device: {device_id}")
        print(f"[@host_ai_generation] Prompt: {prompt[:100]}...")
        
        # Get device and check AI executor
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AI executor initialized'
            }), 404
        
        # Get userinterface_name from request or use default
        userinterface_name = data.get('userinterface_name', 'horizon_android_mobile')
        team_id = request.args.get('team_id')
        
        # Generate plan using AI executor's existing capabilities
        # execute_prompt with async_execution=False returns the generated plan
        result = device.ai_executor.execute_prompt(
            prompt,
            userinterface_name,
            team_id=team_id,
            async_execution=False  # Synchronous mode returns plan + execution result
        )
        
        # Extract just the plan part for the generation endpoint
        if result.get('success'):
            # Return plan-focused response
            plan_result = {
                'success': True,
                'plan': result.get('result', {}).get('plan', {}),
                'analysis': result.get('result', {}).get('analysis', ''),
                'feasible': result.get('success', True)
            }
            result = plan_result
        
        # Determine appropriate status code based on plan generation result
        success = result.get('success', False)
        status_code = 200 if success else 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        print(f"[@host_ai_generation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI plan generation error: {str(e)}'
        }), 500

@host_ai_generation_bp.route('/analyzeCompatibility', methods=['POST'])
def analyze_compatibility():
    """Analyze AI task compatibility using device AI executor."""
    try:
        from  backend_host.src.lib.utils.host_utils import get_device_by_id
        
        # Get device_id from request (defaults to device1)
        data = request.get_json() or {}
        device_id = data.get('device_id', 'device1')
        prompt = data.get('prompt', '')
        
        print(f"[@host_ai_generation] Analyzing AI compatibility for device: {device_id}")
        print(f"[@host_ai_generation] Prompt: {prompt[:100]}...")
        
        # Get device and check AI executor
        device = get_device_by_id(device_id)
        if not device:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        # Check if device has ai_executor
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} does not have AI executor initialized'
            }), 404
        
        # Get userinterface_name from request or use default
        userinterface_name = data.get('userinterface_name', 'horizon_android_mobile')
        team_id = request.args.get('team_id')
        
        # Analyze compatibility using AI executor's existing plan generation
        # The plan generation already includes feasibility analysis
        result = device.ai_executor.execute_prompt(
            f"Analyze compatibility for task: {prompt}",
            userinterface_name,
            team_id=team_id,
            async_execution=False  # Synchronous mode includes analysis
        )
        
        # Extract compatibility analysis from the result
        if result.get('success'):
            # Return compatibility-focused response
            compatibility_result = {
                'success': True,
                'compatible': result.get('success', True),
                'analysis': result.get('result', {}).get('analysis', ''),
                'reasoning': result.get('result', {}).get('analysis', '')
            }
            result = compatibility_result
        
        # Determine appropriate status code based on analysis result
        success = result.get('success', False)
        status_code = 200 if success else 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        print(f"[@host_ai_generation] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI compatibility analysis error: {str(e)}'
        }), 500

def create_exploration_results_from_ai_execution(session: dict, execution_result, step: int):
    """
    Extract exploration results from AI execution log and create nodes/edges
    """
    try:
        # Create nodes based on AI exploration step
        node_id = f"ai_discovered_screen_{step}"
        create_proposed_node(
            session, 
            node_id, 
            f"AI Discovered Screen {step}", 
            'screen', 
            f"Screen discovered by AI during exploration step {step}"
        )
        
        # Create edge if navigation was successful
        if step > 0:
            source_node = f"ai_discovered_screen_{step-1}" if step > 1 else "home"
            create_proposed_edge(
                session,
                source_node,
                node_id,
                {"command": "ai_navigation", "step": step},
                f"AI navigation step {step}"
            )
        
        # Update session progress
        session['progress']['screens_analyzed'] += 1
        session['progress']['nodes_proposed'] = len(session['proposed_nodes'])
        session['progress']['edges_proposed'] = len(session['proposed_edges'])
        
    except Exception as e:
        print(f"[@create_exploration_results] Error processing AI execution log: {e}")



def update_progress(exploration_id: str, step: str):
    """Update exploration progress"""
    if exploration_id in exploration_sessions:
        session = exploration_sessions[exploration_id]
        session['current_step'] = step
        session['progress']['screens_analyzed'] += 1
        print(f"[@progress] {exploration_id}: {step}")

# Legacy helper functions removed - AI now handles all analysis and decision making

def node_exists(session: Dict, node_id: str) -> bool:
    """Check if node already exists in proposed nodes"""
    return any(node['id'] == node_id for node in session['proposed_nodes'])

def create_proposed_node(session: Dict, node_id: str, name: str, screen_type: str, reasoning: str):
    """Create a proposed node"""
    node = {
        'id': node_id,
        'name': name,
        'screen_type': screen_type,
        'reasoning': reasoning,
        'created_at': time.time()
    }
    session['proposed_nodes'].append(node)
    session['progress']['nodes_proposed'] = len(session['proposed_nodes'])
    print(f"[@create_proposed_node] Created node: {node_id} - {name}")

def create_proposed_edge(session: Dict, source: str, target: str, command: Dict, element: str):
    """Create a proposed edge"""
    edge_id = f"{source}_to_{target}"
    edge = {
        'id': edge_id,
        'source': source,
        'target': target,
        'type': 'navigation',
        'data': {
            'action_sets': [{
                'id': f"ai_generated_{edge_id}",
                'direction': 'forward',
                'actions': [{
                    'controller_type': 'android_mobile',
                    'command': command.get('command'),
                    'params': command
                }]
            }],
            'default_action_set_id': f"ai_generated_{edge_id}",
            'final_wait_time': 3000
        },
        'reasoning': f"Navigate from {source} to {target} via {element}",
        'created_at': time.time()
    }
    session['proposed_edges'].append(edge)
    session['progress']['edges_proposed'] = len(session['proposed_edges'])
    print(f"[@create_proposed_edge] Created edge: {edge_id}")
