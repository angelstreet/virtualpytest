"""
Web Controller Command Descriptions
Covers: Playwright web automation commands
"""

WEB_DESCRIPTIONS = {
    # Browser Management Commands
    'open_browser': {
        'description': 'Launch browser instance. Use to start web automation or testing sessions.',
        'example': "open_browser(browser_type='chromium')"
    },
    'close_browser': {
        'description': 'Close browser instance. Use to end web sessions and free resources.',
        'example': "close_browser()"
    },
    'connect_browser': {
        'description': 'Connect to existing browser debug session. Use for debugging or session recovery.',
        'example': "connect_browser(debug_port=9222)"
    },
    'new_page': {
        'description': 'Create new browser tab/page. Use for multi-page testing or parallel operations.',
        'example': "new_page()"
    },
    'close_page': {
        'description': 'Close specific browser tab/page. Use for cleanup or resource management.',
        'example': "close_page(page_id='tab1')"
    },
    
    # Navigation Commands
    'navigate_to_url': {
        'description': 'Navigate browser to specific URL. Use to open web pages or web applications.',
        'example': "navigate_to_url(url='https://example.com')"
    },
    'go_back': {
        'description': 'Navigate back in browser history. Use to return to previous page.',
        'example': "go_back()"
    },
    'go_forward': {
        'description': 'Navigate forward in browser history. Use to move forward after going back.',
        'example': "go_forward()"
    },
    'reload_page': {
        'description': 'Refresh current page. Use to reload content or recover from errors.',
        'example': "reload_page()"
    },
    'get_current_url': {
        'description': 'Get current page URL. Use to verify navigation or page state.',
        'example': "get_current_url()"
    },
    
    # Element Interaction Commands
    'click_element': {
        'description': 'Click web element by selector. Use for buttons, links, or interactive web elements.',
        'example': "click_element(selector='#submit-button')"
    },
    'double_click_element': {
        'description': 'Double-click web element. Use for elements requiring double-click activation.',
        'example': "double_click_element(selector='.file-item')"
    },
    'right_click_element': {
        'description': 'Right-click web element for context menu. Use to access context menus.',
        'example': "right_click_element(selector='.context-target')"
    },
    'hover_element': {
        'description': 'Hover mouse over web element. Use to trigger hover effects or tooltips.',
        'example': "hover_element(selector='.hover-menu')"
    },
    'focus_element': {
        'description': 'Set focus on web element. Use to activate input fields or interactive elements.',
        'example': "focus_element(selector='#username')"
    },
    
    # Form Input Commands
    'fill_input': {
        'description': 'Fill text input field. Use for forms, search boxes, or text entry.',
        'example': "fill_input(selector='#username', text='user123')"
    },
    'clear_input': {
        'description': 'Clear text from input field. Use to reset form fields.',
        'example': "clear_input(selector='#search-box')"
    },
    'type_text': {
        'description': 'Type text character by character. Use for realistic typing simulation.',
        'example': "type_text(selector='#editor', text='Hello World', delay=100)"
    },
    'press_key': {
        'description': 'Press keyboard key in focused element. Use for keyboard shortcuts or special keys.',
        'example': "press_key(key='Enter') or press_key(key='Ctrl+A')"
    },
    'upload_file': {
        'description': 'Upload file through file input. Use for file upload forms.',
        'example': "upload_file(selector='input[type=file]', file_path='/path/to/file.txt')"
    },
    
    # Form Controls Commands
    'select_option': {
        'description': 'Select option from dropdown/select element. Use for form dropdowns.',
        'example': "select_option(selector='#country', value='US')"
    },
    'check_checkbox': {
        'description': 'Check checkbox element. Use to enable checkbox options.',
        'example': "check_checkbox(selector='#agree-terms')"
    },
    'uncheck_checkbox': {
        'description': 'Uncheck checkbox element. Use to disable checkbox options.',
        'example': "uncheck_checkbox(selector='#newsletter')"
    },
    'select_radio': {
        'description': 'Select radio button option. Use for radio button groups.',
        'example': "select_radio(selector='input[name=payment][value=credit]')"
    },
    'set_slider_value': {
        'description': 'Set value of range slider. Use for slider controls.',
        'example': "set_slider_value(selector='#volume', value=75)"
    },
    
    # Element Waiting Commands
    'wait_for_element': {
        'description': 'Wait for web element to appear. Use to ensure page content loads before interaction.',
        'example': "wait_for_element(selector='.content', timeout=10)"
    },
    'wait_for_element_visible': {
        'description': 'Wait for element to become visible. Use for dynamic content that appears.',
        'example': "wait_for_element_visible(selector='#modal', timeout=5)"
    },
    'wait_for_element_hidden': {
        'description': 'Wait for element to become hidden. Use to verify elements disappear.',
        'example': "wait_for_element_hidden(selector='.loading', timeout=10)"
    },
    'wait_for_text': {
        'description': 'Wait for specific text to appear on page. Use for content verification.',
        'example': "wait_for_text(text='Success', timeout=5)"
    },
    'wait_for_url': {
        'description': 'Wait for URL to match pattern. Use to verify navigation completion.',
        'example': "wait_for_url(pattern='*/dashboard', timeout=10)"
    },
    
    # Page Interaction Commands
    'scroll_page': {
        'description': 'Scroll web page up or down. Use to access content below the fold.',
        'example': "scroll_page(direction='down', pixels=500)"
    },
    'scroll_to_element': {
        'description': 'Scroll page to bring element into view. Use to ensure element visibility.',
        'example': "scroll_to_element(selector='#footer')"
    },
    'scroll_to_top': {
        'description': 'Scroll to top of page. Use to return to page beginning.',
        'example': "scroll_to_top()"
    },
    'scroll_to_bottom': {
        'description': 'Scroll to bottom of page. Use to reach page end or load more content.',
        'example': "scroll_to_bottom()"
    },
    'zoom_page': {
        'description': 'Change page zoom level. Use for accessibility or content scaling.',
        'example': "zoom_page(zoom_factor=1.5)"
    },
    
    # Element Information Commands
    'get_element_text': {
        'description': 'Get text content from web element. Use to read labels, messages, or content.',
        'example': "get_element_text(selector='#status')"
    },
    'get_element_attribute': {
        'description': 'Get attribute value from web element. Use to check element properties.',
        'example': "get_element_attribute(selector='#link', attribute='href')"
    },
    'get_element_property': {
        'description': 'Get JavaScript property from element. Use for dynamic property values.',
        'example': "get_element_property(selector='#input', property='value')"
    },
    'is_element_visible': {
        'description': 'Check if element is visible on page. Use for UI state verification.',
        'example': "is_element_visible(selector='#error-message')"
    },
    'is_element_enabled': {
        'description': 'Check if element is enabled/interactive. Use to verify element accessibility.',
        'example': "is_element_enabled(selector='#submit-button')"
    },
    'is_element_checked': {
        'description': 'Check if checkbox/radio is selected. Use for form state verification.',
        'example': "is_element_checked(selector='#agree-checkbox')"
    },
    
    # Page Information Commands
    'get_page_title': {
        'description': 'Get current page title. Use for page verification or navigation confirmation.',
        'example': "get_page_title()"
    },
    'get_page_source': {
        'description': 'Get complete page HTML source. Use for debugging or content analysis.',
        'example': "get_page_source()"
    },
    'get_page_cookies': {
        'description': 'Get all page cookies. Use for session or authentication verification.',
        'example': "get_page_cookies()"
    },
    'set_page_cookie': {
        'description': 'Set cookie for current page. Use for authentication or state setup.',
        'example': "set_page_cookie(name='session', value='abc123')"
    },
    'delete_page_cookies': {
        'description': 'Delete all page cookies. Use for cleanup or session reset.',
        'example': "delete_page_cookies()"
    },
    
    # JavaScript Execution Commands
    'execute_javascript': {
        'description': 'Execute JavaScript code on page. Use for custom interactions or data extraction.',
        'example': "execute_javascript(script='return document.title')"
    },
    'execute_async_javascript': {
        'description': 'Execute asynchronous JavaScript. Use for operations requiring callbacks.',
        'example': "execute_async_javascript(script='setTimeout(arguments[0], 1000)')"
    },
    'inject_javascript': {
        'description': 'Inject JavaScript into page context. Use to add custom functionality.',
        'example': "inject_javascript(script='window.testHelper = function() { return true; }')"
    },
    
    # Screenshot and Recording Commands
    'take_screenshot': {
        'description': 'Capture screenshot of current page. Use for visual verification or debugging.',
        'example': "take_screenshot(filename='page_screenshot.png')"
    },
    'take_element_screenshot': {
        'description': 'Capture screenshot of specific element. Use for focused visual verification.',
        'example': "take_element_screenshot(selector='#main-content', filename='element.png')"
    },
    'start_video_recording': {
        'description': 'Start recording page interactions. Use for test documentation or debugging.',
        'example': "start_video_recording(filename='test_recording.webm')"
    },
    'stop_video_recording': {
        'description': 'Stop video recording and save file. Use to end recording session.',
        'example': "stop_video_recording()"
    },
    
    # Network and Performance Commands
    'set_network_conditions': {
        'description': 'Simulate network conditions (slow, fast, offline). Use for performance testing.',
        'example': "set_network_conditions(condition='slow_3g')"
    },
    'block_urls': {
        'description': 'Block specific URLs from loading. Use to test error handling or performance.',
        'example': "block_urls(patterns=['*.ads.com', '*/analytics/*'])"
    },
    'get_network_logs': {
        'description': 'Get network request logs. Use for debugging or performance analysis.',
        'example': "get_network_logs()"
    },
    'measure_page_load_time': {
        'description': 'Measure page loading performance. Use for performance verification.',
        'example': "measure_page_load_time(url='https://example.com')"
    },
    
    # Browser State Commands
    'set_viewport_size': {
        'description': 'Set browser window size. Use for responsive testing or specific resolutions.',
        'example': "set_viewport_size(width=1920, height=1080)"
    },
    'set_user_agent': {
        'description': 'Set browser user agent string. Use for device simulation or compatibility testing.',
        'example': "set_user_agent(user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)')"
    },
    'set_geolocation': {
        'description': 'Set browser geolocation. Use for location-based feature testing.',
        'example': "set_geolocation(latitude=40.7128, longitude=-74.0060)"
    },
    'set_timezone': {
        'description': 'Set browser timezone. Use for time-sensitive feature testing.',
        'example': "set_timezone(timezone='America/New_York')"
    }
}
