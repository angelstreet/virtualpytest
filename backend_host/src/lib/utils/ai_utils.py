#!/usr/bin/env python3
"""
AI and Host-Specific Script Utilities

Host-specific functions extracted from script_utils.py to keep them separate from shared utilities.
"""

import sys
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional

from shared.src.lib.utils.app_utils import load_environment_variables
from  backend_host.src.lib.utils.host_utils import get_host_instance, list_available_devices, get_controller
from  backend_host.src.lib.utils.navigation_cache import populate_cache
from  backend_host.src.lib.utils.report_utils import generate_and_upload_script_report
from shared.src.lib.supabase.script_results_db import record_script_execution_start, update_script_execution_result


def setup_script_environment(script_name: str = "script") -> Dict[str, Any]:
    """
    Setup script environment by loading configuration and creating host instance.
    Reuses existing host_utils and app_utils infrastructure.
    
    Args:
        script_name: Name of the script for logging
        
    Returns:
        Dictionary containing host, team_id, and other configuration
    """
    print(f"[@ai_utils:setup_script_environment] Setting up environment for {script_name}...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Load environment variables using shared utility (loads project root .env + service-specific if available)
    print(f"[@ai_utils:setup_script_environment] Loading environment variables...")
    
    # Find the backend_host/src directory for service-specific .env (where device configs are)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.dirname(current_dir)
    shared_dir = os.path.dirname(lib_dir)
    project_root = os.path.dirname(shared_dir)
    backend_host_src = os.path.join(project_root, 'backend_host', 'src')
    
    try:
        # Use the shared load_environment_variables which handles project root .env + service-specific .env
        load_environment_variables(mode='host', calling_script_dir=backend_host_src)
        print(f"[@ai_utils:setup_script_environment] Environment variables loaded successfully")
    except Exception as e:
        print(f"[@ai_utils:setup_script_environment] ERROR: Failed to load environment variables: {e}")
        return {'success': False, 'error': f'Failed to load environment variables: {e}'}
    
    # Check if critical environment variables are set
    host_name = os.getenv('HOST_NAME')
    print(f"[@ai_utils:setup_script_environment] HOST_NAME from environment: {host_name}")
    
    device1_name = os.getenv('DEVICE1_NAME')
    print(f"[@ai_utils:setup_script_environment] DEVICE1_NAME from environment: {device1_name}")
    
    try:
        print(f"[@ai_utils:setup_script_environment] Creating host instance...")
        host = get_host_instance()
        
        device_count = host.get_device_count()
        print(f"[@ai_utils:setup_script_environment] Host created with {device_count} devices")
        
        if device_count == 0:
            return {'success': False, 'error': 'No devices configured'}
        
        # List available devices for debugging
        devices = host.get_devices()
        for device in devices:
            print(f"[@ai_utils:setup_script_environment] Found device: {device.device_name} ({device.device_model})")
        
    except Exception as e:
        import traceback
        print(f"[@ai_utils:setup_script_environment] ERROR: Failed to create host: {e}")
        traceback.print_exc()
        return {'success': False, 'error': f'Failed to create host: {e}'}
    
    team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
    
    return {
        'success': True,
        'host': host,
        'team_id': team_id,
        'script_name': script_name
    }


def select_device(host, device_id: Optional[str] = None, script_name: str = "script") -> Dict[str, Any]:
    """
    Select a device from the host, either specified or first available.
    
    Args:
        host: Host instance
        device_id: Optional specific device ID to select
        script_name: Name of the script for logging
        
    Returns:
        Dictionary with selected device or error
    """
    print(f"[@ai_utils:select_device] Selecting device for {script_name}...")
    available_devices = [d.device_id for d in host.get_devices()]
    print(f"[@ai_utils:select_device] Available devices: {available_devices}")
    
    if device_id:
        print(f"[@ai_utils:select_device] Requested device: {device_id}")
        selected_device = next((d for d in host.get_devices() if d.device_id == device_id), None)
        if not selected_device:
            error_msg = f"Device {device_id} not found. Available: {available_devices}"
            print(f"[@ai_utils:select_device] ERROR: {error_msg}")
            return {'success': False, 'error': error_msg}
    else:
        devices = host.get_devices()
        if not devices:
            error_msg = "No devices available"
            print(f"[@ai_utils:select_device] ERROR: {error_msg}")
            return {'success': False, 'error': error_msg}
        selected_device = devices[0]
        print(f"[@ai_utils:select_device] No device specified, using first available: {selected_device.device_id}")
    
    print(f"[@ai_utils:select_device] Selected device: {selected_device.device_name} ({selected_device.device_model}) [{selected_device.device_id}]")
    return {'success': True, 'device': selected_device}


def execute_script(script_name: str, device_id: str, parameters: str = "") -> Dict[str, Any]:
    """Execute a script with parameters and real-time output streaming using device script executor"""
    start_time = time.time()
    
    # Get device instance and use its script executor
    from  backend_host.src.lib.host_utils import get_device_by_id
    device = get_device_by_id(device_id)
    if not device:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Device {device_id} not found',
            'exit_code': 1,
            'script_name': script_name,
            'device_id': device_id,
            'parameters': parameters,
            'execution_time_ms': int((time.time() - start_time) * 1000),
            'report_url': ""
        }
    
    if not hasattr(device, 'script_executor'):
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Device {device_id} does not have script executor',
            'exit_code': 1,
            'script_name': script_name,
            'device_id': device_id,
            'parameters': parameters,
            'execution_time_ms': int((time.time() - start_time) * 1000),
            'report_url': ""
        }
    
    # Use device's script executor
    return device.script_executor.execute_script(script_name, parameters)
