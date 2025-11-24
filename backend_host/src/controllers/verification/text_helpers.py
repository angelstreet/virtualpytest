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
        """
        Check if extracted text matches target text.
        
        Normalizes both strings by:
        - Removing special characters (keeping only alphanumeric + spaces)
        - Normalizing whitespace
        - Converting to lowercase
        
        Examples:
        - "Movies Series" matches "Movies & Series" ✅
        - "Settings" matches "Settings!" ✅
        - "TV Guide" matches "TV - Guide" ✅
        """
        if not extracted_text or not target_text:
            return False
        
        import re
        
        # Remove all non-alphanumeric characters (except spaces)
        # This removes: &, @, !, ?, -, etc.
        extracted_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', extracted_text)
        target_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', target_text)
        
        # Normalize multiple spaces to single space and lowercase
        extracted_clean = ' '.join(extracted_clean.split()).lower()
        target_clean = ' '.join(target_clean.split()).lower()
        
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
        
        Results are SORTED BY FONT SIZE (largest first) - titles/headings appear first.
        This prioritizes larger, more prominent text for better verification matching.
        
        Args:
            image_path: Path to screenshot
            confidence_threshold: Minimum OCR confidence (0-100), default 30
            
        Returns:
            List of text elements with areas (sorted by font_size descending):
            [
                {'text': 'Rent', 'area': {...}, 'confidence': 95, 'font_size': 48},  # Title - largest
                {'text': 'Lassie 2 Ein neues Abenteuer', 'area': {...}, 'confidence': 85, 'font_size': 24},
                {'text': 'SD 2 days CHF 3.50', 'area': {...}, 'confidence': 92, 'font_size': 18},
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
                filtered_by_quality = 0  # Layer 1: OCR quality filter
                
                # 🐛 DEBUG: Log meaningful raw OCR results (skip empty text)
                print(f"\n  🐛 DEBUG: ===== RAW OCR RESULTS (BEFORE FILTERING) =====")
                print(f"  🐛 Total raw results: {len(lines)-1}")
                shown_count = 0
                for idx, line in enumerate(lines[1:], start=1):
                    cols = line.split('\t')
                    if len(cols) >= len(header):
                        data = dict(zip(header, cols))
                        text = data.get('text', '').strip()
                        conf = data.get('conf', '-1')
                        
                        # ✅ Only show non-empty text entries
                        if text:
                            left = data.get('left', '?')
                            top = data.get('top', '?')
                            width = data.get('width', '?')
                            height = data.get('height', '?')
                            print(f"  🐛 [{idx:3d}] text='{text}' conf={conf:>3s} box=({left},{top},{width}x{height})")
                            shown_count += 1
                
                empty_count = len(lines) - 1 - shown_count
                if empty_count > 0:
                    print(f"  🐛 (Skipped {empty_count} empty text entries)")
                print(f"  🐛 DEBUG: ===== END RAW OCR RESULTS ({shown_count} shown, {empty_count} empty) =====\n")
                
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
                        confidence = int(float(conf))
                        if confidence < confidence_threshold:
                            filtered_by_confidence += 1
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
                    
                    # ✅ LAYER 1: Filter garbage OCR text (TV-optimized)
                    if not self._is_valid_ocr_text_for_verification(text):
                        filtered_by_quality += 1
                        continue
                    
                    # Expand area for better verification matching (-5 x/y, +10 width/height)
                    expanded_x = max(0, left - 5)
                    expanded_y = max(0, top - 5)
                    expanded_width = width + 10
                    expanded_height = height + 10
                    
                    elements.append({
                        'text': text,
                        'area': {
                            'x': expanded_x,
                            'y': expanded_y,
                            'width': expanded_width,
                            'height': expanded_height
                        },
                        'confidence': confidence,
                        'font_size': height  # Use original height as font size proxy (larger = title/heading)
                    })
                
                print(f"\n  🐛 DEBUG: OCR Processing Summary")
                print(f"     Total detected by Tesseract: {total_detected}")
                print(f"     Filtered (empty/no-conf): {filtered_by_empty}")
                print(f"     Filtered (confidence < {confidence_threshold}): {filtered_by_confidence}")
                print(f"     Filtered (invalid box): {filtered_by_invalid_box}")
                print(f"     Filtered (quality - Layer 1): {filtered_by_quality}")
                print(f"     ✅ Valid elements: {len(elements)}")
                
                print(f"[@text_helpers:extract_full_ocr_dump] Extracted {len(elements)} text elements (confidence >= {confidence_threshold})")
                
                # Show ALL valid elements
                if elements:
                    print(f"  🐛 DEBUG: All valid elements ({len(elements)} total):")
                    for elem in elements:
                        print(f"    - '{elem['text']}' (conf={elem['confidence']}, size={elem.get('font_size', 0)}) at ({elem['area']['x']}, {elem['area']['y']})")
                
                # Group nearby words into phrases (combine words on same line)
                if elements:
                    grouped_elements = self._group_text_elements(elements)
                    print(f"[@text_helpers:extract_full_ocr_dump] Grouped into {len(grouped_elements)} phrases (sorted by font size)")
                    if grouped_elements:
                        print(f"  🐛 DEBUG: All grouped phrases ({len(grouped_elements)} total, sorted largest first):")
                        for phrase in grouped_elements:
                            print(f"    - '{phrase['text']}' (conf={phrase['confidence']}, size={phrase.get('font_size', 0)}) at ({phrase['area']['x']}, {phrase['area']['y']})")
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
    
    def _is_valid_ocr_text_for_verification(self, text: str) -> bool:
        """
        Filter garbage OCR text for verification quality (TV-optimized).
        
        Applies strict quality rules to ensure only meaningful text is used:
        - NOT checking min length here (done in Layer 2 after grouping)
        - Not all numeric (filters times like '12:20')
        - Not symbol-only (filters '@)', '®', '-~\.')
        - Not common UI indicators (filters 'HD', 'SD', 'OK', '4K')
        - Not single letter + punctuation (filters 'E.', 'H!')
        
        Args:
            text: Text to validate
            
        Returns:
            True if text is valid for verification, False if garbage
        """
        text_clean = text.strip()
        
        # 1. ✅ NO MINIMUM LENGTH CHECK - Let "TV" pass for grouping with "Guide"
        #    Layer 2 will filter standalone short words AFTER grouping
        
        # 2. All numeric (times, channel numbers)
        #    Filters: '12:20', '1:55', '123'
        if text_clean.replace(':', '').replace('.', '').replace(' ', '').isdigit():
            return False
        
        # 3. Symbol-only (UI icons misread as text)
        #    Filters: '@)', '-~\.', '®', '©'
        if not any(c.isalnum() for c in text_clean):
            return False
        
        # 4. Common UI indicators (too generic for verification)
        #    Filters: 'HD', 'SD', 'OK', '4K', 'UHD'
        common_ui = {'hd', 'sd', 'ok', '4k', 'uhd'}
        if text_clean.lower() in common_ui:
            return False
        
        # 5. Single letter + punctuation/symbol (OCR artifacts)
        #    Filters: 'E.', 'H!', 'A?', '@)'
        if len(text_clean) == 2:
            if text_clean[0].isalpha() and not text_clean[1].isalnum():
                return False
            if not text_clean[0].isalnum() and text_clean[1].isalpha():
                return False
        
        return True
    
    def _clean_grouped_text(self, text: str) -> str:
        """
        Clean special characters from grouped text.
        
        Removes special characters from start/end of each word:
        - 'Store) FEATURED (New Staging' → 'FEATURED New Staging'
        - '(New' → 'New'
        - 'Store)' → 'Store'
        - 'store"' → 'store'
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text with special chars removed, or empty string if nothing remains
        """
        words = text.split()
        cleaned_words = []
        
        for word in words:
            # Strip special chars from start/end: '(New' → 'New', 'Store)' → 'Store'
            cleaned = word.strip('()[]{}"\',.:;!?@#$%^&*_-+=~`|\\/<>')
            
            # Skip if nothing left after cleaning, or single letter
            if cleaned and len(cleaned) > 1:
                cleaned_words.append(cleaned)
        
        return ' '.join(cleaned_words)
    
    def _is_valid_grouped_phrase(self, text: str) -> bool:
        """
        Filter grouped phrases for verification quality (Layer 2).
        
        NOTE: Text should already be cleaned by _clean_grouped_text() before calling this.
        
        Filters:
        - Single letters: 'Q', 'E' → Invalid
        - Too short: 'TV', 'be' → Invalid (but 'TV Guide' → Valid)
        - Orphan letters: 'E Shared', 'Apps De' → Invalid
        
        Args:
            text: Cleaned grouped phrase to validate
            
        Returns:
            True if phrase is valid, False if likely grouping error
        """
        # First apply base quality check (no min length check there now)
        if not self._is_valid_ocr_text_for_verification(text):
            return False
        
        text_clean = text.strip()
        
        # ✅ Single letter (moved from Layer 1)
        # Filters: 'Q', 'E', 'T', 'A' - even with high confidence
        if len(text_clean) == 1:
            return False
        
        # ✅ Minimum 3 characters (moved from Layer 1)
        # Filters standalone short words: 'TV', 'Er', 'It', 'De', 'be'
        # But allows them in grouped phrases: 'TV Guide' ✅, 'Apple TV' ✅
        if len(text_clean) < 3:
            return False
        
        words = text_clean.split()
        
        # Single word: Already validated by min length above
        if len(words) == 1:
            return True
        
        # Multi-word phrase: Check for orphan single letters at start/end
        # Filters: 'E Shared', 'It Now', 'Settings E', 'Apps De'
        first_word = words[0]
        last_word = words[-1]
        
        # Orphan single letter at start
        if len(first_word) == 1 and first_word.isalpha():
            return False
        
        # Orphan single letter at end
        if len(last_word) == 1 and last_word.isalpha():
            return False
        
        return True
    
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
                    'font_size': elem.get('font_size', 0),  # Track font size (use max from group)
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
                    
                    # Use MAX font size from all words (important for titles with mixed sizes)
                    current_group['font_size'] = max(
                        current_group.get('font_size', 0),
                        elem.get('font_size', 0)
                    )
                    
                    current_group['word_count'] += 1
                else:
                    # ✅ LAYER 2: Save current group with cleaned text if it passes quality check
                    if current_group:
                        cleaned_text = self._clean_grouped_text(current_group['text'])
                        if cleaned_text and self._is_valid_grouped_phrase(cleaned_text):
                            grouped.append({
                                'text': cleaned_text,
                                'area': current_group['area'],
                                'confidence': current_group['confidence'],
                                'font_size': current_group.get('font_size', 0)
                            })
                    
                    current_group = {
                        'text': elem['text'],
                        'area': elem['area'].copy(),
                        'confidence': elem['confidence'],
                        'font_size': elem.get('font_size', 0),
                        'word_count': 1
                    }
        
        # ✅ LAYER 2: Don't forget the last group (with cleaned text and quality check)
        if current_group:
            cleaned_text = self._clean_grouped_text(current_group['text'])
            if cleaned_text and self._is_valid_grouped_phrase(cleaned_text):
                grouped.append({
                    'text': cleaned_text,
                    'area': current_group['area'],
                    'confidence': current_group['confidence'],
                    'font_size': current_group.get('font_size', 0)
                })
        
        # Sort by font_size (descending) - larger text (titles) comes first
        grouped.sort(key=lambda g: g.get('font_size', 0), reverse=True)
        
        return grouped

 