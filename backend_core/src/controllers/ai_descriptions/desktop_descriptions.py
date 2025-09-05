"""
Desktop Controller Command Descriptions  
Covers: Bash, PyAutoGUI desktop automation
"""

DESKTOP_DESCRIPTIONS = {
    # Bash Shell Commands
    'execute_command': {
        'description': 'Execute shell command on host system. Use for system operations or script execution.',
        'example': "execute_command(command='ls -la /tmp')"
    },
    'run_script': {
        'description': 'Run shell script file. Use for complex automation or system configuration.',
        'example': "run_script(script_path='/path/to/script.sh')"
    },
    'execute_with_timeout': {
        'description': 'Execute command with timeout limit. Use for potentially long-running commands.',
        'example': "execute_with_timeout(command='ping google.com', timeout=10)"
    },
    'execute_in_background': {
        'description': 'Execute command in background process. Use for non-blocking operations.',
        'example': "execute_in_background(command='tail -f /var/log/system.log')"
    },
    'kill_process': {
        'description': 'Terminate specific process by PID or name. Use for cleanup or process management.',
        'example': "kill_process(process_name='firefox')"
    },
    
    # File System Commands
    'create_file': {
        'description': 'Create new file with content. Use for test data setup or configuration.',
        'example': "create_file(file_path='/tmp/test.txt', content='Hello World')"
    },
    'read_file': {
        'description': 'Read content from file. Use for verification or data extraction.',
        'example': "read_file(file_path='/var/log/app.log')"
    },
    'write_file': {
        'description': 'Write content to file (overwrite). Use for configuration or data setup.',
        'example': "write_file(file_path='/tmp/config.txt', content='setting=value')"
    },
    'append_file': {
        'description': 'Append content to existing file. Use for logging or incremental data.',
        'example': "append_file(file_path='/tmp/log.txt', content='New entry')"
    },
    'delete_file': {
        'description': 'Delete file from filesystem. Use for cleanup or test teardown.',
        'example': "delete_file(file_path='/tmp/temp_file.txt')"
    },
    'copy_file': {
        'description': 'Copy file to new location. Use for backup or file distribution.',
        'example': "copy_file(source='/tmp/source.txt', destination='/tmp/backup.txt')"
    },
    'move_file': {
        'description': 'Move file to new location. Use for file organization or renaming.',
        'example': "move_file(source='/tmp/old.txt', destination='/tmp/new.txt')"
    },
    'check_file_exists': {
        'description': 'Check if file exists on filesystem. Use for file verification.',
        'example': "check_file_exists(file_path='/etc/config.conf')"
    },
    'get_file_size': {
        'description': 'Get file size in bytes. Use for file verification or monitoring.',
        'example': "get_file_size(file_path='/var/log/app.log')"
    },
    'get_file_permissions': {
        'description': 'Get file permissions and ownership. Use for security verification.',
        'example': "get_file_permissions(file_path='/etc/passwd')"
    },
    'set_file_permissions': {
        'description': 'Set file permissions. Use for security configuration.',
        'example': "set_file_permissions(file_path='/tmp/script.sh', permissions='755')"
    },
    
    # Directory Commands
    'create_directory': {
        'description': 'Create new directory. Use for test setup or organization.',
        'example': "create_directory(dir_path='/tmp/test_dir')"
    },
    'delete_directory': {
        'description': 'Delete directory and contents. Use for cleanup or test teardown.',
        'example': "delete_directory(dir_path='/tmp/test_dir')"
    },
    'list_directory': {
        'description': 'List directory contents. Use for file discovery or verification.',
        'example': "list_directory(dir_path='/var/log')"
    },
    'change_directory': {
        'description': 'Change current working directory. Use for context-sensitive operations.',
        'example': "change_directory(dir_path='/home/user')"
    },
    'get_current_directory': {
        'description': 'Get current working directory path. Use for path verification.',
        'example': "get_current_directory()"
    },
    
    # System Information Commands
    'get_system_info': {
        'description': 'Get system information (OS, version, architecture). Use for environment verification.',
        'example': "get_system_info()"
    },
    'get_memory_usage': {
        'description': 'Get system memory usage statistics. Use for resource monitoring.',
        'example': "get_memory_usage()"
    },
    'get_cpu_usage': {
        'description': 'Get CPU usage statistics. Use for performance monitoring.',
        'example': "get_cpu_usage()"
    },
    'get_disk_usage': {
        'description': 'Get disk space usage. Use for storage monitoring.',
        'example': "get_disk_usage(path='/')"
    },
    'get_network_interfaces': {
        'description': 'Get network interface information. Use for network verification.',
        'example': "get_network_interfaces()"
    },
    'get_running_processes': {
        'description': 'Get list of running processes. Use for process monitoring.',
        'example': "get_running_processes()"
    },
    
    # Service Management Commands
    'start_service': {
        'description': 'Start system service. Use for service management or test setup.',
        'example': "start_service(service_name='nginx')"
    },
    'stop_service': {
        'description': 'Stop system service. Use for service management or cleanup.',
        'example': "stop_service(service_name='apache2')"
    },
    'restart_service': {
        'description': 'Restart system service. Use for service recovery or configuration reload.',
        'example': "restart_service(service_name='mysql')"
    },
    'get_service_status': {
        'description': 'Check system service status. Use for service verification.',
        'example': "get_service_status(service_name='ssh')"
    },
    'enable_service': {
        'description': 'Enable service to start on boot. Use for permanent service configuration.',
        'example': "enable_service(service_name='docker')"
    },
    'disable_service': {
        'description': 'Disable service from starting on boot. Use for service configuration.',
        'example': "disable_service(service_name='bluetooth')"
    },
    
    # PyAutoGUI Desktop Automation Commands
    'click_desktop': {
        'description': 'Click at desktop coordinates. Use for desktop applications or system UI interaction.',
        'example': "click_desktop(x=100, y=200)"
    },
    'double_click_desktop': {
        'description': 'Double-click at desktop coordinates. Use for file/folder opening.',
        'example': "double_click_desktop(x=150, y=250)"
    },
    'right_click_desktop': {
        'description': 'Right-click at desktop coordinates. Use for context menus.',
        'example': "right_click_desktop(x=300, y=400)"
    },
    'drag_desktop': {
        'description': 'Drag from one desktop coordinate to another. Use for drag-and-drop operations.',
        'example': "drag_desktop(start_x=100, start_y=200, end_x=300, end_y=400)"
    },
    'scroll_desktop': {
        'description': 'Scroll at desktop coordinates. Use for scrolling in desktop applications.',
        'example': "scroll_desktop(x=500, y=300, clicks=3, direction='up')"
    },
    
    # Keyboard Input Commands
    'type_text': {
        'description': 'Type text using keyboard. Use for text input in desktop applications.',
        'example': "type_text(text='Hello World')"
    },
    'press_key': {
        'description': 'Press single keyboard key. Use for special keys or shortcuts.',
        'example': "press_key(key='enter')"
    },
    'press_hotkey': {
        'description': 'Press keyboard shortcut combination. Use for desktop shortcuts or application commands.',
        'example': "press_hotkey(keys=['ctrl', 'c'])"
    },
    'hold_key': {
        'description': 'Hold key down for duration. Use for continuous key press operations.',
        'example': "hold_key(key='shift', duration=2.0)"
    },
    'type_with_delay': {
        'description': 'Type text with delay between characters. Use for slow typing simulation.',
        'example': "type_with_delay(text='password', delay=0.1)"
    },
    
    # Mouse Control Commands
    'move_mouse': {
        'description': 'Move mouse to desktop coordinates. Use for mouse positioning.',
        'example': "move_mouse(x=500, y=300)"
    },
    'get_mouse_position': {
        'description': 'Get current mouse coordinates. Use for position verification or debugging.',
        'example': "get_mouse_position()"
    },
    'mouse_down': {
        'description': 'Press mouse button down (without release). Use for custom mouse operations.',
        'example': "mouse_down(button='left')"
    },
    'mouse_up': {
        'description': 'Release mouse button. Use to complete custom mouse operations.',
        'example': "mouse_up(button='left')"
    },
    
    # Screen Analysis Commands
    'take_desktop_screenshot': {
        'description': 'Capture desktop screenshot. Use for desktop application verification.',
        'example': "take_desktop_screenshot(filename='desktop.png')"
    },
    'find_image_on_desktop': {
        'description': 'Find image location on desktop. Use for UI element detection.',
        'example': "find_image_on_desktop(image_path='button.png')"
    },
    'wait_for_image_on_desktop': {
        'description': 'Wait for image to appear on desktop. Use for UI state verification.',
        'example': "wait_for_image_on_desktop(image_path='dialog.png', timeout=10)"
    },
    'get_pixel_color': {
        'description': 'Get color of pixel at coordinates. Use for visual verification.',
        'example': "get_pixel_color(x=100, y=200)"
    },
    'locate_text_on_desktop': {
        'description': 'Find text location on desktop using OCR. Use for text-based UI interaction.',
        'example': "locate_text_on_desktop(text='OK')"
    },
    
    # Window Management Commands
    'get_active_window': {
        'description': 'Get information about active window. Use for window state verification.',
        'example': "get_active_window()"
    },
    'get_all_windows': {
        'description': 'Get list of all open windows. Use for window management or verification.',
        'example': "get_all_windows()"
    },
    'activate_window': {
        'description': 'Bring specific window to foreground. Use for window focus management.',
        'example': "activate_window(window_title='Calculator')"
    },
    'close_window': {
        'description': 'Close specific window. Use for application cleanup.',
        'example': "close_window(window_title='Notepad')"
    },
    'minimize_window': {
        'description': 'Minimize specific window. Use for window management.',
        'example': "minimize_window(window_title='Browser')"
    },
    'maximize_window': {
        'description': 'Maximize specific window. Use for full-screen operations.',
        'example': "maximize_window(window_title='Editor')"
    },
    'resize_window': {
        'description': 'Resize specific window. Use for window size management.',
        'example': "resize_window(window_title='Terminal', width=800, height=600)"
    },
    'move_window': {
        'description': 'Move window to specific position. Use for window positioning.',
        'example': "move_window(window_title='App', x=100, y=100)"
    },
    
    # Application Launch Commands
    'launch_application': {
        'description': 'Launch desktop application. Use to start applications for testing.',
        'example': "launch_application(app_path='/usr/bin/firefox')"
    },
    'launch_application_with_args': {
        'description': 'Launch application with command line arguments. Use for specific app configurations.',
        'example': "launch_application_with_args(app_path='/usr/bin/vlc', args=['--intf', 'dummy'])"
    },
    'close_application': {
        'description': 'Close application by name or PID. Use for application cleanup.',
        'example': "close_application(app_name='firefox')"
    },
    'is_application_running': {
        'description': 'Check if application is currently running. Use for application state verification.',
        'example': "is_application_running(app_name='chrome')"
    }
}
