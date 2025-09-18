"""
AI Agent Test Case Generation

Test case generation and management functionality for the AI Agent.
Handles creating reusable test cases from natural language prompts.
"""

import time
import json
from typing import Dict, Any, List
from .ai_agent_core import AIAgentCore


class AIAgentTestCase(AIAgentCore):
    """AI Agent test case generation and management."""

    def generate_test_case(self, prompt: str, userinterface_name: str = None, store_in_db: bool = True) -> Dict[str, Any]:
        """
        Generate a test case from natural language prompt using existing AI analysis.
        Reuses all existing AI Agent capabilities for superior analysis.
        
        Args:
            prompt: Natural language description of test scenario
            userinterface_name: Target interface (optional, uses cached if available)
            store_in_db: Whether to store the generated test case in database
            
        Returns:
            Complete test case ready for storage and execution
        """
        try:
            print(f"AI[{self.device_name}]: Generating test case for: {prompt}")
            
            # Use cached interface or provided one
            interface_name = userinterface_name or self.cached_userinterface_name or "horizon_android_mobile"
            
            # Get device capabilities using existing method
            available_actions = self._get_available_actions(self.device_id)
            
            # Get navigation tree using existing method
            navigation_tree = self._get_navigation_tree(interface_name)
            available_nodes = list(navigation_tree.get('unified_graph', {}).keys()) if navigation_tree else []
            
            # Generate AI plan using existing _generate_plan method
            ai_plan_result = self._generate_plan(
                prompt, 
                [{'command': cmd} for cmd in available_actions.keys()],  # Convert to expected format
                [],  # Verifications - will be enhanced later
                self._extract_device_model(),
                navigation_tree
            )
            
            if not ai_plan_result.get('success'):
                return {
                    'success': False,
                    'error': ai_plan_result.get('error', 'Failed to generate test case plan'),
                    'test_case': None
                }
            
            ai_plan = ai_plan_result['plan']
            plan_steps = ai_plan.get('plan', [])
            
            # Convert AI plan to test case format
            test_case = {
                'id': f"ai_{int(time.time())}_{interface_name}",
                'name': f"AI: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
                'description': f"AI-generated test case: {prompt}",
                'creator': 'ai',
                'original_prompt': prompt,
                'ai_analysis': {
                    'feasibility': 'possible' if ai_plan.get('feasible', True) else 'impossible',
                    'reasoning': ai_plan.get('analysis', 'AI generated test case'),
                    'required_capabilities': [step.get('command') for step in plan_steps if step.get('command')],
                    'estimated_steps': len(plan_steps),
                    'compatible_devices': [self._extract_device_model()],
                    'compatible_userinterfaces': [interface_name],
                    'device_adaptations': {}
                },
                'device_model': self._extract_device_model(),
                'interface_name': interface_name,
                'test_steps': self._convert_plan_to_test_steps(plan_steps),
                'expected_outcomes': self._extract_expected_outcomes(plan_steps, prompt),
                'estimated_duration_ms': len(plan_steps) * 3000,  # 3s per step estimate
                'required_capabilities': list(set([step.get('command') for step in plan_steps if step.get('command')])),
                'status': 'ready',
                'compatible_devices': [self._extract_device_model()],
                'compatible_userinterfaces': [interface_name],
                'device_adaptations': {}
            }
            
            # Store in database if requested
            if store_in_db:
                stored_result = self._store_test_case(test_case)
                if not stored_result.get('success'):
                    print(f"AI[{self.device_name}]: Warning - test case generation succeeded but storage failed: {stored_result.get('error')}")
            
            return {
                'success': True,
                'test_case': test_case,
                'ai_confidence': ai_plan.get('confidence', 0.8)
            }
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Error generating test case: {e}")
            return {
                'success': False,
                'error': f'Test case generation failed: {str(e)}'
            }

    def _extract_device_model(self) -> str:
        """Extract device model from device_id or use default"""
        # Try to extract from device_id patterns
        if 'android' in self.device_id.lower():
            return 'android_mobile'
        elif 'ios' in self.device_id.lower():
            return 'ios_mobile'
        elif 'web' in self.device_id.lower():
            return 'web'
        elif 'stb' in self.device_id.lower():
            return 'stb'
        else:
            return 'generic'  # Default fallback

    def _convert_plan_to_test_steps(self, plan_steps: List[Dict]) -> List[Dict[str, Any]]:
        """Convert AI plan steps to test case step format"""
        test_steps = []
        for i, step in enumerate(plan_steps):
            test_step = {
                'step': i + 1,
                'type': self._determine_step_type(step.get('command')),
                'command': step.get('command'),
                'params': step.get('params', {}),
                'description': step.get('description', f"Step {i + 1}"),
                'estimated_duration_ms': 3000  # 3 second default
            }
            test_steps.append(test_step)
        return test_steps

    def _determine_step_type(self, command: str) -> str:
        """Determine step type based on command"""
        if command == 'execute_navigation':
            return 'navigation'
        elif command in ['press_key', 'click_element', 'swipe', 'tap']:
            return 'action'
        elif 'verify' in command or 'check' in command:
            return 'verification'
        else:
            return 'action'

    def _extract_expected_outcomes(self, plan_steps: List[Dict], prompt: str) -> List[str]:
        """Extract expected outcomes from plan and prompt"""
        outcomes = []
        
        # Add general success outcome
        outcomes.append(f"Successfully execute: {prompt}")
        
        # Add step-specific outcomes
        for step in plan_steps:
            command = step.get('command')
            if command == 'execute_navigation':
                outcomes.append(f"Navigate to target successfully")
            elif 'verify' in command or 'check' in command:
                outcomes.append(f"Verification passes")
        
        return outcomes

    def _store_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Store test case in database (placeholder for database integration)"""
        try:
            # This would integrate with your database system
            # For now, just return success
            print(f"AI[{self.device_name}]: Test case '{test_case['name']}' ready for storage")
            return {'success': True, 'test_case_id': test_case['id']}
        except Exception as e:
            return {'success': False, 'error': f'Storage failed: {str(e)}'}

    def execute_stored_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a stored test case using the core execution system.
        
        Args:
            test_case: Test case dictionary with steps and metadata
            
        Returns:
            Execution results
        """
        try:
            print(f"AI[{self.device_name}]: Executing stored test case: {test_case.get('name', 'Unknown')}")
            
            # Extract test case information
            test_steps = test_case.get('test_steps', [])
            interface_name = test_case.get('interface_name', 'horizon_android_mobile')
            
            # Set execution state
            self.is_executing = True
            self.task_start_time = time.time()
            self.execution_log = []
            
            # Load navigation tree for the test case interface
            navigation_tree = self._get_navigation_tree(interface_name)
            
            # Execute test steps
            executed_steps = 0
            total_steps = len(test_steps)
            
            for i, step in enumerate(test_steps):
                step_num = i + 1
                command = step.get('command')
                params = step.get('params', {})
                description = step.get('description', f'Step {step_num}')
                
                print(f"AI[{self.device_name}]: Executing test step {step_num}/{total_steps}: {description}")
                
                # Execute step based on command type
                if command == 'execute_navigation':
                    target_node = params.get('target_node')
                    result = self._execute_navigation(target_node, interface_name)
                elif command in ['press_key', 'click_element', 'wait']:
                    result = self._execute_action(command, params)
                else:
                    result = {'success': False, 'error': f'Unknown command: {command}'}
                
                if result.get('success'):
                    executed_steps += 1
                    print(f"AI[{self.device_name}]: Test step {step_num} completed successfully")
                else:
                    print(f"AI[{self.device_name}]: Test step {step_num} failed: {result.get('error', 'Unknown error')}")
                    break
            
            # Calculate execution time
            execution_time = time.time() - self.task_start_time
            
            return {
                'success': executed_steps == total_steps,
                'executed_steps': executed_steps,
                'total_steps': total_steps,
                'execution_time_ms': int(execution_time * 1000),
                'current_position': self.current_node_id,
                'test_case_id': test_case.get('id'),
                'test_case_name': test_case.get('name'),
                'execution_log': self.execution_log
            }
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Test case execution error: {e}")
            return {
                'success': False,
                'error': f'Test case execution failed: {str(e)}'
            }
        finally:
            self.is_executing = False
