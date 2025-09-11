"""
AI Command Description Registry
Central registry for all controller command descriptions
"""

from typing import Dict, List, Any, Optional
from .remote_descriptions import REMOTE_DESCRIPTIONS
from .verification_descriptions import VERIFICATION_DESCRIPTIONS
from .av_descriptions import AV_DESCRIPTIONS
from .web_descriptions import WEB_DESCRIPTIONS
from .desktop_descriptions import DESKTOP_DESCRIPTIONS
from .power_descriptions import POWER_DESCRIPTIONS

# Controller Implementation to Command Mapping
# Maps each controller implementation to the specific commands it provides
CONTROLLER_COMMAND_MAP = {
    # Remote Controller Implementations
    'android_mobile': [
        'click_element', 'click_element_by_id', 'tap_coordinates', 'swipe', 
        'long_press', 'press_key', 'send_text', 'scroll_to_element', 
        'find_element', 'dump_ui_elements'
    ],
    'android_tv': [
        'click_element', 'click_element_by_id', 'tap_coordinates', 'swipe',
        'long_press', 'press_key', 'send_text', 'navigate_dpad',
        'find_element', 'dump_ui_elements'
    ],
    'appium': [
        'find_element', 'click_element', 'send_keys', 'swipe', 'tap',
        'long_press', 'scroll', 'get_page_source', 'wait_for_element'
    ],
    'ir_remote': [
        'send_ir_command', 'press_button', 'power_on', 'power_off',
        'volume_up', 'volume_down', 'channel_up', 'channel_down'
    ],
    'bluetooth_remote': [
        'send_bluetooth_command', 'connect_bluetooth', 'disconnect_bluetooth',
        'press_button', 'send_key_sequence'
    ],
    
    # AV Controller Implementations
    'hdmi_stream': [
        'take_screenshot', 'take_video', 'start_stream', 'stop_stream',
        'get_stream_status', 'capture_frame', 'set_resolution'
    ],
    'vnc_stream': [
        'take_screenshot', 'start_vnc_stream', 'stop_vnc_stream',
        'get_vnc_status', 'vnc_click', 'vnc_type'
    ],
    'camera_stream': [
        'take_screenshot', 'start_camera_stream', 'stop_camera_stream',
        'get_camera_status', 'set_camera_resolution'
    ],
    
    # Verification Controller Implementations
    'image': [
        'waitForImageToAppear', 'waitForImageToDisappear'
    ],
    'text': [
        'waitForTextToAppear', 'waitForTextToDisappear'
    ],
    'video': [
        'DetectMotion', 'DetectBlackscreen', 'DetectColorChange',
        'AnalyzeVideoQuality'
    ],
    'audio': [
        'DetectAudioSpeech', 'DetectAudioPresence', 'AnalyzeAudioMenu',
        'DetectAudioLanguage', 'VerifyAudioQuality', 'WaitForAudioToStart', 'WaitForAudioToStop'
    ],
    'adb': [
        'waitForElementToAppear', 'waitForElementToDisappear',
        'waitForActivityChange', 'checkElementExists'
    ],
    'appium': [
        'waitForElementToAppear', 'waitForElementToDisappear',
        'waitForTextInElement', 'checkElementEnabled'
    ],
    
    # Desktop Controller Implementations
    'bash': [
        'execute_command', 'run_script', 'check_process', 'kill_process',
        'read_file', 'write_file', 'list_directory'
    ],
    'pyautogui': [
        'click_desktop', 'right_click_desktop', 'double_click_desktop',
        'type_text', 'press_hotkey', 'scroll_desktop', 'take_desktop_screenshot',
        'locate_image_on_desktop', 'move_mouse'
    ],
    
    # Web Controller Implementations
    'playwright': [
        'navigate_to_url', 'click_element', 'fill_input', 'select_option',
        'wait_for_element', 'scroll_page', 'take_page_screenshot',
        'execute_javascript', 'get_page_title', 'get_page_url'
    ],
    
    # Power Controller Implementations
    'tapo': [
        'power_on', 'power_off', 'power_cycle', 'get_power_status',
        'set_power_schedule', 'get_power_consumption'
    ],
    'usb_hub': [
        'power_on_port', 'power_off_port', 'power_cycle_port',
        'get_port_status', 'get_all_ports_status'
    ]
}

# Combine all descriptions into master registry
ALL_DESCRIPTIONS = {
    **REMOTE_DESCRIPTIONS,
    **VERIFICATION_DESCRIPTIONS,
    **AV_DESCRIPTIONS,
    **WEB_DESCRIPTIONS,
    **DESKTOP_DESCRIPTIONS,
    **POWER_DESCRIPTIONS
}

def get_enhanced_description(command: str) -> Dict[str, str]:
    """
    Get enhanced description for any command.
    
    Args:
        command: Command name to look up
        
    Returns:
        Dict with 'description' and 'example' keys
    """
    return ALL_DESCRIPTIONS.get(command, {
        'description': f'Execute {command} command',
        'example': f'{command}()'
    })

def enhance_action_with_description(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add enhanced description to an action dictionary.
    
    Args:
        action: Original action dict from controller
        
    Returns:
        Enhanced action dict with AI description fields
    """
    enhanced = action.copy()
    command = action.get('command', '')
    
    # Get enhanced description
    desc_info = get_enhanced_description(command)
    
    # Add AI-specific fields without modifying original structure
    enhanced['ai_description'] = desc_info['description']
    enhanced['ai_example'] = desc_info['example']
    
    return enhanced

def enhance_verification_with_description(verification: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add enhanced description to a verification dictionary.
    
    Args:
        verification: Original verification dict from controller
        
    Returns:
        Enhanced verification dict with AI description fields
    """
    enhanced = verification.copy()
    command = verification.get('command', '')
    
    # Get enhanced description
    desc_info = get_enhanced_description(command)
    
    # Add AI-specific fields
    enhanced['ai_description'] = desc_info['description']
    enhanced['ai_example'] = desc_info['example']
    
    return enhanced

def enhance_actions_list(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhance a list of actions with AI descriptions.
    
    Args:
        actions: List of action dicts from controller
        
    Returns:
        List of enhanced action dicts
    """
    return [enhance_action_with_description(action) for action in actions]

def enhance_verifications_list(verifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhance a list of verifications with AI descriptions.
    
    Args:
        verifications: List of verification dicts from controller
        
    Returns:
        List of enhanced verification dicts
    """
    return [enhance_verification_with_description(verification) for verification in verifications]

def enhance_controller_actions(controller_type: str, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhance actions from any controller type with AI descriptions.
    
    Args:
        controller_type: Type of controller ('remote', 'verification', 'av', etc.)
        actions: List of actions from controller
        
    Returns:
        List of enhanced actions with AI descriptions
    """
    if controller_type == 'verification':
        return enhance_verifications_list(actions)
    else:
        return enhance_actions_list(actions)

def get_all_enhanced_actions_for_device(device_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all enhanced actions for a specific device.
    
    Args:
        device_id: Device identifier
        
    Returns:
        Dict with controller categories as keys, enhanced actions as values
    """
    try:
        from shared.lib.utils.host_utils import get_device_by_id, get_controller
        
        device = get_device_by_id(device_id)
        if not device:
            return {}
        
        enhanced_actions = {}
        
        # Get remote controller actions
        remote_controller = get_controller(device_id, 'remote')
        if remote_controller and hasattr(remote_controller, 'get_available_actions'):
            try:
                actions = remote_controller.get_available_actions()
                for category, action_list in actions.items():
                    if isinstance(action_list, list):
                        enhanced_actions[category] = enhance_actions_list(action_list)
            except Exception as e:
                print(f"[@ai_descriptions] Error getting remote actions for {device_id}: {e}")
        
        # Get AV controller actions
        av_controller = get_controller(device_id, 'av')
        if av_controller and hasattr(av_controller, 'get_available_actions'):
            try:
                actions = av_controller.get_available_actions()
                if isinstance(actions, dict):
                    for category, action_list in actions.items():
                        if isinstance(action_list, list):
                            enhanced_actions[f'av_{category}'] = enhance_actions_list(action_list)
                elif isinstance(actions, list):
                    enhanced_actions['av'] = enhance_actions_list(actions)
            except Exception as e:
                print(f"[@ai_descriptions] Error getting AV actions for {device_id}: {e}")
        
        # Get web controller actions
        web_controller = get_controller(device_id, 'web')
        if web_controller and hasattr(web_controller, 'get_available_actions'):
            try:
                actions = web_controller.get_available_actions()
                if isinstance(actions, dict):
                    for category, action_list in actions.items():
                        if isinstance(action_list, list):
                            enhanced_actions[f'web_{category}'] = enhance_actions_list(action_list)
                elif isinstance(actions, list):
                    enhanced_actions['web'] = enhance_actions_list(actions)
            except Exception as e:
                print(f"[@ai_descriptions] Error getting web actions for {device_id}: {e}")
        
        # Get desktop controller actions
        for desktop_type in ['bash', 'pyautogui']:
            desktop_controller = get_controller(device_id, f'desktop_{desktop_type}')
            if desktop_controller and hasattr(desktop_controller, 'get_available_actions'):
                try:
                    actions = desktop_controller.get_available_actions()
                    if isinstance(actions, dict):
                        for category, action_list in actions.items():
                            if isinstance(action_list, list):
                                enhanced_actions[f'desktop_{desktop_type}_{category}'] = enhance_actions_list(action_list)
                    elif isinstance(actions, list):
                        enhanced_actions[f'desktop_{desktop_type}'] = enhance_actions_list(actions)
                except Exception as e:
                    print(f"[@ai_descriptions] Error getting desktop {desktop_type} actions for {device_id}: {e}")
        
        # Get power controller actions
        power_controller = get_controller(device_id, 'power')
        if power_controller and hasattr(power_controller, 'get_available_actions'):
            try:
                actions = power_controller.get_available_actions()
                if isinstance(actions, dict):
                    for category, action_list in actions.items():
                        if isinstance(action_list, list):
                            enhanced_actions[f'power_{category}'] = enhance_actions_list(action_list)
                elif isinstance(actions, list):
                    enhanced_actions['power'] = enhance_actions_list(actions)
            except Exception as e:
                print(f"[@ai_descriptions] Error getting power actions for {device_id}: {e}")
        
        # Get verification actions
        verification_types = ['image', 'text', 'adb', 'appium', 'video', 'audio']
        enhanced_actions['verification'] = []
        
        for v_type in verification_types:
            controller = get_controller(device_id, f'verification_{v_type}')
            if controller and hasattr(controller, 'get_available_verifications'):
                try:
                    verifications = controller.get_available_verifications()
                    if isinstance(verifications, list):
                        enhanced_verifications = enhance_verifications_list(verifications)
                        enhanced_actions['verification'].extend(enhanced_verifications)
                except Exception as e:
                    print(f"[@ai_descriptions] Error getting {v_type} verifications for {device_id}: {e}")
        
        return enhanced_actions
        
    except Exception as e:
        print(f"[@ai_descriptions] Error getting enhanced actions for device {device_id}: {e}")
        return {}

def get_commands_for_device_model(device_model: str) -> Dict[str, Any]:
    """
    Get model-specific commands based on DEVICE_CONTROLLER_MAP.
    This ensures AI only gets commands that the device model actually supports.
    
    Args:
        device_model: Device model name (e.g., 'android_mobile', 'stb', 'S21x')
        
    Returns:
        Dict with 'actions' and 'verifications' keys containing model-specific commands
    """
    try:
        # Import here to avoid circular imports
        from backend_core.src.controllers.controller_config_factory import DEVICE_CONTROLLER_MAP, CONTROLLER_VERIFICATION_MAP
        
        if device_model not in DEVICE_CONTROLLER_MAP:
            return {
                'error': f'Device model {device_model} not supported',
                'available_models': list(DEVICE_CONTROLLER_MAP.keys()),
                'actions': [],
                'verifications': []
            }
        
        model_config = DEVICE_CONTROLLER_MAP[device_model]
        available_actions = []
        available_verifications = []
        
        print(f"[@ai_descriptions:get_commands_for_device_model] Getting commands for model: {device_model}")
        print(f"[@ai_descriptions:get_commands_for_device_model] Model config: {model_config}")
        
        # Process each controller type this model supports
        for controller_type, implementations in model_config.items():
            for impl in implementations:
                print(f"[@ai_descriptions:get_commands_for_device_model] Processing {controller_type}/{impl}")
                
                # Get action commands for this implementation
                if impl in CONTROLLER_COMMAND_MAP:
                    for cmd in CONTROLLER_COMMAND_MAP[impl]:
                        if cmd in ALL_DESCRIPTIONS:
                            desc_info = ALL_DESCRIPTIONS[cmd]
                            action = {
                                'command': cmd,
                                'category': controller_type,
                                'implementation': impl,
                                'ai_description': desc_info['description'],
                                'ai_example': desc_info['example'],
                                'params': {}  # Default empty params
                            }
                            available_actions.append(action)
                            print(f"[@ai_descriptions:get_commands_for_device_model] Added action: {cmd}")
                else:
                    print(f"[@ai_descriptions:get_commands_for_device_model] WARNING: No commands found for {controller_type} implementation: {impl}")
        
        # Load verification commands from CONTROLLER_VERIFICATION_MAP
        verification_types = []
        for controller_list in model_config.values():
            for controller_impl in controller_list:
                verification_types.extend(CONTROLLER_VERIFICATION_MAP.get(controller_impl, []))
        
        # Add verification commands
        for verif_type in set(verification_types):
            if verif_type in CONTROLLER_COMMAND_MAP:
                for cmd in CONTROLLER_COMMAND_MAP[verif_type]:
                    if cmd in ALL_DESCRIPTIONS:
                        desc_info = ALL_DESCRIPTIONS[cmd]
                        verification = {
                            'command': cmd,
                            'category': 'verification',
                            'implementation': verif_type,
                            'ai_description': desc_info['description'],
                            'ai_example': desc_info['example'],
                            'params': {}
                        }
                        available_verifications.append(verification)
                        print(f"[@ai_descriptions:get_commands_for_device_model] Added verification: {cmd}")
        
        result = {
            'actions': available_actions,
            'verifications': available_verifications,
            'model': device_model,
            'supported_controllers': model_config,
            'total_actions': len(available_actions),
            'total_verifications': len(available_verifications)
        }
        
        print(f"[@ai_descriptions:get_commands_for_device_model] Result: {len(available_actions)} actions, {len(available_verifications)} verifications")
        return result
        
    except Exception as e:
        print(f"[@ai_descriptions:get_commands_for_device_model] Error getting commands for model {device_model}: {e}")
        return {
            'error': f'Error getting commands for model {device_model}: {str(e)}',
            'actions': [],
            'verifications': [],
            'total_actions': 0,
            'total_verifications': 0
        }

def get_enhanced_actions_for_ai(device_id: str) -> Dict[str, Any]:
    """
    Get device actions enhanced with AI descriptions, formatted for AI consumption.
    This is the main function for AI test case generation.
    
    Args:
        device_id: Device identifier
        
    Returns:
        Dict with 'actions' and 'verifications' keys containing enhanced command lists
    """
    try:
        all_enhanced = get_all_enhanced_actions_for_device(device_id)
        
        # Flatten actions into categories for AI
        actions_by_type = {}
        verifications = []
        
        for category, action_list in all_enhanced.items():
            if category == 'verification':
                verifications.extend(action_list)
            else:
                # Group by action type for better AI understanding
                if category not in actions_by_type:
                    actions_by_type[category] = []
                actions_by_type[category].extend(action_list)
        
        # Create flattened list for AI with type annotations
        all_actions = []
        for category, actions in actions_by_type.items():
            for action in actions:
                action_with_type = action.copy()
                action_with_type['category'] = category
                all_actions.append(action_with_type)
        
        return {
            'actions': all_actions,
            'verifications': verifications,
            'total_actions': len(all_actions),
            'total_verifications': len(verifications)
        }
        
    except Exception as e:
        print(f"[@ai_descriptions] Error getting AI-formatted actions for device {device_id}: {e}")
        return {
            'actions': [],
            'verifications': [],
            'total_actions': 0,
            'total_verifications': 0
        }

def get_command_categories() -> Dict[str, List[str]]:
    """
    Get all available command categories and their commands.
    
    Returns:
        Dict mapping categories to command lists
    """
    categories = {
        'remote': list(REMOTE_DESCRIPTIONS.keys()),
        'verification': list(VERIFICATION_DESCRIPTIONS.keys()),
        'av': list(AV_DESCRIPTIONS.keys()),
        'web': list(WEB_DESCRIPTIONS.keys()),
        'desktop': list(DESKTOP_DESCRIPTIONS.keys()),
        'power': list(POWER_DESCRIPTIONS.keys())
    }
    
    return categories

def search_commands_by_keyword(keyword: str) -> List[Dict[str, Any]]:
    """
    Search for commands containing a keyword in name or description.
    
    Args:
        keyword: Search term
        
    Returns:
        List of matching commands with their descriptions
    """
    keyword_lower = keyword.lower()
    matches = []
    
    for command, desc_info in ALL_DESCRIPTIONS.items():
        if (keyword_lower in command.lower() or 
            keyword_lower in desc_info.get('description', '').lower()):
            matches.append({
                'command': command,
                'description': desc_info.get('description', ''),
                'example': desc_info.get('example', '')
            })
    
    return matches

def get_commands_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Get all commands for a specific category.
    
    Args:
        category: Category name ('remote', 'verification', etc.)
        
    Returns:
        List of commands in that category
    """
    category_map = {
        'remote': REMOTE_DESCRIPTIONS,
        'verification': VERIFICATION_DESCRIPTIONS,
        'av': AV_DESCRIPTIONS,
        'web': WEB_DESCRIPTIONS,
        'desktop': DESKTOP_DESCRIPTIONS,
        'power': POWER_DESCRIPTIONS
    }
    
    descriptions = category_map.get(category, {})
    return [
        {
            'command': command,
            'description': desc_info.get('description', ''),
            'example': desc_info.get('example', '')
        }
        for command, desc_info in descriptions.items()
    ]
