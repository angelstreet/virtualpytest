"""
AI Executor

Unified AI executor with integrated plan generation and execution capabilities.
Uses device's existing executors instead of creating new instances.
"""

import time
import uuid
import threading
import re
import json
from typing import Dict, List, Optional, Any

from .ai_types import ExecutionResult
from shared.src.lib.utils.ai_utils import call_text_ai, AI_CONFIG


class AIExecutor:
    """
    Main AI executor that handles all AI operations per device:
    - Integrated plan generation capabilities
    - Plan execution using device's existing executors
    - Execution status tracking
    - Position tracking delegated to NavigationExecutor
    
    CRITICAL: Do not create new instances directly! Use device.ai_executor instead.
    Each device has a singleton AIExecutor that preserves execution state and caches.
    """
    
    @classmethod
    def get_for_device(cls, device):
        """
        Factory method to get the device's existing AIExecutor.
        
        RECOMMENDED: Use device.ai_executor directly instead of this method.
        
        Args:
            device: Device instance
            
        Returns:
            The device's existing AIExecutor instance
            
        Raises:
            ValueError: If device doesn't have an ai_executor
        """
        if not hasattr(device, 'ai_executor') or not device.ai_executor:
            raise ValueError(f"Device {device.device_id} does not have an AIExecutor. "
                           "AIExecutors are created during device initialization.")
        return device.ai_executor
    
    # Class-level storage for execution tracking across all devices
    _executions = {}  # {execution_id: execution_data}
    
    def __init__(self, device, _from_device_init: bool = False):
        """Initialize AI executor for a specific device"""
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
            print(f"⚠️ [AIExecutor] WARNING: Creating new AIExecutor instance for device {device.device_id}")
            print(f"⚠️ [AIExecutor] This may cause state loss! Use device.ai_executor instead.")
            print(f"⚠️ [AIExecutor] Call stack:")
            for line in traceback.format_stack()[-3:-1]:  # Show last 2 stack frames
                print(f"⚠️ [AIExecutor]   {line.strip()}")
        
        # Store instances directly
        self.device = device
        self.host_name = device.host_name
        self.device_id = device.device_id
        self.device_model = device.device_model
        
        # Initialize integrated AI plan generation capabilities
        self._context_cache = {}
        self._action_cache = {}
        self._verification_cache = {}
        self._navigation_cache = {}
        self._cache_ttl = 86400  # 24 hours
        
        # Initialize AI plan cache (loaded on demand)
        self.plan_cache = None
        
        # Initialized for device: {self.device_id}, model: {self.device_model}
    
    def execute_prompt(self, 
                      prompt: str, 
                      userinterface_name: str,
                      team_id: str,
                      current_node_id: Optional[str] = None,
                      async_execution: bool = True,
                      use_cache: bool = False,
                      debug_mode: bool = False) -> Dict[str, Any]:
        """
        Execute AI prompt with optional cache control
        
        Args:
            prompt: User prompt
            userinterface_name: Interface name
            team_id: Team ID
            current_node_id: Current navigation position
            async_execution: Whether to execute asynchronously
            use_cache: True to use/store cache, False for fresh generation (default: False)
            debug_mode: True prevents storage even if successful (default: False)
        
        Returns:
        - For async: {'success': True, 'execution_id': str}
        - For sync: {'success': bool, 'execution_id': str, 'result': dict}
        """
        start_time = time.time()
        execution_id = str(uuid.uuid4())
        
        # CRITICAL: Start execution tracking BEFORE generating plan
        # This ensures frontend can query status even if plan generation fails
        dummy_plan = {'id': execution_id, 'prompt': prompt, 'analysis': 'Generating plan...', 'feasible': True, 'plan': []}
        self._start_execution_tracking(execution_id, dummy_plan)
        
        try:
            # Get current position if not provided
            if current_node_id is None:
                position = self.device.navigation_executor.get_current_position()
                current_node_id = position.get('current_node_id')
            
            # Load context using device's existing executors
            context = self._load_context(userinterface_name, current_node_id, team_id)
            
            # Check cache first (only if use_cache=True)
            cached_plan = None
            if use_cache:
                # Load cache on demand
                if self.plan_cache is None:
                    from .ai_plan_cache import AIExecutorCache
                    self.plan_cache = AIExecutorCache()
                
                cached_plan = self.plan_cache.find_cached_plan(prompt, context, team_id)
                if cached_plan:
                    print(f"[@ai_executor] Using cached plan: {cached_plan['fingerprint']}")
                    plan_dict = cached_plan['plan']
                    
                    # Execute cached plan
                    if async_execution:
                        self._start_execution_tracking(execution_id, plan_dict)
                        threading.Thread(
                            target=self._execute_cached_plan_async, 
                            args=(execution_id, cached_plan, context, team_id)
                        ).start()
                        
                        return {
                            'success': True,
                            'execution_id': execution_id,
                            'message': 'Executing cached plan',
                            'cached': True,
                            'execution_time': time.time() - start_time
                        }
                    else:
                        result = self._execute_cached_plan_sync(cached_plan, context, team_id)
                        return {
                            'success': result.success,
                            'execution_id': execution_id,
                            'message': 'Cached plan executed',
                            'cached': True,
                            'result': result,
                            'execution_time': time.time() - start_time
                        }
                else:
                    # use_cache=True but no valid cache found - FAIL FAST (no AI generation)
                    print(f"[@ai_executor] ❌ use_cache=True but no valid cached plan found for prompt: '{prompt}'")
                    return {
                        'success': False,
                        'execution_id': execution_id,
                        'error': 'No cached plan available. Uncheck "Use Cache" to generate a new plan, or execute this task once to populate the cache.',
                        'cache_miss': True,
                        'execution_time': time.time() - start_time
                    }
            
            # Generate new plan (only if use_cache=False)
            print(f"[@ai_executor] Generating new plan (cache disabled)")
            plan_dict = self.generate_plan(prompt, context, current_node_id)
            
            if not plan_dict.get('feasible', True):
                return {
                    'success': False,
                    'execution_id': execution_id,
                    'error': 'Task not feasible',
                    'analysis': plan_dict.get('analysis', ''),
                    'execution_time': time.time() - start_time
                }
            
            # Execute plan
            if async_execution:
                # Start async execution
                self._start_execution_tracking(execution_id, plan_dict)
                threading.Thread(
                    target=self._execute_new_plan_async, 
                    args=(execution_id, plan_dict, context, prompt, use_cache, debug_mode, team_id)
                ).start()
                
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'message': 'Execution started',
                    'plan_steps': len(plan_dict.get('steps', [])),
                    'cached': False,
                    'execution_time': time.time() - start_time
                }
            else:
                # Synchronous execution
                self._start_execution_tracking(execution_id, plan_dict)
                result = self._execute_plan_sync(plan_dict, context)
                self._complete_execution_tracking(execution_id, result)
                
                # Store plan if successful and conditions met
                self._store_plan_if_conditions_met(prompt, context, plan_dict, result, use_cache, debug_mode, team_id)
                
                return {
                    'success': result.success,
                    'execution_id': execution_id,
                    'message': 'Execution completed' if result.success else result.error,
                    'steps_executed': len([r for r in result.step_results if r.get('success')]),
                    'total_steps': len(result.step_results),
                    'cached': False,
                    'execution_time': time.time() - start_time,
                    'result': result
                }
                
        except Exception as e:
            # Update plan in tracking to show error instead of "Generating plan..."
            if execution_id in self._executions:
                error_plan = {
                    'id': execution_id,
                    'prompt': prompt,
                    'analysis': f'Goal: {prompt}\nThinking: Plan generation failed - {str(e)}',
                    'feasible': False,
                    'plan': []
                }
                self._executions[execution_id]['plan'] = error_plan
            
            # Mark execution as failed so frontend stops polling
            error_result = type('ErrorResult', (), {
                'success': False,
                'error': f'AI execution error: {str(e)}',
                'step_results': [],
                'total_time_ms': int((time.time() - start_time) * 1000)
            })()
            self._complete_execution_tracking(execution_id, error_result)
            
            return {
                'success': False,
                'execution_id': execution_id,
                'error': f'AI execution error: {str(e)}',
                'execution_time': time.time() - start_time
            }
    
    def execute_testcase(self, test_case_id: str, team_id: str) -> Dict[str, Any]:
        """Execute stored test case"""
        try:
            from shared.src.lib.supabase.testcase_db import get_test_case
            
            test_case = get_test_case(test_case_id, team_id)
            if not test_case:
                return {
                    'success': False,
                    'error': f'Test case {test_case_id} not found'
                }
            
            # Get stored plan
            stored_plan = test_case.get('ai_plan')
            if not stored_plan:
                return {
                    'success': False,
                    'error': 'Test case missing ai_plan'
                }
            
            # Execute stored plan synchronously
            execution_id = str(uuid.uuid4())
            self._start_execution_tracking(execution_id, stored_plan)
            
            # Load minimal context for execution
            userinterface_name = stored_plan.get('userinterface_name', 'horizon_android_mobile')
            current_node_id = stored_plan.get('current_node_id')
            context = self._load_context(userinterface_name, current_node_id, team_id)
            
            result = self._execute_plan_sync(stored_plan, context)
            self._complete_execution_tracking(execution_id, result)
            
            return {
                'success': result.success,
                'execution_id': execution_id,
                'message': 'Test case executed' if result.success else result.error,
                'steps_executed': len([r for r in result.step_results if r.get('success')]),
                'total_steps': len(result.step_results)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Test case execution error: {str(e)}'
            }
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status - simplified tracking"""
        print(f"[@ai_executor] Looking for execution {execution_id}, available executions: {list(self._executions.keys())}")
        
        if execution_id not in self._executions:
            print(f"[@ai_executor] Execution {execution_id} not found in tracking")
            return {
                'success': False,
                'error': f'Execution {execution_id} not found',
                'is_executing': False  # Explicitly set to prevent frontend confusion
            }
        
        execution = self._executions[execution_id]
        plan_steps = execution['plan'].get('steps', [])
        completed_steps = len([r for r in execution['step_results'] if r.get('success')])
        
        # Convert step_results to execution_log format for frontend compatibility
        execution_log = []
        for i, step_result in enumerate(execution['step_results']):
            if step_result.get('success'):
                execution_log.append({
                    'action_type': 'step_success',
                    'data': {
                        'step': step_result.get('step_id', i + 1),
                        'duration': step_result.get('execution_time_ms', 0) / 1000.0,
                        'message': step_result.get('message', '')
                    }
                })
            else:
                execution_log.append({
                    'action_type': 'step_failed',
                    'data': {
                        'step': step_result.get('step_id', i + 1),
                        'duration': step_result.get('execution_time_ms', 0) / 1000.0,
                        'error': step_result.get('message', 'Step failed')
                    }
                })
        
        # Add task completion entry if execution is finished
        if execution['status'] in ['completed', 'failed']:
            total_duration = (execution.get('end_time', time.time()) - execution['start_time'])
            if execution['status'] == 'completed':
                execution_log.append({
                    'action_type': 'task_completed',
                    'data': {
                        'duration': total_duration,
                        'message': 'Task completed successfully'
                    }
                })
            else:
                execution_log.append({
                    'action_type': 'task_failed',
                    'data': {
                        'duration': total_duration,
                        'message': 'Task failed'
                    }
                })

        return {
            'success': True,
            'execution_id': execution_id,
            'status': execution['status'],
            'current_step': execution['current_step'],
            'progress_percentage': (completed_steps / len(plan_steps)) * 100 if plan_steps else 0,
            'plan': execution['plan'],
            'step_results': execution['step_results'],
            'execution_log': execution_log,  # Add execution_log for frontend compatibility
            'is_executing': execution['status'] == 'executing',
            'execution_summary': {
                'total_steps': len(plan_steps),
                'completed_steps': completed_steps,
                'failed_steps': len([r for r in execution['step_results'] if not r.get('success')]),
                'start_time': execution['start_time'],
                'end_time': execution.get('end_time'),
                'total_duration': (execution.get('end_time', time.time()) - execution['start_time']) if execution['status'] in ['completed', 'failed'] else 0
            }
        }
    
    def get_device_position(self) -> Dict[str, Any]:
        """Get current device position from navigation executor"""
        return self.device.navigation_executor.get_current_position()
    
    def update_device_position(self, node_id: str, tree_id: str = None, node_label: str = None) -> Dict[str, Any]:
        """Update device position via navigation executor"""
        return self.device.navigation_executor.update_current_position(node_id, tree_id, node_label)
    
    # Private methods
    
    def _load_context(self, userinterface_name: str, current_node_id: str, team_id: str) -> Dict[str, Any]:
        """Load context using device's existing executors"""
        print(f"[@ai_executor] Loading context for device: {self.device_id}, model: {self.device_model}, interface: {userinterface_name}")
        
        # Use device's existing executors to load context
        action_context = self.device.action_executor.get_available_context(userinterface_name)
        verification_context = self.device.verification_executor.get_available_context(userinterface_name)
        navigation_context = self.device.navigation_executor.get_available_context(userinterface_name, team_id)
        
        return {
            'device_model': self.device_model,
            'userinterface_name': userinterface_name,
            'current_node_id': current_node_id,
            'team_id': team_id,
            'tree_id': navigation_context.get('tree_id'),
            'available_nodes': navigation_context.get('available_nodes', []),
            'available_actions': action_context.get('available_actions', []),
            'available_verifications': verification_context.get('available_verifications', [])
        }
    
    def _get_device_position(self, device_id: str) -> Dict[str, str]:
        """Get device position from navigation executor (deprecated - use get_device_position)"""
        position = self.device.navigation_executor.get_current_position()
        return {
            'node_id': position.get('current_node_id'),
            'node_label': position.get('current_node_label')
        }
    
    def _extract_target_from_prompt(self, prompt: str) -> Optional[str]:
        """Extract target node from prompt for optimization"""
        match = re.search(r'(?:go to|navigate to|goto)\s+(\w+)', prompt.lower())
        return match.group(1) if match else None
    
    def _start_execution_tracking(self, execution_id: str, plan_dict: Dict):
        """Start tracking execution"""
        plan_steps = plan_dict.get('steps', [])
        initial_step_msg = f"Starting execution with {len(plan_steps)} steps..." if plan_steps else "Starting execution..."
        
        self._executions[execution_id] = {
            'plan': plan_dict,
            'status': 'executing',
            'current_step': initial_step_msg,
            'step_results': [],
            'start_time': time.time()
        }
        print(f"[@ai_executor] Started tracking execution {execution_id} with {len(plan_steps)} steps")
        print(f"[@ai_executor] Total executions now tracked: {len(self._executions)}, keys: {list(self._executions.keys())}")
    
    def _complete_execution_tracking(self, execution_id: str, result: ExecutionResult):
        """Complete execution tracking"""
        if execution_id in self._executions:
            execution = self._executions[execution_id]
            execution['status'] = 'completed' if result.success else 'failed'
            execution['result'] = result
            execution['end_time'] = time.time()
            
            # Add completion log entry with error details if failed
            if not result.success:
                error_message = getattr(result, 'error', 'Unknown error')
                total_duration = execution['end_time'] - execution.get('start_time', execution['end_time'])
                
                error_log_entry = {
                    'timestamp': time.time(),
                    'log_type': 'execution',
                    'action_type': 'task_failed',
                    'data': {
                        'success': False,
                        'duration': total_duration,
                        'error': error_message,
                        'message': error_message
                    },
                    'value': {
                        'success': False,
                        'duration': total_duration,
                        'message': error_message
                    },
                    'description': f'Task failed: {error_message}'
                }
                
                if 'execution_log' not in execution:
                    execution['execution_log'] = []
                execution['execution_log'].append(error_log_entry)
            
            print(f"[@ai_executor] Completed execution {execution_id}: {'success' if result.success else 'failed'}")
    
    def _format_step_display(self, step_data: Dict) -> str:
        """
        Format step for display (same format as UI).
        Shows command format for navigation, description for others.
        """
        command = step_data.get('command', 'unknown')
        
        if command == 'execute_navigation':
            target_node = step_data.get('params', {}).get('target_node', 'unknown')
            return f"{command}({target_node})"
        else:
            # For non-navigation steps, use description or command
            return step_data.get('description', command)
    
    def _update_current_step_tracking(self, plan_id: str, step_number: int, step_description: str):
        """Update current step in real-time tracking"""
        for exec_id, exec_data in self._executions.items():
            if exec_data.get('plan', {}).get('id') == plan_id:
                exec_data['current_step'] = step_description
                print(f"[@ai_executor] Step {step_number} started for execution {exec_id}: {step_description}")
                break
    
    def _update_step_result_tracking(self, plan_id: str, step_number: int, step_result: Dict[str, Any], all_step_results: List[Dict[str, Any]]):
        """Update step result in real-time tracking"""
        for exec_id, exec_data in self._executions.items():
            if exec_data.get('plan', {}).get('id') == plan_id:
                exec_data['step_results'] = all_step_results
                success = step_result.get('success', False)
                status_msg = f"Step {step_number} {'completed' if success else 'failed'}"
                if not success and step_result.get('message'):
                    status_msg += f": {step_result.get('message')}"
                exec_data['current_step'] = status_msg
                print(f"[@ai_executor] Step {step_number} {'completed' if success else 'failed'} for execution {exec_id}")
                break
    
    def _execute_cached_plan_async(self, execution_id: str, cached_plan: Dict, context: Dict, team_id: str):
        """Execute cached plan asynchronously"""
        try:
            result = self._execute_cached_plan_sync(cached_plan, context, team_id)
            self._complete_execution_tracking(execution_id, result)
        except Exception as e:
            error_result = ExecutionResult(
                plan_id=cached_plan.get('plan', {}).get('id', 'unknown'),
                success=False,
                step_results=[],
                total_time_ms=0,
                error=str(e)
            )
            self._complete_execution_tracking(execution_id, error_result)
    
    def _execute_cached_plan_sync(self, cached_plan: Dict, context: Dict, team_id: str) -> ExecutionResult:
        """Execute cached plan synchronously and update metrics"""
        plan_dict = cached_plan['plan']
        result = self._execute_plan_sync(plan_dict, context)
        
        # Update cache metrics (load cache if needed)
        if self.plan_cache is None:
            from .ai_plan_cache import AIExecutorCache
            self.plan_cache = AIExecutorCache()
        
        self.plan_cache.update_plan_metrics(
            cached_plan['fingerprint'], 
            result.success, 
            result.total_time_ms, 
            team_id
        )
        
        return result
    
    def _execute_new_plan_async(self, execution_id: str, plan_dict: Dict, context: Dict, 
                              prompt: str, use_cache: bool, debug_mode: bool, team_id: str):
        """Execute new plan asynchronously with cache storage"""
        try:
            result = self._execute_plan_sync(plan_dict, context)
            self._complete_execution_tracking(execution_id, result)
            
            # Store plan if conditions met
            self._store_plan_if_conditions_met(prompt, context, plan_dict, result, use_cache, debug_mode, team_id)
                    
        except Exception as e:
            error_result = ExecutionResult(
                plan_id=plan_dict.get('id', 'unknown'),
                success=False,
                step_results=[],
                total_time_ms=0,
                error=str(e)
            )
            self._complete_execution_tracking(execution_id, error_result)
    
    def _store_plan_if_conditions_met(self, prompt: str, context: Dict, plan_dict: Dict, 
                                    result: ExecutionResult, use_cache: bool, debug_mode: bool, team_id: str):
        """Store plan only if all conditions are met"""
        should_store = (
            result.success and                    # Must be successful
            use_cache and                         # User allows caching
            not debug_mode and                    # Not in debug mode
            len(result.step_results) > 0 and      # Has actual steps
            all(r.get('success') for r in result.step_results)  # All steps succeeded
        )
        
        if should_store:
            # Load cache on demand for storage
            if self.plan_cache is None:
                from .ai_plan_cache import AIExecutorCache
                self.plan_cache = AIExecutorCache()
            
            success = self.plan_cache.store_successful_plan(prompt, context, plan_dict, result, team_id)
            if success:
                print("[@ai_executor] Stored successful plan in cache")
            else:
                print("[@ai_executor] Failed to store plan in cache")
        else:
            reasons = []
            if not result.success: reasons.append("execution failed")
            if not use_cache: reasons.append("caching disabled")
            if debug_mode: reasons.append("debug mode active")
            if not len(result.step_results): reasons.append("no steps executed")
            if not all(r.get('success') for r in result.step_results): reasons.append("some steps failed")
            print(f"[@ai_executor] NOT storing plan: {', '.join(reasons)}")
    
    def _execute_plan_sync(self, plan_dict: Dict, context: Dict) -> ExecutionResult:
        """Execute plan synchronously using device's existing executors"""
        start_time = time.time()
        step_results = []
        
        plan_steps = plan_dict.get('steps', [])
        for i, step_data in enumerate(plan_steps):
            step_number = step_data.get('step', i + 1)
            
            # Update current step in tracking BEFORE execution (use formatted display)
            formatted_step = self._format_step_display(step_data)
            self._update_current_step_tracking(plan_dict.get('id'), step_number, f"Executing step {step_number}: {formatted_step}")
            
            step_result = self._execute_step(step_data, context)
            step_results.append(step_result)
            
            # Handle step injection from reassessment
            if step_result.get('requires_step_injection') and step_result.get('updated_steps'):
                injected_steps = step_result.get('updated_steps', [])
                print(f"[@ai_executor] Injecting {len(injected_steps)} steps from reassessment")
                
                # Insert new steps after current position
                for j, injected_step in enumerate(injected_steps):
                    # Adjust step numbers to continue sequence
                    injected_step['step'] = step_number + j + 1
                    plan_steps.insert(i + j + 1, injected_step)
                
                print(f"[@ai_executor] Plan now has {len(plan_steps)} total steps")
            
            # Update tracking with step result
            self._update_step_result_tracking(plan_dict.get('id'), step_number, step_result, step_results)
            
            # Stop on first failure
            if not step_result.get('success'):
                break
        
        total_time = int((time.time() - start_time) * 1000)
        success = all(r.get('success', False) for r in step_results)
        
        return ExecutionResult(
            plan_id=plan_dict.get('id', 'unknown'),
            success=success,
            step_results=step_results,
            total_time_ms=total_time,
            error=None if success else "One or more steps failed"
        )
    
    def _execute_step(self, step_data: Dict, context: Dict) -> Dict[str, Any]:
        """Execute a single step by delegating to appropriate executor"""
        try:
            command = step_data.get('command')
            step_type = step_data.get('step_type') or self._determine_step_type(command)
            
            # Pure orchestration - delegate to appropriate executor
            if step_type == 'navigation':
                result = self._execute_navigation_step(step_data, context)
            elif step_type == 'navigation_reassessment':
                result = self._execute_navigation_reassessment_step(step_data, context)
            elif step_type == 'action':
                result = self._execute_action_step(step_data, context)
            elif step_type == 'verification':
                result = self._execute_verification_step(step_data, context)
            elif step_type == 'wait':
                result = self._execute_wait_step(step_data, context)
            else:
                result = {
                    'success': False, 
                    'error': f'Unknown step type: {step_type}',
                    'execution_time_ms': 0
                }
            
            step_result = {
                'step_id': step_data.get('step', 1),
                'success': result.get('success', False),
                'message': result.get('message', step_data.get('description', '')),
                'execution_time_ms': result.get('execution_time_ms', 0)
            }
            
            # Include navigation transitions if available (avoid re-fetching in UI)
            if result.get('transitions'):
                step_result['transitions'] = result['transitions']
            
            return step_result
            
        except Exception as e:
            return {
                'step_id': step_data.get('step', 1),
                'success': False,
                'message': str(e),
                'execution_time_ms': 0
            }
    
    def _determine_step_type(self, command: str) -> str:
        """Determine step type from command - simple classification"""
        if command == 'execute_navigation':
            return 'navigation'
        elif command == 'navigation_reassessment':
            return 'navigation_reassessment'
        elif command in ['press_key', 'click_element', 'input_text', 'tap_coordinates']:
            return 'action'
        elif command.startswith('verify_') or command.startswith('check_'):
            return 'verification'
        elif command == 'wait':
            return 'wait'
        else:
            return 'unknown'
    
    def _execute_navigation_step(self, step_data: Dict, context: Dict) -> Dict[str, Any]:
        """Execute navigation step via NavigationExecutor"""
        params = step_data.get('params', {})
        
        # Update navigation executor context
        self.device.navigation_executor.tree_id = context.get('tree_id')
        
        result = self.device.navigation_executor.execute_navigation(
            tree_id=context.get('tree_id'),
            target_node_id=params.get('target_node'),
            current_node_id=context.get('current_node_id'),
            team_id=context.get('team_id')
        )
        
        # Update context with position changes
        if result.get('success') and result.get('final_position_node_id'):
            context['final_position_node_id'] = result.get('final_position_node_id')
        
        # Include navigation_path in result for frontend (avoid re-fetching)
        if result.get('navigation_path'):
            result['transitions'] = result['navigation_path']  # Rename for frontend clarity
        
        return result
    
    def _execute_navigation_reassessment_step(self, step_data: Dict, context: Dict) -> Dict[str, Any]:
        """Execute navigation reassessment step - take screenshot and find target"""
        start_time = time.time()
        
        try:
            # Take screenshot using verification executor
            success, screenshot_b64, error = self.device.verification_executor.take_screenshot()
            if not success:
                return {
                    'success': False, 
                    'error': f'Screenshot failed: {error}',
                    'execution_time_ms': int((time.time() - start_time) * 1000)
                }
            
            # Get reassessment parameters
            params = step_data.get('params', {})
            original_target = params.get('original_target', '')
            remaining_goal = params.get('remaining_goal', '')
            
            print(f"[@ai_executor] Navigation reassessment: looking for '{original_target}' with goal '{remaining_goal}'")
            
            # Call AI with screenshot for navigation reassessment
            reassessment_result = self._navigation_reassess_with_visual(
                original_target=original_target,
                remaining_goal=remaining_goal,
                screenshot=screenshot_b64,
                context=context
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            if not reassessment_result.get('success'):
                return {
                    'success': False, 
                    'error': f'Cannot find {original_target} on current screen: {reassessment_result.get("error", "Visual analysis failed")}',
                    'execution_time_ms': execution_time_ms,
                    'reassessment_failed': True
                }
            
            # Get updated steps from reassessment
            updated_steps = reassessment_result.get('steps', [])
            
            return {
                'success': True,
                'message': f'Found {original_target} on screen, generated {len(updated_steps)} follow-up steps',
                'execution_time_ms': execution_time_ms,
                'updated_steps': updated_steps,
                'requires_step_injection': True,
                'analysis': reassessment_result.get('analysis', '')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Navigation reassessment error: {str(e)}',
                'execution_time_ms': int((time.time() - start_time) * 1000)
            }
    
    def _navigation_reassess_with_visual(self, original_target: str, remaining_goal: str, 
                                       screenshot: str, context: Dict) -> Dict[str, Any]:
        """Call AI with screenshot to find navigation target and generate next steps"""
        
        prompt = f"""You are looking at a screenshot of a TV interface. 
        
Original goal: {remaining_goal}
Target you're looking for: "{original_target}"
Current screen: You've navigated to the closest available node and now need to find "{original_target}".

Analyze the screenshot and:
1. Can you see "{original_target}" or something similar on the screen?
2. If yes, provide the exact steps to reach it (click coordinates, press keys, etc.)
3. If no, respond with feasible=false

Available actions you can use:
- click_element: Click on UI element by text/ID
- tap_coordinates: Tap at specific screen coordinates  
- press_key: Press remote control keys (BACK, HOME, UP, DOWN, LEFT, RIGHT, OK, etc.)
- swipe_up, swipe_down, swipe_left, swipe_right: Swipe gestures

Respond with JSON only:
{{"analysis": "I can see...", "feasible": true/false, "steps": [{{"step": 1, "command": "tap_coordinates", "params": {{"x": 100, "y": 200, "action_type": "remote"}}, "description": "Tap on replay button"}}]}}

If feasible=false, the navigation will fail. Only return feasible=true if you can clearly see the target."""

        from shared.src.lib.utils.ai_utils import call_vision_ai
        
        try:
            result = call_vision_ai(prompt, screenshot, max_tokens=500, temperature=0.0)
            
            if not result.get('success'):
                return {'success': False, 'error': f'AI vision call failed: {result.get("error", "Unknown error")}'}
            
            # Parse AI response
            import json
            ai_response = json.loads(result['content'].strip())
            
            return {
                'success': ai_response.get('feasible', False),
                'steps': ai_response.get('steps', []),
                'analysis': ai_response.get('analysis', ''),
                'error': None if ai_response.get('feasible', False) else ai_response.get('analysis', 'Target not found')
            }
            
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid AI response format: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Vision analysis error: {str(e)}'}
    
    def _execute_action_step(self, step_data: Dict, context: Dict) -> Dict[str, Any]:
        """Execute action step via ActionExecutor"""
        action = {
            'command': step_data.get('command'),
            'params': step_data.get('params', {}),
            'action_type': step_data.get('params', {}).get('action_type', 'remote')
        }
        
        return self.device.action_executor.execute_actions([action], team_id=context.get('team_id'))
    
    def _execute_verification_step(self, step_data: Dict, context: Dict) -> Dict[str, Any]:
        """Execute verification step via VerificationExecutor"""
        verification = {
            'verification_type': step_data.get('params', {}).get('verification_type', 'text'),
            'command': step_data.get('command'),
            'params': step_data.get('params', {})
        }
        
        return self.device.verification_executor.execute_verifications([verification], team_id=context.get('team_id'))
    
    def _execute_wait_step(self, step_data: Dict, context: Dict) -> Dict[str, Any]:
        """Execute wait step - simple timing operation"""
        start_wait = time.time()
        duration_ms = step_data.get('params', {}).get('duration', 1000)
        
        time.sleep(duration_ms / 1000.0)
        actual_wait_ms = int((time.time() - start_wait) * 1000)
        
        return {
            'success': True,
            'message': f'Waited {duration_ms}ms',
            'execution_time_ms': actual_wait_ms
        }
    
    @classmethod
    def clear_all_cache(cls):
        """Clear all class-level caches"""
        cls._executions.clear()
        print("[@ai_executor] Cleared all execution caches")
    
    # ========================================
    # INTEGRATED AI PLAN GENERATION METHODS
    # ========================================
    
    def generate_plan(self, prompt: str, context: Dict, current_node_id: str = None) -> Dict:
        """Generate plan dict directly - no object conversion"""
        # Add current node to context
        context = context.copy()
        context['current_node_id'] = current_node_id
        
        # Use cached context if available
        cached_context = self._get_cached_context(context)
        ai_response = self._call_ai(prompt, cached_context)
        
        # Transform plan structure for frontend compatibility
        if 'plan' in ai_response:
            ai_response['steps'] = ai_response.pop('plan')  # Rename 'plan' to 'steps'
        
        # Add metadata to AI response and return dict directly
        ai_response['id'] = str(uuid.uuid4())
        ai_response['prompt'] = prompt
        
        # PRE-FETCH TRANSITIONS: Fetch navigation transitions for each navigation step
        # This ensures transitions are ALWAYS available in the plan (no UI fetching needed)
        if ai_response.get('steps'):
            self._prefetch_navigation_transitions(ai_response['steps'], context)
        
        return ai_response
    
    def _prefetch_navigation_transitions(self, steps: List[Dict], context: Dict) -> None:
        """
        Pre-fetch navigation transitions for all navigation steps in the plan.
        This ensures transitions are embedded in the plan and NO UI fetching is needed.
        
        Args:
            steps: List of plan steps
            context: Execution context with tree_id and team_id
        """
        tree_id = context.get('tree_id')
        team_id = context.get('team_id')
        
        if not tree_id or not team_id:
            print(f"[@ai_executor:prefetch] Skipping transition prefetch - missing tree_id or team_id")
            return
        
        for step in steps:
            if step.get('command') == 'execute_navigation':
                target_node = step.get('params', {}).get('target_node')
                if not target_node:
                    continue
                
                try:
                    # Use navigation executor's preview functionality
                    from backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path
                    
                    # Get navigation path (same logic as preview)
                    # Signature: find_shortest_path(tree_id, target_node_id, team_id, start_node_id=None)
                    navigation_path = find_shortest_path(tree_id, target_node, team_id, start_node_id=None)
                    
                    if navigation_path:
                        # Store transitions directly in the step
                        step['transitions'] = navigation_path
                        print(f"[@ai_executor:prefetch] Pre-fetched {len(navigation_path)} transitions for step: {target_node}")
                    else:
                        print(f"[@ai_executor:prefetch] No path found for: {target_node}")
                        step['transitions'] = []
                        
                except Exception as e:
                    print(f"[@ai_executor:prefetch] Error fetching transitions for {target_node}: {str(e)}")
                    step['transitions'] = []  # Empty transitions on error
    
    def _get_cached_context(self, context: Dict) -> Dict:
        """Apply caching logic to context"""
        userinterface_name = context['userinterface_name']
        device_model = context['device_model']
        current_time = time.time()
        
        # Check main context cache
        cache_key = f"{userinterface_name}:{device_model}"
        if cache_key in self._context_cache:
            cached_data, cache_time = self._context_cache[cache_key]
            if current_time - cache_time < self._cache_ttl:
                print(f"[@ai_executor] Using cached context for {cache_key}")
                # Merge with current context (preserve current_node_id)
                cached_data = cached_data.copy()
                cached_data['current_node_id'] = context.get('current_node_id')
                return cached_data
        
        # Cache the context
        self._context_cache[cache_key] = (context, current_time)
        print(f"[@ai_executor] Cached context for {cache_key}")
        return context
    
    def _call_ai(self, prompt: str, context: Dict) -> Dict:
        """Integrated AI prompt logic with all original sophistication"""
        available_nodes = context['available_nodes']
        available_actions = context['available_actions']
        available_verifications = context['available_verifications']
        device_model = context['device_model']
        current_node_id = context.get('current_node_id')
        current_node_label = context.get('current_node_label')
        
        print(f"[@ai_executor] _call_ai context: nodes={len(available_nodes)}, actions={len(available_actions)}, verifications={len(available_verifications)}, device_model={device_model}")
        
        # Use context as-is from services
        navigation_context = available_nodes
        action_context = available_actions
        verification_context = available_verifications
        
        # Integrated sophisticated AI prompt
        ai_prompt = f"""You are controlling a TV application on a device ({device_model}).
Your task is to navigate through the app using available commands provided.

Task: "{prompt}"
Device: {device_model}
Current Position: {current_node_label}

Navigation System: Each node in the navigation list is a DIRECT destination you can navigate to in ONE STEP.
- Node names like "home_replay", "home_movies", "live" are COMPLETE node identifiers, not hierarchical paths
- To go to "home_replay" → execute_navigation with target_node="home_replay" (NOT "home" then "replay")
- Each node represents a specific screen/section that can be reached directly through the navigation tree
- Only use action commands (click/press) if the exact node doesn't exist in the available navigation nodes

{navigation_context}

{action_context}

{verification_context}

Rules:
- If already at target node, respond with feasible=true, plan=[]
- If exact node exists → navigate directly: execute_navigation, target_node="X"
- If exact node NOT exists:
  1. Check if SIMILAR/RELATED node exists (e.g., "live" for "live fullscreen")
  2. If similar exists → navigate to similar node + add navigation_reassessment
  3. If NO similar node → set feasible=false (DO NOT guess or invent node names)
- "click X" → click_element, element_id="X"  
- "press X" → press_key, key="X"
- NEVER break down node names (e.g., "home_replay" is ONE node, not "home" + "replay")
- NEVER use node names not in the navigation list
- PRIORITIZE navigation over manual actions
- ALWAYS specify action_type in params
- CRITICAL: When no relevant nodes exist, mark task as NOT FEASIBLE immediately

Navigation Reassessment Format:
When target node doesn't exist, use this pattern:
{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "closest_node", "action_type": "navigation"}}}},
{{"step": 2, "command": "navigation_reassessment", "params": {{"original_target": "target_name", "remaining_goal": "find and click target_name", "action_type": "navigation"}}}}

CRITICAL: You MUST include an "analysis" field with Goal and Thinking.

Analysis format:
- Goal: [What needs to be achieved]
- Thinking: [Brief explanation of approach/reasoning]

DESCRIPTION FIELD RULES:
- NEVER use verbose AI descriptions like "Navigate directly to X" or "The X node exists..."
- Keep descriptions minimal: just the target node name for navigation steps
- For navigation: description should be ONLY the target node name (e.g., "home_replay", "live")
- For actions: description can be brief command (e.g., "click element", "press key")

Example response formats:

Direct navigation (exact node exists):
{{"analysis": "Goal: Navigate to home_replay screen\nThinking: 'home_replay' node exists in navigation list → direct navigation in one step", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "home_replay", "action_type": "navigation"}}, "description": "home_replay"}}]}}

Navigation with reassessment (exact node doesn't exist):
{{"analysis": "Goal: Find and access 'replay' element\nThinking: Exact 'replay' node not found → navigate to closest 'home_replay' → use visual reassessment to locate target", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "home_replay", "action_type": "navigation"}}, "description": "home_replay"}}, {{"step": 2, "command": "navigation_reassessment", "params": {{"original_target": "replay", "remaining_goal": "find and click replay button", "action_type": "navigation"}}, "description": "reassess navigation"}}]}}

If task is not possible:
{{"analysis": "Goal: [state goal]\nThinking: Task not feasible → no relevant navigation nodes exist and visual reassessment cannot help", "feasible": false, "plan": []}}

RESPOND WITH JSON ONLY. Keep analysis concise with Goal and Thinking structure."""

        # Log the full prompt for debugging
        print(f"[@ai_executor] AI Prompt (length: {len(ai_prompt)} chars):")
        print("=" * 80)
        print(repr(ai_prompt))
        print("=" * 80)

        # Integrated AI call logic
        result = call_text_ai(
            prompt=ai_prompt,
            max_tokens=2000,
            temperature=0.0,
            model=AI_CONFIG['providers']['openrouter']['models']['agent']
        )

        print(f"[@ai_executor] AI Response received, content length: {len(result.get('content', '')) if result else 0} characters")

        if not result.get('success'):
            raise Exception(f"AI call failed: {result.get('error')}")

        return self._extract_json_from_ai_response(result['content'])
    
    def _extract_json_from_ai_response(self, content: str) -> Dict[str, Any]:
        """Extract and sanitize JSON from AI response with robust error handling"""
        try:
            # Use existing codebase pattern (same as ai_utils.py, video_ai_helpers.py, ai_analyzer.py)
            cleaned_content = content.strip()
            
            # Handle markdown code blocks
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content.replace('```json', '').replace('```', '').strip()
            elif cleaned_content.startswith('```'):
                cleaned_content = cleaned_content.replace('```', '').strip()
            
            # CRITICAL FIX: Sanitize control characters in JSON strings
            # AI sometimes returns literal newlines in "analysis" field instead of \n
            # This causes "Invalid control character" JSON parse errors
            cleaned_content = self._sanitize_json_string(cleaned_content)
            
            print(f"[@ai_executor] Cleaned content (first 200 chars): {repr(cleaned_content[:200])}")
            
            # Parse JSON
            parsed_json = json.loads(cleaned_content)
            print(f"[@ai_executor] ✅ Successfully parsed JSON with keys: {list(parsed_json.keys())}")
            
            # Validate required fields
            if 'analysis' not in parsed_json:
                raise Exception("AI response missing required 'analysis' field")
            if 'feasible' not in parsed_json:
                print(f"[@ai_executor] ⚠️ Warning: 'feasible' field missing, defaulting to True")
                parsed_json['feasible'] = True
            if 'plan' not in parsed_json:
                print(f"[@ai_executor] ⚠️ Warning: 'plan' field missing, defaulting to empty array")
                parsed_json['plan'] = []
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            # Enhanced error reporting
            error_pos = e.pos if hasattr(e, 'pos') else 'unknown'
            error_context = content[max(0, error_pos-50):error_pos+50] if error_pos != 'unknown' else content[:100]
            
            print(f"[@ai_executor] ❌ JSON parsing error at position {error_pos}: {e}")
            print(f"[@ai_executor] Error context: {repr(error_context)}")
            print(f"[@ai_executor] Full raw content (first 500 chars): {repr(content[:500])}")
            
            raise Exception(f"AI returned invalid JSON at position {error_pos}: {e}")
        except Exception as e:
            print(f"[@ai_executor] ❌ JSON extraction error: {e}")
            print(f"[@ai_executor] Raw content (first 500 chars): {repr(content[:500])}")
            raise Exception(f"Failed to extract JSON from AI response: {e}")
    
    def _sanitize_json_string(self, json_str: str) -> str:
        """Sanitize JSON string by escaping control characters in string values"""
        import re
        
        # Find all string values in JSON (content between quotes not preceded by backslash)
        # This regex finds "..." strings and escapes control characters inside them
        def escape_control_chars(match):
            string_content = match.group(1)
            # Escape control characters
            string_content = string_content.replace('\\', '\\\\')  # Escape backslashes first
            string_content = string_content.replace('\n', '\\n')   # Escape newlines
            string_content = string_content.replace('\r', '\\r')   # Escape carriage returns
            string_content = string_content.replace('\t', '\\t')   # Escape tabs
            string_content = string_content.replace('\b', '\\b')   # Escape backspace
            string_content = string_content.replace('\f', '\\f')   # Escape form feed
            return f'"{string_content}"'
        
        # Match quoted strings (but not already escaped quotes)
        # This pattern matches: "any content that's not a quote or is an escaped quote"
        pattern = r'"((?:[^"\\]|\\.)*)\"'
        sanitized = re.sub(pattern, escape_control_chars, json_str)
        
        return sanitized
    
    def clear_context_cache(self, device_model: str = None, userinterface_name: str = None):
        """Clear context caches with all original cache clearing logic"""
        if device_model and userinterface_name:
            # Clear specific caches
            action_key = f"action:{device_model}:{userinterface_name}"
            verification_key = f"verification:{device_model}:{userinterface_name}"
            navigation_key = f"navigation:{device_model}:{userinterface_name}"
            context_key = f"{userinterface_name}:{device_model}"
            
            self._action_cache.pop(action_key, None)
            self._verification_cache.pop(verification_key, None)
            self._navigation_cache.pop(navigation_key, None)
            self._context_cache.pop(context_key, None)
            
            print(f"[@ai_executor] Cleared context caches for model: {device_model}, interface: {userinterface_name}")
        else:
            # Clear all caches
            self._action_cache.clear()
            self._verification_cache.clear()
            self._navigation_cache.clear()
            self._context_cache.clear()
            print(f"[@ai_executor] Cleared all context caches")
