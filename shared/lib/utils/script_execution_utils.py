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
import select

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
    # Load environment variables using shared utility (loads project root .env + service-specific if available)
    print(f"[@script_execution_utils:setup_script_environment] Loading environment variables...")
    
    try:
        # Load only project root .env (host-specific variables are already loaded by the host service)
        load_environment_variables(mode='host', calling_script_dir=None)
        print(f"[@script_execution_utils:setup_script_environment] Environment variables loaded successfully")
    except Exception as e:
        print(f"[@script_execution_utils:setup_script_environment] ERROR: Failed to load environment variables: {e}")
        return {'success': False, 'error': f'Failed to load environment variables: {e}'}
    
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
    """Execute a script with parameters and real-time output streaming"""
    start_time = time.time()
    
    # Database tracking for script execution
    script_result_id = None
    try:
        # Import here to avoid circular dependencies
        from shared.lib.supabase.script_results_db import record_script_execution_start
        
        # Get team_id from environment
        team_id = os.getenv('TEAM_ID', '123e4567-e89b-12d3-a456-426614174000')
        
        # Get host info using existing function
        host_info = get_host_info_for_report()
        host_name = host_info.get('host_name', os.getenv('HOST_NAME', 'localhost'))
        
        # Record script execution start in database
        script_result_id = record_script_execution_start(
            team_id=team_id,
            script_name=script_name,
            script_type='manual',  # From RunTests page
            host_name=host_name,
            device_name=device_id,  # Use device_id as device_name for now
            userinterface_name=None,  # Will be updated if available
            metadata={
                'device_id': device_id,
                'parameters': parameters,
                'execution_source': 'run_tests'
            }
        )
        
        if script_result_id:
            print(f"[@script_execution_utils:execute_script] Script execution recorded with ID: {script_result_id}")
        else:
            print(f"[@script_execution_utils:execute_script] Warning: Failed to record script execution in database")
    except Exception as e:
        print(f"[@script_execution_utils:execute_script] Warning: Database tracking failed: {e}")
        # Continue execution even if database tracking fails
    
    # Check if this is an AI test case - redirect to ai_testcase_executor.py
    # IMPORTANT: Exclude the executor script itself to prevent infinite recursion
    if script_name.startswith("ai_testcase_") and script_name != "ai_testcase_executor":
        print(f"[@script_execution_utils:execute_script] AI test case detected: {script_name}")
        
        # Execute via ai_testcase_executor.py with SAME parameters as normal scripts
        actual_script = "ai_testcase_executor"
        
        print(f"[@script_execution_utils:execute_script] Redirecting to: {actual_script} with params: {parameters}")
        
        # Pass the original AI script name via environment so executor can find the test case
        original_env = os.environ.copy()
        os.environ['AI_SCRIPT_NAME'] = script_name
        
        try:
            # Continue with normal subprocess execution (same parameters format)
            result = execute_script(actual_script, device_id, parameters)
            # Restore the script_name in the result to maintain transparency
            result['script_name'] = script_name
            return result
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
    
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
        
        print(f"[@script_execution_utils:execute_script] Executing: {command}")
        print(f"[@script_execution_utils:execute_script] === SCRIPT OUTPUT START ===")
        
        # Use streaming subprocess execution (like campaign executor)
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout for unified streaming
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Stream output in real-time with timeout
        stdout_lines = []
        report_url = ""
        logs_url = ""
        timeout_seconds = 3600  # 1 hour timeout
        start_time_for_timeout = time.time()
        
        while True:
            # Use select to wait for output with timeout
            ready = select.select([process.stdout], [], [], 1.0)[0]  # 1 second timeout
            
            poll_result = process.poll()
            
            if ready:
                output = process.stdout.readline()
                if output:
                    line = output.rstrip()
                    
                    # Extract report URL from cloudflare upload logs  
                    if '[@cloudflare_utils:upload_script_report] INFO: Uploaded script report:' in line:
                        try:
                            report_path = line.split('Uploaded script report: ')[1]
                            base_url = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', 'https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev')
                            report_url = f"{base_url.rstrip('/')}/{report_path}"
                            print(f"📊 [Script] Report URL captured: {report_url}")
                        except Exception as e:
                            print(f"⚠️ [Script] Failed to extract report URL: {e}")
                    
                    # Extract logs URL from upload logs
                    if '[@utils:report_utils:generate_and_upload_script_report] Logs uploaded:' in line:
                        try:
                            logs_url = line.split('Logs uploaded: ')[1].strip()
                            print(f"📝 [Script] Logs URL captured: {logs_url}")
                        except Exception as e:
                            print(f"⚠️ [Script] Failed to extract logs URL: {e}")
                    
                    # Stream all output with prefix
                    print(f"[{script_name}] {line}")
                    
                    stdout_lines.append(output)
                elif poll_result is not None:
                    print(f"[@script_execution_utils:execute_script] LOOP EXIT: Empty output and process ended (exit code: {poll_result})")
                    break
            elif poll_result is not None:
                print(f"[@script_execution_utils:execute_script] LOOP EXIT: No output ready and process ended (exit code: {poll_result})")
                break
            
            # Check for timeout
            current_time = time.time()
            elapsed_time = current_time - start_time_for_timeout
            if elapsed_time > timeout_seconds:
                print(f"❌ [Script] Script execution timed out after {timeout_seconds} seconds (elapsed: {elapsed_time:.1f}s)")
                if poll_result is None:
                    print(f"❌ [Script] Process still running, force killing...")
                    process.kill()
                    process.wait()
                else:
                    print(f"❌ [Script] Process already ended but loop didn't exit properly")
                stdout_lines.append(f"\n[TIMEOUT] Script execution timed out after {timeout_seconds} seconds\n")
                break
            
            # Log progress every 30 seconds to track long-running scripts
            if int(elapsed_time) % 30 == 0 and int(elapsed_time) > 0:
                poll_status = poll_result
                if poll_status is None:
                    print(f"[@script_execution_utils:execute_script] PROGRESS: Script running for {elapsed_time:.0f}s, process still active")
                else:
                    print(f"[@script_execution_utils:execute_script] PROGRESS: Script at {elapsed_time:.0f}s, process ended with code {poll_status} but loop still running")
        
        # Wait for process completion
        exit_code = process.wait()
        stdout = ''.join(stdout_lines)
        
        print(f"[@script_execution_utils:execute_script] === SCRIPT OUTPUT END ===")
        print(f"[@script_execution_utils:execute_script] Process completed with exit code: {exit_code}")
        print(f"[@script_execution_utils:execute_script] DEBUG: Total stdout lines captured: {len(stdout_lines)}")
        print(f"[@script_execution_utils:execute_script] DEBUG: Final stdout length: {len(stdout)}")
        
        # Simple logic: exit code 0 = success, report URL captured from upload logs
        
        total_execution_time = int((time.time() - start_time) * 1000)
        
        print(f"[@script_execution_utils:execute_script] PREPARE RETURN: Creating return dictionary...")
        print(f"[@script_execution_utils:execute_script] EXIT_CODE: {exit_code}, EXECUTION_TIME: {total_execution_time}ms")
        print(f"[@script_execution_utils:execute_script] REPORT_URL: {report_url}")
        
        # Extract SCRIPT_SUCCESS marker from stdout (critical for frontend result accuracy)
        script_success = None
        print(f"[@script_execution_utils:execute_script] DEBUG: Checking for SCRIPT_SUCCESS marker in stdout...")
        print(f"[@script_execution_utils:execute_script] DEBUG: stdout length: {len(stdout) if stdout else 0}")
        print(f"[@script_execution_utils:execute_script] DEBUG: stdout contains 'SCRIPT_SUCCESS:': {'SCRIPT_SUCCESS:' in stdout if stdout else False}")
        
        if stdout and 'SCRIPT_SUCCESS:' in stdout:
            import re
            success_match = re.search(r'SCRIPT_SUCCESS:(true|false)', stdout)
            if success_match:
                script_success = success_match.group(1) == 'true'
                print(f"[@script_execution_utils:execute_script] SCRIPT_SUCCESS extracted: {script_success}")
            else:
                print(f"[@script_execution_utils:execute_script] DEBUG: SCRIPT_SUCCESS found but regex didn't match")
        else:
            print(f"[@script_execution_utils:execute_script] DEBUG: No SCRIPT_SUCCESS marker found in stdout")
            # Print last 500 chars of stdout to see what's there
            if stdout:
                stdout_tail = stdout[-500:] if len(stdout) > 500 else stdout
                print(f"[@script_execution_utils:execute_script] DEBUG: Last 500 chars of stdout: {repr(stdout_tail)}")
            else:
                print(f"[@script_execution_utils:execute_script] DEBUG: stdout is empty or None")
        result = {
            'stdout': stdout,
            'stderr': '',  # We merged stderr into stdout
            'exit_code': exit_code,  # Raw exit code (0 = process success)
            'script_name': script_name,
            'device_id': device_id,
            'script_path': script_path,
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': report_url,
            'logs_url': logs_url,
            'script_success': script_success,  # Extracted from SCRIPT_SUCCESS marker
            'script_result_id': script_result_id  # Database tracking ID
        }
        
        # Update database with completion status
        if script_result_id:
            try:
                from shared.lib.supabase.script_results_db import update_script_execution_result
                
                # Determine success based on script_success marker (most reliable)
                execution_success = script_success if script_success is not None else (exit_code == 0)
                
                update_script_execution_result(
                    script_result_id=script_result_id,
                    success=execution_success,
                    execution_time_ms=total_execution_time,
                    html_report_r2_url=report_url if report_url else None,
                    logs_r2_url=logs_url if logs_url else None,
                    error_msg=None if execution_success else f"Script failed with exit code {exit_code}"
                )
                print(f"[@script_execution_utils:execute_script] Database updated with completion status: {execution_success}")
            except Exception as e:
                print(f"[@script_execution_utils:execute_script] Warning: Failed to update database: {e}")
        
        print(f"[@script_execution_utils:execute_script] RETURNING: About to return result dictionary")
        return result
        
    except Exception as e:
        total_execution_time = int((time.time() - start_time) * 1000)
        print(f"[@script_execution_utils:execute_script] ERROR: {str(e)}")
        
        # Update database with error status
        if script_result_id:
            try:
                from shared.lib.supabase.script_results_db import update_script_execution_result
                update_script_execution_result(
                    script_result_id=script_result_id,
                    success=False,
                    execution_time_ms=total_execution_time,
                    error_msg=str(e)
                )
                print(f"[@script_execution_utils:execute_script] Database updated with error status")
            except Exception as db_error:
                print(f"[@script_execution_utils:execute_script] Warning: Failed to update database with error: {db_error}")
        
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'exit_code': 1,
            'script_name': script_name,
            'device_id': device_id,
            'parameters': parameters,
            'execution_time_ms': total_execution_time,
            'report_url': "",
            'script_result_id': script_result_id
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


