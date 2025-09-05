"""
Remote Controller Command Descriptions
Covers: AndroidTV, AndroidMobile, Appium, IR, Bluetooth controllers
"""

REMOTE_DESCRIPTIONS = {
    # Android TV/Mobile Commands
    'click_element': {
        'description': 'Click UI element by visible text or Android resource ID. Best for buttons, tabs, menu items with text.',
        'example': "click_element(element_id='Settings')"
    },
    'tap_coordinates': {
        'description': 'Tap at exact screen coordinates. Use for unlabeled icons, images, or precise positioning.',
        'example': "tap_coordinates(x=100, y=200)"
    },
    'press_key': {
        'description': 'Press system/navigation keys. Use for directional navigation, BACK, HOME, or media keys.',
        'example': "press_key(key='UP') or press_key(key='BACK')"
    },
    'swipe': {
        'description': 'Swipe gesture between coordinates. Use for scrolling, swiping between screens, or drag actions.',
        'example': "swipe(start_x=100, start_y=200, end_x=100, end_y=400)"
    },
    'long_press': {
        'description': 'Long press on coordinates or element. Use for context menus or special actions.',
        'example': "long_press(x=100, y=200, duration=2.0)"
    },
    'scroll': {
        'description': 'Scroll screen in specified direction. Use to navigate through lists or long content.',
        'example': "scroll(direction='down', distance=500)"
    },
    'drag': {
        'description': 'Drag from one coordinate to another. Use for drag-and-drop operations or custom gestures.',
        'example': "drag(start_x=100, start_y=200, end_x=300, end_y=400)"
    },
    'input_text': {
        'description': 'Input text into focused field. Use after clicking on text input fields.',
        'example': "input_text(text='username123')"
    },
    'clear_text': {
        'description': 'Clear text from focused input field. Use to reset form fields.',
        'example': "clear_text()"
    },
    
    # IR Remote Commands
    'send_ir_command': {
        'description': 'Send infrared remote command. Use for traditional TV/STB remote control (power, volume, channels).',
        'example': "send_ir_command(command='POWER') or send_ir_command(command='CH_UP')"
    },
    'power_toggle': {
        'description': 'Toggle device power via IR. Use to turn TV/STB on or off.',
        'example': "power_toggle()"
    },
    'volume_up': {
        'description': 'Increase volume via IR remote. Use for audio level control.',
        'example': "volume_up()"
    },
    'volume_down': {
        'description': 'Decrease volume via IR remote. Use for audio level control.',
        'example': "volume_down()"
    },
    'channel_up': {
        'description': 'Change to next channel via IR. Use for channel navigation on TV/STB.',
        'example': "channel_up()"
    },
    'channel_down': {
        'description': 'Change to previous channel via IR. Use for channel navigation on TV/STB.',
        'example': "channel_down()"
    },
    'mute_toggle': {
        'description': 'Toggle audio mute via IR. Use to mute/unmute TV/STB audio.',
        'example': "mute_toggle()"
    },
    
    # Appium Cross-Platform Commands
    'find_element': {
        'description': 'Find UI element using Appium selectors. Cross-platform element detection for iOS/Android.',
        'example': "find_element(by='id', value='com.app:id/button')"
    },
    'find_elements': {
        'description': 'Find multiple UI elements matching selector. Use to get lists of similar elements.',
        'example': "find_elements(by='class', value='android.widget.Button')"
    },
    'scroll_to_element': {
        'description': 'Scroll until element becomes visible. Use when element is off-screen in scrollable content.',
        'example': "scroll_to_element(element_text='Settings')"
    },
    'wait_for_element': {
        'description': 'Wait for element to appear using Appium. Cross-platform element waiting.',
        'example': "wait_for_element(by='id', value='submit_button', timeout=10)"
    },
    'get_element_text': {
        'description': 'Get text content from UI element. Use to read labels, messages, or content.',
        'example': "get_element_text(element_id='status_label')"
    },
    'get_element_attribute': {
        'description': 'Get attribute value from UI element. Use to check element properties or state.',
        'example': "get_element_attribute(element_id='checkbox', attribute='checked')"
    },
    'is_element_displayed': {
        'description': 'Check if element is visible on screen. Use for UI state verification.',
        'example': "is_element_displayed(element_id='error_message')"
    },
    'is_element_enabled': {
        'description': 'Check if element is enabled/interactive. Use to verify element accessibility.',
        'example': "is_element_enabled(element_id='submit_button')"
    },
    
    # Bluetooth Remote Commands
    'connect_bluetooth': {
        'description': 'Connect to Bluetooth HID device. Use to establish remote control connection.',
        'example': "connect_bluetooth(device_address='AA:BB:CC:DD:EE:FF')"
    },
    'disconnect_bluetooth': {
        'description': 'Disconnect Bluetooth HID device. Use to end remote control session.',
        'example': "disconnect_bluetooth()"
    },
    'send_bluetooth_key': {
        'description': 'Send key via Bluetooth HID. Use for wireless remote control commands.',
        'example': "send_bluetooth_key(key='HOME')"
    },
    
    # Navigation Commands (Universal)
    'execute_navigation': {
        'description': 'Navigate between app screens using navigation tree. Use for major screen transitions within the app.',
        'example': "execute_navigation(target_node='live') or execute_navigation(target_node='settings')"
    },
    'go_back': {
        'description': 'Navigate back to previous screen. Use to return from current screen.',
        'example': "go_back()"
    },
    'go_home': {
        'description': 'Navigate to home screen. Use to return to main app screen or system home.',
        'example': "go_home()"
    },
    'open_app': {
        'description': 'Launch specific application. Use to start apps or switch between apps.',
        'example': "open_app(package_name='com.netflix.mediaclient')"
    },
    'close_app': {
        'description': 'Close/terminate application. Use to exit apps or free resources.',
        'example': "close_app(package_name='com.netflix.mediaclient')"
    },
    
    # Timing Commands
    'wait': {
        'description': 'Wait for specified duration. Use to add delays between actions or wait for processing.',
        'example': "wait(duration=2.0)"
    },
    'wait_for_idle': {
        'description': 'Wait until system is idle. Use to ensure previous actions complete before continuing.',
        'example': "wait_for_idle(timeout=5.0)"
    }
}
