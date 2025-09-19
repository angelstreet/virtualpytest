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
        # Use the same working approach as the old AI agent
        try:
            from shared.lib.utils.navigation_utils import load_navigation_tree_with_hierarchy
            
            print(f"[@ai_central] Loading unified navigation tree hierarchy for: {userinterface_name}")
            tree_result = load_navigation_tree_with_hierarchy(userinterface_name, "ai_central")
            
            if not tree_result.get('success'):
                raise ValueError(f"Failed to load navigation tree for {userinterface_name}: {tree_result.get('error')}")
            
            tree_id = tree_result.get('tree_id')
            if not tree_id:
                raise ValueError(f"No tree_id returned for {userinterface_name}")
            
            print(f"[@ai_central] Successfully loaded unified navigation tree for: {userinterface_name}")
            print(f"[@ai_central] Unified cache populated with {tree_result.get('unified_graph_nodes', 0)} nodes, {tree_result.get('unified_graph_edges', 0)} edges")
            
            # Now we can safely get the cached unified graph
            from shared.lib.utils.navigation_cache import get_cached_unified_graph
            unified_graph = get_cached_unified_graph(tree_id, self.team_id)
            
            if not unified_graph:
                raise ValueError(f"Unified graph not found in cache for {userinterface_name}")
            
            # Extract available nodes from the unified graph
            available_nodes = []
            if unified_graph.nodes:
                for node_id in unified_graph.nodes:
                    node_data = unified_graph.nodes[node_id]
                    label = node_data.get('label')
                    if label:
                        available_nodes.append(label)
            
            print(f"[@ai_central] Extracted {len(available_nodes)} navigation nodes from unified cache")
            
            # Load minimal device actions directly from controllers if device_id is provided
            device_actions = []
            if device_id:
                try:
                    from shared.lib.utils.host_utils import get_device_by_id, get_controller
                    
                    print(f"[@ai_central] Loading minimal actions from controllers for device: {device_id}")
                    device = get_device_by_id(device_id)
                    
                    if device:
                        # Get actions from each controller type
                        controller_types = ['remote', 'web', 'desktop_bash', 'desktop_pyautogui', 'av', 'power']
                        
                        for controller_type in controller_types:
                            try:
                                controller = get_controller(device_id, controller_type)
                                if controller and hasattr(controller, 'get_available_actions'):
                                    actions = controller.get_available_actions()
                                    if isinstance(actions, dict):
                                        for category, action_list in actions.items():
                                            if isinstance(action_list, list):
                                                for action in action_list:
                                                    device_actions.append({
                                                        'command': action.get('command', ''),
                                                        'action_type': action.get('action_type', controller_type.replace('desktop_', 'desktop')),
                                                        'params': action.get('params', {})
                                                    })
                                    elif isinstance(actions, list):
                                        for action in actions:
                                            device_actions.append({
                                                'command': action.get('command', ''),
                                                'action_type': action.get('action_type', controller_type.replace('desktop_', 'desktop')),
                                                'params': action.get('params', {})
                                            })
                            except Exception as e:
                                print(f"[@ai_central] Could not load {controller_type} actions: {e}")
                                continue
                        
                        # Get verification actions from verification controllers
                        verification_types = ['image', 'text', 'adb', 'appium', 'video', 'audio']
                        for v_type in verification_types:
                            try:
                                controller = get_controller(device_id, f'verification_{v_type}')
                                if controller and hasattr(controller, 'get_available_verifications'):
                                    verifications = controller.get_available_verifications()
                                    if isinstance(verifications, list):
                                        for verification in verifications:
                                            device_actions.append({
                                                'command': verification.get('command', ''),
                                                'action_type': 'verification',
                                                'params': verification.get('params', {})
                                            })
                            except Exception as e:
                                print(f"[@ai_central] Could not load verification_{v_type} actions: {e}")
                                continue
                    
                    print(f"[@ai_central] Loaded {len(device_actions)} minimal actions from controllers")
                    
                except Exception as e:
                    print(f"[@ai_central] Warning: Could not load controller actions for device {device_id}: {e}")
                    # Continue without device actions - fallback to basic functionality
            
            return {
                'userinterface_name': userinterface_name,
                'tree_id': tree_id,
                'available_nodes': available_nodes,
                'device_actions': device_actions,
                'device_id': device_id
            }
            
        except ImportError as e:
            raise ValueError(f"Navigation system import error for {userinterface_name}: {e}")
        except Exception as e:
            error_str = str(e)
            if "NavigationTreeError" in error_str or "UnifiedCacheError" in error_str:
                raise ValueError(f"Navigation system error for {userinterface_name}: {e}")
            else:
                raise ValueError(f"Error loading unified navigation tree for {userinterface_name}: {e}")

    def _call_ai(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        available_nodes = context['available_nodes']
        device_actions = context.get('device_actions', [])
        
        # Build minimal action list - just command names and action_type
        action_list = []
        if device_actions:
            # Group by action_type for clarity
            actions_by_type = {}
            for action in device_actions:
                action_type = action.get('action_type', 'remote')
                if action_type not in actions_by_type:
                    actions_by_type[action_type] = []
                actions_by_type[action_type].append(action['command'])
            
            # Create minimal action list
            for action_type, commands in actions_by_type.items():
                # Limit to 8 most common commands per type to avoid token overflow
                limited_commands = commands[:8]
                action_list.append(f"{action_type}: {', '.join(limited_commands)}")
        
        # Create minimal AI prompt
        ai_prompt = f"""Task: "{prompt}"

Available nodes: {available_nodes}
Available actions: {' | '.join(action_list) if action_list else 'click_element, press_key, input_text'}

Rules:
- "navigate to X" → execute_navigation, target_node="X"
- Always specify action_type (remote, web, desktop, av, power)

Response format:
{{"analysis": "reasoning", "feasible": true/false, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "home"}}, "description": "Navigate to home"}}]}}"""

        result = call_text_ai(
            prompt=ai_prompt,
            max_tokens=1500,
            temperature=0.0,
            model=AI_CONFIG['providers']['openrouter']['models']['agent']
        )

        if not result.get('success'):
            raise Exception(f"AI call failed: {result.get('error')}")

        return json.loads(result['content'])

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
        from backend_core.src.services.navigation.navigation_execution import NavigationExecutor
        
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

    def execute_task(self, prompt: str, userinterface_name: str, options: ExecutionOptions) -> str:
        # Generate plan with device context
        plan = self.generate_plan(prompt, userinterface_name, self.device_id)
        
        # Load context to get tree_id for execution
        context = self.planner._load_context(userinterface_name, self.device_id)
        tree_id = context.get('tree_id')
        
        # Update execution options with the correct tree_id
        options.context['tree_id'] = tree_id
        print(f"[@ai_central] Updated execution context with tree_id: {tree_id}")
        
        return self.execute_plan(plan, options)
