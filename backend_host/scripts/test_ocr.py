#!/usr/bin/env python3
"""
Simple OCR Comparison: Tesseract vs PaddleOCR

Compares 2 crop methods (safe + smart) × 2 OCR engines (Tesseract + PaddleOCR)

Usage:
    python test_ocr.py subtitles.jpg
"""

import cv2
import numpy as np
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Try to import smart crop
try:
    from crop_subtitles import find_subtitle_bbox
    SMART_CROP_AVAILABLE = True
except ImportError:
    SMART_CROP_AVAILABLE = False

def clean_text(text: str) -> str:
    """Remove OCR noise"""
    if not text:
        return text
    lines = []
    for line in text.split('\n'):
        words = line.split()
        real_words = [w for w in words if len(re.sub(r'[^a-zA-Z]', '', w)) >= 3]
        if real_words:
            cleaned = re.sub(r'[\s,\.;:\-\|~\*]+$', '', line)
            cleaned = re.sub(r'^[\s,\.;:\-\|~\*]+', '', cleaned)
            lines.append(cleaned)
    return '\n'.join(lines).strip()


def diagnose_environment():
    """Diagnose the environment for OCR dependencies"""
    print(f"\n{'='*70}")
    print(f"🔧 ENVIRONMENT DIAGNOSTICS")
    print(f"{'='*70}\n")
    
    diagnostics = {
        'python_version': sys.version,
        'cv2_available': False,
        'numpy_available': False,
        'tesseract_available': False,
        'paddle_available': False,
        'crop_subtitles_available': SMART_CROP_AVAILABLE,
    }
    
    # Check OpenCV
    try:
        import cv2
        diagnostics['cv2_available'] = True
        diagnostics['cv2_version'] = cv2.__version__
    except ImportError:
        pass
    
    # Check NumPy
    try:
        import numpy as np
        diagnostics['numpy_available'] = True
        diagnostics['numpy_version'] = np.__version__
    except ImportError:
        pass
    
    # Check Tesseract
    try:
        import pytesseract
        diagnostics['tesseract_available'] = True
        version = pytesseract.get_tesseract_version()
        diagnostics['tesseract_version'] = str(version)
    except (ImportError, Exception) as e:
        diagnostics['tesseract_error'] = str(e)
    
    # Check PaddleOCR
    try:
        from paddleocr import PaddleOCR
        diagnostics['paddle_available'] = True
        diagnostics['paddle_note'] = 'Installed (version check requires init)'
    except ImportError as e:
        diagnostics['paddle_error'] = str(e)
    
    # Print diagnostics
    print("Python Environment:")
    print(f"  Version: {sys.version.split()[0]}")
    print(f"  Executable: {sys.executable}")
    
    print("\nDependencies:")
    for key, value in sorted(diagnostics.items()):
        if key.endswith('_available'):
            lib = key.replace('_available', '')
            status = "✓ Available" if value else "✗ Not available"
            print(f"  {lib}: {status}")
            if value and f'{lib}_version' in diagnostics:
                print(f"    Version: {diagnostics[f'{lib}_version']}")
            if not value and f'{lib}_error' in diagnostics:
                print(f"    Error: {diagnostics[f'{lib}_error']}")
    
    print("\nSmart Crop:")
    print(f"  Status: {'✓ Available' if SMART_CROP_AVAILABLE else '✗ Not available'}")
    if not SMART_CROP_AVAILABLE:
        print(f"  Reason: crop_subtitles.py import failed")
        print(f"  Impact: Will use safe area cropping only")
    
    return diagnostics


def test_tesseract_ocr(crop_img: np.ndarray, config: str = '--psm 6 --oem 3 -l eng+fra+ita+deu+spa') -> Dict[str, Any]:
    """Test Tesseract OCR on cropped image"""
    try:
        import pytesseract
        
        start = time.perf_counter()
        text_raw = pytesseract.image_to_string(crop_img, config=config).strip()
        ocr_time = (time.perf_counter() - start) * 1000
        text_clean = clean_ocr_noise(text_raw)
        
        return {
            'success': True,
            'engine': 'tesseract',
            'text_raw': text_raw,
            'text_clean': text_clean,
            'time_ms': ocr_time,
            'config': config,
        }
    except ImportError:
        return {
            'success': False,
            'engine': 'tesseract',
            'error': 'pytesseract not installed',
        }
    except Exception as e:
        return {
            'success': False,
            'engine': 'tesseract',
            'error': str(e),
            'traceback': traceback.format_exc(),
        }


def test_paddle_ocr(crop_img: np.ndarray, use_angle_cls: bool = True, lang: str = 'en') -> Dict[str, Any]:
    """Test PaddleOCR on cropped image"""
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR (this takes time on first run)
        init_start = time.perf_counter()
        ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang, show_log=False)
        init_time = (time.perf_counter() - init_start) * 1000
        
        # Run OCR
        start = time.perf_counter()
        result = ocr.ocr(crop_img, cls=use_angle_cls)
        ocr_time = (time.perf_counter() - start) * 1000
        
        # Extract text from result
        # PaddleOCR returns: [[[box], (text, confidence)], ...]
        text_lines = []
        confidences = []
        
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text, conf = line[1]
                    text_lines.append(text)
                    confidences.append(conf)
        
        text_raw = '\n'.join(text_lines)
        text_clean = clean_ocr_noise(text_raw)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'success': True,
            'engine': 'paddle',
            'text_raw': text_raw,
            'text_clean': text_clean,
            'time_ms': ocr_time,
            'init_time_ms': init_time,
            'confidence': avg_confidence,
            'num_lines': len(text_lines),
            'config': f'angle_cls={use_angle_cls}, lang={lang}',
        }
    except ImportError as e:
        return {
            'success': False,
            'engine': 'paddle',
            'error': f'PaddleOCR not installed: {e}',
            'install_hint': 'pip install paddlepaddle paddleocr',
        }
    except Exception as e:
        return {
            'success': False,
            'engine': 'paddle',
            'error': str(e),
            'traceback': traceback.format_exc(),
        }

def test_smart_crop_with_diagnostics(img_gray: np.ndarray) -> Tuple[Optional[Dict], str]:
    """
    Test smart crop with detailed diagnostics about why it might fail.
    Returns: (crop_info_dict, diagnostic_message)
    """
    if not SMART_CROP_AVAILABLE:
        return None, "Smart crop module not imported"
    
    try:
        # Test the environment first
        if not hasattr(img_gray, 'shape'):
            return None, "Invalid image array - no shape attribute"
        
        if len(img_gray.shape) != 2:
            return None, f"Image must be grayscale (2D), got shape: {img_gray.shape}"
        
        height, width = img_gray.shape
        if height < 100 or width < 100:
            return None, f"Image too small for smart crop: {width}x{height}"
        
        # Try smart crop
        bbox = find_subtitle_bbox(img_gray)
        
        crop_info = {
            'x': bbox.x,
            'y': bbox.y,
            'w': bbox.w,
            'h': bbox.h,
            'method': 'smart_dark_mask',
        }
        
        return crop_info, "Success"
        
    except ValueError as e:
        # Expected failure from find_subtitle_bbox
        return None, f"Subtitle detection failed: {str(e)}"
    
    except AttributeError as e:
        # Missing cv2 or numpy functions
        return None, f"Missing dependency function: {str(e)}"
    
    except Exception as e:
        # Unexpected error
        tb = traceback.format_exc()
        return None, f"Unexpected error: {str(e)}\nTraceback:\n{tb}"


def test_ocr_on_image(image_path, save_crops=True, test_engines='both'):
    """
    Run OCR comparison testing with Tesseract and PaddleOCR.
    
    Flow:
    1. Load image in grayscale
    2. Test both crop methods (smart + safe)
    3. Run both OCR engines on each crop
    4. Compare results and timings
    
    Args:
        image_path: Path to image file
        save_crops: Save cropped images for visual inspection
        test_engines: 'both', 'tesseract', or 'paddle'
    """
    print(f"\n{'='*70}")
    print(f"🔍 OCR COMPARISON TEST: {os.path.basename(image_path)}")
    print(f"{'='*70}\n")
    
    # Load image in grayscale
    print("1. Loading image...")
    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        print(f"❌ Error: Failed to load image: {image_path}")
        return None
    
    img_height, img_width = img_gray.shape[:2]
    print(f"   Image size: {img_width}x{img_height}")
    
    # Test all crop methods
    print(f"\n2. Testing crop methods...")
    crops_to_test = []
    
    # SMART CROP
    if SMART_CROP_AVAILABLE:
        print(f"   Testing smart crop...")
        start = time.perf_counter()
        crop_info, diagnostic = test_smart_crop_with_diagnostics(img_gray)
        crop_time = (time.perf_counter() - start) * 1000
        
        if crop_info:
            x, y, w, h = crop_info['x'], crop_info['y'], crop_info['w'], crop_info['h']
            crop_img = img_gray[y:y+h, x:x+w]
            crops_to_test.append({
                'name': 'smart',
                'image': crop_img,
                'bbox': crop_info,
                'time_ms': crop_time,
                'diagnostic': diagnostic
            })
            print(f"   ✓ Smart crop: {w}x{h} at ({x},{y}) in {crop_time:.2f}ms")
        else:
            print(f"   ✗ Smart crop failed: {diagnostic}")
    else:
        print(f"   ⊘ Smart crop not available")
    
    # SAFE AREA CROP
    print(f"   Testing safe area crop...")
    start = time.perf_counter()
    x = int(img_width * 0.10)
    y = int(img_height * 0.60)
    w = int(img_width * 0.80)
    h = int(img_height * 0.35)
    crop_img = img_gray[y:y+h, x:x+w]
    crop_time = (time.perf_counter() - start) * 1000
    
    crops_to_test.append({
        'name': 'safe',
        'image': crop_img,
        'bbox': {'x': x, 'y': y, 'w': w, 'h': h, 'method': 'safe_area_fixed'},
        'time_ms': crop_time,
        'diagnostic': 'Success'
    })
    print(f"   ✓ Safe crop: {w}x{h} at ({x},{y}) in {crop_time:.2f}ms")
    
    # Save crops for visual inspection
    if save_crops:
        base_name = Path(image_path).stem
        save_dir = Path(image_path).parent
        for crop_data in crops_to_test:
            crop_path = save_dir / f"{base_name}_{crop_data['name']}_crop.jpg"
            cv2.imwrite(str(crop_path), crop_data['image'])
            print(f"   💾 Saved: {crop_path.name}")
    
    # Run OCR on all crops with all engines
    print(f"\n3. Running OCR engines...")
    all_results = []
    
    for crop_data in crops_to_test:
        print(f"\n   Testing crop: {crop_data['name'].upper()}")
        crop_results = {'crop_method': crop_data['name'], 'crop_bbox': crop_data['bbox']}
        
        # Tesseract
        if test_engines in ['both', 'tesseract']:
            print(f"     • Tesseract...")
            tess_result = test_tesseract_ocr(crop_data['image'])
            crop_results['tesseract'] = tess_result
            if tess_result['success']:
                print(f"       Time: {tess_result['time_ms']:.0f}ms | Text: {len(tess_result['text_clean'])} chars")
            else:
                print(f"       ✗ Failed: {tess_result.get('error', 'Unknown error')}")
        
        # PaddleOCR
        if test_engines in ['both', 'paddle']:
            print(f"     • PaddleOCR...")
            paddle_result = test_paddle_ocr(crop_data['image'])
            crop_results['paddle'] = paddle_result
            if paddle_result['success']:
                print(f"       Time: {paddle_result['time_ms']:.0f}ms (init: {paddle_result['init_time_ms']:.0f}ms) | Text: {len(paddle_result['text_clean'])} chars | Confidence: {paddle_result['confidence']:.2f}")
            else:
                print(f"       ✗ Failed: {paddle_result.get('error', 'Unknown error')}")
                if 'install_hint' in paddle_result:
                    print(f"       💡 {paddle_result['install_hint']}")
        
        all_results.append(crop_results)
    
    # Language detection (use best OCR result)
    print(f"\n4. Detecting language...")
    best_text = None
    for result in all_results:
        for engine in ['tesseract', 'paddle']:
            if engine in result and result[engine].get('success') and result[engine].get('text_clean'):
                if not best_text or len(result[engine]['text_clean']) > len(best_text):
                    best_text = result[engine]['text_clean']
    
    detected_language = None
    if best_text:
        try:
            from shared.src.lib.utils.image_utils import detect_language
            start = time.perf_counter()
            detected_language = detect_language(best_text)
            lang_time = (time.perf_counter() - start) * 1000
            print(f"   ✓ Language detected in {lang_time:.0f}ms: {detected_language}")
        except Exception as e:
            detected_language = 'unknown'
            print(f"   ⚠️  Language detection failed: {e}")
    else:
        print(f"   ⚠️  No text to detect language")
    
    # Print comparison summary
    print(f"\n{'='*70}")
    print(f"📊 COMPARISON RESULTS")
    print(f"{'='*70}")
    
    for result in all_results:
        crop_name = result['crop_method'].upper()
        bbox = result['crop_bbox']
        print(f"\nCrop Method: {crop_name}")
        print(f"  Region: {bbox['w']}x{bbox['h']} at ({bbox['x']},{bbox['y']})")
        
        for engine in ['tesseract', 'paddle']:
            if engine in result:
                engine_result = result[engine]
                print(f"\n  {engine.capitalize()}:")
                if engine_result['success']:
                    print(f"    Time: {engine_result['time_ms']:.0f}ms")
                    if 'confidence' in engine_result:
                        print(f"    Confidence: {engine_result['confidence']:.2%}")
                    text = engine_result['text_clean']
                    if text:
                        print(f"    Text ({len(text)} chars):")
                        for line in text.split('\n')[:3]:  # First 3 lines
                            print(f"      \"{line[:60]}{'...' if len(line) > 60 else ''}\"")
                        if len(text.split('\n')) > 3:
                            print(f"      ... ({len(text.split('\n')) - 3} more lines)")
                    else:
                        print(f"    Text: (empty)")
                else:
                    print(f"    ✗ Error: {engine_result.get('error', 'Unknown')}")
    
    # Final recommendation
    print(f"\n{'='*70}")
    print(f"🎯 RECOMMENDATION")
    print(f"{'='*70}")
    
    best_combo = None
    best_score = -1
    
    for result in all_results:
        for engine in ['tesseract', 'paddle']:
            if engine in result and result[engine].get('success'):
                text_len = len(result[engine].get('text_clean', ''))
                confidence = result[engine].get('confidence', 0.8)  # Tesseract gets default 0.8
                score = text_len * confidence
                
                if score > best_score:
                    best_score = score
                    best_combo = {
                        'crop': result['crop_method'],
                        'engine': engine,
                        'text': result[engine]['text_clean'],
                        'time_ms': result[engine]['time_ms'],
                        'confidence': confidence,
                    }
    
    if best_combo:
        print(f"Best combination: {best_combo['crop'].upper()} crop + {best_combo['engine'].capitalize()}")
        print(f"  Score: {best_score:.1f} (text_length × confidence)")
        print(f"  Time: {best_combo['time_ms']:.0f}ms")
        print(f"  Confidence: {best_combo['confidence']:.2%}")
    else:
        print(f"⚠️  No successful OCR results")
    
    return {
        'results': all_results,
        'language': detected_language,
        'best_combination': best_combo,
    }


def main():
    """Main entry point"""
    
    # Parse command-line arguments
    test_engines = 'both'
    debug_mode = False
    show_diagnostics = False
    image_path = None
    
    for arg in sys.argv[1:]:
        if arg == '--paddle-only':
            test_engines = 'paddle'
        elif arg == '--tesseract-only':
            test_engines = 'tesseract'
        elif arg == '--debug':
            debug_mode = True
        elif arg == '--diagnose':
            show_diagnostics = True
        elif arg in ['--help', '-h']:
            print(__doc__)
            print("\nOptions:")
            print("  --paddle-only      Test only PaddleOCR")
            print("  --tesseract-only   Test only Tesseract")
            print("  --debug            Extra debug output")
            print("  --diagnose         Show environment diagnostics only")
            return 0
        elif not arg.startswith('--') and image_path is None:
            image_path = arg
    
    # Show diagnostics if requested
    if show_diagnostics or debug_mode:
        diagnostics = diagnose_environment()
        if show_diagnostics and image_path is None:
            return 0
    
    # Single image mode
    if image_path:
        if not os.path.exists(image_path):
            print(f"❌ Error: Image not found: {image_path}")
            return 1
        
        # Always save crops for debugging
        result = test_ocr_on_image(image_path, save_crops=True, test_engines=test_engines)
        
        if result is None:
            return 1
        
        return 0
    
    # Batch mode - test all images in img/subt/
    script_dir = Path(__file__).parent
    subt_dir = script_dir / 'img' / 'subt'
    
    if not subt_dir.exists():
        print(f"❌ Error: Directory not found: {subt_dir}")
        print("Usage: python test_ocr.py [image_path] [options]")
        print("Example: python test_ocr.py img/subt/subtitles.jpg")
        print("         python test_ocr.py img/subt/subtitles.jpg --paddle-only")
        print("         python test_ocr.py --diagnose")
        return 1
    
    # Find all images directly in subt/ (not in subdirectories)
    image_files = sorted(subt_dir.glob('*.jpg'))
    # Filter out crop images and any that contain "_crop" in name
    image_files = [f for f in image_files if '_crop' not in f.stem]
    
    if not image_files:
        print(f"❌ Error: No .jpg images found in {subt_dir}")
        return 1
    
    print("\n" + "="*70)
    print("🧪 OCR COMPARISON TEST - BATCH MODE")
    print("="*70)
    print(f"Testing {len(image_files)} images from {subt_dir}")
    print(f"\nEngines: {test_engines.upper()}")
    print(f"Crop methods: Smart (if available) + Safe area")
    print("="*70)
    
    # Test each image
    results = []
    for img_path in image_files:
        result = test_ocr_on_image(str(img_path), save_crops=True, test_engines=test_engines)
        if result:
            results.append({
                'name': img_path.name,
                'result': result
            })
    
    # Summary
    print("\n" + "="*70)
    print("📊 BATCH SUMMARY")
    print("="*70)
    
    total_images = len(results)
    successful_tests = len([r for r in results if r['result'].get('best_combination')])
    
    print(f"\nTotal images tested: {total_images}")
    print(f"Successful extractions: {successful_tests}")
    print(f"Failed extractions: {total_images - successful_tests}")
    
    # Best combinations per image
    print(f"\n🏆 Best Results Per Image:")
    for r in results:
        best = r['result'].get('best_combination')
        if best:
            text_preview = best['text'].split('\n')[0][:40]
            print(f"  • {r['name']:<30} {best['crop'].upper():>5} + {best['engine'].capitalize():<10} ({best['time_ms']:.0f}ms)")
            print(f"    \"{text_preview}{'...' if len(best['text']) > 40 else ''}\"")
        else:
            print(f"  • {r['name']:<30} NO TEXT EXTRACTED")
    
    # Engine comparison
    if test_engines == 'both':
        print(f"\n📈 Engine Comparison:")
        tess_wins = 0
        paddle_wins = 0
        
        for r in results:
            best = r['result'].get('best_combination')
            if best:
                if best['engine'] == 'tesseract':
                    tess_wins += 1
                elif best['engine'] == 'paddle':
                    paddle_wins += 1
        
        print(f"  Tesseract best: {tess_wins} images")
        print(f"  PaddleOCR best: {paddle_wins} images")
        
        if tess_wins + paddle_wins > 0:
            tess_pct = tess_wins / (tess_wins + paddle_wins) * 100
            paddle_pct = paddle_wins / (tess_wins + paddle_wins) * 100
            print(f"  Winner: {'Tesseract' if tess_wins > paddle_wins else 'PaddleOCR' if paddle_wins > tess_wins else 'TIE'}")
    
    print(f"\n🔍 Debug crops saved in: {subt_dir}/")
    print(f"✅ Test complete!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

