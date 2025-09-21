"""
Verification Controllers Package

This package contains all verification and validation implementations.
Each controller provides different methods for verifying device states and content.

Available Controllers:
- TextVerificationController: OCR-based text verification using Tesseract
- ImageVerificationController: Template matching-based image verification using OpenCV
- ADBVerificationController: Direct ADB element verification using ADB commands
- AppiumVerificationController: Cross-platform element verification using Appium WebDriver
- VideoVerificationController: Motion detection and video content verification
- AudioVerificationController: Audio level and sound verification
- VNCStreamController: VNC stream controller for VNC-based verification

Available Helpers:
- VideoRestartHelpers: Restart video generation and analysis functionality
"""

from .text import TextVerificationController
from .image import ImageVerificationController
from .adb import ADBVerificationController
from .appium import AppiumVerificationController
from .video import VideoVerificationController
from .audio import AudioVerificationController
from .vnc_stream import VNCStreamController
from .video_restart_helpers import VideoRestartHelpers

__all__ = [
    'TextVerificationController', 
    'ImageVerificationController',
    'ADBVerificationController',
    'AppiumVerificationController',
    'VideoVerificationController',
    'AudioVerificationController',
    'VNCStreamController',
    'VideoRestartHelpers'
]
