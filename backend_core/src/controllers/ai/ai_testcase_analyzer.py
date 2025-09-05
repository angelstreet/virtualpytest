"""
AI Test Case Analyzer

Server-side AI test case analysis and generation - NO device dependencies.
Pure heuristic logic and navigation graph inspection for compatibility analysis.
"""

import uuid
import json
from typing import Dict, Any, List, Optional


class AITestCaseAnalyzer:
    """
    Server-side AI test case analysis and generation.
    
    NO device dependencies - uses pure heuristic logic and navigation graph inspection.
    Designed for server-side analysis phase where no devices are available.
    """
    
    def __init__(self):
        """Initialize analyzer with no device dependencies."""
        # No device controllers needed
        # Pure logic and heuristic analysis only
        pass
    
    def analyze_compatibility(self, prompt: str, userinterfaces: List[Dict[str, Any]], model_commands: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze test case compatibility using heuristics and navigation graphs.
        
        Args:
            prompt: Natural language test case description
            userinterfaces: List of available userinterfaces with metadata
            
        Returns:
            {
                'analysis_id': 'uuid',
                'understanding': 'Parsed intent from prompt',
                'compatibility_matrix': {
                    'compatible_userinterfaces': ['interface1', 'interface2'],
                    'incompatible': ['interface3'],
                    'reasons': {'interface1': 'Has required navigation nodes'}
                },
                'requires_multiple_testcases': bool,
                'estimated_complexity': 'low|medium|high'
            }
        """
        print(f"[@AITestCaseAnalyzer:analyze] Analyzing prompt: {prompt}")
        print(f"[@AITestCaseAnalyzer:analyze] Available interfaces: {len(userinterfaces)}")
        
        # Generate unique analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Parse prompt for intent understanding
        understanding = self._parse_prompt_intent(prompt)
        
        # Analyze each userinterface for compatibility
        compatibility_results = []
        
        for ui in userinterfaces:
            ui_name = ui.get('name', 'unknown')
            print(f"[@AITestCaseAnalyzer:analyze] Analyzing interface: {ui_name}")
            
            try:
                # Analyze compatibility using real commands if available, fallback to heuristics
                compatibility = self._analyze_interface_compatibility(prompt, ui, model_commands)
                
                compatibility_results.append({
                    'userinterface': ui_name,
                    'compatible': compatibility['compatible'],
                    'reasoning': compatibility['reasoning'],
                    'confidence': compatibility['confidence'],
                    'missing_capabilities': compatibility.get('missing_capabilities', [])
                })
                
            except Exception as e:
                print(f"[@AITestCaseAnalyzer:analyze] Error analyzing {ui_name}: {e}")
                compatibility_results.append({
                    'userinterface': ui_name,
                    'compatible': False,
                    'reasoning': f'Analysis failed: {str(e)}',
                    'confidence': 0.0,
                    'missing_capabilities': ['analysis_error']
                })
        
        # Separate compatible and incompatible interfaces
        compatible = [r for r in compatibility_results if r['compatible']]
        incompatible = [r for r in compatibility_results if not r['compatible']]
        
        # Build compatibility matrix
        compatibility_matrix = {
            'compatible_userinterfaces': [ui['userinterface'] for ui in compatible],
            'incompatible': [ui['userinterface'] for ui in incompatible],
            'reasons': {ui['userinterface']: ui['reasoning'] for ui in compatibility_results}
        }
        
        # Determine complexity and multi-testcase requirement
        requires_multiple = len(compatible) > 1
        complexity = self._estimate_complexity(prompt, compatible)
        
        # Generate step preview for the first compatible interface (if any)
        step_preview = []
        if compatible:
            primary_interface = compatible[0]['userinterface']
            step_preview = self.generate_test_steps(prompt, primary_interface)
        
        result = {
            'analysis_id': analysis_id,
            'understanding': understanding,
            'compatibility_matrix': compatibility_matrix,
            'requires_multiple_testcases': requires_multiple,
            'estimated_complexity': complexity,
            'total_analyzed': len(userinterfaces),
            'compatible_count': len(compatible),
            'incompatible_count': len(incompatible),
            'step_preview': step_preview  # NEW: Show what steps will be generated
        }
        
        print(f"[@AITestCaseAnalyzer:analyze] Analysis complete: {len(compatible)}/{len(userinterfaces)} compatible")
        return result
    
    def _extract_device_model_from_interface(self, ui_name: str) -> str:
        """Extract device model from interface name."""
        # Common patterns: horizon_android_mobile -> android_mobile, perseus_360_web -> web
        if 'android_mobile' in ui_name:
            return 'android_mobile'
        elif 'android_tv' in ui_name:
            return 'android_tv'
        elif 'fire_tv' in ui_name:
            return 'fire_tv'
        elif 'ios_mobile' in ui_name:
            return 'ios_mobile'
        elif 'web' in ui_name:
            return 'web'
        elif 'stb' in ui_name:
            return 'stb'
        else:
            # Default fallback - try to extract last part
            parts = ui_name.split('_')
            if len(parts) >= 2:
                return '_'.join(parts[-2:])  # Take last two parts
            return ui_name
    
    def _parse_prompt_requirements(self, prompt_lower: str) -> Dict[str, bool]:
        """Parse prompt to identify required capabilities."""
        requirements = {}
        
        # Navigation requirements
        if any(word in prompt_lower for word in ['go to', 'navigate', 'open', 'menu', 'live']):
            requirements['navigation'] = True
        
        # Audio verification requirements
        if any(word in prompt_lower for word in ['audio', 'sound', 'music', 'volume', 'check audio']):
            requirements['audio_verification'] = True
        
        # Video verification requirements
        if any(word in prompt_lower for word in ['video', 'playback', 'motion', 'check video']):
            requirements['video_verification'] = True
        
        # UI interaction requirements
        if any(word in prompt_lower for word in ['click', 'tap', 'button', 'text', 'element']):
            requirements['ui_interaction'] = True
        
        return requirements
    
    def generate_test_steps(self, prompt: str, interface_name: str, 
                          navigation_graph: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Generate executable test steps using static logic.
        
        Args:
            prompt: Original natural language prompt
            interface_name: Target userinterface name
            navigation_graph: Navigation graph data (optional)
            
        Returns:
            List of test steps in AI Agent format:
            [
                {
                    'step': 1,
                    'type': 'action',
                    'command': 'execute_navigation',
                    'params': {'target_node': 'live'},
                    'description': 'Navigate to live content'
                },
                {
                    'step': 2,
                    'type': 'verification',
                    'verification_type': 'verify_audio',
                    'command': 'check_audio_quality',
                    'params': {'threshold': 0.8},
                    'description': 'Verify audio quality'
                }
            ]
        """
        print(f"[@AITestCaseAnalyzer:generate] Generating steps for: {prompt}")
        print(f"[@AITestCaseAnalyzer:generate] Interface: {interface_name}")
        
        # Parse prompt for action requirements
        required_actions = self._parse_required_actions(prompt)
        required_verifications = self._parse_required_verifications(prompt)
        
        # Generate action steps
        action_steps = self._generate_action_steps(required_actions, navigation_graph)
        
        # Generate verification steps
        verification_steps = self._generate_verification_steps(required_verifications)
        
        # Combine steps with proper sequencing
        all_steps = []
        step_counter = 1
        
        # Add action steps first
        for action in action_steps:
            action['step'] = step_counter
            action['type'] = 'action'
            all_steps.append(action)
            step_counter += 1
        
        # Add verification steps after actions
        for verification in verification_steps:
            verification['step'] = step_counter
            verification['type'] = 'verification'
            all_steps.append(verification)
            step_counter += 1
        
        print(f"[@AITestCaseAnalyzer:generate] Generated {len(all_steps)} steps ({len(action_steps)} actions, {len(verification_steps)} verifications)")
        return all_steps
    
    def _parse_prompt_intent(self, prompt: str) -> str:
        """Parse natural language prompt to understand intent."""
        prompt_lower = prompt.lower()
        
        # Identify key intents
        intents = []
        
        if any(word in prompt_lower for word in ['navigate', 'go to', 'open', 'access']):
            intents.append('navigation')
        
        if any(word in prompt_lower for word in ['check', 'verify', 'test', 'validate']):
            intents.append('verification')
        
        if any(word in prompt_lower for word in ['audio', 'sound', 'music', 'volume']):
            intents.append('audio_testing')
        
        if any(word in prompt_lower for word in ['video', 'playback', 'stream', 'live']):
            intents.append('video_testing')
        
        if any(word in prompt_lower for word in ['text', 'display', 'ui', 'screen']):
            intents.append('ui_testing')
        
        # Build understanding
        if intents:
            intent_desc = ' and '.join(intents)
            return f"Test case requires: {intent_desc}. Original prompt: '{prompt}'"
        else:
            return f"General test case analysis for: '{prompt}'"
    
    def _analyze_interface_compatibility(self, prompt: str, userinterface: Dict[str, Any], model_commands: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze compatibility between prompt and specific userinterface using real command checking."""
        ui_name = userinterface.get('name', 'unknown')
        prompt_lower = prompt.lower()
        
        # If we have real command data, use it; otherwise fallback to heuristics
        if model_commands:
            return self._analyze_with_real_commands(prompt_lower, ui_name, model_commands)
        else:
            return self._analyze_with_heuristics(prompt_lower, ui_name)
    
    def _analyze_with_real_commands(self, prompt_lower: str, ui_name: str, model_commands: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze compatibility using real command availability."""
        # Extract device model from interface name (e.g., horizon_android_mobile -> android_mobile)
        device_model = self._extract_device_model_from_interface(ui_name)
        
        if device_model not in model_commands:
            return {
                'compatible': False,
                'reasoning': f'Device model {device_model} not found in command registry',
                'confidence': 0.1,
                'missing_capabilities': ['unknown_model']
            }
        
        model_data = model_commands[device_model]
        if 'error' in model_data:
            return {
                'compatible': False,
                'reasoning': f'Error loading commands for {device_model}: {model_data["error"]}',
                'confidence': 0.1,
                'missing_capabilities': ['command_loading_error']
            }
        
        # Parse prompt to identify required capabilities
        required_capabilities = self._parse_prompt_requirements(prompt_lower)
        
        # Check if model has required commands
        available_actions = model_data.get('actions', [])
        available_verifications = model_data.get('verifications', [])
        
        missing_capabilities = []
        reasons = []
        compatibility_score = 0.5  # Base score
        
        # Check navigation capabilities
        if required_capabilities.get('navigation', False):
            has_navigation = any(action.get('command') in ['execute_navigation', 'click_element', 'tap_coordinates'] 
                               for action in available_actions)
            if has_navigation:
                compatibility_score += 0.2
                reasons.append("Has navigation capabilities")
            else:
                missing_capabilities.append('navigation commands')
        
        # Check audio verification capabilities
        if required_capabilities.get('audio_verification', False):
            has_audio = any(verif.get('command') in ['DetectAudioSpeech', 'check_audio_quality', 'AnalyzeAudioMenu'] 
                          for verif in available_verifications)
            if has_audio:
                compatibility_score += 0.3
                reasons.append("Supports audio verification")
            else:
                missing_capabilities.append('audio verification commands')
                compatibility_score -= 0.2
        
        # Check video verification capabilities
        if required_capabilities.get('video_verification', False):
            has_video = any(verif.get('command') in ['DetectMotion', 'DetectBlackscreen', 'AnalyzeVideoQuality'] 
                          for verif in available_verifications)
            if has_video:
                compatibility_score += 0.3
                reasons.append("Supports video verification")
            else:
                missing_capabilities.append('video verification commands')
                compatibility_score -= 0.2
        
        # Check text/UI interaction capabilities
        if required_capabilities.get('ui_interaction', False):
            has_ui = any(action.get('command') in ['click_element', 'tap_coordinates', 'find_element'] 
                        for action in available_actions)
            if has_ui:
                compatibility_score += 0.2
                reasons.append("Supports UI element interaction")
            else:
                missing_capabilities.append('UI interaction commands')
        
        # Determine final compatibility
        is_compatible = compatibility_score >= 0.6 and len(missing_capabilities) == 0
        confidence = min(max(compatibility_score, 0.0), 1.0)
        
        if missing_capabilities:
            reasoning = f"Missing required capabilities: {', '.join(missing_capabilities)}"
        else:
            reasoning = '; '.join(reasons) if reasons else "All required capabilities available"
        
        return {
            'compatible': is_compatible,
            'reasoning': reasoning,
            'confidence': confidence,
            'missing_capabilities': missing_capabilities,
            'available_actions_count': len(available_actions),
            'available_verifications_count': len(available_verifications)
        }
    
    def _analyze_with_heuristics(self, prompt_lower: str, ui_name: str) -> Dict[str, Any]:
        """Fallback heuristic analysis when real commands are not available."""
        compatibility_score = 0.5  # Default neutral
        reasons = []
        missing_capabilities = []
        
        # Audio-related prompts
        if any(word in prompt_lower for word in ['audio', 'sound', 'music', 'volume']):
            if 'mobile' in ui_name or 'tv' in ui_name or 'android' in ui_name:
                compatibility_score += 0.3
                reasons.append("Supports audio verification on mobile/TV platforms")
            elif 'web' in ui_name:
                compatibility_score += 0.1
                reasons.append("Limited audio verification capabilities on web")
            else:
                missing_capabilities.append('audio_verification')
        
        # Video-related prompts
        if any(word in prompt_lower for word in ['video', 'live', 'stream', 'playback']):
            if 'tv' in ui_name or 'android' in ui_name:
                compatibility_score += 0.3
                reasons.append("Excellent video capabilities on TV/Android platforms")
            elif 'mobile' in ui_name:
                compatibility_score += 0.2
                reasons.append("Good video capabilities on mobile")
            elif 'web' in ui_name:
                compatibility_score += 0.1
                reasons.append("Basic video capabilities on web")
            else:
                missing_capabilities.append('video_verification')
        
        # Navigation-related prompts
        if any(word in prompt_lower for word in ['navigate', 'go to', 'open', 'menu']):
            compatibility_score += 0.2
            reasons.append("Has navigation capabilities")
        
        # Text/UI-related prompts
        if any(word in prompt_lower for word in ['text', 'display', 'button', 'click']):
            compatibility_score += 0.2
            reasons.append("Supports UI element interaction")
        
        # Platform-specific bonuses
        if 'horizon' in ui_name and any(word in prompt_lower for word in ['live', 'tv', 'channel']):
            compatibility_score += 0.2
            reasons.append("Horizon platform optimized for TV/live content")
        
        if 'web' in ui_name and any(word in prompt_lower for word in ['browser', 'web', 'url']):
            compatibility_score += 0.2
            reasons.append("Web platform optimized for browser interactions")
        
        # Determine final compatibility
        is_compatible = compatibility_score >= 0.6
        confidence = min(compatibility_score, 1.0)
        
        if not reasons:
            reasons.append("Basic compatibility - no specific optimizations identified")
        
        return {
            'compatible': is_compatible,
            'reasoning': '. '.join(reasons),
            'confidence': confidence,
            'missing_capabilities': missing_capabilities
        }
    
    def _estimate_complexity(self, prompt: str, compatible_interfaces: List[Dict]) -> str:
        """Estimate test case complexity based on prompt and compatible interfaces."""
        prompt_lower = prompt.lower()
        
        # Count complexity indicators
        complexity_score = 0
        
        # Multiple verification types
        verification_types = 0
        if any(word in prompt_lower for word in ['audio', 'sound']):
            verification_types += 1
        if any(word in prompt_lower for word in ['video', 'visual']):
            verification_types += 1
        if any(word in prompt_lower for word in ['text', 'display']):
            verification_types += 1
        
        complexity_score += verification_types * 0.3
        
        # Navigation complexity
        if any(word in prompt_lower for word in ['navigate', 'menu', 'multiple']):
            complexity_score += 0.3
        
        # Multiple interfaces
        if len(compatible_interfaces) > 2:
            complexity_score += 0.2
        
        # Timing/coordination requirements
        if any(word in prompt_lower for word in ['wait', 'sequence', 'order']):
            complexity_score += 0.3
        
        # Determine complexity level
        if complexity_score <= 0.4:
            return 'low'
        elif complexity_score <= 0.8:
            return 'medium'
        else:
            return 'high'
    
    def _parse_required_actions(self, prompt: str) -> List[str]:
        """Parse prompt to identify required actions."""
        prompt_lower = prompt.lower()
        actions = []
        
        # Navigation actions - be more specific
        if any(word in prompt_lower for word in ['go to', 'navigate to', 'open']):
            if 'settings' in prompt_lower:
                actions.append('navigate_to_settings')
            if 'live' in prompt_lower or 'tv' in prompt_lower:
                actions.append('navigate_to_live')
            if 'menu' in prompt_lower:
                actions.append('navigate_to_menu')
            if 'recording' in prompt_lower:
                actions.append('navigate_to_recordings')
            if not any(target in prompt_lower for target in ['settings', 'live', 'tv', 'menu', 'recording']):
                actions.append('navigate_generic')
        
        # Configuration/change actions
        if any(word in prompt_lower for word in ['change', 'set', 'configure']):
            if 'language' in prompt_lower:
                actions.append('change_language')
            else:
                actions.append('change_setting')
        
        # Interaction actions
        if any(word in prompt_lower for word in ['click', 'press', 'select']):
            actions.append('click_element')
        
        # Playback actions
        if any(word in prompt_lower for word in ['play', 'start']):
            actions.append('start_playback')
        
        # Zapping/channel actions
        if any(word in prompt_lower for word in ['zap', 'channel']):
            actions.append('zap_channels')
        
        # Wait actions
        if any(word in prompt_lower for word in ['wait', 'pause']):
            actions.append('wait')
        
        return actions
    
    def _parse_required_verifications(self, prompt: str) -> List[str]:
        """Parse prompt to identify required verifications."""
        prompt_lower = prompt.lower()
        verifications = []
        
        if any(word in prompt_lower for word in ['check', 'verify', 'test']):
            if any(word in prompt_lower for word in ['audio', 'sound', 'music']):
                verifications.append('verify_audio')
            
            if any(word in prompt_lower for word in ['video', 'visual', 'playback']):
                verifications.append('verify_video')
            
            if any(word in prompt_lower for word in ['text', 'display', 'content']):
                verifications.append('verify_text')
            
            if any(word in prompt_lower for word in ['image', 'picture', 'screenshot']):
                verifications.append('verify_image')
        
        return verifications
    
    def _generate_action_steps(self, required_actions: List[str], 
                             navigation_graph: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Generate action steps based on requirements."""
        steps = []
        
        for action in required_actions:
            if action == 'navigate_to_settings':
                steps.append({
                    'command': 'execute_navigation',
                    'params': {'target_node': 'settings'},
                    'description': 'Navigate to settings'
                })
            elif action == 'navigate_to_live':
                steps.append({
                    'command': 'execute_navigation',
                    'params': {'target_node': 'live'},
                    'description': 'Navigate to live content'
                })
            elif action == 'navigate_to_menu':
                steps.append({
                    'command': 'execute_navigation', 
                    'params': {'target_node': 'main_menu'},
                    'description': 'Navigate to main menu'
                })
            elif action == 'navigate_to_recordings':
                steps.append({
                    'command': 'execute_navigation',
                    'params': {'target_node': 'recordings'},
                    'description': 'Navigate to recordings'
                })
            elif action == 'navigate_generic':
                steps.append({
                    'command': 'execute_navigation',
                    'params': {'target_node': 'home'},
                    'description': 'Navigate to specified location'
                })
            elif action == 'change_language':
                steps.append({
                    'command': 'click_element',
                    'params': {'element_id': 'language_setting'},
                    'description': 'Change language to English'
                })
            elif action == 'change_setting':
                steps.append({
                    'command': 'click_element',
                    'params': {'element_id': 'setting_option'},
                    'description': 'Change configuration setting'
                })
            elif action == 'start_playback':
                steps.append({
                    'command': 'click_element',
                    'params': {'element_id': 'play_button'},
                    'description': 'Start video playback'
                })
            elif action == 'zap_channels':
                steps.append({
                    'command': 'press_key',
                    'params': {'key': 'CHANNEL_UP'},
                    'description': 'Zap to next channel'
                })
            elif action == 'click_element':
                steps.append({
                    'command': 'click_element',
                    'params': {'element_id': 'target_element'},
                    'description': 'Click specified element'
                })
            elif action == 'wait':
                steps.append({
                    'command': 'wait',
                    'params': {'duration': 2.0},
                    'description': 'Wait for content to load'
                })
        
        return steps
    
    def _generate_verification_steps(self, required_verifications: List[str]) -> List[Dict[str, Any]]:
        """Generate verification steps based on requirements."""
        steps = []
        
        for verification in required_verifications:
            if verification == 'verify_audio':
                steps.append({
                    'verification_type': 'verify_audio',
                    'command': 'check_audio_quality',
                    'params': {'threshold': 0.8, 'duration': 5.0},
                    'description': 'Verify audio quality and presence'
                })
            elif verification == 'verify_video':
                steps.append({
                    'verification_type': 'verify_video',
                    'command': 'check_video_playback',
                    'params': {'threshold': 0.7, 'duration': 5.0},
                    'description': 'Verify video playback quality'
                })
            elif verification == 'verify_text':
                steps.append({
                    'verification_type': 'verify_text',
                    'command': 'check_text_presence',
                    'params': {'expected_text': 'target_text'},
                    'description': 'Verify expected text is displayed'
                })
            elif verification == 'verify_image':
                steps.append({
                    'verification_type': 'verify_image',
                    'command': 'check_image_content',
                    'params': {'similarity_threshold': 0.8},
                    'description': 'Verify image content matches expectations'
                })
        
        return steps
