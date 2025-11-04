"""
MCP HTTP Routes - HTTP endpoint for Model Context Protocol

Exposes MCP tools via HTTP for external LLM clients (Cursor, Claude Desktop, etc.)
Requires Bearer token authentication for security.
"""

from flask import Blueprint, request, jsonify
import asyncio
import os
from functools import wraps

# Import MCP server - use relative import for proper module resolution
import sys
from pathlib import Path

# Add backend_server/src to path if needed
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from mcp.mcp_server import VirtualPyTestMCPServer

# Create blueprint
mcp_bp = Blueprint('mcp', __name__, url_prefix='/mcp')

# Initialize MCP server instance (singleton)
mcp_server = VirtualPyTestMCPServer()

# Get MCP secret from environment
MCP_SECRET_KEY = os.getenv('MCP_SECRET_KEY', 'vpt_mcp_secret_key_2025')


def require_mcp_auth(f):
    """Decorator to require MCP authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'Missing Authorization header',
                'message': 'MCP endpoint requires Bearer token authentication'
            }), 401
        
        # Check Bearer token format
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Invalid Authorization header format',
                'message': 'Expected: Authorization: Bearer <token>'
            }), 401
        
        # Extract token
        token = auth_header.replace('Bearer ', '').strip()
        
        # Validate token
        if token != MCP_SECRET_KEY:
            return jsonify({
                'error': 'Invalid MCP authentication token',
                'message': 'Access denied'
            }), 403
        
        # Token valid, proceed
        return f(*args, **kwargs)
    
    return decorated_function


@mcp_bp.route('/', methods=['POST'])
@require_mcp_auth
def mcp_endpoint():
    """
    MCP HTTP endpoint - receives tool calls from LLM clients
    
    Request body:
    {
        "tool": "take_control",
        "params": {
            "host_name": "ubuntu-host-1",
            "device_id": "device1",
            "team_id": "team_abc123",
            "tree_id": "main_navigation"
        }
    }
    
    Response:
    {
        "content": [
            {
                "type": "text",
                "text": "..."
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No JSON data provided'
            }), 400
        
        tool_name = data.get('tool')
        params = data.get('params', {})
        
        if not tool_name:
            return jsonify({
                'error': 'tool name is required'
            }), 400
        
        # Handle tool call
        result = asyncio.run(mcp_server.handle_tool_call(tool_name, params))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': f'MCP endpoint error: {str(e)}'
        }), 500


@mcp_bp.route('/tools', methods=['GET'])
@require_mcp_auth
def list_mcp_tools():
    """
    List available MCP tools
    
    Returns:
    {
        "tools": [
            {
                "name": "take_control",
                "description": "...",
                "category": "control",
                "required_params": [...],
                "optional_params": [...]
            },
            ...
        ]
    }
    """
    try:
        tools = mcp_server.get_available_tools()
        return jsonify({
            'tools': tools,
            'count': len(tools)
        })
    except Exception as e:
        return jsonify({
            'error': f'Failed to list tools: {str(e)}'
        }), 500


@mcp_bp.route('/health', methods=['GET'])
def mcp_health():
    """MCP server health check"""
    return jsonify({
        'status': 'healthy',
        'mcp_version': '1.0.0',
        'tools_count': len(mcp_server.tool_handlers)
    })

