#!/usr/bin/env python3
"""
Server-Side Script Utilities

Server-specific script utilities for script management and analysis.
Only contains functions needed by the server (no host-specific functionality).
"""

import os
import glob

# Import host-specific function for campaign executor (temporary - should be refactored)
try:
    import sys
    # Add backend_host to path for importing ai_utils
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    backend_host_path = os.path.join(project_root, 'backend_host', 'src')
    if backend_host_path not in sys.path:
        sys.path.insert(0, backend_host_path)
    from lib.utils.ai_utils import setup_script_environment
except ImportError:
    # Fallback if host utils not available
    def setup_script_environment(script_name: str = "script"):
        return {'success': False, 'error': 'Host utilities not available on server'}


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
    """Get full path to a script file"""
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
    """List all available Python scripts in the scripts directory"""
    scripts_dir = get_scripts_directory()
    
    if not os.path.exists(scripts_dir):
        return []
    
    # Find all Python files in the scripts directory
    script_pattern = os.path.join(scripts_dir, '*.py')
    script_files = glob.glob(script_pattern)
    
    # Extract just the filenames without path and extension
    available_scripts = []
    for script_file in script_files:
        filename = os.path.basename(script_file)
        script_name = os.path.splitext(filename)[0]  # Remove .py extension
        
        # Hide internal AI executor script from user interface
        if script_name == 'ai_testcase_executor':
            continue
            
        available_scripts.append(script_name)
    
    # Sort alphabetically
    available_scripts.sort()
    
    return available_scripts
