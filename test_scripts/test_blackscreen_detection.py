#!/usr/bin/env python3
"""
Test Blackscreen Detection Script

This script downloads images from the public URL and tests blackscreen detection
with the same parameters used by the ZapController to debug detection issues.

Usage:
    python test_scripts/test_blackscreen_detection.py [base_url] [timestamp] [--analysis_rectangle x,y,width,height]
    
Example:
    python test_scripts/test_blackscreen_detection.py https://virtualpytest.com/host/stream/capture2/captures/ 20250805155132 --analysis_rectangle 296,300,432,368
"""

import os
import sys
import requests
import cv2
import numpy as np
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

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

def analyze_blackscreen_opencv(image_path: str, analysis_rectangle: Dict[str, int] = None, 
                              blackscreen_threshold: int = 10) -> Dict[str, Any]:
    """
    Analyze image for blackscreen using OpenCV (same logic as VideoContentHelpers)
    
    Args:
        image_path: Path to image file
        analysis_rectangle: Rectangle to analyze {'x': int, 'y': int, 'width': int, 'height': int}
        blackscreen_threshold: Threshold for blackscreen detection (default: 10)
        
    Returns:
        Dictionary with blackscreen analysis results
    """
    try:
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return {'success': False, 'error': 'Could not load image'}
        
        original_height, original_width = img.shape[:2]
        print(f"🖼️  Original image size: {original_width}x{original_height}")
        
        # Apply analysis rectangle if specified
        if analysis_rectangle:
            x = analysis_rectangle['x']
            y = analysis_rectangle['y']
            width = analysis_rectangle['width']
            height = analysis_rectangle['height']
            
            # Validate rectangle bounds
            if (x < 0 or y < 0 or x + width > original_width or y + height > original_height):
                print(f"⚠️  Analysis rectangle {x},{y},{width},{height} is out of bounds for image {original_width}x{original_height}")
                print(f"📊 Using full image instead")
                cropped_img = img
                actual_rectangle = {'x': 0, 'y': 0, 'width': original_width, 'height': original_height}
            else:
                # Crop to analysis rectangle
                cropped_img = img[y:y+height, x:x+width]
                actual_rectangle = analysis_rectangle
                print(f"✂️  Cropped to analysis rectangle: {x},{y},{width},{height}")
        else:
            cropped_img = img
            actual_rectangle = {'x': 0, 'y': 0, 'width': original_width, 'height': original_height}
            print(f"📊 Analyzing full image")
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
        
        # Calculate blackscreen percentage
        total_pixels = gray.shape[0] * gray.shape[1]
        dark_pixels = np.sum(gray <= blackscreen_threshold)
        blackscreen_percentage = (dark_pixels / total_pixels) * 100
        
        # Determine if it's a blackscreen
        is_blackscreen = blackscreen_percentage > 80.0  # Same threshold as VideoContentHelpers
        
        # Calculate some additional stats
        mean_brightness = np.mean(gray)
        std_brightness = np.std(gray)
        min_brightness = np.min(gray)
        max_brightness = np.max(gray)
        
        result = {
            'success': True,
            'is_blackscreen': is_blackscreen,
            'blackscreen_percentage': round(blackscreen_percentage, 1),
            'blackscreen_threshold': blackscreen_threshold,
            'analysis_rectangle': actual_rectangle,
            'cropped_size': f"{cropped_img.shape[1]}x{cropped_img.shape[0]}",
            'original_size': f"{original_width}x{original_height}",
            'brightness_stats': {
                'mean': round(mean_brightness, 1),
                'std': round(std_brightness, 1),
                'min': int(min_brightness),
                'max': int(max_brightness)
            }
        }
        
        # Print analysis result
        status = "✅ BLACKSCREEN" if is_blackscreen else "❌ NOT BLACKSCREEN"
        print(f"🔍 {os.path.basename(image_path)}: {status} ({blackscreen_percentage:.1f}%)")
        print(f"    Mean brightness: {mean_brightness:.1f}, Std: {std_brightness:.1f}")
        print(f"    Range: {min_brightness}-{max_brightness}, Dark pixels: {dark_pixels}/{total_pixels}")
        
        return result
        
    except Exception as e:
        return {'success': False, 'error': f'Blackscreen analysis failed: {str(e)}'}

def test_zapping_sequence(base_url: str, timestamp: str, analysis_rectangle: Dict[str, int] = None,
                         num_images: int = 8) -> Dict[str, Any]:
    """
    Test zapping sequence detection by downloading and analyzing multiple images
    
    Args:
        base_url: Base URL for image downloads (should end with /)
        timestamp: Starting timestamp (format: YYYYMMDDHHMMSS)
        analysis_rectangle: Rectangle to analyze for blackscreen
        num_images: Number of sequential images to analyze
        
    Returns:
        Dictionary with zapping sequence analysis results
    """
    print(f"🎯 Testing zapping sequence detection")
    print(f"📍 Base URL: {base_url}")
    print(f"⏰ Starting timestamp: {timestamp}")
    print(f"🖼️  Number of images: {num_images}")
    if analysis_rectangle:
        print(f"📐 Analysis rectangle: {analysis_rectangle}")
    else:
        print(f"📐 Analysis rectangle: Full image")
    
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
        
        print(f"\n🔍 Analyzing {len(downloaded_images)} images for blackscreen detection...")
        
        # Analyze each image
        analysis_results = []
        blackscreen_start = None
        blackscreen_end = None
        
        for img_data in downloaded_images:
            result = analyze_blackscreen_opencv(
                img_data['local_path'], 
                analysis_rectangle, 
                blackscreen_threshold=10
            )
            
            if result['success']:
                result['filename'] = img_data['filename']
                result['timestamp'] = img_data['timestamp']
                result['url'] = img_data['url']
                analysis_results.append(result)
                
                # Track blackscreen sequence
                if result['is_blackscreen'] and blackscreen_start is None:
                    blackscreen_start = img_data['filename']
                elif not result['is_blackscreen'] and blackscreen_start is not None and blackscreen_end is None:
                    blackscreen_end = downloaded_images[downloaded_images.index(img_data) - 1]['filename']
        
        # If blackscreen sequence goes to the end
        if blackscreen_start and blackscreen_end is None and analysis_results:
            blackscreen_end = analysis_results[-1]['filename']
        
        # Calculate zapping detection result
        zapping_detected = blackscreen_start is not None
        if zapping_detected and blackscreen_end:
            # Calculate duration (simplified - assumes 1 second per image)
            start_idx = next(i for i, r in enumerate(analysis_results) if r['filename'] == blackscreen_start)
            end_idx = next(i for i, r in enumerate(analysis_results) if r['filename'] == blackscreen_end)
            duration = end_idx - start_idx + 1
        else:
            duration = 0
        
        # Summary
        print(f"\n📊 ZAPPING SEQUENCE ANALYSIS SUMMARY")
        print(f"=" * 50)
        print(f"✅ Images analyzed: {len(analysis_results)}")
        print(f"🎯 Zapping detected: {'YES' if zapping_detected else 'NO'}")
        if zapping_detected:
            print(f"⏱️  Blackscreen start: {blackscreen_start}")
            print(f"⏱️  Blackscreen end: {blackscreen_end}")
            print(f"⏱️  Duration: {duration} seconds")
        
        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        for result in analysis_results:
            status = "🖤" if result['is_blackscreen'] else "🖼️ "
            print(f"{status} {result['filename']}: {result['blackscreen_percentage']:.1f}% blackscreen")
        
        return {
            'success': True,
            'zapping_detected': zapping_detected,
            'blackscreen_start': blackscreen_start,
            'blackscreen_end': blackscreen_end,
            'duration': duration,
            'images_analyzed': len(analysis_results),
            'analysis_results': analysis_results,
            'analysis_rectangle': analysis_rectangle
        }

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test blackscreen detection with downloaded images')
    parser.add_argument('base_url', nargs='?', 
                       default='https://virtualpytest.com/host/stream/capture2/captures/',
                       help='Base URL for image downloads')
    parser.add_argument('timestamp', nargs='?',
                       default='20250805155132',
                       help='Starting timestamp (YYYYMMDDHHMMSS)')
    parser.add_argument('--analysis_rectangle', 
                       help='Analysis rectangle as x,y,width,height (e.g., 296,300,432,368)')
    parser.add_argument('--num_images', type=int, default=8,
                       help='Number of sequential images to analyze (default: 8)')
    parser.add_argument('--blackscreen_threshold', type=int, default=10,
                       help='Blackscreen threshold (default: 10)')
    
    args = parser.parse_args()
    
    # Parse analysis rectangle if provided
    analysis_rectangle = None
    if args.analysis_rectangle:
        try:
            x, y, width, height = map(int, args.analysis_rectangle.split(','))
            analysis_rectangle = {'x': x, 'y': y, 'width': width, 'height': height}
            print(f"📐 Using analysis rectangle: {analysis_rectangle}")
        except (ValueError, IndexError) as e:
            print(f"❌ Invalid analysis_rectangle format '{args.analysis_rectangle}': {e}")
            print(f"📐 Expected format: x,y,width,height (e.g., 296,300,432,368)")
            sys.exit(1)
    
    print(f"🚀 Starting blackscreen detection test...")
    print(f"🔧 Blackscreen threshold: {args.blackscreen_threshold}")
    
    # Run the test
    result = test_zapping_sequence(
        args.base_url, 
        args.timestamp, 
        analysis_rectangle,
        args.num_images
    )
    
    if result['success']:
        print(f"\n✅ Test completed successfully!")
        if result['zapping_detected']:
            print(f"🎉 Zapping sequence detected - Duration: {result['duration']}s")
        else:
            print(f"❌ No zapping sequence detected")
    else:
        print(f"\n❌ Test failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()