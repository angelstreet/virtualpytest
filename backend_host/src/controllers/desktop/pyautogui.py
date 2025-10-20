"""
PyAutoGUI Desktop Controller Implementation

This controller provides PyAutoGUI cross-platform GUI automation functionality.
Works on Windows, Linux, and ARM (Raspberry Pi) - assumes PyAutoGUI is installed on the system.
"""

from typing import Dict, Any, List, Optional
import time
from ..base_controller import DesktopControllerInterface

# Import basic modules at module level
import os
import sys

# Global flag to track availability - will be set during first controller instantiation
PYAUTOGUI_AVAILABLE = None
pyautogui = None


class PyAutoGUIDesktopController(DesktopControllerInterface):
    """PyAutoGUI desktop controller for cross-platform GUI automation."""
    
    def __init__(self, **kwargs):
        """Initialize the PyAutoGUI desktop controller."""
        super().__init__("PyAutoGUI Desktop", "pyautogui")
        
        # Initialize PyAutoGUI on first controller instantiation
        self._initialize_pyautogui()
        
        # Command execution state
        self.last_command_output = ""
        self.last_command_error = ""
        self.last_exit_code = 0
        
        if not PYAUTOGUI_AVAILABLE:
            print(f"[@controller:PyAutoGUIDesktop] WARNING: PyAutoGUI module not available. Please install pyautogui")
        else:
            print(f"[@controller:PyAutoGUIDesktop] Initialized for cross-platform GUI automation")
    
    def _initialize_pyautogui(self):
        """Initialize PyAutoGUI module - only called once per controller instantiation."""
        global PYAUTOGUI_AVAILABLE, pyautogui
        
        # Skip if already initialized
        if PYAUTOGUI_AVAILABLE is not None:
            return
        
        try:
            # Set DISPLAY for VNC environment if not already set
            if sys.platform.startswith('linux') and 'DISPLAY' not in os.environ:
                print(f"[@controller:PyAutoGUIDesktop] Setting DISPLAY to :1 for VNC environment")
                os.environ['DISPLAY'] = ':1'
            
            import pyautogui as _pyautogui
            # Configure PyAutoGUI safety features
            _pyautogui.FAILSAFE = True  # Move mouse to corner to abort
            _pyautogui.PAUSE = 0.1      # Short pause between actions
            
            # Set global variables
            pyautogui = _pyautogui
            PYAUTOGUI_AVAILABLE = True
            print(f"[@controller:PyAutoGUIDesktop] PyAutoGUI initialized successfully with DISPLAY={os.environ.get('DISPLAY')}")
        except ImportError:
            PYAUTOGUI_AVAILABLE = False
            print(f"[@controller:PyAutoGUIDesktop] WARNING: PyAutoGUI module not available. Please install pyautogui")
        except Exception as e:
            print(f"[@controller:PyAutoGUIDesktop] WARNING: PyAutoGUI initialization failed: {e}")
            PYAUTOGUI_AVAILABLE = False
    
    def connect(self) -> bool:
        """Connect to PyAutoGUI service (always true for local execution)."""
        if not PYAUTOGUI_AVAILABLE:
            print(f"Desktop[{self.desktop_type.upper()}]: ERROR - PyAutoGUI not available")
            return False
        
        print(f"Desktop[{self.desktop_type.upper()}]: Cross-platform GUI automation ready")
        return True
            
    def disconnect(self) -> bool:
        """Disconnect from PyAutoGUI service (always true for local execution)."""
        print(f"Desktop[{self.desktop_type.upper()}]: Cross-platform GUI automation disconnected")
        return True
            
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute PyAutoGUI command for GUI automation.
        
        Args:
            command: Command type (click, rightclick, doubleclick, keypress, type, screenshot, locate)
            params: Command parameters containing PyAutoGUI-specific arguments
            
        Returns:
            Dict: Command execution result
        """
        if params is None:
            params = {}
        
        if not PYAUTOGUI_AVAILABLE:
            return {
                'success': False,
                'output': '',
                'error': 'PyAutoGUI module not available',
                'exit_code': -1,
                'execution_time': 0
            }
        
        print(f"Desktop[{self.desktop_type.upper()}]: Executing command '{command}' with params: {params}")
        
        start_time = time.time()
        
        try:
            if command == 'execute_ldtp_click' or command == 'execute_pyautogui_click':
                x = params.get('x')
                y = params.get('y')
                
                if x is None or y is None:
                    return self._error_result('Missing x or y coordinates for click', start_time)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Clicking at coordinates ({x}, {y})")
                pyautogui.click(x, y)
                return self._success_result(f"Click executed at ({x}, {y})", start_time)
                
            elif command == 'execute_ldtp_rightclick' or command == 'execute_pyautogui_rightclick':
                x = params.get('x')
                y = params.get('y')
                
                if x is None or y is None:
                    return self._error_result('Missing x or y coordinates for rightclick', start_time)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Right-clicking at coordinates ({x}, {y})")
                pyautogui.rightClick(x, y)
                return self._success_result(f"Right-click executed at ({x}, {y})", start_time)
                
            elif command == 'execute_ldtp_doubleclick' or command == 'execute_pyautogui_doubleclick':
                x = params.get('x')
                y = params.get('y')
                
                if x is None or y is None:
                    return self._error_result('Missing x or y coordinates for doubleclick', start_time)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Double-clicking at coordinates ({x}, {y})")
                pyautogui.doubleClick(x, y)
                return self._success_result(f"Double-click executed at ({x}, {y})", start_time)
                
            elif command == 'execute_ldtp_keypress' or command == 'execute_pyautogui_keypress':
                key = params.get('key')
                keys = params.get('keys')  # For key combinations
                
                if key:
                    print(f"Desktop[{self.desktop_type.upper()}]: Pressing key: {key}")
                    try:
                        pyautogui.press(key)
                        return self._success_result(f"Key pressed: {key}", start_time)
                    except Exception as e:
                        error_msg = f"Failed to press key '{key}': {str(e)}"
                        print(f"Desktop[{self.desktop_type.upper()}]: ERROR - {error_msg}")
                        return self._error_result(error_msg, start_time)
                elif keys:
                    print(f"Desktop[{self.desktop_type.upper()}]: Pressing key combination: {keys}")
                    try:
                        pyautogui.hotkey(*keys)
                        return self._success_result(f"Key combination pressed: {keys}", start_time)
                    except Exception as e:
                        error_msg = f"Failed to press key combination '{keys}': {str(e)}"
                        print(f"Desktop[{self.desktop_type.upper()}]: ERROR - {error_msg}")
                        return self._error_result(error_msg, start_time)
                else:
                    return self._error_result('Missing key or keys for keypress', start_time)
                
            elif command == 'execute_ldtp_enterstring' or command == 'execute_pyautogui_type':
                text = params.get('text')
                interval = params.get('interval', 0.0)  # Delay between keystrokes
                
                if text is None:
                    return self._error_result('Missing text for type', start_time)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Typing text: '{text}'")
                pyautogui.typewrite(text, interval=interval)
                return self._success_result(f"Text typed: {text}", start_time)
                
            elif command == 'execute_pyautogui_screenshot':
                filename = params.get('filename')
                region = params.get('region')  # (left, top, width, height)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Taking screenshot")
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    screenshot = pyautogui.screenshot()
                
                if filename:
                    screenshot.save(filename)
                    return self._success_result(f"Screenshot saved to: {filename}", start_time)
                else:
                    return self._success_result(f"Screenshot taken (not saved)", start_time)
                
            elif command == 'execute_pyautogui_locate':
                image_path = params.get('image_path')
                confidence = params.get('confidence', 0.9)
                region = params.get('region')  # (left, top, width, height)
                
                if not image_path:
                    return self._error_result('Missing image_path for locate', start_time)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Locating image: {image_path}")
                try:
                    if region:
                        location = pyautogui.locateOnScreen(image_path, confidence=confidence, region=region)
                    else:
                        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                    
                    if location:
                        return self._success_result(f"Image found at: {location}", start_time)
                    else:
                        return self._error_result(f"Image not found: {image_path}", start_time)
                except pyautogui.ImageNotFoundException:
                    return self._error_result(f"Image not found: {image_path}", start_time)
                
            elif command == 'execute_pyautogui_locate_and_click':
                image_path = params.get('image_path')
                confidence = params.get('confidence', 0.9)
                region = params.get('region')  # (left, top, width, height)
                
                if not image_path:
                    return self._error_result('Missing image_path for locate_and_click', start_time)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Locating and clicking image: {image_path}")
                try:
                    if region:
                        location = pyautogui.locateOnScreen(image_path, confidence=confidence, region=region)
                    else:
                        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                    
                    if location:
                        center = pyautogui.center(location)
                        pyautogui.click(center)
                        return self._success_result(f"Image found and clicked at: {center}", start_time)
                    else:
                        return self._error_result(f"Image not found: {image_path}", start_time)
                except pyautogui.ImageNotFoundException:
                    return self._error_result(f"Image not found: {image_path}", start_time)
                
            elif command == 'execute_pyautogui_move':
                x = params.get('x')
                y = params.get('y')
                duration = params.get('duration', 0.0)
                
                if x is None or y is None:
                    return self._error_result('Missing x or y coordinates for move', start_time)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Moving mouse to ({x}, {y})")
                pyautogui.moveTo(x, y, duration=duration)
                return self._success_result(f"Mouse moved to ({x}, {y})", start_time)
                
            elif command == 'execute_pyautogui_scroll':
                clicks = params.get('clicks', 1)
                x = params.get('x')
                y = params.get('y')
                
                if x is not None and y is not None:
                    print(f"Desktop[{self.desktop_type.upper()}]: Scrolling {clicks} clicks at ({x}, {y})")
                    pyautogui.scroll(clicks, x=x, y=y)
                else:
                    print(f"Desktop[{self.desktop_type.upper()}]: Scrolling {clicks} clicks at current position")
                    pyautogui.scroll(clicks)
                return self._success_result(f"Scrolled {clicks} clicks", start_time)
                
            elif command == 'execute_pyautogui_launch':
                app_name = params.get('app_name')
                
                if not app_name:
                    return self._error_result('Missing app_name for launch', start_time)
                
                print(f"Desktop[{self.desktop_type.upper()}]: Launching application: {app_name}")
                
                # Use subprocess to launch applications on Windows
                import subprocess
                import sys
                
                try:
                    if sys.platform.startswith('win'):
                        # Windows - try common methods
                        if app_name.lower() in ['notepad', 'calc', 'mspaint']:
                            subprocess.Popen([app_name])
                        else:
                            # Try to run as command
                            subprocess.Popen([app_name], shell=True)
                    else:
                        # Linux/Mac - use which to find the application
                        subprocess.Popen([app_name])
                    
                    return self._success_result(f"Application launched: {app_name}", start_time)
                except Exception as e:
                    return self._error_result(f"Failed to launch {app_name}: {e}", start_time)
                
            else:
                print(f"Desktop[{self.desktop_type.upper()}]: Unknown command: {command}")
                return {
                    'success': False,
                    'output': '',
                    'error': f'Unknown PyAutoGUI command: {command}',
                    'exit_code': -1,
                    'execution_time': int((time.time() - start_time) * 1000)
                }
                
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f"PyAutoGUI command execution error: {e}"
            print(f"Desktop[{self.desktop_type.upper()}]: {error_msg}")
            
            return {
                'success': False,
                'output': '',
                'error': error_msg,
                'exit_code': -1,
                'execution_time': execution_time
            }
    
    def _success_result(self, output: str, start_time: float) -> Dict[str, Any]:
        """Helper to create success result."""
        execution_time = int((time.time() - start_time) * 1000)
        
        # Store last command results
        self.last_command_output = output
        self.last_command_error = ""
        self.last_exit_code = 0
        
        print(f"Desktop[{self.desktop_type.upper()}]: {output} - SUCCESS")
        
        return {
            'success': True,
            'output': output,
            'error': '',
            'exit_code': 0,
            'execution_time': execution_time
        }
    
    def _error_result(self, error: str, start_time: float) -> Dict[str, Any]:
        """Helper to create error result."""
        execution_time = int((time.time() - start_time) * 1000)
        
        # Store last command results
        self.last_command_output = ""
        self.last_command_error = error
        self.last_exit_code = -1
        
        print(f"Desktop[{self.desktop_type.upper()}]: {error} - FAILED")
        
        return {
            'success': False,
            'output': '',
            'error': error,
            'exit_code': -1,
            'execution_time': execution_time
        }
    
    def get_available_actions(self) -> Dict[str, Any]:
        """Get available actions for PyAutoGUI desktop controller."""
        return {
            'Desktop': [
                # Click actions
                {
                    'id': 'pyautogui_click',
                    'label': 'Click Coordinates',
                    'command': 'execute_pyautogui_click',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Click at specific screen coordinates',
                    'requiresInput': True,
                    'inputLabel': 'Coordinates (x,y)',
                    'inputPlaceholder': '100,200'
                },
                {
                    'id': 'pyautogui_rightclick',
                    'label': 'Right Click Coordinates',
                    'command': 'execute_pyautogui_rightclick',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Right-click at specific screen coordinates',
                    'requiresInput': True,
                    'inputLabel': 'Coordinates (x,y)',
                    'inputPlaceholder': '100,200'
                },
                {
                    'id': 'pyautogui_doubleclick',
                    'label': 'Double Click Coordinates',
                    'command': 'execute_pyautogui_doubleclick',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Double-click at specific screen coordinates',
                    'requiresInput': True,
                    'inputLabel': 'Coordinates (x,y)',
                    'inputPlaceholder': '100,200'
                },
                # Keyboard actions
                {
                    'id': 'pyautogui_keypress',
                    'label': 'Press Key',
                    'command': 'execute_pyautogui_keypress',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Press a single key',
                    'requiresInput': True,
                    'inputLabel': 'Key name',
                    'inputPlaceholder': 'enter, space, tab, ctrl, alt'
                },
                {
                    'id': 'pyautogui_type',
                    'label': 'Type Text',
                    'command': 'execute_pyautogui_type',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Type text at current cursor position',
                    'requiresInput': True,
                    'inputLabel': 'Text to type',
                    'inputPlaceholder': 'Hello World'
                },
                # Mouse actions
                {
                    'id': 'pyautogui_move',
                    'label': 'Move Mouse',
                    'command': 'execute_pyautogui_move',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Move mouse to specific coordinates',
                    'requiresInput': True,
                    'inputLabel': 'Coordinates (x,y)',
                    'inputPlaceholder': '100,200'
                },
                {
                    'id': 'pyautogui_scroll',
                    'label': 'Scroll',
                    'command': 'execute_pyautogui_scroll',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Scroll up (positive) or down (negative)',
                    'requiresInput': True,
                    'inputLabel': 'Scroll clicks (positive=up, negative=down)',
                    'inputPlaceholder': '3'
                },
                # Image-based actions
                {
                    'id': 'pyautogui_locate',
                    'label': 'Locate Image',
                    'command': 'execute_pyautogui_locate',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Find an image on screen',
                    'requiresInput': True,
                    'inputLabel': 'Image file path',
                    'inputPlaceholder': '/path/to/image.png'
                },
                {
                    'id': 'pyautogui_locate_and_click',
                    'label': 'Locate and Click Image',
                    'command': 'execute_pyautogui_locate_and_click',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Find an image on screen and click it',
                    'requiresInput': True,
                    'inputLabel': 'Image file path',
                    'inputPlaceholder': '/path/to/image.png'
                },
                # App launch action
                {
                    'id': 'pyautogui_launch',
                    'label': 'Launch Application',
                    'command': 'execute_pyautogui_launch',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Launch an application',
                    'requiresInput': True,
                    'inputLabel': 'Application name',
                    'inputPlaceholder': 'notepad, calc, firefox'
                },
                # Screenshot action
                {
                    'id': 'pyautogui_screenshot',
                    'label': 'Take Screenshot',
                    'command': 'execute_pyautogui_screenshot',
                    'action_type': 'desktop',
                    'params': {},
                    'description': 'Take a screenshot',
                    'requiresInput': False
                }
            ]
        } 