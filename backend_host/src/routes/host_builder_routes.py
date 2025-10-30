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
    Execute a standard block (sleep, loop, set_variable, etc.)
    
    Request body:
        {
            "command": "sleep",
            "params": {"duration": 2.0},
            "device_id": "device1"
        }
    
    Returns:
        {
            "success": true/false,
            "message": "...",
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
        
        print(f"[@route:host_builder:execute] Executing standard block: {command}")
        print(f"[@route:host_builder:execute] Params: {params}")
        print(f"[@route:host_builder:execute] Device: {device_id}")
        
        # Validate
        if not command:
            return jsonify({
                'success': False,
                'error': 'command is required'
            }), 400
        
        # Get device context (optional - some blocks may not need it)
        context = None
        try:
            from backend_host.src.devices.device_manager import DeviceManager
            device_manager = DeviceManager()
            device = device_manager.get_device(device_id)
            
            # Create minimal context object
            context = type('Context', (), {
                'device': device,
                'device_id': device_id,
                'variables': {},
                'metadata': {}
            })()
            
            print(f"[@route:host_builder:execute] Device context created for {device_id}")
        except Exception as e:
            print(f"[@route:host_builder:execute] Warning: Could not create device context: {e}")
            # Continue without device context - some blocks don't need it
        
        # Execute block using registry
        result = execute_block(command, params=params, context=context)
        
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
