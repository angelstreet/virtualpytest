"""
Screen Analyzer - AI vision analysis using VideoAIHelpers
Analyzes screenshots to understand menu structure and detect screen changes
"""

from typing import Dict, Optional
import json


class ScreenAnalyzer:
    """AI vision analysis using existing VideoAIHelpers"""
    
    def __init__(self, device_id: str, host_name: str, device_model_name: str = None, controller = None, ai_model: str = 'qwen'):
        """
        Initialize with device context
        
        Args:
            device_id: Device ID
            host_name: Host name
            device_model_name: Device model (e.g., 'android_mobile') for screenshot source selection
            controller: Remote controller instance (for android_mobile native screenshots)
            ai_model: 'qwen' (default), later: user-selectable
        """
        self.device_id = device_id
        self.host_name = host_name
        self.device_model_name = device_model_name
        self.controller = controller
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
        from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
        
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
            # Create instance with device info
            ai_helpers = VideoAIHelpers(
                device_name=self.device_id,
                device_model=self.device_model_name,
                host_name=self.host_name
            )
            
            # Use analyze_full_image_with_ai which exists
            response = ai_helpers.analyze_full_image_with_ai(
                image_path=screenshot_path,
                user_question=prompt
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
        from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
        
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
            # Create instance with device info
            ai_helpers = VideoAIHelpers(
                device_name=self.device_id,
                device_model=self.device_model_name,
                host_name=self.host_name
            )
            
            # Use analyze_full_image_with_ai for the after screenshot
            response = ai_helpers.analyze_full_image_with_ai(
                image_path=after_path,
                user_question=prompt
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
        Capture screenshot and save to cold storage:
        - android_mobile: Use ADB native screenshot (exact display buffer)
        - Other devices: Use HDMI capture via VideoAIHelpers
        
        Returns:
            Screenshot file path in COLD storage or None on error
        """
        try:
            import shutil
            from datetime import datetime
            from shared.src.lib.utils.storage_path_utils import get_captures_path, get_capture_folder_from_device_id
            
            # Get device capture folder
            try:
                device_folder = get_capture_folder_from_device_id(self.device_id)
            except ValueError as e:
                print(f"[@screen_analyzer:capture_screenshot] Error getting device folder: {e}")
                return None
            
            # For android_mobile, use native ADB screenshot
            if self.device_model_name and 'mobile' in self.device_model_name.lower() and self.controller:
                success, base64_data, error = self.controller.take_screenshot()
                if success and base64_data:
                    # Convert base64 to image data
                    import base64
                    image_data = base64.b64decode(base64_data)
                    
                    # Save to COLD storage (captures path)
                    captures_path = get_captures_path(device_folder)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"ai_exploration_{timestamp}.png"
                    cold_path = f"{captures_path}/{filename}"
                    
                    # Ensure directory exists
                    import os
                    os.makedirs(captures_path, exist_ok=True)
                    
                    # Write to cold storage
                    with open(cold_path, 'wb') as f:
                        f.write(image_data)
                    
                    print(f"[@screen_analyzer:capture_screenshot] Saved to cold storage: {cold_path}")
                    return cold_path
            
            # Fallback to HDMI capture for all other devices
            from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
            temp_screenshot = VideoAIHelpers.capture_screenshot(self.device_id, self.host_name)
            
            if temp_screenshot:
                # Copy to cold storage
                captures_path = get_captures_path(device_folder)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"ai_exploration_{timestamp}.png"
                cold_path = f"{captures_path}/{filename}"
                
                # Ensure directory exists
                import os
                os.makedirs(captures_path, exist_ok=True)
                
                # Copy file
                shutil.copy2(temp_screenshot, cold_path)
                print(f"[@screen_analyzer:capture_screenshot] Copied to cold storage: {cold_path}")
                return cold_path
            
            return None
            
        except Exception as e:
            print(f"[@screen_analyzer:capture_screenshot] Error: {e}")
            import traceback
            traceback.print_exc()
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

