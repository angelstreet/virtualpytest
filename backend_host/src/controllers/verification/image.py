"""
Image Verification Controller

Clean image controller that uses helpers for all operations.
Provides route interfaces and core domain logic.
"""

import time
import os
import cv2
import numpy as np
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from .image_helpers import ImageHelpers
import logging


class ImageVerificationController:
    """Pure image verification controller that uses template matching to detect images on screen."""
    
    def __init__(self, av_controller, device_model=None, **kwargs):
        """
        Initialize the Image Verification controller.
        
        Args:
            av_controller: AV controller for capturing images (dependency injection)
            device_model: Device model for reference image resolution (e.g., 'android_tv')
        """
        self.av_controller = av_controller
        self.device_model = device_model
        self.captures_path = os.path.join(av_controller.video_capture_path, 'captures')
        self.verification_type = 'image'

        self.verification_results_dir = os.path.join(self.captures_path, 'verification_results')
        self.cropped_images_dir = os.path.join(self.captures_path, 'cropped')
        self.references_dir = os.path.join(self.captures_path, 'references')
        
        # Ensure all directories exist
        for directory in [self.verification_results_dir, self.cropped_images_dir, self.references_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Initialize helpers with explicit references directory
        self.helpers = ImageHelpers(self.captures_path, av_controller)
        
        print(f"[@controller:ImageVerification] Initialized")
        print(f"[@controller:ImageVerification] Initialized with paths:")
        print(f"  Captures: {self.captures_path}")
        print(f"  Verification results: {self.verification_results_dir}")
        print(f"  Cropped images: {self.cropped_images_dir}")
        print(f"  References: {self.references_dir}")
        
        # Controller is always ready
        self.is_connected = True
        self.verification_session_id = f"image_verify_{int(time.time())}"

    def connect(self) -> bool:
        """Connect to the image verification controller."""
        self.is_connected = True
        return True

    def disconnect(self) -> bool:
        """Disconnect from the image verification controller."""
        self.is_connected = False
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the image verification controller."""
        return {
            "connected": self.is_connected,
            "av_controller": self.av_controller.device_name if self.av_controller else None,
            "controller_type": "image",
            "captures_path": self.captures_path
        }
    
    def waitForImageToAppear(self, image_path: str, timeout: float = 1.0, threshold: float = 0.8, 
                            area: dict = None, image_list: List[str] = None, 
                            verification_index: int = 0, image_filter: str = 'none', model: str = 'default') -> Tuple[bool, str, dict]:
        """
        Wait for image to appear either in provided image list or by capturing new frames.
        
        Args:
            image_path: Path to reference image to search for
            timeout: Maximum time to wait (seconds)
            threshold: Matching threshold (0.0 to 1.0)
            area: Optional area to search within
            image_list: List of image paths to search in (if None, captures new frames)
            verification_index: Index of verification for naming
            image_filter: Filter to apply ('none', 'greyscale', 'binary')
            model: Device model for reference image resolution
            
        Returns:
            Tuple of (success, message, additional_data)
        """
        # Check if image_path is provided
        if not image_path or image_path.strip() == '':
            error_msg = "No reference image specified. Please select a reference image or provide an image path."
            print(f"[@controller:ImageVerification] {error_msg}")
            return False, error_msg, {}
        
        print(f"[@controller:ImageVerification] Looking for image: {image_path}")
        if image_filter and image_filter != 'none':
            print(f"[@controller:ImageVerification] Using image filter: {image_filter}")
        
        # Resolve reference image path and area using provided device model
        resolved_image_path, resolved_area = self._resolve_reference_image(image_path, model)
        if not resolved_image_path:
            error_msg = f"Reference image file not found: '{image_path}' (could not locate or download reference image)"
            print(f"[@controller:ImageVerification] {error_msg}")
            return False, error_msg, {}
        
        # Use database area if available, otherwise use passed area
        if resolved_area:
            area = resolved_area
            print(f"[@controller:ImageVerification] Using database area for reference {image_path}: {resolved_area}")
        else:
            print(f"[@controller:ImageVerification] Using passed area for reference {image_path}: {area}")
        
        # Get filtered reference image path (only change the reference, not source)
        filtered_reference_path = resolved_image_path
        if image_filter and image_filter != 'none':
            base_path, ext = os.path.splitext(resolved_image_path)
            filtered_path = f"{base_path}_{image_filter}{ext}"
            if os.path.exists(filtered_path):
                filtered_reference_path = filtered_path
                print(f"[@controller:ImageVerification] Using pre-existing filtered reference: {filtered_reference_path}")
            else:
                print(f"[@controller:ImageVerification] Filtered reference not found, using original: {resolved_image_path}")
        
        ref_img = cv2.imread(filtered_reference_path, cv2.IMREAD_COLOR)
        if ref_img is None:
            error_msg = f"Reference image corrupted or invalid format: '{os.path.basename(filtered_reference_path)}' (file exists but cannot be loaded)"
            return False, error_msg, {}
        
        # Construct R2 URL for the reference image (for display purposes)
        reference_name = os.path.basename(image_path)
        if not reference_name.endswith(('.jpg', '.jpeg', '.png')):
            reference_name = f"{reference_name}.jpg"
        reference_r2_url = f"https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/reference-images/{model}/{reference_name}"
        
        additional_data = {
            "reference_image_path": filtered_reference_path,  # Local path for processing
            "reference_image_url": reference_r2_url,          # R2 URL for display
            "image_filter": image_filter,
            "user_threshold": threshold  # Store user's original threshold setting
        }
        
        if image_list:
            # Search in provided images
            print(f"[@controller:ImageVerification] Searching in {len(image_list)} provided images")
            max_threshold_score = 0.0
            best_source_path = None
            
            for source_path in image_list:
                if not os.path.exists(source_path):
                    print(f"[@controller:ImageVerification] WARNING: Source image not found: {os.path.basename(source_path)}")
                    continue
                
                source_img = cv2.imread(source_path, cv2.IMREAD_COLOR)
                if source_img is None:
                    print(f"[@controller:ImageVerification] WARNING: Source image corrupted/invalid: {os.path.basename(source_path)}")
                    continue
                
                threshold_score = self._match_template(ref_img, source_img, area)
                
                # Always set first valid source as best_source_path, then update if better threshold score found
                if best_source_path is None or threshold_score > max_threshold_score:
                    max_threshold_score = threshold_score
                    best_source_path = source_path
                
                if threshold_score >= threshold:
                    print(f"[@controller:ImageVerification] Match found in {source_path} with threshold score {threshold_score:.3f}")
                    
                    # Save actual threshold score (separate from user threshold)
                    additional_data["matching_result"] = threshold_score  # Actual threshold score
                    
                    # Generate comparison images for successful match
                    image_urls = self._generate_comparison_images(source_path, resolved_image_path, area, verification_index, image_filter)
                    additional_data.update(image_urls)
                    
                    # Create consistent message format for success (same as failure format)
                    source_info = f"source: {os.path.basename(source_path)}"
                    reference_info = f"reference: {os.path.basename(resolved_image_path)}"
                    
                    return True, f"{reference_info} detected in {source_info}. Match score: {threshold_score:.3f} (required: {threshold:.3f})", additional_data
            
            # ALWAYS generate comparison images for debugging (especially important for failures)
            if best_source_path:
                print(f"[@controller:ImageVerification] Generating debug comparison images for failed match (best score: {max_threshold_score:.3f})")
                image_urls = self._generate_comparison_images(best_source_path, resolved_image_path, area, verification_index, image_filter)
                additional_data.update(image_urls)
            else:
                print(f"[@controller:ImageVerification] WARNING: No valid source images found for comparison")
            
            # Save best threshold score (separate from user threshold)
            additional_data["matching_result"] = max_threshold_score  # Actual threshold score
            
            # Create detailed error message with source and reference info
            source_info = f"source: {os.path.basename(best_source_path)}" if best_source_path else "source: none"
            reference_info = f"reference: {os.path.basename(resolved_image_path)}"
            error_msg = f"{reference_info} not detected in {source_info}. Match score: {max_threshold_score:.3f} (required: {threshold:.3f})"
            
            return False, error_msg, additional_data
        
        else:
            # Capture new image if no image list provided - this shouldn't happen in our case
            print(f"[@controller:ImageVerification] No image list provided, image not found")
            return False, "Error : Image not found in current screenshot", additional_data

    def waitForImageToDisappear(self, image_path: str, timeout: float = 1.0, threshold: float = 0.8,
                               area: dict = None, image_list: List[str] = None,
                               verification_index: int = 0, image_filter: str = 'none', model: str = 'default') -> Tuple[bool, str, dict]:
        """
        Wait for image to disappear by calling waitForImageToAppear and inverting the result.
        """
        # Check if image_path is provided
        if not image_path or image_path.strip() == '':
            error_msg = "No reference image specified. Please select a reference image or provide an image path."
            print(f"[@controller:ImageVerification] {error_msg}")
            return False, error_msg, {}
            
        print(f"[@controller:ImageVerification] Looking for image to disappear: {image_path}")
        
        # Smart reuse: call waitForImageToAppear and invert result
        found, message, additional_data = self.waitForImageToAppear(image_path, timeout, threshold, area, image_list, verification_index, image_filter, model)
        
        # Invert the boolean result and adjust the message
        success = not found
        
        # For disappear operations, invert the matching result for UI display to make it intuitive
        if 'matching_result' in additional_data and additional_data['matching_result'] is not None:
            original_threshold_score = additional_data['matching_result']
            # Invert threshold score for disappear operations: 1.0 - original gives intuitive "disappear percentage"
            inverted_threshold_score = 1.0 - original_threshold_score
            additional_data['matching_result'] = inverted_threshold_score
            additional_data['original_threshold_score'] = original_threshold_score  # Keep original for debugging
            print(f"[@controller:ImageVerification] Disappear threshold score display: {original_threshold_score:.3f} -> {inverted_threshold_score:.3f} (inverted for UI)")
        
        if success:
            # Image has disappeared (was not found)
            return True, f"Image disappeared: {message}", additional_data
        else:
            # Image is still present (was found)
            return False, f"Image still present: {message}", additional_data

    # =============================================================================
    # Route Interface Methods (Required by host_verification_image_routes.py)
    # =============================================================================

    def crop_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route interface for image cropping."""
        try:
            # Get source filename from frontend
            image_source_url = data.get('image_source_url', '')
            area = data.get('area')
            reference_name = data.get('reference_name', 'cropped_image')
            
            if not image_source_url:
                return {'success': False, 'message': 'image_source_url is required'}
            
            if not area:
                return {'success': False, 'message': 'area is required for cropping'}
            
            # Build full path for local files, keep URLs as-is
            if image_source_url.startswith(('http://', 'https://')):
                # URL case - download first
                image_source_path = self.helpers.download_image(image_source_url)
            else:
                # Local filename case - build full path directly
                image_source_path = os.path.join(self.captures_path, image_source_url)
                
                if not os.path.exists(image_source_path):
                    return {'success': False, 'message': f'Local file not found: {image_source_path}'}
            
            # Generate unique filename for output
            filename = self.helpers.get_unique_filename(reference_name)
            image_cropped_path = os.path.join(self.captures_path, filename)
            
            # Crop image using helpers
            success = self.helpers.crop_image_to_area(image_source_path, image_cropped_path, area)
            
            if not success:
                return {'success': False, 'message': 'Image cropping failed'}
            
            # Create filtered versions
            self.helpers.create_filtered_versions(image_cropped_path)
            
            return {
                'success': True,
                'message': f'Image cropped successfully: {filename}',
                'image_cropped_path': image_cropped_path,
                'filename': filename,
                'area': area,
                'source_was_url': image_source_url.startswith(('http://', 'https://'))
            }
                
        except Exception as e:
            return {'success': False, 'message': f'Image crop failed: {str(e)}'}

    def process_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route interface for image processing."""
        try:
            image_source_url = data.get('image_source_url', '')
            remove_background = data.get('remove_background', False)
            image_filter = data.get('image_filter', 'none')
            
            if not image_source_url:
                return {'success': False, 'message': 'image_source_url is required'}
            
            # Build full path for local files, keep URLs as-is
            if image_source_url.startswith(('http://', 'https://')):
                # URL case - download first
                image_source_path = self.helpers.download_image(image_source_url)
                # Create a copy in captures directory
                filename = self.helpers.get_unique_filename('filtered_image')
                image_filtered_path = os.path.join(self.captures_path, filename)
                self.helpers.copy_image_file(image_source_path, image_filtered_path)
                # Clean up temp file
                try:
                    os.unlink(image_source_path)
                except:
                    pass
                image_filtered_path = image_filtered_path
            else:
                # Local filename case - build full path directly
                image_source_path = os.path.join(self.captures_path, image_source_url)
                
                if not os.path.exists(image_source_path):
                    return {'success': False, 'message': f'Local file not found: {image_source_path}'}
                
                # Create copy for filtering
                filename = self.helpers.get_unique_filename('filtered_image')
                image_filtered_path = os.path.join(self.captures_path, filename)
                self.helpers.copy_image_file(image_source_path, image_filtered_path)
            
            # Apply background removal if requested
            if remove_background:
                bg_success = self.helpers.remove_background(image_filtered_path)
                if not bg_success:
                    return {'success': False, 'message': 'Background removal failed'}
            
            # Apply filter using helpers
            filter_success = self.helpers.apply_image_filter(image_filtered_path, image_filter)
            if not filter_success:
                return {'success': False, 'message': f'Filter application failed: {image_filter}'}
            
            return {
                'success': True,
                'message': f'Image filtered successfully',
                'image_filtered_path': image_filtered_path,
                'filename': os.path.basename(image_filtered_path),
                'operations': {
                    'remove_background': remove_background,
                    'filter': image_filter
                },
                'source_was_url': image_source_url.startswith(('http://', 'https://'))
            }
                
        except Exception as e:
            return {'success': False, 'message': f'Image processing failed: {str(e)}'}

    def save_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route interface for saving image references."""
        try:
            image_source_url = data.get('image_source_url', '')
            reference_name = data.get('reference_name', 'image_reference')
            area = data.get('area')
            
            if not image_source_url:
                return {'success': False, 'message': 'image_source_url is required for saving reference'}
            
            # Build full path for local files, keep URLs as-is
            if image_source_url.startswith(('http://', 'https://')):
                # URL case - download first
                image_source_path = self.helpers.download_image(image_source_url)
            else:
                # Local filename case - build full path directly
                image_source_path = os.path.join(self.captures_path, image_source_url)
                
                if not os.path.exists(image_source_path):
                    return {'success': False, 'message': f'Local file not found: {image_source_path}'}
            
            # Generate unique filename for saved reference
            filename = self.helpers.get_unique_filename(reference_name)
            image_saved_path = os.path.join(self.captures_path, filename)
            
            # Save image using helpers
            success = self.helpers.copy_image_file(image_source_path, image_saved_path)
            
            if not success:
                return {'success': False, 'message': 'Image save failed'}
            
            # Create filtered versions
            self.helpers.create_filtered_versions(image_saved_path)
            
            # Get device model from request data (frontend provides it)
            device_model = data.get('device_model')
            
            if not device_model:
                return {'success': False, 'message': 'device_model is required for saving reference'}
            
            # Save reference using helpers (handles R2 upload and database save)
            save_result = self.helpers.save_image_reference(image_saved_path, reference_name, device_model, area)
            
            if not save_result.get('success'):
                return {
                    'success': False,
                    'message': save_result.get('error', 'Failed to save image reference')
                }
            
            # Clean up temp file if we downloaded it
            if image_source_url.startswith(('http://', 'https://')) and image_source_path.startswith('/tmp/'):
                try:
                    os.unlink(image_source_path)
                except:
                    pass
            
            return {
                'success': True,
                'message': f'Image reference saved successfully: {reference_name}',
                'reference_name': save_result.get('reference_name'),
                'r2_url': save_result.get('r2_url'),
                'r2_path': save_result.get('r2_path'),
                'reference_id': save_result.get('reference_id')
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Image save failed: {str(e)}'}

    def execute_verification(self, verification_config: Dict[str, Any]) -> Dict[str, Any]:
        """Route interface for executing verification."""
        try:
            # Check if a source image path is provided in the config
            source_path = verification_config.get('source_image_path')
            
            if source_path:
                print(f"[@controller:ImageVerification] Using provided source image: {source_path}")
                # Validate the provided source image exists
                if not os.path.exists(source_path):
                    return {
                        'success': False,
                        'message': f'Provided source image not found: {source_path}',
                        'screenshot_path': None
                    }
            else:
                # Fallback: automatically capture screenshot from AV controller
                print(f"[@controller:ImageVerification] No source image provided, capturing screenshot automatically")
                source_path = self.av_controller.take_screenshot()
                if not source_path or not os.path.exists(source_path):
                    return {
                        'success': False,
                        'message': 'Failed to capture screenshot automatically for image verification',
                        'screenshot_path': None
                    }
                print(f"[@controller:ImageVerification] Using automatically captured screenshot: {source_path}")
            
            # Extract parameters from nested structure
            params = verification_config.get('params', {})
            command = verification_config.get('command', 'waitForImageToAppear')
            
            # Required parameters
            image_path = params.get('image_path', '')
            if not image_path:
                return {
                    'success': False,
                    'message': 'No reference image specified for image verification',
                    'screenshot_path': source_path
                }
            
            # Optional parameters with defaults
            threshold = float(params.get('threshold', 0.8))  # Keep float for threshold (0.0-1.0 range)
            timeout = int(params.get('timeout', 1))
            area = params.get('area')
            image_filter = params.get('image_filter', 'none')
            model = params.get('model', self.device_model)  # Use controller's device_model as fallback
            verification_index = verification_config.get('verification_index', 0)  # Get index from config
            
            # Keep area as dict - different functions expect different formats
            print(f"[@controller:ImageVerification] Using area: {area}")
            
            print(f"[@controller:ImageVerification] Searching for image: {image_path}")
            print(f"[@controller:ImageVerification] Timeout: {timeout}s, Threshold: {threshold}")
            print(f"[@controller:ImageVerification] Using source image: {source_path}")
            print(f"[@controller:ImageVerification] Verification index: {verification_index} (source_image_{verification_index}.png)")
            
            # Execute verification based on command using provided device model
            if command == 'waitForImageToAppear':
                success, message, details = self.waitForImageToAppear(
                    image_path=image_path,
                    timeout=timeout,
                    threshold=threshold,
                    area=area,
                    image_list=[source_path],  # Use source_path as image list
                    verification_index=verification_index,  # Use dynamic index
                    image_filter=image_filter,
                    model=model
                )
            elif command == 'waitForImageToDisappear':
                success, message, details = self.waitForImageToDisappear(
                    image_path=image_path,
                    timeout=timeout,
                    threshold=threshold,
                    area=area,
                    image_list=[source_path],  # Use source_path as image list
                    verification_index=verification_index,  # Use dynamic index
                    image_filter=image_filter,
                    model=model
                )
            else:
                return {
                    'success': False,
                    'message': f'Unknown image verification command: {command}',
                    'screenshot_path': source_path
                }
            
            # Return results in frontend-expected format
            result = {
                'success': success,
                'message': message,
                'screenshot_path': source_path,
                'matching_result': details.get('matching_result', 0.0),  # Actual threshold score
                'user_threshold': details.get('user_threshold', threshold),  # User's threshold setting
                'image_filter': details.get('image_filter', image_filter),  # Applied filter
                'details': details  # Keep for route processing, will be removed by route
            }
            
            return result
            
        except Exception as e:
            print(f"[@controller:ImageVerification] Execution error: {e}")
            return {
                'success': False,
                'message': f'Image verification execution error: {str(e)}',
                'screenshot_path': source_path if 'source_path' in locals() else None
            }

    def get_available_verifications(self) -> list:
        """Get list of available verification types."""
        return [
            {
                "command": "waitForImageToAppear",
                "params": {
                    "image_path": "",       # Empty string for user input
                    "timeout": 0,           # Default: single check, no polling
                    "threshold": 0.8,      # Default value
                    "area": None            # Optional area
                },
                "verification_type": "image",
                "description": "Wait for image to appear on screen"
            },
            {
                "command": "waitForImageToDisappear",
                "params": {
                    "image_path": "",       # Empty string for user input
                    "timeout": 0,           # Default: single check, no polling
                    "threshold": 0.8,      # Default value
                    "area": None            # Optional area
                },
                "verification_type": "image",
                "description": "Wait for image to disappear from screen"
            }
        ]

    def _generate_comparison_images(self, source_path: str, reference_path: str, area: dict = None, 
                                   verification_index: int = 0, image_filter: str = 'none') -> dict:
        """
        Generate comparison images and return local file paths.
        Only creates source image and overlay - does NOT copy reference image.
        Route will handle URL building.
        """
        try:
            # Use predefined verification results directory
            results_dir = self.verification_results_dir
            
            # Generate unique filenames for this verification
            source_result_path = f'{results_dir}/source_image_{verification_index}.png'
            overlay_result_path = f'{results_dir}/result_overlay_{verification_index}.png'
            
            print(f"[@controller:ImageVerification] Generating comparison images:")
            print(f"  Source: {source_result_path}")
            print(f"  Reference: {reference_path} (using original, not copying)")
            print(f"  Overlay: {overlay_result_path}")
            
            # === STEP 1: Handle Source Image ===
            if area:
                print(f"[@controller:ImageVerification] Cropping source to area: {area}")
                if not self.helpers.crop_image_to_area(source_path, source_result_path, area):
                    print(f"[@controller:ImageVerification] Failed to crop source image")
                    return {}
            else:
                print(f"[@controller:ImageVerification] Using full source image: {source_path}")
                self.helpers.copy_image_file(source_path, source_result_path)
            
            # Apply filter to source if requested
            if image_filter and image_filter != 'none':
                print(f"[@controller:ImageVerification] Applying {image_filter} filter to source")
                if not self.helpers.apply_image_filter(source_result_path, image_filter):
                    print(f"[@controller:ImageVerification] Warning: Failed to apply {image_filter} filter to source")
            
            # === STEP 2: Determine Reference Image Path (No Copying) ===
            # Use filtered reference if available, otherwise use original
            reference_image_for_overlay = reference_path
            if image_filter and image_filter != 'none':
                base_path, ext = os.path.splitext(reference_path)
                filtered_reference_path = f"{base_path}_{image_filter}{ext}"
                
                if os.path.exists(filtered_reference_path):
                    print(f"[@controller:ImageVerification] Using existing filtered reference: {filtered_reference_path}")
                    reference_image_for_overlay = filtered_reference_path
                else:
                    print(f"[@controller:ImageVerification] Filtered reference not available, using original: {reference_path}")
            else:
                print(f"[@controller:ImageVerification] Using original reference: {reference_path}")
            
            # === STEP 3: Create Overlay ===
            source_img = cv2.imread(source_result_path)
            ref_img = cv2.imread(reference_image_for_overlay)
            
            if source_img is None or ref_img is None:
                print(f"[@controller:ImageVerification] Failed to load images for comparison")
                return {}
            
            overlay_img = self._create_pixel_difference_overlay(source_img, ref_img)
            if overlay_img is not None:
                cv2.imwrite(overlay_result_path, overlay_img)
                print(f"[@controller:ImageVerification] Created overlay image")
            else:
                print(f"[@controller:ImageVerification] Failed to create overlay")
                return {}
            
            # Return paths - NO reference_image_path since we don't create a copy
            return {
                "source_image_path": source_result_path,
                "result_overlay_path": overlay_result_path
                # NOTE: reference_image_path removed - use reference_image_url from waitForImageToAppear instead
            }
            
        except Exception as e:
            print(f"[@controller:ImageVerification] Error generating comparison images: {e}")
            return {}

    def _create_pixel_difference_overlay(self, source_img, ref_img):
        """
        Create a pixel-by-pixel difference overlay image.
        
        Green pixels (with transparency) = matching pixels
        Red pixels (with transparency) = non-matching pixels
        """
        try:
            # Ensure both images have the same dimensions
            if source_img.shape != ref_img.shape:
                print(f"[@controller:ImageVerification] Resizing images to match - Source: {source_img.shape}, Ref: {ref_img.shape}")
                # Resize reference to match source
                ref_img = cv2.resize(ref_img, (source_img.shape[1], source_img.shape[0]))
            
            # Convert to grayscale for pixel comparison (more reliable than color)
            source_gray = cv2.cvtColor(source_img, cv2.COLOR_BGR2GRAY)
            ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
            
            # Calculate absolute difference between pixels
            diff = cv2.absdiff(source_gray, ref_gray)
            
            # Create binary mask for matching/non-matching pixels
            # Threshold for pixel difference (adjust as needed - smaller = more sensitive)
            pixel_threshold = 10  # Pixels with difference <= 10 are considered matching
            matching_mask = diff <= pixel_threshold
            
            # Create BGRA overlay (BGR + Alpha channel for transparency)
            height, width = source_img.shape[:2]
            overlay = np.zeros((height, width, 4), dtype=np.uint8)
            
            # Set transparency level (0-255, where 0=fully transparent, 255=fully opaque)
            transparency = 128  # 50% transparency
            
            # Green pixels for matching areas (BGR format: Green = [0, 255, 0])
            overlay[matching_mask] = [0, 255, 0, transparency]  # Green with transparency
            
            # Red pixels for non-matching areas (BGR format: Red = [0, 0, 255])
            overlay[~matching_mask] = [0, 0, 255, transparency]  # Red with transparency
            
            # Optional: Make areas with very small differences more transparent
            # This helps focus attention on significant differences
            small_diff_mask = (diff > 0) & (diff <= 5)
            if np.any(small_diff_mask):
                overlay[small_diff_mask] = [0, 255, 0, transparency // 2]  # More transparent green
            
            print(f"[@controller:ImageVerification] Pixel comparison stats:")
            matching_pixels = np.sum(matching_mask)
            total_pixels = height * width
            match_percentage = (matching_pixels / total_pixels) * 100
            print(f"  Matching pixels: {matching_pixels}/{total_pixels} ({match_percentage:.1f}%)")
            print(f"  Pixel threshold: {pixel_threshold}")
            print(f"  Overlay transparency: {transparency}/255")
            
            return overlay
            
        except Exception as e:
            print(f"[@controller:ImageVerification] Error creating pixel difference overlay: {e}")
            return None

    def _resolve_reference_image(self, image_path: str, model: str = 'default') -> tuple[Optional[str], Optional[dict]]:
        """
        Resolve reference image path and area by downloading from R2 and querying database.
        Returns tuple of (image_path, area_dict).
        """
        try:
            # Extract reference name from path
            if '/' in image_path:
                reference_name = os.path.basename(image_path)
            else:
                reference_name = image_path
            
            # Remove extension if present to get base name
            base_name = reference_name.split('.')[0]
            
            print(f"[@controller:ImageVerification] Resolving reference: {reference_name} for model: {model}")
            
            # Use provided device model
            local_dir = os.path.join(self.references_dir, model)
            os.makedirs(local_dir, exist_ok=True)
            
            # Use the reference name with proper extension
            if not reference_name.endswith(('.jpg', '.jpeg', '.png')):
                reference_name = f"{reference_name}.jpg"
            
            local_path = f'{local_dir}/{reference_name}'
            
            # Check if already exists locally
            if os.path.exists(local_path):
                print(f"[@controller:ImageVerification] Reference already exists locally: {local_path}")
                # Also resolve area from database
                from src.lib.utils.reference_utils import resolve_reference_area_backend
                resolved_area = resolve_reference_area_backend(base_name, model)
                return local_path, resolved_area
            
            print(f"[@controller:ImageVerification] Downloading from R2 to: {local_path}")
            
            # Download from R2 using CloudflareUtils
            try:
                from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
                
                # Construct R2 object key using provided device model
                r2_object_key = f"reference-images/{model}/{reference_name}"
                
                print(f"[@controller:ImageVerification] R2 object key: {r2_object_key}")
                
                # Download file
                cloudflare_utils = get_cloudflare_utils()
                download_result = cloudflare_utils.download_file(r2_object_key, local_path)
                
                if download_result.get('success'):
                    print(f"[@controller:ImageVerification] Successfully downloaded reference from R2: {local_path}")
                    # Also resolve area from database
                    from src.lib.utils.reference_utils import resolve_reference_area_backend
                    resolved_area = resolve_reference_area_backend(base_name, model)
                    return local_path, resolved_area
                else:
                    print(f"[@controller:ImageVerification] Failed to download from R2: {download_result.get('error')}")
                    return None, None
                    
            except Exception as download_error:
                print(f"[@controller:ImageVerification] R2 download error: {download_error}")
                return None, None
                
        except Exception as e:
            print(f"[@controller:ImageVerification] Reference resolution error: {e}")
            return None, None

    def _match_template(self, ref_img, source_img, area: dict = None) -> float:
        """
        Perform template matching between reference and source images.
        
        Returns:
            Threshold score (0.0 to 1.0)
        """
        try:
            # Crop source image to area if specified
            if area:
                x, y, w, h = int(area['x']), int(area['y']), int(area['width']), int(area['height'])
                source_img = source_img[y:y+h, x:x+w]
            
            # Perform standard template matching
            result = cv2.matchTemplate(source_img, ref_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            return max_val
            
        except Exception as e:
            print(f"[@controller:ImageVerification] Template matching error: {e}")
            return 0.0

 