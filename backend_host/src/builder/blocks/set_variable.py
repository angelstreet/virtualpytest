"""
Set Variable Block

Set a variable value in execution context for later use.
"""

from typing import Dict, Any
from backend_host.src.builder.decorators import capture_logs
from shared.src.lib.schemas.param_types import create_param, ParamType


def get_block_info() -> Dict[str, Any]:
    """Return block metadata for registration"""
    return {
        'command': 'set_variable',
        'label': 'Set Variable',  # Short name for toolbox
        'description': 'Set a variable value',  # Longer description
        'params': {
            'variable_name': create_param(
                ParamType.STRING,
                required=True,
                default='',
                description="Variable name to set",
                placeholder="Enter variable name"
            ),
            'variable_value': create_param(
                ParamType.STRING,
                required=True,
                default='',
                description="Value to store in the variable",
                placeholder="Enter value"
            )
        },
        'block_type': 'standard'
    }


@capture_logs
def execute(variable_name: str, variable_value: Any, context=None, **kwargs) -> Dict[str, Any]:
    """
    Set a variable in execution context.
    
    Args:
        variable_name: Name of the variable to set
        variable_value: Value to store (any type)
        context: Execution context
        **kwargs: Additional parameters
        
    Returns:
        Dict with success status
    """
    print(f"[@block:set_variable] Setting variable: {variable_name} = {variable_value}")
    
    try:
        if not context:
            return {
                'success': False,
                'message': 'No execution context provided'
            }
        
        # Initialize variables dict if not exists
        if not hasattr(context, 'variables'):
            context.variables = {}
        
        # Store variable
        context.variables[variable_name] = variable_value
        
        print(f"[@block:set_variable] SUCCESS - Stored in context.variables['{variable_name}']")
        
        return {
            'success': True,
            'message': f'Variable "{variable_name}" set successfully'
        }
        
    except Exception as e:
        error_msg = f"Error setting variable: {str(e)}"
        print(f"[@block:set_variable] ERROR: {error_msg}")
        
        return {
            'success': False,
            'message': error_msg
        }

