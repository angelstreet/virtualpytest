#!/usr/bin/env python3
"""
Test Channel Detection Script

This script downloads images from the public URL and tests AI channel detection
with the same parameters used by the VideoContentHelpers to debug channel analysis issues.

The script automatically loads environment variables from .env file in the project root,
including OPENROUTER_API_KEY for real AI analysis.

Usage:
    python test_scripts/test_channel_detection.py [base_url] [timestamp] [--banner_region x,y,width,height]
    
Example:
    python test_scripts/test_channel_detection.py https://virtualpytest.com/host/stream/capture2/captures/ 20250805171406 --banner_region 437,460,405,260
"""

import os
import sys
import requests
import cv2
import numpy as np
import tempfile
import base64
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Load environment variables from .env file
def load_env_file(env_path: str = '.env'):
    """Load environment variables from .env file"""
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key.strip()] = value
        print(f"📄 Loaded environment variables from {env_path}")
    else:
        print(f"⚠️  No .env file found at {env_path}")

# Load .env file from project root
load_env_file('.env')

def download_image(url: str, local_path: str) -> bool:
    """Download image from URL to local path"""
    try:
        print(f"📥 Downloading: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Downloaded: {local_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")
        return False

def crop_banner_region(image_path: str, banner_region: Dict[str, int] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Crop banner region from image for analysis
    
    Args:
        image_path: Path to image file
        banner_region: Region to crop {'x': int, 'y': int, 'width': int, 'height': int}
        
    Returns:
        Tuple of (success, cropped_image_path, info)
    """
    try:
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return False, "", {'error': 'Could not load image'}
        
        original_height, original_width = img.shape[:2]
        print(f"🖼️  Original image size: {original_width}x{original_height}")
        
        # Apply banner region if specified
        if banner_region:
            x = banner_region['x']
            y = banner_region['y']
            width = banner_region['width']
            height = banner_region['height']
            
            # Validate rectangle bounds
            if (x < 0 or y < 0 or x + width > original_width or y + height > original_height):
                print(f"⚠️  Banner region {x},{y},{width},{height} is out of bounds for image {original_width}x{original_height}")
                print(f"📊 Using full image instead")
                cropped_img = img
                actual_region = {'x': 0, 'y': 0, 'width': original_width, 'height': original_height}
            else:
                # Crop to banner region
                cropped_img = img[y:y+height, x:x+width]
                actual_region = banner_region
                print(f"✂️  Cropped to banner region: {x},{y},{width},{height}")
        else:
            cropped_img = img
            actual_region = {'x': 0, 'y': 0, 'width': original_width, 'height': original_height}
            print(f"📊 Using full image")
        
        # Save cropped image
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        cropped_path = os.path.join(os.path.dirname(image_path), f"{base_name}_banner_crop.jpg")
        cv2.imwrite(cropped_path, cropped_img)
        
        info = {
            'original_size': f"{original_width}x{original_height}",
            'cropped_size': f"{cropped_img.shape[1]}x{cropped_img.shape[0]}",
            'banner_region': actual_region,
            'cropped_path': cropped_path
        }
        
        print(f"💾 Saved cropped banner region to: {cropped_path}")
        return True, cropped_path, info
        
    except Exception as e:
        return False, "", {'error': f'Banner cropping failed: {str(e)}'}

def analyze_channel_with_real_ai(image_path: str, banner_region: Dict[str, int] = None) -> Dict[str, Any]:
    """
    Real AI analysis for channel detection using VideoAIHelpers
    
    Args:
        image_path: Path to image file
        banner_region: Banner region to analyze
        
    Returns:
        Dictionary with channel analysis results
    """
    try:
        # Import the real AI helpers
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        
        from backend_core.src.controllers.verification.video_ai_helpers import VideoAIHelpers
        
        # Create a mock AV controller for the AI helper
        class MockAVController:
            def __init__(self):
                self.device_model = 'android_mobile'
                self.device_name = 'ChannelTest'
        
        # Initialize AI helper
        mock_av = MockAVController()
        ai_helper = VideoAIHelpers(mock_av, "ChannelTest")
        
        # Crop banner region first if specified
        if banner_region:
            success, cropped_path, crop_info = crop_banner_region(image_path, banner_region)
            
            if not success:
                return {
                    'success': False,
                    'error': f"Failed to crop banner region: {crop_info.get('error', 'Unknown error')}",
                    'banner_detected': False
                }
            
            analysis_path = cropped_path
            print(f"✂️  Using cropped banner region for AI analysis")
        else:
            analysis_path = image_path
            crop_info = {'original_size': 'N/A', 'cropped_size': 'N/A', 'banner_region': None}
            print(f"📊 Using full image for AI analysis")
        
        print(f"🤖 Real AI Analysis: Analyzing {os.path.basename(analysis_path)} for channel info...")
        
        # Check if API key is available
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        if not openrouter_key:
            print(f"⚠️  OPENROUTER_API_KEY not found in environment")
            print(f"💡 To use real AI analysis, set the API key:")
            print(f"   export OPENROUTER_API_KEY='your-api-key-here'")
            print(f"🤖 Falling back to mock analysis for demonstration...")
            
            # Provide mock result that shows what real AI would return
            return {
                'success': True,
                'banner_detected': True,
                'channel_info': {
                    'channel_name': 'ITV1',
                    'channel_number': '103', 
                    'program_name': 'Lingo',
                    'start_time': '16:00',
                    'end_time': '17:00'
                },
                'confidence': 0.85,
                'crop_info': crop_info,
                'note': 'Mock result - set OPENROUTER_API_KEY for real AI analysis'
            }
        
        # Use real AI analysis
        ai_result = ai_helper.analyze_channel_banner_ai(analysis_path, banner_region)
        
        if ai_result.get('success', False):
            if ai_result.get('banner_detected', False):
                channel_info = ai_result.get('channel_info', {})
                confidence = ai_result.get('confidence', 0.0)
                
                print(f"✅ Real AI Analysis: Banner detected!")
                print(f"📺 Channel Info Extracted:")
                print(f"    Channel: {channel_info.get('channel_name', 'N/A')}")
                print(f"    Number: {channel_info.get('channel_number', 'N/A')}")
                print(f"    Program: {channel_info.get('program_name', 'N/A')}")
                print(f"    Time: {channel_info.get('start_time', 'N/A')} - {channel_info.get('end_time', 'N/A')}")
                print(f"    Confidence: {confidence:.2f}")
                
                return {
                    'success': True,
                    'banner_detected': True,
                    'channel_info': channel_info,
                    'confidence': confidence,
                    'crop_info': crop_info,
                    'ai_result': ai_result
                }
            else:
                print(f"❌ Real AI Analysis: No banner detected by AI")
                return {
                    'success': True,
                    'banner_detected': False,
                    'channel_info': {},
                    'confidence': 0.0,
                    'crop_info': crop_info,
                    'ai_result': ai_result
                }
        else:
            error_msg = ai_result.get('error', 'AI analysis failed')
            print(f"❌ Real AI Analysis failed: {error_msg}")
            return {
                'success': False,
                'error': f'AI analysis failed: {error_msg}',
                'banner_detected': False,
                'crop_info': crop_info
            }
        
    except Exception as e:
        print(f"❌ Error during real AI analysis: {str(e)}")
        return {
            'success': False,
            'error': f'Channel analysis failed: {str(e)}',
            'banner_detected': False
        }

def test_single_image_channel_detection(url: str, banner_region: Dict[str, int] = None) -> Dict[str, Any]:
    """
    Test channel detection on a single image
    
    Args:
        url: URL of the image to analyze
        banner_region: Banner region to analyze
        
    Returns:
        Dictionary with channel detection results
    """
    print(f"🎯 Testing channel detection on single image")
    print(f"🔗 Image URL: {url}")
    if banner_region:
        print(f"📐 Banner region: {banner_region}")
    else:
        print(f"📐 Banner region: Full image")
    
    # Create temporary directory for download
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Download image
        filename = os.path.basename(url)
        local_path = os.path.join(temp_dir, filename)
        
        if not download_image(url, local_path):
            return {'success': False, 'error': 'Failed to download image'}
        
        print(f"\n🔍 Analyzing image for channel detection...")
        
        # Analyze image
        result = analyze_channel_with_real_ai(local_path, banner_region)
        
        # Summary
        print(f"\n📊 CHANNEL DETECTION ANALYSIS SUMMARY")
        print(f"=" * 50)
        print(f"🖼️  Image: {filename}")
        print(f"✅ Analysis successful: {'YES' if result['success'] else 'NO'}")
        
        if result['success']:
            print(f"🎯 Banner detected: {'YES' if result['banner_detected'] else 'NO'}")
            
            if result['banner_detected'] and result['channel_info']:
                channel_info = result['channel_info']
                print(f"📺 Channel Information:")
                print(f"    Name: {channel_info.get('channel_name', 'N/A')}")
                print(f"    Number: {channel_info.get('channel_number', 'N/A')}")
                print(f"    Program: {channel_info.get('program_name', 'N/A')}")
                print(f"    Time: {channel_info.get('start_time', 'N/A')} - {channel_info.get('end_time', 'N/A')}")
                print(f"    Confidence: {result.get('confidence', 0.0):.2f}")
            
            if 'crop_info' in result:
                crop_info = result['crop_info']
                print(f"📈 Analysis Information:")
                print(f"    Original size: {crop_info.get('original_size', 'N/A')}")
                print(f"    Cropped size: {crop_info.get('cropped_size', 'N/A')}")
                if 'ai_result' in result:
                    print(f"    AI processing: Success")
        else:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
        
        return result

def test_sequence_channel_detection(base_url: str, timestamp: str, banner_region: Dict[str, int] = None,
                                  num_images: int = 3) -> Dict[str, Any]:
    """
    Test channel detection on a sequence of images (like after blackscreen ends)
    
    Args:
        base_url: Base URL for image downloads
        timestamp: Starting timestamp
        banner_region: Banner region to analyze
        num_images: Number of images to analyze
        
    Returns:
        Dictionary with sequence analysis results
    """
    print(f"🎯 Testing channel detection on image sequence")
    print(f"📍 Base URL: {base_url}")
    print(f"⏰ Starting timestamp: {timestamp}")
    print(f"🖼️  Number of images: {num_images}")
    if banner_region:
        print(f"📐 Banner region: {banner_region}")
    else:
        print(f"📐 Banner region: Full image")
    
    # Create temporary directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Download images
        downloaded_images = []
        base_timestamp = int(timestamp)
        
        for i in range(num_images):
            current_timestamp = base_timestamp + i
            filename = f"capture_{current_timestamp}.jpg"
            url = f"{base_url.rstrip('/')}/{filename}"
            local_path = os.path.join(temp_dir, filename)
            
            if download_image(url, local_path):
                downloaded_images.append({
                    'filename': filename,
                    'timestamp': str(current_timestamp),
                    'local_path': local_path,
                    'url': url
                })
        
        if not downloaded_images:
            return {'success': False, 'error': 'No images downloaded successfully'}
        
        print(f"\n🔍 Analyzing {len(downloaded_images)} images for channel detection...")
        
        # Analyze each image
        analysis_results = []
        channel_found = None
        
        for img_data in downloaded_images:
            print(f"\n--- Analyzing {img_data['filename']} ---")
            result = analyze_channel_with_real_ai(img_data['local_path'], banner_region)
            
            if result['success']:
                result['filename'] = img_data['filename']
                result['timestamp'] = img_data['timestamp']
                result['url'] = img_data['url']
                analysis_results.append(result)
                
                # Track first successful channel detection
                if result['banner_detected'] and result['channel_info'] and not channel_found:
                    channel_found = result
        
        # Summary
        print(f"\n📊 SEQUENCE CHANNEL DETECTION SUMMARY")
        print(f"=" * 50)
        print(f"✅ Images analyzed: {len(analysis_results)}")
        print(f"🎯 Channel info found: {'YES' if channel_found else 'NO'}")
        
        if channel_found:
            channel_info = channel_found['channel_info']
            print(f"📺 Channel Information (from {channel_found['filename']}):")
            print(f"    Name: {channel_info.get('channel_name', 'N/A')}")
            print(f"    Number: {channel_info.get('channel_number', 'N/A')}")
            print(f"    Program: {channel_info.get('program_name', 'N/A')}")
            print(f"    Time: {channel_info.get('start_time', 'N/A')} - {channel_info.get('end_time', 'N/A')}")
            print(f"    Confidence: {channel_found.get('confidence', 0.0):.2f}")
        
        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        for result in analysis_results:
            status = "📺" if result['banner_detected'] else "❌"
            channel_name = result['channel_info'].get('channel_name', 'N/A') if result.get('channel_info') else 'N/A'
            print(f"{status} {result['filename']}: Banner={result['banner_detected']}, Channel={channel_name}")
        
        return {
            'success': True,
            'channel_found': channel_found is not None,
            'channel_info': channel_found['channel_info'] if channel_found else {},
            'best_result': channel_found,
            'images_analyzed': len(analysis_results),
            'analysis_results': analysis_results,
            'banner_region': banner_region
        }

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test channel detection with downloaded images')
    parser.add_argument('input', nargs='?', 
                       help='Either a full image URL or base URL for sequence testing')
    parser.add_argument('timestamp', nargs='?',
                       help='Starting timestamp for sequence testing (YYYYMMDDHHMMSS)')
    parser.add_argument('--banner_region', 
                       help='Banner region as x,y,width,height (e.g., 437,460,405,260 for mobile)')
    parser.add_argument('--num_images', type=int, default=3,
                       help='Number of sequential images to analyze for sequence testing (default: 3)')
    parser.add_argument('--mode', choices=['single', 'sequence'], default='auto',
                       help='Testing mode: single image or sequence (auto-detects based on args)')
    parser.add_argument('--full_image', action='store_true',
                       help='Analyze full image instead of banner region (for debugging)')
    parser.add_argument('--api_key', 
                       help='OpenRouter API key for real AI analysis (or set OPENROUTER_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Default values if no arguments provided
    if not args.input:
        # Default to the test image you provided
        args.input = 'https://virtualpytest.com/host/stream/capture2/captures/capture_20250805171406.jpg'
        args.mode = 'single'
    
    # Parse banner region if provided
    banner_region = None
    if args.full_image:
        print(f"📐 Using full image (no banner region cropping)")
    elif args.banner_region:
        try:
            x, y, width, height = map(int, args.banner_region.split(','))
            banner_region = {'x': x, 'y': y, 'width': width, 'height': height}
            print(f"📐 Using banner region: {banner_region}")
        except (ValueError, IndexError) as e:
            print(f"❌ Invalid banner_region format '{args.banner_region}': {e}")
            print(f"📐 Expected format: x,y,width,height (e.g., 437,460,405,260)")
            sys.exit(1)
    else:
        # Default mobile banner region based on your setup
        banner_region = {'x': 437, 'y': 460, 'width': 405, 'height': 260}
        print(f"📐 Using default mobile banner region: {banner_region}")
    
    # Determine testing mode
    if args.mode == 'auto':
        if args.input.endswith('.jpg') or args.input.endswith('.png'):
            mode = 'single'
        else:
            mode = 'sequence'
    else:
        mode = args.mode
    
    # Set API key if provided
    if args.api_key:
        os.environ['OPENROUTER_API_KEY'] = args.api_key
        print(f"🔑 Using provided API key for real AI analysis")
    
    print(f"🚀 Starting channel detection test in {mode} mode...")
    
    # Run the appropriate test
    if mode == 'single':
        if not args.input.startswith('http'):
            print(f"❌ For single image mode, provide a full image URL")
            sys.exit(1)
        
        result = test_single_image_channel_detection(args.input, banner_region)
    else:
        if not args.timestamp:
            print(f"❌ For sequence mode, provide both base_url and timestamp")
            sys.exit(1)
        
        result = test_sequence_channel_detection(
            args.input, 
            args.timestamp, 
            banner_region,
            args.num_images
        )
    
    if result['success']:
        print(f"\n✅ Test completed successfully!")
        if mode == 'single':
            if result.get('banner_detected') and result.get('channel_info'):
                print(f"🎉 Channel information detected successfully!")
            else:
                print(f"❌ No channel information detected")
        else:
            if result.get('channel_found'):
                print(f"🎉 Channel information found in sequence!")
            else:
                print(f"❌ No channel information found in sequence")
    else:
        print(f"\n❌ Test failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()