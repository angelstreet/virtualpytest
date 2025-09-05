"""
Verification Controller Command Descriptions  
Covers: Image, Text, ADB, Appium, Video, Audio verifications
"""

VERIFICATION_DESCRIPTIONS = {
    # Image Verification Commands
    'waitForImageToAppear': {
        'description': 'Wait for specific image/icon to appear on screen. Use for visual UI state confirmations.',
        'example': "waitForImageToAppear(image_path='play_button.png', timeout=10)"
    },
    'waitForImageToDisappear': {
        'description': 'Wait for image to disappear from screen. Use to verify loading screens or popups are gone.',
        'example': "waitForImageToDisappear(image_path='loading.png', timeout=15)"
    },
    'verify_image_match': {
        'description': 'Check if reference image matches current screen. Use for exact visual verification.',
        'example': "verify_image_match(reference_path='expected_screen.png', threshold=0.8)"
    },
    'find_image_on_screen': {
        'description': 'Locate image position on screen. Use to find UI elements for interaction.',
        'example': "find_image_on_screen(image_path='button.png')"
    },
    
    # Text Verification Commands (OCR)
    'waitForTextToAppear': {
        'description': 'Wait for text to appear using OCR. Use to verify messages, labels, or content display.',
        'example': "waitForTextToAppear(text='Connected', timeout=5)"
    },
    'waitForTextToDisappear': {
        'description': 'Wait for text to disappear using OCR. Use to verify error messages or notifications clear.',
        'example': "waitForTextToDisappear(text='Loading...', timeout=10)"
    },
    'verify_text_present': {
        'description': 'Check if specific text exists on screen using OCR. Use for content verification.',
        'example': "verify_text_present(text='Welcome')"
    },
    'extract_text_from_area': {
        'description': 'Extract all text from screen region using OCR. Use to read content or messages.',
        'example': "extract_text_from_area(x=100, y=200, width=300, height=100)"
    },
    'verify_text_in_area': {
        'description': 'Verify text exists in specific screen area. Use for targeted text verification.',
        'example': "verify_text_in_area(text='Error', x=0, y=0, width=400, height=100)"
    },
    
    # ADB Verification Commands
    'waitForElementToAppear': {
        'description': 'Wait for Android UI element using ADB. Fast element detection for Android apps.',
        'example': "waitForElementToAppear(search_term='Settings', timeout=10)"
    },
    'waitForElementToDisappear': {
        'description': 'Wait for Android element to disappear using ADB. Verify dialogs or screens close.',
        'example': "waitForElementToDisappear(search_term='Dialog', timeout=5)"
    },
    'verify_element_exists': {
        'description': 'Check if Android element exists using ADB. Use for UI state verification.',
        'example': "verify_element_exists(search_term='com.app:id/button')"
    },
    'get_element_properties': {
        'description': 'Get Android element properties via ADB. Use to check element state or content.',
        'example': "get_element_properties(search_term='EditText')"
    },
    'verify_app_running': {
        'description': 'Check if specific app is running using ADB. Use for app state verification.',
        'example': "verify_app_running(package_name='com.netflix.mediaclient')"
    },
    
    # Appium Verification Commands
    'waitForAppiumElementToAppear': {
        'description': 'Wait for element using Appium selectors. Cross-platform element verification.',
        'example': "waitForAppiumElementToAppear(by='id', value='submit_button', timeout=10)"
    },
    'waitForAppiumElementToDisappear': {
        'description': 'Wait for Appium element to disappear. Cross-platform element state verification.',
        'example': "waitForAppiumElementToDisappear(by='class', value='LoadingSpinner', timeout=15)"
    },
    'verify_appium_element_text': {
        'description': 'Verify text content of Appium element. Use for cross-platform text verification.',
        'example': "verify_appium_element_text(by='id', value='status', expected_text='Ready')"
    },
    'verify_appium_element_attribute': {
        'description': 'Verify Appium element attribute value. Use for element property verification.',
        'example': "verify_appium_element_attribute(by='id', value='checkbox', attribute='checked', expected='true')"
    },
    
    # Video Verification Commands
    'DetectMotion': {
        'description': 'Detect video motion/playback. Use to verify video is playing and not frozen or black.',
        'example': "DetectMotion(duration=3.0, threshold=5.0)"
    },
    'WaitForVideoToAppear': {
        'description': 'Wait for video content to start playing. Use after channel changes or video launches.',
        'example': "WaitForVideoToAppear(motion_threshold=5.0, timeout=10)"
    },
    'WaitForVideoToDisappear': {
        'description': 'Wait for video to stop playing. Use to verify video ends or switches to other content.',
        'example': "WaitForVideoToDisappear(motion_threshold=5.0, timeout=10)"
    },
    'DetectBlackscreen': {
        'description': 'Detect if screen is mostly black. Use to verify video issues or channel problems.',
        'example': "DetectBlackscreen(threshold=10)"
    },
    'DetectFreeze': {
        'description': 'Detect if video is frozen (identical frames). Use to verify video playback quality.',
        'example': "DetectFreeze(duration=3.0, threshold=1.0)"
    },
    'DetectSubtitles': {
        'description': 'Detect subtitle text on screen. Use to verify subtitle functionality.',
        'example': "DetectSubtitles(extract_text=True)"
    },
    'WaitForVideoChange': {
        'description': 'Wait for video content to change. Use to verify channel zapping or content switching.',
        'example': "WaitForVideoChange(timeout=10, threshold=10.0)"
    },
    'VerifyColorPresent': {
        'description': 'Verify specific color exists on screen. Use for visual state or content verification.',
        'example': "VerifyColorPresent(color='red', tolerance=10.0)"
    },
    'DetectMacroblocks': {
        'description': 'Detect video compression artifacts. Use to verify video quality issues.',
        'example': "DetectMacroblocks()"
    },
    'AnalyzeImageWithAI': {
        'description': 'Analyze screen content using AI vision. Use for complex visual verification.',
        'example': "AnalyzeImageWithAI(query='Is the video playing?')"
    },
    
    # Audio Verification Commands
    'DetectAudioSpeech': {
        'description': 'Detect speech in audio stream. Use to verify audio is playing and contains speech.',
        'example': "DetectAudioSpeech(duration=5.0)"
    },
    'DetectAudioPresence': {
        'description': 'Detect any audio signal presence. Use to verify audio output exists.',
        'example': "DetectAudioPresence(duration=3.0, threshold=0.1)"
    },
    'AnalyzeAudioMenu': {
        'description': 'Analyze audio/subtitle menu options. Use to verify language menu functionality.',
        'example': "AnalyzeAudioMenu()"
    },
    'DetectAudioLanguage': {
        'description': 'Detect spoken language in audio. Use to verify correct audio track selection.',
        'example': "DetectAudioLanguage(duration=10.0)"
    },
    'VerifyAudioQuality': {
        'description': 'Analyze audio quality metrics. Use to verify audio clarity and levels.',
        'example': "VerifyAudioQuality(duration=5.0)"
    },
    'WaitForAudioToStart': {
        'description': 'Wait for audio playback to begin. Use after starting content or changing channels.',
        'example': "WaitForAudioToStart(timeout=10.0, threshold=0.1)"
    },
    'WaitForAudioToStop': {
        'description': 'Wait for audio playback to end. Use to verify content stops or mutes.',
        'example': "WaitForAudioToStop(timeout=5.0, threshold=0.1)"
    },
    
    # Zapping/Channel Verification Commands
    'DetectZapping': {
        'description': 'Detect channel zapping sequence (blackscreen + content change). Use to verify channel changes.',
        'example': "DetectZapping(folder_path='/captures', key_release_timestamp=1234567890)"
    },
    'DetectFreezeZapping': {
        'description': 'Detect freeze-based channel zapping. Use for devices that freeze instead of blackscreen.',
        'example': "DetectFreezeZapping(folder_path='/captures', key_release_timestamp=1234567890)"
    },
    'VerifyChannelChange': {
        'description': 'Verify successful channel change with content analysis. Use for comprehensive zapping verification.',
        'example': "VerifyChannelChange(expected_channel='CNN')"
    },
    
    # Performance Verification Commands
    'VerifyResponseTime': {
        'description': 'Measure and verify system response time. Use to check performance requirements.',
        'example': "VerifyResponseTime(action='channel_change', max_time=3.0)"
    },
    'VerifyMemoryUsage': {
        'description': 'Check system memory usage levels. Use to verify resource consumption.',
        'example': "VerifyMemoryUsage(max_percentage=80.0)"
    },
    'VerifyNetworkConnectivity': {
        'description': 'Verify network connection status. Use to check internet connectivity.',
        'example': "VerifyNetworkConnectivity()"
    },
    
    # State Verification Commands
    'VerifyScreenState': {
        'description': 'Verify screen is in expected state (loading, ready, error). Use for UI state verification.',
        'example': "VerifyScreenState(expected_state='ready', timeout=5.0)"
    },
    'VerifySystemReady': {
        'description': 'Verify system is ready for interaction. Use before starting test sequences.',
        'example': "VerifySystemReady(timeout=30.0)"
    },
    'VerifyAppState': {
        'description': 'Verify application is in expected state. Use for app lifecycle verification.',
        'example': "VerifyAppState(app_package='com.netflix.mediaclient', expected_state='foreground')"
    }
}
