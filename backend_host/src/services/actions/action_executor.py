"""
Standardized Action Executor

This module provides a standardized way to execute actions that can be used by:
- Python code directly (navigation execution, scripts, etc.)
- API endpoints (maintaining consistency)
- Frontend hooks (via API calls)

The core logic is the same as /server/action/executeBatch but available as a reusable class.
"""

import time
import threading
import uuid
import logging
from typing import Dict, List, Optional, Any
from shared.src.lib.database.execution_results_db import record_edge_execution

# Get capture monitor logger for frame JSON operations
logger = logging.getLogger('capture_monitor')


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
        self.device_name = device.device_name
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
        
        # Async execution tracking (for action polling)
        self._executions: Dict[str, Dict[str, Any]] = {}  # execution_id -> execution state
        self._lock = threading.Lock()
    
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
    
    async def execute_actions(self, 
                       actions: List[Dict[str, Any]], 
                       retry_actions: Optional[List[Dict[str, Any]]] = None,
                       failure_actions: Optional[List[Dict[str, Any]]] = None,
                       team_id: str = None,
                       context = None) -> Dict[str, Any]:
        """
        Execute batch of actions with retry logic (PURE - no log capture)
        
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
        
        # Clear screenshots from previous step - ActionExecutor is reused across navigation steps
        self.action_screenshots = []
        
        # Validate inputs
        if not actions:
            return {
                'success': True,
                'message': 'No actions to execute',
                'results': [],
                'passed_count': 0,
                'total_count': 0,
                'main_actions_succeeded': True
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
                'total_count': 0,
                'main_actions_succeeded': False
            }
        
        results = []
        passed_count = 0
        execution_order = 1
        
        # Execute main actions - stop on first failure
        main_actions_failed = False
        
        # Capture "before action" screenshot BEFORE executing last action (for KPI report)
        # Store separately - DON'T add to action_screenshots (which is used for validation report counting)
        before_action_screenshot = ""
        if valid_actions:
            from shared.src.lib.utils.device_utils import capture_screenshot
            before_action_screenshot = capture_screenshot(self.device, context=None) or ""
            if before_action_screenshot:
                # Store in separate variable for KPI use - not in action_screenshots list
                print(f"[@lib:action_executor:execute_actions] 📸 Captured before-action screenshot (for KPI, not for validation report)")
        
        for i, action in enumerate(valid_actions):
            result = await self._execute_single_action(action, execution_order, i+1, 'main', team_id, context)
            results.append(result)
            
            if result.get('success'):
                passed_count += 1
            else:
                # Check if action has continue_on_fail flag
                continue_on_fail = action.get('continue_on_fail', False)
                
                if continue_on_fail:
                    # Action failed but continue_on_fail is set - continue execution
                    print(f"[@lib:action_executor:execute_actions] ⚠️  Main action {i+1} failed but continue_on_fail=True, continuing...")
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
                result = await self._execute_single_action(retry_action, execution_order, i+1, 'retry', team_id, context)
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
                result = await self._execute_single_action(failure_action, execution_order, i+1, 'failure', team_id, context)
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
        
        # Individual action recording is handled in _execute_single_action()
        # No batch-level recording needed
        
        # ✅ Aggregate output_data from ALL actions (including failed ones for debugging)
        # For single action: use that action's output_data
        # For multiple actions: combine all output_data (later actions can override earlier ones)
        # Even failed actions can return valuable debug data (e.g., raw extracted text)
        aggregated_output_data = {}
        for result in results:
            if result.get('output_data'):
                aggregated_output_data.update(result['output_data'])
        
        return {
            'success': overall_success,
            'total_count': len(valid_actions),
            'passed_count': passed_count,
            'failed_count': len(valid_actions) - passed_count,
            'results': results,
            'action_screenshots': self.action_screenshots,  # Only actual action screenshots (for validation report)
            'before_action_screenshot': before_action_screenshot,  # Separate for KPI use only
            'message': f'Batch action execution completed: {passed_count}/{len(valid_actions)} passed',
            'error': error_message,
            'execution_time_ms': total_execution_time,
            'main_actions_succeeded': not main_actions_failed,
            'output_data': aggregated_output_data  # ✅ Include aggregated output_data at top level
        }
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of async action execution (called by route polling).
        
        Returns:
            {
                'success': bool,
                'execution_id': str,
                'status': 'running' | 'completed' | 'error',
                'result': dict (if completed),
                'error': str (if error),
                'progress': int,
                'message': str
            }
        """
        with self._lock:
            if execution_id not in self._executions:
                return {
                    'success': False,
                    'error': f'Execution {execution_id} not found'
                }
            
            execution = self._executions[execution_id].copy()
        
        return {
            'success': True,
            'execution_id': execution['execution_id'],
            'status': execution['status'],
            'result': execution.get('result'),
            'error': execution.get('error'),
            'progress': execution.get('progress', 0),
            'message': execution.get('message', ''),
            'elapsed_time_ms': int((time.time() - execution['start_time']) * 1000)
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
    
    async def _execute_single_action(self, action: Dict[str, Any], execution_order: int, action_number: int, action_category: str, team_id: str = None, context = None) -> Dict[str, Any]:
        """Execute a single action and return standardized result"""
        
        # Get iterator count (default to 1 if not specified)
        # Only allow iterations for non-verification actions
        action_type = action.get('action_type', 'remote')
        if action_type == 'verification':
            iterator_count = 1  # Force single execution for verifications
        else:
            iterator_count = self._parse_iterator_count(action.get('iterator', 1))
        
        # Consolidated action execution log with clear visibility
        command = action.get('command', 'unknown')
        params_summary = action.get('params', {})
        
        # Build readable action description
        action_desc = f"{action_category.upper()} ACTION {action_number}: {command}"
        
        # Add key params to description for context
        if 'url' in params_summary:
            action_desc += f"(url={params_summary.get('url')})"
        elif 'element_id' in params_summary:
            action_desc += f"(element_id={params_summary.get('element_id')})"
        elif 'selector' in params_summary:
            action_desc += f"(selector={params_summary.get('selector')})"
        
        if iterator_count > 1:
            action_desc += f" [×{iterator_count}]"
        
        print(f"")  # Blank line for visibility
        print(f"[@lib:action_executor] ▶️  {action_desc}")
        print(f"[@lib:action_executor] " + "─" * 60)
        
        # Track results for all iterations
        all_iterations_successful = True
        total_execution_time = 0
        iteration_results = []
        action_output_data = {}  # ✅ Capture output_data from last successful iteration
        
        for iteration in range(iterator_count):
            iteration_start_time = time.time()
            
            try:
                # Use action params directly - wait_time is already in params from database
                raw_params = action.get('params', {})
                
                # ✅ CRITICAL: Clean params - extract actual values from typed schema objects
                # Frontend may send params as {default: X, type: Y, required: Z} instead of just X
                # This ensures both single-block execute and full test-case execute work identically
                params = {}
                for key, value in raw_params.items():
                    # If value is a typed param schema object (has 'default' field), extract the default
                    if isinstance(value, dict) and 'default' in value and 'type' in value:
                        params[key] = value['default']
                    else:
                        # Already a simple value
                        params[key] = value
                
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
                elif action_type == 'power':
                    # Route to power endpoint
                    endpoint = '/host/power/executeCommand'
                    request_data = {
                        'command': action.get('command'),
                        'params': params,
                        'device_id': self.device_id
                    }
                elif action_type == 'standard_block':
                    # Execute standard block directly via block registry (no HTTP)
                    from backend_host.src.builder import execute_block
                    
                    if iteration == 0:  # Only log once
                        print(f"[@lib:action_executor:_execute_single_action] Executing standard block: {action.get('command')}")
                    
                    # Execute block with context
                    response_data = execute_block(
                        command=action.get('command'),
                        params=params,
                        context=context
                    )
                    
                    # Standard blocks return response_data directly (no HTTP call needed)
                    endpoint = None
                    status_code = 200 if response_data.get('success', False) else 500
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
                        response_data = await web_controller.execute_command(
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
                    
                    # Get all desktop controllers and find the right one by implementation
                    desktop_controllers = self.device.get_controllers('desktop')
                    
                    if command in bash_commands:
                        # Use bash desktop controller - find it by desktop_type attribute
                        bash_controller = next((c for c in desktop_controllers if hasattr(c, 'desktop_type') and c.desktop_type == 'bash'), None)
                        if bash_controller:
                            response_data = bash_controller.execute_command(
                                command=request_data['command'],
                                params=request_data['params']
                            )
                            status_code = 200 if response_data.get('success', False) else 500
                        else:
                            response_data = {'success': False, 'error': 'Bash desktop controller not available'}
                            status_code = 500
                    else:
                        # Use pyautogui desktop controller (default) - find it by desktop_type attribute
                        pyautogui_controller = next((c for c in desktop_controllers if hasattr(c, 'desktop_type') and c.desktop_type == 'pyautogui'), None)
                        if pyautogui_controller:
                            response_data = pyautogui_controller.execute_command(
                                command=request_data['command'],
                                params=request_data['params']
                            )
                            status_code = 200 if response_data.get('success', False) else 500
                        else:
                            response_data = {'success': False, 'error': 'PyAutoGUI desktop controller not available'}
                            status_code = 500
                            
                elif action_type == 'power':
                    # Use power controller directly
                    power_controller = self.device._get_controller('power')
                    if power_controller:
                        response_data = power_controller.execute_command(
                            command=request_data['command'],
                            params=request_data['params']
                        )
                        # Power controller returns boolean, convert to proper response format
                        if isinstance(response_data, bool):
                            response_data = {'success': response_data}
                        status_code = 200 if response_data.get('success', False) else 500
                    else:
                        response_data = {'success': False, 'error': 'Power controller not available'}
                        status_code = 500
                elif action_type == 'verification':
                    # Use verification executor directly
                    verification_type = action.get('verification_type', 'text')
                    
                    # Get verification controller
                    verification_executor = self.device.verification_executor
                    if verification_executor:
                        # Execute single verification
                        verification_config = {
                            'command': action.get('command'),
                            'params': params,
                            'verification_type': verification_type
                        }
                        
                        # Get userinterface name from device for reference resolution
                        userinterface_name = self.device.device_model  # Use device model as fallback
                        if hasattr(self.device, 'get_userinterface_name'):
                            userinterface_name = self.device.get_userinterface_name()
                        
                        # Execute verification using verification_executor's single verification method
                        # IMPORTANT: Pass context to enable metadata storage for getMenuInfo
                        # NOTE: Verification executor will NOT capture duplicate screenshots if screenshots are disabled
                        result = await verification_executor._execute_single_verification(
                            verification=verification_config,
                            userinterface_name=userinterface_name,
                            image_source_url=None,
                            context=context,  # Pass context for metadata storage (getMenuInfo needs this)
                            team_id=team_id
                        )
                        
                        # Convert verification result to action response format
                        response_data = {
                            'success': result.get('success', False),
                            'message': result.get('message', ''),
                            'error': result.get('error'),
                            'verification_type': verification_type,
                            'output_data': result.get('output_data', {})  # ✅ Include output_data from verification
                        }
                        status_code = 200 if result.get('success', False) else 500
                    else:
                        response_data = {'success': False, 'error': 'Verification executor not available'}
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
                
                # Log detailed results including error information with clear visibility
                if iterator_count > 1:
                    if iteration_success:
                        print(f"[@lib:action_executor] ✅ {command} iteration {iteration + 1}/{iterator_count}: SUCCESS ({iteration_execution_time}ms)")
                    else:
                        error_msg = response_data.get('error', 'Unknown error')
                        warning = response_data.get('warning', '')
                        print(f"[@lib:action_executor] ❌ {command} iteration {iteration + 1}/{iterator_count}: FAILED ({iteration_execution_time}ms)")
                        print(f"[@lib:action_executor]    Error: {error_msg}")
                        if warning:
                            print(f"[@lib:action_executor]    Warning: {warning}")
                        print(f"[@lib:action_executor]    Full response: {response_data}")
                else:
                    if iteration_success:
                        print(f"[@lib:action_executor] ✅ {command}: SUCCESS ({iteration_execution_time}ms)")
                    else:
                        error_msg = response_data.get('error', 'Unknown error')
                        warning = response_data.get('warning', '')
                        print(f"[@lib:action_executor] ❌ {command}: FAILED ({iteration_execution_time}ms)")
                        print(f"[@lib:action_executor]    Error: {error_msg}")
                        if warning:
                            print(f"[@lib:action_executor]    Warning: {warning}")
                        # Check if it's a timeout error
                        if 'TimeoutError' in error_msg or 'Timeout' in error_msg or 'timeout' in error_msg.lower():
                            print(f"[@lib:action_executor]    ⏱️  TIMEOUT: Action took longer than expected")
                        print(f"[@lib:action_executor]    Full response: {response_data}")
                
                # Track iteration results
                # Provide default message if controller doesn't return one
                if iteration_success:
                    message = response_data.get('message') or 'Success'
                else:
                    message = response_data.get('error') or 'Failed'
                
                iteration_results.append({
                    'iteration': iteration + 1,
                    'success': iteration_success,
                    'execution_time_ms': iteration_execution_time,
                    'message': message
                })
                
                # ✅ Capture output_data from this iteration (will be overwritten by next iteration if multiple)
                # This ensures we always have the last successful iteration's output_data
                if 'output_data' in response_data:
                    action_output_data = response_data['output_data']
                    print(f"[@lib:action_executor:_execute_single_action] ✅ Captured output_data with keys: {list(action_output_data.keys())}")
                
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
        
        # ✅ Store action timestamp IMMEDIATELY after action executes (before wait)
        # This ensures last_action.json is written before zapping detection happens during wait
        action_completion_timestamp = time.time()
        
        # ✅ Write action metadata BEFORE wait so capture_monitor can read it during zapping
        print(f"[@lib:action_executor:_execute_single_action] 🎬 Writing to frame JSON and last_action.json...")
        from backend_host.src.lib.utils.frame_metadata_utils import write_action_to_frame_json
        try:
            write_action_to_frame_json(self.device, action, action_completion_timestamp)
            print(f"[@lib:action_executor:_execute_single_action] ✅ write_action_to_frame_json completed")
        except Exception as e:
            print(f"[@lib:action_executor:_execute_single_action] ❌ write_action_to_frame_json failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait after successful action execution (once per action, after all iterations)
        wait_time = self._parse_wait_time(params.get('wait_time', 0))
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
        
        # Capture screenshot (no upload)
        from shared.src.lib.utils.device_utils import capture_screenshot
        screenshot_path = capture_screenshot(self.device, context) or ""
        
        # Add screenshot to collection for report
        if screenshot_path:
            self.action_screenshots.append(screenshot_path)
        
        # Build detailed action info for KPI report
        action_details = {
            'command': action.get('command'),
            'action_type': action_type,
            'params': params,
            'iterator_count': iterator_count,
            'execution_time_ms': total_execution_time,
            'wait_time_ms': wait_time,
            'total_time_ms': total_execution_time + wait_time
        }
        
        return {
            'success': all_iterations_successful,
            'message': result_message,
            'error': None if all_iterations_successful else f"Failed after {len(iteration_results)} iteration(s)",
            'resultType': 'PASS' if all_iterations_successful else 'FAIL',
            'execution_time_ms': total_execution_time,
            'action_category': action_category,
            'screenshot_path': screenshot_path,  # Always present
            'action_timestamp': action_completion_timestamp,  # ✅ NEW: Timestamp for zapping detection sync
            'iterations': iteration_results if iterator_count > 1 else None,
            'action_details': action_details,  # ✅ NEW: Detailed action info for KPI report
            'output_data': action_output_data  # ✅ Use captured output_data from iteration loop
        }
    
    def _detect_action_type_from_device(self, command: str) -> str:
        """Detect action_type by checking which device controller has the command"""
        try:
            # Check verification controllers FIRST (higher priority than remote)
            for v_type in ['image', 'text', 'adb', 'appium', 'video', 'audio']:
                try:
                    # Direct controller access from device instance
                    controller = self.device._get_controller(f'verification_{v_type}')
                    if controller and hasattr(controller, 'get_available_verifications'):
                        verifications = controller.get_available_verifications()
                        if self._command_exists_in_actions(command, verifications):
                            # Return 'verification' (not 'verification_text') for routing
                            return 'verification'
                except:
                    continue
            
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
            
            # Skip recording if explicitly requested (frontend testing from useEdge/useNode hooks)
            if nav_context.get('skip_db_recording'):
                print(f"[@lib:action_executor:_record_execution_to_database] Skipping database recording - frontend testing (skip_db_recording=true)")
                return
            
            # Get tree_id from ActionExecutor attributes first (for edge recording), 
            # then fall back to device navigation context (for full navigation)
            tree_id = getattr(self, 'tree_id', None)
            if not tree_id:  # Handles None and empty string
                tree_id = nav_context.get('current_tree_id')
            
            # Skip recording if tree_id is not valid (standalone testing from edge edit dialog)
            if not tree_id:
                print(f"[@lib:action_executor:_record_execution_to_database] Skipping database recording - missing tree_id (standalone test)")
                return
            
            record_edge_execution(
                team_id=team_id,
                tree_id=tree_id,
                edge_id=self.edge_id,
                host_name=self.host_name,
                device_model=self.device_model,
                device_name=self.device_name,
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
    
    