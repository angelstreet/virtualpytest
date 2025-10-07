"""
System Utilities

Centralized system command utilities for VirtualPyTest.
Handles systemctl, reboot, and other system-level operations.
"""

import os
import signal
import subprocess
from typing import Dict, Any, Optional, List


def kill_existing_script_instances(script_name: str) -> List[int]:
    """
    Kill any existing instances of a Python script before starting.
    Ensures only ONE instance runs at a time.
    
    Args:
        script_name: Name of the script file (e.g., 'hot_cold_archiver.py')
        
    Returns:
        List of PIDs that were killed
    """
    current_pid = os.getpid()
    killed_pids = []
    
    try:
        # Find all processes running this script
        output = subprocess.check_output(['pgrep', '-f', script_name], text=True).strip()
        pids = [int(pid) for pid in output.split('\n') if pid]
        
        # Kill all except current process
        for pid in pids:
            if pid != current_pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                    killed_pids.append(pid)
                except ProcessLookupError:
                    pass  # Already dead
        
        return killed_pids
        
    except subprocess.CalledProcessError:
        # No other processes found - this is good
        return []
    except Exception as e:
        print(f"Warning: Error checking for existing {script_name} processes: {e}")
        return []


def restart_systemd_service(service_name: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Restart a systemd service using sudo systemctl restart.
    
    Args:
        service_name: Name of the systemd service (e.g., 'vpt_host', 'stream')
        timeout: Command timeout in seconds
        
    Returns:
        Dict with success status, message, and error details
    """
    try:
        print(f"[SYSTEM_UTILS] Restarting systemd service: {service_name}")
        
        result = subprocess.run(
            ['sudo', 'systemctl', 'restart', service_name],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            print(f"[SYSTEM_UTILS] Successfully restarted service: {service_name}")
            return {
                'success': True,
                'message': f'Service {service_name} restarted successfully',
                'service': service_name
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or 'Unknown error'
            print(f"[SYSTEM_UTILS] Failed to restart service {service_name}: {error_msg}")
            return {
                'success': False,
                'error': f'Failed to restart service {service_name}: {error_msg}',
                'service': service_name
            }
            
    except subprocess.TimeoutExpired:
        error_msg = f'Service restart timed out after {timeout}s'
        print(f"[SYSTEM_UTILS] {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'service': service_name
        }
    except Exception as e:
        error_msg = f'System error restarting service {service_name}: {str(e)}'
        print(f"[SYSTEM_UTILS] {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'service': service_name
        }


def reboot_system(timeout: int = 10) -> Dict[str, Any]:
    """
    Reboot the system using sudo reboot.
    
    Args:
        timeout: Command timeout in seconds (should be short since system will reboot)
        
    Returns:
        Dict with success status and message
    """
    try:
        print("[SYSTEM_UTILS] Initiating system reboot")
        
        # Use reboot command with short timeout since system will restart
        result = subprocess.run(
            ['sudo', 'reboot'],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # If we reach here, reboot command was issued
        print("[SYSTEM_UTILS] Reboot command issued successfully")
        return {
            'success': True,
            'message': 'System reboot initiated',
            'action': 'reboot'
        }
        
    except subprocess.TimeoutExpired:
        # This is actually expected for reboot - system is restarting
        print("[SYSTEM_UTILS] Reboot command timed out (expected - system restarting)")
        return {
            'success': True,
            'message': 'System reboot initiated (timeout expected)',
            'action': 'reboot'
        }
    except Exception as e:
        error_msg = f'System error during reboot: {str(e)}'
        print(f"[SYSTEM_UTILS] {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'action': 'reboot'
        }


def get_systemd_service_status(service_name: str) -> Dict[str, Any]:
    """
    Get status of a systemd service.
    
    Args:
        service_name: Name of the systemd service
        
    Returns:
        Dict with service status information
    """
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        status = result.stdout.strip()
        is_active = result.returncode == 0
        
        return {
            'success': True,
            'service': service_name,
            'status': status,
            'is_active': is_active
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'service': service_name,
            'status': 'unknown',
            'is_active': False
        }
