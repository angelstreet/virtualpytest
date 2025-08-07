"""
Script execution utilities for VirtualPyTest

This module contains functions for:
- Script environment setup
- Device management and control
- Script execution and management
- Command execution utilities
"""

import os
import sys
import subprocess
import uuid
import time
import glob
from typing import Tuple, Dict, Any, Optional, List

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.dirname(current_dir)
shared_dir = os.path.dirname(lib_dir)
project_root = os.path.dirname(shared_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .app_utils import load_environment_variables
from .host_utils import get_host_instance, list_available_devices, get_controller
from .lock_utils import is_device_locked, lock_device, unlock_device


def setup_script_environment(script_name: str = "script") -> Dict[str, Any]:
    """
    Setup script environment by loading configuration and creating host instance.
    Reuses existing host_utils and app_utils infrastructure.
    
    Args:
        script_name: Name of the script for logging
        
    Returns:
        Dictionary containing host, team_id, and other configuration
    """
    print(f"[@script_execution_utils:setup_script_environment] Setting up environment for {script_name}...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate to project root and then to backend_host/src/.env
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    env_path = os.path.join(project_root, 'backend_host', 'src', '.env')
    
    print(f"[@script_execution_utils:setup_script_environment] Looking for .env at: {env_path}")
    
    if os.path.exists(env_path):
        print(f"[@script_execution_utils:setup_script_environment] Found .env file, loading environment variables")
        load_environment_variables(mode='host', calling_script_dir=os.path.dirname(env_path))
    else:
        print(f"[@script_execution_utils:setup_script_environment] ERROR: .env file not found at {env_path}")
        return {'success': False, 'error': f'.env file not found at {env_path}'}
    
    # Check if critical environment variables are set
    host_name = os.getenv('HOST_NAME')
    print(f"[@script_execution_utils:setup_script_environment] HOST_NAME from environment: {host_name}")
    
    device1_name = os.getenv('DEVICE1_NAME')
    print(f"[@script_execution_utils:setup_script_environment] DEVICE1_NAME from environment: {device1_name}")
    
    try:
        print(f"[@script_execution_utils:setup_script_environment] Creating host instance...")
        host = get_host_instance()
        
        device_count = host.get_device_count()
        print(f"[@script_execution_utils:setup_script_environment] Host created with {device_count} devices")
        
        if device_count == 0:
            return {'success': False, 'error': 'No devices configured'}
        
        # List available devices for debugging
        devices = host.get_devices()
        for device in devices:
            print(f"[@script_execution_utils:setup_script_environment] Found device: {device.device_name} ({device.device_model})")
        
    except Exception as e:
        import traceback
        print(f"[@script_execution_utils:setup_script_environment] ERROR: Failed to create host: {e}")
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
    print(f"[@script_execution_utils:select_device] Selecting device for {script_name}...")
    available_devices = [d.device_id for d in host.get_devices()]
    print(f"[@script_execution_utils:select_device] Available devices: {available_devices}")
    
    if device_id:
        print(f"[@script_execution_utils:select_device] Requested device: {device_id}")
        selected_device = next((d for d in host.get_devices() if d.device_id == device_id), None)
        if not selected_device:
            error_msg = f"Device {device_id} not found. Available: {available_devices}"
            print(f"[@script_execution_utils:select_device] ERROR: {error_msg}")
            return {'success': False, 'error': error_msg}
    else:
        devices = host.get_devices()
        if not devices:
            error_msg = "No devices available"
            print(f"[@script_execution_utils:select_device] ERROR: {error_msg}")
            return {'success': False, 'error': error_msg}
        selected_device = devices[0]
        print(f"[@script_execution_utils:select_device] No device specified, using first available: {selected_device.device_id}")
    
    print(f"[@script_execution_utils:select_device] Selected device: {selected_device.device_name} ({selected_device.device_model}) [{selected_device.device_id}]")
    return {'success': True, 'device': selected_device}


def take_device_control(host, device, script_name: str = "script") -> Dict[str, Any]:
    """
    Take control of a device using existing lock_utils.
    
    Args:
        host: Host instance
        device: Device instance
        script_name: Name of the script for logging
        
    Returns:
        Dictionary with session_id or error
    """
    device_key = f"{host.host_name}:{device.device_id}"
    
    if is_device_locked(device_key):
        return {'success': False, 'error': f"Device {device.device_id} is locked by another process"}
    
    session_id = str(uuid.uuid4())
    
    if not lock_device(device_key, session_id):
        return {'success': False, 'error': f"Failed to take control of device {device.device_id}"}
    
    return {'success': True, 'session_id': session_id, 'device_key': device_key}


def release_device_control(device_key: str, session_id: str, script_name: str = "script") -> bool:
    """
    Release control of a device using existing lock_utils.
    
    Args:
        device_key: Device key in format "hostname:device_id"
        session_id: Session ID from take_device_control
        script_name: Name of the script for logging
        
    Returns:
        True if successful, False otherwise
    """
    try:
        unlock_device(device_key, session_id)
        return True
    except Exception:
        return False


def get_scripts_directory() -> str:
    """Get the scripts directory path - single source of truth"""
    current_dir = os.path.dirname(os.path.abspath(__file__))  # /shared/lib/utils
    lib_dir = os.path.dirname(current_dir)  # /shared/lib
    shared_dir = os.path.dirname(lib_dir)  # /shared
    project_root = os.path.dirname(shared_dir)  # /virtualpytest
    
    # Use test_scripts folder as the primary scripts location
    return os.path.join(project_root, 'test_scripts')


def get_script_path(script_name: str) -> str:
    """Get full path to a script file"""
    scripts_dir = get_scripts_directory()
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
        available_scripts.append(script_name)
    
    # Sort alphabetically
    available_scripts.sort()
    
    return available_scripts


def execute_command(command: str, timeout: int = 30) -> Tuple[bool, str, str, int]:
    """Execute a shell command with timeout"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        exit_code = result.returncode
        
        return success, stdout, stderr, exit_code
        
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out", -1
    except Exception as e:
        return False, "", str(e), -1


def execute_script(script_name: str, device_id: str, parameters: str = "") -> Dict[str, Any]:
    """Execute a script with parameters and generate report"""
    start_time = time.time()
    
    try:
        script_path = get_script_path(script_name)
        
        hostname = os.getenv('HOST_NAME', 'localhost')
        
        # Build command with parameters
        base_command = f"bash -c 'source /home/{hostname}/myvenv/bin/activate && python {script_path}"
        
        if parameters and parameters.strip():
            # Add parameters to the command
            command = f"{base_command} {parameters.strip()}'"
        else:
            command = f"{base_command}'"
        
        success, stdout, stderr, exit_code = execute_command(command, timeout=300)  # Increased timeout
        
        total_execution_time = int((time.time() - start_time) * 1000)
        
        # Script handles its own execution and provides all results
        return {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code,
            'script_name': script_name,
            'device_id': device_id,
            'script_path': script_path,
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': ""  # Script should provide this through proper channels
        }
        
    except Exception as e:
        total_execution_time = int((time.time() - start_time) * 1000)
        
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'exit_code': 1,
            'script_name': script_name,
            'device_id': device_id,
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': ""
        }


def get_device_info_for_report(device_id: str) -> Dict[str, Any]:
    """Get device information for report generation"""
    try:
        from .host_utils import get_device_by_id
        device = get_device_by_id(device_id)
        
        if device:
            return {
                'device_name': device.device_name,
                'device_model': device.device_model,
                'device_id': device.device_id
            }
        else:
            return {
                'device_name': f'Device {device_id}',
                'device_model': 'Unknown Model',
                'device_id': device_id
            }
    except Exception:
        return {
            'device_name': f'Device {device_id}',
            'device_model': 'Unknown Model', 
            'device_id': device_id
        }


def get_host_info_for_report() -> Dict[str, Any]:
    """Get host information for report generation"""
    try:
        from .host_utils import get_host_instance
        host = get_host_instance()
        
        if host:
            return {
                'host_name': host.host_name
            }
        else:
            hostname = os.getenv('HOST_NAME', 'localhost')
            return {
                'host_name': hostname
            }
    except Exception:
        hostname = os.getenv('HOST_NAME', 'localhost')
        return {
            'host_name': hostname
        }