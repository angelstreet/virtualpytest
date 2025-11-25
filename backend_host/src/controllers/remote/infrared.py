"""
IR Remote Controller Implementation

This controller provides IR (Infrared) remote control functionality for TVs, STBs, and other devices.
Supports classic remote control buttons with standard IR keycodes.
"""

from typing import Dict, Any, List, Optional, Tuple
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
        """Get the IR remote configuration from JSON file."""
        # Load configuration from JSON file
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'config', 'remote', 'infrared_remote.json'
        )
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"IR remote config file not found at: {config_path}")
            
        try:
            print(f"Loading IR remote config from: {config_path}")
            with open(config_path, 'r') as config_file:
                return json.load(config_file)
        except Exception as e:
            raise RuntimeError(f"Error loading IR remote config from file: {e}")
    
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
        self.last_command_time = 0
        
        print(f"[@controller:InfraredRemote] Initialized for device: {self.ir_path}")
        print(f"[@controller:InfraredRemote] Using config type: {self.ir_type}")
        
        # Auto-connect IR controller since it doesn't require network connection
        # IR controllers should be available immediately once config is loaded
        self.connect()
        
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
        """Send IR key press command."""
        if not self.is_connected:
            print(f"Remote[{self.device_type.upper()}]: ERROR - Not connected")
            return False
            
        key_upper = key.upper()
        
        # Check if key is available in config
        if key_upper not in self.ir_available_keys:
            print(f"Remote[{self.device_type.upper()}]: Key '{key_upper}' not found")
            return False
            
        print(f"Remote[{self.device_type.upper()}]: Sending {key_upper}")
        return self._send_ir_command_integrated(key_upper)
            
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """
        Execute IR remote specific command.
        
        Args:
            command: Command to execute ('press_key')
            params: Command parameters
            
        Returns:
            bool: True if command executed successfully
        """
        if params is None:
            params = {}
        
        print(f"Remote[{self.device_type.upper()}]: Executing command '{command}' with params: {params}")
        
        if command == 'press_key':
            key = params.get('key')
            return self.press_key(key) if key else False
        
        print(f"Remote[{self.device_type.upper()}]: Unknown command: {command}")
        return False
    

            
    def _load_ir_config(self) -> Tuple[bool, dict]:
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
    
    def _convert_to_pulse_space(self, raw_code: str) -> str:
        """Convert IR code to pulse/space format."""
        # Split by spaces, remove +/- prefixes, convert to pulse/space format
        values = raw_code.strip().split()
        converted = []
        for i, val in enumerate(values):
            clean_val = val.lstrip('+-')
            if i % 2 == 0:
                converted.append(f"pulse {clean_val}")
            else:
                converted.append(f"space {clean_val}")
        return '\n'.join(converted)
    
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
            
            print(f"Remote[{self.device_type.upper()}]: Raw IR code: {raw_code[:100]}...")  # Debug: show first 100 chars
            
            # Convert to pulse/space format
            converted_code = self._convert_to_pulse_space(raw_code)
            
            # Use fixed temporary file path
            temp_path = "/tmp/ircode.txt"
            
            # Write converted IR code to fixed temp file
            with open(temp_path, 'w') as temp_file:
                temp_file.write(converted_code)
            
            result = subprocess.run(
                ["sudo", "ir-ctl", "--device", self.ir_path, "--send", temp_path], 
                check=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
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
            'success': True,
            'controller_type': self.controller_type,
            'device_type': self.device_type,
            'device_name': self.device_name,
            'ir_path': self.ir_path,
            'ir_type': self.ir_type,
            'ir_config_file': self.ir_config_file,
            'connected': self.is_connected,
            'supported_keys': self.ir_available_keys,
            'capabilities': [
                'ir_control', 'navigation', 'numeric_input', 'media_control', 
                'volume_control', 'channel_control', 'power_control'
            ]
        }
    
    def get_available_actions(self) -> Dict[str, Any]:
        """Get available actions from loaded IR config JSON."""
        if not self.ir_config_data:
            raise ValueError(f"No IR config loaded for {self.ir_type}")
        
        # Create actions for all keys in the config
        actions = []
        for key_name in self.ir_config_data.keys():
            # Skip empty keys
            if not self.ir_config_data[key_name]:
                continue
                
            actions.append({
                'id': f'ir_press_key_{key_name.lower()}',
                'label': f'{key_name}',
                'command': 'press_key',
                'action_type': 'remote',
                'params': {'key': key_name},
                'description': f'Press {key_name} key via infrared',
                'requiresInput': False
            })
        
        return {'remote': actions}
