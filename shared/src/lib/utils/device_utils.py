#!/usr/bin/env python3

"""
Device Utility Functions

Centralized utilities for common device operations to avoid code duplication.
"""

import os
import shutil
from typing import Optional, Tuple


def capture_screenshot_for_script(device, context, screenshot_id: str = None) -> Optional[str]:
    """
    Capture screenshot, copy to COLD storage, add to context for batch upload.
    
    Simple flow:
    1. Take screenshot (HOT storage)
    2. Copy to COLD root (safe from archiver for 1 hour)
    3. Add to context with ID
    4. Return screenshot ID for report mapping
    
    Upload happens in batch at script end via context.upload_screenshots_to_r2()
    
    Args:
        device: Device instance with controllers
        context: ScriptExecutionContext (required for script screenshots)
        screenshot_id: Optional ID for report mapping (e.g., "step_1_start", "zap_iteration_2")
        
    Returns:
        screenshot_id if successful, None otherwise
        
    Example:
        # Navigation screenshot
        capture_screenshot_for_script(device, context, "step_1_start")
        
        # Zap iteration screenshot  
        capture_screenshot_for_script(device, context, "zap_iter_1_motion")
        
        # Later, after batch upload:
        # context.screenshot_paths contains R2 URLs
        # Map using screenshot_id to populate report
    """
    try:
        av_controller = device._get_controller('av')
        if not av_controller:
            return None
        
        screenshot_path = av_controller.take_screenshot()
        if not screenshot_path:
            return None
        
        # Copy from HOT to COLD if needed (same logic as context.add_screenshot)
        if '/hot/' in screenshot_path:
            cold_path = screenshot_path.replace('/hot/', '/')
            os.makedirs(os.path.dirname(cold_path), exist_ok=True)
            if os.path.exists(screenshot_path):
                shutil.copy2(screenshot_path, cold_path)
            screenshot_path = cold_path
        
        # Add to context for batch upload
        context.add_screenshot(screenshot_path)
        
        # Store mapping for report generation (if ID provided)
        if screenshot_id:
            if not hasattr(context, 'screenshot_ids'):
                context.screenshot_ids = {}
            context.screenshot_ids[screenshot_id] = len(context.screenshot_paths) - 1  # Index in list
        
        return screenshot_id
        
    except Exception as e:
        print(f"⚠️ Screenshot capture failed: {e}")
        return None


def capture_screenshot(device, context=None, log_prefix: str = "") -> Optional[str]:
    """
    LEGACY: Capture screenshot with logging.
    Use capture_screenshot_for_script() for script executions!
    
    Args:
        device: Device instance with controllers
        context: Optional ScriptExecutionContext to add screenshot to
        log_prefix: Optional prefix for log messages (e.g., "[script_name]")
        
    Returns:
        Screenshot path if successful, None otherwise
    """
    try:
        av_controller = device._get_controller('av')
        
        if not av_controller:
            if log_prefix:
                print(f"⚠️ {log_prefix} No AV controller found, skipping screenshot")
            return None
        
        screenshot_path = av_controller.take_screenshot()
        
        if screenshot_path:
            # Add to context if provided
            if context:
                context.add_screenshot(screenshot_path)
            
            if log_prefix:
                print(f"✅ {log_prefix} Screenshot captured: {os.path.basename(screenshot_path)}")
            
            return screenshot_path
        else:
            if log_prefix:
                print(f"⚠️ {log_prefix} Screenshot capture returned None")
            return None
            
    except Exception as e:
        if log_prefix:
            print(f"⚠️ {log_prefix} Screenshot failed: {e}")
        return None


def add_existing_image_to_context(device, filename: str, context) -> Optional[str]:
    """
    Find existing capture image and add to context for upload.
    
    This is for EXISTING images (like motion analysis frames), not new screenshots.
    Handles hot→cold copy automatically, checks both locations, fails fast if missing.
    
    Args:
        device: Device instance with AV controller
        filename: Image filename (e.g., 'capture_000237967.jpg')
        context: ScriptExecutionContext
        
    Returns:
        Full path if found and added, None if missing (fail-fast)
        
    Example:
        # Motion analysis - find existing frame from FFmpeg
        path = add_existing_image_to_context(device, 'capture_000237967.jpg', context)
        if path:
            # Image found, copied to cold, added to context for upload
            motion_images.append({'path': path, 'filename': filename})
        else:
            # Image missing - fail fast, don't add broken paths
            print(f"❌ Motion image not found: {filename}")
    """
    from shared.src.lib.utils.storage_path_utils import (
        get_captures_path, 
        get_capture_folder,
        get_cold_storage_path
    )
    
    try:
        av_controller = device._get_controller('av')
        if not av_controller or not hasattr(av_controller, 'video_capture_path'):
            return None
        
        # Get device folder (e.g., 'capture4' from '/var/www/html/stream/capture4')
        device_folder = get_capture_folder(av_controller.video_capture_path)
        
        # 1. Check HOT first (where FFmpeg actively generates files)
        # get_captures_path() automatically returns HOT or COLD based on RAM mode
        hot_captures_path = get_captures_path(device_folder)
        hot_image_path = os.path.join(hot_captures_path, filename)
        
        if os.path.exists(hot_image_path):
            # Found in hot - add_screenshot will auto-copy to cold
            context.add_screenshot(hot_image_path)
            # Return cold path (same as what add_screenshot stores internally)
            cold_path = hot_image_path.replace('/hot/', '/')
            return cold_path
        
        # 2. Check COLD (may have been archived already by hot_cold_archiver)
        # Use centralized cold path resolution
        cold_captures_path = get_cold_storage_path(device_folder, 'captures')
        cold_image_path = os.path.join(cold_captures_path, filename)
        
        if os.path.exists(cold_image_path):
            # Found in cold - already persisted
            context.add_screenshot(cold_image_path)
            return cold_image_path
        
        # 3. FAIL FAST - image not found in either location
        print(f"❌ [device_utils] Motion image not found: {filename} (checked hot: {hot_captures_path}, cold: {cold_captures_path})")
        return None
        
    except Exception as e:
        print(f"❌ [device_utils] Error adding existing image {filename}: {e}")
        return None


def get_av_controller(device):
    """
    Get the AV controller from a device.
    
    Args:
        device: Device instance
        
    Returns:
        AV controller instance or None
    """
    return device._get_controller('av')


def get_device_capture_path(device) -> Optional[str]:
    """
    Get the capture base path from a device's AV controller.
    
    RENAMED from get_capture_folder() to avoid conflict with storage_path_utils.get_capture_folder()
    
    Args:
        device: Device instance
        
    Returns:
        Capture base path or None (e.g., '/var/www/html/stream/capture4')
        
    Example:
        capture_path = get_device_capture_path(device)
        if capture_path:
            # Use storage_path_utils functions to get specific paths
            from shared.src.lib.utils.storage_path_utils import get_captures_path, get_capture_folder
            device_folder = get_capture_folder(capture_path)
            captures_path = get_captures_path(device_folder)
    """
    av_controller = device._get_controller('av')
    if av_controller and hasattr(av_controller, 'video_capture_path'):
        return av_controller.video_capture_path
    return None

