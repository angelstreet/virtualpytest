"""
AI Central - Clean unified AI system
"""

import time
import json
import uuid
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from shared.lib.utils.ai_utils import call_text_ai, AI_CONFIG
from shared.lib.supabase.userinterface_db import get_userinterface_by_name, get_all_userinterfaces
from shared.lib.supabase.navigation_trees_db import get_root_tree_for_interface
from shared.lib.utils.navigation_cache import get_cached_unified_graph


class AIStepType(Enum):
    NAVIGATION = "navigation"
    ACTION = "action"
    VERIFICATION = "verification"
    WAIT = "wait"


class ExecutionMode(Enum):
    REAL_TIME = "real_time"
    TEST_CASE = "test_case"
    SCRIPT = "script"


@dataclass
class AIStep:
    step_id: int
    type: AIStepType
    command: str
    params: Dict[str, Any]
    description: str


@dataclass
class AIPlan:
    id: str
    prompt: str
    analysis: str
    feasible: bool
    steps: List[AIStep]
    userinterface_name: str


@dataclass
class ExecutionOptions:
    mode: ExecutionMode
    context: Dict[str, Any]
    enable_db_tracking: bool = False
    stop_on_first_error: bool = True


@dataclass
class StepResult:
    step_id: int
    success: bool
    message: str
    execution_time_ms: int


@dataclass
class ExecutionResult:
    plan_id: str
    success: bool
    step_results: List[StepResult]
    total_time_ms: int
    error: Optional[str] = None


class AIPlanGenerator:
    def __init__(self, team_id: str):
        self.team_id = team_id
        # Context caching to avoid repeated expensive operations
        self._context_cache = {}
        self._action_cache = {}
        self._verification_cache = {}
        self._navigation_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL

    def generate_plan(self, prompt: str, userinterface_name: str, device_id: str = None) -> AIPlan:
        context = self._load_context(userinterface_name, device_id)
        ai_response = self._call_ai(prompt, context)
        return self._convert_to_plan(prompt, ai_response, userinterface_name)

    def analyze_compatibility(self, prompt: str) -> Dict[str, Any]:
        interfaces = get_all_userinterfaces(self.team_id)
        compatible = []
        incompatible = []

        for interface in interfaces:
            try:
                plan = self.generate_plan(prompt, interface['name'])
                if plan.feasible:
                    compatible.append({
                        'userinterface_name': interface['name'],
                        'reasoning': plan.analysis
                    })
                else:
                    incompatible.append({
                        'userinterface_name': interface['name'],
                        'reasoning': plan.analysis
                    })
            except Exception as e:
                incompatible.append({
                    'userinterface_name': interface['name'],
                    'reasoning': f'Analysis failed: {str(e)}'
                })

        return {
            'compatible_interfaces': compatible,
            'incompatible_interfaces': incompatible,
            'compatible_count': len(compatible)
        }

    def _load_context(self, userinterface_name: str, device_id: str = None) -> Dict[str, Any]:
        """Load context for AI planning by asking services for their available context"""
        import time
        
        # Check cache first
        cache_key = f"{userinterface_name}:{device_id}"
        current_time = time.time()
        
        if cache_key in self._context_cache:
            cached_data, cache_time = self._context_cache[cache_key]
            if current_time - cache_time < self._cache_ttl:
                print(f"[@ai_central] Using cached context for interface: {userinterface_name}, device: {device_id}")
                return cached_data
        
        try:
            from shared.lib.utils.host_utils import get_device_by_id
            from backend_core.src.services.actions.action_executor import ActionExecutor
            from backend_core.src.services.verifications.verification_executor import VerificationExecutor
            from backend_core.src.services.navigation.navigation_executor import NavigationExecutor
            
            print(f"[@ai_central] Loading context from services for interface: {userinterface_name}, device: {device_id}")
            
            # Get device model for context
            device_model = None
            if device_id:
                device = get_device_by_id(device_id)
                if device:
                    device_model = device.get('device_model', 'unknown')
                    print(f"[@ai_central] Retrieved device model: {device_model} for device: {device_id}")
                else:
                    print(f"[@ai_central] Warning: Device not found for device_id: {device_id}")
            else:
                print(f"[@ai_central] Warning: No device_id provided for context loading")
            
            # Initialize service executors with minimal host info for context loading
            host_info = {'host_name': 'context_loading'}
            
            # Get context from each service
            action_executor = ActionExecutor(host=host_info, device_id=device_id, team_id=self.team_id)
            verification_executor = VerificationExecutor(host=host_info, device_id=device_id, team_id=self.team_id)
            navigation_executor = NavigationExecutor(host=host_info, device_id=device_id, team_id=self.team_id)
            
            # Load context from each service with individual caching
            action_context = self._get_cached_action_context(action_executor, device_model, userinterface_name)
            verification_context = self._get_cached_verification_context(verification_executor, device_model, userinterface_name)
            navigation_context = self._get_cached_navigation_context(navigation_executor, device_model, userinterface_name)
            
            # Separate contexts for clean AI prioritization
            available_actions = action_context.get('available_actions', [])
            available_verifications = verification_context.get('available_verifications', [])
            available_nodes = navigation_context.get('available_nodes', [])
            tree_id = navigation_context.get('tree_id')
            
            print(f"[@ai_central] Loaded context from services:")
            print(f"  - Actions: {len(available_actions)}")
            print(f"  - Verifications: {len(available_verifications)}")
            print(f"  - Navigation nodes: {len(available_nodes)} (tree_id: {tree_id})")
            
            # Ensure navigation tree is cached for execution
            if tree_id and available_nodes:
                try:
                    from shared.lib.utils.navigation_cache import get_cached_graph
                    cached_graph = get_cached_graph(tree_id, self.team_id)
                    if cached_graph:
                        print(f"[@ai_central] Navigation tree cached successfully for tree_id: {tree_id}")
                    else:
                        print(f"[@ai_central] Warning: Navigation tree not cached for tree_id: {tree_id}")
                except Exception as e:
                    print(f"[@ai_central] Error checking navigation cache: {e}")
            
            # Create context result
            context_result = {
                'userinterface_name': userinterface_name,
                'tree_id': tree_id,
                'available_nodes': available_nodes,
                'available_actions': available_actions,
                'available_verifications': available_verifications,
                'device_id': device_id,
                'device_model': device_model
            }
            
            # Cache the result
            self._context_cache[cache_key] = (context_result, current_time)
            print(f"[@ai_central] Context cached for interface: {userinterface_name}, device: {device_id}")
            
            return context_result
            
        except Exception as e:
            print(f"[@ai_central] Error loading context from services: {e}")
            return {
                'userinterface_name': userinterface_name,
                'tree_id': None,
                'available_nodes': [],
                'available_actions': [],
                'available_verifications': [],
                'device_id': device_id,
                'device_model': None
            }

    def _get_cached_action_context(self, action_executor, device_model: str, userinterface_name: str) -> Dict[str, Any]:
        """Get action context with caching per device_model/userinterface"""
        import time
        
        cache_key = f"action:{device_model}:{userinterface_name}"
        current_time = time.time()
        
        if cache_key in self._action_cache:
            cached_data, cache_time = self._action_cache[cache_key]
            if current_time - cache_time < self._cache_ttl:
                print(f"[@ai_central] Using cached action context for model: {device_model}, interface: {userinterface_name}")
                return cached_data
        
        print(f"[@ai_central] Loading fresh action context for model: {device_model}, interface: {userinterface_name}")
        action_context = action_executor.get_available_context(device_model, userinterface_name)
        self._action_cache[cache_key] = (action_context, current_time)
        return action_context

    def _get_cached_verification_context(self, verification_executor, device_model: str, userinterface_name: str) -> Dict[str, Any]:
        """Get verification context with caching per device_model/userinterface"""
        import time
        
        cache_key = f"verification:{device_model}:{userinterface_name}"
        current_time = time.time()
        
        if cache_key in self._verification_cache:
            cached_data, cache_time = self._verification_cache[cache_key]
            if current_time - cache_time < self._cache_ttl:
                print(f"[@ai_central] Using cached verification context for model: {device_model}, interface: {userinterface_name}")
                return cached_data
        
        print(f"[@ai_central] Loading fresh verification context for model: {device_model}, interface: {userinterface_name}")
        verification_context = verification_executor.get_available_context(device_model, userinterface_name)
        self._verification_cache[cache_key] = (verification_context, current_time)
        return verification_context

    def _get_cached_navigation_context(self, navigation_executor, device_model: str, userinterface_name: str) -> Dict[str, Any]:
        """Get navigation context with caching per device_model/userinterface"""
        import time
        
        cache_key = f"navigation:{device_model}:{userinterface_name}"
        current_time = time.time()
        
        if cache_key in self._navigation_cache:
            cached_data, cache_time = self._navigation_cache[cache_key]
            if current_time - cache_time < self._cache_ttl:
                print(f"[@ai_central] Using cached navigation context for model: {device_model}, interface: {userinterface_name}")
                return cached_data
        
        print(f"[@ai_central] Loading fresh navigation context for model: {device_model}, interface: {userinterface_name}")
        navigation_context = navigation_executor.get_available_context(device_model, userinterface_name)
        self._navigation_cache[cache_key] = (navigation_context, current_time)
        return navigation_context

    def clear_context_cache(self, device_model: str = None, userinterface_name: str = None):
        """Clear context caches - optionally for specific device_model/userinterface"""
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
            
            print(f"[@ai_central] Cleared context caches for model: {device_model}, interface: {userinterface_name}")
        else:
            # Clear all caches
            self._action_cache.clear()
            self._verification_cache.clear()
            self._navigation_cache.clear()
            self._context_cache.clear()
            print(f"[@ai_central] Cleared all context caches")

    def _call_ai(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        available_nodes = context.get('available_nodes', [])
        available_actions = context.get('available_actions', [])
        available_verifications = context.get('available_verifications', [])
        device_model = context.get('device_model', 'unknown')
        
        # Build navigation context (prioritized)
        navigation_context = ""
        if available_nodes:
            navigation_context = f"Navigation: Nodes label used to navigate in app with navigation function\n{available_nodes}"
        
        # Build action commands (secondary)
        action_commands = []
        if available_actions:
            # Limit actions to avoid token overflow
            for action in available_actions[:10]:  # Max 10 actions
                cmd = action['command']
                action_type = action.get('action_type', 'remote')
                description = action.get('description', '')
                command_str = f"{cmd}({action_type}): {description}" if description else f"{cmd}({action_type})"
                action_commands.append(command_str)
        
        # Build verification commands (tertiary)
        verification_commands = []
        if available_verifications:
            # Limit verifications to avoid token overflow
            for verification in available_verifications[:5]:  # Max 5 verifications
                cmd = verification['command']
                action_type = verification.get('action_type', 'verification')
                description = verification.get('description', '')
                command_str = f"{cmd}({action_type}): {description}" if description else f"{cmd}({action_type})"
                verification_commands.append(command_str)
        
        # Build action context (secondary)
        action_context = ""
        if action_commands:
            action_context = f"Action: Actions available to control the device\n{', '.join(action_commands)}"
        
        # Build verification context (tertiary)
        verification_context = ""
        if verification_commands:
            verification_context = f"Verification: Verification available to check the device\n{', '.join(verification_commands)}"
        
        # Create comprehensive AI prompt
        ai_prompt = f"""You are controlling a TV application on a device ({device_model}).
Your task is to navigate through the app using available commands provided.

Task: "{prompt}"
Device: {device_model}

Navigation System: Apps have hierarchical menus (home_replay, home_movies, etc.) - navigate to parent menu first, then use OK/select to enter submenu.
If target node doesn't exist, find closest parent menu and navigate there, then use action commands to reach the final destination.

{navigation_context}

{action_context}

{verification_context}
Rules:
- "go to node X" → execute_navigation, target_node="X"
- "click X" → click_element, element_id="X"  
- "press X" → press_key, key="X"
- PRIORITIZE navigation over manual actions
- ALWAYS specify action_type in params

CRITICAL: You MUST include an "analysis" field explaining your reasoning.

Example response format:
{{"analysis": "Task requires navigating to live content. Since 'live' node is available, I'll navigate there directly.", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "live", "action_type": "navigation"}}, "description": "Navigate to live content"}}]}}

If task is not possible:
{{"analysis": "Task cannot be completed because the requested node does not exist in the navigation tree.", "feasible": false, "plan": []}}

RESPOND WITH JSON ONLY. ANALYSIS FIELD IS REQUIRED:"""

        result = call_text_ai(
            prompt=ai_prompt,
            max_tokens=1500,
            temperature=0.0,
            model=AI_CONFIG['providers']['openrouter']['models']['agent']
        )

        if not result.get('success'):
            raise Exception(f"AI call failed: {result.get('error')}")

        # Extract JSON from AI response with protective parsing
        return self._extract_json_from_ai_response(result['content'])

    def _extract_json_from_ai_response(self, content: str) -> Dict[str, Any]:
        """Extract JSON from AI response using existing codebase pattern"""
        try:
            print(f"[@ai_central] Raw AI response: {repr(content)}")
            
            # Use existing codebase pattern (same as ai_utils.py, video_ai_helpers.py, ai_analyzer.py)
            cleaned_content = content.strip()
            
            # Handle markdown code blocks
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content.replace('```json', '').replace('```', '').strip()
            elif cleaned_content.startswith('```'):
                cleaned_content = cleaned_content.replace('```', '').strip()
            
            print(f"[@ai_central] Cleaned content: {repr(cleaned_content)}")
            
            # Parse JSON
            parsed_json = json.loads(cleaned_content)
            print(f"[@ai_central] Successfully parsed JSON with keys: {list(parsed_json.keys())}")
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            print(f"[@ai_central] JSON parsing error: {e}")
            print(f"[@ai_central] Raw content: {repr(content)}")
            raise Exception(f"AI returned invalid JSON: {e}")
        except Exception as e:
            print(f"[@ai_central] JSON extraction error: {e}")
            raise Exception(f"Failed to extract JSON from AI response: {e}")

    def _convert_to_plan(self, prompt: str, ai_response: Dict, userinterface_name: str) -> AIPlan:
        steps = []
        for i, step_data in enumerate(ai_response.get('plan', [])):
            step_type = self._get_step_type(step_data.get('command'))
            
            # Extract params and ensure action_type is included
            params = step_data.get('params', {})
            
            # If action_type is provided at step level, add it to params
            if 'action_type' in step_data and 'action_type' not in params:
                params['action_type'] = step_data['action_type']
            
            steps.append(AIStep(
                step_id=i + 1,
                type=step_type,
                command=step_data.get('command'),
                params=params,
                description=step_data.get('description', '')
            ))

        return AIPlan(
            id=str(uuid.uuid4()),
            prompt=prompt,
            analysis=ai_response.get('analysis', ''),
            feasible=ai_response.get('feasible', True),
            steps=steps,
            userinterface_name=userinterface_name
        )

    def _get_step_type(self, command: str) -> AIStepType:
        if command == 'execute_navigation':
            return AIStepType.NAVIGATION
        elif command in ['press_key', 'click_element', 'input_text']:
            return AIStepType.ACTION
        elif command.startswith('verify_') or command.startswith('check_'):
            return AIStepType.VERIFICATION
        elif command == 'wait':
            return AIStepType.WAIT
        else:
            return AIStepType.ACTION


class AIOrchestrator:
    def __init__(self, host: Dict, device_id: str, team_id: str, tracker: 'AITracker' = None):
        self.host = host
        self.device_id = device_id
        self.team_id = team_id
        self.tracker = tracker

    def execute_plan(self, plan: AIPlan, options: ExecutionOptions, execution_id: str = None) -> ExecutionResult:
        start_time = time.time()
        step_results = []

        for step in plan.steps:
            step_result = self._execute_step(step, options)
            step_results.append(step_result)
            
            # Update tracker if available and execution_id provided
            if self.tracker and execution_id:
                self.tracker.update_step(execution_id, step_result)

            if not step_result.success and options.stop_on_first_error:
                break

        total_time = int((time.time() - start_time) * 1000)
        success = all(r.success for r in step_results)

        return ExecutionResult(
            plan_id=plan.id,
            success=success,
            step_results=step_results,
            total_time_ms=total_time,
            error=None if success else "One or more steps failed"
        )

    def _execute_step(self, step: AIStep, options: ExecutionOptions) -> StepResult:
        start_time = time.time()

        try:
            if step.type == AIStepType.NAVIGATION:
                result = self._execute_navigation(step, options)
            elif step.type == AIStepType.ACTION:
                result = self._execute_action(step, options)
            elif step.type == AIStepType.VERIFICATION:
                result = self._execute_verification(step, options)
            elif step.type == AIStepType.WAIT:
                result = self._execute_wait(step)
            else:
                result = {'success': False, 'error': f'Unknown step type: {step.type}'}

            execution_time = int((time.time() - start_time) * 1000)
            
            return StepResult(
                step_id=step.step_id,
                success=result.get('success', False),
                message=result.get('message', step.description),
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return StepResult(
                step_id=step.step_id,
                success=False,
                message=str(e),
                execution_time_ms=execution_time
            )

    def _execute_navigation(self, step: AIStep, options: ExecutionOptions) -> Dict[str, Any]:
        from backend_core.src.services.navigation.navigation_executor import NavigationExecutor
        
        executor = NavigationExecutor(self.host, self.device_id, self.team_id)
        
        return executor.execute_navigation(
            tree_id=options.context.get('tree_id'),
            target_node_id=step.params.get('target_node'),
            current_node_id=options.context.get('current_node_id')
        )

    def _execute_action(self, step: AIStep, options: ExecutionOptions) -> Dict[str, Any]:
        from backend_core.src.services.actions.action_executor import ActionExecutor
        
        executor = ActionExecutor(
            host=self.host,
            device_id=self.device_id,
            tree_id=options.context.get('tree_id'),
            edge_id=options.context.get('edge_id'),
            team_id=self.team_id
        )

        # Extract action_type from params or use intelligent detection
        action_type = step.params.get('action_type')
        
        # If no action_type specified, let the action executor handle intelligent detection
        action = {
            'command': step.command,
            'params': step.params,
            'action_type': action_type  # Let action executor handle None case
        }

        return executor.execute_actions([action])

    def _execute_verification(self, step: AIStep, options: ExecutionOptions) -> Dict[str, Any]:
        from backend_core.src.services.verifications.verification_executor import VerificationExecutor
        
        executor = VerificationExecutor(
            host=self.host,
            device_id=self.device_id,
            tree_id=options.context.get('tree_id'),
            node_id=options.context.get('node_id'),
            team_id=self.team_id
        )

        verification = {
            'verification_type': step.params.get('verification_type', 'text'),
            'command': step.command,
            'params': step.params
        }

        return executor.execute_verifications([verification])

    def _execute_wait(self, step: AIStep) -> Dict[str, Any]:
        duration_ms = step.params.get('duration', 1000)
        time.sleep(duration_ms / 1000.0)
        return {'success': True, 'message': f'Waited {duration_ms}ms'}


class AITracker:
    # Class-level shared executions dictionary for persistence across instances
    _shared_executions = {}
    
    def __init__(self):
        # All instances share the same executions dictionary
        self.executions = AITracker._shared_executions

    def start_execution(self, execution_id: str, plan: AIPlan):
        self.executions[execution_id] = {
            'plan': plan,
            'status': 'executing',
            'current_step': 0,
            'step_results': [],
            'start_time': time.time(),
            'plan_generated_at': time.time()
        }
        
        # Add plan generation log entry
        plan_log_entry = {
            'timestamp': time.time(),
            'log_type': 'ai_plan',
            'action_type': 'plan_generated',
            'data': {
                'plan_id': plan.id,
                'feasible': plan.feasible,
                'step_count': len(plan.steps),
                'analysis': plan.analysis
            },
            'value': {
                'id': plan.id,
                'prompt': plan.prompt,
                'analysis': plan.analysis,
                'feasible': plan.feasible,
                'steps': [
                    {
                        'step': step.step_id,
                        'type': step.type.value,
                        'command': step.command,
                        'params': step.params,
                        'description': step.description
                    }
                    for step in plan.steps
                ]
            },
            'description': f'AI plan generated with {len(plan.steps)} steps'
        }
        
        # Initialize with plan generation entry
        self.executions[execution_id]['execution_log'] = [plan_log_entry]
        print(f"[@ai_tracker] Started execution {execution_id} with plan, total tracked: {len(self.executions)}")

    def update_step(self, execution_id: str, step_result: StepResult):
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            execution['current_step'] = step_result.step_id
            execution['step_results'].append(step_result)
            
            # Add step log entry to execution_log
            step_log_entry = {
                'timestamp': time.time(),
                'log_type': 'execution',
                'action_type': 'step_success' if step_result.success else 'step_failed',
                'data': {
                    'step': step_result.step_id,
                    'duration': step_result.execution_time_ms / 1000.0,
                    'success': step_result.success,
                    'command': getattr(step_result, 'command', ''),
                    'description': step_result.message
                },
                'value': {
                    'step': step_result.step_id,
                    'duration': step_result.execution_time_ms / 1000.0,
                    'success': step_result.success,
                    'message': step_result.message
                },
                'description': step_result.message
            }
            
            # Append to execution log
            if 'execution_log' not in execution:
                execution['execution_log'] = []
            execution['execution_log'].append(step_log_entry)

    def complete_execution(self, execution_id: str, result: ExecutionResult):
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            execution['status'] = 'completed' if result.success else 'failed'
            execution['result'] = result
            execution['end_time'] = time.time()
            
            # Calculate total duration
            total_duration = execution['end_time'] - execution['start_time']
            
            # Add task completion log entry
            completion_log_entry = {
                'timestamp': time.time(),
                'log_type': 'execution',
                'action_type': 'task_completed' if result.success else 'task_failed',
                'data': {
                    'success': result.success,
                    'duration': total_duration,
                    'total_steps': len(execution['step_results']),
                    'successful_steps': len([r for r in execution['step_results'] if r.success]),
                    'failed_steps': len([r for r in execution['step_results'] if not r.success])
                },
                'value': {
                    'success': result.success,
                    'duration': total_duration,
                    'message': 'Task completed successfully' if result.success else (result.error or 'Task failed')
                },
                'description': 'Task completed successfully' if result.success else (result.error or 'Task failed')
            }
            
            # Append to execution log
            if 'execution_log' not in execution:
                execution['execution_log'] = []
            execution['execution_log'].append(completion_log_entry)

    def get_status(self, execution_id: str) -> Dict[str, Any]:
        print(f"[@ai_tracker] Looking for execution {execution_id}, available: {list(self.executions.keys())}")
        if execution_id not in self.executions:
            return {'success': False, 'error': 'Execution not found'}

        execution = self.executions[execution_id]
        plan = execution['plan']
        
        # Use the rich execution_log if available, otherwise fall back to step_results
        execution_log = execution.get('execution_log', [])
        if not execution_log and execution['step_results']:
            # Fallback: convert step_results to log entries
            execution_log = [self._step_to_log_entry(r) for r in execution['step_results']]

        # Calculate progress
        completed_steps = len([r for r in execution['step_results'] if r.success or not r.success])  # All attempted steps
        progress_percentage = (completed_steps / len(plan.steps)) * 100 if plan.steps else 0
        
        # Current step description
        current_step_desc = f"Step {execution['current_step']}/{len(plan.steps)}"
        if execution['status'] == 'executing' and execution['current_step'] > 0:
            current_step_desc = f"Executing step {execution['current_step']}"
        elif execution['status'] != 'executing':
            current_step_desc = "Task completed" if execution['status'] == 'completed' else "Task failed"

        return {
            'success': True,
            'is_executing': execution['status'] == 'executing',
            'current_step': current_step_desc,
            'execution_log': execution_log,
            'progress_percentage': min(progress_percentage, 100),  # Cap at 100%
            
            # Additional rich data for enhanced UX
            'plan': {
                'id': plan.id,
                'prompt': plan.prompt,
                'analysis': plan.analysis,
                'feasible': plan.feasible,
                'steps': [
                    {
                        'step': step.step_id,
                        'type': step.type.value,
                        'command': step.command,
                        'params': step.params,
                        'description': step.description
                    }
                    for step in plan.steps
                ]
            },
            'execution_summary': {
                'total_steps': len(plan.steps),
                'completed_steps': len([r for r in execution['step_results'] if r.success]),
                'failed_steps': len([r for r in execution['step_results'] if not r.success]),
                'start_time': execution['start_time'],
                'end_time': execution.get('end_time'),
                'total_duration': execution.get('end_time', time.time()) - execution['start_time']
            }
        }

    def _step_to_log_entry(self, step_result: StepResult) -> Dict[str, Any]:
        return {
            'timestamp': time.time(),
            'log_type': 'execution',
            'action_type': 'step_success' if step_result.success else 'step_failed',
            'data': {
                'step': step_result.step_id,
                'duration': step_result.execution_time_ms / 1000.0
            },
            'description': step_result.message
        }


class AICentral:
    def __init__(self, team_id: str, host: Dict = None, device_id: str = None):
        self.team_id = team_id
        self.host = host
        self.device_id = device_id
        
        self.planner = AIPlanGenerator(team_id)
        self.tracker = AITracker()
        
        # Track current node like the old system
        self.current_node_id = None
        self.orchestrator = AIOrchestrator(host, device_id, team_id, self.tracker) if host else None

    def analyze_compatibility(self, prompt: str) -> Dict[str, Any]:
        return self.planner.analyze_compatibility(prompt)

    def generate_plan(self, prompt: str, userinterface_name: str, device_id: str = None) -> AIPlan:
        return self.planner.generate_plan(prompt, userinterface_name, device_id or self.device_id)

    def execute_plan(self, plan: AIPlan, options: ExecutionOptions) -> str:
        if not self.orchestrator:
            raise ValueError("Cannot execute without host/device")

        execution_id = str(uuid.uuid4())
        self.tracker.start_execution(execution_id, plan)

        if options.mode == ExecutionMode.REAL_TIME:
            threading.Thread(
                target=self._execute_async,
                args=(execution_id, plan, options)
            ).start()
        else:
            result = self.orchestrator.execute_plan(plan, options, execution_id)
            self.tracker.complete_execution(execution_id, result)

        return execution_id

    def _execute_async(self, execution_id: str, plan: AIPlan, options: ExecutionOptions):
        try:
            result = self.orchestrator.execute_plan(plan, options, execution_id)
            self.tracker.complete_execution(execution_id, result)
        except Exception as e:
            error_result = ExecutionResult(
                plan_id=plan.id,
                success=False,
                step_results=[],
                total_time_ms=0,
                error=str(e)
            )
            self.tracker.complete_execution(execution_id, error_result)

    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        return self.tracker.get_status(execution_id)
    
    def update_current_node(self, node_id: str):
        """Update the current node position for navigation context"""
        self.current_node_id = node_id
        print(f"[@ai_central] Current node updated to: {node_id}")

    def execute_task(self, prompt: str, userinterface_name: str, options: ExecutionOptions) -> str:
        # Generate plan with device context
        plan = self.generate_plan(prompt, userinterface_name, self.device_id)
        
        # Load context to get tree_id for execution
        context = self.planner._load_context(userinterface_name, self.device_id)
        tree_id = context.get('tree_id')
        device_model = context.get('device_model')
        
        # Update execution options with the correct context
        options.context['tree_id'] = tree_id
        options.context['device_model'] = device_model
        options.context['current_node_id'] = self.current_node_id
        print(f"[@ai_central] Updated execution context with tree_id: {tree_id}, device_model: {device_model}, current_node: {self.current_node_id}")
        
        return self.execute_plan(plan, options)
