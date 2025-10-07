#!/usr/bin/env python3

"""
Device Utility Functions

Centralized utilities for common device operations to avoid code duplication.
"""

import os
from typing import Optional, Tuple


def capture_screenshot(device, context=None, log_prefix: str = "") -> Optional[str]:
    """
    Capture a screenshot from a device and optionally add it to context.
    
    This utility encapsulates the common pattern of:
    - Getting the AV controller
    - Taking a screenshot
    - Optionally adding to context
    - Error handling and logging
    
    Args:
        device: Device instance with controllers
        context: Optional ScriptExecutionContext to add screenshot to
        log_prefix: Optional prefix for log messages (e.g., "[script_name]")
        
    Returns:
        Screenshot path if successful, None otherwise
        
    Example:
        # Simple usage
        screenshot_path = capture_screenshot(device)
        
        # With context (auto-adds to context.screenshot_paths)
        screenshot_path = capture_screenshot(device, context, "[fullzap]")
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

