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


def execute_navigation_with_verifications(host, device, transition: Dict[str, Any], team_id: str, tree_id: str = None, script_result_id: str = None, script_context: str = 'script', global_verification_counter: int = 0) -> Dict[str, Any]:
    """
    Execute a single navigation step with verifications following NavigationExecutor pattern.
    
    This function mimics the NavigationExecutor.execute_navigation() behavior:
    1. Execute navigation actions using ActionExecutor pattern
    2. Execute target node verifications using VerificationExecutor pattern
    3. Record execution results to database (same as server-side NavigationExecutor)
    
    Args:
        host: Host instance
        device: Device instance
        transition: Navigation transition with actions and verifications
        team_id: Team ID for database recording
        tree_id: Tree ID for database recording (should be UUID)
        
    Returns:
        Dictionary with execution results including verification results
    """
    try:
        start_time = time.time()
        
        actions = transition.get('actions', [])
        retry_actions = transition.get('retryActions', [])
        failure_actions = transition.get('failureActions', [])
        
        # Log detailed action information before execution
        edge_id = transition.get('edge_id', 'unknown')
        from_node = transition.get('from_node_label', 'unknown')
        to_node = transition.get('to_node_label', 'unknown')
        
        print(f"[@action_utils:execute_navigation] Executing navigation step: {from_node} → {to_node}")
        print(f"[@action_utils:execute_navigation] Edge ID: {edge_id}")
        print(f"[@action_utils:execute_navigation] Actions to execute: {len(actions)}")
        print(f"[@action_utils:execute_navigation] Retry actions available: {len(retry_actions)}, Failure actions available: {len(failure_actions)}")
        
        # Step-start screenshot using current R2 system (not old Supabase)
        # Take screenshot BEFORE any actions are executed
        step_name = f"step_{transition.get('step_number', 'unknown')}_{from_node}_{to_node}"
        step_start_screenshot_path = capture_validation_screenshot(host, device, f"{step_name}_start", script_context)
        screenshot_url = None
        
        if step_start_screenshot_path:
            print(f"[@action_utils:execute_navigation] Step-start screenshot captured: {step_start_screenshot_path}")
            # Note: R2 upload happens later in batch via generate_and_upload_script_report()
        else:
            print(f"[@action_utils:execute_navigation] Step-start screenshot capture failed")
            
        # Log each action for debugging
        for i, action in enumerate(actions):
            action_cmd = action.get('command', 'unknown')
            action_params = action.get('params', {})
            print(f"[@action_utils:execute_navigation] Action {i+1}: {action_cmd} with params: {action_params}")
        
        action_start_time = time.time()
        
        # Use the original edge data with the correct action set selection
        original_edge_data = transition.get('original_edge_data')
        action_set_id = transition.get('action_set_id') 
        
        action_result = execute_edge_actions(host, device, original_edge_data, action_set_id=action_set_id, team_id=team_id)
        action_execution_time = int((time.time() - action_start_time) * 1000)
        
        # Get action screenshots from execute_edge_actions
        action_screenshots = action_result.get('action_screenshots', [])
        print(f"[@action_utils:execute_navigation] Captured {len(action_screenshots)} action screenshots")
        
        actions_success = action_result.get('success', False)
        
        # Enhanced error logging with more context
        if not actions_success:
            error_details = {
                'edge_id': edge_id,
                'from_node': from_node,
                'to_node': to_node,
                'actions_count': len(actions),
                'retry_actions_count': len(retry_actions),
                'failure_actions_count': len(failure_actions),
                'execution_time_ms': action_execution_time,
                'actions': actions,
                'retry_actions': retry_actions,
                'failure_actions': failure_actions
            }
            
            print(f"[@action_utils:execute_navigation] ACTION EXECUTION FAILED:")
            print(f"[@action_utils:execute_navigation]   Edge: {from_node} → {to_node} (ID: {edge_id})")
            print(f"[@action_utils:execute_navigation]   Failed after {action_execution_time}ms")
            print(f"[@action_utils:execute_navigation]   Actions attempted: {len(actions)}")
            print(f"[@action_utils:execute_navigation]   Retry actions attempted: {len(retry_actions)}")
            print(f"[@action_utils:execute_navigation]   Failure actions attempted: {len(failure_actions)}")
            
            # Set detailed error message
            detailed_error = "Action execution failed"
            if action_result.get('error'):
                detailed_error = f"Action execution failed: {action_result['error']}"
                print(f"[@action_utils:execute_navigation]   Action result error: {action_result['error']}")
        else:
            print(f"[@action_utils:execute_navigation] Actions completed successfully in {action_execution_time}ms")
            error_details = None
            detailed_error = None
        
        if tree_id and actions:
            try:
                from shared.lib.supabase.execution_results_db import record_edge_execution
                result = record_edge_execution(
                    team_id=team_id,
                    tree_id=tree_id,
                    edge_id=edge_id,
                    host_name=host.host_name,
                    device_model=device.device_model,
                    success=actions_success,
                    execution_time_ms=action_execution_time,
                    message='Navigation actions completed' if actions_success else detailed_error or 'Navigation actions failed',
                    error_details=error_details if not actions_success else None,
                    script_result_id=script_result_id,
                    script_context=script_context,
                    action_set_id=action_set_id
                )
                if result:
                    print(f"[@action_utils:execute_navigation] ✅ Edge execution recorded: {result}")
                else:
                    print(f"[@action_utils:execute_navigation] ❌ Edge execution recording failed: No result returned")
            except Exception as e:
                print(f"[@action_utils:execute_navigation] ❌ Edge execution recording error: {e}")
                print(f"[@action_utils:execute_navigation] Parameters: tree_id={tree_id}, edge_id={edge_id}, action_set_id={action_set_id}")
        
        if not actions_success:
            # Capture step-end screenshot even when actions fail
            print(f"[@action_utils:execute_navigation] Attempting step-end screenshot capture after action failure...")
            try:
                step_end_screenshot_path = capture_validation_screenshot(host, device, f"{step_name}_end_action_failure", script_context)
                
                if step_end_screenshot_path:
                    print(f"[@action_utils:execute_navigation] ✅ Step-end screenshot captured after action failure: {step_end_screenshot_path}")
                else:
                    print(f"[@action_utils:execute_navigation] ❌ Step-end screenshot capture returned None after action failure")
            except Exception as screenshot_error:
                print(f"[@action_utils:execute_navigation] ❌ Step-end screenshot capture exception after action failure: {str(screenshot_error)}")
                step_end_screenshot_path = None
                
            return {
                'success': False,
                'error': detailed_error or 'Navigation actions failed',
                'message': f'Navigation step failed during action execution: {from_node} → {to_node}',
                'verification_results': [],
                'step_start_screenshot_path': step_start_screenshot_path,
                'step_end_screenshot_path': step_end_screenshot_path,
                'action_screenshots': action_screenshots,
                'verification_images': [],  # No verification images since verifications didn't run
                'error_details': error_details,
                'global_verification_counter_increment': 0
            }
        
        verifications = transition.get('verifications', [])
        verification_results = []
        
        # Collect verification images for upload
        verification_image_paths = []
        
        for i, verification in enumerate(verifications):
            verification_start_time = time.time()
            # Use global verification counter to prevent overwriting across all steps
            verification['verification_index'] = global_verification_counter + i
            verify_result = execute_verification_directly(host, device, verification)
            verification_execution_time = int((time.time() - verification_start_time) * 1000)
            
            # Collect verification images (source and reference)
            verification_images = verify_result.get('verification_images', [])
            if verification_images:
                verification_image_paths.extend(verification_images)
                print(f"[@action_utils:execute_navigation] Collected {len(verification_images)} verification images for step:")
                for img_path in verification_images:
                    print(f"  - {os.path.basename(img_path) if img_path else 'None'}")
            
            if tree_id:
                try:
                    from shared.lib.supabase.execution_results_db import record_node_execution
                    node_id = transition.get('to_node_id', 'unknown')
                    result = record_node_execution(
                        team_id=team_id,
                        tree_id=tree_id,
                        node_id=node_id,
                        host_name=host.host_name,
                        device_model=device.device_model,
                        success=verify_result.get('success', False),
                        execution_time_ms=verification_execution_time,
                        message=verify_result.get('message', 'Verification completed'),
                        error_details={'error': verify_result.get('error')} if verify_result.get('error') else None,
                        script_result_id=script_result_id,
                        script_context=script_context
                    )
                    if result:
                        print(f"[@action_utils:execute_navigation] ✅ Node execution recorded: {result}")
                    else:
                        print(f"[@action_utils:execute_navigation] ❌ Node execution recording failed: No result returned")
                except Exception as e:
                    print(f"[@action_utils:execute_navigation] ❌ Node execution recording error: {e}")
                    print(f"[@action_utils:execute_navigation] Parameters: tree_id={tree_id}, node_id={node_id}")
            
            verification_result = {
                'verification_number': i + 1,
                'verification_type': verification.get('verification_type', 'adb'),
                'success': verify_result.get('success', False),
                'message': verify_result.get('message', 'Verification completed'),
                'resultType': 'PASS' if verify_result.get('success') else 'FAIL',
                'error': verify_result.get('error') if not verify_result.get('success') else None,
                'details': verify_result.get('details', {}),  # Preserve verification details (includes reference_image_url)
                'verification_images': verify_result.get('verification_images', [])  # Store verification images with each result
            }
            verification_results.append(verification_result)
            
            if not verify_result['success']:
                verification_error = verify_result.get("error", "Unknown error")
                verification_type = verification.get('verification_type', 'adb')
                
                print(f"[@action_utils:execute_navigation] VERIFICATION FAILED:")
                print(f"[@action_utils:execute_navigation]   Verification {i+1}/{len(verifications)}: {verification_type}")
                print(f"[@action_utils:execute_navigation]   Error: {verification_error}")
                print(f"[@action_utils:execute_navigation]   Execution time: {verification_execution_time}ms")
                print(f"[@action_utils:execute_navigation]   Verification config: {verification}")
                
                # Step-end screenshot after verification failure
                print(f"[@action_utils:execute_navigation] Attempting step-end screenshot capture after verification failure...")
                try:
                    step_end_screenshot_path = capture_validation_screenshot(host, device, f"{step_name}_end", script_context)
                    
                    if step_end_screenshot_path:
                        print(f"[@action_utils:execute_navigation] ✅ Step-end screenshot captured after verification failure: {step_end_screenshot_path}")
                    else:
                        print(f"[@action_utils:execute_navigation] ❌ Step-end screenshot capture returned None after verification failure")
                except Exception as screenshot_error:
                    print(f"[@action_utils:execute_navigation] ❌ Step-end screenshot capture exception after verification failure: {str(screenshot_error)}")
                    step_end_screenshot_path = None
                
                return {
                    'success': False,
                    'error': f'Verification {i+1} ({verification_type}) failed: {verification_error}',
                    'message': f'Navigation step failed during verification {i+1}',
                    'verification_results': verification_results,
                    'verification_images': verification_image_paths,  # Include verification images even on failure
                    'step_start_screenshot_path': step_start_screenshot_path,
                    'step_end_screenshot_path': step_end_screenshot_path,
                    'action_screenshots': action_screenshots,
                    'error_details': {
                        'verification_number': i+1,
                        'verification_type': verification_type,
                        'verification_error': verification_error,
                        'verification_config': verification,
                        'execution_time_ms': verification_execution_time
                    },
                    'global_verification_counter_increment': i + 1  # Increment by number of verifications executed so far
                }
        
        # Step-end screenshot after verifications complete
        print(f"[@action_utils:execute_navigation] Attempting step-end screenshot capture after successful completion...")
        try:
            step_end_screenshot_path = capture_validation_screenshot(host, device, f"{step_name}_end", script_context)
            
            if step_end_screenshot_path:
                print(f"[@action_utils:execute_navigation] ✅ Step-end screenshot captured: {step_end_screenshot_path}")
            else:
                print(f"[@action_utils:execute_navigation] ❌ Step-end screenshot capture returned None")
        except Exception as screenshot_error:
            print(f"[@action_utils:execute_navigation] ❌ Step-end screenshot capture exception: {str(screenshot_error)}")
            step_end_screenshot_path = None
        
        execution_time = time.time() - start_time
        
        return {
            'success': True,
            'message': 'Navigation step with verifications completed successfully',
            'verification_results': verification_results,
            'verifications_executed': len(verifications),
            'execution_time': execution_time,
            'screenshot_url': screenshot_url,
            'step_start_screenshot_path': step_start_screenshot_path,
            'step_end_screenshot_path': step_end_screenshot_path,
            'action_screenshots': action_screenshots,
            'verification_images': verification_image_paths,  # Add verification images for upload
            'global_verification_counter_increment': len(verifications)  # How much to increment the global counter
        }
        
    except Exception as e:
        import traceback
        print(f"[@action_utils:execute_navigation_with_verifications] ERROR: {str(e)}")
        print(f"[@action_utils:execute_navigation_with_verifications] TRACEBACK: {traceback.format_exc()}")
        
        # Try to capture step-end screenshot on exception
        step_end_screenshot_path = None
        print(f"[@action_utils:execute_navigation] Attempting step-end screenshot capture after exception...")
        try:
            # Use the same step_name format as before
            from_node = transition.get('from_node_label', 'unknown')
            to_node = transition.get('to_node_label', 'unknown')
            step_name = f"step_{transition.get('step_number', 'unknown')}_{from_node}_{to_node}"
            step_end_screenshot_path = capture_validation_screenshot(host, device, f"{step_name}_end_error", script_context)
            
            if step_end_screenshot_path:
                print(f"[@action_utils:execute_navigation] ✅ Step-end screenshot captured after exception: {step_end_screenshot_path}")
            else:
                print(f"[@action_utils:execute_navigation] ❌ Step-end screenshot capture returned None after exception")
        except Exception as screenshot_error:
            print(f"[@action_utils:execute_navigation] ❌ Step-end screenshot capture exception during exception handling: {str(screenshot_error)}")
            
        return {
            'success': False, 
            'error': f'Navigation step with verifications execution error: {str(e)}',
            'verification_results': [],
            'step_start_screenshot_path': None,  # We might not have gotten to capturing the start screenshot
            'step_end_screenshot_path': step_end_screenshot_path,
            'action_screenshots': [],
            'verification_images': [],
            'global_verification_counter_increment': 0
        }



def execute_edge_actions(host, device, edge: Dict, action_set_id: str = None, team_id: str = 'default') -> Dict:
    """
    Execute edge actions directly - no HTTP proxy, maximum performance.
    
    Args:
        host: Host instance 
        device: Device instance
        edge: Edge dictionary with action_sets
        action_set_id: Optional specific action set ID to execute (uses default if None)
        team_id: Team ID for database recording
        
    Returns:
        Execution result dictionary with success status and details (same format as ActionExecutor)
    """
    try:
        # Get action set by ID or use forward action set (index 0) as fallback
        action_sets = edge.get('action_sets', [])
        
        if action_set_id:
            # Find specific action set by ID
            action_set = next((s for s in action_sets if s.get('id') == action_set_id), None)
        else:
            # Use forward action set (index 0) as fallback
            action_set = action_sets[0] if action_sets else None
        
        if not action_set:
            return {
                'success': False, 
                'error': f'Action set not found (looking for: {action_set_id or "forward set"})'
            }
        
        actions = action_set.get('actions', [])
        retry_actions = action_set.get('retry_actions') or []
        failure_actions = action_set.get('failure_actions') or []
        
        print(f"[@action_utils:execute_edge_actions] Executing action set: {action_set.get('id')}")
        print(f"[@action_utils:execute_edge_actions] Actions: {len(actions)}, Retry actions: {len(retry_actions)}, Failure actions: {len(failure_actions)}")
        print(f"[@action_utils:execute_edge_actions] Using DIRECT execution (no HTTP proxy)")
        
        # Validate inputs
        if not actions:
            return {
                'success': True,
                'message': 'No actions to execute',
                'results': [],
                'passed_count': 0,
                'total_count': 0
            }
        
        # Filter valid actions
        valid_actions = [a for a in actions if a.get('command')]
        valid_retry_actions = [a for a in retry_actions if a.get('command')]
        valid_failure_actions = [a for a in failure_actions if a.get('command')]
        
        if not valid_actions:
            return {
                'success': False,
                'error': 'All actions were invalid and filtered out',
                'results': [],
                'passed_count': 0,
                'total_count': 0
            }
        
        results = []
        passed_count = 0
        action_screenshots = []
        
        # Execute main actions - stop on first failure
        print(f"[@action_utils:execute_edge_actions] Executing {len(valid_actions)} main actions")
        main_actions_failed = False
        
        for i, action in enumerate(valid_actions):
            start_time = time.time()
            
            try:
                print(f"[@action_utils:execute_edge_actions] Executing main action {i+1}: {action.get('command')} with params {action.get('params', {})}")
                
                # DIRECT EXECUTION - no HTTP proxy
                result = execute_action_directly(host, device, action)
                
                execution_time = int((time.time() - start_time) * 1000)
                
                # Capture screenshot after successful action
                screenshot_path = ""
                if result.get('success'):
                    screenshot_path = capture_validation_screenshot(
                        host, device, 
                        f"action_{i+1}_{action.get('command')}", 
                        "action"
                    )
                    if screenshot_path:
                        action_screenshots.append(screenshot_path)
                        print(f"[@action_utils:execute_edge_actions] Screenshot captured for action {i+1}: {screenshot_path}")
                
                # Add ActionExecutor-compatible fields
                enhanced_result = {
                    'success': result.get('success', False),
                    'message': action.get('command'),
                    'error': result.get('error') if not result.get('success') else None,
                    'resultType': 'PASS' if result.get('success') else 'FAIL',
                    'execution_time_ms': execution_time,
                    'action_category': 'main',
                    'screenshot_path': screenshot_path,
                }
                
                results.append(enhanced_result)
                
                print(f"[@action_utils:execute_edge_actions] Action {i+1} result: success={result.get('success')}, time={execution_time}ms")
                
                if result.get('success'):
                    passed_count += 1
                else:
                    # First action failed - stop executing remaining main actions
                    print(f"[@action_utils:execute_edge_actions] Main action {i+1} failed, stopping main action execution")
                    main_actions_failed = True
                    break
                    
            except Exception as e:
                execution_time = int((time.time() - start_time) * 1000)
                print(f"[@action_utils:execute_edge_actions] Action {i+1} error: {str(e)}")
                
                enhanced_result = {
                    'success': False,
                    'message': action.get('command'),
                    'error': str(e),
                    'resultType': 'FAIL',
                    'execution_time_ms': execution_time,
                    'action_category': 'main',
                }
                results.append(enhanced_result)
                main_actions_failed = True
                break
        
        # Execute retry actions if any main action failed
        if main_actions_failed and valid_retry_actions:
            print(f"[@action_utils:execute_edge_actions] Main actions failed, executing {len(valid_retry_actions)} retry actions")
            for i, retry_action in enumerate(valid_retry_actions):
                start_time = time.time()
                
                try:
                    print(f"[@action_utils:execute_edge_actions] Executing retry action {i+1}: {retry_action.get('command')}")
                    
                    # DIRECT EXECUTION - no HTTP proxy
                    result = execute_action_directly(host, device, retry_action)
                    
                    execution_time = int((time.time() - start_time) * 1000)
                    
                    enhanced_result = {
                        'success': result.get('success', False),
                        'message': retry_action.get('command'),
                        'error': result.get('error') if not result.get('success') else None,
                        'resultType': 'PASS' if result.get('success') else 'FAIL',
                        'execution_time_ms': execution_time,
                        'action_category': 'retry',
                    }
                    
                    results.append(enhanced_result)
                    
                    if result.get('success'):
                        passed_count += 1
                        
                except Exception as e:
                    execution_time = int((time.time() - start_time) * 1000)
                    enhanced_result = {
                        'success': False,
                        'message': retry_action.get('command'),
                        'error': str(e),
                        'resultType': 'FAIL',
                        'execution_time_ms': execution_time,
                        'action_category': 'retry',
                    }
                    results.append(enhanced_result)

        # Execute failure actions if retry actions also failed
        retry_actions_failed = main_actions_failed and valid_retry_actions and passed_count < len(valid_actions)
        if retry_actions_failed and valid_failure_actions:
            print(f"[@action_utils:execute_edge_actions] Retry actions failed, executing {len(valid_failure_actions)} failure actions")
            for i, failure_action in enumerate(valid_failure_actions):
                start_time = time.time()
                
                try:
                    print(f"[@action_utils:execute_edge_actions] Executing failure action {i+1}: {failure_action.get('command')}")
                    
                    # DIRECT EXECUTION - no HTTP proxy
                    result = execute_action_directly(host, device, failure_action)
                    
                    execution_time = int((time.time() - start_time) * 1000)
                    
                    enhanced_result = {
                        'success': result.get('success', False),
                        'message': failure_action.get('command'),
                        'error': result.get('error') if not result.get('success') else None,
                        'resultType': 'PASS' if result.get('success') else 'FAIL',
                        'execution_time_ms': execution_time,
                        'action_category': 'failure',
                    }
                    
                    results.append(enhanced_result)
                    
                    if result.get('success'):
                        passed_count += 1
                        
                except Exception as e:
                    execution_time = int((time.time() - start_time) * 1000)
                    enhanced_result = {
                        'success': False,
                        'message': failure_action.get('command'),
                        'error': str(e),
                        'resultType': 'FAIL',
                        'execution_time_ms': execution_time,
                        'action_category': 'failure',
                    }
                    results.append(enhanced_result)

        # Calculate overall success (main actions must pass)
        overall_success = passed_count >= len(valid_actions)
        
        print(f"[@action_utils:execute_edge_actions] Batch completed: {passed_count}/{len(valid_actions)} main actions passed, overall success: {overall_success}")
        
        # Build error message
        failed_actions = [r for r in results if not r.get('success')]
        if failed_actions:
            failed_names = [f.get('message', 'Unknown action') for f in failed_actions]
            error_message = f"Actions failed: {', '.join(failed_names)}"
        else:
            error_message = None
        
        # Return same format as ActionExecutor
        return {
            'success': overall_success,
            'total_count': len(valid_actions),
            'passed_count': passed_count,
            'failed_count': len(valid_actions) - passed_count,
            'results': results,
            'action_screenshots': action_screenshots,
            'message': f'Direct batch execution completed: {passed_count}/{len(valid_actions)} passed',
            'error': error_message
        }
        
    except Exception as e:
        error_msg = f'Direct edge action execution failed: {str(e)}'
        print(f"[@action_utils:execute_edge_actions] ERROR: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'results': [],
            'passed_count': 0,
            'total_count': 0,
            'action_screenshots': []  # Ensure consistent return format
        }


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
        return ""