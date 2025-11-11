#!/usr/bin/env python3
"""
Server-Side Script Utilities

Server-specific script utilities for script management and analysis.
Only contains functions needed by the server (no host-specific functionality).
"""

import os
import glob

# Import from shared library (ai_utils is shared between server and host)
try:
    from shared.src.lib.utils.ai_utils import setup_script_environment
except ImportError:
    # Fallback if shared library not available
    def setup_script_environment(script_name: str = "script"):
        return {'success': False, 'error': 'AI utilities not available'}


def get_scripts_directory() -> str:
    """Get the scripts directory path - single source of truth"""
    # Find project root from server location
    current_dir = os.path.dirname(os.path.abspath(__file__))  # /backend_server/src/lib/utils
    lib_dir = os.path.dirname(current_dir)  # /backend_server/src/lib
    src_dir = os.path.dirname(lib_dir)  # /backend_server/src
    backend_server_dir = os.path.dirname(src_dir)  # /backend_server
    project_root = os.path.dirname(backend_server_dir)  # /virtualpytest
    
    # Use test_scripts folder as the primary scripts location
    return os.path.join(project_root, 'test_scripts')


def get_script_path(script_name: str) -> str:
    """Get full path to a script file (supports subfolder paths like 'gw/get_info')"""
    scripts_dir = get_scripts_directory()
    
    # Handle script names that already have .py extension
    if script_name.endswith('.py'):
        script_path = os.path.join(scripts_dir, script_name)
    else:
        script_path = os.path.join(scripts_dir, f'{script_name}.py')
    
    if not os.path.exists(script_path):
        raise ValueError(f'Script not found: {script_path}')
    
    return script_path


def list_available_scripts() -> list:
    """List all available Python scripts in the scripts directory (supports depth 1 subfolders)"""
    scripts_dir = get_scripts_directory()
    
    if not os.path.exists(scripts_dir):
        return []
    
    available_scripts = []
    
    # Find all Python files in the root scripts directory
    root_pattern = os.path.join(scripts_dir, '*.py')
    root_files = glob.glob(root_pattern)
    
    for script_file in root_files:
        filename = os.path.basename(script_file)
        script_name = os.path.splitext(filename)[0]  # Remove .py extension
        
        # Hide internal AI executor script from user interface
        if script_name == 'ai_testcase_executor':
            continue
            
        available_scripts.append(script_name)
    
    # Find all Python files in subdirectories (depth 1 only)
    subfolder_pattern = os.path.join(scripts_dir, '*', '*.py')
    subfolder_files = glob.glob(subfolder_pattern)
    
    for script_file in subfolder_files:
        # Get relative path from scripts_dir
        rel_path = os.path.relpath(script_file, scripts_dir)
        # Remove .py extension
        script_name = os.path.splitext(rel_path)[0]
        # Replace backslashes with forward slashes for Windows compatibility
        script_name = script_name.replace('\\', '/')
        
        # Hide __pycache__ and other special directories
        if '__pycache__' in script_name or script_name.startswith('.'):
            continue
            
        available_scripts.append(script_name)
    
    # Sort alphabetically
    available_scripts.sort()
    
    return available_scripts
