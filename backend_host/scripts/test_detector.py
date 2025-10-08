#!/usr/bin/env python3
"""
Test script for optimized detector workflow
Tests the new edge-based detection system without breaking production

Optimizations:
1. Edge detection runs first (reused for bottom content + subtitles)
2. Blackscreen check BEFORE bottom content (save cost)
3. Bottom content ONLY checked if blackscreen (for zap confirmation)
4. Smart skip logic:
   - No bottom content if no blackscreen (save cost!)
   - No subtitle check if zap (mutually exclusive - save cost!)
   - No freeze check if blackscreen/zap (save cost!)
   - No macroblocks if blackscreen/zap/freeze (save cost!)
5. Conditional OCR (only if subtitle edges detected and NOT zap)

"""

import cv2
import numpy as np
import os
import sys
import time
from pathlib import Path

# Add project root to Python path for shared module
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import OCR function from shared utils
try:
    from shared.src.lib.utils.image_utils import extract_text_from_region
    OCR_AVAILABLE = True
except ImportError as e:
    OCR_AVAILABLE = False
    print(f"⚠️  OCR not available: {e}")
except Exception as e:
    OCR_AVAILABLE = False
    print(f"⚠️  OCR import error: {type(e).__name__}: {e}")


class OptimizedDetector:
    """New optimized detector with edge-based analysis"""
    
    def detect_issues(self, image_path):
        """
        Optimized detection workflow - COMPLETE FLOW:
        
        1. Load image
        2. Edge detection (CORE - reused)
        3. Blackscreen check (5-70% of image, skip header & banner)
        4. IF blackscreen → Bottom content check (for zap confirmation)
           → Zap = blackscreen + bottom content
        5. IF NOT zap → Subtitle area check (reuse edges)
        6. IF NOT blackscreen/zap → Freeze check
        7. IF NOT blackscreen/zap/freeze → Macroblocks check
        8. IF subtitle area AND NOT zap → Subtitle OCR
        
        NOTE: Smart region analysis - skip TV headers (top 5%) and banners (bottom 30%)
        
        Returns same format as current detector.py for compatibility
        """
        timings = {}
        total_start = time.perf_counter()
        
        # === STEP 1: Load Image ===
        start = time.perf_counter()
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {'error': 'Failed to load image'}
        
        img_height, img_width = img.shape
        timings['image_load'] = (time.perf_counter() - start) * 1000
        
        # === STEP 2: Edge Detection (CORE - runs always) ===
        start = time.perf_counter()
        edges = cv2.Canny(img, 50, 150)
        timings['edge_detection'] = (time.perf_counter() - start) * 1000
        
        # Define regions
        header_y = int(img_height * 0.05)  # Skip top 5% (TV time/header)
        split_y = int(img_height * 0.7)     # Blackscreen region: 5-70%
        
        # === STEP 3: Blackscreen Detection (fast sampling) ===
        start = time.perf_counter()
        # Analyze 5% to 70% (skip header, skip bottom banner)
        top_region = img[header_y:split_y, :]
        
        # Sample every 3rd pixel (11% sample)
        # Threshold = 10 (matches production - accounts for compression artifacts)
        threshold = 10
        sample = top_region[::3, ::3]
        sample_dark = np.sum(sample <= threshold)
        sample_total = sample.shape[0] * sample.shape[1]
        dark_percentage = (sample_dark / sample_total) * 100
        
        # Full scan only if edge case (70-90%)
        if 70 <= dark_percentage <= 90:
            total_pixels = top_region.shape[0] * top_region.shape[1]
            dark_pixels = np.sum(top_region <= threshold)
            dark_percentage = (dark_pixels / total_pixels) * 100
        
        blackscreen = dark_percentage > 85
        timings['blackscreen'] = (time.perf_counter() - start) * 1000
        
        # === STEP 4: Bottom Content Check (ONLY if blackscreen - for zap confirmation) ===
        start = time.perf_counter()
        if blackscreen:
            # Check bottom 30% for banner/channel info (zap confirmation)
            edges_bottom = edges[split_y:img_height, :]
            bottom_edge_density = np.sum(edges_bottom > 0) / edges_bottom.size * 100
            has_bottom_content = 3 < bottom_edge_density < 20
            timings['bottom_content_detection'] = (time.perf_counter() - start) * 1000
        else:
            # No blackscreen = no need to check for zapping
            has_bottom_content = False
            bottom_edge_density = 0.0
            timings['bottom_content_detection'] = 0.0  # Skipped
        
        # Zap decision: blackscreen + bottom content
        zap = blackscreen and has_bottom_content
        
        # === STEP 5: Subtitle Region Detection (SKIP if zap) ===
        start = time.perf_counter()
        if zap:
            # Zapping = banner/channel info, NOT subtitles - skip check
            has_subtitle_area = False
            subtitle_edge_density = 0.0
            timings['subtitle_area_detection'] = 0.0  # Skipped
        else:
            # Only check subtitle area if NOT zapping
            subtitle_y = int(img_height * 0.85)
            edges_subtitle = edges[subtitle_y:img_height, :]
            
            subtitle_edge_density = np.sum(edges_subtitle > 0) / edges_subtitle.size * 100
            has_subtitle_area = 2 < subtitle_edge_density < 25
            timings['subtitle_area_detection'] = (time.perf_counter() - start) * 1000
        
        # === STEP 6: Freeze Detection (SMART SKIP) ===
        # NOT IMPLEMENTED in test - requires previous frames
        # Real implementation: 5-10ms
        freeze = False
        freeze_diff = 0.0
        timings['freeze'] = 0.0  # Not implemented
        
        # === STEP 7: Macroblock Detection (SMART SKIP) ===
        # NOT IMPLEMENTED in test
        # Real implementation: 2-5ms
        macroblocks = False
        quality_score = 0.0
        timings['macroblocks'] = 0.0  # Not implemented
        
        # === STEP 8: Subtitle OCR (CONDITIONAL - skip if zap) ===
        start = time.perf_counter()
        detected_language = None
        confidence = 0.0
        
        if zap:
            # Zapping = blackscreen with bottom content (not subtitles)
            subtitle_text = None
            ocr_box_info = None
            timings['subtitle_ocr'] = 0.0  # Skipped (zap)
            ocr_skip_reason = 'zap'
        elif has_subtitle_area and OCR_AVAILABLE:
            # Subtitle edges detected - run REAL OCR
            try:
                # Use edges to find subtitle box location (bottom 40% of image)
                search_y_start = int(img_height * 0.6)
                edges_search_region = edges[search_y_start:img_height, :]
                
                # Find contours (connected edge regions)
                contours, _ = cv2.findContours(edges_search_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Filter for subtitle-like boxes (horizontal rectangles with text)
                subtitle_boxes = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Filter criteria for subtitle boxes:
                    # - Width > 30% of image width (subtitles span screen)
                    # - Height between 20-150 pixels (text size range)
                    # - Aspect ratio > 3 (horizontal rectangle)
                    if w > img_width * 0.3 and 20 < h < 150 and w / h > 3:
                        # Adjust y coordinate to full image space
                        subtitle_boxes.append((x, search_y_start + y, w, h))
                
                if subtitle_boxes:
                    # Take ONLY the lowest box (highest Y coordinate = bottom-most)
                    # Subtitles are always at the bottom of the screen
                    subtitle_boxes.sort(key=lambda box: box[1], reverse=True)
                    x, y, w, h = subtitle_boxes[0]  # Lowest box
                    
                    # Extract subtitle box with small padding
                    padding = 5
                    x1 = max(0, x - padding)
                    y1 = max(0, y - padding)
                    x2 = min(img_width, x + w + padding)
                    y2 = min(img_height, y + h + padding)
                    
                    subtitle_box_region = img[y1:y2, x1:x2]
                    
                    # OPTIMIZATION 1: Downscale to target height for faster OCR
                    # Target height: 80 pixels (good for OCR, faster processing)
                    box_h, box_w = subtitle_box_region.shape
                    if box_h > 80:
                        scale = 80 / box_h
                        new_w = int(box_w * scale)
                        subtitle_box_region = cv2.resize(subtitle_box_region, (new_w, 80), interpolation=cv2.INTER_AREA)
                    
                    # OPTIMIZATION 2: Fast OCR - multi-line mode
                    # Use --psm 6 (uniform block of text) for subtitles
                    try:
                        import pytesseract
                        # Enhance contrast for better OCR
                        enhanced = cv2.convertScaleAbs(subtitle_box_region, alpha=2.0, beta=0)
                        _, thresh = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
                        
                        # Multi-line OCR (--psm 6 = uniform block of text)
                        subtitle_text = pytesseract.image_to_string(thresh, config='--psm 6 --oem 3').strip()
                    except:
                        # Fallback to standard method
                        subtitle_text = extract_text_from_region(subtitle_box_region)
                    
                    timings['subtitle_ocr'] = (time.perf_counter() - start) * 1000
                    
                    # Store box info for display
                    ocr_box_info = f"{w}x{h} at ({x},{y})"
                else:
                    # No subtitle boxes found
                    subtitle_text = None
                    ocr_box_info = None
                    timings['subtitle_ocr'] = (time.perf_counter() - start) * 1000
                
                # Detect language if text found
                detected_language = None
                confidence = 0.0
                if subtitle_text and len(subtitle_text.strip()) > 0:
                    try:
                        from shared.src.lib.utils.image_utils import detect_language
                        detected_language = detect_language(subtitle_text)  # Returns string like 'en', 'fr'
                        
                        # If language detected successfully, trust the OCR (confidence = 1.0)
                        if detected_language and detected_language != 'unknown':
                            confidence = 1.0
                            ocr_skip_reason = None  # OCR ran successfully
                        else:
                            # Language unknown but text extracted - medium confidence
                            confidence = 0.75
                            ocr_skip_reason = None  # Still accept it
                    except:
                        detected_language = 'unknown'
                        confidence = 0.75  # Text extracted, accept it
                        ocr_skip_reason = None
                else:
                    subtitle_text = None
                    ocr_skip_reason = 'no_text_found'
            except Exception as e:
                # OCR failed - show error
                subtitle_text = None
                ocr_box_info = None
                detected_language = None
                confidence = 0.0
                timings['subtitle_ocr'] = 0.0
                ocr_skip_reason = f'error: {type(e).__name__}: {str(e)}'
        else:
            # No subtitle edges or OCR not available - skip
            subtitle_text = None
            ocr_box_info = None
            detected_language = None
            confidence = 0.0
            timings['subtitle_ocr'] = 0.0  # Skipped
            if not OCR_AVAILABLE:
                ocr_skip_reason = 'ocr_unavailable'
            elif not has_subtitle_area:
                ocr_skip_reason = 'no_edges'
            else:
                ocr_skip_reason = 'unknown'
        
        # === Audio would be checked here (not implemented in test) ===
        has_audio = True  # Placeholder
        timings['audio'] = 0.0
        
        timings['total'] = (time.perf_counter() - total_start) * 1000
        
        # Return format compatible with current detector.py
        result = {
            'filename': os.path.basename(image_path),
            'blackscreen': blackscreen,
            'blackscreen_percentage': round(dark_percentage, 1),
            'blackscreen_threshold': threshold,  # Show threshold used
            'zap': zap,  # NEW!
            'has_bottom_content': has_bottom_content,  # NEW! (edges in bottom 30%)
            'bottom_edge_density': round(bottom_edge_density, 1),
            'freeze': freeze,
            'freeze_diff': round(freeze_diff, 1),
            'macroblocks': macroblocks,
            'quality_score': round(quality_score, 1),
            'subtitle_candidate': has_subtitle_area,  # NEW!
            'subtitle_edge_density': round(subtitle_edge_density, 1),
            'subtitle_text': subtitle_text,
            'ocr_box_info': ocr_box_info,  # Box dimensions and location
            'detected_language': detected_language,
            'confidence': confidence,
            'ocr_skip_reason': ocr_skip_reason,  # Debug
            'audio': has_audio,
            'performance_ms': {k: round(v, 2) for k, v in timings.items()}
        }
        
        return result


def print_result(result, verbose=False):
    """Print detection results in clean format"""
    filename = result.get('filename', 'unknown')
    
    print(f"\n{'='*70}")
    print(f"📸 {filename}")
    print(f"{'='*70}")
    
    # Get values
    blackscreen = result.get('blackscreen', False)
    has_bottom_content = result.get('has_bottom_content', False)
    zap = result.get('zap', False)
    perf = result.get('performance_ms', {})
    dark_pct = result.get('blackscreen_percentage', 0)
    bottom_density = result.get('bottom_edge_density', 0)
    
    # Show execution in order
    print(f"\n1. Edge Detection ({perf.get('edge_detection', 0):.2f}ms)")
    
    bs_threshold = result.get('blackscreen_threshold', 10)
    print(f"2. Blackscreen ({perf.get('blackscreen', 0):.2f}ms) → {'✅ YES' if blackscreen else '❌ NO'} ({dark_pct:.1f}% dark, threshold≤{bs_threshold})")
    
    # Bottom content - only if blackscreen
    bottom_time = perf.get('bottom_content_detection', 0)
    if blackscreen:
        print(f"3. Bottom Content ({bottom_time:.2f}ms) → {'✅ YES' if has_bottom_content else '❌ NO'} ({bottom_density:.1f}% edges)")
        print(f"   🎯 Zap = {'✅ CONFIRMED' if zap else '❌ NO (blackscreen but no banner)'}")
    else:
        print(f"3. Bottom Content → ⏭️  SKIPPED (no blackscreen)")
        print(f"   🎯 Zap = ❌ NO")
    
    # Subtitle area - conditional
    subtitle_time = perf.get('subtitle_area_detection', 0)
    if zap:
        print(f"4. Subtitle Area → ⏭️  SKIPPED (zap)")
    else:
        has_subtitle_area = result.get('subtitle_candidate', False)
        subtitle_density = result.get('subtitle_edge_density', 0)
        print(f"4. Subtitle Area ({subtitle_time:.2f}ms) → {'✅ YES' if has_subtitle_area else '❌ NO'} ({subtitle_density:.1f}% edges)")
        if has_subtitle_area:
            subtitle_text = result.get('subtitle_text')
            if subtitle_text:
                print(f"   Text: {subtitle_text}")
    
    # Freeze - conditional
    freeze = result.get('freeze', False)
    freeze_time = perf.get('freeze', 0)
    if freeze_time == 0:
        reason = 'zap' if zap else 'blackscreen'
        print(f"5. Freeze → ⏭️  SKIPPED ({reason})")
    else:
        freeze_diff = result.get('freeze_diff', 0)
        print(f"5. Freeze ({freeze_time:.2f}ms) → {'✅ YES' if freeze else '❌ NO'} ({freeze_diff:.1f} diff)")
    
    # Macroblocks - conditional
    macroblocks = result.get('macroblocks', False)
    macro_time = perf.get('macroblocks', 0)
    if macro_time == 0:
        reason = 'zap' if zap else ('freeze' if freeze else 'blackscreen')
        print(f"6. Macroblocks → ⏭️  SKIPPED ({reason})")
    else:
        quality = result.get('quality_score', 0)
        print(f"6. Macroblocks ({macro_time:.2f}ms) → {'✅ YES' if macroblocks else '❌ NO'} (quality: {quality:.0f})")
    
    # OCR - conditional
    ocr_time = perf.get('subtitle_ocr', 0)
    ocr_skip_reason = result.get('ocr_skip_reason')
    subtitle_text = result.get('subtitle_text')
    detected_language = result.get('detected_language')
    confidence = result.get('confidence', 0.0)
    
    if ocr_skip_reason == 'low_confidence':
        # OCR ran but confidence too low (< 70%)
        print(f"7. Subtitle OCR ({ocr_time:.0f}ms) → ⚠️  LOW CONFIDENCE")
        print(f"   Language: {detected_language} (confidence: {confidence:.2f} < 0.70 threshold)")
    elif ocr_skip_reason:
        # OCR skipped or failed
        print(f"7. Subtitle OCR → ⏭️  SKIPPED ({ocr_skip_reason})")
    elif subtitle_text:
        # OCR ran and found reliable text
        ocr_box_info = result.get('ocr_box_info')
        print(f"7. Subtitle OCR ({ocr_time:.0f}ms) → ✅ TEXT FOUND")
        if ocr_box_info:
            print(f"   Box: {ocr_box_info}")
        print(f"   Text: \"{subtitle_text}\"")
        print(f"   Language: {detected_language} (confidence: {confidence:.2f})")
    else:
        # OCR ran but found nothing
        print(f"7. Subtitle OCR ({ocr_time:.0f}ms) → ⚠️  NO TEXT EXTRACTED")
    
    # Total
    total = perf.get('total', 0)
    print(f"\n⏱️  Total: {total:.2f}ms")
    




def main():
    """Test all images in img/ directory"""
    
    # Get script directory
    script_dir = Path(__file__).parent
    img_dir = script_dir / 'img'
    
    if not img_dir.exists():
        print(f"❌ Error: Image directory not found: {img_dir}")
        return 1
    
    # Find all images (exclude debug crop images)
    all_images = sorted(img_dir.glob('*.jpg'))
    image_files = [img for img in all_images 
                   if not img.stem.endswith('_crop') and not img.stem.startswith('cropped_')]
    
    if not image_files:
        print(f"❌ Error: No images found in {img_dir}")
        return 1
    
    print("\n" + "="*70)
    print("🚀 OPTIMIZED DETECTOR TEST")
    print("="*70)
    print(f"Testing {len(image_files)} images from {img_dir}")
    print("\nOptimizations:")
    print("  ✅ Edge detection runs first (reused)")
    print("  ✅ Smart skip (no freeze if blackscreen)")
    print("  ✅ Zap confirmation (blackscreen + banner)")
    print("  ✅ Conditional OCR (only if subtitle edges)")
    
    # Check for verbose flag
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    # Create detector
    detector = OptimizedDetector()
    
    # Test each image
    results = []
    for image_path in image_files:
        result = detector.detect_issues(str(image_path))
        results.append(result)
        print_result(result, verbose=verbose)
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}")
    
    zap_count = sum(1 for r in results if r.get('zap', False))
    blackscreen_count = sum(1 for r in results if r.get('blackscreen', False))
    bottom_content_count = sum(1 for r in results if r.get('has_bottom_content', False))
    subtitle_count = sum(1 for r in results if r.get('subtitle_candidate', False))
    
    print(f"Total images tested: {len(results)}")
    print(f"Zapping detected: {zap_count}")
    print(f"Blackscreen (any): {blackscreen_count}")
    print(f"Bottom content detected: {bottom_content_count}")
    print(f"Subtitle areas: {subtitle_count}")
    
    # Average performance
    avg_total = sum(r.get('performance_ms', {}).get('total', 0) for r in results) / len(results)
    avg_edge = sum(r.get('performance_ms', {}).get('edge_detection', 0) for r in results) / len(results)
    
    print(f"\nAverage performance:")
    print(f"  Total: {avg_total:.2f}ms")
    print(f"  Edge detection: {avg_edge:.2f}ms")
    
    print(f"\n✅ Test complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())

