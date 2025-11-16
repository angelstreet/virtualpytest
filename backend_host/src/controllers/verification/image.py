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
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from .image_helpers import ImageHelpers
import logging


class ImageVerificationController:
    """Pure image verification controller that uses template matching to detect images on screen."""
    
    def __init__(self, av_controller, **kwargs):
        """
        Initialize the Image Verification controller.
        
        Args:
            av_controller: AV controller for capturing images (dependency injection)
        """
        from shared.src.lib.utils.storage_path_utils import get_capture_storage_path, get_cold_storage_path, get_capture_folder
        
        self.av_controller = av_controller
        # Use centralized path resolution (handles hot/cold storage automatically)
        self.captures_path = get_capture_storage_path(av_controller.video_capture_path, 'captures')
        self.verification_type = 'image'

        # Verification results, cropped images, and references must be in COLD storage (persistent)
        capture_folder = get_capture_folder(av_controller.video_capture_path)
        cold_captures_path = get_cold_storage_path(capture_folder, 'captures')
        self.verification_results_dir = os.path.join(cold_captures_path, 'verification_results')
        self.cropped_images_dir = os.path.join(cold_captures_path, 'cropped')
        self.references_dir = os.path.join(cold_captures_path, 'references')
        
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
        self.verification_session_id = f"image_verify_{int(time.time())}"

    def connect(self) -> bool:
        """Connect to the image verification controller."""
        return True

    def disconnect(self) -> bool:
        """Disconnect from the image verification controller."""
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the image verification controller."""
        return {
            "connected": True,
            "av_controller": self.av_controller.device_name if self.av_controller else None,
            "controller_type": "image",
            "captures_path": self.captures_path
        }
    
    def waitForImageToAppear(self, image_path: str, timeout: float = 1.0, threshold: float = 0.8, 
                             area: dict = None, image_list: List[str] = None,
                             verification_index: int = 0, image_filter: str = 'none', userinterface_name: str = 'default', team_id: str = None) -> Tuple[bool, str, dict]:
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
            userinterface_name: User interface name for reference image resolution
            
        Returns:
            Tuple of (success, message, additional_data)
        """
        # Check if image_path is provided
        if not image_path or image_path.strip() == '':
            error_msg = "No reference image specified. Please select a reference image or provide an image path."
            return False, error_msg, {}
        
        # SAFEGUARD: Cap timeout at reasonable maximum (30 seconds) to prevent infinite waits
        if timeout > 30:
            print(f"[@controller:ImageVerification] WARNING: Timeout {timeout}s exceeds maximum (30s), capping at 30s")
            timeout = 30
        
        # Resolve reference image path and area using userinterface_name and team_id
        resolved_image_path, resolved_area = self._resolve_reference_image(image_path, userinterface_name, team_id)
        if not resolved_image_path:
            error_msg = f"Reference image file not found: '{image_path}' (could not locate or download reference image)"
            return False, error_msg, {}
        
        if not resolved_area:
            error_msg = f"Reference area not found in database: '{image_path}'"
            return False, error_msg, {}
        
        # Use database area (REQUIRED - no fallback)
        area = resolved_area
        
        # Get filtered reference image path (only change the reference, not source)
        filtered_reference_path = resolved_image_path
        if image_filter and image_filter != 'none':
            base_path, ext = os.path.splitext(resolved_image_path)
            filtered_path = f"{base_path}_{image_filter}{ext}"
            if os.path.exists(filtered_path):
                filtered_reference_path = filtered_path
            else:
                # Filtered reference not found, using original
                pass
        
        ref_img = cv2.imread(filtered_reference_path, cv2.IMREAD_COLOR)
        if ref_img is None:
            error_msg = f"Reference image corrupted or invalid format: '{os.path.basename(filtered_reference_path)}' (file exists but cannot be loaded)"
            return False, error_msg, {}
        
        # Construct R2 URL for the reference image (for display purposes)
        reference_name = os.path.basename(image_path)
        if not reference_name.endswith(('.jpg', '.jpeg', '.png')):
            reference_name = f"{reference_name}.jpg"
        r2_base_url = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', 'https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev')
        reference_r2_url = f"{r2_base_url}/reference-images/{userinterface_name}/{reference_name}"
        
        additional_data = {
            "reference_image_path": filtered_reference_path,  # Local path for processing
            "reference_image_url": reference_r2_url,          # R2 URL for display
            "image_filter": image_filter,
            "user_threshold": threshold  # Store user's original threshold setting
        }
        
        if image_list:
            # Expand image_list based on timeout
            images_to_check = image_list.copy()
            
            if timeout > 0 and len(image_list) == 1:
                fps = getattr(self.av_controller, 'screenshot_fps', 5)
                max_images = int(timeout * fps)
                wait_ms = int(1000 / fps)
                
                print(f"[@controller:ImageVerification] Timeout {timeout}s: checking {max_images} images (wait: {wait_ms}ms)")
                
                base_path = image_list[0]
                for i in range(1, max_images):
                    next_path = self._get_next_capture(base_path, i)
                    if next_path:
                        images_to_check.append(next_path)
            
            max_threshold_score = 0.0
            best_source_path = None
            best_match_location = None  # Store actual match location
            wait_ms = int(1000 / getattr(self.av_controller, 'screenshot_fps', 5)) if timeout > 0 else 0
            
            for idx, source_path in enumerate(images_to_check):
                if idx > 0 and not os.path.exists(source_path):
                    if wait_ms > 0:
                        time.sleep(wait_ms / 1000.0)
                
                if not os.path.exists(source_path):
                    continue
                if not os.path.exists(source_path):
                    continue
                
                source_img = cv2.imread(source_path, cv2.IMREAD_COLOR)
                if source_img is None:
                    continue
                
                # Get match result: found flag tells us if we can exit early!
                is_found, threshold_score, match_location = self._match_template(ref_img, source_img, area, threshold)
                
                # Always set first valid source as best_source_path, then update if better threshold score found
                if best_source_path is None or threshold_score > max_threshold_score:
                    max_threshold_score = threshold_score
                    best_source_path = source_path
                    best_match_location = match_location
                
                # Early exit if found! No need to check more images
                if is_found:
                    # Save actual threshold score (separate from user threshold)
                    additional_data["matching_result"] = threshold_score  # Actual threshold score
                    
                    # KPI optimization: If match found in later image (idx > 0), include timestamp
                    if idx > 0:
                        match_timestamp = os.path.getmtime(source_path)
                        additional_data["kpi_match_timestamp"] = match_timestamp
                        additional_data["kpi_match_index"] = idx
                    
                    # Generate comparison images using ACTUAL match location (not search area)
                    image_urls = self._generate_comparison_images(source_path, resolved_image_path, match_location, verification_index, image_filter)
                    additional_data.update(image_urls)
                    
                    # Create consistent message format for success (same as failure format)
                    source_info = f"source: {os.path.basename(source_path)}"
                    reference_info = f"reference: {os.path.basename(resolved_image_path)}"
                    
                    return True, f"{reference_info} detected in {source_info}. Match score: {threshold_score:.3f} (required: {threshold:.3f})", additional_data
            
            # ALWAYS generate comparison images for debugging (especially important for failures)
            if best_source_path:
                # Use best match location (even if it didn't meet threshold)
                image_urls = self._generate_comparison_images(best_source_path, resolved_image_path, best_match_location, verification_index, image_filter)
                additional_data.update(image_urls)
            
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
                               verification_index: int = 0, image_filter: str = 'none', userinterface_name: str = 'default', team_id: str = None) -> Tuple[bool, str, dict]:
        """Wait for image to disappear - checks all images in timeout window"""
        if not image_path or image_path.strip() == '':
            error_msg = "No reference image specified. Please select a reference image or provide an image path."
            print(f"[@controller:ImageVerification] {error_msg}")
            return False, error_msg, {}
        
        # SAFEGUARD: Cap timeout at reasonable maximum (30 seconds) to prevent infinite waits
        if timeout > 30:
            print(f"[@controller:ImageVerification] WARNING: Timeout {timeout}s exceeds maximum (30s), capping at 30s")
            timeout = 30
            
        print(f"[@controller:ImageVerification] Looking for image to disappear: {image_path}")
        
        # Expand image_list based on timeout (same as appear)
        images_to_check = image_list.copy() if image_list else []
        
        if timeout > 0 and len(image_list) == 1:
            fps = getattr(self.av_controller, 'screenshot_fps', 5)
            max_images = int(timeout * fps)
            wait_ms = int(1000 / fps)
            
            print(f"[@controller:ImageVerification] Timeout {timeout}s: checking {max_images} images for disappearance")
            
            base_path = image_list[0]
            for i in range(1, max_images):
                next_path = self._get_next_capture(base_path, i)
                if next_path:
                    images_to_check.append(next_path)
        
        # Check all images - need ALL to not match for true disappearance
        wait_ms = int(1000 / getattr(self.av_controller, 'screenshot_fps', 5)) if timeout > 0 else 0
        found_in_any = False
        last_found_idx = -1
        additional_data = {}
        
        for idx, source_path in enumerate(images_to_check):
            if idx > 0 and not os.path.exists(source_path):
                if wait_ms > 0:
                    time.sleep(wait_ms / 1000.0)
            
            if not os.path.exists(source_path):
                continue
            
            # Check if image is present
            found, message, check_data = self.waitForImageToAppear(
                image_path, 0, threshold, area, [source_path], 
                verification_index, image_filter, userinterface_name, team_id
            )
            
            additional_data = check_data
            
            if found:
                found_in_any = True
                last_found_idx = idx
        
        # Invert: success = NOT found in any image
        success = not found_in_any
        
        if 'matching_result' in additional_data and additional_data['matching_result'] is not None:
            original_threshold_score = additional_data['matching_result']
            inverted_threshold_score = 1.0 - original_threshold_score
            additional_data['matching_result'] = inverted_threshold_score
            additional_data['original_threshold_score'] = original_threshold_score
        
        # KPI: If disappeared after first check (found in earlier, not in later)
        if success and last_found_idx >= 0 and last_found_idx < len(images_to_check) - 1:
            disappear_path = images_to_check[last_found_idx + 1]
            if os.path.exists(disappear_path):
                additional_data["kpi_match_timestamp"] = os.path.getmtime(disappear_path)
                additional_data["kpi_match_index"] = last_found_idx + 1
                print(f"[@controller:ImageVerification] KPI: Disappeared at index {last_found_idx + 1}")
        
        if success:
            return True, f"Image disappeared", additional_data
        else:
            return False, f"Image still present", additional_data

    def waitForImageToAppearThenDisappear(self, image_path: str, timeout: float = 10.0, threshold: float = 0.8,
                                         area: dict = None, image_list: List[str] = None,
                                         verification_index: int = 0, image_filter: str = 'none', 
                                         userinterface_name: str = 'default', team_id: str = None) -> Tuple[bool, str, dict]:
        """
        Wait for image to appear then disappear within single timeout window.
        Uses state machine: WAITING_FOR_APPEAR → WAITING_FOR_DISAPPEAR
        Both events must occur within the timeout period.
        """
        if not image_path or image_path.strip() == '':
            error_msg = "No reference image specified. Please select a reference image or provide an image path."
            return False, error_msg, {}
        
        # SAFEGUARD: Cap timeout at reasonable maximum (30 seconds)
        if timeout > 30:
            print(f"[@controller:ImageVerification] WARNING: Timeout {timeout}s exceeds maximum (30s), capping at 30s")
            timeout = 30
        
        print(f"[@controller:ImageVerification] Waiting for image to appear then disappear: {image_path} (timeout: {timeout}s)")
        
        # Resolve reference image path and area
        resolved_image_path, resolved_area = self._resolve_reference_image(image_path, userinterface_name, team_id)
        if not resolved_image_path:
            error_msg = f"Reference image file not found: '{image_path}'"
            return False, error_msg, {}
        
        if not resolved_area:
            error_msg = f"Reference area not found in database: '{image_path}'"
            return False, error_msg, {}
        
        area = resolved_area
        
        # Get filtered reference image
        filtered_reference_path = resolved_image_path
        if image_filter and image_filter != 'none':
            base_path, ext = os.path.splitext(resolved_image_path)
            filtered_path = f"{base_path}_{image_filter}{ext}"
            if os.path.exists(filtered_path):
                filtered_reference_path = filtered_path
        
        ref_img = cv2.imread(filtered_reference_path, cv2.IMREAD_COLOR)
        if ref_img is None:
            error_msg = f"Reference image corrupted or invalid format: '{os.path.basename(filtered_reference_path)}'"
            return False, error_msg, {}
        
        # Construct R2 URL for reference
        reference_name = os.path.basename(image_path)
        if not reference_name.endswith(('.jpg', '.jpeg', '.png')):
            reference_name = f"{reference_name}.jpg"
        r2_base_url = os.environ.get('CLOUDFLARE_R2_PUBLIC_URL', 'https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev')
        reference_r2_url = f"{r2_base_url}/reference-images/{userinterface_name}/{reference_name}"
        
        # Expand image_list for full timeout window
        images_to_check = image_list.copy() if image_list else []
        if timeout > 0 and len(image_list) == 1:
            fps = getattr(self.av_controller, 'screenshot_fps', 5)
            max_images = int(timeout * fps)
            wait_ms = int(1000 / fps)
            
            print(f"[@controller:ImageVerification] Checking {max_images} frames over {timeout}s")
            
            base_path = image_list[0]
            for i in range(1, max_images):
                next_path = self._get_next_capture(base_path, i)
                if next_path:
                    images_to_check.append(next_path)
        
        # State machine
        state = "WAITING_FOR_APPEAR"
        appear_index = None
        appear_timestamp = None
        appear_source_path = None
        appear_match_location = None
        disappear_index = None
        disappear_timestamp = None
        
        wait_ms = int(1000 / getattr(self.av_controller, 'screenshot_fps', 5)) if timeout > 0 else 0
        
        for idx, source_path in enumerate(images_to_check):
            # Wait for frame if needed
            if idx > 0 and not os.path.exists(source_path):
                if wait_ms > 0:
                    time.sleep(wait_ms / 1000.0)
            
            if not os.path.exists(source_path):
                continue
            
            # Load source image
            source_img = cv2.imread(source_path, cv2.IMREAD_COLOR)
            if source_img is None:
                continue
            
            # Check match
            threshold_score, match_location = self._match_template(ref_img, source_img, area)
            
            if state == "WAITING_FOR_APPEAR":
                if threshold_score >= threshold:
                    # Image appeared!
                    state = "WAITING_FOR_DISAPPEAR"
                    appear_index = idx
                    appear_timestamp = os.path.getmtime(source_path)
                    appear_source_path = source_path
                    appear_match_location = match_location
                    print(f"[@controller:ImageVerification] Image APPEARED at frame {idx} (score: {threshold_score:.3f})")
            
            elif state == "WAITING_FOR_DISAPPEAR":
                if threshold_score < threshold:
                    # Image disappeared!
                    disappear_index = idx
                    disappear_timestamp = os.path.getmtime(source_path)
                    print(f"[@controller:ImageVerification] Image DISAPPEARED at frame {idx} (score: {threshold_score:.3f})")
                    
                    # Generate comparison images using appear frame
                    image_urls = self._generate_comparison_images(
                        appear_source_path, resolved_image_path, appear_match_location, 
                        verification_index, image_filter
                    )
                    
                    additional_data = {
                        "reference_image_path": filtered_reference_path,
                        "reference_image_url": reference_r2_url,
                        "image_filter": image_filter,
                        "user_threshold": threshold,
                        "matching_result": threshold_score,
                        "kpi_appear_timestamp": appear_timestamp,
                        "kpi_appear_index": appear_index,
                        "kpi_disappear_timestamp": disappear_timestamp,
                        "kpi_disappear_index": disappear_index
                    }
                    additional_data.update(image_urls)
                    
                    source_info = f"source: {os.path.basename(appear_source_path)}"
                    reference_info = f"reference: {os.path.basename(resolved_image_path)}"
                    message = f"{reference_info} appeared at frame {appear_index} and disappeared at frame {disappear_index} in {source_info}"
                    
                    return True, message, additional_data
        
        # Failed - determine why
        additional_data = {
            "reference_image_path": filtered_reference_path,
            "reference_image_url": reference_r2_url,
            "image_filter": image_filter,
            "user_threshold": threshold
        }
        
        if state == "WAITING_FOR_APPEAR":
            error_msg = f"Image never appeared within {timeout}s timeout"
            return False, error_msg, additional_data
        else:  # state == "WAITING_FOR_DISAPPEAR"
            # Image appeared but never disappeared
            if appear_source_path:
                image_urls = self._generate_comparison_images(
                    appear_source_path, resolved_image_path, appear_match_location,
                    verification_index, image_filter
                )
                additional_data.update(image_urls)
                additional_data["kpi_appear_timestamp"] = appear_timestamp
                additional_data["kpi_appear_index"] = appear_index
            
            error_msg = f"Image appeared at frame {appear_index} but never disappeared within timeout"
            return False, error_msg, additional_data

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
                # Strip query parameters from filename (e.g., ?t=timestamp)
                clean_filename = image_source_url.split('?')[0]
                
                # Local filename case - build full path directly
                image_source_path = os.path.join(self.captures_path, clean_filename)
                
                # Check hot storage first, then cold storage
                if not os.path.exists(image_source_path):
                    from shared.src.lib.utils.storage_path_utils import get_cold_storage_path, get_capture_folder
                    device_folder = get_capture_folder(self.captures_path)
                    cold_path = os.path.join(get_cold_storage_path(device_folder, 'captures'), clean_filename)
                    if os.path.exists(cold_path):
                        image_source_path = cold_path
                        print(f"[@controller:ImageVerification] Found in cold storage: {cold_path}")
                    else:
                        return {'success': False, 'message': f'Local file not found in hot or cold: {image_source_path}'}
            
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
                # Strip query parameters from filename (e.g., ?t=timestamp)
                clean_filename = image_source_url.split('?')[0]
                
                # Local filename case - build full path directly
                image_source_path = os.path.join(self.captures_path, clean_filename)
                
                # Check hot storage first, then cold storage
                if not os.path.exists(image_source_path):
                    from shared.src.lib.utils.storage_path_utils import get_cold_storage_path, get_capture_folder
                    device_folder = get_capture_folder(self.captures_path)
                    cold_path = os.path.join(get_cold_storage_path(device_folder, 'captures'), clean_filename)
                    if os.path.exists(cold_path):
                        image_source_path = cold_path
                        print(f"[@controller:ImageVerification] Found in cold storage: {cold_path}")
                    else:
                        return {'success': False, 'message': f'Local file not found in hot or cold: {image_source_path}'}
                
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
            team_id = data.get('team_id')
            
            if not image_source_url:
                return {'success': False, 'message': 'image_source_url is required for saving reference'}
            
            # Build full path for local files, keep URLs as-is
            if image_source_url.startswith(('http://', 'https://')):
                # URL case - download first
                image_source_path = self.helpers.download_image(image_source_url)
            else:
                # Strip query parameters from filename (e.g., ?t=timestamp)
                clean_filename = image_source_url.split('?')[0]
                
                # Local filename case - build full path directly
                image_source_path = os.path.join(self.captures_path, clean_filename)
                
                # Check hot storage first, then cold storage
                if not os.path.exists(image_source_path):
                    from shared.src.lib.utils.storage_path_utils import get_cold_storage_path, get_capture_folder
                    device_folder = get_capture_folder(self.captures_path)
                    cold_path = os.path.join(get_cold_storage_path(device_folder, 'captures'), clean_filename)
                    if os.path.exists(cold_path):
                        image_source_path = cold_path
                        print(f"[@controller:ImageVerification] Found in cold storage: {cold_path}")
                    else:
                        return {'success': False, 'message': f'Local file not found in hot or cold: {image_source_path}'}
            
            # Generate unique filename for saved reference
            filename = self.helpers.get_unique_filename(reference_name)
            image_saved_path = os.path.join(self.captures_path, filename)
            
            # Save image using helpers
            success = self.helpers.copy_image_file(image_source_path, image_saved_path)
            
            if not success:
                return {'success': False, 'message': 'Image save failed'}
            
            # Create filtered versions
            self.helpers.create_filtered_versions(image_saved_path)
            
            # Get userinterface name from request data (frontend provides it)
            userinterface_name = data.get('userinterface_name')
            
            if not userinterface_name:
                return {'success': False, 'message': 'userinterface_name is required for saving reference'}
            
            if not team_id:
                return {'success': False, 'message': 'team_id is required for saving reference'}
            
            # Round area coordinates to 2 decimal places before saving
            if area:
                area = self.helpers.round_area_coordinates(area, max_decimals=2)
                print(f"[@controller:ImageVerification] Rounded area for saving: {area}")
            
            # Save reference using helpers (handles R2 upload and database save)
            save_result = self.helpers.save_image_reference(image_saved_path, reference_name, userinterface_name, team_id, area)
            
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
            # Extract team_id for database operations (reference area resolution)
            team_id = verification_config.get('team_id')
            
            # Extract userinterface_name for reference resolution
            userinterface_name = verification_config.get('userinterface_name')
            if not userinterface_name:
                return {
                    'success': False,
                    'message': 'userinterface_name is required for reference resolution',
                    'screenshot_path': None
                }
            
            # Check if a source image path is provided in the config
            source_path = verification_config.get('source_image_path')
            
            if source_path:
                # Validate the provided source image exists
                if not os.path.exists(source_path):
                    return {
                        'success': False,
                        'message': f'Provided source image not found: {source_path}',
                        'screenshot_path': None
                    }
            else:
                # Fallback: automatically capture screenshot from AV controller
                source_path = self.av_controller.take_screenshot()
                if not source_path or not os.path.exists(source_path):
                    return {
                        'success': False,
                        'message': 'Failed to capture screenshot automatically for image verification',
                        'screenshot_path': None
                    }
            
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
            verification_index = verification_config.get('verification_index', 0)  # Get index from config
            
            # Execute verification based on command using userinterface_name
            if command == 'waitForImageToAppear':
                success, message, details = self.waitForImageToAppear(
                    image_path=image_path,
                    timeout=timeout,
                    threshold=threshold,
                    area=area,
                    image_list=[source_path],  # Use source_path as image list
                    verification_index=verification_index,  # Use dynamic index
                    image_filter=image_filter,
                    userinterface_name=userinterface_name,  # Use userinterface_name for reference resolution
                    team_id=team_id
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
                    userinterface_name=userinterface_name,  # Use userinterface_name for reference resolution
                    team_id=team_id
                )
            elif command == 'waitForImageToAppearThenDisappear':
                success, message, details = self.waitForImageToAppearThenDisappear(
                    image_path=image_path,
                    timeout=timeout,
                    threshold=threshold,
                    area=area,
                    image_list=[source_path],  # Use source_path as image list
                    verification_index=verification_index,  # Use dynamic index
                    image_filter=image_filter,
                    userinterface_name=userinterface_name,  # Use userinterface_name for reference resolution
                    team_id=team_id
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
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Image verification execution error: {str(e)}',
                'screenshot_path': source_path if 'source_path' in locals() else None
            }

    def get_available_verifications(self) -> list:
        """Get list of available verification types with typed parameters."""
        from shared.src.lib.schemas.param_types import create_param, ParamType
        
        return [
            {
                "command": "waitForImageToAppear",
                "label": "Wait for Image to Appear",
                "description": "Wait for reference image to appear on screen using template matching",
                "params": {
                    "image_path": create_param(
                        ParamType.STRING,
                        required=True,
                        default="",
                        description="Path or URL to reference image",
                        placeholder="Select or upload reference image"
                    ),
                    "timeout": create_param(
                        ParamType.NUMBER,
                        required=False,
                        default=0,
                        description="Maximum time to wait (seconds)"
                    ),
                    "threshold": create_param(
                        ParamType.NUMBER,
                        required=False,
                        default=0.8,
                        description="Match threshold (0.0 to 1.0)",
                        min=0.0,
                        max=1.0
                    ),
                    "area": create_param(
                        ParamType.AREA,
                        required=False,
                        default=None,
                        description="Screen area to search in"
                    )
                },
                "verification_type": "image"
            },
            {
                "command": "waitForImageToDisappear",
                "label": "Wait for Image to Disappear",
                "description": "Wait for reference image to disappear from screen using template matching",
                "params": {
                    "image_path": create_param(
                        ParamType.STRING,
                        required=True,
                        default="",
                        description="Path or URL to reference image",
                        placeholder="Select or upload reference image"
                    ),
                    "timeout": create_param(
                        ParamType.NUMBER,
                        required=False,
                        default=0,
                        description="Maximum time to wait (seconds)"
                    ),
                    "threshold": create_param(
                        ParamType.NUMBER,
                        required=False,
                        default=0.8,
                        description="Match threshold (0.0 to 1.0)",
                        min=0.0,
                        max=1.0
                    ),
                    "area": create_param(
                        ParamType.AREA,
                        required=False,
                        default=None,
                        description="Screen area to search in"
                    )
                },
                "verification_type": "image"
            },
            {
                "command": "waitForImageToAppearThenDisappear",
                "label": "Wait for Image to Appear Then Disappear",
                "description": "Wait for reference image to appear and then disappear within timeout window",
                "params": {
                    "image_path": create_param(
                        ParamType.STRING,
                        required=True,
                        default="",
                        description="Path or URL to reference image",
                        placeholder="Select or upload reference image"
                    ),
                    "timeout": create_param(
                        ParamType.NUMBER,
                        required=False,
                        default=10,
                        description="Maximum time to wait (seconds)"
                    ),
                    "threshold": create_param(
                        ParamType.NUMBER,
                        required=False,
                        default=0.8,
                        description="Match threshold (0.0 to 1.0)",
                        min=0.0,
                        max=1.0
                    ),
                    "area": create_param(
                        ParamType.AREA,
                        required=False,
                        default=None,
                        description="Screen area to search in"
                    )
                },
                "verification_type": "image"
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
            
            # Generate UNIQUE filenames using timestamp to avoid browser caching issues
            timestamp = int(time.time() * 1000)  # milliseconds
            source_result_path = f'{results_dir}/source_image_{verification_index}_{timestamp}.png'
            overlay_result_path = f'{results_dir}/result_overlay_{verification_index}_{timestamp}.png'
            
            # === STEP 1: Handle Source Image ===
            if area:
                if not self.helpers.crop_image_to_area(source_path, source_result_path, area):
                    return {}
            else:
                self.helpers.copy_image_file(source_path, source_result_path)
            
            # Apply filter to source if requested
            if image_filter and image_filter != 'none':
                self.helpers.apply_image_filter(source_result_path, image_filter)
            
            # === STEP 3: Determine Reference Image Path (No Copying) ===
            reference_image_for_overlay = reference_path
            if image_filter and image_filter != 'none':
                base_path, ext = os.path.splitext(reference_path)
                filtered_reference_path = f"{base_path}_{image_filter}{ext}"
                
                if os.path.exists(filtered_reference_path):
                    reference_image_for_overlay = filtered_reference_path
            
            # === STEP 4: Create Overlay ===
            source_img = cv2.imread(source_result_path)
            if source_img is None:
                return {}
            
            ref_img = cv2.imread(reference_image_for_overlay)
            if ref_img is None:
                return {}
            
            overlay_img = self._create_pixel_difference_overlay(source_img, ref_img)
            if overlay_img is not None:
                cv2.imwrite(overlay_result_path, overlay_img)
            else:
                return {}
            
            # Return paths - NO reference_image_path since we don't create a copy
            return {
                "source_image_path": source_result_path,
                "result_overlay_path": overlay_result_path
                # NOTE: reference_image_path removed - use reference_image_url from waitForImageToAppear instead
            }
            
        except Exception as e:
            print(f"[@controller:ImageVerification] ERROR: Failed to generate comparison images: {e}")
            import traceback
            traceback.print_exc()
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
            
            # Calculate pixel-based match percentage
            matching_pixels = np.sum(matching_mask)
            total_pixels = source_gray.shape[0] * source_gray.shape[1]
            pixel_match_percentage = (matching_pixels / total_pixels) * 100
            
            print(f"[@overlay] Pixel comparison: {matching_pixels}/{total_pixels} = {pixel_match_percentage:.1f}% matching")
            print(f"[@overlay] Image size: {source_img.shape[1]}x{source_img.shape[0]}, pixel threshold: {pixel_threshold}")
            
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
            
            print(f"[@overlay] ⚠️  WARNING: Pixel-based match ({pixel_match_percentage:.1f}%) may differ from template matching score!")
            print(f"[@overlay] Template matching (TM_CCOEFF_NORMED) is sensitive to contrast/brightness, while pixel comparison uses absolute difference")
            
            return overlay
            
        except Exception as e:
            print(f"[@controller:ImageVerification] Error creating pixel difference overlay: {e}")
            return None

    def _resolve_reference_image(self, image_path: str, userinterface_name: str, team_id: str = None) -> Tuple[Optional[str], Optional[dict]]:
        """
        Resolve reference image path and area from R2 and database.
        
        Strategy:
        - Download from R2 (source of truth) with 24-hour cache
        - Always resolve area from database (REQUIRED - fails if not found)
        - Fail fast on any error (no fallbacks)
        
        Args:
            image_path: Reference image name or path
            userinterface_name: User interface name (e.g., 'horizon_android_tv')
            team_id: Team ID for database area resolution (REQUIRED)
            
        Returns:
            tuple: (local_image_path, area_dict) or (None, None) on failure
        """
        try:
            # Extract reference name from path
            if '/' in image_path:
                reference_name = os.path.basename(image_path)
            else:
                reference_name = image_path
            
            # Remove extension if present to get base name for database lookup
            base_name = reference_name.split('.')[0]
            
            print(f"[@controller:ImageVerification] Resolving reference: {reference_name} for userinterface: {userinterface_name}, team_id: {team_id}")
            
            # Use userinterface name for directory structure
            local_dir = os.path.join(self.references_dir, userinterface_name)
            os.makedirs(local_dir, exist_ok=True)
            
            # Use the reference name with proper extension
            if not reference_name.endswith(('.jpg', '.jpeg', '.png')):
                reference_name = f"{reference_name}.jpg"
            
            local_path = f'{local_dir}/{reference_name}'
            
            # PHASE 1: Reduced TTL to 5 minutes (was 24 hours)
            # PHASE 2: ETag-based freshness check
            from shared.src.lib.config.constants import CACHE_CONFIG
            REFERENCE_CACHE_TTL_SECONDS = CACHE_CONFIG['REFERENCE_IMAGE_TTL']
            
            should_download = True
            cached_etag = None
            
            if os.path.exists(local_path):
                import time
                file_age_seconds = time.time() - os.path.getmtime(local_path)
                file_age_minutes = file_age_seconds / 60
                
                # Read cached ETag from metadata file if exists
                etag_file = f"{local_path}.etag"
                if os.path.exists(etag_file):
                    try:
                        with open(etag_file, 'r') as f:
                            cached_etag = f.read().strip()
                    except Exception as e:
                        print(f"[@controller:ImageVerification] Could not read ETag file: {e}")
                
                if file_age_seconds < REFERENCE_CACHE_TTL_SECONDS:
                    # Cache is fresh by TTL, but check if R2 file changed (ETag check)
                    if cached_etag:
                        print(f"[@controller:ImageVerification] Checking if R2 file changed (cached ETag: {cached_etag[:8]}...)")
                        
                        from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
                        r2_object_key = f"reference-images/{userinterface_name}/{reference_name}"
                        
                        try:
                            cloudflare_utils = get_cloudflare_utils()
                            head_result = cloudflare_utils.head_file(r2_object_key)
                            
                            if head_result.get('success'):
                                r2_etag = head_result.get('etag', '').strip('"')
                                
                                if r2_etag and r2_etag != cached_etag:
                                    print(f"[@controller:ImageVerification] ETag mismatch! R2: {r2_etag[:8]}... vs Cached: {cached_etag[:8]}... - re-downloading")
                                    should_download = True
                                else:
                                    print(f"[@controller:ImageVerification] ETag match - using cached reference (age: {file_age_minutes:.1f}min): {local_path}")
                                    should_download = False
                            else:
                                # HEAD request failed, use cache anyway if TTL valid
                                print(f"[@controller:ImageVerification] ETag check failed - using cached reference (age: {file_age_minutes:.1f}min): {local_path}")
                                should_download = False
                        except Exception as e:
                            print(f"[@controller:ImageVerification] ETag check error: {e} - using cached reference")
                            should_download = False
                    else:
                        # No ETag cached, use TTL only
                        print(f"[@controller:ImageVerification] Using cached reference (age: {file_age_minutes:.1f}min, no ETag): {local_path}")
                        should_download = False
                else:
                    print(f"[@controller:ImageVerification] Cached reference is too old (age: {file_age_minutes:.1f}min), will re-download")
            
            # Download from R2 if needed (not cached or cache expired)
            if should_download:
                print(f"[@controller:ImageVerification] Downloading from R2 to: {local_path}")
                
                from shared.src.lib.utils.cloudflare_utils import get_cloudflare_utils
                
                # Construct R2 object key using userinterface name
                r2_object_key = f"reference-images/{userinterface_name}/{reference_name}"
                
                print(f"[@controller:ImageVerification] R2 object key: {r2_object_key}")
                
                # Download file - fail fast if this doesn't work
                cloudflare_utils = get_cloudflare_utils()
                download_result = cloudflare_utils.download_file(r2_object_key, local_path)
                
                if not download_result.get('success'):
                    error_msg = f"Failed to download reference from R2: {download_result.get('error')}"
                    print(f"[@controller:ImageVerification] {error_msg}")
                    return None, None
                
                # Store ETag for future comparisons
                etag = download_result.get('etag')
                if etag:
                    etag_file = f"{local_path}.etag"
                    try:
                        with open(etag_file, 'w') as f:
                            f.write(etag.strip('"'))
                        etag_clean = etag.strip('"')
                        print(f"[@controller:ImageVerification] Stored ETag: {etag_clean[:8]}...")
                    except Exception as e:
                        print(f"[@controller:ImageVerification] Could not save ETag file: {e}")
                
                print(f"[@controller:ImageVerification] Successfully downloaded reference from R2: {local_path}")
            
            # Always resolve area from database - REQUIRED
            if not team_id:
                error_msg = f"team_id is required for area resolution"
                print(f"[@controller:ImageVerification] {error_msg}")
                return None, None
            
            from shared.src.lib.utils.reference_utils import resolve_reference_area_backend
            resolved_area = resolve_reference_area_backend(base_name, userinterface_name, team_id)
            
            if not resolved_area:
                error_msg = f"No area found in database for reference: {base_name} (userinterface: {userinterface_name})"
                print(f"[@controller:ImageVerification] {error_msg}")
                return None, None
            
            # Round all coordinates to integers (pixels should always be integers)
            resolved_area = {k: round(v) if isinstance(v, (int, float)) else v for k, v in resolved_area.items()}
            
            print(f"[@controller:ImageVerification] Resolved area from database: {resolved_area}")
            return local_path, resolved_area
                
        except Exception as e:
            print(f"[@controller:ImageVerification] Reference resolution error: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    def _match_template(self, ref_img, source_img, area: dict = None, threshold: float = 0.8) -> Tuple[bool, float, Optional[dict]]:
        """
        Match template and return confidence + actual match location.
        
        Args:
            ref_img: Reference image
            source_img: Source image to search in
            area: Search area (may include fuzzy parameters)
            threshold: Matching threshold (used for early exit in fuzzy search)
        
        Returns:
            Tuple of (found, confidence, location) where:
                - found: True if confidence >= threshold (for early exit)
                - confidence: Actual matching score
                - location: Actual match area in source image
        """
        try:
            if area and 'fx' in area and area.get('fx') is not None:
                exact_area = {'x': area['x'], 'y': area['y'], 'width': area['width'], 'height': area['height']}
                fuzzy_area = {'fx': area['fx'], 'fy': area['fy'], 'fwidth': area['fwidth'], 'fheight': area['fheight']}
                # Pass threshold for early exit on exact match
                found, confidence, location = self.helpers.smart_fuzzy_search(source_img, ref_img, exact_area, fuzzy_area, threshold)
                return found, confidence, location  # Return 'found' flag for early exit!
            
            if area:
                x, y, w, h = int(area['x']), int(area['y']), int(area['width']), int(area['height'])
                cropped_source = source_img[y:y+h, x:x+w]
                location = {'x': x, 'y': y, 'width': w, 'height': h}
                
                # Use pixel-based matching (same logic as overlay)
                if cropped_source.shape != ref_img.shape:
                    ref_resized = cv2.resize(ref_img, (cropped_source.shape[1], cropped_source.shape[0]))
                else:
                    ref_resized = ref_img
                source_gray = cv2.cvtColor(cropped_source, cv2.COLOR_BGR2GRAY)
                ref_gray = cv2.cvtColor(ref_resized, cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(source_gray, ref_gray)
                matching_pixels = np.sum(diff <= 10)
                total_pixels = source_gray.shape[0] * source_gray.shape[1]
                pixel_score = matching_pixels / total_pixels
                
                print(f"[@controller:ImageVerification] Pixel match: {matching_pixels}/{total_pixels} = {pixel_score:.1%}")
                found = pixel_score >= threshold
                return found, pixel_score, location
            
            # No area specified - full image search
            result = cv2.matchTemplate(source_img, ref_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            ref_h, ref_w = ref_img.shape[:2]
            location = {'x': max_loc[0], 'y': max_loc[1], 'width': ref_w, 'height': ref_h}
            found = max_val >= threshold
            return found, max_val, location
            
        except Exception as e:
            print(f"[@controller:ImageVerification] ERROR: Template matching error: {e}")
            import traceback
            traceback.print_exc()
            return False, 0.0, None
    
    def _get_next_capture(self, filepath: str, offset: int) -> str:
        """Get next sequential capture filename"""
        match = re.search(r'capture_(\d{9})', filepath)
        if not match:
            return None
        num = int(match.group(1)) + offset
        return filepath.replace(match.group(0), f'capture_{num:09d}')

 