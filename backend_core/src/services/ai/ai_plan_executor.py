"""
AI Plan Executor

Single, simplified AI plan executor that consolidates all AI functionality.
Replaces: AIExecutor, AISession, AIContextService, AITracker, AIDeviceTracker, AIPlanner
"""

import time
import uuid
import threading
import re
from typing import Dict, List, Optional, Any

from .ai_plan_generator import AIPlanGenerator
from .ai_types import ExecutionResult


class AIPlanExecutor:
    """
    Unified AI plan executor that handles all AI operations:
    - Context loading
    - Plan generation  
    - Plan execution
    - Status tracking
    - Device position tracking
    """
    
    # Class-level storage (replaces separate tracker classes)
    _executions = {}  # {execution_id: execution_data}
    _device_positions = {}  # {device_id: {'node_id': str, 'node_label': str}}
    _plan_generators = {}  # {team_id: AIPlanGenerator}
    
    def __init__(self, host: Dict[str, Any], device_id: str, team_id: str):
        """Initialize AI plan executor for a specific device"""
        self.host = host
        self.device_id = device_id
        self.team_id = team_id
        
        # Get device model once
        from shared.lib.utils.build_url_utils import get_device_by_id
        device_dict = get_device_by_id(host, device_id)
        if not device_dict:
            raise Exception(f"Device {device_id} not found in host")
        self.device_model = device_dict.get('device_model')
        
        # Initialize executors once per service instance
        from backend_core.src.services.actions.action_executor import ActionExecutor
        from backend_core.src.services.verifications.verification_executor import VerificationExecutor
        from backend_core.src.services.navigation.navigation_executor import NavigationExecutor
        
        self.action_executor = ActionExecutor(host, device_id, team_id)
        self.verification_executor = VerificationExecutor(host, device_id, team_id)
        self.navigation_executor = NavigationExecutor(host, device_id, team_id)
        
        print(f"[@ai_plan_executor] Initialized for device: {device_id}, model: {self.device_model}")
    
    def execute_prompt(self, 
                      prompt: str, 
                      userinterface_name: str,
                      current_node_id: Optional[str] = None,
                      async_execution: bool = True) -> Dict[str, Any]:
        """
        Execute AI prompt - generates plan and executes it
        
        Returns:
        - For async: {'success': True, 'execution_id': str}
        - For sync: {'success': bool, 'execution_id': str, 'result': dict}
        """
        start_time = time.time()
        execution_id = str(uuid.uuid4())
        
        try:
            # Get current position if not provided
            if current_node_id is None:
                position = self._get_device_position(self.device_id)
                current_node_id = position.get('node_id')
            
            # Check if already at target (quick optimization)
            target_node = self._extract_target_from_prompt(prompt)
            if target_node and target_node == current_node_id:
                print(f"[@ai_plan_executor] Already at target node '{target_node}' - no execution needed")
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'message': 'Already at target location',
                    'execution_time': time.time() - start_time
                }
            
            # Load context inline (no separate service)
            context = self._load_context(userinterface_name, current_node_id)
            
            # Generate plan using cached generator
            plan_generator = self._get_plan_generator(self.team_id)
            plan_dict = plan_generator.generate_plan(prompt, context, current_node_id)
            
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
                    target=self._execute_plan_async, 
                    args=(execution_id, plan_dict, context)
                ).start()
                
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'message': 'Execution started',
                    'plan_steps': len(plan_dict.get('steps', [])),
                    'execution_time': time.time() - start_time
                }
            else:
                # Synchronous execution
                self._start_execution_tracking(execution_id, plan_dict)
                result = self._execute_plan_sync(plan_dict, context)
                self._complete_execution_tracking(execution_id, result)
                
                return {
                    'success': result.success,
                    'execution_id': execution_id,
                    'message': 'Execution completed' if result.success else result.error,
                    'steps_executed': len([r for r in result.step_results if r.get('success')]),
                    'total_steps': len(result.step_results),
                    'execution_time': time.time() - start_time,
                    'result': result
                }
                
        except Exception as e:
            return {
                'success': False,
                'execution_id': execution_id,
                'error': f'AI execution error: {str(e)}',
                'execution_time': time.time() - start_time
            }
    
    def execute_testcase(self, test_case_id: str) -> Dict[str, Any]:
        """Execute stored test case"""
        try:
            from shared.lib.supabase.testcase_db import get_test_case
            
            # Load test case
            test_case = get_test_case(test_case_id, self.team_id)
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
            context = self._load_context(userinterface_name)
            
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
        if execution_id not in self._executions:
            return {
                'success': False,
                'error': 'Execution not found'
            }
        
        execution = self._executions[execution_id]
        plan_steps = execution['plan'].get('steps', [])
        completed_steps = len([r for r in execution['step_results'] if r.get('success')])
        
        return {
            'success': True,
            'execution_id': execution_id,
            'status': execution['status'],
            'current_step': execution['current_step'],
            'progress_percentage': (completed_steps / len(plan_steps)) * 100 if plan_steps else 0,
            'plan': execution['plan'],
            'step_results': execution['step_results'],
            'is_executing': execution['status'] == 'executing',
            'execution_summary': {
                'total_steps': len(plan_steps),
                'completed_steps': completed_steps,
                'failed_steps': len([r for r in execution['step_results'] if not r.get('success')]),
                'start_time': execution['start_time'],
                'end_time': execution.get('end_time')
            }
        }
    
    def get_device_position(self) -> Dict[str, Any]:
        """Get current device position"""
        position = self._get_device_position(self.device_id)
        return {
            'success': True,
            'device_id': self.device_id,
            'position': position
        }
    
    def update_device_position(self, node_id: str, node_label: str = None) -> Dict[str, Any]:
        """Update device position"""
        self._device_positions[self.device_id] = {
            'node_id': node_id,
            'node_label': node_label or node_id
        }
        print(f"[@ai_plan_executor] Updated position for {self.device_id}: {node_id}")
        
        return {
            'success': True,
            'device_id': self.device_id,
            'node_id': node_id,
            'node_label': node_label or node_id
        }
    
    # Private methods
    
    def _load_context(self, userinterface_name: str, current_node_id: str = None) -> Dict[str, Any]:
        """Load context from all executors - inline implementation"""
        print(f"[@ai_plan_executor] Loading context for device: {self.device_id}, model: {self.device_model}, interface: {userinterface_name}")
        
        # Load context from each executor
        action_context = self.action_executor.get_available_context(userinterface_name)
        verification_context = self.verification_executor.get_available_context(userinterface_name)
        navigation_context = self.navigation_executor.get_available_context(userinterface_name)
        
        return {
            'device_model': self.device_model,
            'userinterface_name': userinterface_name,
            'current_node_id': current_node_id,
            'tree_id': navigation_context.get('tree_id'),
            'available_nodes': navigation_context.get('available_nodes', []),
            'available_actions': action_context.get('available_actions', []),
            'available_verifications': verification_context.get('available_verifications', [])
        }
    
    def _get_plan_generator(self, team_id: str) -> AIPlanGenerator:
        """Get cached plan generator"""
        if team_id not in self._plan_generators:
            self._plan_generators[team_id] = AIPlanGenerator(team_id)
        return self._plan_generators[team_id]
    
    def _get_device_position(self, device_id: str) -> Dict[str, str]:
        """Get device position from class storage"""
        return self._device_positions.get(device_id, {})
    
    def _extract_target_from_prompt(self, prompt: str) -> Optional[str]:
        """Extract target node from prompt for optimization"""
        match = re.search(r'(?:go to|navigate to|goto)\s+(\w+)', prompt.lower())
        return match.group(1) if match else None
    
    def _start_execution_tracking(self, execution_id: str, plan_dict: Dict):
        """Start tracking execution"""
        self._executions[execution_id] = {
            'plan': plan_dict,
            'status': 'executing',
            'current_step': 0,
            'step_results': [],
            'start_time': time.time()
        }
        print(f"[@ai_plan_executor] Started tracking execution {execution_id}")
    
    def _complete_execution_tracking(self, execution_id: str, result: ExecutionResult):
        """Complete execution tracking"""
        if execution_id in self._executions:
            execution = self._executions[execution_id]
            execution['status'] = 'completed' if result.success else 'failed'
            execution['result'] = result
            execution['end_time'] = time.time()
            print(f"[@ai_plan_executor] Completed execution {execution_id}: {'success' if result.success else 'failed'}")
    
    def _execute_plan_async(self, execution_id: str, plan_dict: Dict, context: Dict):
        """Execute plan asynchronously"""
        try:
            result = self._execute_plan_sync(plan_dict, context)
            self._complete_execution_tracking(execution_id, result)
            
            # Update device position if successful
            if result.success:
                final_position = context.get('final_position_node_id')
                if final_position:
                    self.update_device_position(final_position)
                    
        except Exception as e:
            error_result = ExecutionResult(
                plan_id=plan_dict.get('id', 'unknown'),
                success=False,
                step_results=[],
                total_time_ms=0,
                error=str(e)
            )
            self._complete_execution_tracking(execution_id, error_result)
    
    def _execute_plan_sync(self, plan_dict: Dict, context: Dict) -> ExecutionResult:
        """Execute plan synchronously"""
        start_time = time.time()
        step_results = []
        
        plan_steps = plan_dict.get('steps', [])
        for i, step_data in enumerate(plan_steps):
            step_result = self._execute_step(step_data, context)
            step_results.append(step_result)
            
            # Update tracking
            if hasattr(self, '_executions'):
                for exec_id, exec_data in self._executions.items():
                    if exec_data.get('plan', {}).get('id') == plan_dict.get('id'):
                        exec_data['current_step'] = i + 1
                        exec_data['step_results'] = step_results
                        break
            
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
        """Execute a single step"""
        start_time = time.time()
        
        try:
            command = step_data.get('command')
            params = step_data.get('params', {})
            
            if command == 'execute_navigation':
                result = self.navigation_executor.execute_navigation(
                    tree_id=context.get('tree_id'),
                    target_node_id=params.get('target_node'),
                    current_node_id=context.get('current_node_id')
                )
                # Track position changes
                if result.get('success') and result.get('final_position_node_id'):
                    context['final_position_node_id'] = result.get('final_position_node_id')
                    
            elif command in ['press_key', 'click_element', 'input_text']:
                action = {
                    'command': command,
                    'params': params,
                    'action_type': params.get('action_type', 'remote')
                }
                result = self.action_executor.execute_actions([action])
                
            elif command.startswith('verify_') or command.startswith('check_'):
                verification = {
                    'verification_type': params.get('verification_type', 'text'),
                    'command': command,
                    'params': params
                }
                result = self.verification_executor.execute_verifications([verification])
                
            elif command == 'wait':
                duration_ms = params.get('duration', 1000)
                time.sleep(duration_ms / 1000.0)
                result = {'success': True, 'message': f'Waited {duration_ms}ms'}
                
            else:
                result = {'success': False, 'error': f'Unknown command: {command}'}
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return {
                'step_id': step_data.get('step', 1),
                'success': result.get('success', False),
                'message': result.get('message', step_data.get('description', '')),
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return {
                'step_id': step_data.get('step', 1),
                'success': False,
                'message': str(e),
                'execution_time_ms': execution_time
            }
    
    @classmethod
    def clear_all_cache(cls):
        """Clear all class-level caches"""
        cls._executions.clear()
        cls._device_positions.clear()
        cls._plan_generators.clear()
        print("[@ai_plan_executor] Cleared all caches")
