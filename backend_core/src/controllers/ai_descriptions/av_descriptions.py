"""
AV Controller Command Descriptions
Covers: HDMI Stream, Camera Stream, VNC Stream controllers
"""

AV_DESCRIPTIONS = {
    # Screenshot Commands
    'take_screenshot': {
        'description': 'Capture current screen image. Use for visual verification or debugging.',
        'example': "take_screenshot(filename='current_state.png')"
    },
    'capture_screenshot': {
        'description': 'Capture screen with automatic naming. Use for automated screenshot collection.',
        'example': "capture_screenshot()"
    },
    'take_screenshot_area': {
        'description': 'Capture specific screen region. Use to focus on particular UI areas.',
        'example': "take_screenshot_area(x=100, y=200, width=300, height=200)"
    },
    
    # Video Recording Commands
    'take_video': {
        'description': 'Record video of screen activity. Use to capture test execution or analyze behavior.',
        'example': "take_video(duration=30.0, filename='test_recording.mp4')"
    },
    'start_recording': {
        'description': 'Start continuous video recording. Use for long-term monitoring or full test capture.',
        'example': "start_recording(filename='full_test.mp4')"
    },
    'stop_recording': {
        'description': 'Stop ongoing video recording. Use to end recording and save file.',
        'example': "stop_recording()"
    },
    'record_for_duration': {
        'description': 'Record video for specific time period. Use for timed capture of events.',
        'example': "record_for_duration(duration=60.0)"
    },
    
    # Stream Management Commands
    'start_stream': {
        'description': 'Start video stream capture. Use to begin continuous monitoring of screen content.',
        'example': "start_stream()"
    },
    'stop_stream': {
        'description': 'Stop video stream capture. Use to end monitoring and save resources.',
        'example': "stop_stream()"
    },
    'restart_stream': {
        'description': 'Restart video stream capture. Use to recover from stream issues.',
        'example': "restart_stream()"
    },
    'get_stream_status': {
        'description': 'Check if video stream is active. Use to verify capture system is working.',
        'example': "get_stream_status()"
    },
    'get_stream_info': {
        'description': 'Get detailed stream information (resolution, fps, format). Use for stream diagnostics.',
        'example': "get_stream_info()"
    },
    
    # Stream Configuration Commands
    'set_stream_resolution': {
        'description': 'Change stream capture resolution. Use to optimize quality vs performance.',
        'example': "set_stream_resolution(width=1920, height=1080)"
    },
    'set_stream_fps': {
        'description': 'Change stream frame rate. Use to adjust capture performance.',
        'example': "set_stream_fps(fps=30)"
    },
    'set_stream_quality': {
        'description': 'Change stream quality settings. Use to balance quality and bandwidth.',
        'example': "set_stream_quality(quality='high')"
    },
    
    # HDMI Specific Commands
    'detect_hdmi_signal': {
        'description': 'Check if HDMI signal is present. Use to verify device connection.',
        'example': "detect_hdmi_signal()"
    },
    'get_hdmi_resolution': {
        'description': 'Get current HDMI input resolution. Use to verify signal quality.',
        'example': "get_hdmi_resolution()"
    },
    'wait_for_hdmi_signal': {
        'description': 'Wait for HDMI signal to stabilize. Use after device power-on or connection.',
        'example': "wait_for_hdmi_signal(timeout=30.0)"
    },
    
    # Camera Specific Commands
    'set_camera_exposure': {
        'description': 'Adjust camera exposure settings. Use to optimize image quality.',
        'example': "set_camera_exposure(exposure=0.5)"
    },
    'set_camera_focus': {
        'description': 'Adjust camera focus settings. Use for clear image capture.',
        'example': "set_camera_focus(focus_mode='auto')"
    },
    'calibrate_camera': {
        'description': 'Calibrate camera settings for optimal capture. Use for setup or troubleshooting.',
        'example': "calibrate_camera()"
    },
    
    # VNC Specific Commands
    'connect_vnc': {
        'description': 'Connect to VNC server. Use to establish remote desktop connection.',
        'example': "connect_vnc(host='192.168.1.100', port=5900)"
    },
    'disconnect_vnc': {
        'description': 'Disconnect from VNC server. Use to end remote desktop session.',
        'example': "disconnect_vnc()"
    },
    'get_vnc_status': {
        'description': 'Check VNC connection status. Use to verify remote connection.',
        'example': "get_vnc_status()"
    },
    
    # Image Processing Commands
    'enhance_image': {
        'description': 'Apply image enhancement filters. Use to improve screenshot quality for analysis.',
        'example': "enhance_image(image_path='screenshot.png', enhancement='sharpen')"
    },
    'crop_image': {
        'description': 'Crop image to specific region. Use to focus analysis on particular areas.',
        'example': "crop_image(image_path='full.png', x=100, y=200, width=300, height=200)"
    },
    'resize_image': {
        'description': 'Resize image to different dimensions. Use for standardizing image sizes.',
        'example': "resize_image(image_path='large.png', width=800, height=600)"
    },
    'convert_image_format': {
        'description': 'Convert image to different format. Use for compatibility or size optimization.',
        'example': "convert_image_format(image_path='image.png', format='jpg')"
    },
    
    # Analysis Commands
    'analyze_image_brightness': {
        'description': 'Analyze image brightness levels. Use to detect blackscreen or exposure issues.',
        'example': "analyze_image_brightness(image_path='screenshot.png')"
    },
    'analyze_image_colors': {
        'description': 'Analyze dominant colors in image. Use for content or state verification.',
        'example': "analyze_image_colors(image_path='screenshot.png')"
    },
    'compare_images': {
        'description': 'Compare two images for differences. Use to detect changes or verify states.',
        'example': "compare_images(image1='before.png', image2='after.png')"
    },
    'detect_image_motion': {
        'description': 'Detect motion between consecutive images. Use for video playback verification.',
        'example': "detect_image_motion(image1='frame1.png', image2='frame2.png')"
    },
    
    # File Management Commands
    'list_captures': {
        'description': 'List all captured files (images/videos). Use to inventory captured content.',
        'example': "list_captures(file_type='images')"
    },
    'delete_capture': {
        'description': 'Delete specific captured file. Use for cleanup or storage management.',
        'example': "delete_capture(filename='old_screenshot.png')"
    },
    'cleanup_old_captures': {
        'description': 'Delete old captured files based on age. Use for automated cleanup.',
        'example': "cleanup_old_captures(days_old=7)"
    },
    'get_capture_info': {
        'description': 'Get information about captured file. Use for file verification or metadata.',
        'example': "get_capture_info(filename='screenshot.png')"
    },
    
    # System Commands
    'get_av_system_status': {
        'description': 'Get overall AV system status. Use for system health verification.',
        'example': "get_av_system_status()"
    },
    'restart_av_system': {
        'description': 'Restart AV capture system. Use to recover from system issues.',
        'example': "restart_av_system()"
    },
    'calibrate_av_system': {
        'description': 'Calibrate AV system settings. Use for optimal capture configuration.',
        'example': "calibrate_av_system()"
    },
    'test_av_connectivity': {
        'description': 'Test AV system connectivity and functionality. Use for diagnostics.',
        'example': "test_av_connectivity()"
    }
}
