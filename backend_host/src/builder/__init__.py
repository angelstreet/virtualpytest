"""
Builder Module

Contains builder-specific blocks and utilities for test case construction.

New Architecture:
- Standard blocks: backend_host/src/builder/blocks/*.py (auto-discovered)
- Custom code: 'custom_code' block allows users to write Python in UI
- Block registry: Auto-discovers and executes blocks

Main exports:
- execute_block: Execute any block by command name
- get_available_blocks: Get list of all available blocks
- Legacy functions: set_variable, set_metadata (for backward compatibility)
"""

from .block_registry import execute_block, get_available_blocks
from .standard_blocks import set_variable, set_metadata, execute_standard_block

__all__ = [
    'execute_block',
    'get_available_blocks', 
    'execute_standard_block',
    'set_variable', 
    'set_metadata',
]

