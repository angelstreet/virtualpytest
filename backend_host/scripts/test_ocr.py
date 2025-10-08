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

# Add project root to Python path for shared module
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the smart cropping algorithm
from crop_subtitles import find_subtitle_bbox
import re

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
    Run OCR testing with smart cropping on original image.
    
    Flow:
    1. Load image in grayscale
    2. Smart crop on original image
    3. Test 2 combinations:
       - Otsu + PSM 4 (single column)
       - Grayscale + PSM 6 (uniform block - best for subtitles)
    4. Compare speed and accuracy
    5. Clean noise with regex
    6. Detect language
    
    Tesseract config:
    - Languages: English, French, Italian, German, Spanish
    - OEM 3 (default LSTM mode)
    
    Saves smart cropped image for visual inspection.
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
    
    # Smart crop on ORIGINAL image
    print("\n2. Smart cropping original image...")
    try:
        start = time.perf_counter()
        bbox = find_subtitle_bbox(img_gray)
        crop_time = (time.perf_counter() - start) * 1000
        crop_img = img_gray[bbox.y:bbox.y+bbox.h, bbox.x:bbox.x+bbox.w]
        print(f"   ✓ Smart crop: {bbox.w}x{bbox.h} ({crop_time:.2f}ms)")
    except Exception as e:
        print(f"   ❌ Smart crop FAILED: {e}")
        return None
    
    # Save smart crop for visual inspection
    if save_crops:
        base_name = Path(image_path).stem
        save_dir = Path(image_path).parent
        crop_path = save_dir / f"{base_name}_smart_crop.jpg"
        cv2.imwrite(str(crop_path), crop_img)
        print(f"   💾 Saved: {crop_path.name}")
    
    # STEP 3: Test 2 specific combinations
    print("\n3. Testing OCR (2 combinations)...")
    
    try:
        import pytesseract
        
        ocr_results = []
        
        # Test 1: Otsu + PSM 4 (single column)
        print(f"\n   Test 1: Otsu + PSM 4")
        _, otsu_img = cv2.threshold(crop_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        start = time.perf_counter()
        config_otsu = '--psm 4 --oem 3 -l eng+fra+ita+deu+spa'
        text_otsu_raw = pytesseract.image_to_string(otsu_img, config=config_otsu).strip()
        time_otsu = (time.perf_counter() - start) * 1000
        text_otsu_clean = clean_ocr_noise(text_otsu_raw)
        ocr_results.append({
            'filter': 'otsu',
            'psm': 4,
            'text': text_otsu_clean,
            'time': time_otsu,
            'length': len(text_otsu_clean)
        })
        print(f"      Time: {time_otsu:.0f}ms | Raw: {len(text_otsu_raw)} chars → Cleaned: {len(text_otsu_clean)} chars")
        print(f"      Raw:     {text_otsu_raw if text_otsu_raw else '(no text)'}")
        print(f"      Cleaned: {text_otsu_clean if text_otsu_clean else '(no text)'}")
        
        # Test 2: Grayscale + PSM 6 (uniform block)
        print(f"\n   Test 2: Grayscale + PSM 6")
        start = time.perf_counter()
        config_gray = '--psm 6 --oem 3 -l eng+fra+ita+deu+spa'
        text_gray_raw = pytesseract.image_to_string(crop_img, config=config_gray).strip()
        time_gray = (time.perf_counter() - start) * 1000
        text_gray_clean = clean_ocr_noise(text_gray_raw)
        ocr_results.append({
            'filter': 'grayscale',
            'psm': 6,
            'text': text_gray_clean,
            'time': time_gray,
            'length': len(text_gray_clean)
        })
        print(f"      Time: {time_gray:.0f}ms | Raw: {len(text_gray_raw)} chars → Cleaned: {len(text_gray_clean)} chars")
        print(f"      Raw:     {text_gray_raw if text_gray_raw else '(no text)'}")
        print(f"      Cleaned: {text_gray_clean if text_gray_clean else '(no text)'}")
        
        # Find best result (by length)
        best_result = max(ocr_results, key=lambda x: x['length'])
        subtitle_text = best_result['text']
        ocr_time = best_result['time']
        
        print(f"\n   ✅ BEST: {best_result['filter']} + PSM {best_result['psm']} = {len(subtitle_text)} chars (cleaned)")
        
        # Speed comparison
        speed_diff = abs(time_otsu - time_gray)
        if time_otsu < time_gray:
            print(f"   ⚡ Otsu+PSM4 is {speed_diff:.0f}ms faster ({(speed_diff/time_gray*100):.0f}%)")
        else:
            print(f"   ⚡ Grayscale+PSM6 is {speed_diff:.0f}ms faster ({(speed_diff/time_otsu*100):.0f}%)")
        
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
    print(f"Smart crop: {bbox.w}x{bbox.h} at ({bbox.x},{bbox.y}) in {crop_time:.2f}ms")
    print(f"Best OCR: {best_result['filter']} + PSM {best_result['psm']} in {ocr_time:.0f}ms")
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
        'bbox': {'x': bbox.x, 'y': bbox.y, 'width': bbox.w, 'height': bbox.h},
        'method': 'smart_crop_original',
        'best_filter': best_result['filter'],
        'best_psm': best_result['psm']
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
    print("\nTesting:")
    print("  Crop: Smart crop on original image")
    print("  OCR tests: 2 combinations")
    print("    - Otsu + PSM 4 (single column)")
    print("    - Grayscale + PSM 6 (uniform block)")
    print("  Languages: English, French, Italian, German, Spanish")
    print("  Speed comparison")
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

