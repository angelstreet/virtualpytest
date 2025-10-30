"""
Host Builder Routes - Standard Blocks API

Provides endpoints for frontend to fetch and execute standard block schemas.
"""

from flask import Blueprint, request, jsonify
from backend_host.src.builder.block_registry import get_available_blocks, execute_block

# Create blueprint
host_builder_bp = Blueprint('host_builder', __name__, url_prefix='/host/builder')


@host_builder_bp.route('/blocks', methods=['GET', 'OPTIONS'])
def get_blocks():
    """
    Get all available standard blocks with their parameter schemas.
    
    Frontend uses this to render input fields dynamically.
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        from flask import current_app
        response = current_app.response_class()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    try:
        print(f"[@route:host_builder:get_blocks] Fetching available standard blocks")
        
        # Get all blocks from registry (auto-discovers from blocks/ folder)
        blocks = get_available_blocks()
        
        print(f"[@route:host_builder:get_blocks] Found {len(blocks)} blocks")
        
        response = jsonify({
            'success': True,
            'blocks': blocks
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        print(f"[@route:host_builder:get_blocks] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        response = jsonify({
            'success': False,
            'error': f'Failed to fetch blocks: {str(e)}'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@host_builder_bp.route('/execute', methods=['POST', 'OPTIONS'])
def execute_standard_block():
    """
    Execute a standard block using ExecutionOrchestrator (unified logging + screenshots)
    
    Request body:
        {
            "command": "sleep",
            "params": {"duration": 2.0},
            "device_id": "device1",
            "team_id": "team1"  // Optional
        }
    
    Returns:
        {
            "success": true/false,
            "message": "...",
            "logs": "...",  // Captured stdout/stderr
            "before_screenshot_url": "...",  // Optional
            "after_screenshot_url": "...",  // Optional
            "result": {...}  // Optional result data
        }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        from flask import current_app
        response = current_app.response_class()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    try:
        data = request.get_json() or {}
        command = data.get('command')
        params = data.get('params', {})
        device_id = data.get('device_id', 'device1')
        team_id = data.get('team_id')
        
        print(f"[@route:host_builder:execute] Executing standard block: {command}")
        print(f"[@route:host_builder:execute] Params: {params}")
        print(f"[@route:host_builder:execute] Device: {device_id}")
        
        # Validate
        if not command:
            return jsonify({
                'success': False,
                'error': 'command is required'
            }), 400
        
        # Get device from app context
        from flask import current_app
        host_devices = getattr(current_app, 'host_devices', {})
        if device_id not in host_devices:
            return jsonify({
                'success': False,
                'error': f'Device {device_id} not found'
            }), 404
        
        device = host_devices[device_id]
        
        # Build blocks array (single block)
        blocks = [{
            'command': command,
            'params': params
        }]
        
        # Execute via orchestrator for unified logging + screenshots
        from backend_host.src.orchestrator import ExecutionOrchestrator
        result = ExecutionOrchestrator.execute_blocks(
            device=device,
            blocks=blocks,
            team_id=team_id,
            context=None
        )
        
        print(f"[@route:host_builder:execute] Block execution completed: success={result.get('success')}")
        
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200 if result.get('success') else 500
        
    except Exception as e:
        print(f"[@route:host_builder:execute] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        response = jsonify({
            'success': False,
            'error': f'Block execution error: {str(e)}'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
