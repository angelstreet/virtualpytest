"""
Image Helpers

Core image processing helpers for 3 main operations:
1. Template matching (image verification)
2. Crop image to area
3. Process image (filters, background removal) 
4. Save/download images

Includes: template matching, cropping, filtering, background removal, URL downloading
"""

import os
import requests
import tempfile
import time
import cv2
import numpy as np
import shutil
import subprocess
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse


class ImageHelpers:
    """Core image processing helpers for verification operations."""
    
    def __init__(self, captures_path: str, av_controller):
        """Initialize image helpers with captures path and AV controller."""
        self.captures_path = captures_path
        self.av_controller = av_controller
    
    def round_area_coordinates(self, area: Dict[str, Any], max_decimals: int = 2) -> Dict[str, Any]:
        """
        Round area coordinates to specified decimal places.
        
        Args:
            area: Area dictionary with coordinates
            max_decimals: Maximum decimal places (default: 2)
        
        Returns:
            Area dict with rounded coordinates
        """
        if not area:
            return area
        
        rounded_area = {}
        for key, value in area.items():
            if isinstance(value, (int, float)):
                # Round to max_decimals places
                rounded_area[key] = round(value, max_decimals)
            else:
                rounded_area[key] = value
        
        return rounded_area
       
    def download_image(self, source_url: str) -> str:
        """Download image from URL only."""
        try:
            response = requests.get(source_url, timeout=30)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp.write(response.content)
                return tmp.name
                
        except Exception as e:
            print(f"[@image_helpers] Error downloading image from URL: {e}")
            raise
    
    def save_image_reference(self, image_path: str, reference_name: str, userinterface_name: str, team_id: str, area: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Save image reference with R2 upload and database save.
        
        Args:
            image_path: Local path to the image file
            reference_name: Name of the reference
            userinterface_name: Name of the user interface (e.g., 'horizon_android_mobile')
            team_id: Team ID
            area: Optional area definition
        
        Returns:
            Dict with success status and details
        """
        try:
            print(f"[@image_helpers] Uploading reference to R2: {reference_name} for userinterface: {userinterface_name}")
            
            # Round all area coordinates to 2 decimal places (max precision needed)
            if area:
                area = self.round_area_coordinates(area, max_decimals=2)
                print(f"[@image_helpers] Rounded area coordinates (2 decimals): {area}")
            
            # Upload to R2 using cloudflare utils
            from shared.src.lib.utils.cloudflare_utils import upload_reference_image
            
            # Use reference name with .jpg extension for R2
            r2_filename = f"{reference_name}.jpg"
            upload_result = upload_reference_image(image_path, userinterface_name, r2_filename)
            
            if not upload_result.get('success'):
                return {
                    'success': False,
                    'error': f"R2 upload failed: {upload_result.get('error')}"
                }
            
            r2_url = upload_result.get('url', '')
            r2_path = upload_result.get('remote_path', '')
            
            print(f"[@image_helpers] Successfully uploaded to R2: {r2_url}")
            
            # Upload filtered versions to R2
            import os
            base_path, ext = os.path.splitext(image_path)
            
            # Upload greyscale version
            greyscale_path = f"{base_path}_greyscale{ext}"
            if os.path.exists(greyscale_path):
                greyscale_filename = f"{reference_name}_greyscale.jpg"
                upload_reference_image(greyscale_path, userinterface_name, greyscale_filename)
            
            # Upload binary version
            binary_path = f"{base_path}_binary{ext}"
            if os.path.exists(binary_path):
                binary_filename = f"{reference_name}_binary.jpg"
                upload_reference_image(binary_path, userinterface_name, binary_filename)
            
            # Save reference to database
            from shared.src.lib.database.verifications_references_db import save_reference
            
            db_result = save_reference(
                name=reference_name,
                userinterface_name=userinterface_name,
                reference_type='reference_image',
                team_id=team_id,
                r2_path=r2_path,
                r2_url=r2_url,
                area=area
            )
            
            if not db_result.get('success'):
                return {
                    'success': False,
                    'error': f"Database save failed: {db_result.get('error')}"
                }
            
            print(f"[@image_helpers] Successfully saved reference to database: {reference_name}")
            
            return {
                'success': True,
                'reference_name': reference_name,
                'r2_url': r2_url,
                'r2_path': r2_path,
                'reference_id': db_result.get('reference_id')
            }
            
        except Exception as e:
            print(f"[@image_helpers] Error saving image reference: {e}")
            return {'success': False, 'error': str(e)}
    
    # =============================================================================
    # Core Operation 1: Template Matching
    # =============================================================================
    
    def match_template_in_area(self, image_source_path: str, template_path: str, 
                              area: Dict[str, Any] = None, threshold: float = 0.8) -> Dict[str, Any]:
        try:
            source_img = cv2.imread(image_source_path)
            template_img = cv2.imread(template_path)
            
            if source_img is None or template_img is None:
                return {'found': False, 'error': 'Failed to load images', 'confidence': 0.0}
            
            if area:
                x, y = int(area['x']), int(area['y'])
                width, height = int(area['width']), int(area['height'])
                
                src_height, src_width = source_img.shape[:2]
                if x < 0 or y < 0 or x + width > src_width or y + height > src_height:
                    return {'found': False, 'error': 'Search area out of bounds', 'confidence': 0.0}
                
                search_area = source_img[y:y+height, x:x+width]
                offset_x, offset_y = x, y
            else:
                search_area = source_img
                offset_x, offset_y = 0, 0
            
            result = cv2.matchTemplate(search_area, template_img, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            found = max_val >= threshold
            
            if found:
                match_x = offset_x + max_loc[0]
                match_y = offset_y + max_loc[1]
                template_height, template_width = template_img.shape[:2]
                
                return {
                    'found': True,
                    'confidence': float(max_val),
                    'location': {
                        'x': match_x,
                        'y': match_y,
                        'width': template_width,
                        'height': template_height
                    },
                    'center': {
                        'x': match_x + template_width // 2,
                        'y': match_y + template_height // 2
                    }
                }
            else:
                return {'found': False, 'confidence': float(max_val), 'threshold': threshold}
                
        except Exception as e:
            return {'found': False, 'error': f'Matching error: {str(e)}', 'confidence': 0.0}

    def smart_fuzzy_search(self, source_img: np.ndarray, reference_img: np.ndarray, 
                          exact_area: Dict[str, Any], fuzzy_area: Dict[str, Any], 
                          threshold: float = 0.8) -> Tuple[bool, float, Optional[Dict[str, int]]]:
        """
        Simple fuzzy search using OpenCV's matchTemplate.
        OpenCV automatically searches the ENTIRE fuzzy area for best match - no need for manual iterations!
        
        Strategy:
        1. Try exact position first (fast path)
        2. If no match, search entire fuzzy area in one OpenCV call
        """
        try:
            ref_h, ref_w = reference_img.shape[:2]
            ex, ey = int(exact_area['x']), int(exact_area['y'])
            ew, eh = int(exact_area['width']), int(exact_area['height'])
            fx, fy = int(fuzzy_area['fx']), int(fuzzy_area['fy'])
            fw, fh = int(fuzzy_area['fwidth']), int(fuzzy_area['fheight'])
            
            # For very small images (< 200 pixels), use pixel-based matching instead of template matching
            # Template matching is unreliable for tiny images due to normalization sensitivity
            ref_area = ref_h * ref_w
            use_pixel_matching = ref_area < 200
            
            if use_pixel_matching:
                print(f"[@fuzzy] Using PIXEL matching for small image ({ref_area}px < 200px threshold)")
            
            print(f"[@fuzzy] Starting fuzzy search - ref size: {ref_w}x{ref_h}, exact: ({ex},{ey}) {ew}x{eh}, fuzzy: ({fx},{fy}) {fw}x{fh}, threshold: {threshold}")
            
            # Step 1: Try exact position first (fast path optimization)
            exact_confidence = 0.0
            exact_region = source_img[ey:ey+eh, ex:ex+ew]
            if exact_region.shape[:2] == (eh, ew):
                if use_pixel_matching:
                    exact_confidence = self._pixel_match_score(exact_region, reference_img)
                else:
                    result = cv2.matchTemplate(exact_region, reference_img, cv2.TM_CCOEFF_NORMED)
                    exact_confidence = float(result[0][0])
                
                print(f"[@fuzzy] Exact position confidence: {exact_confidence:.3f}")
                if exact_confidence >= threshold:
                    print(f"[@fuzzy] ✓ Exact match found: {exact_confidence:.3f}")
                    return True, exact_confidence, {'x': ex, 'y': ey, 'width': ref_w, 'height': ref_h}
            
            # Step 2: Search entire fuzzy area (OpenCV does the sliding window for us!)
            print(f"[@fuzzy] Searching entire fuzzy area...")
            search_region = source_img[fy:fy+fh, fx:fx+fw]
            
            if search_region.shape[0] < ref_h or search_region.shape[1] < ref_w:
                print(f"[@fuzzy] ✗ Search region {search_region.shape} too small for template {ref_h}x{ref_w}")
                return False, exact_confidence, {'x': ex, 'y': ey, 'width': ref_w, 'height': ref_h}
            
            if use_pixel_matching:
                # Use sliding window with pixel matching for small images
                max_val = 0.0
                max_loc = (0, 0)
                for y in range(search_region.shape[0] - ref_h + 1):
                    for x in range(search_region.shape[1] - ref_w + 1):
                        region = search_region[y:y+ref_h, x:x+ref_w]
                        score = self._pixel_match_score(region, reference_img)
                        if score > max_val:
                            max_val = score
                            max_loc = (x, y)
            else:
                # OpenCV automatically searches ENTIRE region - this is the standard approach!
                result = cv2.matchTemplate(search_region, reference_img, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # Convert match location back to full image coordinates
            match_x = fx + max_loc[0]
            match_y = fy + max_loc[1]
            best_location = {'x': match_x, 'y': match_y, 'width': ref_w, 'height': ref_h}
            
            print(f"[@fuzzy] Best match in fuzzy area: confidence={max_val:.3f}, location=({match_x},{match_y})")
            
            found = max_val >= threshold
            if found:
                print(f"[@fuzzy] ✓ Match found in fuzzy area: {max_val:.3f}")
            else:
                print(f"[@fuzzy] ✗ No match found. Best confidence: {max_val:.3f} (required: {threshold:.3f})")
            
            return found, max_val, best_location
            
        except Exception as e:
            print(f"[@fuzzy] ERROR: Fuzzy search crashed: {e}")
            import traceback
            traceback.print_exc()
            return False, 0.0, None

    def _pixel_match_score(self, source_region: np.ndarray, reference_img: np.ndarray) -> float:
        """
        Calculate pixel-based matching score (0.0 to 1.0).
        More reliable than template matching for very small images.
        Uses the same logic as the overlay visualization.
        """
        try:
            # Ensure same dimensions
            if source_region.shape != reference_img.shape:
                return 0.0
            
            # Convert to grayscale
            source_gray = cv2.cvtColor(source_region, cv2.COLOR_BGR2GRAY)
            ref_gray = cv2.cvtColor(reference_img, cv2.COLOR_BGR2GRAY)
            
            # Calculate absolute difference
            diff = cv2.absdiff(source_gray, ref_gray)
            
            # Count matching pixels (difference <= 10)
            matching_pixels = np.sum(diff <= 10)
            total_pixels = source_gray.shape[0] * source_gray.shape[1]
            
            return matching_pixels / total_pixels
        except Exception as e:
            print(f"[@fuzzy] Pixel match error: {e}")
            return 0.0


    # =============================================================================
    # Core Operation 2: Image Cropping
    # =============================================================================
    
    def crop_image_to_area(self, image_source_path: str, image_cropped_path: str, area: Dict[str, Any]) -> bool:
        """
        Core function: Crop image to specific area.
        1. Load source image
        2. Validate area bounds
        3. Crop and save to target path
        """
        try:
            if not os.path.exists(image_source_path):
                print(f"[@image_helpers] Source image not found: {image_source_path}")
                return False
            
            if not self.validate_area(area):
                print(f"[@image_helpers] Invalid area coordinates: {area}")
                return False
            
            # Load image
            img = cv2.imread(image_source_path)
            if img is None:
                print(f"[@image_helpers] Failed to load image: {image_source_path}")
                return False
            
            # Extract coordinates
            x = int(area['x'])
            y = int(area['y'])
            width = int(area['width'])
            height = int(area['height'])
            
            # Validate bounds
            img_height, img_width = img.shape[:2]
            if x < 0 or y < 0 or x + width > img_width or y + height > img_height:
                print(f"[@image_helpers] Crop area out of bounds: {area} for image {img_width}x{img_height}")
                return False
            
            # Crop image
            cropped_img = img[y:y+height, x:x+width]
            
            # Save cropped image
            success = cv2.imwrite(image_cropped_path, cropped_img)
            if success:
                print(f"[@image_helpers] Successfully cropped image: {image_cropped_path}")
                return True
            else:
                print(f"[@image_helpers] Failed to save cropped image: {image_cropped_path}")
                return False
                
        except Exception as e:
            print(f"[@image_helpers] Error cropping image: {e}")
            return False
    
    # =============================================================================
    # Core Operation 3: Image Processing (Filters)
    # =============================================================================
    
    def apply_image_filter(self, image_path: str, filter_type: str) -> bool:
        """
        Core function: Apply image filter.
        1. Load image
        2. Apply filter (greyscale/binary)
        3. Save filtered image
        """
        try:
            if filter_type == 'none' or not filter_type:
                return True  # No filtering needed
                
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                print(f"[@image_helpers] Failed to load image for filtering: {image_path}")
                return False
            
            if filter_type == 'greyscale':
                # Convert to grayscale
                processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # Convert back to 3-channel for consistent format
                processed_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)
                
            elif filter_type == 'binary':
                # Convert to grayscale first
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # Apply binary threshold
                _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                # Convert back to 3-channel
                processed_img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
                
            else:
                print(f"[@image_helpers] Unknown filter type: {filter_type}")
                return False
            
            # Save processed image
            success = cv2.imwrite(image_path, processed_img)
            if success:
                print(f"[@image_helpers] Applied {filter_type} filter to: {image_path}")
            else:
                print(f"[@image_helpers] Failed to save filtered image: {image_path}")
            
            return success
            
        except Exception as e:
            print(f"[@image_helpers] Error applying filter: {e}")
            return False
    
    def remove_background(self, image_path: str, method: str = 'opencv') -> bool:
        """
        Core function: Remove background from image.
        1. Load image
        2. Apply background removal (opencv or rembg)
        3. Save processed image
        """
        try:
            if not os.path.exists(image_path):
                print(f"[@image_helpers] Image not found for background removal: {image_path}")
                return False
            
            if method == 'opencv':
                return self._remove_background_opencv(image_path)
            elif method == 'rembg':
                return self._remove_background_rembg(image_path)
            else:
                print(f"[@image_helpers] Unknown background removal method: {method}")
                return False
                
        except Exception as e:
            print(f"[@image_helpers] Error in background removal: {e}")
            return False
    
    def _remove_background_opencv(self, image_path: str) -> bool:
        """Remove background using OpenCV-based method."""
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return False
            
            # Convert to HSV for better color segmentation
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Create mask for background (assuming white/light background)
            lower_white = np.array([0, 0, 200])
            upper_white = np.array([180, 30, 255])
            mask = cv2.inRange(hsv, lower_white, upper_white)
            
            # Invert mask to get foreground
            mask_inv = cv2.bitwise_not(mask)
            
            # Apply mask
            result = cv2.bitwise_and(img, img, mask=mask_inv)
            
            # Make background transparent by converting to RGBA
            result_rgba = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
            result_rgba[:, :, 3] = mask_inv  # Set alpha channel
            
            # Save as PNG to preserve transparency
            success = cv2.imwrite(image_path, result_rgba)
            if success:
                print(f"[@image_helpers] Background removed using OpenCV: {image_path}")
            
            return success
            
        except Exception as e:
            print(f"[@image_helpers] OpenCV background removal error: {e}")
            return False
    
    def _remove_background_rembg(self, image_path: str) -> bool:
        """Remove background using rembg library."""
        try:
            # Use rembg command line tool
            output_path = f"{image_path}_nobg.png"
            result = subprocess.run(
                ['rembg', 'i', image_path, output_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                # Replace original with processed
                shutil.move(output_path, image_path)
                print(f"[@image_helpers] Background removed using rembg: {image_path}")
                return True
            else:
                print(f"[@image_helpers] rembg failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"[@image_helpers] rembg timeout for: {image_path}")
            return False
        except Exception as e:
            print(f"[@image_helpers] rembg error: {e}")
            return False
    
    # =============================================================================
    # Core Operation 4: Image Saving/Copying
    # =============================================================================
    
    def copy_image_file(self, image_source_path: str, image_target_path: str) -> bool:
        """
        Core function: Copy image file.
        1. Validate source exists
        2. Create target directory
        3. Copy file
        """
        try:
            if not os.path.exists(image_source_path):
                print(f"[@image_helpers] Source image not found: {image_source_path}")
                return False
            
            # Copy the image
            shutil.copy2(image_source_path, image_target_path)
            print(f"[@image_helpers] Copied image: {image_source_path} -> {image_target_path}")
            
            return True
            
        except Exception as e:
            print(f"[@image_helpers] Error copying image: {e}")
            return False
    
    def create_filtered_versions(self, image_path: str) -> None:
        """Create greyscale and binary versions of an image."""
        try:
            # Get base path and extension
            base_path, ext = os.path.splitext(image_path)
            
            # Create greyscale version
            greyscale_path = f"{base_path}_greyscale{ext}"
            shutil.copy2(image_path, greyscale_path)
            if self.apply_image_filter(greyscale_path, 'greyscale'):
                print(f"[@image_helpers] Created greyscale version: {greyscale_path}")
            
            # Create binary version
            binary_path = f"{base_path}_binary{ext}"
            shutil.copy2(image_path, binary_path)
            if self.apply_image_filter(binary_path, 'binary'):
                print(f"[@image_helpers] Created binary version: {binary_path}")
                
        except Exception as e:
            print(f"[@image_helpers] Error creating filtered versions: {e}")
    
    # =============================================================================
    # Utility Functions
    # =============================================================================
    
    def validate_area(self, area: Dict[str, Any]) -> bool:
        """Validate that area contains required coordinates."""
        if not area:
            return False
        required_keys = ['x', 'y', 'width', 'height']
        return all(key in area and isinstance(area[key], (int, float)) for key in required_keys)
    
    def get_unique_filename(self, base_name: str, extension: str = '.png') -> str:
        """Generate unique filename with timestamp."""
        timestamp = int(time.time() * 1000)
        return f"{base_name}_{timestamp}{extension}"
