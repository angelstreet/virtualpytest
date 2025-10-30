"""
Real Android Mobile Remote Controller Implementation

This controller provides real Android mobile remote control functionality using ADB.
Key difference from TV controller: focuses on UI element dumping and clicking rather than just key presses.
Based on the ADB actions pattern and RecAndroidPhoneRemote component.
"""

from typing import Dict, Any, List, Optional, Tuple
import subprocess
import time
import json
import os
from pathlib import Path
from ..base_controller import RemoteControllerInterface

# Use absolute import from shared library
import sys
import os
# Get path to shared/lib/utils (go up to project root)
# Import local utilities

from  backend_host.src.lib.utils.adb_utils import ADBUtils, AndroidElement, AndroidApp


class AndroidMobileRemoteController(RemoteControllerInterface):
    """Real Android mobile remote controller using SSH + ADB with UI element support."""
    
    @staticmethod
    def get_remote_config() -> Dict[str, Any]:
        """Get the remote configuration including layout, buttons, and image."""
        # Load configuration from JSON file
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'config', 'remote', 'android_mobile_remote.json'
        )
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Android Mobile remote config file not found at: {config_path}")
            
        try:
            print(f"Loading Android Mobile remote config from: {config_path}")
            with open(config_path, 'r') as config_file:
                return json.load(config_file)
        except Exception as e:
            raise RuntimeError(f"Error loading Android Mobile remote config from file: {e}")
    
    def __init__(self, device_ip: str, device_port: int = 5555, **kwargs):
        """
        Initialize the Android mobile remote controller.
        
        Args:
            device_ip: Android device IP address (required)
            device_port: ADB port (default: 5555)
        """
        super().__init__("Android Mobile", "android_mobile")
        
        # Android device parameters
        self.device_ip = device_ip
        self.device_port = device_port
        
        # Validate required parameters
        if not self.device_ip:
            raise ValueError("device_ip is required for AndroidMobileRemoteController")
            
        self.android_device_id = f"{self.device_ip}:{self.device_port}"
        self.adb_utils = None
        self.device_resolution = None
        
        # UI elements state
        self.last_ui_elements = []
        self.last_dump_time = 0
        
        self.connect()
    
    def connect(self) -> bool:
        """Connect to Android device via ADB."""
        try:
            # Initialize ADB utilities with direct connection
            self.adb_utils = ADBUtils()
            
            # Connect to Android device via ADB
            if not self.adb_utils.connect_device(self.android_device_id):
                print(f"Remote[{self.device_type.upper()}]: Failed to connect to Android device {self.android_device_id}")
                return False
                
            # Get device resolution
            self.device_resolution = self.adb_utils.get_device_resolution(self.android_device_id)
            
            # Single consolidated success message
            resolution_info = f"{self.device_resolution['width']}x{self.device_resolution['height']}" if self.device_resolution else "unknown"
            print(f"Remote[{self.device_type.upper()}]: Connected to {self.android_device_id}, resolution: {resolution_info}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Connection error: {e}")
            return False
            
    def disconnect(self) -> bool:
        """Disconnect from Android device."""
        try: 
            # Clean up ADB connection
            self.adb_utils = None
            self.is_connected = False
            
            print(f"Remote[{self.device_type.upper()}]: Disconnected successfully")
            return True
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Disconnect error: {e}")
            self.is_connected = False
            return False
            
    def press_key(self, key: str) -> bool:
        """
        Send a key press to the Android device.
        
        Args:
            key: Key name (e.g., "UP", "DOWN", "HOME", "BACK", "VOLUME_UP", "VOLUME_DOWN")
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Pressing key '{key}'")
            
            success = self.adb_utils.execute_key_command(self.android_device_id, key)
            
            if success:
                print(f"Remote[{self.device_type.upper()}]: Successfully pressed key '{key}'")
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to press key '{key}'")
                
            return success
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Key press error: {e}")
            return False
            
    def input_text(self, text: str) -> bool:
        """
        Send text input to the Android device.
        
        Args:
            text: Text to input
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Inputting text: '{text}'")
            
            success = self.adb_utils.input_text(self.android_device_id, text)
            
            if success:
                print(f"Remote[{self.device_type.upper()}]: Successfully input text")
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to input text")
                
            return success
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Text input error: {e}")
            return False
            

            
    def launch_app(self, package_name: str) -> bool:
        """
        Launch an app by package name.
        
        Args:
            package_name: Android package name (e.g., "com.android.settings")
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Launching app: {package_name}")
            
            success = self.adb_utils.launch_app(self.android_device_id, package_name)
            
            if success:
                print(f"Remote[{self.device_type.upper()}]: Successfully launched {package_name}")
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to launch {package_name}")
                
            return success
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: App launch error: {e}")
            return False
            
    def close_app(self, package_name: str) -> bool:
        """
        Close/stop an app by package name.
        
        Args:
            package_name: Android package name (e.g., "com.android.settings")
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Closing app: {package_name}")
            
            success = self.adb_utils.close_app(self.android_device_id, package_name)
            
            if success:
                print(f"Remote[{self.device_type.upper()}]: Successfully closed {package_name}")
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to close {package_name}")
                
            return success
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: App close error: {e}")
            return False
            
    def get_installed_apps(self) -> List[AndroidApp]:
        """
        Get list of installed apps on the device.
        
        Returns:
            List of AndroidApp objects
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Getting installed apps")
            
            apps = self.adb_utils.get_installed_apps(self.android_device_id)
            
            print(f"Remote[{self.device_type.upper()}]: Found {len(apps)} installed apps")
            return apps
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Error getting apps: {e}")
            return []
            
    def dump_ui_elements(self) -> Tuple[bool, List[AndroidElement], str]:
        """
        Dump UI elements from the current screen.
        
        Returns:
            Tuple of (success, elements_list, error_message)
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Dumping UI elements")
            
            success, elements, error = self.adb_utils.dump_ui_elements(self.android_device_id)
            
            if success:
                self.last_ui_elements = elements
                self.last_dump_time = time.time()
                print(f"Remote[{self.device_type.upper()}]: Successfully dumped {len(elements)} UI elements")
                
                # Log each element in one line with requested format: name, index, order, x, y, width, height
                import re
                for i, element in enumerate(elements):
                    # Get element name with same priority as frontend: content_desc → text → class_name
                    name = ""
                    
                    # Priority 1: content_desc (same as frontend contentDesc)
                    if (element.content_desc and 
                        element.content_desc != '<no content-desc>' and 
                        element.content_desc.strip() != ''):
                        name = element.content_desc.strip()
                    # Priority 2: text (same as frontend text)
                    elif (element.text and 
                          element.text != '<no text>' and 
                          element.text.strip() != ''):
                        name = f'"{element.text.strip()}"'
                    # Priority 3: class_name (same as frontend className)
                    else:
                        class_name = element.class_name.split('.')[-1] if element.class_name else "Unknown"
                        name = class_name
                    
                    # Parse bounds to get x, y, width, height
                    x, y, width, height = 0, 0, 0, 0
                    if hasattr(element, 'bounds') and isinstance(element.bounds, str) and element.bounds:
                        # AndroidElement format: '[x1,y1][x2,y2]'
                        bounds_match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', element.bounds)
                        if bounds_match:
                            x1, y1, x2, y2 = map(int, bounds_match.groups())
                            x, y = x1, y1
                            width, height = x2 - x1, y2 - y1
                    
                    print(f"Remote[{self.device_type.upper()}]: Element: {name} | Index: {element.id} | Order: {i+1} | X: {x} | Y: {y} | Width: {width} | Height: {height}")
            else:
                print(f"Remote[{self.device_type.upper()}]: UI dump failed: {error}")
                
            return success, elements, error
            
        except Exception as e:
            error_msg = f"Error dumping UI elements: {e}"
            print(f"Remote[{self.device_type.upper()}]: {error_msg}")
            return False, [], error_msg
            
    def click_element_by_id(self, element: AndroidElement) -> bool:
        """
        PRIVATE: Click on a UI element (for internal/frontend use only).
        This method is used by routes/frontend after UI dump, not exposed in available actions.
        
        Args:
            element: AndroidElement to click
            
        Returns:
            bool: True if click successful
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Clicking element ID={element.id}, text='{element.text}'")
            
            success = self.adb_utils.click_element(self.android_device_id, element)
            
            if success:
                print(f"Remote[{self.device_type.upper()}]: Successfully clicked element")
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to click element")
                
            return success
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Element click error: {e}")
            return False
            
    def click_element(self, element_identifier: str) -> bool:
        """
        Click element directly by text, resource_id, or content_desc using simple ADB command.
        Supports pipe-separated fallback: "Settings|Preferences|Options"
        
        Args:
            element_identifier: Text, resource ID, or content description to click
                                Can use pipe "|" to specify multiple options (tries each until one succeeds)
            
        Returns:
            bool: True if click successful
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Direct click on element: '{element_identifier}'")
            
            # Parse pipe-separated terms for fallback support
            terms = [t.strip() for t in element_identifier.split('|')] if '|' in element_identifier else [element_identifier]
            
            if len(terms) > 1:
                print(f"Remote[{self.device_type.upper()}]: Using fallback strategy with {len(terms)} terms: {terms}")
            
            # Try each term until one succeeds
            last_error = None
            for i, term in enumerate(terms):
                if len(terms) > 1:
                    print(f"Remote[{self.device_type.upper()}]: Attempt {i+1}/{len(terms)}: Searching for '{term}'")
                
                # Find element using single UI dump
                exists, element, error = self.adb_utils.check_element_exists(self.android_device_id, term)
                
                if exists and element:
                    # Directly click the found element instead of re-searching (avoids double UI dump)
                    success = self.adb_utils.click_element(self.android_device_id, element)
                    
                    if success:
                        if len(terms) > 1:
                            print(f"Remote[{self.device_type.upper()}]: Successfully clicked using term '{term}'")
                        else:
                            print(f"Remote[{self.device_type.upper()}]: Successfully clicked element: '{element_identifier}'")
                        self.last_error = None
                        return True
                    else:
                        error_msg = f"Element found but click failed for '{term}'"
                        print(f"Remote[{self.device_type.upper()}]: {error_msg}")
                        last_error = error_msg
                        # Continue to next term
                else:
                    error_msg = f"Element '{term}' not found: {error}"
                    print(f"Remote[{self.device_type.upper()}]: {error_msg}")
                    last_error = error_msg
                    if len(terms) > 1:
                        print(f"Remote[{self.device_type.upper()}]: Term '{term}' not found, trying next...")
            
            # All terms failed
            print(f"Remote[{self.device_type.upper()}]: All terms failed. Last error: {last_error}")
            self.last_error = last_error
            return False
                
        except Exception as e:
            error_msg = f"Element click error: {str(e)}"
            print(f"Remote[{self.device_type.upper()}]: {error_msg}")
            self.last_error = error_msg
            return False
            
    def find_element_by_text(self, text: str) -> Optional[AndroidElement]:
        """
        Find a UI element by its text content.
        
        Args:
            text: Text to search for
            
        Returns:
            AndroidElement if found, None otherwise
        """
        for element in self.last_ui_elements:
            if text.lower() in element.text.lower():
                return element
        return None
        
    def find_element_by_resource_id(self, resource_id: str) -> Optional[AndroidElement]:
        """
        Find a UI element by its resource ID.
        
        Args:
            resource_id: Resource ID to search for
            
        Returns:
            AndroidElement if found, None otherwise
        """
        for element in self.last_ui_elements:
            if resource_id in element.resource_id:
                return element
        return None
        
    def find_element_by_content_desc(self, content_desc: str) -> Optional[AndroidElement]:
        """
        Find a UI element by its content description.
        
        Args:
            content_desc: Content description to search for
            
        Returns:
            AndroidElement if found, None otherwise
        """
        for element in self.last_ui_elements:
            if content_desc.lower() in element.content_desc.lower():
                return element
        return None
        
    def verify_element_exists(self, text: str = "", resource_id: str = "", content_desc: str = "") -> bool:
        """
        Verify that an element exists on the current screen.
        
        Args:
            text: Text to search for
            resource_id: Resource ID to search for
            content_desc: Content description to search for
            
        Returns:
            bool: True if element found
        """
        if text:
            return self.find_element_by_text(text) is not None
        elif resource_id:
            return self.find_element_by_resource_id(resource_id) is not None
        elif content_desc:
            return self.find_element_by_content_desc(content_desc) is not None
        else:
            return False
            
    def get_device_resolution(self) -> Optional[Dict[str, int]]:
        """Get the device screen resolution."""
        if self.device_resolution:
            return self.device_resolution
        return None
        
    def take_screenshot(self) -> Tuple[bool, str, str]:
        """
        Take a screenshot of the Android device.
        
        Returns:
            tuple: (success, base64_screenshot_data, error_message)
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Taking screenshot")
            
            # Use ADB to take screenshot and get base64 data
            success, screenshot_data, error = self.adb_utils.take_screenshot(self.android_device_id)
            
            if success:
                print(f"Remote[{self.device_type.upper()}]: Screenshot captured successfully")
                return True, screenshot_data, ""
            else:
                print(f"Remote[{self.device_type.upper()}]: Screenshot failed: {error}")
                return False, "", error
                
        except Exception as e:
            error_msg = f"Screenshot error: {e}"
            print(f"Remote[{self.device_type.upper()}]: {error_msg}")
            return False, "", error_msg
        
    def get_status(self) -> Dict[str, Any]:
        """Get controller status by checking ADB device connectivity."""
        if not self.device_ip:
            return {'success': False, 'error': 'No device IP provided'}
            
        try:
            # Run adb devices to check connectivity
            import subprocess
            adb_result = subprocess.run(
                ['adb', 'devices'], 
                capture_output=True, 
                text=True
            )
            
            if adb_result.returncode != 0:
                return {'success': False, 'error': 'ADB command failed'}
            
            # Parse adb devices output to find our device
            device_lines = [line.strip() for line in adb_result.stdout.split('\n') 
                          if line.strip() and not line.startswith('List of devices')]
            
            for line in device_lines:
                if self.android_device_id in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        device_status = parts[1].strip()
                        if device_status == 'device':
                            return {'success': True}
                        else:
                            return {'success': False, 'error': f'Device status is {device_status}, expected "device"'}
            
            # Device not found in ADB devices list
            return {'success': False, 'error': f'Device {self.android_device_id} not found in ADB devices'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to check ADB status: {str(e)}'}

    def tap_coordinates(self, x: int, y: int) -> bool:
        """
        Tap at specific coordinates on the screen.
        
        Args:
            x: X coordinate
            y: Y coordinate  
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Tapping at coordinates ({x}, {y})")
            
            success = self.adb_utils.tap_coordinates(self.android_device_id, x, y)
            
            if success:
                print(f"Remote[{self.device_type.upper()}]: Successfully tapped at ({x}, {y})")
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to tap at ({x}, {y})")
                
            return success
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Coordinate tap error: {e}")
            return False

    def swipe(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: int = 300) -> bool:
        """
        Swipe from one coordinate to another.
        
        Args:
            from_x: Starting X coordinate
            from_y: Starting Y coordinate
            to_x: Ending X coordinate
            to_y: Ending Y coordinate
            duration: Swipe duration in milliseconds (default: 300)
        """
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Swiping from ({from_x}, {from_y}) to ({to_x}, {to_y}) in {duration}ms")
            
            success = self.adb_utils.swipe(self.android_device_id, from_x, from_y, to_x, to_y, duration)
            
            if success:
                print(f"Remote[{self.device_type.upper()}]: Successfully swiped from ({from_x}, {from_y}) to ({to_x}, {to_y})")
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to swipe")
                
            return success
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Swipe error: {e}")
            return False

    def swipe_up(self, from_x: int = 500, from_y: int = 800, to_x: int = 500, to_y: int = 500, duration: int = 300) -> bool:
        """
        Swipe up on the screen.
        
        Args:
            from_x: Starting X coordinate (default: 500)
            from_y: Starting Y coordinate (default: 1500)
            to_x: Ending X coordinate (default: 500)
            to_y: Ending Y coordinate (default: 500)
            duration: Swipe duration in milliseconds (default: 300)
        """
        return self.swipe(from_x, from_y, to_x, to_y, duration)

    def swipe_down(self, from_x: int = 500, from_y: int = 500, to_x: int = 500, to_y: int = 1500, duration: int = 300) -> bool:
        """
        Swipe down on the screen.
        
        Args:
            from_x: Starting X coordinate (default: 500)
            from_y: Starting Y coordinate (default: 500)
            to_x: Ending X coordinate (default: 500)
            to_y: Ending Y coordinate (default: 1500)
            duration: Swipe duration in milliseconds (default: 300)
        """
        return self.swipe(from_x, from_y, to_x, to_y, duration)

    def swipe_left(self, from_x: int = 800, from_y: int = 1000, to_x: int = 200, to_y: int = 1000, duration: int = 300) -> bool:
        """
        Swipe left on the screen.
        
        Args:
            from_x: Starting X coordinate (default: 800)
            from_y: Starting Y coordinate (default: 1000)
            to_x: Ending X coordinate (default: 200)
            to_y: Ending Y coordinate (default: 1000)
            duration: Swipe duration in milliseconds (default: 300)
        """
        return self.swipe(from_x, from_y, to_x, to_y, duration)

    def swipe_right(self, from_x: int = 200, from_y: int = 1000, to_x: int = 800, to_y: int = 1000, duration: int = 300) -> bool:
        """
        Swipe right on the screen.
        
        Args:
            from_x: Starting X coordinate (default: 200)
            from_y: Starting Y coordinate (default: 1000)
            to_x: Ending X coordinate (default: 800)
            to_y: Ending Y coordinate (default: 1000)
            duration: Swipe duration in milliseconds (default: 300)
        """
        return self.swipe(from_x, from_y, to_x, to_y, duration)
    
    def getMenuInfo(self, area: dict = None, context = None) -> Dict[str, Any]:
        """
        Extract menu info from UI dump (ADB-based alternative to OCR getMenuInfo)
        Same interface as text.getMenuInfo but uses UI dump instead of OCR
        
        Args:
            area: Optional area to filter elements (x, y, width, height)
            context: Execution context for metadata storage
            
        Returns:
            Same format as text.getMenuInfo:
            {
                success: bool,
                output_data: {
                    parsed_data: dict,
                    raw_output: str
                },
                message: str
            }
        """
        print(f"[@controller:RemoteMobile:getMenuInfo] Params: area={area}, context={context is not None}")
        
        try:
            # 1. Dump UI elements (already exists)
            print(f"[@controller:RemoteMobile:getMenuInfo] Dumping UI elements...")
            success, elements, error = self.dump_ui_elements()
            
            if not success:
                print(f"[@controller:RemoteMobile:getMenuInfo] FAIL: UI dump failed: {error}")
                return {
                    'success': False,
                    'output_data': {},
                    'message': f'Failed to dump UI: {error}'
                }
            
            print(f"[@controller:RemoteMobile:getMenuInfo] Dumped {len(elements)} UI elements")
            
            # 2. Filter by area if specified
            filtered_elements = elements
            if area:
                filtered_elements = []
                import re
                for elem in elements:
                    # Parse bounds to get x, y, width, height
                    if hasattr(elem, 'bounds') and isinstance(elem.bounds, str) and elem.bounds:
                        bounds_match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', elem.bounds)
                        if bounds_match:
                            x1, y1, x2, y2 = map(int, bounds_match.groups())
                            elem_x, elem_y = x1, y1
                            elem_width, elem_height = x2 - x1, y2 - y1
                            
                            # Check if element overlaps with area
                            area_x = area.get('x', 0)
                            area_y = area.get('y', 0)
                            area_width = area.get('width', 99999)
                            area_height = area.get('height', 99999)
                            
                            # Element is in area if it overlaps
                            if (elem_x < area_x + area_width and
                                elem_x + elem_width > area_x and
                                elem_y < area_y + area_height and
                                elem_y + elem_height > area_y):
                                filtered_elements.append(elem)
                
                print(f"[@controller:RemoteMobile:getMenuInfo] Filtered to {len(filtered_elements)} elements in area")
            
            # 3. Parse key-value pairs from element text
            parsed_data = {}
            for elem in filtered_elements:
                text = elem.text.strip() if hasattr(elem, 'text') and elem.text else ''
                
                # Skip empty or placeholder text
                if not text or text == '<no text>':
                    continue
                
                # Parse key-value pairs (format: "Key\nValue")
                if '\n' in text:
                    lines = text.split('\n')
                    if len(lines) >= 2:
                        key = lines[0].strip().replace(' ', '_').replace('-', '_')
                        value = '\n'.join(lines[1:]).strip()  # Handle multi-line values
                        parsed_data[key] = value
                        print(f"  • {key} = {value}")
            
            print(f"[@controller:RemoteMobile:getMenuInfo] Parsed {len(parsed_data)} key-value pairs")
            
            if not parsed_data:
                print(f"[@controller:RemoteMobile:getMenuInfo] WARNING: No key-value pairs found in UI dump")
            
            # 4. Auto-store to context.metadata (same as OCR version)
            if context:
                from datetime import datetime
                
                # Initialize metadata if not exists
                if not hasattr(context, 'metadata'):
                    context.metadata = {}
                
                # Append parsed data directly to metadata (flat structure)
                for key, value in parsed_data.items():
                    context.metadata[key] = value
                
                # Add extraction metadata
                context.metadata['extraction_method'] = 'ui_dump'
                context.metadata['extraction_timestamp'] = datetime.now().isoformat()
                context.metadata['element_count'] = len(filtered_elements)
                
                # Add device info if available
                if hasattr(self, 'device_name'):
                    context.metadata['device_name'] = self.device_name
                
                if area:
                    context.metadata['extraction_area'] = str(area)
                
                print(f"[@controller:RemoteMobile:getMenuInfo] ✅ AUTO-APPENDED to context.metadata (FLAT)")
                print(f"[@controller:RemoteMobile:getMenuInfo] Metadata keys: {list(context.metadata.keys())}")
                print(f"[@controller:RemoteMobile:getMenuInfo] New fields added: {list(parsed_data.keys())}")
            else:
                print(f"[@controller:RemoteMobile:getMenuInfo] WARNING: No context provided, metadata not stored")
            
            # 5. Prepare output data
            output_data = {
                'parsed_data': parsed_data,
                'raw_output': str([{'text': e.text, 'index': e.id} for e in filtered_elements]),
                'element_count': len(filtered_elements),
                'area': area
            }
            
            # 6. Return same format as text.getMenuInfo
            message = f'Parsed {len(parsed_data)} fields from {len(filtered_elements)} UI elements'
            
            print(f"[@controller:RemoteMobile:getMenuInfo] ✅ SUCCESS: {message}")
            
            return {
                'success': True,
                'output_data': output_data,
                'message': message
            }
            
        except Exception as e:
            error_msg = f"Error extracting menu info from UI dump: {str(e)}"
            print(f"[@controller:RemoteMobile:getMenuInfo] ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'output_data': {},
                'message': error_msg
            }
    
    def get_available_verifications(self) -> list:
        """Get list of available verification commands with typed parameters."""
        from shared.src.lib.schemas.param_types import create_param, create_output, ParamType, OutputType
        
        return [
            {
                "command": "getMenuInfo",
                "label": "Get Menu Info (UI Dump)",
                "description": "Extract key-value pairs from menu/info screen using ADB UI dump and parse automatically",
                "params": {
                    "area": create_param(
                        ParamType.AREA,
                        required=False,
                        default=None,
                        description="Screen area to extract menu information from"
                    )
                },
                "outputs": [
                    create_output(
                        "parsed_data",
                        OutputType.OBJECT,
                        description="Parsed key-value pairs from UI elements"
                    ),
                    create_output(
                        "element_count",
                        OutputType.NUMBER,
                        description="Number of UI elements extracted"
                    )
                ],
                "verification_type": "adb"
            }
        ]
    
    def get_available_actions(self) -> Dict[str, Any]:
        """Get available actions for this Android mobile controller."""
        return {
            'Remote': [
                # Navigation actions
                {
                    'id': 'click_element',
                    'label': 'Click Element by Text',
                    'command': 'click_element',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Click on a UI element directly by text/ID (no UI dump required)',
                    'requiresInput': True,
                    'inputLabel': 'Element Text/ID',
                    'inputPlaceholder': 'Home Tab'
                },
                {
                    'id': 'click_element_by_id',
                    'label': 'Click Element by ID',
                    'command': 'click_element_by_id',
                    'action_type': 'remote',
                    'params': {
                        'element_id': ''
                    },
                    'description': 'Click on UI element by exact ID (works with non-visible elements, always dumps UI first)',
                    'requiresInput': True,
                    'inputLabel': 'Element ID',
                    'inputPlaceholder': '8',
                    'inputParam': 'element_id'
                },
                {
                    'id': 'tap_coordinates',
                    'label': 'Tap Coordinates',
                    'command': 'tap_coordinates',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Tap at specific screen coordinates',
                    'requiresInput': True,
                    'inputLabel': 'Coordinates (x,y)',
                    'inputPlaceholder': '100,200'
                },
                # Swipe actions
                {
                    'id': 'swipe',
                    'label': 'Swipe (Custom)',
                    'command': 'swipe',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Swipe from one coordinate to another',
                    'requiresInput': True,
                    'inputLabel': 'From/To coordinates',
                    'inputPlaceholder': 'from_x,from_y,to_x,to_y'
                },
                {
                    'id': 'swipe_up',
                    'label': 'Swipe Up',
                    'command': 'swipe_up',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Swipe up on screen (customizable distance)',
                    'requiresInput': False
                },
                {
                    'id': 'swipe_down',
                    'label': 'Swipe Down',
                    'command': 'swipe_down',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Swipe down on screen (customizable distance)',
                    'requiresInput': False
                },
                {
                    'id': 'swipe_left',
                    'label': 'Swipe Left',
                    'command': 'swipe_left',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Swipe left on screen (customizable distance)',
                    'requiresInput': False
                },
                {
                    'id': 'swipe_right',
                    'label': 'Swipe Right',
                    'command': 'swipe_right',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Swipe right on screen (customizable distance)',
                    'requiresInput': False
                },
               
                {
                    'id': 'press_key_back',
                    'label': 'Back',
                    'command': 'press_key',
                    'action_type': 'remote',
                    'params': {'key': 'BACK'},
                    'description': 'Go back to previous screen',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_home',
                    'label': 'Home',
                    'command': 'press_key',
                    'action_type': 'remote',
                    'params': {'key': 'HOME'},
                    'description': 'Go to home screen',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_volume_up',
                    'label': 'Volume Up',
                    'command': 'press_key',
                    'action_type': 'remote',
                    'params': {'key': 'VOLUME_UP'},
                    'description': 'Increase volume',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_volume_down',
                    'label': 'Volume Down',
                    'command': 'press_key',
                    'action_type': 'remote',
                    'params': {'key': 'VOLUME_DOWN'},
                    'description': 'Decrease volume',
                    'requiresInput': False
                },
                # Text input actions
                {
                    'id': 'input_text',
                    'label': 'Input Text',
                    'command': 'input_text',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Type text into current field',
                    'requiresInput': True,
                    'inputLabel': 'Text to input',
                    'inputPlaceholder': 'Enter text...'
                },
                # App management actions
                {
                    'id': 'launch_app',
                    'label': 'Launch App',
                    'command': 'launch_app',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Launch an application',
                    'requiresInput': True,
                    'inputLabel': 'Package name',
                    'inputPlaceholder': 'com.example.app'
                },
                {
                    'id': 'close_app',
                    'label': 'Close App',
                    'command': 'close_app',
                    'action_type': 'remote',
                    'params': {},
                    'description': 'Close an application',
                    'requiresInput': True,
                    'inputLabel': 'Package name', 
                    'inputPlaceholder': 'com.example.app'
                }  
            ]
        }

    def execute_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """
        Execute Android Mobile specific command with proper abstraction and auto-reconnection.
        
        Args:
            command: Command to execute ('press_key', 'input_text', etc.)
            params: Command parameters (including wait_time)
            
        Returns:
            bool: True if command executed successfully
        """
        if params is None:
            params = {}
        
        # Extract wait_time from params
        wait_time = int(params.get('wait_time', 0))
        
        print(f"Remote[{self.device_type.upper()}]: Executing command '{command}' with params: {params}")
        
        def _execute_specific_command():
            """Execute the specific command - centralized logic"""
            if command == 'press_key':
                key = params.get('key')
                return self.press_key(key) if key else False
            
            elif command == 'input_text':
                text = params.get('text')
                return self.input_text(text) if text else False
            
            elif command == 'launch_app':
                package = params.get('package')
                return self.launch_app(package) if package else False
            
            elif command == 'close_app':
                package = params.get('package')
                return self.close_app(package) if package else False
            
            elif command == 'click_element':
                element_id = params.get('element_id')
                return self.click_element(element_id) if element_id else False
            
            elif command == 'tap_coordinates':
                x, y = params.get('x'), params.get('y')
                return self.tap_coordinates(int(x), int(y)) if x is not None and y is not None else False
            
            elif command == 'swipe':
                from_x = params.get('from_x')
                from_y = params.get('from_y')
                to_x = params.get('to_x')
                to_y = params.get('to_y')
                duration = params.get('duration', 300)
                if all(v is not None for v in [from_x, from_y, to_x, to_y]):
                    return self.swipe(int(from_x), int(from_y), int(to_x), int(to_y), int(duration))
                else:
                    return False
            
            elif command == 'swipe_up':
                # For swipe_up, ensure vertical movement by keeping X coordinate the same
                from_x = params.get('from_x', 500)
                from_y = params.get('from_y', 1500)
                to_x = from_x  # Keep X coordinate the same for vertical swipe
                to_y = params.get('to_y', 500)
                duration = params.get('duration', 300)
                return self.swipe_up(int(from_x), int(from_y), int(to_x), int(to_y), int(duration))
            
            elif command == 'swipe_down':
                # For swipe_down, ensure vertical movement by keeping X coordinate the same
                from_x = params.get('from_x', 500)
                from_y = params.get('from_y', 500)
                to_x = from_x  # Keep X coordinate the same for vertical swipe
                to_y = params.get('to_y', 1500)
                duration = params.get('duration', 300)
                return self.swipe_down(int(from_x), int(from_y), int(to_x), int(to_y), int(duration))
            
            elif command == 'swipe_left':
                # For swipe_left, ensure horizontal movement by keeping Y coordinate the same
                from_x = params.get('from_x', 800)
                from_y = params.get('from_y', 1000)
                to_x = params.get('to_x', 200)
                to_y = from_y  # Keep Y coordinate the same for horizontal swipe
                duration = params.get('duration', 300)
                return self.swipe_left(int(from_x), int(from_y), int(to_x), int(to_y), int(duration))
            
            elif command == 'swipe_right':
                # For swipe_right, ensure horizontal movement by keeping Y coordinate the same
                from_x = params.get('from_x', 200)
                from_y = params.get('from_y', 1000)
                to_x = params.get('to_x', 800)
                to_y = from_y  # Keep Y coordinate the same for horizontal swipe
                duration = params.get('duration', 300)
                return self.swipe_right(int(from_x), int(from_y), int(to_x), int(to_y), int(duration))
            
            # Handle uppercase swipe commands from frontend
            elif command == 'SWIPE_UP':
                return self.swipe_up()
            
            elif command == 'SWIPE_DOWN':
                return self.swipe_down()
            
            elif command == 'SWIPE_LEFT':
                return self.swipe_left()
            
            elif command == 'SWIPE_RIGHT':
                return self.swipe_right()
            
            elif command == 'click_element_by_id':
                # Android Mobile specific - always dumps UI for edge actions to ensure current state
                element_id = params.get('element_id')
                if element_id:
                    # Always perform fresh UI dump for edge actions since UI state may have changed
                    print(f"Remote[{self.device_type.upper()}]: Performing UI dump for edge action")
                    dump_success, elements, dump_error = self.dump_ui_elements()
                    
                    if dump_success and elements:
                        element = next((el for el in elements if str(el.id) == str(element_id)), None)
                        result = self.click_element_by_id(element) if element else False
                        if not result:
                            print(f"Remote[{self.device_type.upper()}]: Element with ID {element_id} not found in current UI dump")
                        return result
                    else:
                        print(f"Remote[{self.device_type.upper()}]: Failed to dump UI elements: {dump_error}")
                        return False
                else:
                    return False
            
            elif command == 'dump_ui_elements':
                # Android Mobile specific
                success, _, _ = self.dump_ui_elements()
                return success
            
            elif command == 'get_installed_apps':
                # Android Mobile specific
                apps = self.get_installed_apps()
                return len(apps) > 0
            
            elif command == 'getMenuInfo':
                # Verification command - return dict instead of bool
                # This is called via execute_verification, not execute_command
                return {'success': False, 'message': 'getMenuInfo should be called via verification route, not action route'}
            
            else:
                print(f"Remote[{self.device_type.upper()}]: Unknown command: {command}")
                return False
        
        # First attempt
        try:
            result = _execute_specific_command()
            
            # If command failed, try reconnecting and retry once
            if not result:
                print(f"Remote[{self.device_type.upper()}]: Command '{command}' failed - attempting reconnection...")
                if self.connect():
                    print(f"Remote[{self.device_type.upper()}]: Reconnected - retrying command '{command}'")
                    result = _execute_specific_command()
                    if result:
                        print(f"Remote[{self.device_type.upper()}]: Command '{command}' succeeded after reconnection")
                    else:
                        print(f"Remote[{self.device_type.upper()}]: Command '{command}' failed even after reconnection")
                else:
                    print(f"Remote[{self.device_type.upper()}]: Failed to reconnect for command '{command}' retry")
                    return False
                    
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Command '{command}' exception: {e}")
            # Try to reconnect on exception and retry once
            print(f"Remote[{self.device_type.upper()}]: Exception in '{command}' - attempting reconnection...")
            if self.connect():
                try:
                    print(f"Remote[{self.device_type.upper()}]: Reconnected - retrying command '{command}' after exception")
                    result = _execute_specific_command()
                    if result:
                        print(f"Remote[{self.device_type.upper()}]: Command '{command}' succeeded after exception recovery")
                    else:
                        print(f"Remote[{self.device_type.upper()}]: Command '{command}' failed even after exception recovery")
                except Exception as retry_e:
                    print(f"Remote[{self.device_type.upper()}]: Command '{command}' retry after exception also failed: {retry_e}")
                    return False
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to reconnect after command '{command}' exception")
                return False
        
        # Apply wait_time after successful command execution
        if result and wait_time > 0:
            wait_seconds = wait_time / 1000.0
            print(f"Remote[{self.device_type.upper()}]: Waiting {wait_seconds}s after {command}")
            time.sleep(wait_seconds)
        
        return result
    
    def execute_verification(self, verification_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute verification command (called by verification routes)
        
        Args:
            verification_config: Verification configuration with command and params
            
        Returns:
            Dict with success, message, and output_data
        """
        try:
            command = verification_config.get('command')
            params = verification_config.get('params', {})
            context = verification_config.get('context')
            
            print(f"[@controller:RemoteMobile:execute_verification] Executing {command}")
            
            if command == 'getMenuInfo':
                area = params.get('area')
                result = self.getMenuInfo(area=area, context=context)
                return result
            else:
                return {
                    'success': False,
                    'message': f'Unknown verification command: {command}'
                }
                
        except Exception as e:
            print(f"[@controller:RemoteMobile:execute_verification] Error: {e}")
            return {
                'success': False,
                'message': f'Verification execution error: {str(e)}'
            }