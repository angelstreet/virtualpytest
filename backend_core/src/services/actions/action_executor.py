"""
Standardized Action Executor

This module provides a standardized way to execute actions that can be used by:
- Python code directly (navigation execution, scripts, etc.)
- API endpoints (maintaining consistency)
- Frontend hooks (via API calls)

The core logic is the same as /server/action/executeBatch but available as a reusable class.
"""

import time
import requests
from typing import Dict, List, Optional, Any
from shared.lib.utils.route_utils import proxy_to_host_direct


class ActionExecutor:
    """
    Standardized action executor that provides consistent action execution
    across Python code and API endpoints.
    """
    
    def __init__(self, host: Dict[str, Any], device_id: Optional[str] = None, tree_id: str = None, edge_id: str = None, team_id: str = None):
        """
        Initialize ActionExecutor
        
        Args:
            host: Host configuration dict with host_name, devices, etc.
            device_id: Optional device ID for multi-device hosts
            tree_id: Tree ID for navigation context
            edge_id: Edge ID for navigation context
            team_id: Team ID for database context
        """
        self.host = host
        self.device_id = device_id
        self.tree_id = tree_id
        self.edge_id = edge_id
        
        # team_id is required
        self.team_id = team_id
        
        # Validate host configuration
        if not host or not host.get('host_name'):
            raise ValueError("Host configuration with host_name is required")
    
    def execute_actions(self, 
                       actions: List[Dict[str, Any]], 
                       retry_actions: Optional[List[Dict[str, Any]]] = None,
                       failure_actions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Execute batch of actions with retry logic
        
        Args:
            actions: List of action dictionaries with command, params, etc.
            retry_actions: Optional list of retry actions to execute if main actions fail
            
        Returns:
            Dict with success status, results, and execution statistics
        """
        print(f"[@lib:action_executor:execute_actions] Starting batch action execution")
        print(f"[@lib:action_executor:execute_actions] Processing {len(actions)} main actions, {len(retry_actions or [])} retry actions")
        print(f"[@lib:action_executor:execute_actions] Host: {self.host.get('host_name')}")
        
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
        valid_actions = self._filter_valid_actions(actions)
        valid_retry_actions = self._filter_valid_actions(retry_actions or [])
        valid_failure_actions = self._filter_valid_actions(failure_actions or [])
        
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
        execution_order = 1
        
        # Execute main actions - stop on first failure
        print(f"[@lib:action_executor:execute_actions] Executing {len(valid_actions)} main actions")
        main_actions_failed = False
        
        for i, action in enumerate(valid_actions):
            result = self._execute_single_action(action, execution_order, i+1, 'main')
            results.append(result)
            
            if result.get('success'):
                passed_count += 1
            else:
                # First action failed - stop executing remaining main actions
                print(f"[@lib:action_executor:execute_actions] Main action {i+1} failed, stopping main action execution")
                main_actions_failed = True
                break
                
            execution_order += 1
        
        # Execute retry actions if any main action failed
        retry_actions_passed = 0
        retry_actions_failed = False
        if main_actions_failed and valid_retry_actions:
            print(f"[@lib:action_executor:execute_actions] Main actions failed, executing {len(valid_retry_actions)} retry actions")
            for i, retry_action in enumerate(valid_retry_actions):
                result = self._execute_single_action(retry_action, execution_order, i+1, 'retry')
                results.append(result)
                if result.get('success'):
                    retry_actions_passed += 1
                else:
                    # Stop on first retry failure
                    print(f"[@lib:action_executor:execute_actions] Retry action {i+1} failed, stopping retry execution")
                    retry_actions_failed = True
                    break
                execution_order += 1

        # Execute failure actions if retry actions also failed
        failure_actions_passed = 0
        failure_actions_failed = False
        if main_actions_failed and retry_actions_failed and valid_failure_actions:
            print(f"[@lib:action_executor:execute_actions] Retry actions failed, executing {len(valid_failure_actions)} failure actions")
            for i, failure_action in enumerate(valid_failure_actions):
                result = self._execute_single_action(failure_action, execution_order, i+1, 'failure')
                results.append(result)
                if result.get('success'):
                    failure_actions_passed += 1
                else:
                    # Stop on first failure action failure
                    print(f"[@lib:action_executor:execute_actions] Failure action {i+1} failed, stopping failure execution")
                    failure_actions_failed = True
                    break
                execution_order += 1

        # Calculate overall success: main actions must pass OR ALL retry actions must pass if main failed
        if main_actions_failed:
            # If main failed but we have retry actions, success depends on retry actions
            if valid_retry_actions:
                overall_success = not retry_actions_failed and retry_actions_passed == len(valid_retry_actions)
            else:
                # If main failed and no retry actions available, it's a failure
                overall_success = False
        else:
            overall_success = passed_count >= len(valid_actions)
        
        if main_actions_failed and valid_retry_actions:
            print(f"[@lib:action_executor:execute_actions] Batch completed: {passed_count}/{len(valid_actions)} main actions passed, {retry_actions_passed}/{len(valid_retry_actions)} retry actions passed, overall success: {overall_success}")
        else:
            print(f"[@lib:action_executor:execute_actions] Batch completed: {passed_count}/{len(valid_actions)} main actions passed, overall success: {overall_success}")
        
        # Build simple error message showing which actions failed
        failed_actions = [r for r in results if not r.get('success')]
        
        if failed_actions:
            failed_names = [f.get('message', 'Unknown action') for f in failed_actions]
            error_message = f"Actions failed: {', '.join(failed_names)}"
        else:
            error_message = None
        
        return {
            'success': overall_success,
            'total_count': len(valid_actions),
            'passed_count': passed_count,
            'failed_count': len(valid_actions) - passed_count,
            'results': results,
            'message': f'Batch action execution completed: {passed_count}/{len(valid_actions)} passed',
            'error': error_message
        }
    
    def _filter_valid_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out invalid actions"""
        valid_actions = []
        
        for i, action in enumerate(actions):
            if not action.get('command') or action.get('command', '').strip() == '':
                print(f"[@lib:action_executor:_filter_valid_actions] Removing action {i}: No command specified")
                continue
            
            # Check if action requires input and has it
            if action.get('requiresInput') and not action.get('inputValue'):
                print(f"[@lib:action_executor:_filter_valid_actions] Removing action {i}: No input value for required input")
                continue
            
            valid_actions.append(action)
        
        return valid_actions
    
    def _execute_single_action(self, action: Dict[str, Any], execution_order: int, action_number: int, action_category: str) -> Dict[str, Any]:
        """Execute a single action and return standardized result"""
        
        # Get iterator count (default to 1 if not specified)
        # Only allow iterations for non-verification actions
        action_type = action.get('action_type', 'remote')
        if action_type == 'verification':
            iterator_count = 1  # Force single execution for verifications
        else:
            iterator_count = action.get('iterator', 1)
            if iterator_count < 1 or iterator_count > 100:
                iterator_count = 1  # Clamp to valid range
        
        if action_type == 'verification':
            print(f"[@lib:action_executor:_execute_single_action] Executing {action_category} verification {action_number}: {action.get('command')} (verifications always run once)")
        else:
            print(f"[@lib:action_executor:_execute_single_action] Executing {action_category} action {action_number}: {action.get('command')} with {iterator_count} iteration(s)")
        
        # Track results for all iterations
        all_iterations_successful = True
        total_execution_time = 0
        iteration_results = []
        
        for iteration in range(iterator_count):
            iteration_start_time = time.time()
            
            try:
                iteration_label = f"iteration {iteration + 1}/{iterator_count}" if iterator_count > 1 else ""
                print(f"[@lib:action_executor:_execute_single_action] Executing {action_category} action {action_number} {iteration_label}: {action.get('command')} with params {action.get('params', {})}")
                
                # Use action params directly - wait_time is already in params from database
                params = action.get('params', {})
                action_type = action.get('action_type')
                
                # Device-aware action_type detection using controller factory
                if not action_type:
                    command = action.get('command', '')
                    
                    # Get device model for intelligent routing
                    device_model = self._get_device_model()
                    if iteration == 0:  # Only log once
                        print(f"[@lib:action_executor:_execute_single_action] Device model: {device_model}")
                    
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
                    
                    # First check for controller-specific commands
                    if command in web_only_commands:
                        action_type = 'web'
                        if iteration == 0:
                            print(f"[@lib:action_executor:_execute_single_action] Web-only command detected: {command}")
                    elif command in desktop_only_commands:
                        action_type = 'desktop'
                        if iteration == 0:
                            print(f"[@lib:action_executor:_execute_single_action] Desktop-only command detected: {command}")
                    elif command in verification_commands:
                        action_type = 'verification'
                        if iteration == 0:
                            print(f"[@lib:action_executor:_execute_single_action] Verification command detected: {command}")
                    else:
                        # For generic commands (click_element, input_text, press_key), use device capabilities
                        from backend_core.src.controllers.controller_config_factory import get_controller_type_for_device, DEVICE_CONTROLLER_MAP
                        
                        # Check what controllers this device has and route accordingly
                        if device_model in DEVICE_CONTROLLER_MAP:
                            device_mapping = DEVICE_CONTROLLER_MAP[device_model]
                            
                            # Priority order: web > desktop > remote (most specific to least specific)
                            if device_mapping.get('web', []):
                                action_type = 'web'
                                if iteration == 0:
                                    print(f"[@lib:action_executor:_execute_single_action] Generic command '{command}' routed to web (device has web controller)")
                            elif device_mapping.get('desktop', []):
                                action_type = 'desktop'
                                if iteration == 0:
                                    print(f"[@lib:action_executor:_execute_single_action] Generic command '{command}' routed to desktop (device has desktop controller)")
                            elif device_mapping.get('remote', []):
                                action_type = 'remote'
                                if iteration == 0:
                                    print(f"[@lib:action_executor:_execute_single_action] Generic command '{command}' routed to remote (device has remote controller)")
                            else:
                                # Fallback to remote
                                action_type = 'remote'
                                if iteration == 0:
                                    print(f"[@lib:action_executor:_execute_single_action] Generic command '{command}' defaulted to remote (no specific controllers found)")
                        else:
                            # Unknown device model - default to remote
                            action_type = 'remote'
                            if iteration == 0:
                                print(f"[@lib:action_executor:_execute_single_action] Unknown device model '{device_model}', defaulting to remote for command '{command}'")
                
                if iteration == 0:  # Only log action type once
                    print(f"[@lib:action_executor:_execute_single_action] Action type: {action_type}")
                
                # Route to appropriate endpoint based on action_type
                if action_type == 'verification':
                    verification_type = action.get('verification_type', 'text')  # Default to text verification
                    if iteration == 0:  # Only log routing once
                        print(f"[@lib:action_executor:_execute_single_action] Routing verification action to verification_{verification_type} endpoint")
                    
                    # Route to verification endpoint
                    endpoint = f'/host/verification/{verification_type}/execute'
                    request_data = {
                        'verification': {
                            'verification_type': verification_type,
                            'command': action.get('command'),
                            'params': params
                        },
                        'device_id': self.device_id or 'device1'
                    }
                elif action_type == 'web':
                    # Route to web endpoint
                    if iteration == 0:  # Only log routing once
                        print(f"[@lib:action_executor:_execute_single_action] Routing web action to web endpoint")
                    endpoint = '/host/web/executeCommand'
                    request_data = {
                        'command': action.get('command'),
                        'params': params,
                        'device_id': self.device_id or 'device1'
                    }
                elif action_type == 'desktop':
                    # Intelligent routing to correct desktop controller
                    command = action.get('command', '')
                    
                    # Bash-specific commands
                    bash_commands = {'execute_bash_command'}
                    
                    if command in bash_commands:
                        endpoint = '/host/desktop/bash/executeCommand'
                        if iteration == 0:  # Only log routing once
                            print(f"[@lib:action_executor:_execute_single_action] Routing desktop action to bash endpoint")
                    else:
                        # Default to pyautogui for all other desktop commands
                        endpoint = '/host/desktop/pyautogui/executeCommand'
                        if iteration == 0:  # Only log routing once
                            print(f"[@lib:action_executor:_execute_single_action] Routing desktop action to pyautogui endpoint")
                    
                    request_data = {
                        'command': action.get('command'),
                        'params': params,
                        'device_id': self.device_id or 'device1'
                    }
                else:
                    # Route to remote endpoint (default behavior for remote actions)
                    if iteration == 0:  # Only log routing once
                        print(f"[@lib:action_executor:_execute_single_action] Routing {action_type} action to remote endpoint")
                    endpoint = '/host/remote/executeCommand'
                    request_data = {
                        'command': action.get('command'),
                        'params': params,
                        'device_id': self.device_id or 'device1'
                    }
                
                # Proxy to appropriate host endpoint using direct host info (no Flask context needed)
                response_data, status_code = proxy_to_host_direct(self.host, endpoint, 'POST', request_data)
                
                iteration_execution_time = int((time.time() - iteration_start_time) * 1000)
                iteration_success = status_code == 200 and response_data.get('success', False)
                
                total_execution_time += iteration_execution_time
                
                if iterator_count > 1:
                    print(f"[@lib:action_executor:_execute_single_action] Action {action_number} iteration {iteration + 1}/{iterator_count} result: success={iteration_success}, time={iteration_execution_time}ms")
                else:
                    print(f"[@lib:action_executor:_execute_single_action] Action {action_number} result: success={iteration_success}, time={iteration_execution_time}ms")
                
                # Track iteration results
                iteration_results.append({
                    'iteration': iteration + 1,
                    'success': iteration_success,
                    'execution_time_ms': iteration_execution_time,
                    'message': response_data.get('message') if iteration_success else response_data.get('error')
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
                        print(f"[@lib:action_executor:_execute_single_action] [{iter_time}] Waiting {wait_time}ms between iterations")
                        time.sleep(wait_time / 1000.0)
                        iter_end_time = time.strftime("%H:%M:%S", time.localtime())
                        print(f"[@lib:action_executor:_execute_single_action] [{iter_end_time}] Iteration wait completed")
                
            except Exception as e:
                iteration_execution_time = int((time.time() - iteration_start_time) * 1000)
                total_execution_time += iteration_execution_time
                all_iterations_successful = False
                
                iteration_results.append({
                    'iteration': iteration + 1,
                    'success': False,
                    'execution_time_ms': iteration_execution_time,
                    'message': str(e)
                })
                
                print(f"[@lib:action_executor:_execute_single_action] Action {action_number} iteration {iteration + 1}/{iterator_count} error: {str(e)}")
                # Stop on exception - don't continue iterations
                break
        
        # Wait after successful action execution (once per action, after all iterations)
        wait_time = params.get('wait_time', 0)
        if all_iterations_successful and wait_time > 0:
            wait_seconds = wait_time / 1000.0
            current_time = time.strftime("%H:%M:%S", time.localtime())
            print(f"[@lib:action_executor:_execute_single_action] [{current_time}] Waiting {wait_time}ms after successful {action.get('command')} execution")
            time.sleep(wait_seconds)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            print(f"[@lib:action_executor:_execute_single_action] [{end_time}] Wait completed after {action.get('command')}")
        
        # Record execution to database (summary of all iterations)
        self._record_execution_to_database(
            success=all_iterations_successful,
            execution_time_ms=total_execution_time,
            message=f"{action.get('command')} ({len(iteration_results)}/{iterator_count} iterations)" if iterator_count > 1 else f"{action.get('command')}",
            error_details={'iterations': iteration_results} if not all_iterations_successful else None
        )
        
        # Return standardized result (same format as API)
        result_message = f"{action.get('command')}"
        if iterator_count > 1:
            successful_iterations = len([r for r in iteration_results if r['success']])
            result_message += f" ({successful_iterations}/{iterator_count} iterations)"
        
        return {
            'success': all_iterations_successful,
            'message': result_message,
            'error': None if all_iterations_successful else f"Failed after {len(iteration_results)} iteration(s)",
            'resultType': 'PASS' if all_iterations_successful else 'FAIL',
            'execution_time_ms': total_execution_time,
            'action_category': action_category,
            'iterations': iteration_results if iterator_count > 1 else None
        }
    
    def _get_device_model(self) -> str:
        """Get device model for the current device_id."""
        try:
            # Import here to avoid circular imports
            from shared.lib.utils.host_utils import get_device_by_id
            
            device = get_device_by_id(self.device_id or 'device1')
            if device:
                return device.device_model
            else:
                print(f"[@lib:action_executor:_get_device_model] Device {self.device_id} not found, using 'unknown'")
                return 'unknown'
        except Exception as e:
            print(f"[@lib:action_executor:_get_device_model] Error getting device model: {e}")
            return 'unknown'
    
    def _record_execution_to_database(self, success: bool, execution_time_ms: int, message: str, error_details: Optional[Dict] = None):
        """Record single execution directly to database"""
        try:
            from shared.lib.supabase.execution_results_db import record_edge_execution
            
            record_edge_execution(
                team_id=self.team_id,
                tree_id=self.tree_id,
                edge_id=self.edge_id,
                host_name=self.host.get('host_name'),
                success=success,
                execution_time_ms=execution_time_ms,
                message=message,
                error_details=error_details,
                script_result_id=getattr(self, 'script_result_id', None),
                script_context=getattr(self, 'script_context', 'direct')
            )
            
        except Exception as e:
            print(f"[@lib:action_executor:_record_execution_to_database] Database recording error: {e}") 