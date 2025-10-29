"""
Standard Blocks (Legacy Wrapper)

Builder-specific blocks for test case construction.

New Architecture (as of 2025):
- Standard blocks: backend_host/src/builder/blocks/*.py (pre-built)
- Custom code: Users write Python directly in UI via 'custom_code' block

Each standard block is a separate file with:
1. get_block_info() -> Dict (metadata with typed params)
2. execute(**kwargs) -> Dict (execution logic)

This file provides backward compatibility for legacy imports.
"""

from typing import Dict, Any, List
from backend_host.src.builder.block_registry import get_available_blocks, execute_block


def get_available_standard_blocks() -> List[Dict[str, Any]]:
    """
    Get available standard blocks with typed parameters.
    
    This delegates to the block registry which auto-discovers blocks from:
    - backend_host/src/builder/blocks/*.py
    
    Returns:
        List of block info dicts with metadata
    """
    return get_available_blocks()


def execute_standard_block(command: str, params: Dict[str, Any] = None, context=None) -> Dict[str, Any]:
    """
    Execute a standard block by command name.
    
    This delegates to the block registry.
    
    Args:
        command: Block command name (e.g., 'sleep', 'set_variable')
        params: Block parameters dict
        context: Execution context
        
    Returns:
        Dict with success status and result
    """
    return execute_block(command, params=params or {}, context=context)


# Legacy direct function exports for backward compatibility
def set_variable(variable_name: str, variable_value: Any, context=None, **kwargs) -> Dict[str, Any]:
    """Legacy wrapper for set_variable block"""
    return execute_block('set_variable', params={'variable_name': variable_name, 'variable_value': variable_value}, context=context)


def set_metadata(source_variable: str = None, mode: str = 'set', context=None, **kwargs) -> Dict[str, Any]:
    """Legacy wrapper for set_metadata block"""
    return execute_block('set_metadata', params={'source_variable': source_variable, 'mode': mode}, context=context)
