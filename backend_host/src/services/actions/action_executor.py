"""
Standardized Action Executor

This module provides a standardized way to execute actions that can be used by:
- Python code directly (navigation execution, scripts, etc.)
- API endpoints (maintaining consistency)
- Frontend hooks (via API calls)

The core logic is the same as /server/action/executeBatch but available as a reusable class.
"""

import time
from typing import Dict, List, Optional, Any
from shared.src.lib.supabase.execution_results_db import record_edge_execution


class ActionExecutor:
    """
    Standardized action executor that provides consistent action execution
    across Python code and API endpoints.
    
    CRITICAL: Do not create new instances directly! Use device.action_executor instead.
    Each device has a singleton ActionExecutor that preserves state and caches.
    """
    
    @classmethod
    def get_for_device(cls, device):
        """
        Factory method to get the device's existing ActionExecutor.
        
        RECOMMENDED: Use device.action_executor directly instead of this method.
        
        Args:
            device: Device instance
            
        Returns:
            The device's existing ActionExecutor instance
            
        Raises:
            ValueError: If device doesn't have an action_executor
        """
        if not hasattr(device, 'action_executor') or not device.action_executor:
            raise ValueError(f"Device {device.device_id} does not have an ActionExecutor. "
                           "ActionExecutors are created during device initialization.")
        return device.action_executor
    
    @staticmethod
    def _parse_wait_time(wait_time) -> int:
        """Parse and validate wait_time parameter"""
        try:
            wait_time = int(wait_time)
        except (ValueError, TypeError):
            wait_time = 0
        return max(0, wait_time)  # Ensure non-negative
    
    @staticmethod
    def _parse_iterator_count(iterator_count) -> int:
        """Parse and validate iterator count parameter"""
        try:
            iterator_count = int(iterator_count)
        except (ValueError, TypeError):
            iterator_count = 1
        return max(1, min(iterator_count, 100))  # Clamp to valid range [1, 100]
    
    def __init__(self, device, tree_id: str = None, edge_id: str = None, action_set_id: Optional[str] = None, _from_device_init: bool = False):
        """
        Initialize ActionExecutor
        
        Args:
            device: Device instance (mandatory, contains host_name and device_id)
            tree_id: Tree ID for navigation context
            edge_id: Edge ID for navigation context
            action_set_id: Action set ID for navigation context
            _from_device_init: Internal flag to indicate creation from device initialization
        """
        # Validate required parameters - fail fast if missing
        if not device:
            raise ValueError("Device instance is required")
        if not device.host_name:
            raise ValueError("Device must have host_name")
        if not device.device_id:
            raise ValueError("Device must have device_id")
        
        # Warn if creating instance outside of device initialization
        if not _from_device_init:
            import traceback
            print(f"⚠️ [ActionExecutor] WARNING: Creating new ActionExecutor instance for device {device.device_id}")
            print(f"⚠️ [ActionExecutor] This may cause state loss! Use device.action_executor instead.")
            print(f"⚠️ [ActionExecutor] Call stack:")
            for line in traceback.format_stack()[-3:-1]:  # Show last 2 stack frames
                print(f"⚠️ [ActionExecutor]   {line.strip()}")
        
        # Store instances directly
        self.device = device
        self.host_name = device.host_name
        self.device_id = device.device_id
        self.device_model = device.device_model
        # Navigation context - REMOVED: Now using device.navigation_context
        # Action-specific context
        self.edge_id = edge_id
        self.action_set_id = action_set_id
        
        # Get AV controller directly from device
        self.av_controller = device._get_controller('av')
        if not self.av_controller:
            print(f"[@action_executor] Warning: No AV controller found for device {self.device_id}")
        
        # Initialize screenshot tracking
        self.action_screenshots = []
        
        # Cache for action type detection to avoid repeated controller lookups
        self._action_type_cache = {}
    
    def get_available_context(self, userinterface_name: str = None) -> Dict[str, Any]:
        """
        Get available action context for AI based on user interface
        
        Args:
            userinterface_name: User interface name for context
            
        Returns:
            Dict with available actions and their descriptions
        """
        try:
            device_actions = []
            
            print(f"[@action_executor] Loading action context for device: {self.device_id}, model: {self.device_model}")
            
            # Get actions from each controller type
            controller_types = ['remote', 'web', 'desktop_bash', 'desktop_pyautogui', 'av', 'power']
            
            for controller_type in controller_types:
                try:
                    # Direct controller access from device instance
                    controller = self.device._get_controller(controller_type)
                    if controller and hasattr(controller, 'get_available_actions'):
                        actions = controller.get_available_actions()
                        if isinstance(actions, dict):
                            for category, action_list in actions.items():
                                if isinstance(action_list, list):
                                    for action in action_list:
                                        device_actions.append({
                                            'command': action.get('command', ''),
                                            'action_type': action.get('action_type', controller_type.replace('desktop_', 'desktop')),
                                            'params': action.get('params', {}),
                                            'description': action.get('description', '')
                                        })
                        elif isinstance(actions, list):
                            for action in actions:
                                device_actions.append({
                                    'command': action.get('command', ''),
                                    'action_type': action.get('action_type', controller_type.replace('desktop_', 'desktop')),
                                    'params': action.get('params', {}),
                                    'description': action.get('description', '')
                                })
                except Exception as e:
                    print(f"[@action_executor] Could not load {controller_type} actions: {e}")
                    continue
            
            print(f"[@action_executor] Loaded {len(device_actions)} actions from controllers")
            
            return {
                'service_type': 'actions',
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,
                'available_actions': device_actions
            }
            
        except Exception as e:
            print(f"[@action_executor] Error loading action context: {e}")
            return {
                'service_type': 'actions',
                'device_id': self.device_id,
                'device_model': self.device_model,
                'userinterface_name': userinterface_name,
                'available_actions': []
            }
    
    def execute_actions(self, 
                       actions: List[Dict[str, Any]], 
                       retry_actions: Optional[List[Dict[str, Any]]] = None,
                       failure_actions: Optional[List[Dict[str, Any]]] = None,
                       team_id: str = None,
                       context = None) -> Dict[str, Any]:
        """
        Execute batch of actions with retry logic
        
        Args:
            actions: List of action dictionaries with command, params, etc.
            retry_actions: Optional list of retry actions to execute if main actions fail
            
        Returns:
            Dict with success status, results, and execution statistics
        """
        # Build action summary for consolidated logging
        action_summary = f"{len(actions)} actions"
        if retry_actions:
            action_summary += f", {len(retry_actions)} retry"
        if failure_actions:
            action_summary += f", {len(failure_actions)} failure"
        
        print(f"[@lib:action_executor:execute_actions] Executing {action_summary} on {self.host_name}")
        
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
        main_actions_failed = False
        
        for i, action in enumerate(valid_actions):
            result = self._execute_single_action(action, execution_order, i+1, 'main', team_id, context)
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
                result = self._execute_single_action(retry_action, execution_order, i+1, 'retry', team_id, context)
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
                result = self._execute_single_action(failure_action, execution_order, i+1, 'failure', team_id, context)
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
        
        # Calculate total execution time
        total_execution_time = sum(r.get('execution_time_ms', 0) for r in results)
        
        # Record edge execution to database if we have navigation context
        nav_context = self.device.navigation_context
        tree_id = nav_context['current_tree_id']
        if tree_id and self.edge_id and valid_actions:
            self._record_edge_execution(
                success=overall_success,
                execution_time_ms=total_execution_time,
                error_details=error_message if not overall_success else None,
                team_id=team_id
            )
        
        return {
            'success': overall_success,
            'total_count': len(valid_actions),
            'passed_count': passed_count,
            'failed_count': len(valid_actions) - passed_count,
            'results': results,
            'action_screenshots': self.action_screenshots,  # NEW: Include screenshots
            'message': f'Batch action execution completed: {passed_count}/{len(valid_actions)} passed',
            'error': error_message,
            'execution_time_ms': total_execution_time
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
    
    def _execute_single_action(self, action: Dict[str, Any], execution_order: int, action_number: int, action_category: str, team_id: str = None, context = None) -> Dict[str, Any]:
        """Execute a single action and return standardized result"""
        
        # Get iterator count (default to 1 if not specified)
        # Only allow iterations for non-verification actions
        action_type = action.get('action_type', 'remote')
        if action_type == 'verification':
            iterator_count = 1  # Force single execution for verifications
        else:
            iterator_count = self._parse_iterator_count(action.get('iterator', 1))
        
        # Consolidated action execution log
        action_desc = f"{action_category} {action_number}: {action.get('command')}"
        if iterator_count > 1:
            action_desc += f" ({iterator_count}x)"
        print(f"[@lib:action_executor:_execute_single_action] {action_desc}")
        
        # Track results for all iterations
        all_iterations_successful = True
        total_execution_time = 0
        iteration_results = []
        
        for iteration in range(iterator_count):
            iteration_start_time = time.time()
            
            try:
                # Use action params directly - wait_time is already in params from database
                params = action.get('params', {})
                action_type = action.get('action_type')
                
                # Dynamic action_type detection based on device controllers (with caching)
                if not action_type:
                    command = action.get('command', '')
                    if command in self._action_type_cache:
                        action_type = self._action_type_cache[command]
                    else:
                        action_type = self._detect_action_type_from_device(command)
                        self._action_type_cache[command] = action_type
                
                # Log controller type and params only on first iteration
                if iteration == 0:
                    controller_info = f"→ {action_type}"
                    if params:
                        # Show only essential params
                        essential_params = {}
                        for key in ['element_id', 'text', 'xpath', 'wait_time']:
                            if key in params and params[key]:
                                essential_params[key] = params[key]
                        if essential_params:
                            controller_info += f" {essential_params}"
                    print(f"[@lib:action_executor:_execute_single_action] {controller_info}")
                
                # Route to appropriate endpoint based on action_type
                if action_type == 'verification':
                    verification_type = action.get('verification_type', 'text')  # Default to text verification
                    
                    # Route to verification endpoint
                    endpoint = f'/host/verification/{verification_type}/execute'
                    request_data = {
                        'verification': {
                            'verification_type': verification_type,
                            'command': action.get('command'),
                            'params': params
                        },
                        'device_id': self.device_id
                    }
                elif action_type == 'web':
                    # Route to web endpoint
                    
                    # Transform parameters for web controller compatibility
                    web_params = params.copy()
                    # Convert element_id to selector for web actions
                    if 'element_id' in web_params and 'selector' not in web_params:
                        web_params['selector'] = web_params.pop('element_id')
                        if iteration == 0:  # Only log transformation once
                            print(f"[@lib:action_executor:_execute_single_action] Transformed element_id to selector for web action")
                    
                    endpoint = '/host/web/executeCommand'
                    request_data = {
                        'command': action.get('command'),
                        'params': web_params,
                        'device_id': self.device_id
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
                        'device_id': self.device_id
                    }
                else:
                    # Route to remote endpoint (default behavior for remote actions)
                    endpoint = '/host/remote/executeCommand'
                    request_data = {
                        'command': action.get('command'),
                        'params': params,
                        'device_id': self.device_id
                    }
                
                # Execute action using direct controller access (we are the host)
                if action_type == 'web':
                    # Use web controller directly
                    web_controller = self.device._get_controller('web')
                    if web_controller:
                        response_data = web_controller.execute_command(
                            command=request_data['command'],
                            params=request_data['params']
                        )
                        status_code = 200 if response_data.get('success', False) else 500
                    else:
                        response_data = {'success': False, 'error': 'Web controller not available'}
                        status_code = 500
                        
                elif action_type == 'desktop':
                    # Use appropriate desktop controller
                    command = action.get('command', '')
                    bash_commands = {'execute_bash_command'}
                    
                    if command in bash_commands:
                        # Use bash desktop controller
                        bash_controller = self.device._get_controller('desktop')  # Gets first desktop controller
                        if bash_controller and hasattr(bash_controller, 'execute_bash_command'):
                            response_data = bash_controller.execute_command(
                                command=request_data['command'],
                                params=request_data['params']
                            )
                            status_code = 200 if response_data.get('success', False) else 500
                        else:
                            response_data = {'success': False, 'error': 'Bash desktop controller not available'}
                            status_code = 500
                    else:
                        # Use pyautogui desktop controller (default)
                        desktop_controller = self.device._get_controller('desktop')
                        if desktop_controller:
                            response_data = desktop_controller.execute_command(
                                command=request_data['command'],
                                params=request_data['params']
                            )
                            status_code = 200 if response_data.get('success', False) else 500
                        else:
                            response_data = {'success': False, 'error': 'Desktop controller not available'}
                            status_code = 500
                            
                else:
                    # Use remote controller (default for remote actions)
                    remote_controller = self.device._get_controller('remote')
                    if remote_controller:
                        response_data = remote_controller.execute_command(
                            command=request_data['command'],
                            params=request_data['params']
                        )
                        # Remote controller returns boolean, convert to proper response format
                        if isinstance(response_data, bool):
                            response_data = {'success': response_data}
                        status_code = 200 if response_data.get('success', False) else 500
                    else:
                        response_data = {'success': False, 'error': 'Remote controller not available'}
                        status_code = 500
                
                iteration_execution_time = int((time.time() - iteration_start_time) * 1000)
                iteration_success = status_code == 200 and response_data.get('success', False)
                
                total_execution_time += iteration_execution_time
                
                # Log detailed results including error information
                if iterator_count > 1:
                    if iteration_success:
                        print(f"[@lib:action_executor:_execute_single_action] Action {action_number} iteration {iteration + 1}/{iterator_count} result: success={iteration_success}, time={iteration_execution_time}ms")
                    else:
                        error_msg = response_data.get('error', 'Unknown error')
                        print(f"[@lib:action_executor:_execute_single_action] Action {action_number} iteration {iteration + 1}/{iterator_count} result: success={iteration_success}, time={iteration_execution_time}ms, error: {error_msg}")
                        print(f"[@lib:action_executor:_execute_single_action] Full response data: {response_data}")
                else:
                    if iteration_success:
                        print(f"[@lib:action_executor:_execute_single_action] Action {action_number} result: success={iteration_success}, time={iteration_execution_time}ms")
                    else:
                        error_msg = response_data.get('error', 'Unknown error')
                        print(f"[@lib:action_executor:_execute_single_action] Action {action_number} result: success={iteration_success}, time={iteration_execution_time}ms, error: {error_msg}")
                        print(f"[@lib:action_executor:_execute_single_action] Full response data: {response_data}")
                
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
                    wait_time = self._parse_wait_time(params.get('wait_time', 0))
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
        wait_time = self._parse_wait_time(params.get('wait_time', 0))
        if all_iterations_successful and wait_time > 0:
            wait_seconds = wait_time / 1000.0
            current_time = time.strftime("%H:%M:%S", time.localtime())
            print(f"[@lib:action_executor:_execute_single_action] [{current_time}] Waiting {wait_time}ms after successful {action.get('command')} execution")
            time.sleep(wait_seconds)
            end_time = time.strftime("%H:%M:%S", time.localtime())
            print(f"[@lib:action_executor:_execute_single_action] [{end_time}] Wait completed after {action.get('command')}")
        
        # Store the actual completion timestamp (after all iterations and waits)
        action_completion_timestamp = time.time()
        
        # Record execution to database (summary of all iterations)
        self._record_execution_to_database(
            success=all_iterations_successful,
            execution_time_ms=total_execution_time,
            message=f"{action.get('command')} ({len(iteration_results)}/{iterator_count} iterations)" if iterator_count > 1 else f"{action.get('command')}",
            error_details={'iterations': iteration_results} if not all_iterations_successful else None,
            team_id=team_id
        )
        
        # Update navigation context with last action executed and precise completion timestamp
        # This provides accurate timing for post-processing analysis
        nav_context = self.device.navigation_context
        nav_context['last_action_executed'] = action.get('command')
        nav_context['last_action_timestamp'] = action_completion_timestamp
        
        # Return standardized result (same format as API)
        result_message = f"{action.get('command')}"
        if iterator_count > 1:
            successful_iterations = len([r for r in iteration_results if r['success']])
            result_message += f" ({successful_iterations}/{iterator_count} iterations)"
        
        # ALWAYS capture screenshot - success OR failure
        screenshot_path = ""
        try:
            # Use capture_and_upload_screenshot for consistent naming (same as NavigationExecutor)
            if context:
                from backend_host.src.lib.utils.report_utils import capture_and_upload_screenshot
                # Create meaningful step name with command and action number
                step_name = f"action_{action_number}_{action.get('command', 'unknown')}"
                screenshot_result = capture_and_upload_screenshot(self.device, step_name, "action")
                screenshot_path = screenshot_result.get('screenshot_path', '')
                
                if screenshot_path:
                    self.action_screenshots.append(screenshot_path)
                    print(f"[@action_executor] Screenshot captured: {screenshot_path}")
                    context.add_screenshot(screenshot_path)
                    print(f"[@action_executor] Screenshot added to context: {step_name}")
            else:
                # Fallback to direct AV controller call if no context
                screenshot_path = self.av_controller.take_screenshot()
                if screenshot_path:
                    self.action_screenshots.append(screenshot_path)
                    print(f"[@action_executor] Screenshot captured: {screenshot_path}")
        except Exception as e:
            print(f"[@action_executor] Screenshot failed: {e}")
        
        return {
            'success': all_iterations_successful,
            'message': result_message,
            'error': None if all_iterations_successful else f"Failed after {len(iteration_results)} iteration(s)",
            'resultType': 'PASS' if all_iterations_successful else 'FAIL',
            'execution_time_ms': total_execution_time,
            'action_category': action_category,
            'screenshot_path': screenshot_path,  # Always present
            'iterations': iteration_results if iterator_count > 1 else None
        }
    
    def _detect_action_type_from_device(self, command: str) -> str:
        """Detect action_type by checking which device controller has the command"""
        try:
            # Check each controller type in priority order
            for controller_type in ['remote', 'web', 'desktop', 'av', 'power']:
                try:
                    # Direct controller access from device instance
                    controller = self.device._get_controller(controller_type)
                    if controller and hasattr(controller, 'get_available_actions'):
                        actions = controller.get_available_actions()
                        if self._command_exists_in_actions(command, actions):
                            return controller_type.replace('desktop_', 'desktop')
                except:
                    continue
            
            # Check verification controllers
            for v_type in ['image', 'text', 'adb', 'appium', 'video', 'audio']:
                try:
                    # Direct controller access from device instance
                    controller = self.device._get_controller(f'verification_{v_type}')
                    if controller and hasattr(controller, 'get_available_verifications'):
                        verifications = controller.get_available_verifications()
                        if self._command_exists_in_actions(command, verifications):
                            return f'verification_{v_type}'
                except:
                    continue
            
            return 'remote'  # Default fallback
        except:
            return 'remote'  # Safe fallback
    
    def _command_exists_in_actions(self, command: str, actions) -> bool:
        """Check if command exists in controller actions"""
        if isinstance(actions, dict):
            for action_list in actions.values():
                if isinstance(action_list, list):
                    for action in action_list:
                        if action.get('command') == command:
                            return True
        elif isinstance(actions, list):
            for action in actions:
                if action.get('command') == command:
                    return True
        return False


    def _record_execution_to_database(self, success: bool, execution_time_ms: int, message: str, error_details: Optional[Dict] = None, team_id: str = None):
        """Record single execution directly to database"""
        try:
            # Get script context from device navigation_context - single source of truth
            nav_context = self.device.navigation_context
            script_result_id = nav_context.get('script_id')
            script_context = nav_context.get('script_context', 'direct')
            
            tree_id = nav_context['current_tree_id']
            record_edge_execution(
                team_id=team_id,
                tree_id=tree_id,
                edge_id=self.edge_id,
                host_name=self.host_name,
                device_model=self.device_model,
                success=success,
                execution_time_ms=execution_time_ms,
                message=message,
                error_details=error_details,
                script_result_id=script_result_id,
                script_context=script_context,
                action_set_id=self.action_set_id
            )
            
        except Exception as e:
            print(f"[@lib:action_executor:_record_execution_to_database] Database recording error: {e}")
    
    
    def _record_edge_execution(self, success: bool, execution_time_ms: int, error_details: Optional[str] = None, team_id: str = None):
        """Record edge execution to database (same as old system)"""
        try:
            # Get tree_id from ActionExecutor attributes first (for edge recording), 
            # then fall back to device navigation context (for full navigation)
            tree_id = getattr(self, 'tree_id', None)
            print(f"[@action_executor:_record_edge_execution] DEBUG: self.tree_id = {tree_id}")
            print(f"[@action_executor:_record_edge_execution] DEBUG: hasattr(self, 'tree_id') = {hasattr(self, 'tree_id')}")
            print(f"[@action_executor:_record_edge_execution] DEBUG: ActionExecutor attributes: {[attr for attr in dir(self) if not attr.startswith('_')]}")
            
            if tree_id is None:
                nav_context = self.device.navigation_context
                tree_id = nav_context['current_tree_id']
                print(f"[@action_executor:_record_edge_execution] DEBUG: Fallback to device nav_context tree_id = {tree_id}")
            
            # DEBUG: Log the values being recorded
            print(f"[@action_executor:_record_edge_execution] DEBUG Recording:")
            print(f"  - edge_id: {self.edge_id}")
            print(f"  - action_set_id: {self.action_set_id}")
            print(f"  - tree_id: {tree_id}")
            print(f"  - team_id: {team_id}")
            print(f"  - success: {success}")
            print(f"  - execution_time_ms: {execution_time_ms}")
            
            result = record_edge_execution(
                team_id=team_id,
                tree_id=tree_id,
                edge_id=self.edge_id,
                host_name=self.host_name,
                device_model=self.device_model,
                success=success,
                execution_time_ms=execution_time_ms,
                message='Navigation actions completed' if success else 'Navigation actions failed',
                error_details=error_details,
                action_set_id=self.action_set_id
            )
            
            if result:
                print(f"[@action_executor] ✅ Edge execution recorded: {result}")
            else:
                print(f"[@action_executor] ❌ Edge execution recording failed")
                
        except Exception as e:
            print(f"[@action_executor] ❌ Edge execution recording error: {e}") 