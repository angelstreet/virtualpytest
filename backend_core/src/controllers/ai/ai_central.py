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

    def generate_plan(self, prompt: str, userinterface_name: str) -> AIPlan:
        context = self._load_context(userinterface_name)
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

    def _load_context(self, userinterface_name: str) -> Dict[str, Any]:
        userinterface_info = get_userinterface_by_name(userinterface_name, self.team_id)
        if not userinterface_info:
            raise ValueError(f"Userinterface {userinterface_name} not found")

        root_tree = get_root_tree_for_interface(userinterface_info['userinterface_id'], self.team_id)
        if not root_tree:
            raise ValueError(f"No root tree found for {userinterface_name}")

        unified_graph = get_cached_unified_graph(root_tree['tree_id'], self.team_id)
        if not unified_graph:
            raise ValueError(f"No navigation graph found for {userinterface_name}")

        available_nodes = []
        if unified_graph.nodes:
            for node_id in unified_graph.nodes:
                node_data = unified_graph.nodes[node_id]
                label = node_data.get('label')
                if label:
                    available_nodes.append(label)

        return {
            'userinterface_name': userinterface_name,
            'tree_id': root_tree['tree_id'],
            'available_nodes': available_nodes
        }

    def _call_ai(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        available_nodes = context['available_nodes']
        
        ai_prompt = f"""Task: "{prompt}"
Available nodes: {available_nodes}

Rules:
- Use only nodes from the available list
- "navigate to X" → execute_navigation, target_node="X"
- "press X" → press_key, key="X"
- "click X" → click_element, element_id="X"
- "wait X seconds" → wait, duration={1000}

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
            steps.append(AIStep(
                step_id=i + 1,
                type=step_type,
                command=step_data.get('command'),
                params=step_data.get('params', {}),
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
    def __init__(self, host: Dict, device_id: str, team_id: str):
        self.host = host
        self.device_id = device_id
        self.team_id = team_id

    def execute_plan(self, plan: AIPlan, options: ExecutionOptions) -> ExecutionResult:
        start_time = time.time()
        step_results = []

        for step in plan.steps:
            step_result = self._execute_step(step, options)
            step_results.append(step_result)

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

        action = {
            'command': step.command,
            'params': step.params,
            'action_type': step.params.get('action_type', 'remote')
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
    def __init__(self):
        self.executions = {}

    def start_execution(self, execution_id: str, plan: AIPlan):
        self.executions[execution_id] = {
            'plan': plan,
            'status': 'executing',
            'current_step': 0,
            'step_results': [],
            'start_time': time.time()
        }

    def update_step(self, execution_id: str, step_result: StepResult):
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            execution['current_step'] = step_result.step_id
            execution['step_results'].append(step_result)

    def complete_execution(self, execution_id: str, result: ExecutionResult):
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            execution['status'] = 'completed' if result.success else 'failed'
            execution['result'] = result
            execution['end_time'] = time.time()

    def get_status(self, execution_id: str) -> Dict[str, Any]:
        if execution_id not in self.executions:
            return {'success': False, 'error': 'Execution not found'}

        execution = self.executions[execution_id]
        plan = execution['plan']

        return {
            'success': True,
            'is_executing': execution['status'] == 'executing',
            'current_step': f"Step {execution['current_step']}/{len(plan.steps)}",
            'execution_log': [self._step_to_log_entry(r) for r in execution['step_results']],
            'progress_percentage': (execution['current_step'] / len(plan.steps)) * 100 if plan.steps else 0
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
        self.orchestrator = AIOrchestrator(host, device_id, team_id) if host else None
        self.tracker = AITracker()

    def analyze_compatibility(self, prompt: str) -> Dict[str, Any]:
        return self.planner.analyze_compatibility(prompt)

    def generate_plan(self, prompt: str, userinterface_name: str) -> AIPlan:
        return self.planner.generate_plan(prompt, userinterface_name)

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
            result = self.orchestrator.execute_plan(plan, options)
            self.tracker.complete_execution(execution_id, result)

        return execution_id

    def _execute_async(self, execution_id: str, plan: AIPlan, options: ExecutionOptions):
        try:
            result = self.orchestrator.execute_plan(plan, options)
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
        plan = self.generate_plan(prompt, userinterface_name)
        return self.execute_plan(plan, options)
