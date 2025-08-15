#!/usr/bin/env python3
"""
Debug Report Generation Script

This script simulates the exact report generation process that's failing
during script execution, allowing us to see the exact error without
the complexity of the full script execution pipeline.
"""

import os
import sys
import traceback
from datetime import datetime

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir  # Assuming we're running from project root

if project_root not in sys.path:
    sys.path.insert(0, project_root)

def simulate_report_generation():
    """
    Simulate the exact report generation process that's failing
    """
    try:
        print("="*60)
        print("🔍 DEBUG REPORT GENERATION SIMULATION")
        print("="*60)
        
        # Step 1: Import required modules
        print("📦 Step 1: Importing modules...")
        try:
            from shared.lib.utils.report_generation import generate_and_upload_script_report
            print("✅ Successfully imported generate_and_upload_script_report")
        except Exception as e:
            print(f"❌ Failed to import report generation: {e}")
            traceback.print_exc()
            return False
        
        # Step 2: Prepare test data (similar to what script framework sends)
        print("\n📋 Step 2: Preparing test data...")
        
        # Simulate script execution data
        script_name = "goto.py"
        device_info = {
            'device_name': 'sunri-pi1_Host',
            'device_model': 'host_vnc', 
            'device_id': 'host'
        }
        host_info = {
            'host_name': 'sunri-pi1'
        }
        execution_time = 50000  # 50 seconds
        success = True
        userinterface_name = "perseus_360_web"
        
        # Simulate step results
        step_results = [{
            'step_number': 1,
            'success': True,
            'screenshot_path': None,
            'message': f'Navigation step: goto home',
            'execution_time_ms': 25000,
            'start_time': '16:50:00',
            'end_time': '16:50:25',
            'from_node': 'Entry',
            'to_node': 'home',
            'actions': [{
                'command': 'navigate',
                'params': {'target': 'home'},
                'label': 'Navigate to home'
            }],
            'verifications': [],
            'verification_results': []
        }]
        
        # Simulate screenshot paths (use some actual paths from recent captures)
        print("🔍 Looking for recent screenshot files...")
        capture_dirs = [
            '/var/www/html/stream/capture3/captures',
            '/var/www/html/stream/capture2/captures', 
            '/var/www/html/stream/capture1/captures'
        ]
        
        screenshot_paths = []
        for capture_dir in capture_dirs:
            if os.path.exists(capture_dir):
                print(f"📂 Found capture directory: {capture_dir}")
                # Get recent .jpg files
                import glob
                jpg_files = glob.glob(os.path.join(capture_dir, "*.jpg"))
                if jpg_files:
                    # Sort by modification time and take recent ones
                    jpg_files.sort(key=os.path.getmtime, reverse=True)
                    screenshot_paths.extend(jpg_files[:7])  # Take 7 recent files
                    print(f"📸 Found {len(jpg_files)} screenshots, using {len(screenshot_paths[:7])}")
                    break
        
        if not screenshot_paths:
            print("⚠️ No screenshots found, creating dummy paths for testing...")
            screenshot_paths = [
                "/tmp/dummy_screenshot1.jpg",
                "/tmp/dummy_screenshot2.jpg", 
                "/tmp/dummy_screenshot3.jpg"
            ]
        
        print(f"📸 Using {len(screenshot_paths)} screenshot paths")
        for i, path in enumerate(screenshot_paths[:3]):
            print(f"   {i+1}. {path}")
        if len(screenshot_paths) > 3:
            print(f"   ... and {len(screenshot_paths)-3} more")
        
        # Step 3: Execute report generation with detailed logging
        print(f"\n🚀 Step 3: Executing report generation...")
        print(f"📄 Script: {script_name}")
        print(f"🖥️ Device: {device_info['device_name']} ({device_info['device_model']})")
        print(f"📸 Screenshots: {len(screenshot_paths)} files")
        print(f"📊 Step results: {len(step_results)} steps")
        
        # Call the actual function that's failing
        result = generate_and_upload_script_report(
            script_name=script_name,
            device_info=device_info,
            host_info=host_info,
            execution_time=execution_time,
            success=success,
            step_results=step_results,
            screenshot_paths=screenshot_paths,
            error_message="",
            userinterface_name=userinterface_name,
            stdout="",
            stderr="", 
            exit_code=0,
            parameters="",
            execution_summary="",
            test_video_url=""
        )
        
        # Step 4: Analyze results
        print(f"\n📊 Step 4: Analyzing results...")
        print(f"✅ Report generation completed successfully!")
        print(f"🔗 Result: {result}")
        
        if result.get('success'):
            print(f"📄 Report URL: {result.get('report_url')}")
            print(f"📁 Report Path: {result.get('report_path')}")
        else:
            print(f"❌ Report generation failed: {result}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ EXCEPTION DURING SIMULATION:")
        print(f"Error: {str(e)}")
        print(f"Type: {type(e).__name__}")
        print("\n📋 Full Traceback:")
        traceback.print_exc()
        return False

def test_individual_components():
    """
    Test individual components that might be failing
    """
    print("\n" + "="*60)
    print("🧪 TESTING INDIVIDUAL COMPONENTS")
    print("="*60)
    
    # Test 1: Screenshot upload
    print("\n📸 Test 1: Screenshot upload function...")
    try:
        from shared.lib.utils.cloudflare_utils import upload_validation_screenshots
        print("✅ Successfully imported upload_validation_screenshots")
        
        # Test with dummy data
        test_paths = ["/tmp/test1.jpg", "/tmp/test2.jpg"]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        print("📤 Testing screenshot upload with dummy data...")
        print("ℹ️ This will fail (no actual files) but should show us where it breaks...")
        
        result = upload_validation_screenshots(
            screenshot_paths=test_paths,
            device_model="host_vnc",
            script_name="goto",
            timestamp=timestamp
        )
        print(f"📊 Upload result: {result}")
        
    except Exception as e:
        print(f"❌ Screenshot upload test failed: {e}")
        traceback.print_exc()
    
    # Test 2: HTML generation
    print("\n📄 Test 2: HTML generation...")
    try:
        from shared.lib.utils.report_generation import generate_validation_report
        print("✅ Successfully imported generate_validation_report")
        
        # Test with minimal data
        test_data = {
            'script_name': 'test.py',
            'device_info': {'device_name': 'test', 'device_model': 'test'},
            'host_info': {'host_name': 'test'},
            'execution_time': 1000,
            'success': True,
            'step_results': [],
            'screenshots': {'initial': None, 'steps': [], 'final': None},
            'error_msg': '',
            'timestamp': '20250815000000',
            'userinterface_name': 'test',
            'total_steps': 1,
            'passed_steps': 1,
            'failed_steps': 0,
            'total_verifications': 0,
            'passed_verifications': 0,
            'failed_verifications': 0,
            'execution_summary': '',
            'test_video_url': ''
        }
        
        html_content = generate_validation_report(test_data)
        print(f"✅ HTML generation successful, content length: {len(html_content)}")
        
    except Exception as e:
        print(f"❌ HTML generation test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Starting Report Generation Debug Session...")
    
    # Run main simulation
    success = simulate_report_generation()
    
    # If main simulation fails, test components individually
    if not success:
        test_individual_components()
    
    print("\n" + "="*60)
    print("🏁 Debug session completed")
    print("="*60)
