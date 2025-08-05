#!/usr/bin/env python3
"""
Test Single Blackscreen Image Detection

This script tests the single blackscreen image case for fast zapping (under 2s).
"""

import sys
import os

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_single_blackscreen_case():
    """Test the single blackscreen image detection logic."""
    
    # Mock data simulating one blackscreen image in sequence (true single case)
    # Only ONE blackscreen image, no clear sequence end
    mock_blackscreen_results = [
        {'success': True, 'is_blackscreen': False, 'filename': 'capture_20250805132126.jpg'},  # Normal
        {'success': True, 'is_blackscreen': True, 'filename': 'capture_20250805132127.jpg'},   # Blackscreen (ONLY ONE)
        {'success': True, 'is_blackscreen': False, 'filename': 'capture_20250805132128.jpg'},  # Normal but makes sequence
    ]
    
    # Let's create a TRUE single case - only one blackscreen, rest are normal or failed
    mock_single_case_results = [
        {'success': True, 'is_blackscreen': False, 'filename': 'capture_20250805132126.jpg'},  # Normal
        {'success': True, 'is_blackscreen': True, 'filename': 'capture_20250805132127.jpg'},   # Blackscreen (ONLY ONE)
        {'success': False, 'is_blackscreen': False, 'filename': 'capture_20250805132128.jpg'}, # Failed - no clear end
        {'success': False, 'is_blackscreen': False, 'filename': 'capture_20250805132129.jpg'}, # Failed
    ]
    
    mock_image_data = [
        {'timestamp': 1754392886.0, 'filename': 'capture_20250805132126.jpg'},  # t=0s (action completion)
        {'timestamp': 1754392887.0, 'filename': 'capture_20250805132127.jpg'},  # t=1s (blackscreen)
        {'timestamp': 1754392888.0, 'filename': 'capture_20250805132128.jpg'},  # t=2s
    ]
    
    # Import the video content helpers
    from backend_core.src.controllers.verification.video_content_helpers import VideoContentHelpers
    
    # Create a mock instance
    class MockAVController:
        def __init__(self):
            self.device_name = "test_device"
    
    helpers = VideoContentHelpers(MockAVController(), "TestDevice")
    
    # Test the TRUE single case
    print("Testing TRUE single blackscreen case...")
    sequence = helpers._find_blackscreen_sequence(mock_single_case_results)
    
    print("🧪 Testing Single Blackscreen Image Case")
    print("=" * 50)
    print(f"Blackscreen start index: {sequence['blackscreen_start_index']}")
    print(f"Blackscreen end index: {sequence['blackscreen_end_index']}")
    print(f"Zapping detected: {sequence['zapping_detected']}")
    print(f"Single image case: {sequence.get('single_image_case', False)}")
    
    # Test duration calculation logic
    if sequence['zapping_detected']:
        first_image_time = mock_image_data[0]['timestamp']
        
        if sequence.get('single_image_case', False):
            # Single blackscreen image case
            blackscreen_duration = 1.0  # Assumed 1s
            blackscreen_start_time = mock_image_data[sequence['blackscreen_start_index']]['timestamp']
            time_to_blackscreen = blackscreen_start_time - first_image_time
            zapping_duration = time_to_blackscreen + blackscreen_duration
            
            print(f"\n📊 Single Image Case Results:")
            print(f"   • Time to blackscreen: {time_to_blackscreen:.1f}s")
            print(f"   • Blackscreen duration: {blackscreen_duration:.1f}s (assumed)")
            print(f"   • Total zapping duration: {zapping_duration:.1f}s")
            
            # Verify expected results
            assert sequence['single_image_case'] == True, "Should detect single image case"
            assert blackscreen_duration == 1.0, "Should assume 1s blackscreen duration"
            assert zapping_duration == 2.0, f"Expected 2.0s zapping duration, got {zapping_duration}s"
            
            print(f"✅ Single blackscreen image case working correctly!")
        else:
            print(f"❌ Failed to detect single image case")
            return False
    else:
        print(f"❌ Failed to detect zapping")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = test_single_blackscreen_case()
        if success:
            print(f"\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print(f"\n❌ Tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1)