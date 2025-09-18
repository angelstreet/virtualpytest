"""
AI Agent Analysis and Compatibility

Analysis, compatibility checking, and feasibility assessment for AI Agent.
Handles cross-device analysis and real-time feasibility checking.
"""

import json
from typing import Dict, Any, List
from .ai_agent_testcase import AIAgentTestCase
from shared.lib.utils.ai_utils import call_text_ai, AI_CONFIG


class AIAgentAnalysis(AIAgentTestCase):
    """AI Agent analysis and compatibility checking."""

    def analyze_cross_device_compatibility(self, test_case: Dict[str, Any], target_interfaces: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze test case compatibility across multiple devices/interfaces.
        Uses existing capability fetching for accurate analysis.
        
        Args:
            test_case: Generated test case to analyze
            target_interfaces: List of interface names to check compatibility
            
        Returns:
            List of compatibility results for each interface
        """
        try:
            print(f"AI[{self.device_name}]: Analyzing compatibility across {len(target_interfaces)} interfaces")
            
            compatibility_results = []
            original_steps = test_case.get('test_steps', [])
            
            for interface_name in target_interfaces:
                try:
                    # Extract device model from interface name
                    device_model = self._extract_device_model_from_interface(interface_name)
                    
                    # Get capabilities for this device using existing method
                    # Note: We'd need device_id, but for analysis we can use model-based lookup
                    device_capabilities = self._get_model_capabilities(device_model)
                    
                    # Get navigation tree for this interface
                    navigation_tree = self._get_navigation_tree(interface_name)
                    available_nodes = list(navigation_tree.get('unified_graph', {}).keys()) if navigation_tree else []
                    
                    # Analyze step compatibility
                    compatible_steps = 0
                    incompatible_reasons = []
                    
                    for step in original_steps:
                        command = step.get('command')
                        
                        if command == 'execute_navigation':
                            target_node = step.get('params', {}).get('target_node')
                            if target_node in available_nodes:
                                compatible_steps += 1
                            else:
                                incompatible_reasons.append(f"Navigation node '{target_node}' not available")
                        
                        elif command in device_capabilities:
                            compatible_steps += 1
                        else:
                            incompatible_reasons.append(f"Command '{command}' not supported")
                    
                    compatibility_score = compatible_steps / len(original_steps) if original_steps else 0
                    is_compatible = compatibility_score >= 0.8  # 80% compatibility threshold
                    
                    compatibility_results.append({
                        'interface_name': interface_name,
                        'device_model': device_model,
                        'compatible': is_compatible,
                        'compatibility_score': compatibility_score,
                        'compatible_steps': compatible_steps,
                        'total_steps': len(original_steps),
                        'reasoning': f"Compatible with {compatible_steps}/{len(original_steps)} steps" if is_compatible else f"Incompatible: {', '.join(incompatible_reasons[:3])}",
                        'missing_capabilities': incompatible_reasons,
                        'required_nodes': [step.get('params', {}).get('target_node') for step in original_steps if step.get('command') == 'execute_navigation'],
                        'available_nodes': available_nodes
                    })
                    
                except Exception as e:
                    compatibility_results.append({
                        'interface_name': interface_name,
                        'compatible': False,
                        'reasoning': f"Analysis failed: {str(e)}",
                        'error': str(e)
                    })
            
            return compatibility_results
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Error in cross-device analysis: {e}")
            return [{'error': f'Cross-device analysis failed: {str(e)}'}]

    def _extract_device_model_from_interface(self, interface_name: str) -> str:
        """Extract device model from interface name using existing patterns"""
        if 'android_mobile' in interface_name:
            return 'android_mobile'
        elif 'android_tv' in interface_name:
            return 'android_tv'
        elif 'fire_tv' in interface_name:
            return 'fire_tv'
        elif 'ios_mobile' in interface_name:
            return 'ios_mobile'
        elif 'web' in interface_name:
            return 'web'
        elif 'stb' in interface_name:
            return 'stb'
        elif 'apple_tv' in interface_name:
            return 'apple_tv'
        else:
            parts = interface_name.split('_')
            return '_'.join(parts[-2:]) if len(parts) >= 2 else interface_name

    def _get_model_capabilities(self, device_model: str) -> Dict[str, Any]:
        """Get capabilities for a device model (for compatibility analysis)"""
        try:
            # This would need to be implemented to get model-based capabilities
            # For now, return basic capabilities based on model type
            basic_capabilities = {
                'android_mobile': ['press_key', 'click_element', 'swipe', 'wait'],
                'android_tv': ['press_key', 'wait', 'navigate'],
                'ios_mobile': ['tap', 'swipe', 'wait'],
                'web': ['click', 'type', 'wait'],
                'stb': ['press_key', 'wait', 'navigate']
            }
            return basic_capabilities.get(device_model, ['press_key', 'wait'])
        except Exception as e:
            print(f"AI[{self.device_name}]: Error getting model capabilities: {e}")
            return ['press_key', 'wait']  # Minimal fallback

    def quick_feasibility_check(self, prompt: str, interface_name: str = None) -> Dict[str, Any]:
        """
        Quick feasibility check for real-time UI feedback.
        Uses existing AI analysis for fast response.
        
        Args:
            prompt: Natural language description
            interface_name: Target interface (optional)
            
        Returns:
            Feasibility result with suggestions
        """
        try:
            interface_name = interface_name or self.cached_userinterface_name or "horizon_android_mobile"
            
            # Get basic contexts using existing methods
            available_actions = self._get_available_actions(self.device_id)
            navigation_context = self._get_navigation_context([])  # Quick check without full tree
            action_context = self._get_action_context()
            
            # Quick AI analysis prompt
            quick_prompt = f"""Quick feasibility check only. Can this be automated?
            
Request: "{prompt}"
{navigation_context}
{action_context}

Return JSON only: {{"feasible": true/false, "reason": "brief explanation", "suggestions": ["alternatives"]}}"""
            
            # Use existing AI call with agent model
            agent_model = AI_CONFIG['providers']['openrouter']['models']['agent']
            result = call_text_ai(
                prompt=quick_prompt,
                max_tokens=300,
                temperature=0.0,
                model=agent_model
            )
            
            if result.get('success'):
                ai_response = json.loads(result['content'])
                return {
                    'success': True,
                    'feasible': ai_response.get('feasible', False),
                    'reason': ai_response.get('reason', ''),
                    'suggestions': ai_response.get('suggestions', [])
                }
            else:
                return {
                    'success': False,
                    'feasible': False,
                    'reason': f'Feasibility check failed: {result.get("error", "Unknown error")}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'feasible': False,
                'reason': f'Feasibility check error: {str(e)}'
            }

    def analyze_compatibility(self, task_description: str, available_actions: List[Dict], available_verifications: List[Dict], device_model: str = None, userinterface_name: str = "horizon_android_mobile") -> Dict[str, Any]:
        """
        Analyze compatibility WITHOUT executing - just check if task can be done.
        
        Args:
            task_description: User's task description (e.g., "go to live and check audio")
            available_actions: List of available device actions
            available_verifications: List of available verifications
            device_model: Device model for context
            userinterface_name: Target userinterface name
            
        Returns:
            Dictionary with compatibility analysis results
        """
        try:
            print(f"AI[{self.device_name}]: Analyzing compatibility for: {task_description}")
            
            # Load navigation tree for analysis
            navigation_tree = self._get_navigation_tree(userinterface_name)
            
            # Generate AI plan for analysis (without execution)
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
                    'compatible': False,
                    'reason': plan_result.get('error', 'Analysis failed'),
                    'confidence': 0.0
                }
            
            ai_plan = plan_result['plan']
            
            # Analyze feasibility
            is_feasible = ai_plan.get('feasible', False)
            analysis = ai_plan.get('analysis', 'No analysis provided')
            plan_steps = ai_plan.get('plan', [])
            
            # Calculate compatibility metrics
            total_steps = len(plan_steps)
            navigation_steps = len([s for s in plan_steps if s.get('command') == 'execute_navigation'])
            action_steps = len([s for s in plan_steps if s.get('command') in ['press_key', 'click_element']])
            
            return {
                'success': True,
                'compatible': is_feasible,
                'reason': analysis,
                'confidence': 0.9 if is_feasible else 0.1,
                'analysis_details': {
                    'total_steps': total_steps,
                    'navigation_steps': navigation_steps,
                    'action_steps': action_steps,
                    'required_capabilities': [s.get('command') for s in plan_steps],
                    'estimated_duration': total_steps * 3  # 3 seconds per step
                },
                'ai_plan': ai_plan
            }
            
        except Exception as e:
            print(f"AI[{self.device_name}]: Compatibility analysis error: {e}")
            return {
                'success': False,
                'compatible': False,
                'reason': f'Analysis error: {str(e)}',
                'confidence': 0.0
            }

    def analyze_task_complexity(self, task_description: str) -> Dict[str, Any]:
        """
        Analyze task complexity without device-specific context.
        
        Args:
            task_description: Natural language task description
            
        Returns:
            Complexity analysis results
        """
        try:
            # Simple heuristic-based complexity analysis
            task_lower = task_description.lower()
            
            # Count complexity indicators
            navigation_words = ['go to', 'navigate', 'open', 'menu', 'back', 'home']
            action_words = ['click', 'press', 'tap', 'swipe', 'type', 'enter']
            verification_words = ['check', 'verify', 'ensure', 'confirm', 'validate']
            
            navigation_count = sum(1 for word in navigation_words if word in task_lower)
            action_count = sum(1 for word in action_words if word in task_lower)
            verification_count = sum(1 for word in verification_words if word in task_lower)
            
            total_operations = navigation_count + action_count + verification_count
            
            # Determine complexity level
            if total_operations <= 2:
                complexity = 'low'
                estimated_steps = 1-3
            elif total_operations <= 5:
                complexity = 'medium'
                estimated_steps = 3-7
            else:
                complexity = 'high'
                estimated_steps = 7-15
            
            return {
                'success': True,
                'complexity': complexity,
                'estimated_steps': estimated_steps,
                'operation_breakdown': {
                    'navigation_operations': navigation_count,
                    'action_operations': action_count,
                    'verification_operations': verification_count,
                    'total_operations': total_operations
                },
                'estimated_duration_seconds': estimated_steps * 3
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Complexity analysis failed: {str(e)}'
            }
