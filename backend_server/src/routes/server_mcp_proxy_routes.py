"""
MCP Proxy Routes - Execute prompts via OpenRouter Function Calling

Uses Qwen/Phi-3 models with function calling to decide which MCP tools to execute.
This bridges natural language prompts to MCP tool execution.
"""

from flask import Blueprint, request, jsonify
import requests
import json
import os
import sys
from pathlib import Path

# Add backend_server/src to path for MCP server import
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from mcp.mcp_server import VirtualPyTestMCPServer

server_mcp_proxy_bp = Blueprint('server_mcp_proxy', __name__, url_prefix='/server/mcp-proxy')

# Initialize MCP server instance (reuse same instance as mcp_routes)
mcp_server = VirtualPyTestMCPServer()


@server_mcp_proxy_bp.route('/execute-prompt', methods=['POST'])
def execute_prompt():
    """
    Execute natural language prompt via OpenRouter with function calling (multi-turn)
    
    Request body:
    {
      "prompt": "Swipe up on the device",
      "device_id": "device1",
      "host_name": "sunri-pi1", 
      "userinterface_name": "horizon_android_mobile",
      "team_id": "team_1",
      "tree_id": "bbf2d95d-72c2-4701-80a7-0b9d131a5c38",
      "max_iterations": 3  # Optional, defaults to 3
    }
    
    Returns:
    {
      "success": true,
      "result": { ... final result ... },
      "tool_calls": [...],  # All tool calls made
      "iterations": 2,  # Number of turns taken
      "ai_response": "I executed a swipe up action"
    }
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        device_id = data.get('device_id', 'device1')
        host_name = data.get('host_name', 'sunri-pi1')
        userinterface_name = data.get('userinterface_name')
        team_id = request.args.get('team_id')
        tree_id = data.get('tree_id')
        max_iterations = data.get('max_iterations', 3)  # Default 3 turns
        
        print(f"[@mcp_proxy] Received prompt: {prompt}")
        print(f"[@mcp_proxy] Context - device: {device_id}, host: {host_name}, interface: {userinterface_name}, team_id: {team_id}")
        print(f"[@mcp_proxy] Max iterations: {max_iterations}")
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt required'}), 400
        
        # Get OpenRouter API key
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'OPENROUTER_API_KEY not configured in .env'}), 500
        
        # Get available MCP tools and convert to OpenRouter function format
        available_tools = mcp_server.get_available_tools()
        
        # Convert MCP tool schemas to OpenRouter tools format (new API)
        tools = []
        for tool in available_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool['name'],
                    "description": tool['description'][:1000],  # Allow longer descriptions for context
                    "parameters": tool['inputSchema']
                }
            })
        
        print(f"[@mcp_proxy] Prepared {len(tools)} tools for AI (all available)")
        
        # System prompt - explain categories and workflow
        system_prompt = f'''You are a device automation assistant with access to MCP tools.

Current context:
- Device ID: {device_id}
- Host: {host_name}
- Interface: {userinterface_name}
- Team ID: {team_id}
- Tree ID: {tree_id or 'not provided'}

IMPORTANT: Control session is ALREADY ACTIVE. Do NOT call take_control or release_control.
Focus ONLY on executing the user's requested action.

TOOL CATEGORIES:

1. ACTIONS - Direct device commands (click, swipe, type, press key, etc.)
   - If unsure about available commands: Call list_actions first
   - Then: Call execute_device_action with the discovered command

2. VERIFICATIONS - Check or wait for something on device
   - If unsure: Call list_verifications first
   - Then: Call verify_device_state with the discovered verification

3. NAVIGATION - Navigate through UI using predefined nodes
   - If unsure: Call list_navigation_nodes first
   - Then: Call navigate_to_node with the discovered node

4. SCREENSHOTS - Capture device screen
   - Directly call capture_screenshot

RULES:
- ALWAYS include device_id, host_name, team_id in function calls (use values from context above)
- You can make multiple tool calls to complete the task (list first, then execute)
- Use exact command/node/verification names from list responses
- Do NOT call take_control or release_control - session is already active'''

        # Multi-turn conversation
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ]
        
        all_tool_calls = []
        final_result = None
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            print(f"[@mcp_proxy] === Iteration {iteration}/{max_iterations} ===")
            print(f"[@mcp_proxy] Calling OpenRouter with model: google/gemini-2.0-flash-001")
            
            openrouter_response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'HTTP-Referer': 'https://virtualpytest.com',
                    'X-Title': 'VirtualPyTest MCP Proxy',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'google/gemini-2.0-flash-001',
                    'messages': messages,
                    'tools': tools,
                    'tool_choice': 'auto',
                    'max_tokens': 2000,
                    'temperature': 0.0
                },
                timeout=60
            )
            
            if not openrouter_response.ok:
                error_text = openrouter_response.text
                print(f"[@mcp_proxy] ❌ OpenRouter error: {openrouter_response.status_code}")
                print(f"[@mcp_proxy] Error details: {error_text}")
                return jsonify({
                    'success': False,
                    'error': f'OpenRouter error {openrouter_response.status_code}: {error_text}'
                }), 500
            
            response_data = openrouter_response.json()
            message = response_data['choices'][0]['message']
            
            print(f"[@mcp_proxy] OpenRouter response received")
            print(f"[@mcp_proxy] Message keys: {list(message.keys())}")
            
            # Add assistant message to history
            messages.append(message)
            
            # Check if model wants to call a tool
            if 'tool_calls' in message and message['tool_calls']:
                # Model called one or more tools - execute the first one
                tool_call = message['tool_calls'][0]
                function_name = tool_call['function']['name']
                function_args_str = tool_call['function']['arguments']
                function_args = json.loads(function_args_str) if isinstance(function_args_str, str) else function_args_str
                
                print(f"[@mcp_proxy] ✅ AI decided to call tool: {function_name}")
                print(f"[@mcp_proxy] Tool arguments: {json.dumps(function_args, indent=2)}")
                
                # Inject context if not provided by AI
                if 'device_id' not in function_args and device_id:
                    function_args['device_id'] = device_id
                if 'host_name' not in function_args and host_name:
                    function_args['host_name'] = host_name
                if 'team_id' not in function_args and team_id:
                    function_args['team_id'] = team_id
                
                # Add userinterface_name for tools that need it
                if function_name in ['navigate_to_node', 'verify_device_state']:
                    if 'userinterface_name' not in function_args and userinterface_name:
                        function_args['userinterface_name'] = userinterface_name
                
                # Add tree_id for navigation
                if function_name == 'navigate_to_node':
                    if 'tree_id' not in function_args and tree_id:
                        function_args['tree_id'] = tree_id
                
                # ✅ AUTO-WRAP: Transform flat action parameters into actions array
                if function_name == 'execute_device_action' and 'actions' not in function_args:
                    action_obj = {
                        'command': function_args.pop('command', ''),
                        'params': {}
                    }
                    standard_keys = {'device_id', 'host_name', 'team_id', 'userinterface_name'}
                    for key in list(function_args.keys()):
                        if key not in standard_keys:
                            action_obj['params'][key] = function_args.pop(key)
                    function_args['actions'] = [action_obj]
                    print(f"[@mcp_proxy] ✅ Auto-wrapped flat action params into actions array")
                
                # ✅ AUTO-WRAP: Transform flat verification parameters into verifications array
                if function_name == 'verify_device_state' and 'verifications' not in function_args:
                    verification_obj = {
                        'command': function_args.pop('element_id', '') or function_args.pop('command', ''),
                        'verification_type': function_args.pop('verification_type', 'image'),
                        'params': {}
                    }
                    standard_keys = {'device_id', 'host_name', 'team_id', 'userinterface_name', 'tree_id', 'node_id'}
                    for key in list(function_args.keys()):
                        if key not in standard_keys:
                            verification_obj['params'][key] = function_args.pop(key)
                    function_args['verifications'] = [verification_obj]
                    print(f"[@mcp_proxy] ✅ Auto-wrapped flat verification params into verifications array")
                
                print(f"[@mcp_proxy] Final arguments (after context injection): {json.dumps(function_args, indent=2)}")
                
                # Call MCP tool
                print(f"[@mcp_proxy] Calling MCP server tool: {function_name}")
                mcp_result = mcp_server.handle_tool_call(function_name, function_args)
                
                print(f"[@mcp_proxy] MCP result keys: {list(mcp_result.keys())}")
                
                # Parse MCP response
                if mcp_result.get('isError'):
                    error_text = mcp_result['content'][0]['text'] if mcp_result.get('content') else 'Unknown error'
                    print(f"[@mcp_proxy] ❌ MCP tool error: {error_text}")
                    return jsonify({
                        'success': False,
                        'error': f'MCP tool error: {error_text}',
                        'iterations': iteration,
                        'tool_calls': all_tool_calls
                    }), 500
                
                # Extract result from MCP response
                result_text = mcp_result['content'][0]['text'] if mcp_result.get('content') else '{}'
                
                # Try to parse as JSON, fallback to raw text
                try:
                    tool_result = json.loads(result_text)
                except json.JSONDecodeError:
                    tool_result = {'message': result_text}
                
                # Check if execution tools succeeded
                execution_success = True
                if 'success' in tool_result:
                    execution_success = tool_result['success']
                
                if execution_success:
                    print(f"[@mcp_proxy] ✅ MCP tool executed successfully")
                else:
                    error_msg = tool_result.get('error') or tool_result.get('message') or 'Execution failed'
                    print(f"[@mcp_proxy] ❌ Tool execution failed: {error_msg}")
                    all_tool_calls.append({
                        'tool': function_name,
                        'arguments': function_args,
                        'result': tool_result
                    })
                    return jsonify({
                        'success': False,
                        'error': f'Tool execution failed: {error_msg}',
                        'result': tool_result,
                        'tool_calls': all_tool_calls,
                        'iterations': iteration
                    }), 500
                
                # Record tool call
                all_tool_calls.append({
                    'tool': function_name,
                    'arguments': function_args,
                    'result': tool_result
                })
                
                # Check if this is an execution tool (final step)
                if function_name in ['execute_device_action', 'verify_device_state', 'navigate_to_node', 'capture_screenshot']:
                    # Execution tool succeeded - we're done!
                    print(f"[@mcp_proxy] ✅ Execution tool completed successfully - ending conversation")
                    final_result = tool_result
                    break
                
                # Add tool result to conversation history for next turn
                # OpenAI format: Add tool response message
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call['id'],
                    'name': function_name,
                    'content': result_text
                })
                
                # Continue loop for next AI decision
                
            else:
                # Model didn't call a tool - just returned text (task completed or can't proceed)
                print(f"[@mcp_proxy] ⚠️ AI did not call any tool")
                print(f"[@mcp_proxy] AI response: {message.get('content', 'No response')}")
                final_result = {
                    'message': message.get('content', 'No response from AI')
                }
                break  # End conversation
        
        # Return final result
        return jsonify({
            'success': True,
            'result': final_result,
            'tool_calls': all_tool_calls,
            'iterations': iteration,
            'ai_response': message.get('content', '')
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[@mcp_proxy] 💥 Exception: {str(e)}")
        print(f"[@mcp_proxy] Traceback:\n{error_trace}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500


@server_mcp_proxy_bp.route('/list-tools', methods=['GET'])
def list_tools():
    """
    List available MCP tools (for debugging/discovery)
    """
    try:
        available_tools = mcp_server.get_available_tools()
        return jsonify({
            'success': True,
            'tools': [
                {
                    'name': tool['name'],
                    'description': tool['description'][:200]  # Truncated
                }
                for tool in available_tools
            ],
            'count': len(available_tools)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

