"""
Remote Controllers Package

This package contains all remote control implementations for different device types.
Each controller provides remote control functionality for specific devices or protocols.

Available Controllers:
- AndroidTVRemoteController: Real ADBAndroid TV remote control
- AndroidMobileRemoteController: Real ADBAndroid mobile remote control  
- IRRemoteController: Infrared remote control with classic TV/STB buttons
- BluetoothRemoteController: Bluetooth HID remote control
"""

from .android_tv import AndroidTVRemoteController
from .android_mobile import AndroidMobileRemoteController
from .infrared import IRRemoteController
from .bluetooth import BluetoothRemoteController

__all__ = [
    'AndroidTVRemoteController', 
    'AndroidMobileRemoteController',
    'IRRemoteController',
    'BluetoothRemoteController'
]
