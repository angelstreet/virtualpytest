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
    Execute natural language prompt via OpenRouter with function calling (MCP-style)
    
    Simple proxy: expose MCP tools to AI, let AI decide what to call.
    No system prompt engineering, no multi-turn complexity.
    
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
      "result": { ... tool result ... },
      "tool_name": "execute_device_action",
      "tool_arguments": {...}
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
        
        print(f"[@mcp_proxy] Received prompt: {prompt}")
        print(f"[@mcp_proxy] Context - device: {device_id}, host: {host_name}, interface: {userinterface_name}, team_id: {team_id}")
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt required'}), 400
        
        # Get OpenRouter API key
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'OPENROUTER_API_KEY not configured in .env'}), 500
        
        # Get available MCP tools - expose them as-is
        available_tools = mcp_server.get_available_tools()
        
        # Convert MCP tool schemas to OpenRouter tools format
        tools = []
        for tool in available_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool['name'],
                    "description": tool['description'],  # Use full description - no truncation
                    "parameters": tool['inputSchema']
                }
            })
        
        print(f"[@mcp_proxy] Prepared {len(tools)} tools for AI")
        
        # Minimal system message - just provide context, no instructions
        system_message = f'''Device automation context:
- Device: {device_id} on {host_name}
- Interface: {userinterface_name}
- Team: {team_id}
- Tree: {tree_id or 'none'}'''

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
                'messages': [
                    {'role': 'system', 'content': system_message},
                    {'role': 'user', 'content': prompt}
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
            return jsonify({
                'success': False,
                'error': f'OpenRouter error {openrouter_response.status_code}: {error_text}'
            }), 500
        
        response_data = openrouter_response.json()
        message = response_data['choices'][0]['message']
        
        print(f"[@mcp_proxy] OpenRouter response: {list(message.keys())}")
        
        # Check if AI called a tool
        if 'tool_calls' not in message or not message['tool_calls']:
            print(f"[@mcp_proxy] ⚠️ AI did not call any tool")
            return jsonify({
                'success': False,
                'error': 'AI did not call any tool',
                'ai_response': message.get('content', '')
            }), 400
        
        # Execute the tool the AI chose
        tool_call = message['tool_calls'][0]
        function_name = tool_call['function']['name']
        function_args_str = tool_call['function']['arguments']
        function_args = json.loads(function_args_str) if isinstance(function_args_str, str) else function_args_str
        
        print(f"[@mcp_proxy] AI chose tool: {function_name}")
        print(f"[@mcp_proxy] Arguments: {json.dumps(function_args, indent=2)}")
        
        # Inject context if missing
        if 'device_id' not in function_args and device_id:
            function_args['device_id'] = device_id
        if 'host_name' not in function_args and host_name:
            function_args['host_name'] = host_name
        if 'team_id' not in function_args and team_id:
            function_args['team_id'] = team_id
        if function_name in ['navigate_to_node', 'verify_device_state']:
            if 'userinterface_name' not in function_args and userinterface_name:
                function_args['userinterface_name'] = userinterface_name
        if function_name == 'navigate_to_node':
            if 'tree_id' not in function_args and tree_id:
                function_args['tree_id'] = tree_id
        
        # Auto-wrap flat params into arrays for execute_device_action
        if function_name == 'execute_device_action' and 'actions' not in function_args:
            action_obj = {'command': function_args.pop('command', ''), 'params': {}}
            standard_keys = {'device_id', 'host_name', 'team_id', 'userinterface_name'}
            for key in list(function_args.keys()):
                if key not in standard_keys:
                    action_obj['params'][key] = function_args.pop(key)
            function_args['actions'] = [action_obj]
        
        # Auto-wrap flat params into arrays for verify_device_state  
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
        
        print(f"[@mcp_proxy] Final arguments: {json.dumps(function_args, indent=2)}")
        
        # Call MCP tool
        print(f"[@mcp_proxy] Calling MCP tool: {function_name}")
        mcp_result = mcp_server.handle_tool_call(function_name, function_args)
        
        # Parse result
        if mcp_result.get('isError'):
            error_text = mcp_result['content'][0]['text'] if mcp_result.get('content') else 'Unknown error'
            print(f"[@mcp_proxy] ❌ MCP error: {error_text}")
            return jsonify({
                'success': False,
                'error': f'MCP error: {error_text}',
                'tool_name': function_name,
                'tool_arguments': function_args
            }), 500
        
        result_text = mcp_result['content'][0]['text'] if mcp_result.get('content') else '{}'
        
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            result = {'message': result_text}
        
        # Check success for execution tools
        execution_success = True
        if 'success' in result:
            execution_success = result['success']
        
        if execution_success:
            print(f"[@mcp_proxy] ✅ Tool executed successfully")
            return jsonify({
                'success': True,
                'result': result,
                'tool_name': function_name,
                'tool_arguments': function_args,
                'ai_response': message.get('content', '')
            })
        else:
            error_msg = result.get('error') or result.get('message') or 'Execution failed'
            print(f"[@mcp_proxy] ❌ Tool execution failed: {error_msg}")
            return jsonify({
                'success': False,
                'error': f'Tool execution failed: {error_msg}',
                'result': result,
                'tool_name': function_name,
                'tool_arguments': function_args
            }), 500
        
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

