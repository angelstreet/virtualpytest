#!/usr/bin/env python3
"""Test the banner detection fix with the banner.jpg image"""

import sys
import os

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Test the AI banner detection
from shared.src.lib.utils.ai_utils import analyze_channel_banner_ai

def test_banner_detection():
    print("Testing banner detection with banner.jpg...")
    
    image_path = "backend_host/scripts/img/banner.jpg"
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    print(f"📸 Testing image: {image_path}")
    print("=" * 80)
    
    # Test our AI function
    result = analyze_channel_banner_ai(image_path, context_name="TEST")
    
    print("=" * 80)
    print("🎯 FINAL RESULT:")
    print(f"   Success: {result.get('success')}")
    print(f"   Banner detected: {result.get('banner_detected')}")
    print(f"   Channel info: {result.get('channel_info')}")
    print(f"   Confidence: {result.get('confidence')}")
    
    if result.get('banner_detected'):
        print("✅ SUCCESS: Banner detection working!")
    else:
        print("❌ FAILED: Still not detecting banner")

if __name__ == "__main__":
    test_banner_detection()
