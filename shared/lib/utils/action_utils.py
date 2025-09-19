"""
Action and verification execution utilities for VirtualPyTest

This module contains functions for:
- Direct action execution
- Verification execution
- Edge action execution
- Navigation with verifications
- Screenshot capture
"""

import os
import sys
import time
import uuid
from typing import Dict, Any, Optional, List

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.dirname(current_dir)
shared_dir = os.path.dirname(lib_dir)
project_root = os.path.dirname(shared_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .host_utils import get_controller


def execute_action_directly(host, device, action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an action directly using controller-specific abstraction.
    
    This function now implements the same routing logic and iteration support as ActionExecutor 
    to ensure verification actions (like waitForTextToAppear) are routed to verification controllers
    instead of remote controllers, and supports action iteration.
    
    Args:
        host: Host instance
        device: Device instance
        action: Action dictionary with 'command', 'params', 'action_type', 'verification_type', and 'iterator'
        
    Returns:
        Dictionary with success status, execution details, and iteration results
    """
    try:
        command = action.get('command')
        params = action.get('params', {})
        action_type = action.get('action_type')
        
        # Device-aware action_type detection using controller factory (same as ActionExecutor)
        if not action_type:
            command = action.get('command', '')
            
            # Get device model for intelligent routing
            device_model = device.device_model if device else 'unknown'
            print(f"[@action_utils:execute_action_directly] Device model: {device_model}")
            
            # Specific command-based detection for commands that are controller-specific
            web_only_commands = {
                'open_browser', 'close_browser', 'connect_browser',
                'navigate_to_url', 'find_element', 'execute_javascript', 
                'get_page_info', 'activate_semantic', 'dump_elements', 
                'browser_use_task'
            }
            
            desktop_only_commands = {
                'execute_pyautogui_click', 'execute_pyautogui_rightclick', 'execute_pyautogui_doubleclick',
                'execute_pyautogui_move', 'execute_pyautogui_keypress', 'execute_pyautogui_type',
                'execute_pyautogui_scroll', 'execute_pyautogui_locate', 'execute_pyautogui_locate_and_click',
                'execute_pyautogui_launch', 'execute_bash_command'
            }
            
            verification_commands = {
                'waitForTextToAppear', 'waitForTextToDisappear',
                'waitForImageToAppear', 'waitForImageToDisappear'
            }
            
            power_commands = {
                'power_on', 'power_off', 'reboot'
            }
            
            # First check for controller-specific commands
            if command in web_only_commands:
                action_type = 'web'
                print(f"[@action_utils:execute_action_directly] Web-only command detected: {command}")
            elif command in desktop_only_commands:
                action_type = 'desktop'
                print(f"[@action_utils:execute_action_directly] Desktop-only command detected: {command}")
            elif command in verification_commands:
                action_type = 'verification'
                print(f"[@action_utils:execute_action_directly] Verification command detected: {command}")
            elif command in power_commands:
                action_type = 'power'
                print(f"[@action_utils:execute_action_directly] Power command detected: {command}")
            elif command in ['enter_subtree', 'exit_subtree']:
                # Handle virtual cross-tree navigation commands silently
                action_type = 'virtual'
            else:
                # For generic commands (click_element, input_text, press_key), use device capabilities
                try:
                    # Add project root to path for controller factory import
                    import sys
                    import os
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    lib_dir = os.path.dirname(current_dir)
                    shared_dir = os.path.dirname(lib_dir)
                    project_root = os.path.dirname(shared_dir)
                    if project_root not in sys.path:
                        sys.path.insert(0, project_root)
                    
                    from backend_core.src.controllers.controller_config_factory import DEVICE_CONTROLLER_MAP
                    
                    # Check what controllers this device has and route accordingly
                    if device_model in DEVICE_CONTROLLER_MAP:
                        device_mapping = DEVICE_CONTROLLER_MAP[device_model]
                        
                        # Priority order: web > desktop > remote (most specific to least specific)
                        if device_mapping.get('web', []):
                            action_type = 'web'
                            print(f"[@action_utils:execute_action_directly] Generic command '{command}' routed to web (device has web controller)")
                        elif device_mapping.get('desktop', []):
                            action_type = 'desktop'
                            print(f"[@action_utils:execute_action_directly] Generic command '{command}' routed to desktop (device has desktop controller)")
                        elif device_mapping.get('remote', []):
                            action_type = 'remote'
                            print(f"[@action_utils:execute_action_directly] Generic command '{command}' routed to remote (device has remote controller)")
                        else:
                            # Fallback to remote
                            action_type = 'remote'
                            print(f"[@action_utils:execute_action_directly] Generic command '{command}' defaulted to remote (no specific controllers found)")
                    else:
                        # Unknown device model - default to remote
                        action_type = 'remote'
                        print(f"[@action_utils:execute_action_directly] Unknown device model '{device_model}', defaulting to remote for command '{command}'")
                except Exception as e:
                    # Fallback to remote on any import/lookup error
                    action_type = 'remote'
                    print(f"[@action_utils:execute_action_directly] Error in device routing: {e}, defaulting to remote for command '{command}'")
        
        # Get iterator count (default to 1 if not specified)
        # Only allow iterations for non-verification actions (same logic as ActionExecutor)
        if action_type == 'verification':
            iterator_count = 1  # Force single execution for verifications
        else:
            iterator_count = action.get('iterator', 1)
            if iterator_count < 1 or iterator_count > 100:
                iterator_count = 1  # Clamp to valid range
        
        if action_type == 'verification':
            print(f"[@action_utils:execute_action_directly] Executing verification: {command} (verifications always run once)")
        else:
            print(f"[@action_utils:execute_action_directly] Executing action: {command} with {iterator_count} iteration(s)")
        
        print(f"[@action_utils:execute_action_directly] Action type: {action_type}")
        
        # Track results for all iterations
        all_iterations_successful = True
        total_execution_time = 0
        iteration_results = []
        
        for iteration in range(iterator_count):
            iteration_start_time = time.time()
            
            try:
                iteration_label = f"iteration {iteration + 1}/{iterator_count}" if iterator_count > 1 else ""
                if iteration_label:
                    print(f"[@action_utils:execute_action_directly] Executing {iteration_label}: {command}")
                
                # Route to appropriate controller based on action_type (same logic as ActionExecutor)
                if action_type == 'verification':
                    verification_type = action.get('verification_type', 'text')  # Default to text verification
                    if iteration == 0:  # Only log routing once
                        print(f"[@action_utils:execute_action_directly] Routing verification action to {verification_type} verification controller")
                    
                    # Get verification controller
                    verification_controller = get_controller(device.device_id, f'verification_{verification_type}')
                    if not verification_controller:
                        return {
                            'success': False,
                            'error': f'No {verification_type} verification controller found for device {device.device_id}',
                            'total_execution_time_ms': 0,
                            'iteration_results': []
                        }
                    
                    # Execute verification using unified method (same as ActionExecutor)
                    verification_config = {
                        'command': command,
                        'params': params
                    }
                    
                    result = verification_controller.execute_verification(verification_config)
                    iteration_success = result.get('success', False)
                    
                elif action_type == 'web':
                    # Route to web controller
                    if iteration == 0:  # Only log routing once
                        print(f"[@action_utils:execute_action_directly] Routing web action to web controller")
                    
                    web_controller = get_controller(device.device_id, 'web')
                    if not web_controller:
                        return {
                            'success': False,
                            'error': f'No web controller found for device {device.device_id}',
                            'total_execution_time_ms': 0,
                            'iteration_results': []
                        }
                    
                    # Transform parameters for web controller compatibility
                    web_params = params.copy()
                    # Convert element_id to selector for web actions
                    if 'element_id' in web_params and 'selector' not in web_params:
                        web_params['selector'] = web_params.pop('element_id')
                        if iteration == 0:  # Only log transformation once
                            print(f"[@action_utils:execute_action_directly] Transformed element_id to selector for web action")
                    
                    result = web_controller.execute_command(command, web_params)
                    iteration_success = result.get('success', False)
                    
                elif action_type == 'desktop':
                    # Intelligent routing to correct desktop controller
                    bash_commands = {'execute_bash_command'}
                    
                    if command in bash_commands:
                        controller_key = 'desktop_bash'
                        if iteration == 0:  # Only log routing once
                            print(f"[@action_utils:execute_action_directly] Routing desktop action to bash controller")
                    else:
                        controller_key = 'desktop_pyautogui'
                        if iteration == 0:  # Only log routing once
                            print(f"[@action_utils:execute_action_directly] Routing desktop action to pyautogui controller")
                    
                    # Try specific controller first, fallback to generic 'desktop'
                    desktop_controller = get_controller(device.device_id, controller_key) or get_controller(device.device_id, 'desktop')
                    if not desktop_controller:
                        return {
                            'success': False,
                            'error': f'No {controller_key} or desktop controller found for device {device.device_id}',
                            'total_execution_time_ms': 0,
                            'iteration_results': []
                        }
                    
                    result = desktop_controller.execute_command(command, params)
                    iteration_success = result.get('success', False)
                    
                elif action_type == 'power':
                    # Route to power controller
                    if iteration == 0:  # Only log routing once
                        print(f"[@action_utils:execute_action_directly] Routing power action to power controller")
                    
                    power_controller = get_controller(device.device_id, 'power')
                    if not power_controller:
                        return {
                            'success': False,
                            'error': f'No power controller found for device {device.device_id}',
                            'total_execution_time_ms': 0,
                            'iteration_results': []
                        }
                    
                    result = power_controller.execute_command(command, params)
                    iteration_success = result.get('success', False)
                    
                elif action_type == 'virtual':
                    # Handle virtual cross-tree navigation commands silently
                    # Virtual transitions complete instantly - they represent logical context changes
                    # The actual navigation is handled by the unified pathfinding system
                    iteration_success = True
                    result = {
                        'success': True,
                        'message': f'Virtual {command} transition completed',
                        'execution_time': 0
                    }
                    
                else:
                    # Route to remote controller (default behavior for remote actions)
                    if iteration == 0:  # Only log routing once
                        print(f"[@action_utils:execute_action_directly] Routing {action_type} action to remote controller")
                    
                    remote_controller = get_controller(device.device_id, 'remote')
                    if not remote_controller:
                        return {
                            'success': False,
                            'error': f'No remote controller found for device {device.device_id}',
                            'total_execution_time_ms': 0,
                            'iteration_results': []
                        }
                    
                    iteration_success = remote_controller.execute_command(command, params)
                    result = {'success': iteration_success}
                
                iteration_execution_time = int((time.time() - iteration_start_time) * 1000)
                total_execution_time += iteration_execution_time
                
                if iterator_count > 1:
                    print(f"[@action_utils:execute_action_directly] Iteration {iteration + 1}/{iterator_count} result: success={iteration_success}, time={iteration_execution_time}ms")
                else:
                    print(f"[@action_utils:execute_action_directly] Action result: success={iteration_success}, time={iteration_execution_time}ms")
                
                # Track iteration results
                iteration_results.append({
                    'iteration': iteration + 1,
                    'success': iteration_success,
                    'execution_time_ms': iteration_execution_time,
                    'message': result.get('message', f'{"Successfully executed" if iteration_success else "Failed to execute"} {command}'),
                    'details': result if action_type == 'verification' else None
                })
                
                # If any iteration fails, mark overall action as failed
                if not iteration_success:
                    all_iterations_successful = False
                    # Stop on first failure - don't continue iterations
                    break
                
                # Wait between iterations if there are more iterations (same wait_time)
                if iteration < iterator_count - 1:
                    wait_time = params.get('wait_time', 0)
                    if wait_time > 0:
                        iter_time = time.strftime("%H:%M:%S", time.localtime())
                        print(f"[@action_utils:execute_action_directly] [{iter_time}] Waiting {wait_time}ms between iterations")
                        time.sleep(wait_time / 1000.0)
                        iter_end_time = time.strftime("%H:%M:%S", time.localtime())
                        print(f"[@action_utils:execute_action_directly] [{iter_end_time}] Iteration wait completed")
                
            except Exception as e:
                iteration_execution_time = int((time.time() - iteration_start_time) * 1000)
                total_execution_time += iteration_execution_time
                all_iterations_successful = False
                
                iteration_results.append({
                    'iteration': iteration + 1,
                    'success': False,
                    'execution_time_ms': iteration_execution_time,
                    'message': f'Iteration execution error: {str(e)}',
                    'error': str(e)
                })
                
                print(f"[@action_utils:execute_action_directly] Iteration {iteration + 1} error: {str(e)}")
                break
        
        # Wait after successful action execution (once per action, after all iterations)
        wait_time = params.get('wait_time', 0)
        if all_iterations_successful and wait_time > 0:
            wait_seconds = wait_time / 1000.0
            current_time = time.strftime("%H:%M:%S", time.localtime())
            print(f"[@action_utils:execute_action_directly] [{current_time}] Waiting {wait_time}ms after successful {command} execution")
            time.sleep(wait_seconds)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            print(f"[@action_utils:execute_action_directly] [{end_time}] Wait completed after {command}")
        
        # Return comprehensive results (same format as ActionExecutor)
        return {
            'success': all_iterations_successful,
            'message': f'{"Successfully executed" if all_iterations_successful else "Failed to execute"} {command} ({len(iteration_results)}/{iterator_count} iterations passed)',
            'error': None if all_iterations_successful else f'Action failed after {len(iteration_results)} iteration(s)',
            'total_execution_time_ms': total_execution_time,
            'iterator_count': iterator_count,
            'iteration_results': iteration_results,
            'details': iteration_results[-1].get('details') if iteration_results and action_type == 'verification' else None
        }
            
    except Exception as e:
        return {
            'success': False, 
            'error': f'Action execution error: {str(e)}',
            'total_execution_time_ms': 0,
            'iteration_results': []
        }


def execute_verification_directly(host, device, verification: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a verification directly using controller-specific abstraction.
    
    Args:
        host: Host instance
        device: Device instance
        verification: Verification dictionary with 'verification_type' and other params
        
    Returns:
        Dictionary with success status and verification results
    """
    try:
        verification_type = verification.get('verification_type', 'adb')
        
        verification_controller = get_controller(device.device_id, f'verification_{verification_type}')
        if not verification_controller:
            return {
                'success': False,
                'error': f'No {verification_type} verification controller found for device {device.device_id}'
            }
        
        result = verification_controller.execute_verification(verification)
        
        # Extract verification images for upload (source images only)
        verification_images = []
        if verification_type == 'image':
            # Image verification generates comparison images in the 'details' field
            details = result.get('details', {})
            
            # Debug logging to see what's in details
            print(f"[@action_utils:execute_verification_directly] Verification details keys: {list(details.keys())}")
            if details.get('source_image_path'):
                print(f"[@action_utils:execute_verification_directly] Source image path: {details.get('source_image_path')}")
            if details.get('reference_image_path'):
                print(f"[@action_utils:execute_verification_directly] Reference image path (NOT uploading): {details.get('reference_image_path')}")
            if details.get('reference_image_url'):
                print(f"[@action_utils:execute_verification_directly] Reference image URL: {details.get('reference_image_url')}")
            
            # Source image (screenshot taken) - needs to be uploaded
            if details.get('source_image_path'):
                verification_images.append(details.get('source_image_path'))
                print(f"[@action_utils:execute_verification_directly] Added source image to upload: {details.get('source_image_path')}")
            
            # Overlay image (comparison result) - needs to be uploaded
            if details.get('result_overlay_path'):
                verification_images.append(details.get('result_overlay_path'))
                print(f"[@action_utils:execute_verification_directly] Added overlay image to upload: {details.get('result_overlay_path')}")
                
            # Note: Reference image R2 URL is already in details['reference_image_url'] 
            # and doesn't need uploading - it will be available in step_results
        
        return {
            'success': result.get('success', False),
            'message': result.get('message', 'Verification completed'),
            'error': result.get('message', 'Verification completed') if not result.get('success', False) else None,
            'verification_type': verification_type,
            'resultType': 'PASS' if result.get('success') else 'FAIL',
            'verification_images': verification_images,  # Add images for upload (source images only)
            'details': result.get('details', {})  # Preserve verification details (includes reference_image_url)
        }
            
    except Exception as e:
        import traceback
        print(f"[@action_utils:execute_verification_directly] ERROR: {str(e)}")
        print(f"[@action_utils:execute_verification_directly] TRACEBACK: {traceback.format_exc()}")
        return {'success': False, 'error': f'Verification execution error: {str(e)}'}


def capture_validation_screenshot(host, device: Any, step_name: str, script_name: str = "validation") -> str:
    """
    Capture screenshot for validation reporting using AV controller directly.
    No HTTP requests needed - uses controller abstraction.
    
    Args:
        host: Host instance (not dict)
        device: Device object
        step_name: Name of the step (e.g., "initial_state", "step_1", "final_state")
        script_name: Name of the script for logging
        
    Returns:
        Local path to captured screenshot or empty string if failed
    """
    try:
        print(f"[@action_utils:capture_validation_screenshot] Capturing screenshot for step: {step_name}")
        av_controller = get_controller(device.device_id, 'av')
        
        screenshot_path = av_controller.take_screenshot()
        
        if screenshot_path:
            print(f"[@action_utils:capture_validation_screenshot] Screenshot captured successfully: {screenshot_path}")
            return screenshot_path
        else:
            print(f"[@action_utils:capture_validation_screenshot] Screenshot capture returned empty path")
            return ""
            
    except Exception as e:
        print(f"[@action_utils:capture_validation_screenshot] Screenshot capture failed: {str(e)}")
        import traceback
        print(f"[@action_utils:capture_validation_screenshot] Traceback: {traceback.format_exc()}")
