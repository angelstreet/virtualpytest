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
        print("[@route:host_ai_generation:start_exploration] Starting AI interface exploration")
        
        # Get request data
        request_data = request.get_json() or {}
        exploration_id = request_data.get('exploration_id')
        tree_id = request_data.get('tree_id')
        device_id = request_data.get('device_id')
        exploration_depth = request_data.get('exploration_depth', 5)
        start_node_id = request_data.get('start_node_id')
        
        # Validate required fields
        if not exploration_id or not tree_id or not device_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: exploration_id, tree_id, device_id'
            }), 400
        
        # Initialize exploration session
        exploration_sessions[exploration_id] = {
            'exploration_id': exploration_id,
            'tree_id': tree_id,
            'device_id': device_id,
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
        print(f"[@route:host_ai_generation:start_exploration] Error: {str(e)}")
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
        print(f"[@route:host_ai_generation:get_exploration_status] Error: {str(e)}")
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
        print(f"[@route:host_ai_generation:cancel_exploration] Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def run_exploration(exploration_id: str):
    """
    Main exploration logic running in background thread
    
    This function implements the step-by-step AI exploration:
    1. Initialize controllers and AI agent
    2. Take screenshot and analyze current screen
    3. Identify interactive elements (buttons, menus)
    4. Test each element to understand navigation
    5. Create nodes and edges based on discoveries
    6. Continue exploration depth-first with sibling-first strategy
    """
    try:
        print(f"[@host_ai_generation:run_exploration] Starting exploration {exploration_id}")
        
        session = exploration_sessions[exploration_id]
        session['status'] = 'exploring'
        
        # Import AI Central for exploration
        from shared.lib.utils.ai_central import AICentral
        from backend_core.src.controllers.remote.android_mobile import AndroidMobileController
        from backend_core.src.controllers.verification.video_ai_helpers import VideoAIHelpers
        
        # Update progress
        update_progress(exploration_id, "Initializing AI agent and controllers...")
        
        # Initialize controllers based on device type
        device_id = session['device_id']
        tree_id = session['tree_id']
        
        # Initialize controllers using existing infrastructure
        remote_controller = AndroidMobileController(device_id)
        ai_central = AICentral(team_id="default", device_id=device_id)
        
        # Initialize AI helpers for image analysis - use existing VideoAIHelpers
        ai_helpers = VideoAIHelpers(device_model='android_mobile')
        
        # Update progress
        update_progress(exploration_id, "Taking initial screenshot...")
        
        # Take initial screenshot for analysis using remote controller
        success, screenshot_data, error = remote_controller.take_screenshot()
        if not success:
            raise Exception(f"Failed to take screenshot: {error}")
        
        # Note: screenshot_data is base64, we'll need to save it as a file for AI analysis
        # For now, let's use a simple approach - save the base64 as temp file
        import base64
        import tempfile
        
        screenshot_bytes = base64.b64decode(screenshot_data)
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        temp_file.write(screenshot_bytes)
        temp_file.flush()
        screenshot_path = temp_file.name
        
        # Update progress
        update_progress(exploration_id, "Analyzing home screen with AI...")
        
        # Use existing VideoAIHelpers to analyze the screenshot
        analysis_question = """Analyze this mobile interface screenshot and identify:
1. Interactive elements (buttons, menu items, clickable areas)
2. Current screen type (home, menu, settings, etc.)
3. Navigation elements (arrows, tabs, etc.)
4. Text labels and their positions

Focus on main navigation elements. List the main menu items you can see."""

        analysis_text = ai_helpers.analyze_full_image_with_ai(screenshot_path, analysis_question)
        
        print(f"[@run_exploration] AI Analysis Result: {analysis_text}")
        
        # Update current analysis
        session['current_analysis'] = {
            'screen_name': 'home',
            'elements_found': extract_elements_from_analysis(analysis_text),
            'reasoning': analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text
        }
        
        # Update progress
        update_progress(exploration_id, "Testing navigation elements...")
        
        # Start real exploration using existing controllers
        explore_interface_step_by_step(
            exploration_id=exploration_id,
            current_screen='home',
            screenshot_path=screenshot_path,
            ai_helpers=ai_helpers,
            remote_controller=remote_controller,
            device_id=device_id,
            depth=0,
            max_depth=session['exploration_depth']
        )
        
        # Mark exploration as completed
        session['status'] = 'completed'
        session['current_step'] = f"Exploration completed. Found {len(session['proposed_nodes'])} screens and {len(session['proposed_edges'])} navigation paths."
        
        print(f"[@host_ai_generation:run_exploration] Exploration {exploration_id} completed successfully")
        
    except Exception as e:
        print(f"[@host_ai_generation:run_exploration] Error in exploration {exploration_id}: {str(e)}")
        if exploration_id in exploration_sessions:
            exploration_sessions[exploration_id]['status'] = 'failed'
            exploration_sessions[exploration_id]['error'] = str(e)
            exploration_sessions[exploration_id]['current_step'] = f"Exploration failed: {str(e)}"

def explore_interface_step_by_step(exploration_id: str, current_screen: str, screenshot_path: str,
                                   ai_helpers, remote_controller, device_id: str, depth: int, max_depth: int):
    """
    Real exploration using existing controllers - implements step-by-step UI exploration
    """
    try:
        session = exploration_sessions[exploration_id]
        
        # Check if exploration was cancelled
        if session['status'] == 'cancelled':
            return
        
        # Check depth limit  
        if depth >= max_depth:
            print(f"[@explore_interface] Reached max depth {max_depth}")
            return
            
        update_progress(exploration_id, f"Analyzing screen elements at depth {depth}...")
        
        # Use AI to identify navigation elements
        elements_question = f"""What interactive elements can you see on this mobile interface?
List the main navigation buttons, menu items, or controls that a user can interact with.
Focus on elements that would lead to different screens or sections.
Provide a simple list of element names."""

        ai_response = ai_helpers.analyze_full_image_with_ai(screenshot_path, elements_question)
        elements = extract_elements_from_analysis(ai_response)
        
        print(f"[@explore_interface] AI found elements: {elements}")
        
        # Create home node
        create_proposed_node(session, 'home', 'Home', 'menu', 'Main home screen')
        
        # Test navigation with directional keys (common for TV/mobile interfaces)
        navigation_commands = [
            {'command': 'press_key', 'key': 'DPAD_RIGHT'},
            {'command': 'press_key', 'key': 'DPAD_DOWN'}, 
            {'command': 'press_key', 'key': 'DPAD_LEFT'},
            {'command': 'press_key', 'key': 'DPAD_UP'}
        ]
        
        for i, nav_cmd in enumerate(navigation_commands):
            if session['status'] == 'cancelled':
                break
                
            update_progress(exploration_id, f"Testing navigation: {nav_cmd['key']}")
            
            # Execute navigation command using existing remote controller
            result = remote_controller.execute_command(device_id, nav_cmd)
            
            if result.get('success'):
                # Wait for screen to change
                time.sleep(3)
                
                # Take new screenshot
                success, new_screenshot_data, error = remote_controller.take_screenshot()
                if success:
                    # Save new screenshot
                    import base64
                    import tempfile
                    
                    screenshot_bytes = base64.b64decode(new_screenshot_data)
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    temp_file.write(screenshot_bytes)
                    temp_file.flush()
                    new_screenshot_path = temp_file.name
                    
                    # Create node and edge for successful navigation
                    target_node_id = f"home_{nav_cmd['key'].lower()}"
                    edge_id = f"home_to_{nav_cmd['key'].lower()}"
                    
                    # Create proposed node and edge
                    create_proposed_node(session, target_node_id, f"Screen via {nav_cmd['key']}", 'menu', 
                                       f"Screen reached by pressing {nav_cmd['key']} from home")
                    
                    create_proposed_edge(session, 'home', target_node_id, nav_cmd, nav_cmd['key'])
                    
                    print(f"[@explore_interface] Created navigation: home -> {target_node_id}")
                    
                    # Navigate back to home
                    back_result = remote_controller.execute_command(device_id, {'command': 'press_key', 'key': 'BACK'})
                    time.sleep(2)
                else:
                    print(f"[@explore_interface] Failed to take screenshot after {nav_cmd['key']}")
            else:
                print(f"[@explore_interface] Navigation command failed: {nav_cmd}")
        
        print(f"[@explore_interface] Completed exploration - created {len(session['proposed_nodes'])} nodes, {len(session['proposed_edges'])} edges")
        
    except Exception as e:
        print(f"[@explore_interface] Error: {str(e)}")
        session['status'] = 'failed'
        session['error'] = str(e)



def update_progress(exploration_id: str, step: str):
    """Update exploration progress"""
    if exploration_id in exploration_sessions:
        session = exploration_sessions[exploration_id]
        session['current_step'] = step
        session['progress']['screens_analyzed'] += 1
        print(f"[@progress] {exploration_id}: {step}")

def extract_elements_from_analysis(analysis_text: str) -> List[str]:
    """Extract interactive elements from AI analysis text"""
    # Simple extraction - in production, use more sophisticated parsing
    elements = []
    lines = analysis_text.split('\n')
    for line in lines:
        if any(keyword in line.lower() for keyword in ['button', 'menu', 'click', 'navigate']):
            # Extract element name
            element = line.strip()
            if element and len(element) < 50:
                elements.append(element)
    return elements[:10]  # Limit to 10 elements

def extract_screen_name(analysis_text: str) -> str:
    """Extract screen name from AI analysis"""
    # Simple extraction - first word that looks like a screen name
    words = analysis_text.split()
    for word in words:
        if len(word) > 2 and word.isalpha():
            return word.capitalize()
    return "Unknown"

def determine_navigation_command(element: str) -> List[Dict]:
    """Determine navigation commands to test for an element"""
    element_lower = element.lower()
    
    # Map common elements to navigation commands
    if 'right' in element_lower or 'next' in element_lower:
        return [{"command": "keycode", "keycode": "DPAD_RIGHT"}]
    elif 'left' in element_lower or 'prev' in element_lower:
        return [{"command": "keycode", "keycode": "DPAD_LEFT"}]
    elif 'up' in element_lower:
        return [{"command": "keycode", "keycode": "DPAD_UP"}]
    elif 'down' in element_lower:
        return [{"command": "keycode", "keycode": "DPAD_DOWN"}]
    elif 'enter' in element_lower or 'ok' in element_lower or 'select' in element_lower:
        return [{"command": "keycode", "keycode": "DPAD_CENTER"}]
    else:
        # Try common navigation patterns
        return [
            {"command": "keycode", "keycode": "DPAD_RIGHT"},
            {"command": "keycode", "keycode": "DPAD_CENTER"},
            {"command": "keycode", "keycode": "DPAD_DOWN"}
        ]

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
