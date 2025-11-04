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
    Execute natural language prompt via OpenRouter with function calling
    
    Request body:
    {
      "prompt": "Swipe up on the device",
      "device_id": "device1",
      "host_name": "sunri-pi1", 
      "userinterface_name": "horizon_android_mobile",
      "team_id": "team_1",
      "tree_id": "bbf2d95d-72c2-4701-80a7-0b9d131a5c38"
    }
    
    Returns:
    {
      "success": true,
      "result": { ... MCP tool result ... },
      "tool_calls": [{"tool": "execute_device_action", "arguments": {...}, "result": {...}}],
      "ai_response": "I executed a swipe up action"
    }
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        device_id = data.get('device_id', 'device1')
        host_name = data.get('host_name', 'sunri-pi1')
        userinterface_name = data.get('userinterface_name')
        team_id = request.args.get('team_id')  # ✅ Get from query params (buildServerUrl adds it there)
        tree_id = data.get('tree_id')
        
        print(f"[@mcp_proxy] Received prompt: {prompt}")
        print(f"[@mcp_proxy] Context - device: {device_id}, host: {host_name}, interface: {userinterface_name}, team_id: {team_id}")
        
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
            # Only include commonly used tools to avoid overwhelming the model
            if tool['name'] in [
                'execute_device_action', 
                'navigate_to_node', 
                'verify_device_state',
                'capture_screenshot',
                'list_actions',
                'list_navigation_nodes'
            ]:
                tools.append({
                    "type": "function",  # NEW: tools format requires type
                    "function": {
                        "name": tool['name'],
                        "description": tool['description'][:500],  # Truncate long descriptions
                        "parameters": tool['inputSchema']
                    }
                })
        
        print(f"[@mcp_proxy] Prepared {len(tools)} tools for AI")
        
        # Call OpenRouter with function calling
        system_prompt = f'''You are a device automation assistant with access to MCP tools.

Current context:
- Device ID: {device_id}
- Host: {host_name}
- Interface: {userinterface_name}
- Team ID: {team_id}
- Tree ID: {tree_id or 'not provided'}

CRITICAL RULES:
1. ALWAYS include device_id, host_name, and team_id when calling functions (use the values from context above)
2. For simple actions like "swipe up", "swipe down", "screenshot", use execute_device_action or capture_screenshot
3. For navigation like "go to home", use navigate_to_node
4. Call only ONE function per request
5. If you're unsure, use list_actions or list_navigation_nodes to discover what's available

Examples:
- "Swipe up" → execute_device_action with swipe_up command
- "Take screenshot" → capture_screenshot
- "Navigate to home" → navigate_to_node with target_node_label="home"'''

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
                'model': 'google/gemini-2.0-flash-001',  # Gemini 2.0 Flash (paid) - excellent tool calling, no rate limits
                'messages': [
                    {
                        'role': 'system',
                        'content': system_prompt
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
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
        
        # Check if model wants to call a tool (NEW: using tool_calls instead of function_call)
        tool_calls = []
        final_result = None
        
        if 'tool_calls' in message and message['tool_calls']:
            # Model called one or more tools - execute the first one
            tool_call = message['tool_calls'][0]  # Take first tool call
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
            if function_name == 'navigate_to_node':
                if 'userinterface_name' not in function_args and userinterface_name:
                    function_args['userinterface_name'] = userinterface_name
                if 'tree_id' not in function_args and tree_id:
                    function_args['tree_id'] = tree_id
            
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
                    'error': f'MCP tool error: {error_text}'
                }), 500
            
            # Extract result from MCP response
            result_text = mcp_result['content'][0]['text'] if mcp_result.get('content') else '{}'
            
            # Try to parse as JSON, fallback to raw text
            try:
                final_result = json.loads(result_text)
            except json.JSONDecodeError:
                final_result = {'message': result_text}
            
            print(f"[@mcp_proxy] ✅ MCP tool executed successfully")
            
            tool_calls.append({
                'tool': function_name,
                'arguments': function_args,
                'result': final_result
            })
        else:
            # Model didn't call a tool - just returned text
            print(f"[@mcp_proxy] ⚠️  AI did not call any tool")
            print(f"[@mcp_proxy] AI response: {message.get('content', 'No response')}")
            final_result = {
                'message': message.get('content', 'No response from AI')
            }
        
        return jsonify({
            'success': True,
            'result': final_result,
            'tool_calls': tool_calls,
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

