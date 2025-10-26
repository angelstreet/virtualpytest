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
        
        # Initialize execution tracking immediately (no plan yet)
        self._init_execution_tracking(execution_id, prompt, start_time)
        
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
                    print(f"[@ai_executor] ✓ Using cached plan (no AI call needed): {cached_plan['fingerprint'][:8]}...")
                    plan_dict = cached_plan['plan']
                    
                    # Execute cached plan
                    if async_execution:
                        # Set plan and start execution
                        self._set_execution_plan(execution_id, plan_dict)
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
                        # Synchronous cached execution
                        self._set_execution_plan(execution_id, plan_dict)
                        result = self._execute_cached_plan_sync(cached_plan, context, team_id)
                        self._complete_execution_tracking(execution_id, result)
                        return {
                            'success': result.success,
                            'execution_id': execution_id,
                            'message': 'Cached plan executed',
                            'cached': True,
                            'result': result,
                            'execution_time': time.time() - start_time
                        }
                else:
                    # Cache miss - fall through to generate new plan (this is normal for first executions)
                    print(f"[@ai_executor] ✓ Cache miss (normal) - Will generate new plan with AI")
            
            # Generate new plan (cache miss or use_cache=False)
            if use_cache:
                print(f"[@ai_executor] 🤖 Generating new plan with AI (will be cached after successful execution for future reuse)")
            else:
                print(f"[@ai_executor] 🤖 Generating new plan with AI (caching disabled - plan will NOT be saved)")
            
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
                # Set plan and start execution
                self._set_execution_plan(execution_id, plan_dict)
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
                self._set_execution_plan(execution_id, plan_dict)
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
            # Set error plan and mark as failed
            error_plan = {
                'id': execution_id,
                'prompt': prompt,
                'analysis': f'Goal: {prompt}\nThinking: Plan generation failed - {str(e)}',
                'feasible': False,
                'steps': []
            }
            
            if execution_id in AIExecutor._executions:
                AIExecutor._executions[execution_id]['plan'] = error_plan
                AIExecutor._executions[execution_id]['status'] = 'failed'
                AIExecutor._executions[execution_id]['current_step'] = f'Error: {str(e)}'
                AIExecutor._executions[execution_id]['end_time'] = time.time()
            
            print(f"[@ai_executor] Execution {execution_id} failed: {str(e)}")
            
            return {
                'success': False,
                'execution_id': execution_id,
                'error': f'AI execution error: {str(e)}',
                'execution_time': time.time() - start_time
            }
    
    def generate_graph_only(self, 
                           prompt: str, 
                           userinterface_name: str,
                           team_id: str,
                           current_node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate visual graph for TestCase Builder WITHOUT execution.
        This returns the graph structure for display in the builder UI.
        
        Args:
            prompt: User prompt
            userinterface_name: Interface name
            team_id: Team ID
            current_node_id: Current navigation position
        
        Returns:
            Dict with 'success', 'graph', 'analysis', etc.
        """
        start_time = time.time()
        
        try:
            # Get current position if not provided
            if current_node_id is None:
                position = self.device.navigation_executor.get_current_position()
                current_node_id = position.get('current_node_id')
            
            # Load context using device's existing executors
            context = self._load_context(userinterface_name, current_node_id, team_id)
            
            # Generate plan (which includes graph)
            print(f"[@ai_executor] 🎨 Generating graph only (no execution) for prompt: {prompt}")
            plan_dict = self.generate_plan(prompt, context, current_node_id)
            
            if not plan_dict.get('feasible', True):
                return {
                    'success': False,
                    'error': 'Task not feasible',
                    'analysis': plan_dict.get('analysis', ''),
                    'execution_time': time.time() - start_time
                }
            
            # Calculate block counts from graph
            graph = plan_dict.get('graph', {})
            nodes = graph.get('nodes', [])
            
            block_counts = {
                'navigation': len([n for n in nodes if n.get('type') == 'navigation']),
                'action': len([n for n in nodes if n.get('type') == 'action']),
                'verification': len([n for n in nodes if n.get('type') == 'verification']),
                'other': len([n for n in nodes if n.get('type') not in ['start', 'success', 'failure', 'navigation', 'action', 'verification']]),
                'total': len(nodes),
            }
            
            # Get block details for list
            blocks_generated = [
                {
                    'type': node.get('type'),
                    'label': node.get('data', {}).get('label') or node.get('data', {}).get('command') or node.get('type'),
                    'id': node.get('id'),
                }
                for node in nodes
            ]
            
            # Extract usage stats (token counts)
            usage = plan_dict.get('_usage', {})
            
            # Return graph structure without execution
            return {
                'success': True,
                'graph': graph,
                'analysis': plan_dict.get('analysis', ''),
                'plan_id': plan_dict.get('id'),
                'execution_time': time.time() - start_time,
                'message': 'Graph generated successfully (not executed)',
                'generation_stats': {
                    'prompt_tokens': usage.get('prompt_tokens', 0),
                    'completion_tokens': usage.get('completion_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0),
                    'block_counts': block_counts,
                    'blocks_generated': blocks_generated,
                }
            }
                
        except Exception as e:
            print(f"[@ai_executor] Graph generation failed: {str(e)}")
            return {
                'success': False,
                'error': f'Graph generation error: {str(e)}',
                'execution_time': time.time() - start_time
            }
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status - use class variable explicitly"""
        print(f"[@ai_executor] Looking for execution {execution_id}, available executions: {list(AIExecutor._executions.keys())}")
        
        if execution_id not in AIExecutor._executions:
            print(f"[@ai_executor] Execution {execution_id} not found in tracking")
            return {
                'success': False,
                'error': f'Execution {execution_id} not found',
                'is_executing': False
            }
        
        execution = AIExecutor._executions[execution_id]
        plan = execution.get('plan')
        
        # Handle case where plan hasn't been generated yet
        if not plan:
            return {
                'success': True,
                'execution_id': execution_id,
                'status': execution['status'],
                'current_step': execution['current_step'],
                'progress_percentage': 0,
                'plan': None,
                'step_results': [],
                'execution_log': [],
                'is_executing': execution['status'] in ['generating_plan', 'executing']
            }
        
        plan_steps = plan.get('steps', [])
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
    
    def _init_execution_tracking(self, execution_id: str, prompt: str, start_time: float):
        """Initialize execution tracking - plan will be added when generated"""
        AIExecutor._executions[execution_id] = {
            'plan': None,  # Will be set when plan is generated
            'prompt': prompt,
            'status': 'generating_plan',
            'current_step': 'Generating AI plan...',
            'step_results': [],
            'start_time': start_time
        }
        print(f"[@ai_executor] Initialized tracking for execution {execution_id}")
        print(f"[@ai_executor] Total executions tracked: {len(AIExecutor._executions)}")
    
    def _set_execution_plan(self, execution_id: str, plan_dict: Dict):
        """Set plan for execution and update status to executing"""
        if execution_id not in AIExecutor._executions:
            print(f"[@ai_executor] ERROR: Execution {execution_id} not found when setting plan")
            return
        
        graph = plan_dict.get('graph', {})
        nodes = graph.get('nodes', [])
        # Count executable nodes (exclude start, success, failure)
        executable_nodes = [n for n in nodes if n.get('type') not in ['start', 'success', 'failure']]
        
        print(f"[@ai_executor] 🔍 Plan dict keys: {list(plan_dict.keys())}")
        print(f"[@ai_executor] 🔍 Graph nodes: {len(nodes)}, executable: {len(executable_nodes)}")
        
        AIExecutor._executions[execution_id]['plan'] = plan_dict
        AIExecutor._executions[execution_id]['status'] = 'executing'
        AIExecutor._executions[execution_id]['current_step'] = f"Starting execution with {len(executable_nodes)} nodes..."
        print(f"[@ai_executor] ▶️ Set plan for execution {execution_id} with {len(executable_nodes)} nodes")
    
    def _complete_execution_tracking(self, execution_id: str, result: ExecutionResult):
        """Complete execution tracking - use class variable explicitly"""
        if execution_id in AIExecutor._executions:
            execution = AIExecutor._executions[execution_id]
            execution['status'] = 'completed' if result.success else 'failed'
            execution['result'] = result
            execution['end_time'] = time.time()
            
            # Extract step_results from ExecutionResult for get_execution_status
            execution['step_results'] = result.step_results if hasattr(result, 'step_results') else []
            
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
        Shows clean command format - NO verbose AI descriptions.
        """
        command = step_data.get('command', 'unknown')
        params = step_data.get('params', {})
        
        if command == 'execute_navigation':
            target_node = params.get('target_node', 'unknown')
            return f"{command}({target_node})"
        elif command == 'click_element':
            element_id = params.get('element_id', 'unknown')
            return f"{command}({element_id})"
        elif command == 'tap_coordinates':
            x = params.get('x', '?')
            y = params.get('y', '?')
            return f"{command}(x={x}, y={y})"
        elif command == 'press_key':
            key = params.get('key', 'unknown')
            return f"{command}({key})"
        elif command.startswith('verify_'):
            # For verification, show command name
            return command
        else:
            # Default: show command name
            return command
    
    def _update_current_step_tracking(self, plan_id: str, step_number: int, step_description: str):
        """Update current step in real-time tracking - use class variable explicitly"""
        for exec_id, exec_data in AIExecutor._executions.items():
            if exec_data.get('plan', {}).get('id') == plan_id:
                exec_data['current_step'] = step_description
                print(f"[@ai_executor] Step {step_number} started for execution {exec_id}: {step_description}")
                break
    
    def _update_step_result_tracking(self, plan_id: str, step_number: int, step_result: Dict[str, Any], all_step_results: List[Dict[str, Any]]):
        """Update step result in real-time tracking - use class variable explicitly"""
        for exec_id, exec_data in AIExecutor._executions.items():
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
        """Execute graph using TestCaseExecutor"""
        start_time = time.time()
        
        print(f"[@ai_executor] ▶️ Starting graph execution - plan_dict keys: {list(plan_dict.keys())}")
        
        graph = plan_dict.get('graph')
        if not graph:
            return ExecutionResult(
                plan_id=plan_dict.get('id', 'unknown'),
                success=False,
                step_results=[],
                total_time_ms=0,
                error="No graph found in plan"
            )
        
        # Create ScriptExecutionContext for testcase executor
        from shared.src.lib.executors.script_executor import ScriptExecutionContext
        execution_context = ScriptExecutionContext("ai_execution")
        execution_context.team_id = context.get('team_id')
        execution_context.userinterface_name = context.get('userinterface_name')
        execution_context.tree_id = context.get('tree_id')
        execution_context.selected_device = self.device
        
        # Get host from device
        from backend_host.src.controllers.controller_manager import get_host
        host = get_host(device_ids=[self.device.device_id])
        execution_context.host = host
        
        # Use TestCaseExecutor to execute graph
        from backend_host.src.services.testcase.testcase_executor import TestCaseExecutor
        executor = TestCaseExecutor()
        executor.device = self.device
        executor.context = execution_context
        
        print(f"[@ai_executor] 🎯 Executing graph with {len(graph.get('nodes', []))} nodes via TestCaseExecutor")
        
        result = executor._execute_graph(graph, execution_context)
        
        total_time = int((time.time() - start_time) * 1000)
        
        print(f"[@ai_executor] ⏹️ Graph execution completed - Success: {result.get('success')}, Time: {total_time}ms")
        
        # Convert testcase executor result to ExecutionResult
        return ExecutionResult(
            plan_id=plan_dict.get('id', 'unknown'),
            success=result.get('success', False),
            step_results=execution_context.step_results,  # From context.record_step_immediately()
            total_time_ms=total_time,
            error=result.get('error')
        )
    
    @classmethod
    def clear_all_cache(cls):
        """Clear all class-level caches"""
        cls._executions.clear()
        print("[@ai_executor] Cleared all execution caches")
    
    # ========================================
    # INTEGRATED AI PLAN GENERATION METHODS
    # ========================================
    
    def generate_plan(self, prompt: str, context: Dict, current_node_id: str = None) -> Dict:
        """Generate test case graph directly"""
        # Add current node to context
        context = context.copy()
        context['current_node_id'] = current_node_id
        
        # Use cached context if available
        cached_context = self._get_cached_context(context)
        ai_response = self._call_ai(prompt, cached_context)
        
        # Add metadata
        ai_response['id'] = str(uuid.uuid4())
        ai_response['prompt'] = prompt
        
        # Extract steps from graph and pre-fetch transitions
        if ai_response.get('feasible', True) and ai_response.get('graph'):
            self._prefetch_navigation_transitions_from_graph(ai_response['graph'], context)
            steps = self._extract_steps_from_graph(ai_response['graph'])
            ai_response['steps'] = steps
            
            print(f"[@ai_executor] 📊 Graph nodes: {len(ai_response['graph'].get('nodes', []))}")
            print(f"[@ai_executor] 📊 Extracted steps: {len(steps)}")
            print(f"[@ai_executor] 📊 Steps: {[s.get('command') for s in steps]}")
        
        return ai_response
    
    def _extract_steps_from_graph(self, graph: Dict) -> List[Dict]:
        """Extract executable steps from graph nodes"""
        steps = []
        
        for node in graph.get('nodes', []):
            node_type = node.get('type')
            if node_type in ['start', 'success', 'failure']:
                continue
            
            data = node.get('data', {})
            
            if node_type == 'navigation':
                steps.append({
                    'command': 'execute_navigation',
                    'params': {
                        'target_node': data.get('target_node'),
                        'transitions': data.get('transitions', [])
                    }
                })
            elif node_type == 'action':
                steps.append({
                    'command': data.get('command'),
                    'params': {k: v for k, v in data.items() if k != 'command'}
                })
            elif node_type == 'verification':
                steps.append({
                    'command': f"verify_{data.get('verification_type', 'text')}",
                    'params': data
                })
            elif node_type == 'ai':
                steps.append({
                    'command': 'execute_ai',
                    'params': {'prompt': data.get('prompt', '')}
                })
        
        return steps
    
    def _prefetch_navigation_transitions_from_graph(self, graph: Dict, context: Dict) -> None:
        """
        Pre-fetch navigation transitions for all navigation nodes in the graph.
        This ensures transitions are embedded in the graph and NO UI fetching is needed.
        
        Args:
            graph: Graph structure with nodes and edges
            context: Execution context with tree_id and team_id
        """
        tree_id = context.get('tree_id')
        team_id = context.get('team_id')
        
        if not tree_id or not team_id:
            print(f"[@ai_executor:prefetch] Skipping transition prefetch - missing tree_id or team_id")
            return
        
        nodes = graph.get('nodes', [])
        for node in nodes:
            if node.get('type') == 'navigation':
                target_node = node.get('data', {}).get('target_node')
                if not target_node:
                    continue
                
                try:
                    # Use navigation executor's preview functionality
                    from backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path
                    
                    # Get navigation path
                    navigation_path = find_shortest_path(tree_id, target_node, team_id, start_node_id=None)
                    
                    if navigation_path:
                        # Store transitions directly in the node data
                        node['data']['transitions'] = navigation_path
                        print(f"[@ai_executor:prefetch] Pre-fetched {len(navigation_path)} transitions for node: {target_node}")
                    else:
                        print(f"[@ai_executor:prefetch] No path found for: {target_node}")
                        node['data']['transitions'] = []
                        
                except Exception as e:
                    print(f"[@ai_executor:prefetch] Error fetching transitions for {target_node}: {str(e)}")
                    node['data']['transitions'] = []
    
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

OUTPUT FORMAT: Generate a React Flow graph with nodes and edges.

Node Types:
- start: Entry point (always first, id="start")
- navigation: Navigate to UI node
- action: Execute device action  
- verification: Check UI state
- loop: Repeat nested flow
- success: Test passed (terminal)
- failure: Test failed (terminal)

{navigation_context}

{action_context}

{verification_context}

Rules:
- If already at target node, respond with feasible=true, graph with just start→success
- If exact node exists → navigate directly: navigation node with target_node="X"
- If exact node NOT exists → find SIMILAR node + add requires_reassessment metadata
- If NO similar node → set feasible=false
- NEVER use node names not in the navigation list
- PRIORITIZE navigation over manual actions
- ALWAYS specify action_type in node data

Reassessment Metadata:
When target node doesn't exist, add to navigation node data:
{{"requires_reassessment": true, "reassessment_config": {{"original_target": "target_name", "remaining_goal": "find and click target_name"}}}}

CRITICAL: Include "analysis" field with Goal and Thinking.

Analysis format:
- Goal: [What needs to be achieved]
- Thinking: [Brief explanation of approach/reasoning]

Example Response (direct navigation):
{{
  "analysis": "Goal: Navigate to home_replay screen\\nThinking: 'home_replay' node exists in navigation list → direct navigation in one step",
  "feasible": true,
  "graph": {{
    "nodes": [
      {{"id": "start", "type": "start", "position": {{"x": 100, "y": 100}}, "data": {{}}}},
      {{"id": "nav1", "type": "navigation", "position": {{"x": 100, "y": 200}}, "data": {{"target_node": "home_replay", "target_node_id": "home_replay", "action_type": "navigation"}}}},
      {{"id": "success", "type": "success", "position": {{"x": 100, "y": 300}}, "data": {{}}}}
    ],
    "edges": [
      {{"id": "e1", "source": "start", "target": "nav1", "sourceHandle": "success", "type": "success"}},
      {{"id": "e2", "source": "nav1", "target": "success", "sourceHandle": "success", "type": "success"}}
    ]
  }}
}}

Example (with action):
{{
  "analysis": "Goal: Click replay button\\nThinking: Navigate to home_replay then click element",
  "feasible": true,
  "graph": {{
    "nodes": [
      {{"id": "start", "type": "start", "position": {{"x": 100, "y": 100}}, "data": {{}}}},
      {{"id": "nav1", "type": "navigation", "position": {{"x": 100, "y": 200}}, "data": {{"target_node": "home_replay", "action_type": "navigation"}}}},
      {{"id": "act1", "type": "action", "position": {{"x": 100, "y": 300}}, "data": {{"command": "click_element", "element_id": "replay", "action_type": "remote"}}}},
      {{"id": "success", "type": "success", "position": {{"x": 100, "y": 400}}, "data": {{}}}}
    ],
    "edges": [
      {{"id": "e1", "source": "start", "target": "nav1", "sourceHandle": "success", "type": "success"}},
      {{"id": "e2", "source": "nav1", "target": "act1", "sourceHandle": "success", "type": "success"}},
      {{"id": "e3", "source": "act1", "target": "success", "sourceHandle": "success", "type": "success"}}
    ]
  }}
}}

If task is not possible:
{{"analysis": "Goal: [state goal]\\nThinking: Task not feasible → no relevant navigation nodes exist", "feasible": false, "graph": {{"nodes": [], "edges": []}}}}

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

        # Extract JSON and attach usage stats
        parsed_response = self._extract_json_from_ai_response(result['content'])
        
        # Attach usage stats to response for token tracking
        if 'usage' in result:
            parsed_response['_usage'] = result['usage']
        
        return parsed_response
    
    def _extract_json_from_ai_response(self, content: str) -> Dict[str, Any]:
        """Extract and sanitize JSON from AI response with robust error handling"""
        try:
            # Use existing codebase pattern (same as ai_utils.py, video_ai_helpers.py, ai_analyzer.py)
            cleaned_content = content.strip()
            
            # Handle markdown code blocks (AI sometimes wraps JSON in explanation + code blocks)
            # Pattern 1: Text followed by ```json ... ``` (most common with newer models)
            json_match = re.search(r'```json\s*\n(.*?)```', cleaned_content, re.DOTALL)
            if json_match:
                cleaned_content = json_match.group(1).strip()
                print(f"[@ai_executor] Extracted JSON from markdown code block (```json)")
            # Pattern 2: Text followed by ``` ... ``` (generic code block)
            elif '```' in cleaned_content:
                json_match = re.search(r'```\s*\n(.*?)```', cleaned_content, re.DOTALL)
                if json_match:
                    cleaned_content = json_match.group(1).strip()
                    print(f"[@ai_executor] Extracted JSON from generic markdown code block (```)")
            # Pattern 3: JSON starts directly with ```json
            elif cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content.replace('```json', '').replace('```', '').strip()
                print(f"[@ai_executor] Cleaned direct ```json start")
            elif cleaned_content.startswith('```'):
                cleaned_content = cleaned_content.replace('```', '').strip()
                print(f"[@ai_executor] Cleaned direct ``` start")
            
            # CRITICAL FIX: Sanitize control characters in JSON strings
            # AI sometimes returns literal newlines in "analysis" field instead of \n
            # This causes "Invalid control character" JSON parse errors
            cleaned_content = self._sanitize_json_string(cleaned_content)
            
            print(f"[@ai_executor] Cleaned content (first 200 chars): {repr(cleaned_content[:200])}")
            
            # Parse JSON - use JSONDecoder to handle trailing data
            from json import JSONDecoder
            decoder = JSONDecoder()
            parsed_json, idx = decoder.raw_decode(cleaned_content)
            
            # Check if there's extra content after the JSON
            remaining_content = cleaned_content[idx:].strip()
            if remaining_content:
                print(f"[@ai_executor] ⚠️ Warning: AI returned extra content after JSON: {repr(remaining_content[:100])}")
            
            print(f"[@ai_executor] ✅ Successfully parsed JSON with keys: {list(parsed_json.keys())}")
            
            # Validate required fields
            if 'analysis' not in parsed_json:
                raise Exception("AI response missing required 'analysis' field")
            if 'feasible' not in parsed_json:
                parsed_json['feasible'] = True
            
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
