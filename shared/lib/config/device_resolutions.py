"""
Device Resolution Constants

Single centralized resolution for all devices.
One resolution to rule them all.
"""

# ONE centralized resolution for everything
DEFAULT_DEVICE_RESOLUTION = {"width": 1024, "height": 768}

# Simple function - always returns the same resolution
def get_device_resolution(device_model=None):
    """Get the centralized device resolution (always 1024x768)"""
    return DEFAULT_DEVICE_RESOLUTION
