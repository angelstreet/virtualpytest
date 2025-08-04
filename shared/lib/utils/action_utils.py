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
    
    Args:
        host: Host instance
        device: Device instance
        action: Action dictionary with 'command' and 'params'
        
    Returns:
        Dictionary with success status and execution details
    """
    try:
        command = action.get('command')
        params = action.get('params', {})
        
        remote_controller = get_controller(device.device_id, 'remote')
        if not remote_controller:
            return {
                'success': False,
                'error': f'No remote controller found for device {device.device_id}'
            }
        
        success = remote_controller.execute_command(command, params)
        
        return {
            'success': success,
            'message': f'{"Successfully executed" if success else "Failed to execute"} {command}'
        }
            
    except Exception as e:
        return {'success': False, 'error': f'Action execution error: {str(e)}'}


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
        
        return {
            'success': result.get('success', False),
            'message': result.get('message', 'Verification completed'),
            'error': result.get('message', 'Verification completed') if not result.get('success', False) else None,
            'verification_type': verification_type,
            'resultType': 'PASS' if result.get('success') else 'FAIL'
        }
            
    except Exception as e:
        import traceback
        print(f"[@action_utils:execute_verification_directly] ERROR: {str(e)}")
        print(f"[@action_utils:execute_verification_directly] TRACEBACK: {traceback.format_exc()}")
        return {'success': False, 'error': f'Verification execution error: {str(e)}'}


def execute_navigation_with_verifications(host, device, transition: Dict[str, Any], team_id: str, tree_id: str = None, script_result_id: str = None, script_context: str = 'script') -> Dict[str, Any]:
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
        
        remote_controller = get_controller(device.device_id, 'remote')
        if not remote_controller:
            return {
                'success': False,
                'error': f'No remote controller found for device {device.device_id}',
                'verification_results': []
            }
        
        # Log detailed action information before execution
        edge_id = transition.get('edge_id', 'unknown')
        from_node = transition.get('from_node_label', 'unknown')
        to_node = transition.get('to_node_label', 'unknown')
        
        print(f"[@action_utils:execute_navigation] Executing navigation step: {from_node} → {to_node}")
        print(f"[@action_utils:execute_navigation] Edge ID: {edge_id}")
        print(f"[@action_utils:execute_navigation] Actions to execute: {len(actions)}")
        print(f"[@action_utils:execute_navigation] Retry actions available: {len(retry_actions)}, Failure actions available: {len(failure_actions)}")
        
        # Log each action for debugging
        for i, action in enumerate(actions):
            action_cmd = action.get('command', 'unknown')
            action_params = action.get('params', {})
            print(f"[@action_utils:execute_navigation] Action {i+1}: {action_cmd} with params: {action_params}")
        
        action_start_time = time.time()
        actions_success = remote_controller.execute_sequence(actions, retry_actions, failure_actions)
        action_execution_time = int((time.time() - action_start_time) * 1000)
        
        # Capture screenshot after action execution using existing function
        screenshot_path = capture_validation_screenshot(host, device, f"action_{from_node}_{to_node}", script_context)
        screenshot_url = None
        if screenshot_path:
            # Upload screenshot to Cloudflare R2 (same as existing validation script)
            from shared.lib.utils.cloudflare_utils import get_cloudflare_utils
            try:
                uploader = get_cloudflare_utils()
                step_name = f"step_{transition.get('step_number', 'unknown')}_{from_node}_{to_node}"
                remote_path = f"action-screenshots/{device.device_id}/{step_name}.png"
                upload_result = uploader.upload_file(screenshot_path, remote_path)
                if upload_result.get('success'):
                    screenshot_url = upload_result.get('url')
            except Exception as e:
                print(f"[@action_utils:execute_navigation] Screenshot upload failed: {e}")
        
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
            
            # Try to get more specific error from remote controller if available
            detailed_error = "Action execution failed"
            if hasattr(remote_controller, 'get_last_error'):
                last_error = remote_controller.get_last_error()
                if last_error:
                    detailed_error = f"Action execution failed: {last_error}"
                    print(f"[@action_utils:execute_navigation]   Remote controller error: {last_error}")
        else:
            print(f"[@action_utils:execute_navigation] Actions completed successfully in {action_execution_time}ms")
            error_details = None
            detailed_error = None
        
        if tree_id and actions:
            try:
                from shared.lib.supabase.execution_results_db import record_edge_execution
                record_edge_execution(
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
                    script_context=script_context
                )
            except Exception:
                pass  # Silent fail as per optimization
        
        if not actions_success:
            return {
                'success': False,
                'error': detailed_error or 'Navigation actions failed',
                'message': f'Navigation step failed during action execution: {from_node} → {to_node}',
                'verification_results': [],
                'error_details': error_details
            }
        
        verifications = transition.get('verifications', [])
        verification_results = []
        
        for i, verification in enumerate(verifications):
            verification_start_time = time.time()
            verify_result = execute_verification_directly(host, device, verification)
            verification_execution_time = int((time.time() - verification_start_time) * 1000)
            
            if tree_id:
                try:
                    from shared.lib.supabase.execution_results_db import record_node_execution
                    node_id = transition.get('to_node_id', 'unknown')
                    record_node_execution(
                        team_id=team_id,
                        tree_id=tree_id,
                        node_id=node_id,
                        host_name=host.host_name,
                        success=verify_result.get('success', False),
                        execution_time_ms=verification_execution_time,
                        message=verify_result.get('message', 'Verification completed'),
                        error_details={'error': verify_result.get('error')} if verify_result.get('error') else None,
                        script_result_id=script_result_id,
                        script_context=script_context
                    )
                except Exception:
                    pass
            
            verification_result = {
                'verification_number': i + 1,
                'verification_type': verification.get('verification_type', 'adb'),
                'success': verify_result.get('success', False),
                'message': verify_result.get('message', 'Verification completed'),
                'resultType': 'PASS' if verify_result.get('success') else 'FAIL',
                'error': verify_result.get('error') if not verify_result.get('success') else None
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
                
                return {
                    'success': False,
                    'error': f'Verification {i+1} ({verification_type}) failed: {verification_error}',
                    'message': f'Navigation step failed during verification {i+1}',
                    'verification_results': verification_results,
                    'error_details': {
                        'verification_number': i+1,
                        'verification_type': verification_type,
                        'verification_error': verification_error,
                        'verification_config': verification,
                        'execution_time_ms': verification_execution_time
                    }
                }
        
        execution_time = time.time() - start_time
        
        return {
            'success': True,
            'message': 'Navigation step with verifications completed successfully',
            'verification_results': verification_results,
            'verifications_executed': len(verifications),
            'execution_time': execution_time,
            'screenshot_url': screenshot_url
        }
        
    except Exception as e:
        import traceback
        print(f"[@action_utils:execute_navigation_with_verifications] ERROR: {str(e)}")
        print(f"[@action_utils:execute_navigation_with_verifications] TRACEBACK: {traceback.format_exc()}")
        return {
            'success': False, 
            'error': f'Navigation step with verifications execution error: {str(e)}',
            'verification_results': []
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
        # Get action set (specific or default)
        action_sets = edge.get('action_sets', [])
        default_action_set_id = edge.get('default_action_set_id')
        
        if action_set_id:
            # Find specific action set by ID
            action_set = next((s for s in action_sets if s.get('id') == action_set_id), None)
        else:
            # Use default action set
            action_set = next((s for s in action_sets if s.get('id') == default_action_set_id), 
                            action_sets[0] if action_sets else None)
        
        if not action_set:
            return {
                'success': False, 
                'error': f'Action set not found (looking for: {action_set_id or default_action_set_id})'
            }
        
        actions = action_set.get('actions', [])
        retry_actions = action_set.get('retry_actions', [])
        failure_actions = action_set.get('failure_actions', [])
        
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
                
                # Add ActionExecutor-compatible fields
                enhanced_result = {
                    'success': result.get('success', False),
                    'message': action.get('command'),
                    'error': result.get('error') if not result.get('success') else None,
                    'resultType': 'PASS' if result.get('success') else 'FAIL',
                    'execution_time_ms': execution_time,
                    'action_category': 'main',
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
            'total_count': 0
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
        av_controller = get_controller(device.device_id, 'av')
        
        screenshot_path = av_controller.take_screenshot()
        
        return screenshot_path
            
    except Exception:
        return ""