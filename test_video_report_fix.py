#!/usr/bin/env python3
"""
Test script to verify video capture error handling and report generation fixes.
This script simulates the conditions where video capture fails but report should still be generated.
"""

import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_video_thumbnail_html():
    """Test the video thumbnail HTML generation with None/empty values"""
    from shared.lib.utils.report_formatting import get_video_thumbnail_html
    
    print("Testing video thumbnail HTML generation...")
    
    # Test with None
    result_none = get_video_thumbnail_html(None, "Test Video")
    print(f"With None: {result_none}")
    assert "No video available" in result_none
    
    # Test with empty string
    result_empty = get_video_thumbnail_html("", "Test Video")
    print(f"With empty string: {result_empty}")
    assert "No video available" in result_empty
    
    # Test with valid URL
    result_valid = get_video_thumbnail_html("https://example.com/video.m3u8", "Test Video")
    print(f"With valid URL: {result_valid[:100]}...")
    assert "video-thumbnail" in result_valid
    
    print("✅ Video thumbnail HTML generation tests passed!")


def test_report_generation():
    """Test report generation with missing video URL"""
    from shared.lib.utils.report_generation import generate_validation_report
    
    print("\nTesting report generation with missing video...")
    
    # Test data without video URL
    report_data = {
        'script_name': 'test_validation',
        'device_info': {'device_name': 'test_device', 'device_model': 'test_model'},
        'host_info': {'host_name': 'test_host'},
        'execution_time': 5000,
        'success': True,
        'step_results': [],
        'screenshots': {},
        'error_msg': '',
        'execution_summary': 'Test execution completed successfully',
        'test_video_url': None  # This should not break report generation
    }
    
    html_content = generate_validation_report(report_data)
    
    print(f"Generated HTML length: {len(html_content)} characters")
    assert len(html_content) > 1000  # Should generate substantial HTML
    assert "test_validation" in html_content
    assert "No video available" in html_content  # Should show placeholder
    
    print("✅ Report generation with missing video tests passed!")


def main():
    """Run all tests"""
    print("🧪 Testing video capture error handling and report generation fixes...\n")
    
    try:
        test_video_thumbnail_html()
        test_report_generation()
        
        print("\n🎉 All tests passed! The fixes are working correctly.")
        print("Reports will now be generated successfully even when video capture fails.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
