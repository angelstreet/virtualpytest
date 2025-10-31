"""
Evaluate Condition Block

Evaluate a condition and branch execution flow based on operand types and conditions.

Supports:
- int: >, <, >=, <=, =
- str: equal, contains, dont_contain
- list: equal, contain, dont_contain, index_of
- dict: equal, contain_key, contain_value, dont_contain_key, dont_contain_value, index_of_key

Returns:
- result_success: 0 (success), 1 (failure), -1 (error)
- error_msg: Error message if any
- result_output: The evaluation result (bool, int, or other)
"""

from typing import Dict, Any, Union, List
import re
from backend_host.src.builder.decorators import capture_logs
from shared.src.lib.schemas.param_types import create_param, ParamType


# Condition mappings per operand type
OPERAND_CONDITIONS = {
    'int': {
        'greater_than': {'label': 'Greater than (>)', 'value': 'greater_than', 'output_type': 'bool'},
        'less_than': {'label': 'Less than (<)', 'value': 'less_than', 'output_type': 'bool'},
        'greater_equal': {'label': 'Greater or equal (>=)', 'value': 'greater_equal', 'output_type': 'bool'},
        'less_equal': {'label': 'Less or equal (<=)', 'value': 'less_equal', 'output_type': 'bool'},
        'equal': {'label': 'Equal (=)', 'value': 'equal', 'output_type': 'bool'}
    },
    'str': {
        'equal': {'label': 'Equal', 'value': 'equal', 'output_type': 'bool'},
        'contains': {'label': 'Contains', 'value': 'contains', 'output_type': 'bool'},
        'dont_contain': {'label': 'Does not contain', 'value': 'dont_contain', 'output_type': 'bool'}
    },
    'list': {
        'equal': {'label': 'Equal', 'value': 'equal', 'output_type': 'bool'},
        'contain': {'label': 'Contains', 'value': 'contain', 'output_type': 'bool'},
        'dont_contain': {'label': 'Does not contain', 'value': 'dont_contain', 'output_type': 'bool'},
        'index_of': {'label': 'Index of', 'value': 'index_of', 'output_type': 'int'}
    },
    'dict': {
        'equal': {'label': 'Equal', 'value': 'equal', 'output_type': 'bool'},
        'contain_key': {'label': 'Contains key', 'value': 'contain_key', 'output_type': 'bool'},
        'contain_value': {'label': 'Contains value', 'value': 'contain_value', 'output_type': 'bool'},
        'dont_contain_key': {'label': 'Does not contain key', 'value': 'dont_contain_key', 'output_type': 'bool'},
        'dont_contain_value': {'label': 'Does not contain value', 'value': 'dont_contain_value', 'output_type': 'bool'},
        'index_of_key': {'label': 'Index of key', 'value': 'index_of_key', 'output_type': 'int'}
    }
}


def get_block_info() -> Dict[str, Any]:
    """Return block metadata for registration"""
    return {
        'command': 'evaluate_condition',
        'label': 'Evaluate Condition',
        'description': 'Evaluate condition with typed operands and dynamic conditions',
        'params': {
            'operand_type': create_param(
                ParamType.ENUM,
                required=True,
                default='int',
                choices=[
                    {'label': 'Integer', 'value': 'int'},
                    {'label': 'String', 'value': 'str'},
                    {'label': 'List', 'value': 'list'},
                    {'label': 'Dictionary', 'value': 'dict'}
                ],
                description="Type of operands to compare"
            ),
            'condition': create_param(
                ParamType.ENUM,
                required=True,
                default='equal',
                choices=[
                    {'label': 'Equal', 'value': 'equal'}
                ],
                description="Condition to evaluate (dynamically populated based on operand_type)"
            ),
            'left_operand': create_param(
                ParamType.STRING,
                required=True,
                default='',
                description="Left operand (variable reference {var} or literal value)",
                placeholder="Enter value or {variable_name}"
            ),
            'right_operand': create_param(
                ParamType.STRING,
                required=True,
                default='',
                description="Right operand (variable reference {var} or literal value)",
                placeholder="Enter value or {variable_name}"
            )
        },
        'block_type': 'standard',
        'output_schema': {
            'result_success': 'int',  # 0=success, 1=failure, -1=error
            'error_msg': 'str',
            'result_output': 'any'  # bool, int, or other depending on condition
        }
    }


def _resolve_operand(operand_str: str, context, operand_type: str) -> Any:
    """
    Resolve operand from string - either variable reference or literal value.
    
    Variable reference format: {variable_name}
    Literal values: parsed based on operand_type
    
    Args:
        operand_str: The operand string
        context: Execution context with variables
        operand_type: Expected type (int, str, list, dict)
        
    Returns:
        Resolved value with correct type
        
    Raises:
        ValueError: If operand cannot be resolved or converted
    """
    operand_str = operand_str.strip()
    
    # Check for variable reference: {variable_name}
    var_match = re.match(r'^\{(.+?)\}$', operand_str)
    if var_match:
        var_name = var_match.group(1).strip()
        if not context or not hasattr(context, 'variables') or not context.variables:
            raise ValueError(f"Variable '{var_name}' not found in context")
        
        if var_name not in context.variables:
            raise ValueError(f"Variable '{var_name}' not found in context")
        
        value = context.variables[var_name]
        print(f"[@block:evaluate_condition] Resolved variable '{var_name}' = {value} (type: {type(value).__name__})")
        return value
    
    # Parse literal value based on operand_type
    try:
        if operand_type == 'int':
            return int(operand_str)
        elif operand_type == 'str':
            # Remove surrounding quotes if present
            if (operand_str.startswith('"') and operand_str.endswith('"')) or \
               (operand_str.startswith("'") and operand_str.endswith("'")):
                return operand_str[1:-1]
            return operand_str
        elif operand_type == 'list':
            # Try to parse as Python list
            import ast
            return ast.literal_eval(operand_str)
        elif operand_type == 'dict':
            # Try to parse as Python dict
            import ast
            return ast.literal_eval(operand_str)
    except Exception as e:
        raise ValueError(f"Failed to parse operand '{operand_str}' as {operand_type}: {str(e)}")
    
    return operand_str


def _validate_operand_type(value: Any, expected_type: str) -> bool:
    """Validate that value matches expected type"""
    type_map = {
        'int': int,
        'str': str,
        'list': list,
        'dict': dict
    }
    expected_python_type = type_map.get(expected_type)
    return isinstance(value, expected_python_type)


def _evaluate_int_condition(left: int, right: int, condition: str) -> bool:
    """Evaluate integer condition"""
    if condition == 'greater_than':
        return left > right
    elif condition == 'less_than':
        return left < right
    elif condition == 'greater_equal':
        return left >= right
    elif condition == 'less_equal':
        return left <= right
    elif condition == 'equal':
        return left == right
    else:
        raise ValueError(f"Unknown int condition: {condition}")


def _evaluate_str_condition(left: str, right: str, condition: str) -> bool:
    """Evaluate string condition"""
    if condition == 'equal':
        return left == right
    elif condition == 'contains':
        return right in left
    elif condition == 'dont_contain':
        return right not in left
    else:
        raise ValueError(f"Unknown str condition: {condition}")


def _evaluate_list_condition(left: List, right: Any, condition: str) -> Union[bool, int]:
    """Evaluate list condition"""
    if condition == 'equal':
        return left == right
    elif condition == 'contain':
        return right in left
    elif condition == 'dont_contain':
        return right not in left
    elif condition == 'index_of':
        try:
            return left.index(right)
        except ValueError:
            return -1  # Not found
    else:
        raise ValueError(f"Unknown list condition: {condition}")


def _evaluate_dict_condition(left: Dict, right: Any, condition: str) -> Union[bool, int]:
    """Evaluate dict condition"""
    if condition == 'equal':
        return left == right
    elif condition == 'contain_key':
        return right in left
    elif condition == 'contain_value':
        return right in left.values()
    elif condition == 'dont_contain_key':
        return right not in left
    elif condition == 'dont_contain_value':
        return right not in left.values()
    elif condition == 'index_of_key':
        # Get index position of key in dict (insertion order in Python 3.7+)
        keys_list = list(left.keys())
        try:
            return keys_list.index(right)
        except ValueError:
            return -1  # Not found
    else:
        raise ValueError(f"Unknown dict condition: {condition}")


@capture_logs
def execute(
    operand_type: str = 'int',
    condition: str = 'equal',
    left_operand: str = '',
    right_operand: str = '',
    context=None,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute condition evaluation.
    
    Args:
        operand_type: Type of operands (int, str, list, dict)
        condition: Condition to evaluate (depends on operand_type)
        left_operand: Left operand (variable reference or literal)
        right_operand: Right operand (variable reference or literal)
        context: Execution context with variables
        **kwargs: Additional parameters
        
    Returns:
        Dict with:
        - result_success: 0 (success), 1 (failure), -1 (error)
        - error_msg: Error message if error occurred
        - result_output: The evaluation result (bool or int)
    """
    print(f"[@block:evaluate_condition] Evaluating: type={operand_type}, condition={condition}, "
          f"left={left_operand}, right={right_operand}")
    
    try:
        # Validate inputs
        if not left_operand or not right_operand:
            return {
                'result_success': -1,
                'error_msg': 'Both left_operand and right_operand are required',
                'result_output': None
            }
        
        if operand_type not in OPERAND_CONDITIONS:
            return {
                'result_success': -1,
                'error_msg': f"Invalid operand_type: {operand_type}",
                'result_output': None
            }
        
        if condition not in OPERAND_CONDITIONS[operand_type]:
            return {
                'result_success': -1,
                'error_msg': f"Invalid condition '{condition}' for type '{operand_type}'",
                'result_output': None
            }
        
        # Resolve operands
        try:
            left_value = _resolve_operand(left_operand, context, operand_type)
            right_value = _resolve_operand(right_operand, context, operand_type)
        except ValueError as e:
            return {
                'result_success': -1,
                'error_msg': f"Operand resolution error: {str(e)}",
                'result_output': None
            }
        
        # Validate types
        if not _validate_operand_type(left_value, operand_type):
            return {
                'result_success': -1,
                'error_msg': f"Left operand type mismatch: expected {operand_type}, got {type(left_value).__name__}",
                'result_output': None
            }
        
        # Right operand type validation depends on condition
        # For 'contain', 'dont_contain' in list, right can be any type
        # For 'index_of', right can be any type
        # For dict key operations, right should be hashable
        # For other operations, types should match
        if condition not in ['contain', 'dont_contain', 'index_of', 'contain_key', 'contain_value', 
                             'dont_contain_key', 'dont_contain_value', 'index_of_key']:
            if not _validate_operand_type(right_value, operand_type):
                return {
                    'result_success': -1,
                    'error_msg': f"Right operand type mismatch: expected {operand_type}, got {type(right_value).__name__}",
                    'result_output': None
                }
        
        # Evaluate condition
        result_output = None
        
        if operand_type == 'int':
            result_output = _evaluate_int_condition(left_value, right_value, condition)
        elif operand_type == 'str':
            result_output = _evaluate_str_condition(left_value, right_value, condition)
        elif operand_type == 'list':
            result_output = _evaluate_list_condition(left_value, right_value, condition)
        elif operand_type == 'dict':
            result_output = _evaluate_dict_condition(left_value, right_value, condition)
        
        # Store result in context
        if context:
            context.variables = context.variables or {}
            context.variables['result_output'] = result_output
            context.variables['result_success'] = 0
            context.variables['error_msg'] = ''
        
        # Determine success code based on result
        # For boolean results: True = success (0), False = failure (1)
        # For integer results (index): >= 0 = success (0), -1 = failure (1)
        result_success = 0
        if isinstance(result_output, bool):
            result_success = 0 if result_output else 1
        elif isinstance(result_output, int):
            result_success = 0 if result_output >= 0 else 1
        
        print(f"[@block:evaluate_condition] Result: {result_output} (success_code={result_success})")
        
        return {
            'result_success': result_success,
            'error_msg': '',
            'result_output': result_output
        }
        
    except Exception as e:
        error_msg = f"Unexpected error evaluating condition: {str(e)}"
        print(f"[@block:evaluate_condition] ERROR: {error_msg}")
        
        if context:
            context.variables = context.variables or {}
            context.variables['result_success'] = -1
            context.variables['error_msg'] = error_msg
            context.variables['result_output'] = None
        
        return {
            'result_success': -1,
            'error_msg': error_msg,
            'result_output': None
        }

