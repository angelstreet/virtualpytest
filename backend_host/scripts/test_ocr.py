#!/usr/bin/env python3
"""
Simple OCR test script - extracts and tests subtitle OCR

Usage:
    python test_ocr.py subtitles.jpg
    python test_ocr.py subtitles.jpg --debug  # Saves cropped images

Always saves debug crops to see exactly what OCR is processing.
"""

import cv2
import numpy as np
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple
import re

# Add project root to Python path for shared module
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# === CONFIGURATION ===
# OCR Crop Method: 'smart' (dark mask-based, 60-70% smaller) or 'safe' (fixed region)
OCR_CROP_METHOD = 'safe'  # Disabled smart crop - using safe area (faster, more reliable)

# Import the smart cropping algorithm
from crop_subtitles import find_subtitle_bbox

def clean_ocr_noise(text: str) -> str:
    """
    Remove OCR noise: consecutive 1-2 char patterns separated by spaces.
    Examples: ", . . -" or "i ~ t" or "rr ae *. as"
    """
    if not text:
        return text
    
    # Split into lines
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Pattern: match sequences of 1-2 chars separated by spaces/punctuation
        # Remove lines or parts that are mostly garbage (< 3 consecutive letters)
        
        # Check if line has at least one word with 3+ letters
        words = line.split()
        real_words = [w for w in words if len(re.sub(r'[^a-zA-Z]', '', w)) >= 3]
        
        if real_words:
            # Keep line, but clean trailing noise
            # Remove trailing patterns like ", . . -" or "i : |"
            cleaned = re.sub(r'[\s,\.;:\-\|~\*]+$', '', line)
            # Remove leading noise
            cleaned = re.sub(r'^[\s,\.;:\-\|~\*]+', '', cleaned)
            cleaned_lines.append(cleaned)
    
    return '\n'.join(cleaned_lines).strip()

def test_ocr_on_image(image_path, save_crops=True):
    """
    Run OCR testing with configurable cropping (smart or safe area).
    
    Flow:
    1. Load image in grayscale
    2. Edge detection
    3. Find subtitle region
    4. Crop (smart edge-based or safe area)
    5. Run OCR: Grayscale + PSM 6 (uniform block - best for subtitles)
    6. Clean noise with regex (remove consecutive 1-2 char patterns)
    7. Detect language
    
    Tesseract config:
    - PSM 6 (uniform block of text)
    - OEM 3 (default LSTM mode)
    - Languages: English, French, Italian, German, Spanish
    
    Saves cropped image for visual inspection.
    """
    print(f"\n{'='*70}")
    print(f"🔍 OCR TEST: {os.path.basename(image_path)}")
    print(f"{'='*70}\n")
    
    # Load image in grayscale
    print("1. Loading image...")
    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        print(f"❌ Error: Failed to load image: {image_path}")
        return None
    
    img_height, img_width = img_gray.shape[:2]
    print(f"   Image size: {img_width}x{img_height}")
    
    # Cropping (matches detector.py logic)
    print(f"\n2. Cropping ({OCR_CROP_METHOD} mode)...")
    start = time.perf_counter()
    
    # Calculate crop based on method
    if OCR_CROP_METHOD == 'smart':
        # SMART CROP: Dark mask-based (proven implementation from crop_subtitles.py)
        try:
            bbox = find_subtitle_bbox(img_gray)
            x, y, w, h = bbox.x, bbox.y, bbox.w, bbox.h
            crop_method = "smart_dark_mask"
        except (ValueError, Exception) as e:
            # Fall back to safe area if smart crop fails
            x = int(img_width * 0.10)
            y = int(img_height * 0.60)
            w = int(img_width * 0.80)
            h = int(img_height * 0.35)
            crop_method = f"smart_fallback_safe ({str(e)[:30]})"
            print(f"   ⚠️  Smart crop failed: {str(e)[:50]}")
    else:
        # SAFE AREA: Fixed region (60-95% height, 10-90% width)
        x = int(img_width * 0.10)
        y = int(img_height * 0.60)
        w = int(img_width * 0.80)
        h = int(img_height * 0.35)
        crop_method = "safe_area_fixed"
    
    crop_img = img_gray[y:y+h, x:x+w]
    crop_time = (time.perf_counter() - start) * 1000
    print(f"   ✓ Crop: {w}x{h} at ({x},{y}) in {crop_time:.2f}ms [{crop_method}]")
    
    # Save crop for visual inspection
    if save_crops:
        base_name = Path(image_path).stem
        save_dir = Path(image_path).parent
        crop_path = save_dir / f"{base_name}_{OCR_CROP_METHOD}_crop.jpg"
        cv2.imwrite(str(crop_path), crop_img)
        print(f"   💾 Saved: {crop_path.name}")
    
    # STEP 3: Run OCR (Grayscale + PSM 6 - production method)
    print("\n3. Running OCR (Grayscale + PSM 6)...")
    
    try:
        import pytesseract
        
        # Grayscale + PSM 6 (uniform block) - production method
        start = time.perf_counter()
        config = '--psm 6 --oem 3 -l eng+fra+ita+deu+spa'
        text_raw = pytesseract.image_to_string(crop_img, config=config).strip()
        ocr_time = (time.perf_counter() - start) * 1000
        text_clean = clean_ocr_noise(text_raw)
        
        print(f"   Time: {ocr_time:.0f}ms | Raw: {len(text_raw)} chars → Cleaned: {len(text_clean)} chars")
        print(f"   Raw text:     {text_raw if text_raw else '(no text)'}")
        if text_clean != text_raw:
            print(f"   Cleaned text: {text_clean if text_clean else '(no text)'}")
        
        subtitle_text = text_clean
        
    except ImportError:
        print(f"   ❌ Error: pytesseract not available")
        return None
    except Exception as e:
        print(f"   ❌ Error: OCR failed: {e}")
        return None
    
    # Language detection
    print("\n4. Detecting language...")
    detected_language = None
    if subtitle_text and len(subtitle_text.strip()) > 0:
        try:
            from shared.src.lib.utils.image_utils import detect_language
            start = time.perf_counter()
            detected_language = detect_language(subtitle_text)
            lang_time = (time.perf_counter() - start) * 1000
            print(f"   ✓ Language detected in {lang_time:.0f}ms: {detected_language}")
        except:
            detected_language = 'unknown'
            print(f"   ⚠️  Language detection failed, marked as 'unknown'")
    else:
        print(f"   ⚠️  No text to detect language")
    
    # Results summary
    print(f"\n{'='*70}")
    print(f"📊 FINAL RESULT")
    print(f"{'='*70}")
    print(f"Crop: {w}x{h} at ({x},{y}) in {crop_time:.2f}ms [{crop_method}]")
    print(f"OCR: Grayscale + PSM 6 in {ocr_time:.0f}ms")
    print(f"Text extracted: {'YES' if subtitle_text else 'NO'}")
    if subtitle_text:
        print(f"Text length: {len(subtitle_text)} characters")
        print(f"Language: {detected_language}")
        print(f"\nFull extracted text:")
        print(f"┌{'─' * 68}┐")
        for line in subtitle_text.split('\n'):
            print(f"│ {line:<66} │")
        print(f"└{'─' * 68}┘")
    else:
        print(f"⚠️  No text extracted")
    
    return {
        'text': subtitle_text,
        'language': detected_language,
        'bbox': {'x': x, 'y': y, 'width': w, 'height': h},
        'method': crop_method,
        'filter': 'grayscale',
        'psm': 6
    }


def main():
    """Main entry point"""
    
    # Single image mode
    if len(sys.argv) >= 2:
        image_path = sys.argv[1]
        
        if not os.path.exists(image_path):
            print(f"❌ Error: Image not found: {image_path}")
            return 1
        
        # Always save crops for debugging
        result = test_ocr_on_image(image_path, save_crops=True)
        
        if result is None:
            return 1
        
        return 0
    
    # Batch mode - test all images in img/subt/
    script_dir = Path(__file__).parent
    subt_dir = script_dir / 'img' / 'subt'
    
    if not subt_dir.exists():
        print(f"❌ Error: Directory not found: {subt_dir}")
        print("Usage: python test_ocr.py [image_path]")
        print("Example: python test_ocr.py img/subt/subtitles.jpg")
        return 1
    
    # Find all images directly in subt/ (not in subdirectories)
    image_files = sorted(subt_dir.glob('*.jpg'))
    # Filter out crop images and any that contain "_crop_" in name
    image_files = [f for f in image_files if not any(x in f.stem for x in ['_crop'])]
    
    if not image_files:
        print(f"❌ Error: No .jpg images found in {subt_dir}")
        return 1
    
    print("\n" + "="*70)
    print("🧪 OCR TEST - BATCH MODE")
    print("="*70)
    print(f"Testing {len(image_files)} images from {subt_dir}")
    print("\nConfiguration:")
    print(f"  Crop method: {OCR_CROP_METHOD.upper()} ({'dark mask-based' if OCR_CROP_METHOD == 'smart' else 'fixed region'})")
    print("  OCR: Grayscale + PSM 6 (uniform block)")
    print("  Languages: English, French, Italian, German, Spanish")
    print("  Noise cleaning: Regex filter for consecutive 1-2 char patterns")
    print("="*70)
    
    # Test each image
    results = []
    for img_path in image_files:
        result = test_ocr_on_image(str(img_path), save_crops=True)
        if result:
            results.append({
                'name': img_path.name,
                'result': result
            })
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    
    total_images = len(results)
    images_with_text = sum(1 for r in results if r['result']['text'])
    
    print(f"\nTotal images tested: {total_images}")
    print(f"Images with text found: {images_with_text}")
    print(f"Images without text: {total_images - images_with_text}")
    
    print(f"\n📝 Extracted texts:")
    for r in results:
        text = r['result']['text']
        lang = r['result']['language']
        if text:
            # Show first line only
            first_line = text.split('\n')[0]
            if len(first_line) > 50:
                first_line = first_line[:50] + "..."
            print(f"  • {r['name']:<30} [{lang}] \"{first_line}\"")
        else:
            print(f"  • {r['name']:<30} [no text]")
    
    print(f"\n🔍 Debug crops saved in: {subt_dir}/")
    print(f"✅ Test complete!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

