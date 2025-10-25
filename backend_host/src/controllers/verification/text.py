"""
Text Verification Controller

Clean text controller that uses helpers for all operations.
Provides route interfaces and core domain logic.
"""

import os
import re
import time
from typing import Dict, Any, Optional, Tuple, List
from .text_helpers import TextHelpers


class TextVerificationController:
    """Pure text verification controller that uses OCR to detect text on screen."""
    
    def __init__(self, av_controller, **kwargs):
        """
        Initialize the Text Verification controller.
        
        Args:
            av_controller: AV controller for capturing images (dependency injection)
        """
        # Dependency injection
        from shared.src.lib.utils.storage_path_utils import get_capture_storage_path
        
        self.av_controller = av_controller
        
        # Use centralized path resolution (handles hot/cold storage automatically)
        self.captures_path = get_capture_storage_path(av_controller.video_capture_path, 'captures')
        
        # Set verification type for controller lookup
        self.verification_type = 'text'
        
        # Initialize helpers
        self.helpers = TextHelpers(self.captures_path)

        print(f"[@controller:TextVerification] Initialized with captures path: {self.captures_path}")
        
        # Controller is always ready

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the text verification controller."""
        return {
            "connected": True,
            "av_controller": self.av_controller.device_name if self.av_controller else None,
            "controller_type": "text",
            "captures_path": self.captures_path
        }

    def waitForTextToAppear(self, text: str, timeout: float = 10.0, area: dict = None, 
                           image_list: List[str] = None, 
                           verification_index: int = 0, image_filter: str = 'none') -> Tuple[bool, str, dict]:
        """
        Wait for specific text to appear either in provided image list or by capturing new frames.
        
        Args:
            text: Text pattern to look for 
            timeout: Maximum time to wait in seconds  
            area: Optional area to search (x, y, width, height)
            image_list: Optional list of source image paths to search
            verification_index: Index of verification for naming
            image_filter: Optional image filter to apply
            
        Returns:
            Tuple of (success, message, additional_data)
        """
        # Check if text is provided
        if not text or text.strip() == '':
            error_msg = "No text specified. Please provide text to search for."
            print(f"[@controller:TextVerification] {error_msg}")
            return False, error_msg, {"searchedText": text or "", "image_filter": image_filter}
        
        # SAFEGUARD: Cap timeout at reasonable maximum (30 seconds) to prevent infinite waits
        if timeout > 30:
            print(f"[@controller:TextVerification] WARNING: Timeout {timeout}s exceeds maximum (30s), capping at 30s")
            timeout = 30
        
        print(f"[@controller:TextVerification] Looking for text pattern: '{text}'")
        if image_filter and image_filter != 'none':
            print(f"[@controller:TextVerification] Using image filter: {image_filter}")
        
        additional_data = {
            "searchedText": text,  # Frontend-expected property name
            "image_filter": image_filter
        }
        
        if image_list:
            # Expand image_list based on timeout
            images_to_check = image_list.copy()
            
            if timeout > 0 and len(image_list) == 1:
                fps = getattr(self.av_controller, 'screenshot_fps', 5)
                max_images = int(timeout * fps)
                wait_ms = int(1000 / fps)
                
                print(f"[@controller:TextVerification] Timeout {timeout}s: checking {max_images} images (wait: {wait_ms}ms)")
                
                base_path = image_list[0]
                for i in range(1, max_images):
                    next_path = self._get_next_capture(base_path, i)
                    if next_path:
                        images_to_check.append(next_path)
            
            print(f"[@controller:TextVerification] Searching in {len(images_to_check)} images")
            closest_text = ""
            best_source_path = None
            text_found = False
            wait_ms = int(1000 / getattr(self.av_controller, 'screenshot_fps', 5)) if timeout > 0 else 0
            
            for idx, source_path in enumerate(images_to_check):
                if idx > 0 and not os.path.exists(source_path):
                    if wait_ms > 0:
                        time.sleep(wait_ms / 1000.0)
                
                if not os.path.exists(source_path):
                    print(f"[@controller:TextVerification] Skip: {os.path.basename(source_path)}")
                    continue
                    
                # Extract text from area
                extracted_text = self._extract_text_from_area(source_path, area, image_filter)
                
                # Keep track of the longest extracted text as "closest"
                if len(extracted_text.strip()) > len(closest_text):
                    closest_text = extracted_text.strip()
                    best_source_path = source_path
                
                if self._text_matches(extracted_text, text):
                    print(f"[@controller:TextVerification] Text found in {source_path}: '{extracted_text.strip()}'")
                    text_found = True
                    
                    # Save cropped source image for UI comparison using stored device model
                    if area:
                        cropped_source_path = self._save_cropped_source_image(source_path, area, verification_index)
                        if cropped_source_path:
                            additional_data["source_image_path"] = cropped_source_path
                    
                    # KPI optimization: If match found in later image
                    if idx > 0:
                        match_timestamp = os.path.getmtime(source_path)
                        additional_data["kpi_match_timestamp"] = match_timestamp
                        additional_data["kpi_match_index"] = idx
                        print(f"[@controller:TextVerification] KPI: Match at index {idx}, timestamp {match_timestamp}")
                    
                    additional_data["extractedText"] = extracted_text.strip()  # Frontend-expected property name
                    return True, f"Text pattern '{text}' found: '{extracted_text.strip()}'", additional_data
            
            # If no match found, still save the best source for comparison
            if best_source_path and area:
                cropped_source_path = self._save_cropped_source_image(best_source_path, area, verification_index)
                if cropped_source_path:
                    additional_data["source_image_path"] = cropped_source_path
            
            # Set failure data
            additional_data["extractedText"] = closest_text  # Frontend-expected property name
            return False, f"Text pattern '{text}' not found", additional_data
        
        else:
            # Capture new image if no image list provided
            print(f"[@controller:TextVerification] No image list provided, using single screenshot")
            
            # Take screenshot (already taken in execute_verification)
            capture_path = self.av_controller.take_screenshot()
            if not capture_path:
                return False, "Failed to capture screen for text verification", additional_data
            
            # Extract text from area
            extracted_text = self._extract_text_from_area(capture_path, area, image_filter)
            
            if self._text_matches(extracted_text, text):
                print(f"[@controller:TextVerification] Text found in captured frame: '{extracted_text.strip()}'")
                
                # Save cropped source image for UI comparison using stored device model
                if area:
                    cropped_source_path = self._save_cropped_source_image(capture_path, area, verification_index)
                    if cropped_source_path:
                        additional_data["source_image_path"] = cropped_source_path
                
                additional_data["extractedText"] = extracted_text.strip()  # Frontend-expected property name
                return True, f"Text pattern '{text}' found: '{extracted_text.strip()}'", additional_data
            else:
                # Save cropped source for comparison even on failure
                if area:
                    cropped_source_path = self._save_cropped_source_image(capture_path, area, verification_index)
                    if cropped_source_path:
                        additional_data["source_image_path"] = cropped_source_path
                
                additional_data["extractedText"] = extracted_text.strip()  # Frontend-expected property name
                return False, f"Text pattern '{text}' not found", additional_data

    def waitForTextToDisappear(self, text: str, timeout: float = 10.0, area: dict = None, 
                              image_list: List[str] = None,
                              verification_index: int = 0, image_filter: str = 'none') -> Tuple[bool, str, dict]:
        """Wait for text to disappear - checks all images"""
        if not text or text.strip() == '':
            error_msg = "No text specified. Please provide text to search for."
            print(f"[@controller:TextVerification] {error_msg}")
            return False, error_msg, {"searchedText": text or "", "image_filter": image_filter}
        
        # SAFEGUARD: Cap timeout at reasonable maximum (30 seconds) to prevent infinite waits
        if timeout > 30:
            print(f"[@controller:TextVerification] WARNING: Timeout {timeout}s exceeds maximum (30s), capping at 30s")
            timeout = 30
            
        print(f"[@controller:TextVerification] Looking for text pattern to disappear: '{text}'")
        
        # Expand image_list based on timeout
        images_to_check = image_list.copy() if image_list else []
        
        if timeout > 0 and len(image_list) == 1:
            fps = getattr(self.av_controller, 'screenshot_fps', 5)
            max_images = int(timeout * fps)
            
            base_path = image_list[0]
            for i in range(1, max_images):
                next_path = self._get_next_capture(base_path, i)
                if next_path:
                    images_to_check.append(next_path)
        
        # Check all images
        found_in_any = False
        last_found_idx = -1
        wait_ms = int(1000 / getattr(self.av_controller, 'screenshot_fps', 5)) if timeout > 0 else 0
        additional_data = {"searchedText": text, "image_filter": image_filter}
        
        for idx, source_path in enumerate(images_to_check):
            if idx > 0 and not os.path.exists(source_path):
                if wait_ms > 0:
                    time.sleep(wait_ms / 1000.0)
            
            if not os.path.exists(source_path):
                continue
            
            found, message, check_data = self.waitForTextToAppear(
                text, 0, area, [source_path], verification_index, 
                image_filter
            )
            
            additional_data.update(check_data)
            
            if found:
                found_in_any = True
                last_found_idx = idx
        
        success = not found_in_any
        
        # KPI: If disappeared after first check
        if success and last_found_idx >= 0 and last_found_idx < len(images_to_check) - 1:
            disappear_path = images_to_check[last_found_idx + 1]
            if os.path.exists(disappear_path):
                additional_data["kpi_match_timestamp"] = os.path.getmtime(disappear_path)
                additional_data["kpi_match_index"] = last_found_idx + 1
                print(f"[@controller:TextVerification] KPI: Disappeared at index {last_found_idx + 1}")
        
        if success:
            return True, f"Text disappeared", additional_data
        else:
            return False, f"Text still present", additional_data

    def detect_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route interface for text detection."""
        try:
            # Use the controller's helper instance instead of creating a new one
            helpers = self.helpers
            
            # Get source filename from frontend
            image_source_url = data.get('image_source_url', '')
            area = data.get('area')
            
            if not image_source_url:
                return {'success': False, 'message': 'image_source_url is required'}
            
            print(f"[@controller:TextVerification] Detecting text in: {image_source_url}")
            
            # Handle URL-to-path conversion the same way as image verification
            if image_source_url.startswith(('http://', 'https://')):
                # URL case - download first
                image_source_path = helpers.download_image(image_source_url)
                print(f"[@controller:TextVerification] Downloaded image to: {image_source_path}")
            else:
                # Local filename case - use URL conversion utility like image verification
                try:
                    from shared.src.lib.utils.build_url_utils import convertHostUrlToLocalPath
                    from shared.src.lib.utils.storage_path_utils import get_cold_storage_path, get_capture_folder
                    
                    # Strip query parameters from filename (e.g., ?t=timestamp)
                    clean_filename = image_source_url.split('?')[0]
                    
                    # Build a proper URL first if it's just a filename
                    if not clean_filename.startswith('/'):
                        # Assume it's a filename from captures directory
                        image_source_path = os.path.join(self.captures_path, clean_filename)
                    else:
                        # Use URL conversion utility
                        image_source_path = convertHostUrlToLocalPath(clean_filename)
                    
                    print(f"[@controller:TextVerification] Resolved path: {image_source_path}")
                    
                    # Check hot storage first, then cold storage
                    if not os.path.exists(image_source_path):
                        # Try cold storage
                        device_folder = get_capture_folder(self.captures_path)
                        cold_path = os.path.join(get_cold_storage_path(device_folder, 'captures'), os.path.basename(image_source_path))
                        if os.path.exists(cold_path):
                            image_source_path = cold_path
                            print(f"[@controller:TextVerification] Found in cold storage: {cold_path}")
                        else:
                            return {'success': False, 'message': f'Local file not found in hot or cold: {image_source_path}'}
                        
                except Exception as e:
                    print(f"[@controller:TextVerification] Path resolution error: {e}")
                    return {'success': False, 'message': f'Path resolution failed: {str(e)}'}
            
            # Detect text in area (includes crop, filter, OCR, language detection)
            result = helpers.detect_text_in_area(image_source_path, area)
            
            if not result.get('extracted_text'):
                return {'success': False, 'message': 'No text detected in image', **result}
            
            return {
                'success': True,
                'source_was_url': image_source_url.startswith(('http://', 'https://')),
                'image_source_path': image_source_path,
                **result
            }
            
        except Exception as e:
            print(f"[@controller:TextVerification] Error in detect_text: {str(e)}")
            return {'success': False, 'message': f'Text detection failed: {str(e)}'}
    
    def save_text(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route interface for saving text references."""
        try:
            text = data.get('text', '')
            reference_name = data.get('reference_name', 'text_reference')
            area = data.get('area')
            team_id = data.get('team_id')
            
            if not text:
                return {'success': False, 'message': 'text is required for saving reference'}
            
            # Get userinterface_name from request data (frontend provides it)
            userinterface_name = data.get('userinterface_name')
            
            if not userinterface_name:
                return {'success': False, 'message': 'userinterface_name is required for saving reference'}
            
            if not team_id:
                return {'success': False, 'message': 'team_id is required for saving reference'}
            
            # Save text reference using helpers (handles database save)
            save_result = self.helpers.save_text_reference(text, reference_name, userinterface_name, team_id, area)
            
            if not save_result.get('success'):
                return {
                    'success': False,
                    'message': save_result.get('error', 'Failed to save text reference')
                }
            
            return {
                'success': True,
                'message': f'Text reference saved successfully: {reference_name}',
                'reference_name': save_result.get('reference_name'),
                'reference_id': save_result.get('reference_id'),
                'text_data': save_result.get('text_data')
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Text save failed: {str(e)}'}
    
    def execute_verification(self, verification_config: Dict[str, Any]) -> Dict[str, Any]:
        """Route interface for executing verification."""
        try:
            # Check if a source image path is provided in the config
            source_path = verification_config.get('source_image_path')
            
            if source_path:
                print(f"[@controller:TextVerification] Using provided source image: {source_path}")
                # Validate the provided source image exists
                if not os.path.exists(source_path):
                    return {
                        'success': False,
                        'message': f'Provided source image not found: {source_path}',
                        'screenshot_path': None
                    }
            else:
                # Fallback: automatically capture screenshot from AV controller
                print(f"[@controller:TextVerification] No source image provided, capturing screenshot automatically")
                source_path = self.av_controller.take_screenshot()
                if not source_path or not os.path.exists(source_path):
                    return {
                        'success': False,
                        'message': 'Failed to capture screenshot automatically for text verification',
                        'screenshot_path': None
                    }
                print(f"[@controller:TextVerification] Using automatically captured screenshot: {source_path}")
            
            # Extract parameters from nested structure
            params = verification_config.get('params', {})
            command = verification_config.get('command', 'waitForTextToAppear')
            
            # Required parameters
            text = params.get('text', '')
            if not text:
                return {
                    'success': False,
                    'message': 'No text specified for text verification',
                    'details': {'error': 'Missing text parameter'}
                }
            
            # Optional parameters with defaults
            timeout = int(params.get('timeout', 0))
            area = params.get('area')
            image_filter = params.get('image_filter', 'none')
            
            # Extract userinterface_name and team_id for reference resolution (NO LEGACY device_model)
            userinterface_name = verification_config.get('userinterface_name')
            team_id = verification_config.get('team_id')
            
            # Resolve area from database if reference_name is provided AND area is not already present
            reference_name = params.get('reference_name')
            if reference_name and not area:
                from shared.src.lib.utils.reference_utils import resolve_reference_area_backend
                resolved_area = resolve_reference_area_backend(reference_name, userinterface_name, team_id)
                if resolved_area:
                    area = resolved_area
                    print(f"[@controller:TextVerification] Resolved area from reference {reference_name}: {resolved_area}")
                else:
                    print(f"[@controller:TextVerification] Warning: No area found for reference {reference_name}")
            elif area:
                print(f"[@controller:TextVerification] Using pre-resolved area: {area}")
            
            print(f"[@controller:TextVerification] Executing {command} with text: '{text}'")
            print(f"[@controller:TextVerification] Parameters: timeout={timeout}, area={area}, filter={image_filter}")
            print(f"[@controller:TextVerification] Using source image: {source_path}")
            
            # Execute verification based on command
            if command == 'waitForTextToAppear':
                success, message, details = self.waitForTextToAppear(
                    text=text,
                    timeout=timeout,
                    area=area,
                    image_list=[source_path],  # Use source_path as image list
                    verification_index=0,
                    image_filter=image_filter
                )
            elif command == 'waitForTextToDisappear':
                success, message, details = self.waitForTextToDisappear(
                    text=text,
                    timeout=timeout,
                    area=area,
                    image_list=[source_path],  # Use source_path as image list
                    verification_index=0,
                    image_filter=image_filter
                )
            else:
                return {'success': False, 'message': f'Unsupported verification command: {command}'}
            
            # Return frontend-expected format (consistent with image verification)
            return {
                'success': success,
                'message': message,
                'screenshot_path': source_path,
                'image_filter': details.get('image_filter', image_filter),  # Applied filter
                'extractedText': details.get('extractedText', ''),       # Frontend-expected property name
                'searchedText': details.get('searchedText', text),       # Frontend-expected property name
                'details': details  # Keep for route processing, will be removed by route
            }
                
        except Exception as e:
            print(f"[@controller:TextVerification] Execution error: {e}")
            return {
                'success': False,
                'message': f'Text verification execution error: {str(e)}',
                'screenshot_path': source_path if 'source_path' in locals() else None
            }

    def get_available_verifications(self) -> list:
        """Get list of available verification types."""
        return [
            {
                "command": "waitForTextToAppear",
                "params": {
                    "text": "",             # Empty string for user input
                    "timeout": 0,           # Default: single check, no polling
                    "area": None            # Optional area
                },
                "verification_type": "text",
                "description": "Wait for text to appear"
            },
            {
                "command": "waitForTextToDisappear",
                "params": {
                    "text": "",             # Empty string for user input
                    "timeout": 0,           # Default: single check, no polling
                    "area": None            # Optional area
                },
                "verification_type": "text",
                "description": "Wait for text to disappear"
            }
        ] 

    def _extract_text_from_area(self, image_path: str, area: dict = None, image_filter: str = None) -> str:
        """
        Extract text from image area using TextHelpers.
        
        Args:
            image_path: Path to the image file
            area: Optional area to crop {'x': x, 'y': y, 'width': width, 'height': height}
            image_filter: Optional filter to apply to the image before OCR
            
        Returns:
            str: extracted text
        """
        try:
            # Use TextHelpers to extract text (handles cropping, filtering, and OCR)
            result = self.helpers.detect_text_in_area(image_path, area)
            
            extracted_text = result.get('extracted_text', '')
            
            print(f"[@controller:TextVerification] OCR extracted: '{extracted_text.strip()}'")
            
            return extracted_text
            
        except Exception as e:
            print(f"[@controller:TextVerification] Error extracting text from area: {e}")
            return ""

    def _text_matches(self, extracted_text: str, target_text: str) -> bool:
        """
        Check if extracted text matches target text using TextHelpers.
        
        Args:
            extracted_text: Text extracted from OCR
            target_text: Text pattern to search for
            
        Returns:
            bool: True if text matches, False otherwise
        """
        try:
            # Use TextHelpers for consistent text matching
            return self.helpers.text_matches(extracted_text, target_text)
        except Exception as e:
            print(f"[@controller:TextVerification] Error in text matching: {e}")
            return False

    def _save_cropped_source_image(self, source_path: str, area: dict, verification_index: int) -> Optional[str]:
        """
        Save cropped source image for UI comparison using ImageHelpers.
        
        Args:
            source_path: Path to source image
            area: Area to crop
            verification_index: Index for naming
            
        Returns:
            str: Path to saved cropped image, None if failed
        """
        try:
            # Import ImageHelpers for cropping (reuse image cropping logic)
            from .image_helpers import ImageHelpers
            image_helpers = ImageHelpers(self.captures_path, self.av_controller)
            
            # Create results directory in COLD storage (persistent) - use same path as image controller
            from shared.src.lib.utils.storage_path_utils import get_cold_storage_path, get_capture_folder
            capture_folder = get_capture_folder(self.av_controller.video_capture_path)
            cold_captures_path = get_cold_storage_path(capture_folder, 'captures')
            results_dir = os.path.join(cold_captures_path, 'verification_results')
            os.makedirs(results_dir, exist_ok=True)
            
            # Create result file path with UNIQUE timestamp to avoid browser caching
            timestamp = int(time.time() * 1000)  # milliseconds
            cropped_result_path = f'{results_dir}/text_source_image_{verification_index}_{timestamp}.png'
            
            print(f"[@controller:TextVerification] Cropping source image: {source_path} -> {cropped_result_path}")
            
            # Use ImageHelpers to crop the image (reuse existing crop functionality)
            success = image_helpers.crop_image_to_area(source_path, cropped_result_path, area)
            
            if success:
                print(f"[@controller:TextVerification] Successfully cropped text source image")
                return cropped_result_path
            else:
                print(f"[@controller:TextVerification] Failed to crop source image")
                return None
                
        except Exception as e:
            print(f"[@controller:TextVerification] Error cropping source image: {e}")
            return None
    
    def _get_next_capture(self, filepath: str, offset: int) -> str:
        """Get next sequential capture filename"""
        match = re.search(r'capture_(\d{9})', filepath)
        if not match:
            return None
        num = int(match.group(1)) + offset
        return filepath.replace(match.group(0), f'capture_{num:09d}')
