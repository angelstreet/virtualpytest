#!/usr/bin/env python3
"""
Simple blackscreen + banner detection test
Fast sampling + edge detection only
"""

import cv2
import numpy as np
import sys
import os
import time

def analyze_blackscreen(image_path, threshold=5):
    """Analyze blackscreen with edge-based banner detection"""
    
    # Read image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"❌ Error: Could not read image: {image_path}")
        return False
    
    img_height, img_width = img.shape
    is_thumbnail = '_thumbnail' in image_path or img_width < 1000
    
    # Split into top 70% (content) and bottom 30% (banner)
    split_y = int(img_height * 0.7)
    top_region = img[0:split_y, :]
    banner_region = img[split_y:img_height, :]
    
    # === STEP 1: Blackscreen Detection (Fast Sampling) ===
    start = time.perf_counter()
    total_pixels = top_region.shape[0] * top_region.shape[1]
    
    # Sample every 3rd pixel (11% of pixels)
    sample = top_region[::3, ::3]
    sample_dark = np.sum(sample <= threshold)
    sample_total = sample.shape[0] * sample.shape[1]
    dark_percentage = (sample_dark / sample_total) * 100
    
    # Full scan only if edge case (70-90%)
    if 70 <= dark_percentage <= 90:
        dark_pixels = np.sum(top_region <= threshold)
        dark_percentage = (dark_pixels / total_pixels) * 100
        pixels_checked = total_pixels
        method = "FULL"
    else:
        pixels_checked = sample_total
        method = "SAMPLE"
    
    blackscreen_time = (time.perf_counter() - start) * 1000
    is_black = dark_percentage > 85
    
    # === STEP 2: Banner Detection (Edge Detection) ===
    start = time.perf_counter()
    edges = cv2.Canny(banner_region, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size * 100
    has_banner = 3 < edge_density < 20
    banner_time = (time.perf_counter() - start) * 1000
    
    # === FINAL DECISION ===
    is_zapping = is_black and has_banner
    
    # === PRINT RESULTS ===
    print(f"\n🔍 Image: {os.path.basename(image_path)}")
    print(f"   Size: {img_width}x{img_height} ({'thumbnail' if is_thumbnail else 'full-res'})")
    print()
    
    print(f"⬛ BLACKSCREEN CHECK (top 70%)")
    print(f"   Time: {blackscreen_time:.2f}ms [{method}]")
    print(f"   Pixels: {pixels_checked:,} of {total_pixels:,}")
    print(f"   Dark: {dark_percentage:.1f}% → {'✅ BLACK' if is_black else '❌ NOT BLACK'}")
    print()
    
    print(f"📊 BANNER CHECK (bottom 30%)")
    print(f"   Time: {banner_time:.2f}ms [EDGES]")
    print(f"   Edges: {edge_density:.1f}% → {'✅ DETECTED' if has_banner else '❌ NOT DETECTED'}")
    print()
    
    print(f"{'='*50}")
    if is_zapping:
        print(f"  RESULT: 🎯 ZAPPING BLACKSCREEN")
    elif is_black:
        print(f"  RESULT: ⬛ BLACK (no banner - false positive)")
    else:
        print(f"  RESULT: 📺 CONTENT")
    print(f"{'='*50}")
    print()
    
    return is_zapping


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_blackscreen_detection.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"❌ Error: Image not found: {image_path}")
        sys.exit(1)
    
    result = analyze_blackscreen(image_path)
    sys.exit(0 if result else 1)
