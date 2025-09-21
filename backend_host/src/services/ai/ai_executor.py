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
    """
    
    # Class-level storage for execution tracking across all devices
    _executions = {}  # {execution_id: execution_data}
    
    def __init__(self, device):
        """Initialize AI executor for a specific device"""
        # Validate required parameters - fail fast if missing
        if not device:
            raise ValueError("Device instance is required")
        if not device.host_name:
            raise ValueError("Device must have host_name")
        if not device.device_id:
            raise ValueError("Device must have device_id")
        
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
        
        print(f"[@ai_executor] Initialized for device: {self.device_id}, model: {self.device_model}")
    
    def execute_prompt(self, 
                      prompt: str, 
                      userinterface_name: str,
                      team_id: str,
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
                position = self.device.navigation_executor.get_current_position()
                current_node_id = position.get('current_node_id')
            
            # Check if already at target (quick optimization)
            target_node = self._extract_target_from_prompt(prompt)
            if target_node and target_node == current_node_id:
                print(f"[@ai_executor] Already at target node '{target_node}' - no execution needed")
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'message': 'Already at target location',
                    'execution_time': time.time() - start_time
                }
            
            # Load context using device's existing executors
            context = self._load_context(userinterface_name, current_node_id, team_id)
            
            # Generate plan using integrated plan generation
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
                'error': f'Execution {execution_id} not found'
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
            print(f"[@ai_executor] Completed execution {execution_id}: {'success' if result.success else 'failed'}")
    
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
    
    def _execute_plan_async(self, execution_id: str, plan_dict: Dict, context: Dict):
        """Execute plan asynchronously"""
        try:
            result = self._execute_plan_sync(plan_dict, context)
            self._complete_execution_tracking(execution_id, result)

                    
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
        """Execute plan synchronously using device's existing executors"""
        start_time = time.time()
        step_results = []
        
        plan_steps = plan_dict.get('steps', [])
        for i, step_data in enumerate(plan_steps):
            step_number = step_data.get('step', i + 1)
            
            # Update current step in tracking BEFORE execution
            self._update_current_step_tracking(plan_dict.get('id'), step_number, f"Executing step {step_number}: {step_data.get('description', step_data.get('command', 'Unknown step'))}")
            
            step_result = self._execute_step(step_data, context)
            step_results.append(step_result)
            
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
            
            return {
                'step_id': step_data.get('step', 1),
                'success': result.get('success', False),
                'message': result.get('message', step_data.get('description', '')),
                'execution_time_ms': result.get('execution_time_ms', 0)
            }
            
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
        
        return result
    
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
        return ai_response
    
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
- "go to node X" → execute_navigation, target_node="X" (use EXACT node name from navigation list)
- "click X" → click_element, element_id="X"  
- "press X" → press_key, key="X"
- NEVER break down node names (e.g., "home_replay" is ONE node, not "home" + "replay")
- PRIORITIZE navigation over manual actions
- ALWAYS specify action_type in params

CRITICAL: You MUST include an "analysis" field explaining your reasoning.

Example response format:
{{"analysis": "Task requires navigating to home_replay. Since 'home_replay' node is available in the navigation list, I'll navigate there directly in one step.", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "home_replay", "action_type": "navigation"}}, "description": "Navigate directly to home_replay"}}]}}

If task is not possible:
{{"analysis": "Task cannot be completed because the requested node does not exist in the navigation tree.", "feasible": false, "plan": []}}

RESPOND WITH JSON ONLY. ANALYSIS FIELD IS REQUIRED"""

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
        """Extract JSON from AI response using existing codebase pattern"""
        try:
            # Use existing codebase pattern (same as ai_utils.py, video_ai_helpers.py, ai_analyzer.py)
            cleaned_content = content.strip()
            
            # Handle markdown code blocks
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content.replace('```json', '').replace('```', '').strip()
            elif cleaned_content.startswith('```'):
                cleaned_content = cleaned_content.replace('```', '').strip()
            
            print(f"[@ai_executor] Cleaned content: {repr(cleaned_content)}")
            
            # Parse JSON
            parsed_json = json.loads(cleaned_content)
            print(f"[@ai_executor] Successfully parsed JSON with keys: {list(parsed_json.keys())}")
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            print(f"[@ai_executor] JSON parsing error: {e}")
            print(f"[@ai_executor] Raw content: {repr(content)}")
            raise Exception(f"AI returned invalid JSON: {e}")
        except Exception as e:
            print(f"[@ai_executor] JSON extraction error: {e}")
            raise Exception(f"Failed to extract JSON from AI response: {e}")
    
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
