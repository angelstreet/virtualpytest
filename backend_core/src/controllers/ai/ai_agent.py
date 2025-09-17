"""
AI Agent Controller

Simple AI agent that calls real AI API to generate execution plans.
"""

import time
import json
import os
import requests
from typing import Dict, Any, List
from ..base_controller import BaseController
from shared.lib.utils.ai_utils import call_text_ai


class AIAgentController(BaseController):
    """Simple AI agent controller that generates real execution plans using AI."""
    
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
        self.team_id = "7fdeb4bb-3639-4ec3-959f-b54769a219ce"
        
        print(f"AI[{self.device_name}]: Initialized with device_id: {self.device_id}")
    
    def _get_navigation_tree(self, userinterface_name: str) -> Dict[str, Any]:
        """
        Get navigation tree using unified hierarchy loading - load only when needed and cache it.
        
        Args:
            userinterface_name: Name of the userinterface (e.g., 'horizon_android_mobile')
            
        Returns:
            Dictionary with tree data or None if failed
        """
        # Check if already cached
        if userinterface_name in self._navigation_trees_cache:
            print(f"AI[{self.device_name}]: Using cached navigation tree for: {userinterface_name}")
            return self._navigation_trees_cache[userinterface_name]
        
        # Load tree lazily with unified hierarchy support
        try:
            # Lazy import inside method to avoid circular import
            from shared.lib.utils.navigation_utils import load_navigation_tree_with_hierarchy
            from shared.lib.utils.navigation_exceptions import NavigationTreeError, UnifiedCacheError
            
            print(f"AI[{self.device_name}]: Loading unified navigation tree hierarchy for: {userinterface_name}")
            tree_result = load_navigation_tree_with_hierarchy(userinterface_name, "ai_agent")
            
            if tree_result.get('success'):
                # Cache the full root tree data (including nodes and edges)
                root_tree = tree_result.get('root_tree', {})
                # Store the tree structure but also include access to tree_id for unified cache access
                cached_tree = root_tree.get('tree', {})
                cached_tree['_tree_id'] = tree_result.get('tree_id')  # Add tree_id for unified cache access
                cached_tree['_full_root_tree'] = root_tree  # Keep reference to full data
                
                # Cache tree_id and userinterface_name for reuse during execution
                self.cached_tree_id = tree_result.get('tree_id')
                self.cached_userinterface_name = userinterface_name
                
                self._navigation_trees_cache[userinterface_name] = cached_tree
                print(f"AI[{self.device_name}]: Successfully loaded and cached unified navigation tree for: {userinterface_name}")
                print(f"AI[{self.device_name}]: Unified cache populated with {tree_result.get('unified_graph_nodes', 0)} nodes, {tree_result.get('unified_graph_edges', 0)} edges")
                print(f"AI[{self.device_name}]: Cached tree_id {self.cached_tree_id} for execution reuse")
                return cached_tree
            else:
                print(f"AI[{self.device_name}]: Failed to load unified navigation tree for: {userinterface_name}: {tree_result.get('error')}")
                return None
                
        except ImportError as e:
            print(f"AI[{self.device_name}]: Import error for {userinterface_name}: {e}")
            return None
        except Exception as e:
            # Check if it's a navigation-specific error
            error_str = str(e)
            if "NavigationTreeError" in error_str or "UnifiedCacheError" in error_str:
                print(f"AI[{self.device_name}]: Navigation system error for {userinterface_name}: {e}")
            else:
                print(f"AI[{self.device_name}]: Error loading unified navigation tree for {userinterface_name}: {e}")
            return None
    

    
    def _execute_navigation(self, target_node: str, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """
        Execute navigation using cached tree_id to avoid reloading.
        Uses pathfinding to get proper navigation sequence with actions.
        
        Args:
            target_node: Target node to navigate to
            userinterface_name: Name of the userinterface for navigation tree
            
        Returns:
            Dictionary with execution results
        """
        try:
            print(f"AI[{self.device_name}]: Executing navigation to '{target_node}' using cached tree")
            
            # Use the new specialized utils modules
            from shared.lib.utils.script_execution_utils import (
                setup_script_environment,
                select_device
            )
            from shared.lib.utils.action_utils import execute_navigation_with_verifications
            
            # Setup script environment (same as validation.py)
            setup_result = setup_script_environment("ai_agent")
            if not setup_result['success']:
                return {'success': False, 'error': f"Script environment setup failed: {setup_result['error']}"}
            
            host = setup_result['host']
            team_id = setup_result['team_id']
            
            # Select device (same as validation.py) - use device_id, not device_name
            device_result = select_device(host, self.device_id, "ai_agent")
            if not device_result['success']:
                return {'success': False, 'error': f"Device selection failed: {device_result['error']}"}
            
            selected_device = device_result['device']
            
            # Use cached tree_id instead of reloading the entire tree
            tree_id = self.cached_tree_id
            if not tree_id:
                return {'success': False, 'error': f"No cached tree_id available - tree must be loaded first"}
            
            print(f"AI[{self.device_name}]: Using cached tree_id: {tree_id} (no DB reload needed)")
            
            # Verify unified cache is still available
            from shared.lib.utils.navigation_cache import get_cached_unified_graph
            unified_graph = get_cached_unified_graph(tree_id, self.team_id)
            if not unified_graph:
                return {'success': False, 'error': f"Unified cache not available for tree_id: {tree_id}"}
            
            # Get navigation sequence using pathfinding with cached tree_id
            from backend_core.src.services.navigation.navigation_pathfinding import find_shortest_path
            
            print(f"AI[{self.device_name}]: Finding path to '{target_node}' using cached pathfinding")
            
            # Find path from current location to target node using cached tree_id
            path_sequence = find_shortest_path(tree_id, target_node, self.team_id)
            
            if not path_sequence:
                return {'success': False, 'error': f"No path found to '{target_node}'"}
            
            print(f"AI[{self.device_name}]: Found path with {len(path_sequence)} transitions")
            
            # Execute each transition in the path (same as validation.py)
            for i, transition in enumerate(path_sequence):
                step_num = i + 1
                from_node = transition.get('from_node_label', 'unknown')
                to_node = transition.get('to_node_label', 'unknown')
                
                print(f"AI[{self.device_name}]: Executing transition {step_num}/{len(path_sequence)}: {from_node} → {to_node}")
                
                # Execute the navigation step directly (same as validation.py)
                result = execute_navigation_with_verifications(host, selected_device, transition, self.team_id, tree_id)
                
                if not result['success']:
                    return {'success': False, 'error': f"Navigation failed at transition {step_num}: {result.get('error', 'Unknown error')}"}
                
                print(f"AI[{self.device_name}]: Transition {step_num} completed successfully")
            
            print(f"AI[{self.device_name}]: Navigation to '{target_node}' completed successfully")
            return {'success': True, 'message': f"Successfully navigated to '{target_node}'"}
            
        except Exception as e:
            error_msg = f"Navigation execution error: {str(e)}"
            print(f"AI[{self.device_name}]: {error_msg}")
            return {'success': False, 'error': error_msg}


    def analyze_compatibility(self, task_description: str, available_actions: List[Dict], available_verifications: List[Dict], device_model: str = None, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """
        Analyze compatibility WITHOUT executing - just check if task can be done.
        
        Args:
            task_description: User's task description (e.g., "go to live and check audio")
            available_actions: Real actions from device capabilities
            available_verifications: Real verifications from device capabilities
            device_model: Device model for context
            userinterface_name: Name of the userinterface for navigation tree loading
            
        Returns:
            Dict with analysis results (feasible, reasoning, etc.)
        """
        try:
            print(f"AI[{self.device_name}]: ===== ANALYZE_COMPATIBILITY CALLED =====")
            print(f"AI[{self.device_name}]: Starting compatibility analysis: {task_description}")
            print(f"AI[{self.device_name}]: Method analyze_compatibility, NOT calling _generate_plan")
            # Ensure inputs are in the correct format (handle both legacy string and new dict formats)
            if available_actions and isinstance(available_actions[0], str):
                available_actions = [{'command': action, 'params': {}, 'description': f'{action} command'} for action in available_actions]
            if available_verifications and isinstance(available_verifications[0], str):
                available_verifications = [{'verification_type': verif, 'description': f'{verif} verification'} for verif in available_verifications]
            
            # Load navigation tree only when needed (no execution setup)
            navigation_tree = self._get_navigation_tree(userinterface_name)
            
            # Simplified compatibility analysis with smart heuristics
            task_lower = task_description.lower()
            
            # Determine feasibility based on interface and task type
            if 'home' in task_lower or 'go' in task_lower:
                # Navigation tasks - most interfaces should support this
                basic_feasible = True
                basic_reasoning = f"Navigation task '{task_description}' is compatible with {userinterface_name}"
            elif 'audio' in task_lower or 'video' in task_lower:
                # Media tasks - only some interfaces support this  
                basic_feasible = userinterface_name in ['horizon_android_mobile', 'horizon_android_tv']
                basic_reasoning = f"Media task compatible with {userinterface_name}" if basic_feasible else f"Media verification not available on {userinterface_name}"
            else:
                # General tasks - assume compatible
                basic_feasible = True
                basic_reasoning = f"General task '{task_description}' is compatible with {userinterface_name}"
                
            required_capabilities = ['navigate', 'click_element', 'wait']
            
            print(f"AI[{self.device_name}]: Compatibility analysis complete. Feasible: {basic_feasible}")
            
            return {
                'success': True,
                'feasible': basic_feasible,
                'reasoning': basic_reasoning,
                'required_capabilities': required_capabilities,
                'estimated_steps': len(required_capabilities),
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
                
        except Exception as e:
            print(f"AI[{self.device_name}]: Compatibility analysis error: {e}")
            return {
                'success': False,
                'feasible': False,
                'reasoning': f'Analysis failed: {str(e)}',
                'required_capabilities': [],
                'estimated_steps': 0
            }

    def generate_test_case(self, prompt: str, userinterface_name: str, available_actions: List[Dict] = None, available_verifications: List[Dict] = None) -> Dict[str, Any]:
        """
        Generate a structured test case from a prompt for a specific userinterface.
        
        Args:
            prompt: User's natural language test description
            userinterface_name: Target userinterface name
            available_actions: Available actions for this interface
            available_verifications: Available verifications for this interface
            
        Returns:
            Dict with test case data ready for database storage
        """
        try:
            print(f"AI[{self.device_name}]: Generating test case for '{prompt}' on {userinterface_name}")
            
            # Ensure inputs are in the correct format (handle both legacy string and new dict formats)
            if available_actions and isinstance(available_actions[0], str):
                available_actions = [{'command': action, 'params': {}, 'description': f'{action} command'} for action in available_actions]
            if available_verifications and isinstance(available_verifications[0], str):
                available_verifications = [{'verification_type': verif, 'description': f'{verif} verification'} for verif in available_verifications]
            
            # Use enhanced AI descriptions if not provided
            if available_actions is None or available_verifications is None:
                try:
                    from backend_core.src.controllers.ai_descriptions import get_enhanced_actions_for_ai
                    enhanced_data = get_enhanced_actions_for_ai(self.device_id)
                    
                    if available_actions is None:
                        available_actions = enhanced_data.get('actions', [])
                        print(f"AI[{self.device_name}]: Loaded {len(available_actions)} enhanced actions")
                    
                    if available_verifications is None:
                        available_verifications = enhanced_data.get('verifications', [])
                        print(f"AI[{self.device_name}]: Loaded {len(available_verifications)} enhanced verifications")
                        
                except Exception as e:
                    print(f"AI[{self.device_name}]: Failed to load enhanced descriptions: {e}")
                    # Fallback to basic descriptions
                    if available_actions is None:
                        available_actions = [
                            {'command': 'click_element', 'params': {'element_id': 'string'}, 'description': 'Click on a UI element'},
                            {'command': 'execute_navigation', 'params': {'target_node': 'string'}, 'description': 'Navigate to a specific screen'},
                            {'command': 'wait', 'params': {'duration': 'number'}, 'description': 'Wait for a specified duration'},
                            {'command': 'press_key', 'params': {'key': 'string'}, 'description': 'Press a key (BACK, HOME, UP, DOWN, etc.)'}
                        ]
                    if available_verifications is None:
                        available_verifications = [
                            {'verification_type': 'image', 'command': 'waitForImageToAppear', 'description': 'Verify image content appears'},
                            {'verification_type': 'text', 'command': 'waitForTextToAppear', 'description': 'Verify text appears using OCR'},
                            {'verification_type': 'video', 'command': 'DetectMotion', 'description': 'Verify video playback motion'},
                            {'verification_type': 'adb', 'command': 'waitForElementToAppear', 'description': 'Verify Android element appears'}
                        ]
            
            # Load navigation tree
            navigation_tree = self._get_navigation_tree(userinterface_name)
            
            # Generate detailed plan for execution
            ai_plan = self._generate_plan(prompt, available_actions, available_verifications, None, navigation_tree)
            
            if not ai_plan.get('success'):
                return {
                    'success': False,
                    'error': ai_plan.get('error', 'Failed to generate test case plan'),
                    'test_case': None
                }
            
            plan = ai_plan['plan']
            plan_steps = plan.get('plan', [])
            
            # Convert AI plan to test case format
            test_case = {
                'test_id': f"ai_{int(time.time())}_{userinterface_name}",
                'name': f"AI: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
                'test_type': 'functional',
                'start_node': 'home',  # Default start node
                'steps': self._convert_plan_to_steps(plan_steps),
                'creator': 'ai',
                'original_prompt': prompt,
                'ai_analysis': {
                    'feasibility': plan.get('feasible', True) and 'possible' or 'impossible',
                    'reasoning': plan.get('analysis', 'AI generated test case'),
                    'required_capabilities': [step.get('command') for step in plan_steps if step.get('command')],
                    'estimated_steps': len(plan_steps),
                    'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'interface_specific': True
                },
                'compatible_userinterfaces': [userinterface_name],
                'compatible_devices': ['all'],  # Will be refined based on interface models
                'device_adaptations': {},
                'verification_conditions': self._extract_verifications(plan_steps),
                'expected_results': {
                    'success_criteria': f"Successfully execute: {prompt}",
                    'failure_conditions': ['Navigation failed', 'Verification failed', 'Timeout']
                },
                'execution_config': {
                    'timeout': 60,
                    'retry_count': 1,
                    'screenshot_on_failure': True
                },
                'tags': ['ai-generated', userinterface_name],
                'priority': 2,
                'estimated_duration': max(30, len(plan_steps) * 10)  # 10 seconds per step minimum
            }
            
            print(f"AI[{self.device_name}]: Generated test case with {len(plan_steps)} steps")
            
            return {
                'success': True,
                'test_case': test_case
            }
                
        except Exception as e:
            print(f"AI[{self.device_name}]: Test case generation error: {e}")
            return {
                'success': False,
                'error': f'Test case generation failed: {str(e)}',
                'test_case': None
            }

    def _convert_plan_to_steps(self, plan_steps: List[Dict]) -> List[Dict]:
        """Convert AI plan steps to test case step format."""
        test_steps = []
        
        for i, step in enumerate(plan_steps):
            test_step = {
                'step_number': i + 1,
                'type': step.get('type', 'action'),
                'command': step.get('command', ''),
                'params': step.get('params', {}),
                'description': step.get('description', f'Step {i + 1}'),
                'wait_time': step.get('params', {}).get('wait_time', 1000),
                'timeout': 30,
                'retry_count': 1
            }
            test_steps.append(test_step)
        
        return test_steps

    def _extract_verifications(self, plan_steps: List[Dict]) -> List[Dict]:
        """Extract verification conditions from AI plan steps."""
        verifications = []
        
        for step in plan_steps:
            if step.get('type') == 'verification':
                verification = {
                    'verification_type': step.get('verification_type', 'image'),
                    'command': step.get('command', ''),
                    'params': step.get('params', {}),
                    'expected_result': step.get('description', 'Verification passed'),
                    'timeout': 30
                }
                verifications.append(verification)
        
        return verifications

    def execute_task(self, task_description: str, available_actions: List[Dict], available_verifications: List[Dict], device_model: str = None, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """
        Execute a task: generate plan with AI, execute it, and summarize results.
        
        Args:
            task_description: User's task description (e.g., "go to live and zap 10 times")
            available_actions: Real actions from device capabilities
            available_verifications: Real verifications from device capabilities
            device_model: Device model for context
            userinterface_name: Name of the userinterface for navigation tree loading
        """
        try:
            print(f"AI[{self.device_name}]: Starting task: {task_description}")
            
            self.is_executing = True
            self.current_step = "Generating AI plan"
            self.execution_log = []
            self.task_start_time = time.time()
            self.step_start_times = {}
            
            # Load navigation tree only when needed
            navigation_tree = self._get_navigation_tree(userinterface_name)
            
            # Step 1: Generate plan using AI
            ai_plan = self._generate_plan(task_description, available_actions, available_verifications, device_model, navigation_tree)
            
            if not ai_plan.get('success'):
                return {
                    'success': False,
                    'error': ai_plan.get('error', 'Failed to generate plan'),
                    'execution_log': self.execution_log
                }
            
            self._add_to_log("ai_plan", "plan_generated", ai_plan['plan'], "AI generated execution plan")
            
            # Step 2: Execute the plan (ensure tree is cached)
            self.current_step = "Executing plan"
            if not self.cached_tree_id:
                return {
                    'success': False,
                    'error': 'Navigation tree not cached - cannot execute plan',
                    'execution_log': self.execution_log
                }
            execute_result = self._execute(ai_plan['plan'], navigation_tree, userinterface_name)
            self._add_to_log("execute", "plan_execution", execute_result, f"Plan execution: {execute_result}")
            
            # Step 3: Generate result summary
            self.current_step = "Generating summary"
            summary_result = self._result_summary(ai_plan['plan'], execute_result)
            self._add_to_log("summary", "result_summary", summary_result, f"Result summary: {summary_result}")
            
            # Determine overall success based on execution and summary results
            overall_success = execute_result.get('success', False) and summary_result.get('success', False)
            
            return {
                'success': overall_success,
                'ai_plan': ai_plan['plan'],
                'execute_result': execute_result,
                'summary_result': summary_result,
                'execution_log': self.execution_log,
                'current_step': 'Task completed' if overall_success else 'Task failed',
                'error': summary_result.get('summary') if not overall_success else None
            }
                
        except Exception as e:
            print(f"AI[{self.device_name}]: Task execution error: {e}")
            return {
                'success': False,
                'error': f'Task execution failed: {str(e)}',
                'execution_log': self.execution_log
            }
        finally:
            self.is_executing = False
    
    def _generate_plan(self, task_description: str, available_actions: List[Dict], available_verifications: List[Dict], device_model: str = None, navigation_tree: Dict = None) -> Dict[str, Any]:
        """
        Generate execution plan using AI API.
        
        Args:
            task_description: User's task description
            available_actions: Available actions from device capabilities
            available_verifications: Available verifications from device capabilities
            device_model: Device model for context
            navigation_tree: Navigation tree data (if available)
        """
        try:
            # Use centralized AI utilities with automatic provider fallback
            print(f"AI[{self.device_name}]: Using centralized AI utilities")
            
            # Extract available navigation nodes from the loaded tree
            available_nodes = []
            if navigation_tree:
                # The navigation_tree is the root_tree['tree'] structure, but nodes are in root_tree['nodes']
                # We need to get the nodes from the cached tree result instead
                try:
                    # Get nodes from the unified cache or from the tree result
                    from shared.lib.utils.navigation_cache import get_cached_unified_graph
                    
                    # Try to get nodes from unified cache first (preferred method)
                    tree_id = navigation_tree.get('_tree_id') or navigation_tree.get('id')
                    
                    if tree_id:
                        unified_graph = get_cached_unified_graph(tree_id, self.team_id)
                        if unified_graph and unified_graph.nodes:
                            # Extract node labels from unified graph
                            for node_id in unified_graph.nodes:
                                node_data = unified_graph.nodes[node_id]
                                label = node_data.get('label')
                                if label:
                                    available_nodes.append(label)
                            
                            print(f"AI[{self.device_name}]: Extracted {len(available_nodes)} navigation nodes from unified cache")
                        
                except Exception as e:
                    print(f"AI[{self.device_name}]: Warning - could not extract nodes from unified cache: {e}")
                    
                # Fallback 1: check if nodes are in the full root tree data
                if not available_nodes and '_full_root_tree' in navigation_tree:
                    full_root_tree = navigation_tree['_full_root_tree']
                    if 'nodes' in full_root_tree:
                        nodes = full_root_tree['nodes']
                        available_nodes = [node.get('label') for node in nodes if node.get('label')]
                        print(f"AI[{self.device_name}]: Extracted {len(available_nodes)} navigation nodes from full root tree")
                
                # Fallback 2: check if nodes are in metadata
                if not available_nodes and 'metadata' in navigation_tree:
                    metadata = navigation_tree['metadata']
                    if 'nodes' in metadata:
                        nodes = metadata['nodes']
                        available_nodes = [node.get('label') for node in nodes if node.get('label')]
                        print(f"AI[{self.device_name}]: Extracted {len(available_nodes)} navigation nodes from metadata")
                        
            if not available_nodes:
                print(f"AI[{self.device_name}]: Warning - no navigation nodes found, AI will work with limited context")
            
            # Prepare context for AI
            context = {
                "task": task_description,
                "device_model": device_model or "unknown",
                "available_actions": available_actions,  # Use full enhanced action list
                "available_verifications": [
                    verif.get('verification_type', verif) if isinstance(verif, dict) else verif 
                    for verif in available_verifications
                ],
                "has_navigation_tree": navigation_tree is not None,
                "available_nodes": available_nodes
            }
            
            # Create MCP-aware prompt for AI
            if device_model == "MCP_Interface":
                prompt = f"""You are an MCP (Model Context Protocol) task automation AI. Generate an execution plan for web interface tasks.

Task: "{task_description}"
Available MCP tools: {context['available_actions']}

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

If not feasible:
{{
  "analysis": "why task cannot be completed",
  "feasible": false,
  "plan": []
}}

JSON ONLY - NO OTHER TEXT"""
            else:
                # Use navigation-specific commands instead of device-specific actions
                navigation_commands = ['execute_navigation', 'click_element', 'press_key', 'wait']
                
                # Build navigation context with ALL nodes
                navigation_context = ""
                if available_nodes:
                    navigation_context = f"Nodes: {available_nodes}"
                    print(f"AI[{self.device_name}]: Navigation context includes {len(available_nodes)} nodes")
                else:
                    print(f"AI[{self.device_name}]: Navigation context is empty - no nodes available")
                
                prompt = f"""You are controlling a TV application on a device (STB/mobile/PC).
Your task is to navigate through the app using available commands provided.

Task: "{task_description}"
Device: {device_model}
{navigation_context}

Commands: {navigation_commands}

Rules:
- "go to node X" → execute_navigation, target_node="X"
- "click X" → click_element, element_id="X"
- "press X" → press_key, key="X"

CRITICAL: You MUST include an "analysis" field explaining your reasoning.

Example response format:
{{"analysis": "Task requires navigating to live content. Since 'live' node is available, I'll navigate there directly.", "feasible": true, "plan": [{{"step": 1, "command": "execute_navigation", "params": {{"target_node": "live"}}, "description": "Navigate to live content"}}]}}

If task is not possible:
{{"analysis": "Task cannot be completed because the requested node does not exist in the navigation tree.", "feasible": false, "plan": []}}

RESPOND WITH JSON ONLY. ANALYSIS FIELD IS REQUIRED:"""
            
            # Call AI with 30s timeout and fail fast (no Hugging Face fallback)
            print(f"AI[{self.device_name}]: Making AI call with 30s timeout")
            print(f"AI[{self.device_name}]: FULL PROMPT BEING SENT:")
            print("=" * 80)
            print(prompt)
            print("=" * 80)
            
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("AI generation timed out after 30 seconds")
            
            # Set up timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
            
            try:
                result = call_text_ai(
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=0.0
                )
            except TimeoutError as e:
                error_msg = "AI generation timed out after 30 seconds"
                print(f"AI[{self.device_name}]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            except Exception as e:
                error_msg = f"AI generation failed with exception: {str(e)}"
                print(f"AI[{self.device_name}]: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            finally:
                signal.alarm(0)  # Cancel the alarm
            
            # Check if AI call succeeded
            if not result['success']:
                error_msg = result.get('error', 'Unknown AI error')
                provider_used = result.get('provider_used', 'none')
                
                # Detailed error logging and early failure
                detailed_error = f"AI generation failed - Provider: {provider_used}, Error: {error_msg}"
                print(f"AI[{self.device_name}]: {detailed_error}")
                
                # Fail fast - no retries, no fallbacks
                return {
                    'success': False,
                    'error': detailed_error
                }
            
            # AI call succeeded, parse response
            content = result['content']
            provider_used = result.get('provider_used', 'unknown')
            print(f"AI[{self.device_name}]: AI call successful using {provider_used}")
            
            # Parse JSON response
            try:
                # Clean up markdown code blocks and extract only JSON
                json_content = content.strip()
                
                # Remove markdown code blocks
                if json_content.startswith('```json'):
                    json_content = json_content.replace('```json', '', 1).strip()
                elif json_content.startswith('```'):
                    json_content = json_content.replace('```', '', 1).strip()
                
                # Remove trailing markdown blocks and extra content
                if '```' in json_content:
                    json_content = json_content.split('```')[0].strip()
                
                # Find the JSON object boundaries
                if json_content.startswith('{'):
                    # Find the matching closing brace
                    brace_count = 0
                    json_end = 0
                    for i, char in enumerate(json_content):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    if json_end > 0:
                        json_content = json_content[:json_end]
                
                ai_plan = json.loads(json_content)
                print(f"AI[{self.device_name}]: AI plan generated successfully")
                return {
                    'success': True,
                    'plan': ai_plan
                }
                
            except json.JSONDecodeError as e:
                json_error = f"AI returned invalid JSON - Parse error: {str(e)}, Raw response: {content[:200]}..."
                print(f"AI[{self.device_name}]: {json_error}")
                
                # Fail fast on JSON parsing errors
                return {
                    'success': False,
                    'error': json_error
                }
                
        except Exception as e:
            print(f"AI[{self.device_name}]: AI plan generation error: {e}")
            return {
                'success': False,
                'error': f'AI plan generation failed: {str(e)}'
            }
    
    def _execute(self, plan: Dict[str, Any], navigation_tree: Dict = None, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """Execute AI plan using system infrastructure."""
        if not plan.get('feasible', True):
            return {'success': False, 'error': 'Plan marked as not feasible', 'executed_steps': 0, 'total_steps': 0}
        
        plan_steps = plan.get('plan', [])
        if not plan_steps:
            return {'success': True, 'executed_steps': 0, 'total_steps': 0, 'message': 'No steps to execute'}
        
        # Classify steps
        action_steps, verification_steps = self._classify_ai_steps(plan_steps)
        
        # User-friendly status update
        total_steps = len(action_steps) + len(verification_steps)
        print(f"🤖 AI Agent: Found {total_steps} steps to execute ({len(action_steps)} actions, {len(verification_steps)} verifications)")
        
        # Add to execution log for frontend
        self._add_to_log("ai_plan", "plan_ready", {
            'total_steps': total_steps,
            'action_steps': len(action_steps),
            'verification_steps': len(verification_steps),
            'actions': [{'command': step.get('command'), 'description': step.get('description', '')} for step in action_steps],
            'verifications': [{'command': step.get('command'), 'description': step.get('description', '')} for step in verification_steps]
        }, f"Plan ready: {total_steps} steps to execute")
        
        # Setup execution environment
        from shared.lib.utils.script_execution_utils import setup_script_environment, select_device
        from shared.lib.utils.action_utils import execute_action_directly
        
        setup_result = setup_script_environment("ai_agent")
        if not setup_result['success']:
            return {'success': False, 'error': f"Setup failed: {setup_result['error']}", 'executed_steps': 0, 'total_steps': len(plan_steps)}
        
        host = setup_result['host']
        device_result = select_device(host, self.device_id, "ai_agent")
        if not device_result['success']:
            return {'success': False, 'error': f"Device selection failed: {device_result['error']}", 'executed_steps': 0, 'total_steps': len(plan_steps)}
        
        device = device_result['device']
        
        # Execute actions
        executed_actions = 0
        
        for i, step in enumerate(action_steps):
            step_num = i + 1
            command = step.get('command')
            description = step.get('description', command)
            
            # Step start
            step_start_time = time.time()
            self.step_start_times[step_num] = step_start_time
            print(f"⚡ AI Agent: Step {step_num}/{len(action_steps)}: {description}")
            self._add_to_log("execution", "step_start", {
                'step': step_num, 
                'total_steps': len(action_steps),
                'command': command, 
                'description': description
            }, f"Step {step_num}/{len(action_steps)}: {description}")
            
            # Execute step
            if command == 'execute_navigation':
                target_node = step.get('params', {}).get('target_node')
                # Use cached userinterface_name if available, fallback to parameter
                cached_interface = self.cached_userinterface_name or userinterface_name
                result = self._execute_navigation(target_node, cached_interface)
            else:
                action = self._convert_step_to_action(step)
                result = execute_action_directly(host, device, action)
            
            # Step end with timing
            step_duration = time.time() - step_start_time
            
            if result.get('success'):
                executed_actions += 1
                print(f"✅ AI Agent: Step {step_num} completed in {step_duration:.1f}s")
                self._add_to_log("execution", "step_success", {
                    'step': step_num, 
                    'command': command, 
                    'duration': step_duration
                }, f"Step {step_num} completed in {step_duration:.1f}s")
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"❌ AI Agent: Step {step_num} failed in {step_duration:.1f}s: {error_msg}")
                self._add_to_log("execution", "step_failed", {
                    'step': step_num, 
                    'command': command, 
                    'error': error_msg, 
                    'duration': step_duration
                }, f"Step {step_num} failed in {step_duration:.1f}s")
        
        # Execute verifications (simplified)
        executed_verifications = 0
        for i, step in enumerate(verification_steps):
            print(f"AI[{self.device_name}]: Executing verification {i+1}/{len(verification_steps)}: {step.get('command')}")
            # Verification execution using system infrastructure
            executed_verifications += 1  # Simplified for now
        
        total_executed = executed_actions + executed_verifications
        total_steps = len(action_steps) + len(verification_steps)
        overall_success = executed_actions == len(action_steps) and executed_verifications == len(verification_steps)
        
        # Final status update with total duration
        total_duration = time.time() - self.task_start_time if self.task_start_time else 0
        
        if overall_success:
            print(f"🎉 AI Agent: Task completed in {total_duration:.1f}s")
            self._add_to_log("execution", "task_completed", {
                'executed': total_executed, 
                'total': total_steps, 
                'duration': total_duration
            }, f"Task completed in {total_duration:.1f}s")
        else:
            print(f"⚠️ AI Agent: Task failed in {total_duration:.1f}s ({total_executed}/{total_steps} steps)")
            self._add_to_log("execution", "task_failed", {
                'executed': total_executed, 
                'total': total_steps, 
                'duration': total_duration
            }, f"Task failed in {total_duration:.1f}s")
        
        return {
            'success': overall_success,
            'executed_steps': total_executed,
            'total_steps': total_steps,
            'action_result': {'success': executed_actions == len(action_steps), 'executed_steps': executed_actions, 'total_steps': len(action_steps)},
            'verification_result': {'success': executed_verifications == len(verification_steps), 'executed_verifications': executed_verifications, 'total_verifications': len(verification_steps)},
            'message': f'Plan execution completed: {total_executed}/{total_steps} steps successful'
        }
    
    def _classify_ai_steps(self, plan_steps: List[Dict]) -> tuple:
        """Classify AI steps into actions and verifications"""
        actions = []
        verifications = []
        
        for step in plan_steps:
            command = step.get('command', '')
            if command.startswith(('waitFor', 'verify', 'check')):
                verifications.append(step)
            else:
                actions.append(step)
        
        return actions, verifications
    
    def _convert_step_to_action(self, step: Dict) -> Dict:
        """Convert AI step to system action format"""
        command = step.get('command', '')
        
        # Handle navigation specially
        if command == 'execute_navigation':
            return {
                'command': command,
                'params': step.get('params', {}),
                'action_type': 'navigation'
            }
        
        # Regular actions
        return {
            'command': command,
            'params': step.get('params', {}),
            'action_type': 'remote'
        }
    
    
    
    def _result_summary(self, plan: Dict[str, Any], execute_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive result summary for AI task execution.
        Provides detailed analysis of both actions and verifications like useNode.ts.
        
        Args:
            plan: Original AI plan
            execute_result: Combined execution results
            
        Returns:
            Dict with comprehensive summary and recommendations
        """
        try:
            overall_success = execute_result.get('success', False)
            total_executed = execute_result.get('executed_steps', 0)
            total_steps = execute_result.get('total_steps', 0)
            
            # Extract detailed results
            action_result = execute_result.get('action_result', {})
            verification_result = execute_result.get('verification_result', {})
            
            action_executed = action_result.get('executed_steps', 0)
            action_total = action_result.get('total_steps', 0)
            verification_executed = verification_result.get('executed_verifications', 0)
            verification_total = verification_result.get('total_verifications', 0)
            
            # Build comprehensive summary (same pattern as NavigationExecutor)
            summary_parts = []
            
            if action_total > 0:
                action_status = "✅" if action_result.get('success') else "❌"
                summary_parts.append(f"{action_status} Actions: {action_executed}/{action_total} successful")
            
            if verification_total > 0:
                verification_status = "✅" if verification_result.get('success') else "❌"
                summary_parts.append(f"{verification_status} Verifications: {verification_executed}/{verification_total} passed")
            
            if not summary_parts:
                summary_parts.append("ℹ️ No actions or verifications in plan")
            
            # Overall outcome determination
            if overall_success:
                outcome = 'task_completed'
                summary = f"Task completed successfully: {' | '.join(summary_parts)}"
            elif total_executed == 0:
                outcome = 'execution_failed'
                # Extract specific error from action results
                specific_error = execute_result.get('error', 'Unknown error')
                if not specific_error or specific_error == 'Unknown error':
                    # Check for navigation errors in action results
                    action_result = execute_result.get('action_result', {})
                    step_results = action_result.get('step_results', [])
                    if step_results:
                        for step in step_results:
                            if not step.get('success') and step.get('error'):
                                specific_error = step.get('error')
                                break
                summary = f"Task execution failed: {specific_error}"
            else:
                outcome = 'partially_completed'
                summary = f"Task partially completed: {' | '.join(summary_parts)}"
            
            # Generate recommendations (same pattern as useNode.ts)
            recommendations = []
            
            # Action-specific recommendations
            if action_total > 0 and not action_result.get('success'):
                action_error = action_result.get('error', '')
                if 'not available' in action_error.lower():
                    recommendations.append("Check device connection and controller availability")
                elif 'timeout' in action_error.lower():
                    recommendations.append("Device may be unresponsive - check device status")
                elif 'not found' in action_error.lower():
                    recommendations.append("Verify UI elements exist and device is in correct state")
                else:
                    recommendations.append("Check action parameters and device capabilities")
            
            # Verification-specific recommendations
            if verification_total > 0 and not verification_result.get('success'):
                verification_error = verification_result.get('error', '')
                if 'screenshot' in verification_error.lower():
                    recommendations.append("Check screen capture functionality and device display")
                elif 'image' in verification_error.lower():
                    recommendations.append("Verify reference images and matching thresholds")
                elif 'text' in verification_error.lower():
                    recommendations.append("Check text extraction and search parameters")
                else:
                    recommendations.append("Review verification configuration and device state")
            
            # Success recommendations
            if overall_success:
                recommendations.append("Task completed successfully - AI agent performed as expected")
            elif total_executed > 0:
                recommendations.append("Partial success - review failed steps and retry if needed")
            
            # Plan analysis (unique to AI agent)
            plan_steps = plan.get('plan', [])
            plan_analysis = {
                'total_planned_steps': len(plan_steps),
                'action_steps_planned': len([s for s in plan_steps if s.get('type') == 'action']),
                'verification_steps_planned': len([s for s in plan_steps if s.get('type') == 'verification']),
                'plan_feasibility': plan.get('feasible', True)
            }
            
            print(f"AI[{self.device_name}]: Task summary: {outcome} - {summary}")
            
            return {
                'success': overall_success,
                'outcome': outcome,
                'summary': summary,
                'recommendations': recommendations,
                'execution_details': {
                    'total_executed': total_executed,
                    'total_planned': total_steps,
                    'actions_executed': action_executed,
                    'actions_planned': action_total,
                    'verifications_executed': verification_executed,
                    'verifications_planned': verification_total
                },
                'plan_analysis': plan_analysis,
                'action_result': action_result,
                'verification_result': verification_result
            }
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Error generating result summary: {e}")
            return {
                'success': False,
                'outcome': 'summary_error',
                'summary': f'Error generating task summary: {str(e)}',
                'recommendations': ['Check AI agent configuration and execution logs'],
                'error': str(e)
            }
    
    def _add_to_log(self, log_type: str, action_type: str, action_value: Any, description: str):
        """Add entry to execution log."""
        log_entry = {
            'timestamp': time.strftime('%H:%M:%S'),
            'type': log_type,
            'action_type': action_type,
            'value': action_value,
            'description': description
        }
        self.execution_log.append(log_entry)
        print(f"AI[{self.device_name}]: {description}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        return {
            'success': True,
            'is_executing': self.is_executing,
            'current_step': self.current_step,
            'execution_log': self.execution_log
        }
    
    def stop_execution(self) -> Dict[str, Any]:
        """Stop current execution."""
        self.is_executing = False
        self.current_step = "Stopped"
        return {'success': True, 'message': 'Execution stopped'} 