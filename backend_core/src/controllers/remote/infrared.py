"""
IR Remote Controller Implementation

This controller provides IR (Infrared) remote control functionality for TVs, STBs, and other devices.
Supports classic remote control buttons with standard IR keycodes.
"""

from typing import Dict, Any, List, Optional
import subprocess
import time
import json
import os
from pathlib import Path
from ..base_controller import RemoteControllerInterface


class IRRemoteController(RemoteControllerInterface):
    """IR remote controller using external script with JSON config files."""

    @staticmethod
    def get_remote_config() -> Dict[str, Any]:
        """Get the IR remote configuration including layout, buttons, and image."""
        # Return a generic IR remote configuration since actual keys depend on the config file
        return {
            "id": "ir_remote",
            "name": "IR Remote",
            "type": "ir_remote",
            "image": "infrared_remote.png",
            "buttons": [
                {"id": "POWER", "label": "Power", "x": 50, "y": 30},
                {"id": "VOLUME_UP", "label": "Vol+", "x": 20, "y": 60},
                {"id": "VOLUME_DOWN", "label": "Vol-", "x": 20, "y": 90},
                {"id": "UP", "label": "↑", "x": 50, "y": 120},
                {"id": "DOWN", "label": "↓", "x": 50, "y": 180},
                {"id": "LEFT", "label": "←", "x": 20, "y": 150},
                {"id": "RIGHT", "label": "→", "x": 80, "y": 150},
                {"id": "OK", "label": "OK", "x": 50, "y": 150}
            ]
        }
    
    def __init__(self, ir_path: str = None, ir_type: str = None, **kwargs):
        """
        Initialize the Infrared remote controller.
        
        Args:
            ir_path: Path to IR device (e.g., '/dev/lirc0')
            ir_type: Type of IR config file (e.g., 'samsung')
        """
        super().__init__("IR Remote", "infrared")
        
        # IR device parameters
        self.ir_path = ir_path
        self.ir_type = ir_type
        
        # Validate required parameters
        if not self.ir_path:
            raise ValueError("ir_path is required for IRRemoteController")
        if not self.ir_type:
            raise ValueError("ir_type is required for IRRemoteController")
            
        # IR config paths
        self.ir_config_path = os.path.join(
            os.path.dirname(__file__), 'ir_conf'
        )
        self.ir_config_file = f"{self.ir_type}.json"
        
        # IR connection state
        self.ir_available_keys = []
        self.ir_config_data = {}
        
        # Timing attributes
        self.repeat_delay = 100  # milliseconds between repeated commands
        self.command_delay = 50  # milliseconds general command delay
        self.last_command_time = 0  # timestamp of last command
        self.connection_timeout = 5000  # milliseconds
        
        print(f"[@controller:InfraredRemote] Initialized for device: {self.ir_path}")
        print(f"[@controller:InfraredRemote] Using config type: {self.ir_type}")
        
    def connect(self) -> bool:
        """Connect to IR transmitter device."""
        try:
            print(f"Remote[{self.device_type.upper()}]: Initializing IR device {self.ir_path}")
            
            # Load IR configuration first
            success, config_data = self._load_ir_config()
            if not success:
                return False
                
            self.ir_available_keys = list(config_data.keys())
            self.ir_config_data = config_data
            print(f"Remote[{self.device_type.upper()}]: Loaded {len(self.ir_available_keys)} keys from {self.ir_config_file}")
            
            # Check if IR device exists (warn but don't fail for testing)
            if not os.path.exists(self.ir_path):
                print(f"Remote[{self.device_type.upper()}]: WARNING - IR device not found: {self.ir_path}")
                print(f"Remote[{self.device_type.upper()}]: Continuing with config-only mode for testing")
                
            self.is_connected = True
            print(f"Remote[{self.device_type.upper()}]: Connected to {self.device_name}")
            return True
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Connection failed: {e}")
            return False
            
    def disconnect(self) -> bool:
        """Disconnect from IR transmitter."""
        try:
            self.ir_available_keys = []
            self.is_connected = False
            print(f"Remote[{self.device_type.upper()}]: Disconnected from {self.device_name}")
            return True
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Disconnect error: {e}")
            return False
            
    def press_key(self, key: str) -> bool:
        """
        Send IR key press command using external script.
        
        Args:
            key: Key name (e.g., "POWER", "VOLUME_UP", "1", "OK")
        """
        if not self.is_connected:
            print(f"Remote[{self.device_type.upper()}]: ERROR - Not connected to IR device")
            return False
            
        try:
            key_upper = key.upper()
            
            # Check if key is available in config
            if key_upper not in self.ir_available_keys:
                print(f"Remote[{self.device_type.upper()}]: Key '{key_upper}' not found in config {self.ir_config_file}")
                print(f"Remote[{self.device_type.upper()}]: Available keys: {self.ir_available_keys}")
                return False
                
            print(f"Remote[{self.device_type.upper()}]: Sending IR command {key_upper}")
            
            # Apply command delay
            current_time = time.time() * 1000  # Convert to milliseconds
            if current_time - self.last_command_time < self.repeat_delay:
                time.sleep((self.repeat_delay - (current_time - self.last_command_time)) / 1000)
            
            # Send IR command using integrated functionality
            success = self._send_ir_command_integrated(key_upper)
            
            if success:
                self.last_command_time = time.time() * 1000
                print(f"Remote[{self.device_type.upper()}]: Successfully sent {key_upper}")
                return True
            else:
                print(f"Remote[{self.device_type.upper()}]: Failed to send {key_upper}")
                return False
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Key press error: {e}")
            return False
            
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """
        Execute IR remote specific command with proper abstraction.
        
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
        
        result = False
        
        if command == 'press_key':
            key = params.get('key')
            result = self.press_key(key) if key else False
        
        elif command == 'input_text':
            text = params.get('text')
            result = self.input_text(text) if text else False
        
        else:
            print(f"Remote[{self.device_type.upper()}]: Unknown command: {command}")
            result = False
        
        # Apply wait_time after successful command execution
        if result and wait_time > 0:
            delay_seconds = wait_time / 1000.0
            print(f"Remote[{self.device_type.upper()}]: Waiting {delay_seconds}s after command execution")
            time.sleep(delay_seconds)
        
        return result
    
    def input_text(self, text: str) -> bool:
        """
        Send text input by pressing number keys.
        
        Args:
            text: Text to input (numbers only for IR remote)
        """
        if not self.is_connected:
            print(f"Remote[{self.device_type.upper()}]: ERROR - Not connected to IR device")
            return False
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Sending text: '{text}'")
            
            # IR remotes typically only support numeric input
            for char in text:
                if char.isdigit():
                    if not self.press_key(char):
                        print(f"Remote[{self.device_type.upper()}]: Failed to send digit: {char}")
                        return False
                    time.sleep(0.2)  # Small delay between digits
                elif char == ' ':
                    time.sleep(0.5)  # Longer pause for spaces
                else:
                    print(f"Remote[{self.device_type.upper()}]: Skipping non-numeric character: {char}")
            
            print(f"Remote[{self.device_type.upper()}]: Text input completed")
            return True
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Text input error: {e}")
            return False
            
    def power_on(self) -> bool:
        """Turn device on using IR power command."""
        return self.press_key("POWER")
        
    def power_off(self) -> bool:
        """Turn device off using IR power command."""
        return self.press_key("POWER")
        
    def change_channel(self, channel: int) -> bool:
        """
        Change to specific channel number.
        
        Args:
            channel: Channel number to tune to
        """
        if not self.is_connected:
            return False
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Changing to channel {channel}")
            
            # Send each digit of the channel number
            channel_str = str(channel)
            for digit in channel_str:
                if not self.press_key(digit):
                    return False
                time.sleep(0.3)
            
            # Press OK to confirm channel change
            time.sleep(0.5)
            return self.press_key("OK")
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Channel change error: {e}")
            return False
            
    def set_volume(self, level: int) -> bool:
        """
        Set volume to specific level (0-100).
        
        Args:
            level: Volume level (0-100)
        """
        if not self.is_connected:
            return False
            
        try:
            print(f"Remote[{self.device_type.upper()}]: Setting volume to {level}")
            
            # First mute, then unmute to reset volume
            self.press_key("MUTE")
            time.sleep(0.5)
            self.press_key("MUTE")
            time.sleep(0.5)
            
            # Adjust volume (simplified approach)
            if level > 50:
                # Volume up
                presses = (level - 50) // 5
                for _ in range(presses):
                    self.press_key("VOLUME_UP")
                    time.sleep(0.2)
            elif level < 50:
                # Volume down
                presses = (50 - level) // 5
                for _ in range(presses):
                    self.press_key("VOLUME_DOWN")
                    time.sleep(0.2)
            
            print(f"Remote[{self.device_type.upper()}]: Volume set to approximately {level}")
            return True
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Volume set error: {e}")
            return False
            
    def _load_ir_config(self) -> tuple[bool, dict]:
        """
        Load IR configuration from JSON file.
        
        Returns:
            tuple: (success, config_data)
        """
        ir_config_full_path = os.path.join(self.ir_config_path, self.ir_config_file)
        
        if not os.path.exists(ir_config_full_path):
            print(f"Remote[{self.device_type.upper()}]: IR config file not found: {ir_config_full_path}")
            return False, {}
            
        try:
            with open(ir_config_full_path, 'r') as f:
                config_data = json.load(f)
                return True, config_data
        except json.JSONDecodeError as e:
            print(f"Remote[{self.device_type.upper()}]: Invalid JSON in config file {ir_config_full_path}: {e}")
            return False, {}
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Error reading config file {ir_config_full_path}: {e}")
            return False, {}
    
    def _send_ir_command_integrated(self, key: str) -> bool:
        """
        Send IR command using integrated ir-ctl functionality.
        
        Args:
            key: Key name to send
            
        Returns:
            bool: True if command sent successfully
        """
        try:
            # Get raw IR code from config
            raw_code = self.ir_config_data.get(key)
            if not raw_code:
                print(f"Remote[{self.device_type.upper()}]: Key {key} not found in {self.ir_config_file}")
                return False
            
            print(f"Remote[{self.device_type.upper()}]: Sending IR code for {key}")
            print(f"Remote[{self.device_type.upper()}]: Raw IR code: {raw_code[:100]}...")  # Debug: show first 100 chars
            
            # Send IR code using ir-ctl with sudo
            # The raw_code needs to end with a newline for ir-ctl to process it correctly
            ir_data = raw_code.strip() + '\n'
            
            # Check if IR device exists
            if not os.path.exists(self.ir_path):
                print(f"Remote[{self.device_type.upper()}]: WARNING - IR device not found: {self.ir_path}")
                print(f"Remote[{self.device_type.upper()}]: Attempting to send anyway...")
            
            # Try different approaches for ir-ctl command
            cmd = ["sudo", "ir-ctl"]
            
            # If device path is specified, use it
            if self.ir_path and os.path.exists(self.ir_path):
                cmd.extend(["--device", self.ir_path])
            
            cmd.extend(["--send", "-"])
            
            print(f"Remote[{self.device_type.upper()}]: Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                input=ir_data, 
                check=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            print(f"Remote[{self.device_type.upper()}]: Successfully sent IR code for {key}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Remote[{self.device_type.upper()}]: Failed to send IR code: {e}")
            if e.stderr:
                print(f"Remote[{self.device_type.upper()}]: stderr: {e.stderr}")
            if e.stdout:
                print(f"Remote[{self.device_type.upper()}]: stdout: {e.stdout}")
            print(f"Remote[{self.device_type.upper()}]: Return code: {e.returncode}")
            return False
        except FileNotFoundError:
            print(f"Remote[{self.device_type.upper()}]: ir-ctl command not found. Please install lirc-tools.")
            return False
        except subprocess.TimeoutExpired:
            print(f"Remote[{self.device_type.upper()}]: IR command timed out")
            return False
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Unexpected error sending IR code: {e}")
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """Get controller status information."""
        return {
            'controller_type': self.controller_type,
            'device_type': self.device_type,
            'device_name': self.device_name,
            'ir_path': self.ir_path,
            'ir_type': self.ir_type,
            'ir_config_file': self.ir_config_file,
            'connection_timeout': self.connection_timeout,
            'command_delay': self.command_delay,
            'connected': self.is_connected,
            'last_command_time': self.last_command_time,
            'supported_keys': self.ir_available_keys,
            'capabilities': [
                'navigation', 'numeric_input', 'media_control', 
                'volume_control', 'channel_control', 'power_control',
                'color_buttons', 'function_buttons', 'tv_controls',
                'stb_controls'
            ]
        }
    
    def get_available_actions(self) -> Dict[str, Any]:
        """Get available actions for this IR controller."""
        return {
            'remote': [
                {
                    'id': 'press_key_up',
                    'label': 'Navigate Up',
                    'command': 'press_key',
                    'params': {'key': 'UP'},
                    'description': 'Navigate up in the interface',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_down',
                    'label': 'Navigate Down',
                    'command': 'press_key',
                    'params': {'key': 'DOWN'},
                    'description': 'Navigate down in the interface',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_left',
                    'label': 'Navigate Left',
                    'command': 'press_key',
                    'params': {'key': 'LEFT'},
                    'description': 'Navigate left in the interface',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_right',
                    'label': 'Navigate Right',
                    'command': 'press_key',
                    'params': {'key': 'RIGHT'},
                    'description': 'Navigate right in the interface',
                    'requiresInput': False
                }
            ],
            'control': [
                {
                    'id': 'press_key_ok',
                    'label': 'Select/OK',
                    'command': 'press_key',
                    'params': {'key': 'OK'},
                    'description': 'Select current item',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_back',
                    'label': 'Back',
                    'command': 'press_key',
                    'params': {'key': 'BACK'},
                    'description': 'Go back to previous screen',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_home',
                    'label': 'Home',
                    'command': 'press_key',
                    'params': {'key': 'HOME'},
                    'description': 'Go to home screen',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_menu',
                    'label': 'Menu',
                    'command': 'press_key',
                    'params': {'key': 'MENU'},
                    'description': 'Open menu',
                    'requiresInput': False
                }
            ],
            'power': [
                {
                    'id': 'press_key_power',
                    'label': 'Power',
                    'command': 'press_key',
                    'params': {'key': 'POWER'},
                    'description': 'Power on/off device',
                    'requiresInput': False
                },
                {
                    'id': 'power_on',
                    'label': 'Power On',
                    'command': 'power_on',
                    'params': {},
                    'description': 'Turn device on',
                    'requiresInput': False
                },
                {
                    'id': 'power_off',
                    'label': 'Power Off',
                    'command': 'power_off',
                    'params': {},
                    'description': 'Turn device off',
                    'requiresInput': False
                }
            ],
            'volume_control': [
                {
                    'id': 'press_key_volume_up',
                    'label': 'Volume Up',
                    'command': 'press_key',
                    'params': {'key': 'VOLUME_UP'},
                    'description': 'Increase volume',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_volume_down',
                    'label': 'Volume Down',
                    'command': 'press_key',
                    'params': {'key': 'VOLUME_DOWN'},
                    'description': 'Decrease volume',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_mute',
                    'label': 'Mute',
                    'command': 'press_key',
                    'params': {'key': 'MUTE'},
                    'description': 'Toggle mute',
                    'requiresInput': False
                },
                {
                    'id': 'set_volume',
                    'label': 'Set Volume Level',
                    'command': 'set_volume',
                    'params': {},
                    'description': 'Set volume to specific level (0-100)',
                    'requiresInput': True,
                    'inputLabel': 'Volume level (0-100)',
                    'inputPlaceholder': '50'
                }
            ],
            'media_control': [
                {
                    'id': 'press_key_play_pause',
                    'label': 'Play/Pause',
                    'command': 'press_key',
                    'params': {'key': 'PLAY_PAUSE'},
                    'description': 'Toggle play/pause for media',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_fast_forward',
                    'label': 'Fast Forward',
                    'command': 'press_key',
                    'params': {'key': 'FAST_FORWARD'},
                    'description': 'Fast forward media',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_rewind',
                    'label': 'Rewind',
                    'command': 'press_key',
                    'params': {'key': 'REWIND'},
                    'description': 'Rewind media',
                    'requiresInput': False
                }
            ],
            'channel_control': [
                {
                    'id': 'press_key_channel_up',
                    'label': 'Channel Up',
                    'command': 'press_key',
                    'params': {'key': 'CHANNEL_UP'},
                    'description': 'Go to next channel',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_channel_down',
                    'label': 'Channel Down',
                    'command': 'press_key',
                    'params': {'key': 'CHANNEL_DOWN'},
                    'description': 'Go to previous channel',
                    'requiresInput': False
                },
                {
                    'id': 'change_channel',
                    'label': 'Change Channel',
                    'command': 'change_channel',
                    'params': {},
                    'description': 'Change to specific channel number',
                    'requiresInput': True,
                    'inputLabel': 'Channel number',
                    'inputPlaceholder': '1'
                }
            ],
            'numeric_input': [
                {
                    'id': 'press_key_0',
                    'label': 'Number 0',
                    'command': 'press_key',
                    'params': {'key': '0'},
                    'description': 'Press number 0',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_1',
                    'label': 'Number 1',
                    'command': 'press_key',
                    'params': {'key': '1'},
                    'description': 'Press number 1',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_2',
                    'label': 'Number 2',
                    'command': 'press_key',
                    'params': {'key': '2'},
                    'description': 'Press number 2',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_3',
                    'label': 'Number 3',
                    'command': 'press_key',
                    'params': {'key': '3'},
                    'description': 'Press number 3',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_4',
                    'label': 'Number 4',
                    'command': 'press_key',
                    'params': {'key': '4'},
                    'description': 'Press number 4',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_5',
                    'label': 'Number 5',
                    'command': 'press_key',
                    'params': {'key': '5'},
                    'description': 'Press number 5',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_6',
                    'label': 'Number 6',
                    'command': 'press_key',
                    'params': {'key': '6'},
                    'description': 'Press number 6',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_7',
                    'label': 'Number 7',
                    'command': 'press_key',
                    'params': {'key': '7'},
                    'description': 'Press number 7',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_8',
                    'label': 'Number 8',
                    'command': 'press_key',
                    'params': {'key': '8'},
                    'description': 'Press number 8',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_9',
                    'label': 'Number 9',
                    'command': 'press_key',
                    'params': {'key': '9'},
                    'description': 'Press number 9',
                    'requiresInput': False
                }
            ],
            'color_buttons': [
                {
                    'id': 'press_key_red',
                    'label': 'Red Button',
                    'command': 'press_key',
                    'params': {'key': 'RED'},
                    'description': 'Press red color button',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_green',
                    'label': 'Green Button',
                    'command': 'press_key',
                    'params': {'key': 'GREEN'},
                    'description': 'Press green color button',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_yellow',
                    'label': 'Yellow Button',
                    'command': 'press_key',
                    'params': {'key': 'YELLOW'},
                    'description': 'Press yellow color button',
                    'requiresInput': False
                },
                {
                    'id': 'press_key_blue',
                    'label': 'Blue Button',
                    'command': 'press_key',
                    'params': {'key': 'BLUE'},
                    'description': 'Press blue color button',
                    'requiresInput': False
                }
            ],
            'input': [
                {
                    'id': 'input_text',
                    'label': 'Input Text',
                    'command': 'input_text',
                    'params': {},
                    'description': 'Type text using IR remote',
                    'requiresInput': True,
                    'inputLabel': 'Text to input',
                    'inputPlaceholder': 'Enter text...'
                }
            ],
            'sequences': [
                {
                    'id': 'execute_sequence',
                    'label': 'Execute Sequence',
                    'command': 'execute_sequence',
                    'params': {},
                    'description': 'Execute a sequence of IR commands',
                    'requiresInput': True,
                    'inputLabel': 'Command sequence (JSON)',
                    'inputPlaceholder': '[{"action": "press_key", "params": {"key": "OK"}}]'
                }
            ]
        }
