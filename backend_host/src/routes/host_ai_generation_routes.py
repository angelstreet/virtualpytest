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
        
        # Import necessary modules for exploration
        from backend_core.src.controllers.ai.ai_agent import AIAgent
        from backend_core.src.controllers.verification.image import ImageController
        from backend_core.src.controllers.remote.android_mobile import AndroidMobileController
        
        # Update progress
        update_progress(exploration_id, "Initializing AI agent and controllers...")
        
        # Initialize controllers based on device type
        device_id = session['device_id']
        tree_id = session['tree_id']
        
        # For now, assume android_mobile - expand later for other device types
        remote_controller = AndroidMobileController()
        image_controller = ImageController()
        ai_agent = AIAgent()
        
        # Update progress
        update_progress(exploration_id, "Taking initial screenshot...")
        
        # Take initial screenshot for analysis
        screenshot_result = image_controller.take_screenshot(device_id)
        if not screenshot_result.get('success'):
            raise Exception(f"Failed to take screenshot: {screenshot_result.get('error')}")
        
        screenshot_path = screenshot_result.get('screenshot_path')
        
        # Update progress
        update_progress(exploration_id, "Analyzing home screen with AI...")
        
        # Analyze screenshot with AI
        analysis_prompt = f"""
        Analyze this interface screenshot and identify:
        1. Interactive elements (buttons, menu items, clickable areas)
        2. Current screen type (home, menu, settings, etc.)
        3. Navigation elements (arrows, tabs, etc.)
        4. Text labels and their positions
        
        Provide a structured response with element locations and descriptions.
        Focus on main navigation elements first (home menu items).
        """
        
        ai_analysis = ai_agent.analyze_image(screenshot_path, analysis_prompt)
        if not ai_analysis.get('success'):
            raise Exception(f"AI analysis failed: {ai_analysis.get('error')}")
        
        analysis_text = ai_analysis.get('analysis', '')
        
        # Update current analysis
        session['current_analysis'] = {
            'screen_name': 'home',
            'elements_found': extract_elements_from_analysis(analysis_text),
            'reasoning': analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text
        }
        
        # Update progress
        update_progress(exploration_id, "Testing navigation elements...")
        
        # Start exploration from home screen
        explore_screen(
            exploration_id=exploration_id,
            current_screen='home',
            screenshot_path=screenshot_path,
            ai_agent=ai_agent,
            remote_controller=remote_controller,
            image_controller=image_controller,
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

def explore_screen(exploration_id: str, current_screen: str, screenshot_path: str, 
                  ai_agent, remote_controller, image_controller, depth: int, max_depth: int):
    """
    Explore a single screen and its navigation options
    
    Implements sibling-first strategy:
    1. Identify all interactive elements on current screen
    2. Test each element to understand where it leads
    3. Create nodes and edges for discovered screens
    4. Only go deeper after exploring all siblings
    """
    try:
        session = exploration_sessions[exploration_id]
        
        # Check if exploration was cancelled
        if session['status'] == 'cancelled':
            return
        
        # Check depth limit
        if depth >= max_depth:
            print(f"[@explore_screen] Reached max depth {max_depth} for {current_screen}")
            return
        
        update_progress(exploration_id, f"Exploring {current_screen} screen (depth {depth})...")
        
        # Analyze current screen for interactive elements
        elements_prompt = f"""
        Analyze this interface screenshot for interactive elements:
        1. List all clickable buttons and menu items
        2. Identify navigation controls (arrows, directional buttons)
        3. Determine element positions and how to interact with them
        4. Focus on main navigation elements first
        
        Current screen: {current_screen}
        Depth: {depth}/{max_depth}
        """
        
        ai_analysis = ai_agent.analyze_image(screenshot_path, elements_prompt)
        if not ai_analysis.get('success'):
            print(f"[@explore_screen] Failed to analyze {current_screen}: {ai_analysis.get('error')}")
            return
        
        analysis_text = ai_analysis.get('analysis', '')
        elements = extract_elements_from_analysis(analysis_text)
        
        # Update current analysis
        session['current_analysis'] = {
            'screen_name': current_screen,
            'elements_found': elements,
            'reasoning': f"Found {len(elements)} interactive elements on {current_screen}"
        }
        
        # Create node for current screen if not exists
        node_id = current_screen
        if not node_exists(session, node_id):
            create_proposed_node(session, node_id, current_screen, 'menu', f"Screen: {current_screen}")
        
        # Test each interactive element (sibling-first strategy)
        for element in elements[:5]:  # Limit to first 5 elements for initial implementation
            if session['status'] == 'cancelled':
                break
                
            test_navigation_element(
                exploration_id=exploration_id,
                current_screen=current_screen,
                element=element,
                ai_agent=ai_agent,
                remote_controller=remote_controller,
                image_controller=image_controller,
                depth=depth
            )
            
            # Wait between tests to avoid issues
            time.sleep(2)
        
        print(f"[@explore_screen] Completed exploration of {current_screen} at depth {depth}")
        
    except Exception as e:
        print(f"[@explore_screen] Error exploring {current_screen}: {str(e)}")

def test_navigation_element(exploration_id: str, current_screen: str, element: str,
                           ai_agent, remote_controller, image_controller, depth: int):
    """
    Test a single navigation element to see where it leads
    """
    try:
        session = exploration_sessions[exploration_id]
        device_id = session['device_id']
        
        update_progress(exploration_id, f"Testing {element} from {current_screen}...")
        
        # Take screenshot before interaction
        before_screenshot = image_controller.take_screenshot(device_id)
        if not before_screenshot.get('success'):
            return
        
        # Determine interaction method based on element
        # For simplicity, try directional navigation first
        navigation_commands = determine_navigation_command(element)
        
        for command in navigation_commands:
            # Execute navigation command
            result = remote_controller.execute_command(device_id, command)
            if not result.get('success'):
                continue
            
            # Wait for screen to load
            time.sleep(3)
            
            # Take screenshot after interaction
            after_screenshot = image_controller.take_screenshot(device_id)
            if not after_screenshot.get('success'):
                continue
            
            # Compare screenshots to detect screen change
            comparison = image_controller.compare_screenshots(
                before_screenshot['screenshot_path'],
                after_screenshot['screenshot_path']
            )
            
            if comparison.get('similarity', 100) < 90:  # Screen changed significantly
                # Analyze new screen
                new_screen_analysis = ai_agent.analyze_image(
                    after_screenshot['screenshot_path'],
                    f"What screen is this? Provide a short screen name/identifier."
                )
                
                if new_screen_analysis.get('success'):
                    new_screen_name = extract_screen_name(new_screen_analysis.get('analysis', ''))
                    new_node_id = f"{current_screen}_{new_screen_name.lower()}"
                    
                    # Create edge for successful navigation
                    create_proposed_edge(
                        session=session,
                        source=current_screen,
                        target=new_node_id,
                        command=command,
                        element=element
                    )
                    
                    # Create node for new screen
                    if not node_exists(session, new_node_id):
                        create_proposed_node(session, new_node_id, new_screen_name, 'menu', 
                                           f"Navigated from {current_screen} via {element}")
                    
                    print(f"[@test_navigation_element] Found navigation: {current_screen} -> {new_node_id} via {element}")
                    
                # Navigate back to original screen for next test
                back_result = remote_controller.execute_command(device_id, {"command": "back"})
                time.sleep(2)
                
                break  # Successfully tested this element
        
    except Exception as e:
        print(f"[@test_navigation_element] Error testing {element}: {str(e)}")

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
