"""
Set Metadata Block

Push variables to metadata for DB storage.
"""

from typing import Dict, Any, Optional
from backend_host.src.builder.decorators import capture_logs
from shared.src.lib.schemas.param_types import create_param, ParamType


def get_block_info() -> Dict[str, Any]:
    """Return block metadata for registration"""
    return {
        'command': 'set_metadata',
        'label': 'Set Metadata',  # Short name for toolbox
        'description': 'Push variables to metadata',  # Longer description
        'params': {
            'source_variable': create_param(
                ParamType.STRING,
                required=False,
                default=None,
                description="Variable name to push (leave empty to push all variables)",
                placeholder="Enter variable name or leave empty"
            ),
            'mode': create_param(
                ParamType.ENUM,
                required=False,
                default='set',
                choices=[
                    {'label': 'Set (replace all)', 'value': 'set'},
                    {'label': 'Append (merge)', 'value': 'append'}
                ],
                description="How to update metadata"
            )
        },
        'block_type': 'standard',
        'description': 'Push variables to metadata for DB storage'
    }


@capture_logs
def execute(source_variable: Optional[str] = None, mode: str = 'set', context=None, **kwargs) -> Dict[str, Any]:
    """
    Push variables to metadata for DB storage.
    
    Args:
        source_variable: Variable name to push (None = push all variables)
        mode: 'set' (replace) or 'append' (merge) - default 'set'
        context: Execution context
        **kwargs: Additional parameters
        
    Returns:
        Dict with success status
    """
    print(f"[@block:set_metadata] Pushing to metadata - mode: {mode}, source: {source_variable or 'ALL'}")
    
    try:
        if not context:
            return {
                'success': False,
                'message': 'No execution context provided'
            }
        
        # Initialize variables and metadata if not exists
        if not hasattr(context, 'variables'):
            context.variables = {}
        if not hasattr(context, 'metadata'):
            context.metadata = {}
        
        # Determine what to push
        if source_variable:
            # Push specific variable
            if source_variable not in context.variables:
                return {
                    'success': False,
                    'message': f'Variable "{source_variable}" not found in context'
                }
            
            data_to_push = {source_variable: context.variables[source_variable]}
        else:
            # Push all variables
            data_to_push = context.variables.copy()
        
        # Apply based on mode
        if mode == 'set':
            # Replace entire metadata
            context.metadata = data_to_push
            print(f"[@block:set_metadata] Replaced metadata with {len(data_to_push)} variables")
        elif mode == 'append':
            # Merge into existing metadata
            context.metadata.update(data_to_push)
            print(f"[@block:set_metadata] Merged {len(data_to_push)} variables into metadata")
        else:
            return {
                'success': False,
                'message': f'Invalid mode: {mode}. Use "set" or "append"'
            }
        
        print(f"[@block:set_metadata] SUCCESS - Metadata now contains {len(context.metadata)} keys")
        
        return {
            'success': True,
            'message': f'Metadata updated successfully ({mode} mode)'
        }
        
    except Exception as e:
        error_msg = f"Error setting metadata: {str(e)}"
        print(f"[@block:set_metadata] ERROR: {error_msg}")
        
        return {
            'success': False,
            'message': error_msg
        }

