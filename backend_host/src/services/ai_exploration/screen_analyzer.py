"""
Screen Analyzer - AI vision analysis using VideoAIHelpers
Analyzes screenshots to understand menu structure and detect screen changes
"""

from typing import Dict, Optional
import json


class ScreenAnalyzer:
    """AI vision analysis using existing VideoAIHelpers"""
    
    def __init__(self, device, controller=None, ai_model: str = 'qwen'):
        """
        Initialize with device context
        
        Args:
            device: Device instance (from ExplorationEngine)
            controller: Remote controller instance (for android_mobile native screenshots)
            ai_model: 'qwen' (default), later: user-selectable
        """
        self.device = device
        self.device_id = device.device_id
        self.host_name = device.host_name
        self.device_model_name = device.device_model
        self.controller = controller
        self.ai_model = ai_model
        
    def anticipate_tree(self, screenshot_path: str) -> Dict:
        """
        Phase 1: Analyze first screenshot and identify all interactive elements
        
        For mobile/web: Use UI dump to extract interactive elements
        For TV/STB: Use AI vision to identify menu items
        
        Args:
            screenshot_path: Path to screenshot image
            
        Returns:
            {
                'menu_type': 'horizontal',
                'items': ['home', 'settings', 'profile'],
                'lines': [['home', 'settings'], ['profile']],
                'predicted_depth': 2,
                'strategy': 'click_elements' or 'test_dpad_directions'
            }
        """
        # Determine if device uses click (mobile/web) or DPAD (TV/STB)
        is_mobile_or_web = self.device_model_name and ('mobile' in self.device_model_name.lower() or 'web' in self.device_model_name.lower())
        
        print(f"\n{'='*80}")
        print(f"[@screen_analyzer:anticipate_tree] PHASE 1 ANALYSIS")
        print(f"{'='*80}")
        print(f"📸 Screenshot Path: {screenshot_path}")
        print(f"🎮 Device Type: {'MOBILE/WEB (dump-based)' if is_mobile_or_web else 'TV/STB (AI vision-based)'}")
        
        if is_mobile_or_web:
            # Use UI dump for mobile/web
            return self._analyze_from_dump(screenshot_path)
        else:
            # Use AI vision for TV/STB
            return self._analyze_from_ai_vision(screenshot_path)
    
    def _analyze_from_dump(self, screenshot_path: str) -> Dict:
        """
        Extract interactive elements from UI dump (mobile/web only)
        Fails fast if dump is not available - no fallback
        """
        print(f"\n📱 USING UI DUMP ANALYSIS")
        print(f"{'-'*80}")
        
        # Both mobile and web now use unified dump_elements()
        print(f"[@screen_analyzer] Using unified dump_elements() method")
        
        # Try calling dump_elements - signature varies by controller type
        result = self.controller.dump_elements()
        
        # Handle different return types
        if isinstance(result, dict):
            # Web returns dict: {success: bool, elements: list, ...}
            if not result.get('success'):
                error = result.get('error', 'Unknown error')
                raise Exception(f"Failed to get UI dump - cannot proceed: {error}")
            
            elements = result.get('elements', [])
            if not elements:
                raise Exception("No elements found in UI dump")
            
            # Parse web elements (dict format)
            interactive_elements = self._extract_interactive_elements_web(elements)
        else:
            # Mobile returns tuple: (success, elements, error)
            success, elements, error = result
            
            if not success:
                raise Exception(f"Failed to get UI dump - cannot proceed: {error}")
            
            # Parse mobile elements (AndroidElement objects)
            interactive_elements = self._extract_interactive_elements_mobile(elements)
        
        if not interactive_elements:
            raise Exception("No interactive elements found in UI dump")
        
        print(f"✅ EXTRACTED FROM DUMP:")
        print(f"{'-'*80}")
        print(f"Items ({len(interactive_elements)}):")
        print(f"Elements: {', '.join(interactive_elements)}")
        print(f"{'-'*80}\n")
        
        return {
            'menu_type': 'click_based',  # Mobile/web = click-based, no line structure
            'items': interactive_elements,
            'lines': [],  # No lines for click-based navigation
            'predicted_depth': 2,
            'strategy': 'click_elements'
        }
    
    def _extract_interactive_elements_mobile(self, elements: list) -> list:
        """
        Parse mobile UI dump elements (AndroidElement objects)
        Extract both static navigation + dynamic content
        
        Args:
            elements: List of AndroidElement objects from dump_elements()
        
        Returns:
            List of element names (strings)
        """
        interactive_elements = []
        
        # Filter out common non-interactive text
        ignore_keywords = ['image', 'icon', 'loading', 'placeholder', '...', 'content', 'decoration']
        
        # UI accessibility hints to strip (before dynamic content detection)
        # ONLY strip instructions/state, NOT element types (Tab, Button, etc.)
        accessibility_patterns = [
            ', Double-tap to Open',
            ', Double-tap to activate',
            ', Double-tap to select',
            ' currently selected',
        ]
        
        # Dynamic content indicators (program titles, prices, descriptions)
        dynamic_indicators = [
            'available for replay', 'watch now', 'continue watching',
            'chf', 'usd', 'eur', 'gbp', '$', '€', '£',  # Price indicators
            ' - ',  # Time ranges like "21:10 - 23:10"
            ' from ', ' to ',  # Alternate time/price ranges
            'season ', 'episode ', 's0', 'e0',  # TV series
            'podcast ',  # Podcast titles
            ','  # Titles often have commas (e.g., "Show Name, Description")
        ]
        
        # Navigation keywords that should NOT be filtered (even if they match above)
        # These are common navigation tab names that we MUST keep
        navigation_whitelist = ['replay', 'radio', 'guide', 'tv', 'home', 'search', 'settings', 'accueil']
        
        # UI element type keywords (multilingual) - elements containing these get more lenient filtering
        # These indicate proper UI elements, not dynamic content
        ui_element_keywords = [
            'button', 'btn', 'bouton',  # Button (EN, abbrev, FR)
            'tab', 'onglet',  # Tab (EN, FR)
            'selected', 'sélectionné', 'seleccionado',  # Selected (EN, FR, ES)
            'menu', 'menü',  # Menu (EN, DE)
            'switch', 'toggle',  # Toggle switches
            'checkbox', 'radio',  # Form controls
        ]
        
        for elem in elements:
            # ✅ FIX: Don't require clickable=true
            # TextViews in navigation bars (bottom tabs, top tabs) are NOT marked clickable
            # but they ARE navigation elements. We'll filter by content instead.
            # Only skip if it's a container or decoration (checked via keywords)
            
            # Get the best label for this element
            label = None
            
            # Priority 1: text
            if elem.text and elem.text != '<no text>' and elem.text.strip():
                label = elem.text.strip()
            # Priority 2: content_desc
            elif elem.content_desc and elem.content_desc != '<no content-desc>' and elem.content_desc.strip():
                label = elem.content_desc.strip()
            # Priority 3: resource_id (extract last part after /)
            elif elem.resource_id and elem.resource_id != '<no resource-id>' and elem.resource_id.strip():
                # Extract meaningful part from resource ID like "com.example:id/button_name"
                resource_id = elem.resource_id.strip()
                if '/' in resource_id:
                    label = resource_id.split('/')[-1]
                else:
                    label = resource_id
            
            # Skip if no useful label
            if not label:
                continue
            
            # Filter out non-interactive keywords
            if any(keyword in label.lower() for keyword in ignore_keywords):
                continue
            
            # ✅ CLEAN: Strip accessibility hints BEFORE dynamic content detection
            original_label = label
            for pattern in accessibility_patterns:
                if pattern.lower() in label.lower():
                    # Case-insensitive removal
                    import re
                    label = re.sub(re.escape(pattern), '', label, flags=re.IGNORECASE).strip()
            
            # Clean up extra commas/spaces after stripping
            label = label.rstrip(',').strip()
            
            # Skip if label became empty after cleaning
            if not label:
                continue
            
            # ✅ Detect and SKIP dynamic content (AFTER cleaning accessibility text)
            # 1. Very long labels (> 30 chars) = likely program description
            # 2. Contains time patterns or content indicators
            # BUT: Don't skip common navigation keywords even if they match
            
            # Check if it's a navigation keyword (whitelist)
            is_navigation = any(nav.lower() == label.lower() for nav in navigation_whitelist)
            
            # Check if label contains UI element type keywords (more lenient filtering)
            contains_ui_keyword = any(keyword in label.lower() for keyword in ui_element_keywords)
            
            # Determine length threshold based on whether it's a UI element
            if contains_ui_keyword:
                length_threshold = 40  # More lenient for UI elements with metadata
                print(f"[@screen_analyzer:_extract_interactive_elements_mobile] 🏷️  UI element detected: '{label}' | using threshold={length_threshold}")
            else:
                length_threshold = 30  # Standard threshold for other elements
            
            if not is_navigation:
                # Not a whitelisted navigation keyword, apply dynamic content filter
                if len(label) > length_threshold or any(indicator in label.lower() for indicator in dynamic_indicators):
                    print(f"[@screen_analyzer:_extract_interactive_elements_mobile] 🚫 FILTERED: Dynamic content | label='{label}' | len={len(label)} | threshold={length_threshold} | elem.id={elem.id}")
                    continue  # Skip dynamic content
            
            # Add to list (avoid duplicates)
            if label not in interactive_elements:
                interactive_elements.append(label)
                print(f"[@screen_analyzer:_extract_interactive_elements_mobile] ✅ KEPT: '{label}' | elem.id={elem.id} | clickable={elem.clickable}")
            else:
                print(f"[@screen_analyzer:_extract_interactive_elements_mobile] 🔁 DUPLICATE: '{label}' | elem.id={elem.id}")
        
        return interactive_elements[:20]  # Limit to top 20 elements
    
    def _extract_interactive_elements_web(self, elements: list) -> list:
        """
        Parse web UI dump elements (dict objects from Playwright)
        Extract both static navigation + dynamic content
        
        Args:
            elements: List of dict objects from dump_elements()
                     Each dict has: text, tag, selector, visible, clickable, etc.
        
        Returns:
            List of element names (strings)
        """
        interactive_elements = []
        
        # Filter out common non-interactive keywords
        ignore_keywords = ['image', 'icon', 'loading', 'placeholder', 'decoration', 'logo']
        
        # UI accessibility hints to strip (before dynamic content detection)
        # ONLY strip instructions/state, NOT element types (Tab, Button, etc.)
        accessibility_patterns = [
            ', Double-tap to Open',
            ', Double-tap to activate',
            ', Double-tap to select',
            ' currently selected',
        ]
        
        # Dynamic content indicators (same as mobile)
        dynamic_indicators = [
            'available for replay', 'watch now', 'continue watching',
            'chf', 'usd', 'eur', 'gbp', '$', '€', '£',  # Price indicators
            ' from ', ' to ',  # Time/price ranges
            'season ', 'episode ', 's0', 'e0',  # TV series
            ','  # Titles often have commas (e.g., "Show Name, Description")
        ]
        
        for elem in elements:
            # Web elements are already filtered to 'interactive' type
            # Get the best label
            label = None
            
            # Priority 1: text content
            if elem.get('text') and elem['text'].strip():
                label = elem['text'].strip()
            # Priority 2: aria-label
            elif elem.get('aria_label') and elem['aria_label'].strip():
                label = elem['aria_label'].strip()
            # Priority 3: placeholder
            elif elem.get('placeholder') and elem['placeholder'].strip():
                label = elem['placeholder'].strip()
            # Priority 4: Extract from selector (last part)
            elif elem.get('selector'):
                selector = elem['selector']
                if '#' in selector:
                    label = selector.split('#')[-1]
                elif '.' in selector:
                    label = selector.split('.')[-1]
            
            # Skip if no useful label
            if not label:
                continue
            
            # Filter out non-interactive keywords
            if any(keyword in label.lower() for keyword in ignore_keywords):
                continue
            
            # ✅ CLEAN: Strip accessibility hints BEFORE dynamic content detection
            import re
            for pattern in accessibility_patterns:
                if pattern.lower() in label.lower():
                    # Case-insensitive removal
                    label = re.sub(re.escape(pattern), '', label, flags=re.IGNORECASE).strip()
            
            # Clean up extra commas/spaces after stripping
            label = label.rstrip(',').strip()
            
            # Skip if label became empty after cleaning
            if not label:
                continue
            
            # ✅ Detect and SKIP dynamic content (AFTER cleaning accessibility text)
            # 1. Very long labels (> 30 chars) = likely program description
            # 2. Contains price, time, or content indicators
            # We SKIP these because we can't click on "dynamic_1" - it's not a real element
            if len(label) > 30 or any(indicator in label.lower() for indicator in dynamic_indicators):
                continue  # Skip dynamic content entirely
            
            # Add to list (avoid duplicates)
            if label not in interactive_elements:
                interactive_elements.append(label)
        
        return interactive_elements[:20]  # Limit to top 20 elements
    
    def _analyze_from_ai_vision(self, screenshot_path: str) -> Dict:
        """
        Use AI vision to analyze screenshot (TV/STB only)
        """
        # Unified prompt for TV/STB
        prompt = """You are a UI-automation engineer.

From the screenshot of a streaming/TV app (Netflix, YouTube, Android TV, Apple TV, set-top-box, etc.), list every visible item or clickable elements (tabs). Avoid none interactive content: asset, program card, program name, duration or time. Provide the list in the order left to right on same line.

Example output:

profile, sunrise, cast, airplay, search
popular_on_tv, show all
home, tvguide, replay, movies_and_series, saved, debug

Return ONLY the lines of comma-separated items, nothing else."""

        print(f"\n📝 AI VISION ANALYSIS")
        print(f"{'-'*80}")
        print(f"PROMPT SENT TO AI:")
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
            
            # Strategy for TV/STB is always DPAD
            strategy = 'test_dpad_directions'
            
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
            
            # Fallback to HDMI capture for all other devices using device's AV controller
            av_controller = self.device._get_controller('av')
            if not av_controller:
                print(f"[@screen_analyzer:capture_screenshot] ❌ FAIL EARLY: No AV controller found for device {self.device_id}")
                return None
            
            print(f"[@screen_analyzer:capture_screenshot] Attempting HDMI capture via AV controller...")
            temp_screenshot = av_controller.take_screenshot()
            
            if not temp_screenshot:
                print(f"[@screen_analyzer:capture_screenshot] ❌ FAIL EARLY: AV controller returned None/empty")
                return None
            
            # Verify file exists
            import os
            if not os.path.exists(temp_screenshot):
                print(f"[@screen_analyzer:capture_screenshot] ❌ FAIL EARLY: Screenshot file doesn't exist: {temp_screenshot}")
                return None
            
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

