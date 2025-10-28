"""
Builder Module

Contains builder-specific blocks and utilities for test case construction.
These are NOT controllers - they're functions used during test case execution.
"""

from .standard_blocks import getMenuInfo, set_variable, set_metadata

__all__ = [
    'getMenuInfo',
    'set_variable', 
    'set_metadata',
]

