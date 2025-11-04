"""
Screen Analyzer - AI vision analysis using VideoAIHelpers
Analyzes screenshots to understand menu structure and detect screen changes
"""

from typing import Dict, Optional
import json


class ScreenAnalyzer:
    """AI vision analysis using existing VideoAIHelpers"""
    
    def __init__(self, device_id: str, host_name: str, ai_model: str = 'qwen'):
        """
        Initialize with device context
        
        Args:
            device_id: Device ID
            host_name: Host name
            ai_model: 'qwen' (default), later: user-selectable
        """
        self.device_id = device_id
        self.host_name = host_name
        self.ai_model = ai_model
        
    def anticipate_tree(self, screenshot_path: str) -> Dict:
        """
        Phase 1: Analyze first screenshot and predict tree structure
        
        Args:
            screenshot_path: Path to screenshot image
            
        Returns:
            {
                'menu_type': 'horizontal',
                'items': ['home', 'settings', 'profile'],
                'predicted_depth': 2,
                'strategy': 'test_right_left_first_then_ok'
            }
        """
        from services.video_ai.video_ai_helpers import VideoAIHelpers
        
        prompt = """Analyze this menu screen and predict the navigation structure.

Please identify:
1. Menu type: Is it horizontal, vertical, grid, or mixed?
2. Number of menu items visible
3. Names of menu items (what you can read on screen)
4. Predicted navigation depth (how many levels deep can you go?)

Return ONLY valid JSON in this exact format:
{
    "menu_type": "horizontal",
    "items": ["item1", "item2", "item3"],
    "predicted_depth": 2,
    "strategy": "test_right_left_first_then_ok"
}

Menu type must be one of: horizontal, vertical, grid, mixed
Strategy describes the exploration approach based on menu type."""

        try:
            # Use existing VideoAIHelpers for AI analysis
            response = VideoAIHelpers.analyze_with_vision(
                screenshot_path=screenshot_path,
                prompt=prompt,
                model_name=self.ai_model
            )
            
            print(f"[@screen_analyzer:anticipate_tree] AI response: {response}")
            
            # Parse JSON from response
            result = self._parse_json_response(response)
            
            if not result:
                # Fallback to safe defaults
                return {
                    'menu_type': 'mixed',
                    'items': [],
                    'predicted_depth': 3,
                    'strategy': 'test_all_directions'
                }
            
            return result
            
        except Exception as e:
            print(f"[@screen_analyzer:anticipate_tree] Error: {e}")
            # Return safe defaults on error
            return {
                'menu_type': 'mixed',
                'items': [],
                'predicted_depth': 3,
                'strategy': 'test_all_directions'
            }
    
    def is_new_screen(
        self,
        before_path: str,
        after_path: str,
        action: str
    ) -> Dict:
        """
        Phase 2: After OK/BACK action, determine if we reached new screen
        
        Args:
            before_path: Screenshot before action
            after_path: Screenshot after action
            action: Action taken (e.g., 'OK', 'BACK')
            
        Returns:
            {
                'is_new_screen': True,
                'context_visible': False,
                'suggested_name': 'settings',
                'screen_type': 'menu',
                'reasoning': 'Completely different screen...'
            }
        """
        from services.video_ai.video_ai_helpers import VideoAIHelpers
        
        prompt = f"""Compare these two screenshots after action '{action}'.

Please answer:
1. Is this a NEW SCREEN (completely different UI) or SAME SCREEN (just focus changed)?
2. Can you still see the previous menu? (Yes/No)
3. What is a good name for this screen based on visible content?
4. What type of screen is this? (menu, settings, content, info, player, etc.)
5. Brief reasoning for your decision

Return ONLY valid JSON in this exact format:
{{
    "is_new_screen": true,
    "context_visible": false,
    "suggested_name": "settings",
    "screen_type": "menu",
    "reasoning": "Completely different screen, cannot see previous menu"
}}

Context visible = Can you still see elements from the previous screen?
"""

        try:
            # Use existing VideoAIHelpers with both images
            response = VideoAIHelpers.analyze_with_vision(
                screenshot_path=before_path,
                prompt=prompt,
                model_name=self.ai_model
            )
            
            print(f"[@screen_analyzer:is_new_screen] AI response: {response}")
            
            # Parse JSON from response
            result = self._parse_json_response(response)
            
            if not result:
                # Fallback: assume it's a new screen
                return {
                    'is_new_screen': True,
                    'context_visible': False,
                    'suggested_name': 'screen',
                    'screen_type': 'screen',
                    'reasoning': 'Could not determine, assuming new screen'
                }
            
            return result
            
        except Exception as e:
            print(f"[@screen_analyzer:is_new_screen] Error: {e}")
            # Return safe defaults on error
            return {
                'is_new_screen': True,
                'context_visible': False,
                'suggested_name': 'screen',
                'screen_type': 'screen',
                'reasoning': f'Error during analysis: {str(e)}'
            }
    
    def capture_screenshot(self) -> Optional[str]:
        """
        Capture screenshot using VideoAIHelpers
        
        Returns:
            Screenshot file path or None on error
        """
        from services.video_ai.video_ai_helpers import VideoAIHelpers
        
        try:
            screenshot_path = VideoAIHelpers.capture_screenshot(
                device_id=self.device_id,
                host_name=self.host_name
            )
            
            print(f"[@screen_analyzer:capture_screenshot] Captured: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            print(f"[@screen_analyzer:capture_screenshot] Error: {e}")
            return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """
        Parse JSON from AI response text
        
        Args:
            response: Raw AI response (may contain text + JSON)
            
        Returns:
            Parsed dict or None if failed
        """
        try:
            # Try direct JSON parse first
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                if end != -1:
                    json_str = response[start:end].strip()
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
            
            # Try to find JSON object in text
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                json_str = response[start:end+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            print(f"[@screen_analyzer:_parse_json_response] Failed to parse JSON from: {response[:200]}")
            return None

