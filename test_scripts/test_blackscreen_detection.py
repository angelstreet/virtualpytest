#!/usr/bin/env python3
"""
Blackscreen Detection Test Script

This script tests blackscreen detection on a specific image to help fine-tune
the algorithm and banner area settings for mobile TV interfaces.

Usage:
    python test_scripts/test_blackscreen_detection.py [image_url] [--threshold THRESHOLD] [--banner_height HEIGHT]
    
Example:
    python test_scripts/test_blackscreen_detection.py "https://virtualpytest.com/host/stream/capture2/captures/capture_20250805132124.jpg"
    python test_scripts/test_blackscreen_detection.py "https://virtualpytest.com/host/stream/capture2/captures/capture_20250805132124.jpg" --threshold 15 --banner_height 400
"""

import sys
import os
import argparse
import requests
import cv2
import numpy as np
from datetime import datetime
import tempfile

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)


def download_image(url: str, local_path: str) -> bool:
    """Download image from URL to local path."""
    try:
        print(f"📥 Downloading image from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Image downloaded to: {local_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to download image: {e}")
        return False


def analyze_blackscreen_with_regions(image_path: str, threshold: int = 10, banner_height: int = 300) -> dict:
    """
    Analyze blackscreen detection with different regions and thresholds.
    
    Args:
        image_path: Path to image file
        threshold: Pixel intensity threshold (0-255)
        banner_height: Height of banner area to exclude from analysis
        
    Returns:
        Dictionary with analysis results
    """
    try:
        print(f"\n🔍 Analyzing blackscreen detection on: {os.path.basename(image_path)}")
        print(f"📊 Threshold: {threshold}, Banner height: {banner_height}")
        
        # Load image
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {'success': False, 'error': 'Could not load image'}
        
        img_height, img_width = img.shape
        print(f"📐 Image dimensions: {img_width}x{img_height}")
        
        results = {
            'success': True,
            'image_dimensions': {'width': img_width, 'height': img_height},
            'threshold': threshold,
            'banner_height': banner_height,
            'regions': {}
        }
        
        # Test different regions
        regions = {
            'full_image': {
                'x': 0, 'y': 0, 
                'width': img_width, 'height': img_height,
                'description': 'Full image (no exclusions)'
            },
            'exclude_top_banner': {
                'x': 0, 'y': banner_height, 
                'width': img_width, 'height': img_height - banner_height,
                'description': f'Exclude top {banner_height}px banner'
            },
            'content_area_only': {
                'x': 0, 'y': banner_height, 
                'width': img_width, 'height': (img_height - banner_height) // 2,
                'description': f'Content area only (exclude banner and bottom controls)'
            },
            'center_region': {
                'x': img_width // 4, 'y': banner_height, 
                'width': img_width // 2, 'height': (img_height - banner_height) // 2,
                'description': 'Center region only (exclude edges)'
            }
        }
        
        print(f"\n📊 Testing {len(regions)} different regions:")
        
        for region_name, region in regions.items():
            # Validate region bounds
            if (region['x'] < 0 or region['y'] < 0 or 
                region['x'] + region['width'] > img_width or 
                region['y'] + region['height'] > img_height):
                print(f"⚠️  {region_name}: Region out of bounds, skipping")
                continue
            
            # Crop to analysis region
            cropped = img[region['y']:region['y']+region['height'], 
                         region['x']:region['x']+region['width']]
            
            # Count dark pixels
            very_dark_pixels = np.sum(cropped <= threshold)
            total_pixels = cropped.shape[0] * cropped.shape[1]
            dark_percentage = (very_dark_pixels / total_pixels) * 100
            
            # Different blackscreen thresholds to test
            thresholds_to_test = [90, 95, 98, 99]
            blackscreen_results = {}
            
            for bs_threshold in thresholds_to_test:
                is_blackscreen = dark_percentage > bs_threshold
                blackscreen_results[f'{bs_threshold}%'] = is_blackscreen
            
            region_result = {
                'region': region,
                'total_pixels': total_pixels,
                'dark_pixels': very_dark_pixels,
                'dark_percentage': round(dark_percentage, 2),
                'blackscreen_tests': blackscreen_results,
                'recommended_blackscreen': dark_percentage > 95  # Current algorithm
            }
            
            results['regions'][region_name] = region_result
            
            # Print results
            print(f"\n🎯 {region_name.upper()}:")
            print(f"   📍 Region: {region['x']},{region['y']} {region['width']}x{region['height']}")
            print(f"   📝 {region['description']}")
            print(f"   🔢 Dark pixels: {very_dark_pixels:,} / {total_pixels:,} ({dark_percentage:.1f}%)")
            print(f"   ⚫ Blackscreen tests:")
            for bs_threshold, is_bs in blackscreen_results.items():
                status = "✅ YES" if is_bs else "❌ NO"
                print(f"      {bs_threshold} threshold: {status}")
        
        return results
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def test_different_thresholds(image_path: str, banner_height: int = 300) -> dict:
    """Test different pixel intensity thresholds."""
    print(f"\n🧪 Testing different pixel intensity thresholds:")
    
    thresholds_to_test = [5, 10, 15, 20, 25, 30]
    
    for threshold in thresholds_to_test:
        print(f"\n--- Threshold: {threshold} ---")
        result = analyze_blackscreen_with_regions(image_path, threshold, banner_height)
        
        if result['success']:
            # Show just the exclude_top_banner region for comparison
            region_result = result['regions'].get('exclude_top_banner')
            if region_result:
                dark_pct = region_result['dark_percentage']
                is_blackscreen = region_result['recommended_blackscreen']
                status = "✅ BLACKSCREEN" if is_blackscreen else "❌ NOT BLACKSCREEN"
                print(f"   🎯 Exclude banner: {dark_pct:.1f}% dark pixels → {status}")


def create_visual_analysis(image_path: str, threshold: int = 10, banner_height: int = 300):
    """Create visual analysis with region overlays."""
    try:
        print(f"\n🎨 Creating visual analysis...")
        
        # Load original image in color
        img_color = cv2.imread(image_path)
        img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        
        if img_color is None or img_gray is None:
            print("❌ Could not load image for visual analysis")
            return
        
        img_height, img_width = img_gray.shape
        
        # Create overlay showing dark pixels
        dark_mask = img_gray <= threshold
        overlay = img_color.copy()
        overlay[dark_mask] = [0, 0, 255]  # Red for dark pixels
        
        # Blend original and overlay
        result = cv2.addWeighted(img_color, 0.7, overlay, 0.3, 0)
        
        # Draw region boundaries
        # Banner region (top)
        cv2.rectangle(result, (0, 0), (img_width, banner_height), (255, 255, 0), 3)  # Yellow
        cv2.putText(result, "BANNER AREA", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        
        # Content analysis region
        cv2.rectangle(result, (0, banner_height), (img_width, img_height), (0, 255, 0), 3)  # Green
        cv2.putText(result, "ANALYSIS AREA", (10, banner_height + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Save result
        output_path = image_path.replace('.jpg', '_analysis.jpg')
        cv2.imwrite(output_path, result)
        print(f"✅ Visual analysis saved to: {output_path}")
        
        # Also save the dark pixel mask
        mask_path = image_path.replace('.jpg', '_dark_mask.jpg')
        cv2.imwrite(mask_path, dark_mask.astype(np.uint8) * 255)
        print(f"✅ Dark pixel mask saved to: {mask_path}")
        
    except Exception as e:
        print(f"❌ Visual analysis failed: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Test blackscreen detection on specific image')
    parser.add_argument('image_url', nargs='?', 
                       default='https://virtualpytest.com/host/stream/capture2/captures/capture_20250805132124.jpg',
                       help='Image URL to test (default: the problematic mobile image)')
    parser.add_argument('--threshold', type=int, default=10,
                       help='Pixel intensity threshold (0-255, default: 10)')
    parser.add_argument('--banner_height', type=int, default=300,
                       help='Height of banner area to exclude (default: 300)')
    parser.add_argument('--test_thresholds', action='store_true',
                       help='Test multiple pixel intensity thresholds')
    parser.add_argument('--visual', action='store_true',
                       help='Create visual analysis with region overlays')
    
    args = parser.parse_args()
    
    print("🧪 BLACKSCREEN DETECTION TEST SCRIPT")
    print("=" * 50)
    
    # Download image to temp file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        if not download_image(args.image_url, temp_path):
            return 1
        
        # Main analysis
        result = analyze_blackscreen_with_regions(temp_path, args.threshold, args.banner_height)
        
        if not result['success']:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            return 1
        
        # Test different thresholds if requested
        if args.test_thresholds:
            test_different_thresholds(temp_path, args.banner_height)
        
        # Create visual analysis if requested
        if args.visual:
            create_visual_analysis(temp_path, args.threshold, args.banner_height)
        
        # Summary recommendations
        print(f"\n📋 RECOMMENDATIONS:")
        print(f"=" * 30)
        
        exclude_banner = result['regions'].get('exclude_top_banner')
        if exclude_banner:
            dark_pct = exclude_banner['dark_percentage']
            is_blackscreen = exclude_banner['recommended_blackscreen']
            
            print(f"🎯 For mobile TV interfaces:")
            print(f"   • Current result: {dark_pct:.1f}% dark pixels")
            print(f"   • Blackscreen detected: {'✅ YES' if is_blackscreen else '❌ NO'}")
            
            if dark_pct > 85 and not is_blackscreen:
                print(f"   • 💡 SUGGESTION: Lower blackscreen threshold to 85-90% for mobile")
            elif dark_pct < 70:
                print(f"   • 💡 SUGGESTION: This doesn't appear to be blackscreen content")
            
            print(f"   • 🎛️  Try: --threshold {args.threshold + 5} --banner_height {args.banner_height + 50}")
        
        print(f"\n✅ Analysis complete!")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        # Cleanup temp file
        try:
            os.unlink(temp_path)
        except:
            pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())