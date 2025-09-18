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
        self.team_id = kwargs.get('team_id', 'default')
        
        # Current node position tracking (like NavigationContext)
        self.current_node_id = None
        
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

    def _execute_navigation(self, target_node: str, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """
        Execute navigation using existing navigation system with current position tracking.
        
        Args:
            target_node: Target node to navigate to
            userinterface_name: Name of the userinterface for navigation tree
            
        Returns:
            Dictionary with execution results
        """
        try:
            print(f"AI[{self.device_name}]: Executing navigation to '{target_node}' using cached tree")
            
            # Simple validation: check if target_node is in available nodes list
            available_nodes = []
            if self.cached_tree_id:
                from shared.lib.utils.navigation_cache import get_cached_unified_graph
                unified_graph = get_cached_unified_graph(self.cached_tree_id, self.team_id)
                if unified_graph:
                    available_nodes = list(unified_graph.keys())
            
            if target_node not in available_nodes:
                return {
                    'success': False, 
                    'error': f'Target node {target_node} not found in unified graph. Available nodes: {available_nodes}'
                }
            
            # Use existing navigation system with current position
            from backend_core.src.services.navigation.navigation_service import execute_navigation_with_verification
            
            result = execute_navigation_with_verification(
                tree_id=self.cached_tree_id,
                target_node_id=target_node,
                current_node_id=self.current_node_id,  # Start from current position
                team_id=self.team_id
            )
            
            # Update current position after successful navigation
            if result.get('success'):
                final_position = result.get('final_position_node_id')
                if final_position:
                    self.current_node_id = final_position
                    print(f"AI[{self.device_name}]: Updated current position to: {self.current_node_id}")
            
            return result
            
        except Exception as e:
            error_msg = f"Navigation execution error: {str(e)}"
            print(f"AI[{self.device_name}]: {error_msg}")
            return {'success': False, 'error': error_msg}

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

    def _execute_action(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute controller action - delegate to frontend action system"""
        print(f"AI[{self.device_name}]: Executing action '{command}' with params: {params}")
        return {
            'success': True, 
            'action_type': 'controller_action',
            'command': command,
            'params': params,
            'message': f'Action {command} queued for frontend execution'
        }

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
            
            # Extract available nodes from navigation tree
            available_nodes = []
            if navigation_tree and 'unified_graph' in navigation_tree:
                available_nodes = list(navigation_tree['unified_graph'].keys())
                print(f"AI[{self.device_name}]: Found {len(available_nodes)} navigation nodes")
            
            # Handle MCP interface differently
            if device_model == "MCP_Interface":
                # MCP-specific prompt for web interface tasks
                prompt = f"""You are an MCP (Model Context Protocol) task automation AI. Generate an execution plan for web interface tasks.

Task: "{task_description}"
Available MCP tools: {[action.get('command') for action in available_actions]}

MCP Tool Guidelines:
- navigate_to_page: Use for "go to [page]" requests (pages: dashboard, rec, userinterface, runTests)
- execute_navigation_to_node: Use for navigation tree operations
- remote_execute_command: Use for device command execution

CRITICAL: Respond with ONLY valid JSON. No other text.

Required JSON format:
{{
  "analysis": "brief analysis of the task",
  "feasible": true,
  "plan": [
    {{
      "step": 1,
      "type": "action",
      "command": "navigate_to_page",
      "params": {{"page": "rec"}},
      "description": "Navigate to rec page"
    }}
  ]
}}

If task is not possible:
{{
  "analysis": "Task cannot be completed because...",
  "feasible": false,
  "plan": []
}}

JSON ONLY - NO OTHER TEXT"""
            else:
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
- For execute_navigation, target_node MUST be one of the exact node IDs listed
- DO NOT create or assume node names like "home", "live", "home_live" - use only the provided node IDs
- If the task requires navigation to a concept like "home" or "live", you must mark it as not feasible since semantic nodes are not available
- "click X" → click_element, element_id="X" (for UI elements, not navigation nodes)
- "press X" → press_key, key="X" (for remote control keys)

Example response format (using actual node IDs):
{{"analysis": "Task requires navigation but the available nodes are only technical IDs without semantic meaning. Cannot determine which node corresponds to the requested destination.", "feasible": false, "plan": []}}

If a task can be completed with available nodes:
{{"analysis": "Task can be completed using available node IDs.", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "node-1748723779677"}}, "description": "Navigate to node-1748723779677"}}]}}

IMPORTANT: 
- If you cannot map the task to specific available node IDs, mark as NOT FEASIBLE
- Do not guess or create node names
- Only use the exact node IDs provided in the available list

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
                ai_response = result['response']
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

    def execute_task(self, task_description: str, available_actions: List[Dict] = None, available_verifications: List[Dict] = None, device_model: str = None, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """
        Execute AI task with real-time execution and position tracking.
        
        Args:
            task_description: User's task description
            available_actions: Available device actions (optional)
            available_verifications: Available verifications (optional)
            device_model: Device model for context
            userinterface_name: Target userinterface name
            
        Returns:
            Dictionary with execution results
        """
        try:
            print(f"AI[{self.device_name}]: Starting task execution: {task_description}")
            
            # Set execution state
            self.is_executing = True
            self.task_start_time = time.time()
            self.execution_log = []
            
            # Load navigation tree
            navigation_tree = self._get_navigation_tree(userinterface_name)
            
            # Get default actions if not provided
            if available_actions is None:
                available_actions = [{'command': cmd} for cmd in self._get_available_actions(self.device_id).keys()]
            
            if available_verifications is None:
                available_verifications = []
            
            # Generate AI plan
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
                    'error': plan_result.get('error', 'Plan generation failed')
                }
            
            ai_plan = plan_result['plan']
            
            if not ai_plan.get('feasible', True):
                return {
                    'success': False,
                    'error': f"Task not feasible: {ai_plan.get('analysis', 'No analysis provided')}"
                }
            
            plan_steps = ai_plan.get('plan', [])
            
            # Execute steps
            executed_steps = 0
            total_steps = len(plan_steps)
            
            for i, step in enumerate(plan_steps):
                step_num = i + 1
                command = step.get('command')
                description = step.get('description', f'Step {step_num}')
                
                print(f"AI[{self.device_name}]: Executing step {step_num}/{total_steps}: {description}")
                
                # Execute step based on command type
                if command == 'execute_navigation':
                    target_node = step.get('params', {}).get('target_node')
                    cached_interface = self.cached_userinterface_name or userinterface_name
                    result = self._execute_navigation(target_node, cached_interface)
                elif command in ['press_key', 'click_element', 'wait']:
                    params = step.get('params', {})
                    result = self._execute_action(command, params)
                else:
                    result = {'success': False, 'error': f'Unknown command: {command}'}
                
                if result.get('success'):
                    executed_steps += 1
                    print(f"AI[{self.device_name}]: Step {step_num} completed successfully")
                else:
                    print(f"AI[{self.device_name}]: Step {step_num} failed: {result.get('error', 'Unknown error')}")
                    break
            
            # Calculate execution time
            execution_time = time.time() - self.task_start_time
            
            return {
                'success': executed_steps == total_steps,
                'executed_steps': executed_steps,
                'total_steps': total_steps,
                'execution_time_ms': int(execution_time * 1000),
                'current_position': self.current_node_id,
                'ai_analysis': ai_plan.get('analysis', ''),
                'execution_log': self.execution_log
            }
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Task execution error: {e}")
            return {
                'success': False,
                'error': f'Task execution failed: {str(e)}'
            }
        finally:
            self.is_executing = False
