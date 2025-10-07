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


def get_av_controller(device):
    """
    Get the AV controller from a device.
    
    Args:
        device: Device instance
        
    Returns:
        AV controller instance or None
    """
    return device._get_controller('av')


def get_capture_folder(device) -> Optional[str]:
    """
    Get the capture folder path from a device's AV controller.
    
    Args:
        device: Device instance
        
    Returns:
        Capture folder path or None
        
    Example:
        capture_folder = get_capture_folder(device)
        if capture_folder:
            captures_path = f"{capture_folder}/captures"
    """
    av_controller = device._get_controller('av')
    if av_controller and hasattr(av_controller, 'video_capture_path'):
        return av_controller.video_capture_path
    return None

