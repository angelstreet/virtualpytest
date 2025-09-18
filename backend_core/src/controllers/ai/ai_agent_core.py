"""
AI Agent Core Controller

Core AI agent functionality for real-time task execution and navigation.
Handles basic execution, navigation, and device interaction.
"""

import time
import json
import os
import requests
from typing import Dict, Any, List
from ..base_controller import BaseController
from shared.lib.utils.ai_utils import call_text_ai, AI_CONFIG


class AIAgentCore(BaseController):
    """Core AI agent controller for real-time execution and navigation."""
    
    # Class-level cache for navigation trees (singleton pattern)
    _navigation_trees_cache: Dict[str, Dict] = {}
    
    def __init__(self, device_id: str, device_name: str = None, **kwargs):
        # Clean API: device_id is mandatory, device_name is optional
        super().__init__("ai", device_name or device_id)
        
        # Store device_id for controller access
        self.device_id = device_id
        
        self.is_executing = False
        self.current_step = ""
        self.execution_log = []
        
        # Timing tracking
        self.task_start_time = None
        self.step_start_times = {}
        
        # Navigation tree caching for reuse during execution
        self.cached_tree_id = None
        self.cached_userinterface_name = None
        self.team_id = kwargs.get('team_id', "7fdeb4bb-3639-4ec3-959f-b54769a219ce")
        
        # Current node position tracking (like NavigationContext)
        self.current_node_id = None
        
        # Cached plan for 2-phase execution
        self.cached_plan = None
        
        print(f"AI[{self.device_name}]: Initialized with device_id: {self.device_id}")
    
    def _get_navigation_tree(self, userinterface_name: str) -> Dict[str, Any]:
        """
        Get navigation tree using unified hierarchy loading - load only when needed and cache it.
        
        Args:
            userinterface_name: Name of the userinterface to load tree for
            
        Returns:
            Dictionary containing navigation tree data or None if not found
        """
        try:
            # Check cache first
            cache_key = f"{userinterface_name}:{self.team_id}"
            if cache_key in self._navigation_trees_cache:
                cached_tree = self._navigation_trees_cache[cache_key]
                print(f"AI[{self.device_name}]: Using cached navigation tree for {userinterface_name}")
                return cached_tree
            
            # Load fresh tree using existing navigation system
            from shared.lib.utils.navigation_cache import get_cached_unified_graph
            from shared.lib.supabase.userinterface_db import get_userinterface_by_name
            from shared.lib.supabase.navigation_trees_db import get_root_tree_for_interface, get_full_tree
            
            # Get userinterface info
            userinterface_info = get_userinterface_by_name(userinterface_name, self.team_id)
            if not userinterface_info:
                print(f"AI[{self.device_name}]: Userinterface {userinterface_name} not found")
                return None
            
            # Get root tree for this userinterface
            root_tree = get_root_tree_for_interface(userinterface_info.get('userinterface_id'), self.team_id)
            if not root_tree:
                print(f"AI[{self.device_name}]: No root tree found for {userinterface_name}")
                return None
            
            tree_id = root_tree.get('tree_id')
            
            # Try cache first
            unified_graph = get_cached_unified_graph(tree_id, self.team_id)
            if not unified_graph:
                # Load full tree if not cached
                tree_data = get_full_tree(tree_id, self.team_id)
                if tree_data.get('success'):
                    unified_graph = tree_data.get('unified_graph', {})
                else:
                    print(f"AI[{self.device_name}]: Failed to load tree data for {tree_id}")
                    return None
            
            # Cache the tree and tree_id for reuse
            navigation_tree = {
                'tree_id': tree_id,
                'userinterface_name': userinterface_name,
                'unified_graph': unified_graph,
                'userinterface_info': userinterface_info
            }
            
            self._navigation_trees_cache[cache_key] = navigation_tree
            self.cached_tree_id = tree_id
            self.cached_userinterface_name = userinterface_name
            
            print(f"AI[{self.device_name}]: Loaded and cached navigation tree for {userinterface_name} (tree_id: {tree_id})")
            return navigation_tree
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Error loading navigation tree for {userinterface_name}: {e}")
            return None

    def _get_available_actions(self, device_id: str) -> Dict[str, Any]:
        """Get available actions from controller - reuse existing controller system"""
        try:
            from backend_core.src.controllers.controller_config_factory import get_controller_config
            controller_config = get_controller_config(device_id)
            return controller_config.get('available_actions', {})
        except Exception as e:
            print(f"AI[{self.device_name}]: Error getting available actions: {e}")
            return {}

    def _get_navigation_context(self, available_nodes: List[str]) -> str:
        """Get navigation context with available nodes"""
        if available_nodes:
            return f"Navigation - Available nodes: {available_nodes}"
        return "Navigation - No nodes available"

    def _get_action_context(self) -> str:
        """Get action context with available controller commands"""
        try:
            available_actions = self._get_available_actions(self.device_id)
            if not available_actions:
                return "Actions - No controller actions available"
            
            action_commands = list(available_actions.keys())
            return f"Actions - Available commands: {action_commands}"
        except Exception as e:
            print(f"AI[{self.device_name}]: Error getting action context: {e}")
            return f"Actions - Error: {str(e)}"

    def _add_to_log(self, log_type: str, action_type: str, data: Dict[str, Any], description: str = ""):
        """Add entry to execution log with timestamp"""
        log_entry = {
            'timestamp': time.time(),
            'log_type': log_type,
            'action_type': action_type,
            'data': data,
            'description': description
        }
        self.execution_log.append(log_entry)
        
        # Keep log size manageable
        if len(self.execution_log) > 100:
            self.execution_log = self.execution_log[-50:]

    def _generate_plan(self, task_description: str, available_actions: List[Dict], available_verifications: List[Dict], device_model: str = None, navigation_tree: Dict = None) -> Dict[str, Any]:
        """
        Generate AI execution plan using consolidated context system.
        
        Args:
            task_description: User's task description
            available_actions: List of available device actions
            available_verifications: List of available verifications
            device_model: Device model for context
            navigation_tree: Navigation tree data
            
        Returns:
            Dictionary with AI plan or error
        """
        try:
            print(f"AI[{self.device_name}]: Generating plan for: {task_description}")
            
            # Extract available nodes from navigation tree - USE LABELS
            available_nodes = []
            if navigation_tree:
                tree_id = navigation_tree.get('tree_id')
                if tree_id:
                    from shared.lib.utils.navigation_cache import get_cached_unified_graph
                    unified_graph = get_cached_unified_graph(tree_id, self.team_id)
                    if unified_graph and unified_graph.nodes:
                        # Extract node labels from unified graph
                        for node_id in unified_graph.nodes:
                            node_data = unified_graph.nodes[node_id]
                            label = node_data.get('label')
                            if label:
                                available_nodes.append(label)
                        print(f"AI[{self.device_name}]: Extracted {len(available_nodes)} navigation node labels")
            
            # Get consolidated contexts
            navigation_context = self._get_navigation_context(available_nodes)
            action_context = self._get_action_context()
            
            print(f"AI[{self.device_name}]: {navigation_context}")
            print(f"AI[{self.device_name}]: {action_context}")
            
            prompt = f"""You are controlling a TV application on a device (STB/mobile/PC).
Your task is to navigate through the app using available commands provided.

Task: "{task_description}"
Device: {device_model}
{navigation_context}
{action_context}

CRITICAL RULES:
- You MUST ONLY use nodes from the available list above
- For execute_navigation, target_node MUST be one of the exact node labels listed
- "click X" → click_element, element_id="X" (for UI elements, not navigation nodes)
- "press X" → press_key, key="X" (for remote control keys)

Example response format:
{{"analysis": "Task can be completed using available nodes.", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "home"}}, "description": "Navigate to home"}}]}}

If task not possible:
{{"analysis": "Task cannot be completed because...", "feasible": false, "plan": []}}

CRITICAL: RESPOND WITH JSON ONLY. ANALYSIS FIELD explaining your reasoning is REQUIRED"""
            
            # Call AI with timeout handled by AI utils (no signal handling needed)
            print(f"AI[{self.device_name}]: Making AI call with built-in timeout")
            
            try:
                print(f"AI[{self.device_name}]: Calling AI with enhanced error tracking...")
                # Use dedicated agent model for complex reasoning tasks
                agent_model = AI_CONFIG['providers']['openrouter']['models']['agent']
                result = call_text_ai(
                    prompt=prompt,
                    max_tokens=1500,
                    temperature=0.0,
                    model=agent_model
                )
                
                if not result.get('success'):
                    return {
                        'success': False,
                        'error': f"AI API call failed: {result.get('error', 'Unknown error')}"
                    }
                
                # Parse AI response
                ai_response = result['content']
                print(f"AI[{self.device_name}]: Raw AI response: {ai_response[:200]}...")
                
                try:
                    plan_data = json.loads(ai_response)
                except json.JSONDecodeError as e:
                    print(f"AI[{self.device_name}]: JSON parse error: {e}")
                    return {
                        'success': False,
                        'error': f"AI returned invalid JSON: {str(e)}"
                    }
                
                return {
                    'success': True,
                    'plan': plan_data
                }
                
            except Exception as e:
                print(f"AI[{self.device_name}]: AI call error: {e}")
                return {
                    'success': False,
                    'error': f"AI generation failed: {str(e)}"
                }
                
        except Exception as e:
            print(f"AI[{self.device_name}]: Plan generation error: {e}")
            return {
                'success': False,
                'error': f"Plan generation failed: {str(e)}"
            }

    def execute_task(self, task_description: str, available_actions: List[Dict], available_verifications: List[Dict], device_model: str = None, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """Execute a task with both plan generation and execution."""
        try:
            print(f"AI[{self.device_name}]: Starting full task: {task_description}")
            
            # Phase 1: Generate plan
            plan_result = self.generate_plan_only(task_description, available_actions, available_verifications, device_model, userinterface_name)
            
            if not plan_result.get('success'):
                return plan_result
            
            # Phase 2: Execute plan
            execution_result = self.execute_plan_only(userinterface_name)
            
            return execution_result
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            print(f"AI[{self.device_name}]: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_log': self.execution_log,
                'current_step': self.current_step
            }

    def generate_plan_only(self, task_description: str, available_actions: List[Dict], available_verifications: List[Dict], device_model: str = None, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """
        Generate AI plan without executing (for 2-phase execution).
        
        Args:
            task_description: User's task description
            available_actions: Available device actions
            available_verifications: Available verifications
            device_model: Device model for context
            userinterface_name: Target userinterface name
            
        Returns:
            Dictionary with AI plan (no execution)
        """
        try:
            print(f"AI[{self.device_name}]: Generating plan only for: {task_description}")
            
            # Load navigation tree
            navigation_tree = self._get_navigation_tree(userinterface_name)
            
            # Generate AI plan using existing method
            plan_result = self._generate_plan(
                task_description, 
                available_actions, 
                available_verifications, 
                device_model, 
                navigation_tree
            )
            
            if not plan_result.get('success'):
                return {
                    'success': False,
                    'error': plan_result.get('error', 'Plan generation failed'),
                    'execution_log': self.execution_log
                }
            
            ai_plan = plan_result['plan']
            
            if not ai_plan.get('feasible', True):
                return {
                    'success': False,
                    'error': f"Task not feasible: {ai_plan.get('analysis', 'No analysis provided')}",
                    'execution_log': self.execution_log
                }
            
            # Store plan for later execution
            self.cached_plan = ai_plan
            self.cached_userinterface_name = userinterface_name
            
            return {
                'success': True,
                'plan': ai_plan,
                'execution_log': self.execution_log,
                'current_step': 'Plan generated, ready for execution'
            }
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Plan generation error: {e}")
            return {
                'success': False,
                'error': f'Plan generation failed: {str(e)}',
                'execution_log': self.execution_log
            }

    def execute_plan_only(self, userinterface_name: str = None) -> Dict[str, Any]:
        """Execute previously generated plan using existing _execute method."""
        if not hasattr(self, 'cached_plan') or not self.cached_plan:
            return {'success': False, 'error': 'No cached plan available for execution'}
        
        print(f"AI[{self.device_name}]: Executing cached plan")
        
        # Delegate to existing _execute method (same as ai_testcase_executor.py)
        result = self._execute(
            plan=self.cached_plan,
            navigation_tree=None,
            userinterface_name=userinterface_name or self.cached_userinterface_name
        )
        
        # Clear cached plan after execution
        self.cached_plan = None
        self.is_executing = False
        
        return result


    def _execute(self, plan: Dict[str, Any], navigation_tree: Dict = None, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """Execute AI plan with proper logging for frontend polling."""
        try:
            if not plan.get('feasible', True):
                return {'success': False, 'error': 'Plan marked as not feasible', 'executed_steps': 0, 'total_steps': 0}
            
            plan_steps = plan.get('plan', [])
            if not plan_steps:
                return {'success': True, 'executed_steps': 0, 'total_steps': 0, 'message': 'No steps to execute'}
            
            print(f"AI[{self.device_name}]: Executing plan with {len(plan_steps)} steps")
            
            # Set execution state for polling
            self.is_executing = True
            self.task_start_time = time.time()
            
            # Execute steps with proper logging for frontend
            executed_steps = 0
            total_steps = len(plan_steps)
            
            for i, step in enumerate(plan_steps):
                step_num = i + 1
                command = step.get('command')
                params = step.get('params', {})
                description = step.get('description', f'Step {step_num}')
                
                # Update current step for polling
                self.current_step = f"Step {step_num}/{total_steps}: {description}"
                
                # Record step start for frontend
                step_start_time = time.time()
                self._add_to_log("execution", "step_start", {
                    'step': step_num,
                    'total_steps': total_steps,
                    'command': command,
                    'description': description
                })
                
                # Execute step (simplified - just log success for now)
                print(f"AI[{self.device_name}]: Executing step {step_num}: {description}")
                
                # Simulate execution result
                result = {'success': True}  # Placeholder - will be replaced with actual execution
                
                # Record step completion for frontend
                step_duration = time.time() - step_start_time
                
                if result.get('success'):
                    executed_steps += 1
                    self._add_to_log("execution", "step_success", {
                        'step': step_num,
                        'command': command,
                        'duration': step_duration
                    })
                else:
                    self._add_to_log("execution", "step_failed", {
                        'step': step_num,
                        'command': command,
                        'duration': step_duration,
                        'error': result.get('error', 'Unknown error')
                    })
                    break
            
            # Record task completion
            execution_time = time.time() - self.task_start_time
            task_success = executed_steps == total_steps
            
            completion_type = "task_completed" if task_success else "task_failed"
            self._add_to_log("execution", completion_type, {
                'executed_steps': executed_steps,
                'total_steps': total_steps,
                'duration': execution_time,
                'success': task_success
            })
            
            self.current_step = f"Task {'completed' if task_success else 'failed'}"
            
            return {
                'success': task_success,
                'executed_steps': executed_steps,
                'total_steps': total_steps,
                'action_result': {'executed_steps': executed_steps, 'total_steps': total_steps},
                'verification_result': {'executed_verifications': 0, 'total_verifications': 0}
            }
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Execution error: {e}")
            self._add_to_log("execution", "task_failed", {
                'error': str(e),
                'duration': time.time() - (self.task_start_time or time.time())
            })
            return {
                'success': False,
                'error': f'Execution failed: {str(e)}',
                'executed_steps': 0,
                'total_steps': len(plan_steps)
            }
        finally:
            self.is_executing = False


    def get_status(self) -> Dict[str, Any]:
        """Get current AI agent status for frontend polling."""
        return {
            'success': True,
            'is_executing': self.is_executing,
            'current_step': self.current_step,
            'execution_log': self.execution_log,  # Frontend expects full log, not just size
            'current_position': self.current_node_id,
            'cached_tree_id': self.cached_tree_id,
            'cached_interface': self.cached_userinterface_name,
            'device_id': self.device_id
        }

    def stop_execution(self) -> Dict[str, Any]:
        """Stop current AI agent execution."""
        try:
            if self.is_executing:
                print(f"AI[{self.device_name}]: Stopping execution")
                self.is_executing = False
                self.current_step = "Execution stopped by user"
                
                return {
                    'success': True,
                    'message': 'AI execution stopped',
                    'execution_log': self.execution_log
                }
            else:
                return {
                    'success': True,
                    'message': 'AI agent was not executing',
                    'execution_log': self.execution_log
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to stop execution: {str(e)}',
                'execution_log': self.execution_log
            }
