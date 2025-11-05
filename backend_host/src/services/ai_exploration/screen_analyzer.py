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
        Phase 1: AI analyzes first screenshot and identifies all interactive elements
        
        Args:
            screenshot_path: Path to screenshot image
            
        Returns:
            {
                'menu_type': 'horizontal',
                'items': ['home', 'settings', 'profile'],
                'predicted_depth': 2,
                'strategy': 'click_elements' or 'test_dpad_directions'
            }
        """
        from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
        
        # Unified prompt for all device types
        prompt = """You are a UI-automation engineer.

From the screenshot of a streaming/TV app (Netflix, YouTube, Android TV, Apple TV, set-top-box, etc.), list every visible item or clickable elements (tabs). Avoid none interactive content: asset, program card, program name, duration or time. Provide the list in the order left to right on same line.

Example output:

profile, sunrise, cast, airplay, search
popular_on_tv, show all
home, tvguide, replay, movies_and_series, saved, debug

Return ONLY the lines of comma-separated items, nothing else."""

        # Determine device type for post-processing
        is_mobile_or_web = self.device_model_name and ('mobile' in self.device_model_name.lower() or 'web' in self.device_model_name.lower())

        print(f"\n{'='*80}")
        print(f"[@screen_analyzer:anticipate_tree] PHASE 1 AI ANALYSIS")
        print(f"{'='*80}")
        print(f"📸 Screenshot Path: {screenshot_path}")
        print(f"🎮 Device Type: {'MOBILE/WEB (click-based)' if is_mobile_or_web else 'TV/STB (DPAD-based)'}")
        print(f"\n📝 PROMPT SENT TO AI:")
        print(f"{'-'*80}")
        print(prompt)
        print(f"{'-'*80}\n")

        try:
            # Use existing VideoAIHelpers for AI analysis
            # VideoAIHelpers needs av_controller, but we'll pass None and use direct file path
            from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
            
            ai_helpers = VideoAIHelpers(
                av_controller=None,  # We're passing file path directly
                device_name=self.device_id
            )
            
            # Use analyze_full_image_with_ai which exists
            response = ai_helpers.analyze_full_image_with_ai(
                image_path=screenshot_path,
                user_question=prompt
            )
            
            print(f"🤖 RAW AI RESPONSE:")
            print(f"{'-'*80}")
            print(response)
            print(f"{'-'*80}\n")
            
            # Parse line-by-line response
            # Expected format:
            # profile, sunrise, cast, airplay, search
            # popular_on_tv, show all
            # home, tvguide, replay, movies_and_series, saved, debug
            
            lines = []
            all_items = []
            
            # Split response into lines and parse each
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('Example'):
                    # Extract items from this line
                    items_in_line = [item.strip() for item in line.split(',') if item.strip()]
                    if items_in_line:
                        lines.append(items_in_line)
                        all_items.extend(items_in_line)
            
            # Determine menu structure from lines
            if len(lines) == 1:
                menu_type = 'horizontal'
            elif len(lines) > 1:
                # Check if it's vertical (1 item per line) or grid (multiple items per line)
                if all(len(line) == 1 for line in lines):
                    menu_type = 'vertical'
                else:
                    menu_type = 'mixed'  # Has both horizontal and vertical navigation
            else:
                menu_type = 'unknown'
            
            # Determine strategy based on device type
            strategy = 'click_elements' if is_mobile_or_web else 'test_dpad_directions'
            
            result = {
                'menu_type': menu_type,
                'items': all_items,
                'lines': lines,  # Keep line structure for navigation logic
                'predicted_depth': 2,
                'strategy': strategy
            }
            
            print(f"✅ PARSED RESULT:")
            print(f"{'-'*80}")
            print(f"Items ({len(all_items)}):")
            for i, line in enumerate(lines, 1):
                print(f"Line {i}: {', '.join(line)}")
            print(f"{'-'*80}\n")
            
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
            from backend_host.src.controllers.verification.video_ai_helpers import VideoAIHelpers
            
            ai_helpers = VideoAIHelpers(
                av_controller=None,  # We're passing file path directly
                device_name=self.device_id
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
                    
                    print(f"\n{'='*80}")
                    print(f"[@screen_analyzer:capture_screenshot] SCREENSHOT CAPTURED")
                    print(f"{'='*80}")
                    print(f"📸 Local Path: {cold_path}")
                    print(f"📁 Device Folder: {device_folder}")
                    print(f"📝 Filename: {filename}")
                    print(f"{'='*80}\n")
                    
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

