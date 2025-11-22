"""
Text Helpers

Simple text processing helpers for 3 core operations:
1. Detect text from image in area
2. Wait for text to appear  
3. Wait for text to disappear

Includes: crop, filter (greyscale/binary), OCR, language detection
"""

import os
import requests
import tempfile
import json
import time
import cv2
import numpy as np
import subprocess
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse


class TextHelpers:
    """Simple text processing helpers for core operations."""
    
    def __init__(self, captures_path: str):
        """Initialize text helpers with captures path."""
        self.captures_path = captures_path
        
    def download_image(self, source_url: str) -> str:
        """Download image from URL only."""
        try:
            response = requests.get(source_url, timeout=30)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp.write(response.content)
                return tmp.name
                
        except Exception as e:
            print(f"[@text_helpers] Error downloading image from URL: {e}")
            raise
    
    def save_text_reference(self, text: str, reference_name: str, userinterface_name: str, team_id: str,
                           area: Dict[str, Any] = None) -> Dict[str, Any]:
        """Save text reference to database."""
        try:
            print(f"[@text_helpers] Saving text reference to database: {reference_name} for userinterface: {userinterface_name}")
            
            # Round all area coordinates to integers (pixels should always be integers)
            if area:
                area = {k: round(v) if isinstance(v, (int, float)) else v for k, v in area.items()}
                print(f"[@text_helpers] Rounded area coordinates: {area}")
            
            # Save reference to database
            from shared.src.lib.database.verifications_references_db import save_reference
            
            # Create text data structure and merge with area
            text_data = {
                'text': text
            }
            
            # Merge text data with existing area data
            extended_area = {**(area or {}), **text_data}
            
            db_result = save_reference(
                name=reference_name,
                userinterface_name=userinterface_name,
                reference_type='reference_text',
                team_id=team_id,
                r2_path=f'text-references/{userinterface_name}/{reference_name}',
                r2_url='',  # Empty URL for text references
                area=extended_area  # Store text data in area field
            )
            
            if not db_result.get('success'):
                return {
                    'success': False,
                    'error': f"Database save failed: {db_result.get('error')}"
                }
            
            print(f"[@text_helpers] Successfully saved text reference to database: {reference_name}")
            
            return {
                'success': True,
                'reference_name': reference_name,
                'reference_id': db_result.get('reference_id'),
                'text_data': text_data
            }
            
        except Exception as e:
            print(f"[@text_helpers] Error saving text reference: {e}")
            return {'success': False, 'error': str(e)}
    
    def detect_text_in_area(self, image_path: str, area: dict = None, use_advanced_ocr: bool = False) -> Dict[str, Any]:
        """
        Core function: Detect text from image in area.
        1. Crop to area (if specified)
        2. Apply filters (greyscale + binary) 
        3. OCR text extraction
        4. Language detection
        
        Args:
            image_path: Path to the image file
            area: Optional area dict to crop
            use_advanced_ocr: If True, use multi-approach OCR (for getMenuInfo). If False, use simple OCR (for regular text verification)
        """
        try:
            if not os.path.exists(image_path):
                return {'extracted_text': '', 'error': 'Image not found', 'image_textdetected_path': ''}
            
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return {'extracted_text': '', 'error': 'Failed to load image', 'image_textdetected_path': ''}
            
            # Step 1: Crop to area if specified
            if area:
                x, y = int(area['x']), int(area['y'])
                w, h = int(area['width']), int(area['height'])
                
                img_height, img_width = img.shape[:2]
                if x < 0 or y < 0 or x + w > img_width or y + h > img_height:
                    return {'extracted_text': '', 'error': 'Area out of bounds', 'image_textdetected_path': ''}
                
                img = img[y:y+h, x:x+w]
            
            # Step 2: Apply filters for better OCR
            # Convert to greyscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            timestamp = int(time.time())
            
            # Save processed image path
            processed_filename = f'text_detection_{timestamp}.png'
            processed_path = os.path.join(self.captures_path, processed_filename)
            cv2.imwrite(processed_path, img)
            
            # Step 3: OCR text extraction
            if use_advanced_ocr:
                # ADVANCED OCR: Multi-approach for difficult text (getMenuInfo)
                print(f"[@text_helpers:OCR] Using ADVANCED multi-approach OCR")
                
                # Save grayscale for debugging
                gray_filename = f'text_detection_{timestamp}_gray.png'
                gray_path = os.path.join(self.captures_path, gray_filename)
                cv2.imwrite(gray_path, gray)
                print(f"[@text_helpers:OCR] Saved grayscale image: {gray_filename}")
                
                # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                
                # Save enhanced image
                enhanced_filename = f'text_detection_{timestamp}_enhanced.png'
                enhanced_path = os.path.join(self.captures_path, enhanced_filename)
                cv2.imwrite(enhanced_path, enhanced)
                print(f"[@text_helpers:OCR] Saved contrast-enhanced image: {enhanced_filename}")
                # Try multiple preprocessing approaches
                binary_adaptive = cv2.adaptiveThreshold(
                    enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )
                _, binary_otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                _, binary_otsu_inv = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                
                # Save preprocessed versions
                adaptive_filename = f'text_detection_{timestamp}_adaptive.png'
                otsu_filename = f'text_detection_{timestamp}_otsu.png'
                otsu_inv_filename = f'text_detection_{timestamp}_otsu_inv.png'
                
                cv2.imwrite(os.path.join(self.captures_path, adaptive_filename), binary_adaptive)
                cv2.imwrite(os.path.join(self.captures_path, otsu_filename), binary_otsu)
                cv2.imwrite(os.path.join(self.captures_path, otsu_inv_filename), binary_otsu_inv)
                
                print(f"[@text_helpers:OCR] Saved preprocessed images: {adaptive_filename}, {otsu_filename}, {otsu_inv_filename}")
                
                # Try OCR with multiple approaches
                ocr_results = []
                for name, binary_img in [
                    ('adaptive', binary_adaptive),
                    ('otsu', binary_otsu),
                    ('otsu_inv', binary_otsu_inv),
                    ('enhanced', enhanced),
                    ('grayscale', gray)
                ]:
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        cv2.imwrite(tmp.name, binary_img)
                        ocr_temp_path = tmp.name
                    
                    result = subprocess.run(
                        ['tesseract', ocr_temp_path, 'stdout'],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    text = result.stdout.strip() if result.returncode == 0 else ""
                    ocr_results.append({
                        'method': name,
                        'text': text,
                        'length': len(text),
                        'word_count': len(text.split()) if text else 0
                    })
                    
                    try:
                        os.unlink(ocr_temp_path)
                    except:
                        pass
                
                # Pick the result with the most text
                best_result = max(ocr_results, key=lambda r: r['length'])
                extracted_text = best_result['text']
                
                print(f"[@text_helpers:OCR] Tried {len(ocr_results)} OCR approaches:")
                for r in ocr_results:
                    status = "✅ BEST" if r['method'] == best_result['method'] else "  "
                    print(f"[@text_helpers:OCR]   {status} {r['method']:12s}: {r['length']:4d} chars, {r['word_count']:3d} words")
                
                print(f"[@text_helpers:OCR] Selected best result from '{best_result['method']}' method")
                print(f"[@text_helpers:OCR] >>> {extracted_text[:200]}")
                
            else:
                # SIMPLE OCR: Fast and reliable for regular text verification (waitForTextToAppear/Disappear)
                print(f"[@text_helpers:OCR] Using SIMPLE binary threshold OCR")
                
                # Apply simple binarization (old algorithm - works great for regular text)
                _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                
                # Use the binary filtered version for OCR
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    cv2.imwrite(tmp.name, binary)
                    ocr_temp_path = tmp.name
                
                result = subprocess.run(
                    ['tesseract', ocr_temp_path, 'stdout'],
                    capture_output=True, text=True, timeout=30
                )
                
                extracted_text = result.stdout.strip() if result.returncode == 0 else ""
                
                try:
                    os.unlink(ocr_temp_path)
                except:
                    pass
                
                print(f"[@text_helpers:OCR] Extracted: '{extracted_text.strip()}'")
            
            # Step 4: Language detection (simple)
            language = self.detect_language(extracted_text) if extracted_text else 'en'
            
            return {
                'extracted_text': extracted_text,
                'character_count': len(extracted_text),
                'word_count': len(extracted_text.split()) if extracted_text else 0,
                'language': language,
                'area': area,
                'image_textdetected_path': processed_path
            }
            
        except Exception as e:
            return {'extracted_text': '', 'error': str(e), 'image_textdetected_path': ''}
    
    def detect_language(self, text: str) -> str:
        """Simple language detection."""
        try:
            from langdetect import detect
            return detect(text) if len(text.strip()) > 3 else 'en'
        except:
            return 'en'
    
    def text_matches(self, extracted_text: str, target_text: str) -> bool:
        """Check if extracted text matches target text."""
        if not extracted_text or not target_text:
            return False
        
        extracted_clean = ' '.join(extracted_text.split()).lower()
        target_clean = ' '.join(target_text.split()).lower()
        
        return target_clean in extracted_clean
    
    def parse_menu_info(self, ocr_text: str) -> Dict[str, str]:
        """
        Parse key-value pairs from OCR text (menu format).
        
        Supports both horizontal and vertical layouts:
        
        HORIZONTAL (same line with delimiter):
        - "Serial Number: ABC123"
        - "MAC Address = 00:11:22:33:44:55"
        - "Firmware - 1.2.3"
        
        VERTICAL (consecutive lines):
        - Line 1: "APPLICATION VERSION"
        - Line 2: "67_2025102"
        
        Args:
            ocr_text: Raw OCR text from menu/info screen
            
        Returns:
            Dict with parsed key-value pairs (keys normalized to lowercase with underscores)
        """
        parsed_data = {}
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Try horizontal format first (key:value, key=value, key-value)
            found_horizontal = False
            for delimiter in [':', '=', '-']:
                if delimiter in line:
                    parts = line.split(delimiter, 1)
                    if len(parts) == 2:
                        key_raw = parts[0].strip()
                        value = parts[1].strip()
                        
                        # Validate: key should look like a label (contains letters, reasonable length)
                        if key_raw and value and any(c.isalpha() for c in key_raw) and len(key_raw) < 50:
                            key = key_raw.lower().replace(' ', '_').replace('(', '').replace(')', '')
                            parsed_data[key] = value
                            found_horizontal = True
                            break
            
            if found_horizontal:
                i += 1
                continue
            
            # Try vertical format (current line is key, next line is value)
            if i + 1 < len(lines):
                potential_key = line
                potential_value = lines[i + 1]
                
                # Heuristic: Key should contain letters and look like a label (all caps or title case)
                # Value should be different from key (not another label)
                is_key = (
                    any(c.isalpha() for c in potential_key) and
                    len(potential_key) < 50 and
                    (potential_key.isupper() or potential_key.istitle()) and
                    ':' not in potential_key and '=' not in potential_key  # No delimiters
                )
                
                # Value should be different from key
                # Fixed: Don't reject uppercase values - many serial numbers/versions are uppercase
                # Instead, reject if next line looks like another label (ends with VERSION, NUMBER, etc.)
                looks_like_label = (
                    potential_value.isupper() and 
                    any(potential_value.endswith(suffix) for suffix in ['VERSION', 'NUMBER', 'ADDRESS', 'NAME', 'INFO', 'STATUS', 'TYPE', 'MODE'])
                )
                
                is_value = (
                    potential_value and 
                    potential_value != potential_key and
                    not looks_like_label
                )
                
                if is_key and is_value:
                    key = potential_key.lower().replace(' ', '_').replace('(', '').replace(')', '')
                    value = potential_value
                    parsed_data[key] = value
                    i += 2  # Skip both key and value lines
                    continue
            
            # No pattern matched, skip this line
            i += 1
        
        return parsed_data

    def extract_full_ocr_dump(self, image_path: str, confidence_threshold: int = 30) -> list:
        """
        Extract ALL text from image with bounding boxes (like ADB dump for TV).
        
        Uses pytesseract.image_to_data() to get text with coordinates for each word/line.
        This is the TV equivalent of ADB dump - discovers all text elements with their areas.
        
        Args:
            image_path: Path to screenshot
            confidence_threshold: Minimum OCR confidence (0-100), default 30
            
        Returns:
            List of text elements with areas:
            [
                {'text': 'TV Guide', 'area': {'x': 50, 'y': 30, 'width': 300, 'height': 60}, 'confidence': 85},
                {'text': 'GOLF+', 'area': {'x': 100, 'y': 200, 'width': 150, 'height': 40}, 'confidence': 92},
                ...
            ]
        """
        try:
            print(f"[@text_helpers:extract_full_ocr_dump] Extracting OCR dump from: {image_path}")
            print(f"  🐛 DEBUG: confidence_threshold = {confidence_threshold}")
            
            if not os.path.exists(image_path):
                print(f"[@text_helpers:extract_full_ocr_dump] ERROR: Image not found at {image_path}")
                return []
            
            # Get file info
            file_size = os.path.getsize(image_path)
            print(f"  🐛 DEBUG: Image file size = {file_size} bytes")
            
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                print(f"[@text_helpers:extract_full_ocr_dump] ERROR: Failed to load image with cv2.imread")
                return []
            
            img_height, img_width = img.shape[:2]
            print(f"  🐛 DEBUG: Image dimensions = {img_width}x{img_height}")
            
            # Preprocess: Convert to grayscale and apply binary threshold
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            print(f"  🐛 DEBUG: Preprocessed image (grayscale + binary threshold)")
            
            # Save preprocessed image temporarily for pytesseract
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                cv2.imwrite(tmp.name, binary)
                temp_path = tmp.name
            
            try:
                # Use pytesseract.image_to_data to get bounding boxes
                # This returns a TSV string with columns: level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text
                result = subprocess.run(
                    ['tesseract', temp_path, 'stdout', '--psm', '11', 'tsv'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                print(f"  🐛 DEBUG: Tesseract returncode = {result.returncode}")
                
                if result.returncode != 0:
                    print(f"[@text_helpers:extract_full_ocr_dump] ERROR: Tesseract failed")
                    print(f"  🐛 DEBUG: stderr = {result.stderr}")
                    return []
                
                # Parse TSV output
                lines = result.stdout.strip().split('\n')
                print(f"  🐛 DEBUG: Tesseract output lines = {len(lines)} (including header)")
                
                if len(lines) < 2:  # Need header + at least 1 data row
                    print(f"[@text_helpers:extract_full_ocr_dump] No text detected by Tesseract")
                    print(f"  🐛 DEBUG: Output was: {result.stdout[:500]}")  # First 500 chars
                    return []
                
                # Parse header to get column indices
                header = lines[0].split('\t')
                print(f"  🐛 DEBUG: TSV header columns = {header}")
                
                elements = []
                total_detected = 0
                filtered_by_empty = 0
                filtered_by_confidence = 0
                filtered_by_invalid_box = 0
                
                # Process each line (skip header)
                for line in lines[1:]:
                    cols = line.split('\t')
                    if len(cols) < len(header):
                        continue
                    
                    # Extract values by column name
                    data = dict(zip(header, cols))
                    
                    text = data.get('text', '').strip()
                    conf = data.get('conf', '-1')
                    
                    total_detected += 1
                    
                    # Skip empty text or low confidence
                    if not text or conf == '-1':
                        filtered_by_empty += 1
                        continue
                    
                    try:
                        confidence = int(conf)
                        if confidence < confidence_threshold:
                            filtered_by_confidence += 1
                            if len(elements) < 10:  # Log first 10 filtered for debugging
                                print(f"    🐛 DEBUG: Filtered (conf={confidence}): '{text}'")
                            continue
                    except ValueError:
                        filtered_by_confidence += 1
                        continue
                    
                    # Get bounding box
                    try:
                        left = int(data.get('left', 0))
                        top = int(data.get('top', 0))
                        width = int(data.get('width', 0))
                        height = int(data.get('height', 0))
                    except ValueError:
                        continue
                    
                    # Skip invalid boxes
                    if width <= 0 or height <= 0:
                        filtered_by_invalid_box += 1
                        continue
                    
                    elements.append({
                        'text': text,
                        'area': {
                            'x': left,
                            'y': top,
                            'width': width,
                            'height': height
                        },
                        'confidence': confidence
                    })
                
                print(f"\n  🐛 DEBUG: OCR Processing Summary")
                print(f"     Total detected by Tesseract: {total_detected}")
                print(f"     Filtered (empty/no-conf): {filtered_by_empty}")
                print(f"     Filtered (confidence < {confidence_threshold}): {filtered_by_confidence}")
                print(f"     Filtered (invalid box): {filtered_by_invalid_box}")
                print(f"     ✅ Valid elements: {len(elements)}")
                
                print(f"[@text_helpers:extract_full_ocr_dump] Extracted {len(elements)} text elements (confidence >= {confidence_threshold})")
                
                # Show first few valid elements
                if elements:
                    print(f"  🐛 DEBUG: Sample elements (showing first {min(5, len(elements))}):")
                    for elem in elements[:5]:
                        print(f"    - '{elem['text']}' (conf={elem['confidence']}) at ({elem['area']['x']}, {elem['area']['y']})")
                
                # Group nearby words into phrases (combine words on same line)
                if elements:
                    grouped_elements = self._group_text_elements(elements)
                    print(f"[@text_helpers:extract_full_ocr_dump] Grouped into {len(grouped_elements)} phrases")
                    if grouped_elements:
                        print(f"  🐛 DEBUG: Sample grouped phrases (showing first {min(3, len(grouped_elements))}):")
                        for phrase in grouped_elements[:3]:
                            print(f"    - '{phrase['text']}' (conf={phrase['confidence']})")
                    return grouped_elements
                
                print(f"  🐛 DEBUG: ⚠️ No valid elements passed all filters!")
                return elements
                
            finally:
                # Cleanup temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[@text_helpers:extract_full_ocr_dump] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _group_text_elements(self, elements: list) -> list:
        """
        Group nearby text elements into phrases (combine words on same line).
        
        Args:
            elements: List of individual word elements
            
        Returns:
            List of grouped phrase elements
        """
        if not elements:
            return []
        
        # Sort by vertical position (top), then horizontal (left)
        sorted_elements = sorted(elements, key=lambda e: (e['area']['y'], e['area']['x']))
        
        grouped = []
        current_group = None
        
        for elem in sorted_elements:
            if current_group is None:
                # Start new group
                current_group = {
                    'text': elem['text'],
                    'area': elem['area'].copy(),
                    'confidence': elem['confidence'],
                    'word_count': 1
                }
            else:
                # Check if this element is on the same line (similar y position)
                y_diff = abs(elem['area']['y'] - current_group['area']['y'])
                height_avg = (elem['area']['height'] + current_group['area']['height']) / 2
                
                # Also check horizontal proximity
                current_right = current_group['area']['x'] + current_group['area']['width']
                elem_left = elem['area']['x']
                x_gap = elem_left - current_right
                
                # If on same line (y_diff < half height) and close horizontally (gap < 2x height)
                if y_diff < height_avg * 0.5 and x_gap < height_avg * 2:
                    # Merge into current group
                    current_group['text'] += ' ' + elem['text']
                    
                    # Expand bounding box to include new element
                    new_right = elem['area']['x'] + elem['area']['width']
                    current_right = current_group['area']['x'] + current_group['area']['width']
                    
                    current_group['area']['width'] = max(new_right, current_right) - current_group['area']['x']
                    current_group['area']['height'] = max(
                        current_group['area']['height'],
                        elem['area']['y'] + elem['area']['height'] - current_group['area']['y']
                    )
                    
                    # Average confidence
                    current_group['confidence'] = int(
                        (current_group['confidence'] * current_group['word_count'] + elem['confidence']) / 
                        (current_group['word_count'] + 1)
                    )
                    current_group['word_count'] += 1
                else:
                    # Save current group and start new one
                    grouped.append({
                        'text': current_group['text'],
                        'area': current_group['area'],
                        'confidence': current_group['confidence']
                    })
                    
                    current_group = {
                        'text': elem['text'],
                        'area': elem['area'].copy(),
                        'confidence': elem['confidence'],
                        'word_count': 1
                    }
        
        # Don't forget the last group
        if current_group:
            grouped.append({
                'text': current_group['text'],
                'area': current_group['area'],
                'confidence': current_group['confidence']
            })
        
        return grouped

 