"""
Action Command Validation Utility

Validates action commands against available controllers before saving to database.
Prevents invalid action commands from being stored in edges.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from backend_server.src.mcp.utils.api_client import MCPAPIClient
from shared.src.lib.config.constants import APP_CONFIG


logger = logging.getLogger(__name__)


class ActionValidator:
    """
    Validates action commands against available device controllers.
    
    This prevents invalid action commands from being saved to edges,
    catching errors at creation time rather than execution time.
    """
    
    def __init__(self, api_client: MCPAPIClient):
        self.api_client = api_client
        self._cache = {}  # Cache valid commands per device_model
    
    def validate_action_sets(
        self,
        action_sets: List[Dict[str, Any]],
        device_model: str,
        host_name: str = None,
        device_id: str = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate action commands in action_sets against available controllers.
        
        Args:
            action_sets: List of action_set dicts with 'actions', 'retry_actions', 'failure_actions'
            device_model: Device model (e.g., 'web', 'android_mobile', 'android_tv', 'host_vnc')
            host_name: Host name (optional - used for fetching available commands)
            device_id: Device ID (optional - used for fetching available commands)
        
        Returns:
            Tuple of (is_valid, errors, warnings)
            - is_valid: True if all actions are valid
            - errors: List of error messages
            - warnings: List of warning messages
        """
        if not action_sets:
            return True, [], []
        
        # No default host_name - must be provided explicitly via get_compatible_hosts()
        device_id = device_id or self._get_default_device_id_for_model(device_model)
        
        # Get valid commands for this device model
        valid_commands = self._get_valid_commands(device_model, host_name, device_id)
        
        if not valid_commands:
            # If we can't fetch commands, return warning but allow save
            warning = (
                f"⚠️ Could not fetch valid action commands for device model '{device_model}'. "
                f"Actions will be validated at execution time."
            )
            return True, [], [warning]
        
        # Validate each action in all action_sets
        errors = []
        warnings = []
        
        for action_set_idx, action_set in enumerate(action_sets):
            action_set_id = action_set.get('id', f'action_set_{action_set_idx}')
            
            # Validate main actions
            self._validate_action_list(
                action_set.get('actions', []),
                valid_commands,
                device_model,
                f"action_set '{action_set_id}'",
                errors,
                warnings
            )
            
            # Validate retry actions
            self._validate_action_list(
                action_set.get('retry_actions', []),
                valid_commands,
                device_model,
                f"retry_actions in '{action_set_id}'",
                errors,
                warnings
            )
            
            # Validate failure actions
            self._validate_action_list(
                action_set.get('failure_actions', []),
                valid_commands,
                device_model,
                f"failure_actions in '{action_set_id}'",
                errors,
                warnings
            )
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def _validate_action_list(
        self,
        actions: List[Dict[str, Any]],
        valid_commands: Dict[str, Dict],
        device_model: str,
        context: str,
        errors: List[str],
        warnings: List[str]
    ):
        """Validate a list of actions and append errors/warnings"""
        for action_idx, action in enumerate(actions):
            command = action.get('command')
            
            if not command:
                errors.append(f"Action {action_idx + 1} in {context}: Missing 'command' field")
                continue
            
            # Check if command exists for this device model
            if command not in valid_commands:
                similar = self._find_similar_command(command, valid_commands)
                error_msg = (
                    f"Action {action_idx + 1} in {context}: Invalid command '{command}' for device model '{device_model}'\n"
                    f"   Available commands: {', '.join(sorted(valid_commands.keys())[:5])}..."
                )
                if similar:
                    error_msg += f"\n   Did you mean '{similar}'?"
                
                errors.append(error_msg)
            else:
                # Command is valid - check params
                command_info = valid_commands[command]
                param_errors = self._validate_params(
                    action.get('params', {}),
                    command_info.get('params', {}),
                    command,
                    context
                )
                if param_errors:
                    warnings.extend(param_errors)
    
    def _get_valid_commands(
        self,
        device_model: str,
        host_name: str,
        device_id: str
    ) -> Dict[str, Dict]:
        """
        Get valid action commands for a device model.
        
        Returns dict mapping command_name -> command_info
        """
        cache_key = f"{device_model}_{host_name}_{device_id}"
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Call list_actions endpoint
            result = self.api_client.post(
                '/mcp/list_actions',
                data={
                    'device_id': device_id,
                    'host_name': host_name
                }
            )
            
            if not result.get('success'):
                logger.warning(
                    f"Failed to fetch action commands for {device_model}: "
                    f"{result.get('error', 'Unknown error')}"
                )
                return {}
            
            # Parse response to build command map
            commands = {}
            actions = result.get('actions', {})
            
            for category, category_actions in actions.items():
                for action in category_actions:
                    command_name = action.get('command')
                    if command_name:
                        commands[command_name] = {
                            'category': category,
                            'description': action.get('description', ''),
                            'params': action.get('params', {})
                        }
            
            # Cache the result
            self._cache[cache_key] = commands
            return commands
        
        except Exception as e:
            logger.error(f"Error fetching action commands: {e}", exc_info=True)
            return {}
    
    def _get_default_device_id_for_model(self, device_model: str) -> str:
        """Get default device ID based on device model"""
        model_to_device = {
            'android_mobile': 'device1',
            'android_tv': 'device3',
            'web': 'host',
            'host_vnc': 'host',
            'fire_tv': 'device3',
            'stb': 'device1'
        }
        return model_to_device.get(device_model, 'device1')
    
    def _find_similar_command(self, command: str, valid_commands: Dict[str, Dict]) -> Optional[str]:
        """Find similar command using simple string matching"""
        command_lower = command.lower()
        
        # First try exact substring match
        for valid_cmd in valid_commands:
            if command_lower in valid_cmd.lower() or valid_cmd.lower() in command_lower:
                return valid_cmd
        
        # Try similarity matching
        def similarity(s1: str, s2: str) -> int:
            """Simple similarity score based on common characters"""
            s1, s2 = s1.lower(), s2.lower()
            return sum(c in s2 for c in s1)
        
        best_match = None
        best_score = 0
        
        for valid_cmd in valid_commands:
            score = similarity(command, valid_cmd)
            if score > best_score and score >= len(command) * 0.5:
                best_score = score
                best_match = valid_cmd
        
        return best_match
    
    def _validate_params(
        self,
        provided_params: Dict[str, Any],
        expected_params: Dict[str, Dict],
        command: str,
        context: str
    ) -> List[str]:
        """
        Validate parameters against expected schema.
        
        Returns list of warning messages (not errors - params are flexible)
        """
        warnings = []
        
        # Check for required params
        for param_name, param_info in expected_params.items():
            if param_info.get('required', False) and param_name not in provided_params:
                warnings.append(
                    f"   ⚠️ Command '{command}' in {context}: Missing required parameter '{param_name}'"
                )
        
        return warnings
    
    def get_valid_commands_for_display(
        self,
        device_model: str,
        host_name: str = None,
        device_id: str = None
    ) -> str:
        """
        Get formatted list of valid commands for error messages.
        
        Returns:
            Formatted string listing available commands by category
        """
        # No default host_name - must be provided explicitly via get_compatible_hosts()
        device_id = device_id or self._get_default_device_id_for_model(device_model)
        
        valid_commands = self._get_valid_commands(device_model, host_name, device_id)
        
        if not valid_commands:
            return f"No action commands available for device model '{device_model}'"
        
        # Group by category
        by_category = {}
        for cmd, info in valid_commands.items():
            category = info.get('category', 'other')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(cmd)
        
        # Format output
        lines = [f"\n📋 Available action commands for '{device_model}':\n"]
        for category, commands in sorted(by_category.items()):
            lines.append(f"  **{category.upper()}**:")
            for cmd in sorted(commands):
                lines.append(f"    - {cmd}")
        
        lines.append(f"\n💡 To see full details, call: list_actions(device_id='{device_id}', host_name='{host_name}')")
        
        return "\n".join(lines)


def validate_edge_actions(
    action_sets: List[Dict[str, Any]],
    device_model: str,
    api_client: MCPAPIClient,
    host_name: str = None,
    device_id: str = None
) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate edge actions.
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = ActionValidator(api_client)
    return validator.validate_action_sets(
        action_sets,
        device_model,
        host_name,
        device_id
    )

