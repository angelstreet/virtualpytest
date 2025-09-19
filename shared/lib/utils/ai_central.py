"""
AI System - Clean Architecture with All Features Preserved
"""

import time
import json
import uuid
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from shared.lib.utils.ai_utils import call_text_ai, AI_CONFIG


class ExecutionMode(Enum):
    REAL_TIME = "real_time"
    TEST_CASE = "test_case"
    SCRIPT = "script"


@dataclass
class ExecutionResult:
    plan_id: str
    success: bool
    step_results: List[Dict[str, Any]]
    total_time_ms: int
    error: Optional[str] = None


class AIContextService:
    """Centralized context loading - single responsibility"""
    
    @staticmethod
    def load_context(host: Dict, device_id: str, team_id: str, userinterface_name: str, device_model: str) -> Dict:
        """Load complete context from all executors"""
        from backend_core.src.services.actions.action_executor import ActionExecutor
        from backend_core.src.services.verifications.verification_executor import VerificationExecutor
        from backend_core.src.services.navigation.navigation_executor import NavigationExecutor
        
        # Create executors for context loading (they still need host for execution, but not for context)
        action_executor = ActionExecutor(host, device_id, team_id)
        verification_executor = VerificationExecutor(host, device_id, team_id)
        navigation_executor = NavigationExecutor(host, device_id, team_id)
        
        print(f"[@ai_context] Loading context for device: {device_id}, model: {device_model}, interface: {userinterface_name}")
        
        # Load context from each service
        action_context = action_executor.get_available_context(userinterface_name)
        verification_context = verification_executor.get_available_context(userinterface_name)
        navigation_context = navigation_executor.get_available_context(userinterface_name)
        
        return {
            'device_model': device_model,
            'userinterface_name': userinterface_name,
            'tree_id': navigation_context.get('tree_id'),
            'available_nodes': navigation_context.get('available_nodes', []),
            'available_actions': action_context.get('available_actions', []),
            'available_verifications': verification_context.get('available_verifications', [])
        }


class AIDeviceTracker:
    """Global device position tracking"""
    
    _device_positions = {}  # {device_id: {'node_id': 'home', 'node_label': 'Home Screen'}}
    
    @classmethod
    def get_position(cls, device_id: str) -> Dict[str, str]:
        """Get current device position"""
        return cls._device_positions.get(device_id, {})
    
    @classmethod
    def update_position(cls, device_id: str, node_id: str, node_label: str = None):
        """Update device position"""
        cls._device_positions[device_id] = {
            'node_id': node_id,
            'node_label': node_label or node_id
        }
        print(f"[@ai_device_tracker] Updated position for {device_id}: {node_id}")


class AIPlanGenerator:
    """Stateless AI planner with ALL original sophistication preserved"""
    
    def __init__(self, team_id: str):
        self.team_id = team_id
        # PRESERVE: All original caching logic
        self._context_cache = {}
        self._action_cache = {}
        self._verification_cache = {}
        self._navigation_cache = {}
        self._cache_ttl = 300  # 5 minutes

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
        import uuid
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
                print(f"[@ai_planner] Using cached context for {cache_key}")
                # Merge with current context (preserve current_node_id)
                cached_data = cached_data.copy()
                cached_data['current_node_id'] = context.get('current_node_id')
                return cached_data
        
        # Cache the context
        self._context_cache[cache_key] = (context, current_time)
        print(f"[@ai_planner] Cached context for {cache_key}")
        return context
    
    def _call_ai(self, prompt: str, context: Dict) -> Dict:
        """PRESERVE: All original sophisticated AI prompt logic"""
        available_nodes = context['available_nodes']
        available_actions = context['available_actions']
        available_verifications = context['available_verifications']
        device_model = context['device_model']
        current_node_id = context.get('current_node_id')
        current_node_label = context.get('current_node_label')
        
        print(f"[@ai_planner] _call_ai context: nodes={len(available_nodes)}, actions={len(available_actions)}, verifications={len(available_verifications)}, device_model={device_model}")
        
        # Use context as-is from services
        navigation_context = available_nodes
        action_context = available_actions
        verification_context = available_verifications
        
        # PRESERVE: All original sophisticated AI prompt
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
        print(f"[@ai_planner] AI Prompt (length: {len(ai_prompt)} chars):")
        print("=" * 80)
        print(repr(ai_prompt))
        print("=" * 80)

        # PRESERVE: All original AI call logic
        result = call_text_ai(
            prompt=ai_prompt,
            max_tokens=2000,
            temperature=0.0,
            model=AI_CONFIG['providers']['openrouter']['models']['agent']
        )

        print(f"[@ai_planner] AI Response received, content length: {len(result.get('content', '')) if result else 0} characters")

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
            
            print(f"[@ai_planner] Cleaned content: {repr(cleaned_content)}")
            
            # Parse JSON
            parsed_json = json.loads(cleaned_content)
            print(f"[@ai_planner] Successfully parsed JSON with keys: {list(parsed_json.keys())}")
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            print(f"[@ai_planner] JSON parsing error: {e}")
            print(f"[@ai_planner] Raw content: {repr(content)}")
            raise Exception(f"AI returned invalid JSON: {e}")
        except Exception as e:
            print(f"[@ai_planner] JSON extraction error: {e}")
            raise Exception(f"Failed to extract JSON from AI response: {e}")
    
    
    def clear_context_cache(self, device_model: str = None, userinterface_name: str = None):
        """PRESERVE: All original cache clearing logic"""
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
            
            print(f"[@ai_planner] Cleared context caches for model: {device_model}, interface: {userinterface_name}")
        else:
            # Clear all caches
            self._action_cache.clear()
            self._verification_cache.clear()
            self._navigation_cache.clear()
            self._context_cache.clear()
            print(f"[@ai_planner] Cleared all context caches")


class AIPlanner:
    """Global planner cache with all original caching features"""
    
    _instances = {}  # {team_id: AIPlanGenerator}
    
    @classmethod
    def get_instance(cls, team_id: str) -> AIPlanGenerator:
        """Get cached planner instance"""
        if team_id not in cls._instances:
            cls._instances[team_id] = AIPlanGenerator(team_id)
        return cls._instances[team_id]
    
    @classmethod
    def clear_cache(cls, team_id: str = None):
        """Clear planner cache"""
        if team_id:
            cls._instances.pop(team_id, None)
        else:
            cls._instances.clear()


class AITracker:
    """Global execution tracker with ALL original rich features preserved"""
    
    _executions = {}  # Class-level storage
    
    @classmethod
    def start_execution(cls, execution_id: str, plan_dict: Dict):
        """Track execution using plan dict directly"""
        cls._executions[execution_id] = {
            'plan': plan_dict,
            'status': 'executing',
            'current_step': 0,
            'step_results': [],
            'start_time': time.time(),
            'plan_generated_at': time.time()
        }
        
        # Plan generation log entry
        plan_steps = plan_dict.get('steps', [])
        plan_log_entry = {
            'timestamp': time.time(),
            'log_type': 'ai_plan',
            'action_type': 'plan_generated',
            'data': {
                'plan_id': plan_dict.get('id'),
                'feasible': plan_dict.get('feasible', True),
                'step_count': len(plan_steps),
                'analysis': plan_dict.get('analysis', '')
            },
            'value': plan_dict,  # Store dict directly
            'description': f'AI plan generated with {len(plan_steps)} steps'
        }
        
        cls._executions[execution_id]['execution_log'] = [plan_log_entry]
        print(f"[@ai_tracker] Started execution {execution_id} with plan, total tracked: {len(cls._executions)}")
    
    @classmethod
    def update_step_progress(cls, execution_id: str, step_number: int, step_result: Dict[str, Any]):
        """Update step progress in real-time"""
        if execution_id in cls._executions:
            execution = cls._executions[execution_id]
            execution['current_step'] = step_number
            execution['step_results'].append(step_result)
            
            # Add step log entry
            step_log_entry = {
                'timestamp': time.time(),
                'log_type': 'execution',
                'action_type': 'step_success' if step_result.get('success') else 'step_failed',
                'data': {
                    'step': step_number,
                    'duration': step_result.get('execution_time_ms', 0) / 1000.0
                },
                'description': step_result.get('message', '')
            }
            
            if 'execution_log' not in execution:
                execution['execution_log'] = []
            execution['execution_log'].append(step_log_entry)
            
            print(f"[@ai_tracker] Step {step_number} {'completed' if step_result.get('success') else 'failed'} for execution {execution_id}")
    
    @classmethod
    def complete_execution(cls, execution_id: str, result: ExecutionResult):
        """PRESERVE: All original completion tracking"""
        if execution_id in cls._executions:
            execution = cls._executions[execution_id]
            execution['status'] = 'completed' if result.success else 'failed'
            execution['result'] = result
            execution['end_time'] = time.time()
            
            # PRESERVE: Completion log entry
            total_duration = execution['end_time'] - execution['start_time']
            completion_log_entry = {
                'timestamp': time.time(),
                'log_type': 'execution',
                'action_type': 'task_completed' if result.success else 'task_failed',
                'data': {
                    'success': result.success,
                    'duration': total_duration,
                    'total_steps': len(result.step_results),
                    'successful_steps': len([r for r in result.step_results if r.get('success')]),
                    'failed_steps': len([r for r in result.step_results if not r.get('success')])
                },
                'value': {
                    'success': result.success,
                    'duration': total_duration,
                    'message': 'Task completed successfully' if result.success else (result.error or 'Task failed')
                },
                'description': 'Task completed successfully' if result.success else (result.error or 'Task failed')
            }
            
            if 'execution_log' not in execution:
                execution['execution_log'] = []
            execution['execution_log'].append(completion_log_entry)
    
    @classmethod
    def get_status(cls, execution_id: str) -> Dict:
        """PRESERVE: All original rich status reporting"""
        print(f"[@ai_tracker] Looking for execution {execution_id}, available: {list(cls._executions.keys())}")
        if execution_id not in cls._executions:
            return {'success': False, 'error': 'Execution not found'}

        execution = cls._executions[execution_id]
        plan = execution['plan']
        
        # PRESERVE: Rich execution log
        execution_log = execution.get('execution_log', [])
        if not execution_log and execution['step_results']:
            # Fallback: convert step_results to log entries
            execution_log = [cls._step_to_log_entry(r) for r in execution['step_results']]
        
        # Progress calculation using dict
        plan_steps = plan.get('steps', [])
        completed_steps = len([r for r in execution['step_results'] if r.get('success')])
        progress_percentage = (completed_steps / len(plan_steps)) * 100 if plan_steps else 0
        
        # Current step description
        current_step_desc = f"Step {execution['current_step']}/{len(plan_steps)}"
        if execution['status'] == 'executing' and int(execution['current_step']) > 0:
            current_step_desc = f"Executing step {execution['current_step']}"
        elif execution['status'] != 'executing':
            current_step_desc = "Task completed" if execution['status'] == 'completed' else "Task failed"

        return {
            'success': True,
            'is_executing': execution['status'] == 'executing',
            'current_step': current_step_desc,
            'execution_log': execution_log,
            'progress_percentage': min(progress_percentage, 100),
            
            # Return plan dict directly
            'plan': plan,
            'execution_summary': {
                'total_steps': len(plan_steps),
                'completed_steps': len([r for r in execution['step_results'] if r.get('success')]),
                'failed_steps': len([r for r in execution['step_results'] if not r.get('success')]),
                'start_time': execution['start_time'],
                'end_time': execution.get('end_time'),
                'total_duration': execution.get('end_time', time.time()) - execution['start_time']
            }
        }
    
    @classmethod
    def _step_to_log_entry(cls, step_result: Dict) -> Dict[str, Any]:
        """Convert step result to log entry"""
        return {
            'timestamp': time.time(),
            'log_type': 'execution',
            'action_type': 'step_success' if step_result.get('success') else 'step_failed',
            'data': {
                'step': step_result.get('step_id'),
                'duration': step_result.get('execution_time_ms', 0) / 1000.0
            },
            'description': step_result.get('message', '')
        }


class AISession:
    """Per-request execution session with ALL original features preserved"""
    
    def __init__(self, host: Dict, device_id: str, team_id: str):
        self.host = host
        self.device_id = device_id
        self.team_id = team_id
        self.execution_id = str(uuid.uuid4())
        
        # Cache device_model for efficiency
        from shared.lib.utils.build_url_utils import get_device_by_id
        device_dict = get_device_by_id(host, device_id)
        if not device_dict:
            raise Exception(f"Device {device_id} not found in host")
        self.device_model = device_dict.get('device_model')
        
        # PRESERVE: Current node tracking from shared positions
        position = AIDeviceTracker.get_position(device_id)
        self.current_node_id = position.get('node_id')
        self.current_node_label = position.get('node_label')
        
        print(f"[@ai_session] Initialized with device_id: {device_id}, device_model: {self.device_model}, current_node_id: {self.current_node_id}")
        
        # Create executors once per session (for execution, not context loading)
        from backend_core.src.services.actions.action_executor import ActionExecutor
        from backend_core.src.services.verifications.verification_executor import VerificationExecutor
        from backend_core.src.services.navigation.navigation_executor import NavigationExecutor
        
        self.action_executor = ActionExecutor(host, device_id, team_id)
        self.verification_executor = VerificationExecutor(host, device_id, team_id)
        self.navigation_executor = NavigationExecutor(host, device_id, team_id)
    
    def execute_task(self, prompt: str, userinterface_name: str, mode: ExecutionMode = ExecutionMode.REAL_TIME) -> str:
        """Execute AI task from prompt - generates plan and executes"""
        
        # Already there detection - return immediately
        target_node = self._extract_target_from_prompt(prompt)
        if target_node and target_node == self.current_node_id:
            print(f"[@ai_session] Already at target node '{target_node}' - no execution needed")
            return "already_there"
        
        # Load context using centralized service with cached device_model
        context = AIContextService.load_context(self.host, self.device_id, self.team_id, userinterface_name, self.device_model)
        context['current_node_id'] = self.current_node_id
        context['current_node_label'] = self.current_node_label
        
        # Generate plan dict with cached planner
        planner = AIPlanner.get_instance(self.team_id)
        plan_dict = planner.generate_plan(prompt, context, self.current_node_id)
        
        # Execute plan dict directly
        return self.execute_plan_dict(plan_dict, mode)
    
    def execute_plan_dict(self, plan_dict: Dict, mode: ExecutionMode = ExecutionMode.REAL_TIME) -> str:
        """UNIFIED: Execute plan dict - same for all execution paths"""
        
        # Start execution tracking
        AITracker.start_execution(self.execution_id, plan_dict)
        
        # Load context if not already loaded
        userinterface_name = plan_dict.get('userinterface_name', 'horizon_android_mobile')
        context = AIContextService.load_context(self.host, self.device_id, self.team_id, userinterface_name, self.device_model)
        context['current_node_id'] = self.current_node_id
        context['current_node_label'] = self.current_node_label
        
        # Execute with mode handling
        if mode == ExecutionMode.REAL_TIME:
            threading.Thread(target=self._execute_async_dict, args=(plan_dict, context)).start()
        else:
            result = self._execute_plan_dict(plan_dict, context)
            AITracker.complete_execution(self.execution_id, result)
            
            # Position tracking after successful execution
            if result.success:
                final_position = context.get('final_position_node_id')
                if final_position:
                    AIDeviceTracker.update_position(self.device_id, final_position)
                    self.current_node_id = final_position
                    print(f"[@ai_session] Updated current_node_id to: {self.current_node_id}")
        
        return self.execution_id
    
    def execute_stored_testcase(self, test_case_id: str) -> str:
        """Execute stored test case - uses unified dict execution"""
        from shared.lib.supabase.testcase_db import get_test_case
        
        # Load test case
        test_case = get_test_case(test_case_id, self.team_id)
        if not test_case:
            raise Exception(f"Test case {test_case_id} not found")
        
        # Get stored plan dict
        stored_plan = test_case.get('ai_plan')
        if not stored_plan:
            raise Exception("Test case missing ai_plan - old format not supported")
        
        # Execute stored plan dict directly - no reconstruction needed
        return self.execute_plan_dict(stored_plan, ExecutionMode.SCRIPT)
    
    def _execute_async_dict(self, plan_dict: Dict, context: Dict):
        """Execute plan dict asynchronously"""
        try:
            result = self._execute_plan_dict(plan_dict, context)
            AITracker.complete_execution(self.execution_id, result)
            
            # Position tracking for async execution
            if result.success:
                final_position = context.get('final_position_node_id')
                if final_position:
                    AIDeviceTracker.update_position(self.device_id, final_position)
        except Exception as e:
            error_result = ExecutionResult(
                plan_id=plan_dict.get('id', 'unknown'),
                success=False,
                step_results=[],
                total_time_ms=0,
                error=str(e)
            )
            AITracker.complete_execution(self.execution_id, error_result)
    
    def _execute_plan_dict(self, plan_dict: Dict, context: Dict) -> ExecutionResult:
        """UNIFIED: Execute plan dict - same for all execution paths"""
        start_time = time.time()
        step_results = []
        
        plan_steps = plan_dict.get('steps', [])
        for i, step_data in enumerate(plan_steps):
            step_number = step_data.get('step', i + 1)
            step_result = self._execute_step_dict(step_data, context)
            step_results.append(step_result)
            
            # Update real-time step progress
            AITracker.update_step_progress(self.execution_id, step_number, step_result)
            
            # Stop on first error logic
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
    
    def _execute_step_dict(self, step_data: Dict, context: Dict) -> Dict:
        """UNIFIED: Execute step dict - same for all execution paths"""
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
                # Position tracking
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
    
    def _extract_target_from_prompt(self, prompt: str) -> Optional[str]:
        """PRESERVE: Original regex logic for target extraction"""
        import re
        # Match patterns like "go to replay", "navigate to home", etc.
        match = re.search(r'(?:go to|navigate to|goto)\s+(\w+)', prompt.lower())
        return match.group(1) if match else None
    