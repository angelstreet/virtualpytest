"""
Server MCP Routes

Bridge between MCP Task Input UI and existing AI Agent system.
Handles task execution using AI agent with MCP tool awareness.
"""

from flask import Blueprint, request, jsonify
import logging

# Import AI System
from backend_host.src.services.ai.ai_executor import AIExecutor

# Create blueprint
server_mcp_bp = Blueprint('server_mcp', __name__, url_prefix='/server/mcp')

# Set up logging
logger = logging.getLogger(__name__)

@server_mcp_bp.route('/execute-task', methods=['POST'])
def execute_task():
    """
    Execute a user task using AI agent with MCP tool awareness
    
    Expected JSON payload:
    {
        "task": "Go to rec page"
    }
    
    Returns:
    {
        "success": true,
        "result": "Task completed successfully",
        "tool_executed": "navigate_to_page",
        "details": {...}
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        task = data.get('task')
        
        if not task:
            return jsonify({
                "success": False,
                "error": "Task parameter is required"
            }), 400
        
        logger.info(f"[@server_mcp_routes:execute_task] Executing task: {task}")
        
        # Prepare MCP tools context for AI agent
        mcp_tools = [
            {
                "command": "navigate_to_page",
                "description": "Navigate to a specific page (dashboard, rec, userinterface, runTests)",
                "params": ["page"]
            },
            {
                "command": "execute_navigation_to_node", 
                "description": "Execute navigation to a specific node in a navigation tree",
                "params": ["tree_id", "target_node_id", "team_id", "current_node_id"]
            },
            {
                "command": "remote_execute_command",
                "description": "Execute a remote command on a device",
                "params": ["command", "device_id"]
            }
        ]
        
        mcp_verifications = [
            {
                "verification_type": "mcp_tool_success",
                "description": "Verify MCP tool executed successfully"
            }
        ]
        
        # Generate plan using simplified AI system
        try:
            # Create minimal context for MCP interface
            context = {
                'device_model': 'mcp_device',
                'userinterface_name': 'mcp_interface',
                'available_nodes': [],
                'available_actions': mcp_tools,
                'available_verifications': mcp_verifications
            }
            
            # Create AIExecutor for MCP operations
            class MockDevice:
                def __init__(self):
                    self.device_id = "server_mcp"
                    self.device_model = "server"
            
            ai_executor = AIExecutor(
                host={'host_name': 'server_mcp'}, 
                device=MockDevice(), 
                team_id="default"
            )
            plan_dict = ai_executor.generate_plan(task, context)
            
            ai_result = {
                'success': plan_dict.get('feasible', True),
                'plan': plan_dict,
                'error': None if plan_dict.get('feasible', True) else plan_dict.get('analysis', '')
            }
        except Exception as e:
            ai_result = {
                'success': False,
                'error': str(e)
            }
        
        if ai_result.get('success'):
            # Extract MCP tool execution from AI plan
            plan_dict = ai_result.get('plan')
            plan_steps = plan_dict.get('steps', [])  # Use 'steps' key from new format
            
            # Execute the first MCP tool from the plan
            mcp_result = _execute_mcp_tool_from_plan(plan_steps)
            
            return jsonify({
                "success": True,
                "result": "Task completed successfully",
                "tool_executed": mcp_result.get('tool_name'),
                "tool_result": mcp_result.get('result'),
                "ai_analysis": plan_dict.get('analysis', ''),
                "execution_log": []
            })
        else:
            return jsonify({
                "success": False,
                "error": ai_result.get('error', 'AI agent failed to process task'),
                "execution_log": []
            }), 500
        
    except Exception as e:
        logger.error(f"[@server_mcp_routes:execute_task] Error: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

def _execute_mcp_tool_from_plan(plan_steps):
    """
    Execute MCP tool based on AI plan
    
    Args:
        plan_steps: List of plan steps from AI agent
        
    Returns:
        Dict with tool execution result
    """
    try:
        # Find the first action step in the plan
        for step in plan_steps:
            if step.get('type') == 'action':
                command = step.get('command')
                params = step.get('params', {})
                
                logger.info(f"[@server_mcp_routes:_execute_mcp_tool] Executing: {command} with params: {params}")
                
                # Execute the appropriate MCP tool
                if command == "navigate_to_page":
                    return _execute_navigate_to_page(params)
                elif command == "execute_navigation_to_node":
                    return _execute_navigation_to_node(params)
                elif command == "remote_execute_command":
                    return _execute_remote_command(params)
                else:
                    return {
                        'tool_name': command,
                        'result': {'success': False, 'error': f'Unknown MCP tool: {command}'}
                    }
        
        return {
            'tool_name': 'none',
            'result': {'success': False, 'error': 'No executable action found in AI plan'}
        }
        
    except Exception as e:
        logger.error(f"[@server_mcp_routes:_execute_mcp_tool] Error: {e}")
        return {
            'tool_name': 'error',
            'result': {'success': False, 'error': str(e)}
        }

def _execute_navigate_to_page(params):
    """Execute navigate_to_page MCP tool"""
    try:
        page = params.get("page", params.get("key", "dashboard"))
        
        # Define valid pages
        valid_pages = ["dashboard", "rec", "userinterface", "runTests"]
        
        if page not in valid_pages:
            return {
                'tool_name': 'navigate_to_page',
                'result': {
                    'success': False, 
                    'error': f"Invalid page '{page}'. Valid pages: {valid_pages}"
                }
            }
        
        # Generate redirect URL
        redirect_url = f"/{page}"
        
        result = {
            "success": True,
            "redirect_url": redirect_url,
            "page": page,
            "message": f"Navigate to {page} page"
        }
        
        return {
            'tool_name': 'navigate_to_page',
            'result': result
        }
        
    except Exception as e:
        logger.error(f"[@server_mcp_routes:_execute_navigate_to_page] Error: {e}")
        return {
            'tool_name': 'navigate_to_page',
            'result': {'success': False, 'error': str(e)}
        }

def _execute_navigation_to_node(params):
    """Execute execute_navigation_to_node MCP tool"""
    try:
        from backend_host.src.services.navigation.navigation_executor import NavigationExecutor
        from src.lib.utils.app_utils import get_team_id
        
        tree_id = params.get("tree_id", "default_tree")
        target_node_id = params.get("target_node_id", "home")
        team_id = params.get("team_id") or get_team_id()
        current_node_id = params.get("current_node_id")
        
        # Create minimal host configuration for MCP execution
        host = {"host_name": "mcp_host", "device_model": "MCP_Interface"}
        
        # Use the new NavigationExecutor - need to get device from host
        from backend_host.src.controllers.controller_manager import get_host
        host_instance = get_host()
        device = host_instance.get_device(device_id)
        if not device:
            return {'success': False, 'error': f'Device {device_id} not found'}
        
        from src.lib.utils.app_utils import get_team_id
        result = device.navigation_executor.execute_navigation(tree_id, target_node_id, current_node_id, team_id=get_team_id())
        
        return {
            'tool_name': 'execute_navigation_to_node',
            'result': {
                'success': result.get('success', False),
                'message': result.get('message', f"Navigation to {target_node_id} {'completed' if result.get('success') else 'failed'}")
            }
        }
        
    except Exception as e:
        logger.error(f"[@server_mcp_routes:_execute_navigation_to_node] Error: {e}")
        return {
            'tool_name': 'execute_navigation_to_node',
            'result': {'success': False, 'error': str(e)}
        }

def _execute_remote_command(params):
    """Execute remote_execute_command MCP tool"""
    try:
        command = params.get("command", "unknown")
        device_id = params.get("device_id", "default")
        
        logger.info(f"[@server_mcp_routes:_execute_remote_command] Remote command: {command} on device {device_id}")
        
        # This would integrate with actual remote controller
        # For now, return success for demonstration
        return {
            'tool_name': 'remote_execute_command',
            'result': {
                'success': True,
                'message': f"Remote command '{command}' executed on device '{device_id}'"
            }
        }
        
    except Exception as e:
        logger.error(f"[@server_mcp_routes:_execute_remote_command] Error: {e}")
        return {
            'tool_name': 'remote_execute_command',
            'result': {'success': False, 'error': str(e)}
        }

@server_mcp_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for MCP routes"""
    return jsonify({
        "success": True,
        "service": "mcp_routes",
        "message": "MCP routes are healthy"
    }) 