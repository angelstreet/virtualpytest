"""
Evaluate Condition Block

Evaluate a condition and branch execution flow.
"""

from typing import Dict, Any
from backend_host.src.builder.decorators import capture_logs
from shared.src.lib.schemas.param_types import create_param, ParamType


def get_block_info() -> Dict[str, Any]:
    """Return block metadata for registration"""
    return {
        'command': 'evaluate_condition',
        'label': 'Evaluate Condition',  # Short name for toolbox
        'description': 'Branch based on condition',  # Longer description
        'params': {
            'condition': create_param(
                ParamType.STRING,
                required=True,
                default='',
                description="Condition to evaluate (Python expression)",
                placeholder="Enter condition (e.g., variable > 10)"
            ),
            'comparison_type': create_param(
                ParamType.ENUM,
                required=False,
                default='expression',
                choices=[
                    {'label': 'Python expression', 'value': 'expression'},
                    {'label': 'Equal to', 'value': 'equals'},
                    {'label': 'Greater than', 'value': 'greater'},
                    {'label': 'Less than', 'value': 'less'},
                    {'label': 'Contains', 'value': 'contains'}
                ],
                description="Type of comparison"
            )
        },
        'block_type': 'standard'
    }


@capture_logs
def execute(condition: str = '', comparison_type: str = 'expression', context=None, **kwargs) -> Dict[str, Any]:
    """
    Execute condition evaluation - placeholder for now.
    
    Args:
        condition: Condition string to evaluate
        comparison_type: Type of comparison
        context: Execution context
        **kwargs: Additional parameters
        
    Returns:
        Dict with success status and result
    """
    print(f"[@block:evaluate_condition] Condition placeholder - condition={condition}, type={comparison_type}")
    
    try:
        # TODO: Implement condition evaluation logic
        # For now, just return placeholder result
        result = True  # Placeholder
        
        if context:
            context.variables = context.variables or {}
            context.variables['_last_condition_result'] = result
        
        return {
            'success': True,
            'result': result,
            'message': f'Condition block placeholder (result={result})'
        }
        
    except Exception as e:
        error_msg = f"Error evaluating condition: {str(e)}"
        print(f"[@block:evaluate_condition] ERROR: {error_msg}")
        
        return {
            'success': False,
            'message': error_msg
        }

