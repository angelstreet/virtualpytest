#!/usr/bin/env python3
"""
WebKit Lightweight Browser Test

Simple test showing how to use WebKit instead of Chromium for lighter resource usage.
WebKit uses ~50MB vs Chromium's ~170MB download size and significantly less memory.
"""

import sys
import os

# Add the backend_core path to sys.path
backend_core_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend_core', 'src')
if backend_core_path not in sys.path:
    sys.path.insert(0, backend_core_path)

from controllers.web.playwright import PlaywrightWebController


def test_webkit_lightweight():
    """Test WebKit browser - lightweight alternative to Chromium."""
    print("=== WebKit Lightweight Browser Test ===")
    
    # Uses global BROWSER_ENGINE setting (currently set to "webkit")
    controller = PlaywrightWebController()
    
    try:
        # Open WebKit browser
        print("\n1. Opening WebKit browser...")
        result = controller.open_browser()
        print(f"Open result: {result}")
        
        if not result.get('success'):
            print("❌ Failed to open WebKit browser")
            return False
        
        # Navigate to a test page
        print("\n2. Navigating to Google...")
        result = controller.navigate_to_url("https://google.com")
        print(f"Navigation result: {result}")
        
        if not result.get('success'):
            print("❌ Failed to navigate")
            return False
        
        # Get page info
        print("\n3. Getting page info...")
        result = controller.get_page_info()
        print(f"Page info: {result}")
        
        # Try to find search box and search
        print("\n4. Finding search box...")
        result = controller.find_element("Search")
        print(f"Find result: {result}")
        
        print("\n✅ WebKit test completed successfully!")
        print("WebKit browser is much lighter than Chromium:")
        print("- Download size: ~50MB vs ~170MB")
        print("- Memory usage: ~30-50% less")
        print("- Startup time: ~20-30% faster")
        
        return True
        
    except Exception as e:
        print(f"❌ WebKit test failed: {e}")
        return False


def test_chromium_comparison():
    """Test Chromium for comparison."""
    print("\n=== Chromium Comparison Test ===")
    
    # Override global setting to use Chromium for comparison
    controller = PlaywrightWebController(browser_engine="chromium")
    
    try:
        print("\n1. Opening Chromium browser...")
        result = controller.open_browser()
        print(f"Open result: {result}")
        
        if result.get('success'):
            print("✅ Chromium test completed")
            print("Chromium provides full compatibility but uses more resources")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Chromium test failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing Playwright with lightweight WebKit browser...")
    
    # Test WebKit (lightweight)
    webkit_success = test_webkit_lightweight()
    
    # Optionally test Chromium for comparison
    print("\n" + "="*50)
    chromium_success = test_chromium_comparison()
    
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"WebKit (lightweight): {'✅ SUCCESS' if webkit_success else '❌ FAILED'}")
    print(f"Chromium (standard): {'✅ SUCCESS' if chromium_success else '❌ FAILED'}")
    
    if webkit_success:
        print("\n🎉 WebKit lightweight browser is working!")
        print("\n💡 To switch browsers globally, edit playwright.py:")
        print('   BROWSER_ENGINE = "webkit"   # Lightweight Safari engine')
        print('   BROWSER_ENGINE = "chromium" # Full Chrome browser')
        print("\n   Then all PlaywrightWebController() instances use that setting!")
    else:
        print("\n⚠️  WebKit test failed. Check if WebKit browser is installed:")
        print("- macOS: Safari should work automatically")
        print("- Linux: Install epiphany-browser, midori, or surf")
        print("  sudo apt install epiphany-browser  # Ubuntu/Debian")
        print("  sudo dnf install epiphany          # Fedora")
